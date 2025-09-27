"""
MSSQL Database Service Module

This module provides a simplified, async service for interacting with Microsoft SQL Server.
Designed for beginner developers with comprehensive error handling and clear examples.
"""

import asyncio
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
import pyodbc
from loguru import logger

from src.core.config import settings


@dataclass
class QueryResult:
    """Data class for query results with metadata"""

    data: List[Dict[str, Any]]
    row_count: int
    execution_time: float
    query_hash: Optional[str] = None


class DatabaseError(Exception):
    """
    Exception for all database-related errors.

    Provides additional context while keeping the API simple for beginners.
    """

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error
        self.timestamp = datetime.now()

    def __str__(self):
        base_msg = super().__str__()
        if self.original_error:
            return f"{base_msg} (Original: {type(self.original_error).__name__}: {self.original_error})"
        return base_msg


class MSSQLService:
    """
    Simplified MSSQL Database Service for beginner developers.

    Provides async database operations with automatic connection management,
    comprehensive error handling, and clear logging.

    Features:
    - Async query execution
    - Automatic connection management
    - Stored procedure support
    - Bulk operations
    - Transaction support
    - Retry logic with exponential backoff
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        """
        Initialize the MSSQL service.

        Args:
            max_retries: Maximum number of retry attempts for failed operations
            retry_delay: Initial delay between retries (seconds)
        """
        self.server = settings.MSSQL_SERVER
        self.database = settings.MSSQL_DATABASE
        self.user = settings.MSSQL_USER
        self.password = settings.MSSQL_PASSWORD
        self.driver = settings.MSSQL_DRIVER
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        logger.info(
            f"MSSQL Service initialized for database '{self.database}' on server '{self.server}'"
        )

    def _build_connection_string(self) -> str:
        """
        Build a secure connection string with proper password escaping.

        Returns:
            str: Formatted connection string
        """
        # URL encode password to handle special characters safely
        encoded_password = urllib.parse.quote_plus(self.password)

        connection_string = (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.user};"
            f"PWD={encoded_password};"
            f"TrustServerCertificate=yes;"
            f"Encrypt=yes;"
            f"Connection Timeout=30;"
            f"Command Timeout=300;"
        )

        return connection_string

    def _create_connection(self) -> pyodbc.Connection:
        """
        Create a database connection with fallback methods.

        Returns:
            pyodbc.Connection: Active database connection

        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Method 1: Dictionary-based connection (most reliable)
            conn_params = {
                "DRIVER": f"{{{self.driver}}}",
                "SERVER": self.server,
                "DATABASE": self.database,
                "UID": self.user,
                "PWD": self.password,
                "TrustServerCertificate": "yes",
                "Encrypt": "yes",
                "Connection Timeout": "30",
                "Command Timeout": "300",
            }

            connection = pyodbc.connect(**conn_params)
            logger.debug("Database connection established using dictionary method")
            return connection

        except Exception as e1:
            logger.warning(f"Dictionary connection failed: {e1}")

            try:
                # Fallback: Connection string method
                connection_string = self._build_connection_string()
                connection = pyodbc.connect(connection_string)
                logger.debug("Database connection established using connection string")
                return connection

            except Exception as e2:
                error_msg = f"All connection methods failed. Dictionary error: {e1}. String error: {e2}"
                logger.error(error_msg)
                raise DatabaseError(error_msg, original_error=e2) from e2

    async def _execute_with_retry(self, operation, *args, **kwargs):
        """
        Execute database operation with exponential backoff retry logic.

        Args:
            operation: Database operation to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the database operation

        Raises:
            DatabaseError: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await asyncio.to_thread(operation, *args, **kwargs)

            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Database operation failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {wait_time:.1f} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Database operation failed after {self.max_retries + 1} attempts"
                    )

        raise DatabaseError(
            f"Operation failed after {self.max_retries + 1} attempts"
        ) from last_exception

    async def execute_query(
        self,
        query: str,
        params: Optional[Union[Tuple, Dict, List]] = None,
        fetch_results: bool = True,
    ) -> QueryResult:
        """
        Execute an SQL query and return results.

        Args:
            query: SQL query to execute
            params: Query parameters (tuple, dict, or list)
            fetch_results: Whether to fetch and return results

        Returns:
            QueryResult: Query results with metadata

        Raises:
            QueryError: If query execution fails

        Examples:
            # Simple query
            result = await db.execute_query("SELECT * FROM users WHERE active = 1")

            # Query with parameters
            result = await db.execute_query(
                "SELECT * FROM users WHERE department = ? AND active = ?",
                params=("IT", 1)
            )

            # Insert/Update without fetching results
            result = await db.execute_query(
                "UPDATE users SET last_login = GETDATE() WHERE id = ?",
                params=(user_id,),
                fetch_results=False
            )
        """
        import time

        start_time = time.time()

        try:
            logger.info(
                f"Executing query: {query[:100]}{'...' if len(query) > 100 else ''}"
            )

            if params:
                logger.debug(f"Query parameters: {params}")

            result = await self._execute_with_retry(
                self._run_query, query, params, fetch_results
            )

            execution_time = time.time() - start_time
            logger.info(f"Query executed successfully in {execution_time:.2f} seconds")

            return QueryResult(
                data=result,
                row_count=len(result),
                execution_time=execution_time,
                query_hash=str(hash(query)),
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Query failed after {execution_time:.2f} seconds: {str(e)}")
            raise DatabaseError(
                f"Query execution failed: {str(e)}", original_error=e
            ) from e

    def _run_query(
        self,
        query: str,
        params: Optional[Union[Tuple, Dict, List]] = None,
        fetch_results: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Internal method to run query synchronously.

        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_results: Whether to fetch results

        Returns:
            List[Dict[str, Any]]: Query results as list of dictionaries
        """
        connection = None
        cursor = None

        try:
            connection = self._create_connection()
            cursor = connection.cursor()

            # Execute query with parameters
            if params:
                if isinstance(params, dict):
                    # Convert dict to tuple for pyodbc
                    param_values = tuple(params.values())
                elif isinstance(params, list):
                    param_values = tuple(params)
                else:
                    param_values = params

                cursor.execute(query, param_values)
            else:
                cursor.execute(query)

            if fetch_results and cursor.description:
                # Fetch results for SELECT queries
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                results = [dict(zip(columns, row)) for row in rows]
                logger.debug(f"Query returned {len(results)} rows")
                return results
            else:
                # For INSERT, UPDATE, DELETE queries
                rows_affected = cursor.rowcount
                connection.commit()
                logger.debug(f"Query affected {rows_affected} rows")
                return [{"rows_affected": rows_affected}]

        except pyodbc.Error as e:
            logger.error(f"Database error: {str(e)}")
            if connection:
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    async def execute_stored_procedure(
        self, proc_name: str, params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """
        Execute a stored procedure.

        Args:
            proc_name: Name of the stored procedure
            params: Parameters for the stored procedure

        Returns:
            QueryResult: Results from the stored procedure

        Examples:
            # Execute procedure without parameters
            result = await db.execute_stored_procedure("GetActiveUsers")

            # Execute procedure with parameters
            result = await db.execute_stored_procedure(
                "GetUsersByDepartment",
                params={"department": "IT", "active_only": True}
            )
        """
        import time

        start_time = time.time()

        try:
            logger.info(f"Executing stored procedure: {proc_name}")

            if params:
                logger.debug(f"Procedure parameters: {params}")

            result = await self._execute_with_retry(
                self._run_stored_procedure, proc_name, params
            )

            execution_time = time.time() - start_time
            logger.info(
                f"Stored procedure executed successfully in {execution_time:.2f} seconds"
            )

            return QueryResult(
                data=result, row_count=len(result), execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Stored procedure failed after {execution_time:.2f} seconds: {str(e)}"
            )
            raise DatabaseError(
                f"Stored procedure execution failed: {str(e)}", original_error=e
            ) from e

    def _run_stored_procedure(
        self, proc_name: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Internal method to run stored procedure synchronously.

        Args:
            proc_name: Name of the stored procedure
            params: Parameters for the stored procedure

        Returns:
            List[Dict[str, Any]]: Results from the stored procedure
        """
        connection = None
        cursor = None

        try:
            connection = self._create_connection()
            cursor = connection.cursor()

            if params:
                # Build parameterized call
                param_placeholders = ", ".join([f"@{key}=?" for key in params.keys()])
                call_string = f"{{CALL {proc_name}({param_placeholders})}}"
                cursor.execute(call_string, tuple(params.values()))
            else:
                call_string = f"{{CALL {proc_name}}}"
                cursor.execute(call_string)

            if cursor.description:
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                results = [dict(zip(columns, row)) for row in rows]
                logger.debug(f"Stored procedure returned {len(results)} rows")
                return results
            else:
                logger.debug("Stored procedure executed with no results")
                return []

        except pyodbc.Error as e:
            logger.error(f"Stored procedure error: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    async def bulk_insert(
        self, table_name: str, records: List[Dict[str, Any]], batch_size: int = 1000
    ) -> QueryResult:
        """
        Insert multiple records efficiently using bulk operations.

        Args:
            table_name: Target table name
            records: List of dictionaries containing the data to insert
            batch_size: Number of records to insert per batch

        Returns:
            QueryResult: Information about the bulk insert operation

        Examples:
            records = [
                {"name": "John", "email": "john@example.com", "active": True},
                {"name": "Jane", "email": "jane@example.com", "active": True},
            ]
            result = await db.bulk_insert("users", records)
        """
        import time

        if not records:
            logger.warning("No records provided for bulk insert")
            return QueryResult(data=[], row_count=0, execution_time=0.0)

        start_time = time.time()
        total_inserted = 0

        try:
            logger.info(
                f"Starting bulk insert of {len(records)} records into {table_name}"
            )

            # Get column names from first record
            columns = list(records[0].keys())
            column_names = ", ".join(columns)
            placeholders = ", ".join(["?" for _ in columns])

            insert_query = (
                f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
            )

            # Process in batches
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                batch_values = [
                    tuple(record[col] for col in columns) for record in batch
                ]

                await self._execute_with_retry(
                    self._run_bulk_insert, insert_query, batch_values
                )

                total_inserted += len(batch)
                logger.debug(f"Inserted batch: {total_inserted}/{len(records)} records")

            execution_time = time.time() - start_time
            logger.info(
                f"Bulk insert completed: {total_inserted} records in {execution_time:.2f} seconds"
            )

            return QueryResult(
                data=[{"total_inserted": total_inserted}],
                row_count=total_inserted,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Bulk insert failed after {execution_time:.2f} seconds: {str(e)}"
            )
            raise DatabaseError(
                f"Bulk insert failed: {str(e)}", original_error=e
            ) from e

    def _run_bulk_insert(self, query: str, batch_values: List[Tuple]) -> None:
        """
        Internal method for bulk insert operations.

        Args:
            query: INSERT SQL query
            batch_values: List of tuples containing values to insert
        """
        connection = None
        cursor = None

        try:
            connection = self._create_connection()
            cursor = connection.cursor()

            # Enable fast_executemany
            cursor.fast_executemany = True

            cursor.executemany(query, batch_values)
            connection.commit()

        except pyodbc.Error as e:
            if connection:
                connection.rollback()
            logger.error(f"Bulk insert error: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    @asynccontextmanager
    async def transaction(self):
        """
        Async context manager for database transactions.

        Examples:
            async with db.transaction():
                await db.execute_query("INSERT INTO users ...")
                await db.execute_query("UPDATE accounts ...")
                # Transaction is committed automatically
        """
        connection = None
        try:
            connection = await asyncio.to_thread(self._create_connection)
            connection.autocommit = False

            logger.debug("Transaction started")
            yield connection

            await asyncio.to_thread(connection.commit)
            logger.debug("Transaction committed")

        except Exception as e:
            if connection:
                await asyncio.to_thread(connection.rollback)
                logger.warning(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            if connection:
                connection.autocommit = True
                connection.close()

    async def test_connection(self) -> bool:
        """
        Test database connectivity.

        Returns:
            bool: True if connection successful, False otherwise

        Examples:
            if await db.test_connection():
                print("Database is accessible")
            else:
                print("Database connection failed")
        """
        try:
            result = await self.execute_query("SELECT 1 AS test_value")
            if result.data and result.data[0].get("test_value") == 1:
                logger.info("Database connection test successful")
                return True
            else:
                logger.error("Database connection test returned unexpected result")
                return False
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    async def get_table_info(self, table_name: str) -> QueryResult:
        """
        Get information about a table's structure.

        Args:
            table_name: Name of the table to inspect

        Returns:
            QueryResult: Table column information

        Examples:
            info = await db.get_table_info("users")
            for column in info.data:
                print(f"Column: {column['COLUMN_NAME']}, Type: {column['DATA_TYPE']}")
        """
        query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
        """

        return await self.execute_query(query, params=(table_name,))

    async def get_row_count(self, table_name: str, where_clause: str = "") -> int:
        """
        Get the number of rows in a table.

        Args:
            table_name: Name of the table
            where_clause: Optional WHERE clause (without the WHERE keyword)

        Returns:
            int: Number of rows

        Examples:
            # Total rows
            total = await db.get_row_count("users")

            # Rows with condition
            active_users = await db.get_row_count("users", "active = 1")
        """
        query = f"SELECT COUNT(*) as row_count FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        result = await self.execute_query(query)
        return result.data[0]["row_count"] if result.data else 0


# Convenience functions for common operations
async def quick_query(
    query: str, params: Optional[Tuple] = None
) -> List[Dict[str, Any]]:
    """
    Quick database query for simple operations.

    Args:
        query: SQL query to execute
        params: Optional query parameters

    Returns:
        List[Dict[str, Any]]: Query results

    Examples:
        # Simple select
        users = await quick_query("SELECT * FROM users WHERE active = 1")

        # With parameters
        user = await quick_query("SELECT * FROM users WHERE id = ?", (user_id,))
    """
    db = MSSQLService()
    result = await db.execute_query(query, params)
    return result.data


async def test_database_connection() -> bool:
    """
    Test database connection - useful for health checks.

    Returns:
        bool: True if database is accessible
    """
    db = MSSQLService()
    return await db.test_connection()
