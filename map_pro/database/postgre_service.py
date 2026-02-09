# Path: database/postgre_service.py
"""
PostgreSQL Service Management

Handles PostgreSQL service operations:
- Status checking (running, initialized)
- Starting/stopping service
- Connection verification

Uses configuration from .env via database/core/config_loader.py.
"""

import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

from database.core.config_loader import ConfigLoader
from database.core.logger import get_logger

logger = get_logger(__name__, 'core')


class PostgreSQLService:
    """Manages PostgreSQL service operations."""

    def __init__(self, config: Optional[ConfigLoader] = None):
        self.config = config if config else ConfigLoader()
        self._pg_data_dir = self.config.get('db_postgresql_data_dir')

    def get_data_directory(self) -> Path:
        """Get PostgreSQL data directory from configuration."""
        return self._pg_data_dir

    def is_directory_exists(self) -> bool:
        """Check if PostgreSQL data directory exists."""
        if not self._pg_data_dir:
            return False
        return self._pg_data_dir.exists()

    def is_directory_initialized(self) -> bool:
        """Check if PostgreSQL data directory is initialized (has PG_VERSION)."""
        if not self._pg_data_dir:
            return False
        pg_version_file = self._pg_data_dir / 'PG_VERSION'
        try:
            return pg_version_file.exists()
        except PermissionError:
            # Directory owned by postgres means initdb was run
            return True

    def is_service_running(self) -> bool:
        """Check if PostgreSQL service is running using systemctl."""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'postgresql'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() == 'active'
        except Exception:
            return False

    def can_connect_as_postgres(self) -> bool:
        """
        Check if PostgreSQL is accepting connections using postgres superuser.

        Use this right after starting the service, before user/database are created.
        """
        try:
            result = subprocess.run(
                ['sudo', '-u', 'postgres', 'psql', '-c', 'SELECT 1;'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def can_connect(self) -> bool:
        """
        Try to connect to PostgreSQL with configured user/database.

        Use this to verify the application user can connect.
        """
        db_user = self.config.get('db_user')
        db_name = self.config.get('db_name')
        db_host = self.config.get('db_host', 'localhost')
        db_port = self.config.get('db_port', 5432)

        try:
            result = subprocess.run(
                ['psql', '-h', str(db_host), '-p', str(db_port),
                 '-U', db_user, '-d', db_name, '-c', 'SELECT 1;'],
                capture_output=True,
                text=True,
                timeout=5,
                env={**subprocess.os.environ, 'PGPASSWORD': self.config.get('db_password', '')}
            )
            return result.returncode == 0
        except Exception:
            return False

    def start(self) -> Dict:
        """Start PostgreSQL service."""
        logger.info("Starting PostgreSQL service...")

        try:
            result = subprocess.run(
                ['sudo', 'systemctl', 'start', 'postgresql'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return {
                    'success': False,
                    'message': f'Failed to start: {result.stderr}'
                }

            # Wait for service to be active
            for _ in range(10):
                if self.is_service_running():
                    logger.info("PostgreSQL service started")
                    return {'success': True, 'message': 'PostgreSQL started'}
                time.sleep(1)

            return {
                'success': False,
                'message': 'Service started but not responding'
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'message': 'Start command timed out'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def stop(self) -> Dict:
        """Stop PostgreSQL service."""
        try:
            result = subprocess.run(
                ['sudo', 'systemctl', 'stop', 'postgresql'],
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                'success': result.returncode == 0,
                'message': 'Stopped' if result.returncode == 0 else result.stderr
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def run_initdb(self) -> Dict:
        """Run initdb to initialize PostgreSQL data directory."""
        if not self._pg_data_dir:
            return {'success': False, 'message': 'Data directory not configured'}

        logger.info(f"Running initdb: {self._pg_data_dir}")

        try:
            # Set ownership
            subprocess.run(
                ['sudo', 'chown', '-R', 'postgres:postgres', str(self._pg_data_dir)],
                capture_output=True, timeout=30
            )

            # Run initdb
            result = subprocess.run(
                ['sudo', '-u', 'postgres', 'initdb',
                 '--locale=C.UTF-8', '--encoding=UTF8',
                 '-D', str(self._pg_data_dir)],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                logger.info("initdb completed")
                # Configure PostgreSQL for TCP/IP connections
                config_result = self._configure_postgresql()
                if not config_result['success']:
                    return config_result
                return {'success': True, 'message': 'initdb completed and configured'}
            else:
                return {'success': False, 'message': result.stderr}

        except subprocess.TimeoutExpired:
            return {'success': False, 'message': 'initdb timed out'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def _configure_postgresql(self) -> Dict:
        """
        Configure PostgreSQL for TCP/IP connections after initdb.

        Updates postgresql.conf:
        - listen_addresses = 'localhost' (enable TCP/IP)
        - password_encryption = 'md5' (must match pg_hba.conf auth method)

        Updates pg_hba.conf:
        - Allow md5 password auth for TCP/IP from localhost

        IMPORTANT: password_encryption must match pg_hba.conf auth method,
        otherwise PostgreSQL crashes when verifying passwords stored with
        different encoding than the auth method expects.
        """
        if not self._pg_data_dir:
            return {'success': False, 'message': 'Data directory not configured'}

        logger.info("Configuring PostgreSQL for TCP/IP connections...")

        postgresql_conf = self._pg_data_dir / 'postgresql.conf'
        pg_hba_conf = self._pg_data_dir / 'pg_hba.conf'

        try:
            # Update postgresql.conf
            result = subprocess.run(
                ['sudo', '-u', 'postgres', 'test', '-f', str(postgresql_conf)],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                # Read current config
                result = subprocess.run(
                    ['sudo', '-u', 'postgres', 'cat', str(postgresql_conf)],
                    capture_output=True, text=True, timeout=10
                )
                content = result.stdout

                # Settings to add to postgresql.conf
                settings_to_add = []

                # 1. Enable TCP/IP listening on localhost
                if "listen_addresses = 'localhost'" not in content:
                    settings_to_add.append("listen_addresses = 'localhost'")

                # 2. Set password_encryption to md5 (MUST match pg_hba.conf auth method)
                # This ensures passwords created via CREATE USER are stored with md5 hash,
                # which is required for md5 authentication in pg_hba.conf to work
                if "password_encryption = 'md5'" not in content:
                    settings_to_add.append("password_encryption = 'md5'")

                # Append all settings
                if settings_to_add:
                    settings_block = (
                        "\\n# Map Pro TCP/IP Configuration\\n" +
                        "\\n".join(settings_to_add)
                    )
                    subprocess.run(
                        ['sudo', '-u', 'postgres', 'sh', '-c',
                         f'echo -e "{settings_block}" >> {postgresql_conf}'],
                        capture_output=True, timeout=10
                    )
                    logger.info(f"Added to postgresql.conf: {settings_to_add}")

            # Update pg_hba.conf to allow TCP/IP connections from localhost
            result = subprocess.run(
                ['sudo', '-u', 'postgres', 'test', '-f', str(pg_hba_conf)],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                result = subprocess.run(
                    ['sudo', '-u', 'postgres', 'cat', str(pg_hba_conf)],
                    capture_output=True, text=True, timeout=10
                )
                content = result.stdout

                # Check if TCP/IP auth for localhost is configured
                if 'host    all             all             127.0.0.1/32' not in content:
                    # Add TCP/IP auth lines for IPv4 and IPv6 localhost
                    # Use md5 - must match password_encryption setting above
                    auth_lines = (
                        "\\n# TCP/IP connections from localhost (added by map_pro)\\n"
                        "host    all             all             127.0.0.1/32            md5\\n"
                        "host    all             all             ::1/128                 md5"
                    )
                    subprocess.run(
                        ['sudo', '-u', 'postgres', 'sh', '-c',
                         f'echo -e "{auth_lines}" >> {pg_hba_conf}'],
                        capture_output=True, timeout=10
                    )
                    logger.info("Added TCP/IP auth rules to pg_hba.conf (md5)")

            return {'success': True, 'message': 'PostgreSQL configured for TCP/IP'}

        except Exception as e:
            logger.error(f"Failed to configure PostgreSQL: {e}")
            return {'success': False, 'message': f'Configuration failed: {e}'}
