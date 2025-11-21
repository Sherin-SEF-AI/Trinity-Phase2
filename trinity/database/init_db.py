"""
Trinity Phase 2 - Database Initialization
Creates database schema and sets up initial configuration
"""

import os
import sys
from pathlib import Path
from typing import Optional
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from trinity.database.models import Base, Camera
from trinity.core.config import load_config


class DatabaseManager:
    """Database connection and session management"""

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize database manager

        Args:
            config: Configuration dictionary. If None, loads from default config file.
        """
        if config is None:
            config = load_config()

        self.config = config
        self.db_config = config.get('database', {})

        # Build connection string
        self.connection_string = self._build_connection_string()

        # Create engine
        self.engine = create_engine(
            self.connection_string,
            poolclass=QueuePool,
            pool_size=self.db_config.get('postgresql', {}).get('pool_size', 10),
            max_overflow=self.db_config.get('postgresql', {}).get('max_overflow', 20),
            echo=False,  # Set to True for SQL debugging
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info(f"Database initialized: {self._get_safe_connection_string()}")

    def _build_connection_string(self) -> str:
        """Build SQLAlchemy connection string"""
        db_type = self.db_config.get('type', 'sqlite')

        if db_type == 'sqlite':
            db_path = self.db_config.get('sqlite', {}).get('path', 'data/trinity.db')
            # Ensure directory exists
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_path}"

        elif db_type == 'postgresql':
            pg_config = self.db_config.get('postgresql', {})
            host = os.getenv('DB_HOST', pg_config.get('host', 'localhost'))
            port = os.getenv('DB_PORT', pg_config.get('port', 5432))
            database = os.getenv('DB_NAME', pg_config.get('database', 'trinity_av_testing'))
            username = os.getenv('DB_USER', pg_config.get('username', 'trinity_user'))
            password = os.getenv('DB_PASSWORD', pg_config.get('password', ''))

            return f"postgresql://{username}:{password}@{host}:{port}/{database}"

        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    def _get_safe_connection_string(self) -> str:
        """Get connection string with password masked"""
        conn_str = self.connection_string
        if '@' in conn_str:
            # Hide password in logs
            parts = conn_str.split('@')
            if '://' in parts[0]:
                protocol, auth = parts[0].split('://')
                if ':' in auth:
                    user = auth.split(':')[0]
                    return f"{protocol}://{user}:****@{parts[1]}"
        return conn_str

    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(self.engine)
            logger.success("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        try:
            Base.metadata.drop_all(self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            logger.success("Database connection test passed")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def initialize_default_data(self):
        """Initialize database with default configuration data"""
        session = self.get_session()
        try:
            # Check if cameras already exist
            existing_cameras = session.query(Camera).count()
            if existing_cameras > 0:
                logger.info(f"Database already has {existing_cameras} cameras configured")
                return

            # Create default cameras from config
            camera_config = self.config.get('cameras', {})

            for i in range(1, camera_config.get('count', 3) + 1):
                cam_key = f'camera_{i}'
                if cam_key in camera_config:
                    cam_cfg = camera_config[cam_key]

                    camera = Camera(
                        name=cam_cfg.get('name', f'Camera {i}'),
                        device_id=cam_cfg.get('device_id', i - 1),
                        position_x=cam_cfg['position'][0],
                        position_y=cam_cfg['position'][1],
                        position_z=cam_cfg['position'][2],
                        orientation_roll=cam_cfg['orientation'][0],
                        orientation_pitch=cam_cfg['orientation'][1],
                        orientation_yaw=cam_cfg['orientation'][2],
                        resolution_width=cam_cfg['resolution'][0],
                        resolution_height=cam_cfg['resolution'][1],
                        fps=cam_cfg.get('fps', 30),
                        is_active=True
                    )

                    session.add(camera)
                    logger.info(f"Added camera: {camera.name}")

            session.commit()
            logger.success("Default camera configuration created")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to initialize default data: {e}")
            raise
        finally:
            session.close()


def init_database_cli():
    """CLI tool for database initialization"""
    import argparse

    parser = argparse.ArgumentParser(description='Trinity Phase 2 - Database Initialization')
    parser.add_argument('--drop', action='store_true', help='Drop all existing tables before creating')
    parser.add_argument('--no-defaults', action='store_true', help='Skip creating default data')
    parser.add_argument('--test', action='store_true', help='Test database connection only')
    parser.add_argument('--config', type=str, help='Path to configuration file')

    args = parser.parse_args()

    # Load configuration
    if args.config:
        from trinity.core.config import load_config
        config = load_config(args.config)
    else:
        config = None

    # Initialize database manager
    db_manager = DatabaseManager(config)

    if args.test:
        # Test connection only
        if db_manager.test_connection():
            print("✓ Database connection successful")
            sys.exit(0)
        else:
            print("✗ Database connection failed")
            sys.exit(1)

    # Drop tables if requested
    if args.drop:
        confirm = input("Are you sure you want to drop all tables? This cannot be undone! (yes/no): ")
        if confirm.lower() == 'yes':
            db_manager.drop_tables()
        else:
            print("Aborted")
            sys.exit(0)

    # Create tables
    print("Creating database tables...")
    db_manager.create_tables()

    # Initialize default data
    if not args.no_defaults:
        print("Initializing default data...")
        db_manager.initialize_default_data()

    # Test connection
    if db_manager.test_connection():
        print("\n✓ Database initialized successfully!")
    else:
        print("\n✗ Database initialization completed but connection test failed")
        sys.exit(1)


if __name__ == '__main__':
    init_database_cli()
