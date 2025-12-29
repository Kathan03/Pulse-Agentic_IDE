"""
Tier 1 Atomic Tool: Local RAG with Freshness Tracking (Phase 4).

Enhanced RAG engine with:
- ChromaDB for semantic search
- SQLite freshness tracking (prevents stale indexes)
- Incremental embedding updates
- CPU-based sentence-transformers embeddings

Tool: search_workspace
Database: .pulse/chroma_db/ (vector store) + .pulse/history.sqlite (freshness metadata)
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import hashlib
import sqlite3
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    chromadb = None
    Settings = None
    CHROMADB_AVAILABLE = False

from src.core.guardrails import is_path_safe

logger = logging.getLogger(__name__)


# ============================================================================
# RAG MANAGER WITH FRESHNESS TRACKING
# ============================================================================

class RAGManager:
    """
    RAG engine with ChromaDB + SQLite freshness tracking.

    Features:
    - Persistent vector store in .pulse/chroma_db/
    - File hash tracking in .pulse/history.sqlite
    - Incremental updates (only re-index changed files)
    - CPU-based embeddings (sentence-transformers)
    - Bounded output with relevance scoring

    Example:
        >>> rag = RAGManager(project_root=Path("/workspace"))
        >>> rag.index_workspace()
        >>> results = rag.search("timer logic", k=5)
        >>> results[0]["file_path"]
        'src/main.st'
    """

    # Supported file extensions
    SUPPORTED_EXTENSIONS = {".py", ".md", ".txt", ".st", ".scl", ".mat"}

    # Directories to ignore
    IGNORE_DIRS = {".git", "__pycache__", "venv", "node_modules", ".venv", "env", ".pulse"}

    # Chunk size (characters)
    MAX_CHUNK_SIZE = 1500

    def __init__(self, project_root: Path):
        """
        Initialize RAG manager.

        Args:
            project_root: Project root directory (contains .pulse/).

        Raises:
            ImportError: If chromadb is not installed.
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "chromadb not installed. Install with: pip install chromadb"
            )

        self.project_root = Path(project_root).resolve()
        self.pulse_dir = self.project_root / ".pulse"
        self.chroma_dir = self.pulse_dir / "chroma_db"
        self.db_path = self.pulse_dir / "history.sqlite"

        # Ensure directories exist
        self.pulse_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        self.collection = self.client.get_or_create_collection(
            name="pulse_workspace",
            metadata={"description": "Workspace semantic search"}
        )

        # Initialize SQLite freshness tracking
        self._init_freshness_db()

        logger.info(f"RAGManager initialized for: {self.project_root}")

    def _init_freshness_db(self) -> None:
        """Initialize SQLite database for freshness tracking."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_index (
                file_path TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                last_mtime REAL NOT NULL,
                last_indexed_at TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with file_path.open("rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"Could not hash file {file_path}: {e}")
            return ""

    def _is_file_fresh(self, file_path: Path) -> bool:
        """
        Check if file is already indexed and fresh.

        Returns:
            True if file is indexed and unchanged, False if needs re-indexing.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        rel_path = str(file_path.relative_to(self.project_root))

        cursor.execute(
            "SELECT content_hash, last_mtime FROM file_index WHERE file_path = ?",
            (rel_path,)
        )
        result = cursor.fetchone()
        conn.close()

        if not result:
            # Not indexed yet
            return False

        stored_hash, stored_mtime = result

        # Check if file modified
        current_mtime = file_path.stat().st_mtime
        if abs(current_mtime - stored_mtime) > 1:  # 1 second tolerance
            return False

        # Check content hash
        current_hash = self._compute_file_hash(file_path)
        if current_hash != stored_hash:
            return False

        return True

    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed for indexing."""
        # Check extension
        if file_path.suffix not in self.SUPPORTED_EXTENSIONS:
            return False

        # Check if in ignore dirs
        for part in file_path.parts:
            if part in self.IGNORE_DIRS:
                return False

        # Check safety (guardrails)
        if not is_path_safe(file_path, self.project_root, allow_read_only=True):
            return False

        return True

    def _chunk_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Chunk file content for embedding.

        Returns:
            List of chunks with metadata.
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return []

        rel_path = str(file_path.relative_to(self.project_root))
        chunks = []

        if len(content) <= self.MAX_CHUNK_SIZE:
            # Single chunk
            chunks.append({
                "content": content,
                "metadata": {
                    "file_path": rel_path,
                    "chunk_index": 0,
                    "total_chunks": 1,
                }
            })
        else:
            # Split by lines
            lines = content.split('\n')
            current_chunk_lines = []
            current_size = 0
            chunk_index = 0

            for line in lines:
                line_size = len(line) + 1  # +1 for newline

                if current_size + line_size > self.MAX_CHUNK_SIZE and current_chunk_lines:
                    # Save current chunk
                    chunks.append({
                        "content": '\n'.join(current_chunk_lines),
                        "metadata": {
                            "file_path": rel_path,
                            "chunk_index": chunk_index,
                        }
                    })
                    current_chunk_lines = []
                    current_size = 0
                    chunk_index += 1

                current_chunk_lines.append(line)
                current_size += line_size

            # Last chunk
            if current_chunk_lines:
                chunks.append({
                    "content": '\n'.join(current_chunk_lines),
                    "metadata": {
                        "file_path": rel_path,
                        "chunk_index": chunk_index,
                    }
                })

            # Update total_chunks in all chunks
            for chunk in chunks:
                chunk["metadata"]["total_chunks"] = len(chunks)

        return chunks

    def update_file(self, file_path: Path) -> None:
        """
        Incrementally update embeddings for a single file.

        Args:
            file_path: Absolute path to file.

        Behavior:
            - Compute file hash
            - If changed: re-chunk, re-embed, upsert to Chroma
            - Update SQLite freshness record
        """
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return

        if not self._should_process_file(file_path):
            logger.debug(f"Skipping file (unsupported or ignored): {file_path}")
            return

        logger.info(f"Updating RAG index for: {file_path}")

        rel_path = str(file_path.relative_to(self.project_root))

        # Remove old chunks from Chroma
        try:
            # Query for chunks with this file_path
            existing = self.collection.get(where={"file_path": rel_path})
            if existing and existing["ids"]:
                self.collection.delete(ids=existing["ids"])
                logger.debug(f"Removed {len(existing['ids'])} old chunks for {rel_path}")
        except Exception as e:
            logger.warning(f"Could not remove old chunks for {rel_path}: {e}")

        # Chunk file
        chunks = self._chunk_file(file_path)

        if not chunks:
            logger.warning(f"No chunks generated for {rel_path}")
            return

        # Prepare for Chroma
        documents = []
        metadatas = []
        ids = []

        for chunk in chunks:
            chunk_id = f"{rel_path}::{chunk['metadata']['chunk_index']}"
            documents.append(chunk["content"])
            metadatas.append(chunk["metadata"])
            ids.append(chunk_id)

        # Upsert to Chroma
        try:
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.debug(f"Upserted {len(chunks)} chunks for {rel_path}")
        except Exception as e:
            logger.error(f"Chroma upsert failed for {rel_path}: {e}")
            return

        # Update freshness record in SQLite
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        content_hash = self._compute_file_hash(file_path)
        mtime = file_path.stat().st_mtime
        indexed_at = datetime.now().isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO file_index (file_path, content_hash, last_mtime, last_indexed_at, chunk_count)
            VALUES (?, ?, ?, ?, ?)
        """, (rel_path, content_hash, mtime, indexed_at, len(chunks)))

        conn.commit()
        conn.close()

        logger.info(f"RAG index updated for: {rel_path}")

    def remove_file(self, file_path: Path) -> None:
        """
        Remove file from RAG index (after deletion).

        Args:
            file_path: Absolute path to deleted file.
        """
        rel_path = str(file_path.relative_to(self.project_root))

        logger.info(f"Removing from RAG index: {rel_path}")

        # Remove from Chroma
        try:
            existing = self.collection.get(where={"file_path": rel_path})
            if existing and existing["ids"]:
                self.collection.delete(ids=existing["ids"])
                logger.debug(f"Removed {len(existing['ids'])} chunks for {rel_path}")
        except Exception as e:
            logger.warning(f"Could not remove chunks from Chroma for {rel_path}: {e}")

        # Remove from SQLite
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM file_index WHERE file_path = ?", (rel_path,))
        conn.commit()
        conn.close()

        logger.info(f"Removed from RAG index: {rel_path}")

    def index_workspace(self) -> Dict[str, int]:
        """
        Index entire workspace with freshness checks.

        Only re-indexes files that have changed since last index.

        Returns:
            Dict with stats: files_processed, chunks_created, files_skipped.
        """
        logger.info("Starting workspace indexing...")

        files_processed = 0
        chunks_created = 0
        files_skipped = 0

        for file_path in self.project_root.rglob("*"):
            if not file_path.is_file():
                continue

            if not self._should_process_file(file_path):
                continue

            # Check if fresh
            if self._is_file_fresh(file_path):
                files_skipped += 1
                logger.debug(f"Skipping fresh file: {file_path}")
                continue

            # Update file
            try:
                self.update_file(file_path)
                files_processed += 1

                # Count chunks added
                rel_path = str(file_path.relative_to(self.project_root))
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT chunk_count FROM file_index WHERE file_path = ?", (rel_path,))
                result = cursor.fetchone()
                conn.close()
                if result:
                    chunks_created += result[0]

            except Exception as e:
                logger.error(f"Failed to index {file_path}: {e}")

        logger.info(
            f"Workspace indexing complete: {files_processed} processed, "
            f"{files_skipped} skipped (fresh), {chunks_created} chunks"
        )

        return {
            "files_processed": files_processed,
            "chunks_created": chunks_created,
            "files_skipped": files_skipped,
        }


# ============================================================================
# TIER 1 TOOL: search_workspace
# ============================================================================

def search_workspace(
    query: str,
    project_root: Path,
    k: int = 5
) -> List[Dict[str, Any]]:
    """
    Tier 1 tool: Semantic search over workspace files.

    Args:
        query: Search query (natural language or code snippet).
        project_root: Project root directory.
        k: Number of results to return (default: 5).

    Returns:
        List of dicts with keys:
            - file_path: str (relative path)
            - content: str (chunk text)
            - chunk_index: int
            - total_chunks: int
            - distance: Optional[float] (similarity score)

    Example:
        >>> results = search_workspace(
        ...     query="timer logic for conveyor",
        ...     project_root=Path("/workspace"),
        ...     k=3
        ... )
        >>> results[0]["file_path"]
        'src/conveyor.st'
        >>> results[0]["content"][:50]
        'VAR\\n    T_ConveyorDelay : TON;  (* 5s delay *)...'
    """
    logger.info(f"Searching workspace for: {query}")

    try:
        rag = RAGManager(project_root)

        # Ensure index is fresh
        rag.index_workspace()

        # Query ChromaDB
        results = rag.collection.query(
            query_texts=[query],
            n_results=k
        )

        # Format results
        formatted_results = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results.get("distances") else None

                formatted_results.append({
                    "file_path": metadata.get("file_path", "unknown"),
                    "content": doc,
                    "chunk_index": metadata.get("chunk_index", 0),
                    "total_chunks": metadata.get("total_chunks", 1),
                    "distance": distance,
                })

        logger.info(f"Found {len(formatted_results)} results for: {query}")
        return formatted_results

    except Exception as e:
        logger.error(f"Workspace search failed: {e}", exc_info=True)
        return []


__all__ = [
    "RAGManager",
    "search_workspace",
]
