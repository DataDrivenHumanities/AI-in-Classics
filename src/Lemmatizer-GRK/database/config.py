"""
Database Configuration

Manages PostgreSQL connection settings and session creation.
Supports both environment variables and direct configuration.
"""

import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine


def get_database_url(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    """
    Construct PostgreSQL connection URL.
    
    Priority:
    1. Function parameters
    2. Environment variables
    3. Default values
    
    Environment variables:
    - POSTGRES_HOST (default: localhost)
    - POSTGRES_PORT (default: 5432)
    - POSTGRES_DB (default: greek_dictionary)
    - POSTGRES_USER (default: postgres)
    - POSTGRES_PASSWORD (default: empty)
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        user: Database user
        password: Database password
        
    Returns:
        PostgreSQL connection URL
    """
    host = host or os.getenv('POSTGRES_HOST', 'localhost')
    port = port or int(os.getenv('POSTGRES_PORT', '5432'))
    database = database or os.getenv('POSTGRES_DB', 'greek_dictionary')
    user = user or os.getenv('POSTGRES_USER', 'postgres')
    password = password or os.getenv('POSTGRES_PASSWORD', '')
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def get_engine(
    database_url: Optional[str] = None,
    echo: bool = False,
    **kwargs
) -> Engine:
    """
    Create SQLAlchemy engine.
    
    Args:
        database_url: PostgreSQL connection URL (if None, uses get_database_url())
        echo: Whether to log SQL statements
        **kwargs: Additional engine configuration options
        
    Returns:
        SQLAlchemy Engine instance
    """
    if database_url is None:
        database_url = get_database_url()
    
    return create_engine(
        database_url,
        echo=echo,
        pool_size=10,
        max_overflow=20,
        **kwargs
    )


def get_session(engine: Optional[Engine] = None) -> Session:
    """
    Create database session.
    
    Args:
        engine: SQLAlchemy engine (if None, creates new engine)
        
    Returns:
        SQLAlchemy Session instance
    """
    if engine is None:
        engine = get_engine()
    
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()
