"""
Tool Belt for Pulse IDE v2.6 (Phase 4).

Implements the 3-tier tool architecture:
- Tier 1 (Atomic): file_ops, patching, search_workspace
- Tier 2 (Permissioned): terminal commands, dependency management
- Tier 3 (Agentic): web_search, CrewAI/AutoGen subsystems

All tools enforce project-root boundaries and approval gates.
"""

from src.tools.file_ops import manage_file_ops
from src.tools.patching import preview_patch, execute_patch
from src.tools.rag import search_workspace, RAGManager
from src.tools.web_search import web_search, format_search_results_for_llm

__all__ = [
    # Tier 1 (Atomic)
    "manage_file_ops",
    "preview_patch",
    "execute_patch",
    "search_workspace",
    "RAGManager",
    # Tier 3 (Agentic)
    "web_search",
    "format_search_results_for_llm",
]
