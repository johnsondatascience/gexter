"""
Database abstraction layer supporting both SQLite and PostgreSQL

This module provides a unified interface for database operations,
allowing the application to switch between SQLite and PostgreSQL
without changing application code.
"""

import os
import sqlite3
from typing import Optional, Union, Any
from contextlib import contextmanager
import pandas as pd

try:
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.pool import NullPool, QueuePool
    from sqlalchemy.engine import Engine
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


class DatabaseConnection:
    """
    Database connection manager supporting both SQLite and PostgreSQL

    Automatically handles:
    - Connection string creation
    - Connection pooling (PostgreSQL)
    - Column name quoting for PostgreSQL
    - Database-specific SQL syntax
    """

    def __init__(self, db_type: str = 'sqlite', **kwargs):
        """
        Initialize database connection

        Args:
            db_type: 'sqlite' or 'postgresql'
            **kwargs: Database connection parameters
                For SQLite: db_path
                For PostgreSQL: host, port, database, user, password, pool_size, max_overflow
        """
        self.db_type = db_type.lower()
        self.kwargs = kwargs
        self.engine: Optional[Engine] = None

        if self.db_type not in ['sqlite', 'postgresql']:
            raise ValueError(f"Unsupported database type: {db_type}")

        if self.db_type == 'postgresql' and not HAS_SQLALCHEMY:
            raise ImportError("SQLAlchemy and psycopg2 required for PostgreSQL support")

        self._create_engine()

    def _create_engine(self):
        """Create SQLAlchemy engine based on database type"""
        if self.db_type == 'sqlite':
            db_path = self.kwargs.get('db_path', 'data/gex_data.db')
            connection_string = f'sqlite:///{db_path}'

            if HAS_SQLALCHEMY:
                self.engine = create_engine(
                    connection_string,
                    poolclass=NullPool,  # SQLite doesn't benefit from pooling
                    connect_args={'check_same_thread': False}
                )
            else:
                # Fallback to raw sqlite3
                self.engine = None
                self.db_path = db_path

        elif self.db_type == 'postgresql':
            host = self.kwargs.get('host', 'localhost')
            port = self.kwargs.get('port', 5432)
            database = self.kwargs.get('database', 'gexdb')
            user = self.kwargs.get('user', 'gexuser')
            password = self.kwargs.get('password', '')
            pool_size = self.kwargs.get('pool_size', 5)
            max_overflow = self.kwargs.get('max_overflow', 10)

            connection_string = f'postgresql://{user}:{password}@{host}:{port}/{database}'

            self.engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,  # Verify connections before using
                connect_args={'options': '-c timezone=America/New_York'}
            )

    @contextmanager
    def get_connection(self):
        """
        Get database connection (context manager)

        Usage:
            with db.get_connection() as conn:
                df = pd.read_sql(query, conn)
        """
        if self.engine:
            with self.engine.connect() as conn:
                yield conn
        else:
            # Fallback for SQLite without SQLAlchemy
            conn = sqlite3.connect(self.db_path)
            try:
                yield conn
            finally:
                conn.close()

    def execute(self, query: str, params: Optional[dict] = None):
        """
        Execute a SQL query

        Args:
            query: SQL query string
            params: Optional parameters for query

        Returns:
            Result of query execution
        """
        with self.get_connection() as conn:
            if self.engine:
                result = conn.execute(text(query), params or {})
                conn.commit()
                return result
            else:
                cursor = conn.cursor()
                if params:
                    result = cursor.execute(query, params)
                else:
                    result = cursor.execute(query)
                conn.commit()
                return result

    def read_sql(self, query: str, params: Optional[dict] = None) -> pd.DataFrame:
        """
        Execute a SELECT query and return results as DataFrame

        Args:
            query: SQL SELECT query
            params: Optional parameters

        Returns:
            DataFrame with query results
        """
        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=params)

    def to_sql(self, df: pd.DataFrame, table_name: str, if_exists: str = 'append',
               index: bool = True, **kwargs):
        """
        Write DataFrame to database table

        Args:
            df: DataFrame to write
            table_name: Name of table
            if_exists: 'fail', 'replace', or 'append'
            index: Whether to write DataFrame index
            **kwargs: Additional arguments for to_sql
        """
        with self.get_connection() as conn:
            df.to_sql(table_name, conn, if_exists=if_exists, index=index, **kwargs)

    def get_table_info(self, table_name: str) -> pd.DataFrame:
        """
        Get table schema information

        Args:
            table_name: Name of table

        Returns:
            DataFrame with column information
        """
        if self.db_type == 'sqlite':
            query = f'PRAGMA table_info({table_name})'
            return self.read_sql(query)
        else:
            # PostgreSQL
            query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = :table_name
            ORDER BY ordinal_position
            """
            return self.read_sql(query, {'table_name': table_name})

    def get_tables(self) -> list:
        """
        Get list of tables in database

        Returns:
            List of table names
        """
        if self.db_type == 'sqlite':
            query = "SELECT name FROM sqlite_master WHERE type='table'"
            df = self.read_sql(query)
            return df['name'].tolist()
        else:
            # PostgreSQL
            query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """
            df = self.read_sql(query)
            return df['table_name'].tolist()

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        return table_name in self.get_tables()

    def quote_identifier(self, identifier: str) -> str:
        """
        Quote identifier for database-specific syntax

        PostgreSQL requires double quotes for identifiers with dots
        SQLite can use brackets or double quotes

        Args:
            identifier: Column or table name

        Returns:
            Properly quoted identifier
        """
        if self.db_type == 'postgresql':
            # PostgreSQL uses double quotes
            return f'"{identifier}"'
        else:
            # SQLite can use double quotes or brackets
            return f'"{identifier}"' if '.' in identifier else identifier

    def get_max_timestamp(self, table_name: str = 'gex_table',
                         timestamp_column: str = 'greeks.updated_at') -> Optional[str]:
        """
        Get maximum timestamp from table

        Args:
            table_name: Name of table
            timestamp_column: Name of timestamp column

        Returns:
            Maximum timestamp as string, or None if table is empty
        """
        quoted_col = self.quote_identifier(timestamp_column)
        query = f'SELECT MAX({quoted_col}) as max_ts FROM {table_name}'

        try:
            result = self.read_sql(query)
            if not result.empty and result['max_ts'].iloc[0] is not None:
                return str(result['max_ts'].iloc[0])
        except Exception:
            return None

        return None

    def get_row_count(self, table_name: str = 'gex_table') -> int:
        """
        Get total number of rows in table

        Args:
            table_name: Name of table

        Returns:
            Number of rows
        """
        query = f'SELECT COUNT(*) as count FROM {table_name}'
        result = self.read_sql(query)
        return int(result['count'].iloc[0])

    def close(self):
        """Close database connection and dispose of engine"""
        if self.engine:
            self.engine.dispose()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def __repr__(self):
        return f"DatabaseConnection(type='{self.db_type}')"


def create_database_from_config(config) -> DatabaseConnection:
    """
    Create database connection from Config object

    Args:
        config: Config object with database settings

    Returns:
        DatabaseConnection instance
    """
    db_type = getattr(config, 'database_type', 'sqlite')

    if db_type == 'sqlite':
        return DatabaseConnection(
            db_type='sqlite',
            db_path=getattr(config, 'database_path', 'data/gex_data.db')
        )
    else:
        return DatabaseConnection(
            db_type='postgresql',
            host=getattr(config, 'postgres_host', 'localhost'),
            port=getattr(config, 'postgres_port', 5432),
            database=getattr(config, 'postgres_db', 'gexdb'),
            user=getattr(config, 'postgres_user', 'gexuser'),
            password=getattr(config, 'postgres_password', ''),
            pool_size=getattr(config, 'postgres_pool_size', 5),
            max_overflow=getattr(config, 'postgres_max_overflow', 10)
        )
