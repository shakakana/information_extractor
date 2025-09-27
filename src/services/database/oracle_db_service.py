"""
Database Service Module

This module provides an asynchronous service for interacting with an Oracle database.
It handles connection management, query execution, and result processing.
"""

from loguru import logger
from typing import Any, Dict, List, Optional

import oracledb
import asyncio
from src.core.config import settings

# Set this to False to return strings instead of LOB objects
# https://python-oracledb.readthedocs.io/en/latest/api_manual/defaults.html#oracledb.Defaults.fetch_lobs
oracledb.defaults.fetch_lobs = False

# Configure loguru logger
logger.add("logs/oracle_db_service.log", rotation="1 MB", level="INFO")

# Look for Oracle Client libraries (required for thick mode)
# https://python-oracledb.readthedocs.io/en/latest/user_guide/initialization.html
oracledb.init_oracle_client()


class DatabaseService:
    """
    A service class for interacting with an Oracle database.
    """

    def __init__(self) -> None:
        """
        Initialize the Database service with connection parameters from settings.
        """
        self.user = settings.ORACLE_USER
        self.password = settings.ORACLE_PASSWORD
        self.dsn = settings.ORACLE_DSN

        # Connection parameters
        self.connection_params = {
            "user": self.user,
            "password": self.password,
            "dsn": self.dsn,
        }

        logger.info(f"Database service initialized for {self.dsn}")

    async def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute an SQL query and return the results.

        Args:
            query: The SQL query to execute
            params: Optional parameters for the query

        Returns:
            List[Dict[str, Any]]: Query results as a list of dictionaries
        """
        try:
            logger.debug(f"Executing query: {query}")

            return await asyncio.to_thread(self._run_query, query, params)

        except Exception as e:
            logger.exception(f"Error executing query: {str(e)}")
            raise

    def _run_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Run a query on the database (synchronous operation).

        Args:
            query: The SQL query to run
            params: Optional parameters for the query

        Returns:
            List[Dict[str, Any]]: Query results as a list of dictionaries
        """
        try:
            with oracledb.connect(**self.connection_params) as connection:
                with connection.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()

                        results = [dict(zip(columns, row)) for row in rows]
                        logger.debug(f"Query returned {len(results)} rows")
                        return results
                    else:
                        connection.commit()
                        logger.debug("Query executed successfully with no results")
                        return []

        except oracledb.DatabaseError as e:
            logger.error(f"Database error: {str(e)}")
            raise
