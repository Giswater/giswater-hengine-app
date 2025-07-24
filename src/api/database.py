"""
Database configuration and models for the Giswater Hydraulic Engine API.
Uses SQLModel with PostgreSQL for storing file metadata.
"""
import os
from typing import Optional
from datetime import datetime
from contextlib import contextmanager
from sqlmodel import SQLModel, Field, create_engine, Session, select, text
from sqlalchemy import desc


WS_SCHEMA = os.getenv("WS_SCHEMA", "ws")
UD_SCHEMA = os.getenv("UD_SCHEMA", "ud")
AUDIT_SCHEMA = os.getenv("AUDIT_SCHEMA", "audit")


class WSSQLModel(SQLModel, table=False):
    __table_args__ = {"schema": WS_SCHEMA}


class UDSQLModel(SQLModel, table=False):
    __table_args__ = {"schema": UD_SCHEMA}


class AuditSQLModel(SQLModel, table=False):
    __table_args__ = {"schema": AUDIT_SCHEMA}


class InpFileDB(WSSQLModel, table=True):
    """SQLModel for storing INP file metadata in database"""
    id: Optional[int] = Field(default=None, primary_key=True)
    file_id: str = Field(unique=True, index=True, description="Unique identifier for the file")
    filename: str = Field(description="Original filename")
    file_path: str = Field(description="Path to the stored file")
    file_size: int = Field(description="Size of the file in bytes")
    upload_time: datetime = Field(default_factory=datetime.now, description="Timestamp when file was uploaded")


# Database configuration from environment variables
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_NAME = os.getenv("DATABASE_NAME", "giswater_hengine")
DATABASE_USER = os.getenv("DATABASE_USER", "postgres")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "postgres")

# Database URL
DATABASE_URL = f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,
    pool_recycle=300
)


def create_db_and_tables():
    """Create database schemas and tables"""
    # Create schemas if they don't exist
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {WS_SCHEMA}"))
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {UD_SCHEMA}"))
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {AUDIT_SCHEMA}"))
        conn.commit()
    
    # Create tables
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    """Get database session context manager"""
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def get_db_session():
    """Dependency function to get database session for FastAPI"""
    with Session(engine) as session:
        yield session


class InpFileRepository:
    """Repository class for INP file database operations"""

    @staticmethod
    def create_file(session: Session, file_data: dict) -> InpFileDB:
        """Create a new file record in database"""
        db_file = InpFileDB(**file_data)
        session.add(db_file)
        session.commit()
        session.refresh(db_file)
        return db_file

    @staticmethod
    def get_file_by_id(session: Session, file_id: str) -> Optional[InpFileDB]:
        """Get file by file_id"""
        statement = select(InpFileDB).where(InpFileDB.file_id == file_id)
        return session.exec(statement).first()

    @staticmethod
    def get_all_files(session: Session) -> list[InpFileDB]:
        """Get all files from database"""
        statement = select(InpFileDB).order_by(desc(InpFileDB.__table__.c.upload_time))
        return list(session.exec(statement).all())

    @staticmethod
    def delete_file(session: Session, file_id: str) -> bool:
        """Delete file record from database"""
        statement = select(InpFileDB).where(InpFileDB.file_id == file_id)
        db_file = session.exec(statement).first()
        if db_file:
            session.delete(db_file)
            session.commit()
            return True
        return False

    @staticmethod
    def file_exists(session: Session, file_id: str) -> bool:
        """Check if file exists in database"""
        statement = select(InpFileDB).where(InpFileDB.file_id == file_id)
        return session.exec(statement).first() is not None
