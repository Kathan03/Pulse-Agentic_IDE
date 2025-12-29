"""
Workspace Initialization for Pulse IDE v2.6.

Manages workspace-local state directory (.pulse/) with SQLite DB, Chroma vector store,
and optional bounded logs. All workspace state is stored locally within the project root.
"""

import sqlite3
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """
    Manages workspace-local state directory (.pulse/) initialization and lifecycle.

    Directory Structure:
        workspace/
        ├── .pulse/
        │   ├── history.sqlite      # Session state DB
        │   ├── chroma_db/          # Vector store for RAG
        │   └── logs/               # Bounded log files (optional)
        ├── .gitignore              # Auto-updated to include .pulse/
        └── <user PLC code files>
    """

    PULSE_DIR_NAME = ".pulse"
    HISTORY_DB_NAME = "history.sqlite"
    CHROMA_DIR_NAME = "chroma_db"
    LOGS_DIR_NAME = "logs"

    def __init__(self, project_root: Path):
        """
        Initialize WorkspaceManager for a given project root.

        Args:
            project_root: Absolute path to workspace root directory.

        Raises:
            ValueError: If project_root doesn't exist or is not a directory.
        """
        self.project_root = Path(project_root).resolve()

        if not self.project_root.exists():
            raise ValueError(f"Project root does not exist: {self.project_root}")
        if not self.project_root.is_dir():
            raise ValueError(f"Project root is not a directory: {self.project_root}")

        self.pulse_dir = self.project_root / self.PULSE_DIR_NAME
        self.history_db_path = self.pulse_dir / self.HISTORY_DB_NAME
        self.chroma_dir = self.pulse_dir / self.CHROMA_DIR_NAME
        self.logs_dir = self.pulse_dir / self.LOGS_DIR_NAME

    def ensure_workspace_initialized(self) -> None:
        """
        Initialize workspace-local state directory if not exists.

        Creates:
        - .pulse/ directory
        - .pulse/history.sqlite (with minimal bootstrap schema)
        - .pulse/chroma_db/ directory
        - .pulse/logs/ directory (optional)
        - Updates .gitignore to exclude .pulse/

        This is idempotent - safe to call multiple times.
        """
        logger.info(f"Initializing workspace: {self.project_root}")

        # Step 1: Create .pulse/ directory
        self.pulse_dir.mkdir(exist_ok=True)
        logger.debug(f"Created {self.PULSE_DIR_NAME} directory")

        # Step 2: Initialize SQLite DB (minimal schema)
        self._initialize_sqlite_db()

        # Step 3: Create chroma_db/ directory
        self.chroma_dir.mkdir(exist_ok=True)
        logger.debug(f"Created {self.CHROMA_DIR_NAME} directory")

        # Step 4: Create logs/ directory (optional, bounded)
        self.logs_dir.mkdir(exist_ok=True)
        logger.debug(f"Created {self.LOGS_DIR_NAME} directory")

        # Step 5: Update .gitignore
        self._update_gitignore()

        logger.info("Workspace initialization complete")

    def _initialize_sqlite_db(self) -> None:
        """
        Initialize SQLite database with minimal bootstrap schema.

        Phase 2 scope: Create file + minimal schema placeholder.
        Full schema migrations will be handled in later phases.
        """
        if self.history_db_path.exists():
            logger.debug(f"SQLite DB already exists: {self.history_db_path}")
            return

        logger.info(f"Creating SQLite DB: {self.history_db_path}")

        # Create database file and minimal schema
        conn = sqlite3.connect(str(self.history_db_path))
        cursor = conn.cursor()

        # Minimal bootstrap schema (Phase 2 placeholder)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert workspace version marker
        cursor.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("schema_version", "2.6.0")
        )

        conn.commit()
        conn.close()

        logger.info("SQLite DB initialized with bootstrap schema")

    def _update_gitignore(self) -> None:
        """
        Add .pulse/ to .gitignore if git repo detected and entry missing.

        This prevents workspace-local state from being committed to version control.
        """
        gitignore_path = self.project_root / ".gitignore"
        pulse_ignore_entry = f"/{self.PULSE_DIR_NAME}/"

        # Check if .git directory exists (indicates git repo)
        if not (self.project_root / ".git").exists():
            logger.debug("Not a git repository, skipping .gitignore update")
            return

        # Read existing .gitignore or create empty
        if gitignore_path.exists():
            existing_content = gitignore_path.read_text(encoding="utf-8")
        else:
            existing_content = ""

        # Check if .pulse/ already ignored
        if pulse_ignore_entry in existing_content or f"{self.PULSE_DIR_NAME}/" in existing_content:
            logger.debug(".pulse/ already in .gitignore")
            return

        # Append .pulse/ entry
        logger.info("Adding .pulse/ to .gitignore")
        with gitignore_path.open("a", encoding="utf-8") as f:
            if existing_content and not existing_content.endswith("\n"):
                f.write("\n")
            f.write(f"\n# Pulse IDE workspace-local state (generated)\n")
            f.write(f"{pulse_ignore_entry}\n")

        logger.info(".gitignore updated")

    def is_initialized(self) -> bool:
        """
        Check if workspace is already initialized.

        Returns:
            True if .pulse/ directory and core files exist.
        """
        return (
            self.pulse_dir.exists()
            and self.history_db_path.exists()
            and self.chroma_dir.exists()
        )


def ensure_workspace_initialized(project_root: str) -> WorkspaceManager:
    """
    Convenience function to initialize workspace and return manager.

    Args:
        project_root: Absolute path to workspace root directory.

    Returns:
        WorkspaceManager instance with initialized workspace.

    Example:
        >>> workspace_mgr = ensure_workspace_initialized("/path/to/project")
        >>> # .pulse/ directory now exists with DB and folders
    """
    manager = WorkspaceManager(Path(project_root))
    manager.ensure_workspace_initialized()
    return manager


__all__ = ["WorkspaceManager", "ensure_workspace_initialized"]
