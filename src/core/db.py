"""
Conversation Persistence for Pulse IDE v2.6 (Task F1).

Uses SQLite to store conversation history for:
- Resuming conversations across sessions
- Exporting chat history
- Analytics and debugging

Database is stored in the project's .pulse/ directory.
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    project_root TEXT NOT NULL,
    title TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_calls TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
ON messages(conversation_id);

CREATE INDEX IF NOT EXISTS idx_conversations_project_root
ON conversations(project_root);
"""


# ============================================================================
# DATABASE CONNECTION MANAGER
# ============================================================================

class ConversationDB:
    """
    SQLite database manager for conversation persistence.

    Database is stored in {project_root}/.pulse/conversations.db
    """

    DB_FILENAME = "conversations.db"

    def __init__(self, project_root: str):
        """
        Initialize database connection for a project.

        Args:
            project_root: Absolute path to the project root directory.
        """
        self.project_root = Path(project_root).resolve()
        self.pulse_dir = self.project_root / ".pulse"
        self.db_path = self.pulse_dir / self.DB_FILENAME

        # Ensure .pulse directory exists
        self.pulse_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

        logger.info(f"ConversationDB initialized: {self.db_path}")

    def _init_db(self) -> None:
        """Create database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(SCHEMA_SQL)
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn


# ============================================================================
# CONVERSATION MANAGEMENT
# ============================================================================

    def create_conversation(self, title: Optional[str] = None) -> str:
        """
        Create a new conversation.

        Args:
            title: Optional title for the conversation.

        Returns:
            Conversation ID (UUID string).
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO conversations (id, created_at, updated_at, project_root, title)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (conversation_id, now, now, str(self.project_root), title)
                )
                conn.commit()

            logger.info(f"Created conversation: {conversation_id}")
            return conversation_id

        except sqlite3.Error as e:
            logger.error(f"Failed to create conversation: {e}")
            raise

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation by ID.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            Conversation dict or None if not found.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM conversations WHERE id = ?",
                    (conversation_id,)
                )
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None

        except sqlite3.Error as e:
            logger.error(f"Failed to get conversation: {e}")
            return None

    def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent conversations for this project.

        Args:
            limit: Maximum number of conversations to return.

        Returns:
            List of conversation dicts, most recent first.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM conversations
                    WHERE project_root = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (str(self.project_root), limit)
                )
                return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Failed to get recent conversations: {e}")
            return []

    def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """
        Update conversation title.

        Args:
            conversation_id: Conversation UUID.
            title: New title.

        Returns:
            True if update succeeded.
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE conversations
                    SET title = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (title, datetime.now().isoformat(), conversation_id)
                )
                conn.commit()
            return True

        except sqlite3.Error as e:
            logger.error(f"Failed to update conversation title: {e}")
            return False

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its messages.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            True if deletion succeeded.
        """
        try:
            with self._get_connection() as conn:
                # Delete messages first (foreign key)
                conn.execute(
                    "DELETE FROM messages WHERE conversation_id = ?",
                    (conversation_id,)
                )
                # Delete conversation
                conn.execute(
                    "DELETE FROM conversations WHERE id = ?",
                    (conversation_id,)
                )
                conn.commit()

            logger.info(f"Deleted conversation: {conversation_id}")
            return True

        except sqlite3.Error as e:
            logger.error(f"Failed to delete conversation: {e}")
            return False


# ============================================================================
# MESSAGE MANAGEMENT
# ============================================================================

    def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[int]:
        """
        Save a message to a conversation.

        Args:
            conversation_id: Conversation UUID.
            role: Message role ("user", "assistant", or "tool").
            content: Message content.
            tool_calls: Optional list of tool call dicts.

        Returns:
            Message ID (integer) or None if save failed.
        """
        try:
            tool_calls_json = json.dumps(tool_calls) if tool_calls else None
            now = datetime.now().isoformat()

            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO messages (conversation_id, role, content, tool_calls, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (conversation_id, role, content, tool_calls_json, now)
                )
                message_id = cursor.lastrowid

                # Update conversation's updated_at timestamp
                conn.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?",
                    (now, conversation_id)
                )
                conn.commit()

            logger.debug(f"Saved message {message_id} to conversation {conversation_id}")
            return message_id

        except sqlite3.Error as e:
            logger.error(f"Failed to save message: {e}")
            return None

    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation.

        Args:
            conversation_id: Conversation UUID.
            limit: Maximum number of messages to return (None = all).
            offset: Number of messages to skip.

        Returns:
            List of message dicts, ordered by creation time.
        """
        try:
            with self._get_connection() as conn:
                if limit is not None:
                    cursor = conn.execute(
                        """
                        SELECT * FROM messages
                        WHERE conversation_id = ?
                        ORDER BY created_at ASC
                        LIMIT ? OFFSET ?
                        """,
                        (conversation_id, limit, offset)
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM messages
                        WHERE conversation_id = ?
                        ORDER BY created_at ASC
                        """,
                        (conversation_id,)
                    )

                messages = []
                for row in cursor.fetchall():
                    msg = dict(row)
                    # Parse tool_calls JSON
                    if msg.get("tool_calls"):
                        msg["tool_calls"] = json.loads(msg["tool_calls"])
                    messages.append(msg)

                return messages

        except sqlite3.Error as e:
            logger.error(f"Failed to get messages: {e}")
            return []

    def get_message_count(self, conversation_id: str) -> int:
        """
        Get total message count for a conversation.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            Number of messages.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
                    (conversation_id,)
                )
                return cursor.fetchone()[0]

        except sqlite3.Error as e:
            logger.error(f"Failed to get message count: {e}")
            return 0


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

    def export_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a conversation with all messages as a dict.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            Dict with conversation metadata and messages, or None if not found.
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        messages = self.get_messages(conversation_id)

        return {
            "conversation": conversation,
            "messages": messages,
            "exported_at": datetime.now().isoformat()
        }

    def export_conversation_as_markdown(self, conversation_id: str) -> Optional[str]:
        """
        Export a conversation as markdown text.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            Markdown formatted string, or None if not found.
        """
        data = self.export_conversation(conversation_id)
        if not data:
            return None

        conv = data["conversation"]
        messages = data["messages"]

        lines = [
            f"# {conv.get('title') or 'Conversation'}",
            "",
            f"**Created:** {conv.get('created_at')}",
            f"**Project:** {conv.get('project_root')}",
            "",
            "---",
            ""
        ]

        for msg in messages:
            role = msg.get("role", "unknown").title()
            content = msg.get("content", "")
            timestamp = msg.get("created_at", "")

            lines.append(f"## {role}")
            if timestamp:
                lines.append(f"*{timestamp}*")
            lines.append("")
            lines.append(content)
            lines.append("")

            # Include tool calls if present
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                lines.append("**Tool Calls:**")
                lines.append("```json")
                lines.append(json.dumps(tool_calls, indent=2))
                lines.append("```")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_or_resume_conversation(
    project_root: str,
    conversation_id: Optional[str] = None,
    title: Optional[str] = None
) -> tuple[ConversationDB, str]:
    """
    Create a new conversation or resume an existing one.

    Args:
        project_root: Absolute path to project root.
        conversation_id: Optional existing conversation ID to resume.
        title: Optional title for new conversation.

    Returns:
        Tuple of (ConversationDB instance, conversation_id).
    """
    db = ConversationDB(project_root)

    if conversation_id:
        # Verify conversation exists
        existing = db.get_conversation(conversation_id)
        if existing:
            logger.info(f"Resuming conversation: {conversation_id}")
            return db, conversation_id
        else:
            logger.warning(f"Conversation {conversation_id} not found, creating new")

    # Create new conversation
    new_id = db.create_conversation(title=title)
    return db, new_id


def generate_conversation_title(first_message: str, max_length: int = 50) -> str:
    """
    Generate a title from the first message.

    Args:
        first_message: User's first message.
        max_length: Maximum title length.

    Returns:
        Generated title string.
    """
    # Clean and truncate
    title = first_message.strip()
    title = " ".join(title.split())  # Normalize whitespace

    if len(title) > max_length:
        title = title[:max_length - 3] + "..."

    return title


__all__ = [
    "ConversationDB",
    "create_or_resume_conversation",
    "generate_conversation_title",
]
