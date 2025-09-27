"""
Database Service Module

This module provides an asynchronous service for interacting with a Teradata database.
It handles connection management, query execution, and result processing.
"""

from loguru import logger
from typing import Any, Dict, List, Optional

import teradatasql
import asyncio
from src.core.config import settings


class DatabaseService:
    """
    A service class for interacting with a Teradata database.
    """

    def __init__(self) -> None:
        """
        Initialize the Database service with connection parameters from settings.
        """
        self.host = settings.TERADATA_HOST
        self.user = settings.TERADATA_USER
        self.password = settings.TERADATA_PASSWORD
        self.database = settings.TERADATA_DATABASE

        # Connection string
        self.connection_params = {
            "host": self.host,
            "user": self.user,
            "password": self.password,
            "database": self.database,
        }

        logger.info(f"Database service initialized for {self.database} on {self.host}")

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
            logger.info(f"Executing query: {query[:50]}...")

            # Use an async executor to run the blocking database operations
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
        connection = None
        cursor = None

        try:
            # Connect to the database
            connection = teradatasql.connect(**self.connection_params)
            cursor = connection.cursor()

            # Execute the query with parameters if provided
            if params:
                param_values = tuple(params.values())
                cursor.execute(query, param_values)
            else:
                cursor.execute(query)

            # Fetch all results
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            # Convert results to a list of dictionaries
            results = [dict(zip(columns, row)) for row in rows]
            logger.debug(f"Query returned {len(results)} rows")
            return results

        except teradatasql.Error as e:
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            # Clean up resources
            if cursor:
                cursor.close()
            if connection:
                connection.close()
