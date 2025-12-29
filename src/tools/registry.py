"""
Tool Registry for Pulse IDE v2.6 (Phase 4).

Provides tool registration and execution for the Master Graph.
Maps tool names to functions and handles structured invocation.

Architecture:
- Tools are registered with metadata (name, description, parameters)
- Master Graph requests tools by name
- Registry validates arguments and invokes tools
- Results returned as ToolOutput models

Safety:
- All tools receive project_root for boundary enforcement
- RAG manager injected for freshness updates
- Structured error handling with ToolOutput format
"""

from typing import Dict, Any, Callable, Optional, List
from pathlib import Path
import logging
from datetime import datetime

from src.agents.state import ToolOutput
from src.tools.file_ops import manage_file_ops
from src.tools.patching import preview_patch, execute_patch
from src.tools.rag import search_workspace, RAGManager

logger = logging.getLogger(__name__)


# ============================================================================
# TOOL METADATA
# ============================================================================

class ToolDefinition:
    """
    Tool metadata for registration.

    Attributes:
        name: Tool name (unique identifier).
        description: Human-readable description.
        function: Callable to invoke.
        requires_approval: Whether tool requires human approval.
        parameters: List of required parameter names.
    """

    def __init__(
        self,
        name: str,
        description: str,
        function: Callable,
        requires_approval: bool = False,
        parameters: Optional[List[str]] = None
    ):
        self.name = name
        self.description = description
        self.function = function
        self.requires_approval = requires_approval
        self.parameters = parameters or []


# ============================================================================
# TOOL REGISTRY
# ============================================================================

class ToolRegistry:
    """
    Centralized tool registry for Master Graph.

    Manages tool registration, validation, and invocation.

    Example:
        >>> registry = ToolRegistry(project_root=Path("/workspace"))
        >>> registry.register_tier1_tools()
        >>> result = registry.invoke_tool("search_workspace", {"query": "timer logic"})
        >>> result.success
        True
    """

    def __init__(self, project_root: Path):
        """
        Initialize tool registry.

        Args:
            project_root: Project root directory (passed to all tools).
        """
        self.project_root = Path(project_root).resolve()
        self.tools: Dict[str, ToolDefinition] = {}
        self.rag_manager: Optional[RAGManager] = None

        logger.info(f"ToolRegistry initialized for: {self.project_root}")

    def register_tool(self, tool: ToolDefinition) -> None:
        """
        Register a tool.

        Args:
            tool: ToolDefinition to register.

        Raises:
            ValueError: If tool name already registered.
        """
        if tool.name in self.tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def register_tier1_tools(self) -> None:
        """
        Register all Tier 1 (Atomic) tools.

        Tier 1 tools:
        - manage_file_ops (read, write, delete, list)
        - apply_patch (preview → approval → execute)
        - search_workspace (semantic search via RAG)
        """
        # File operations
        self.register_tool(ToolDefinition(
            name="manage_file_ops",
            description="Create, read, update, delete, or list files (project-root restricted)",
            function=self._wrap_file_ops,
            requires_approval=False,  # Individual operations validated separately
            parameters=["operation", "path"],
        ))

        # Patch workflow (preview only - execution happens after approval)
        self.register_tool(ToolDefinition(
            name="apply_patch",
            description="Preview unified diff patch (requires approval before execution)",
            function=self._wrap_patch_preview,
            requires_approval=True,  # Pause graph for approval
            parameters=["diff"],
        ))

        # Workspace search
        self.register_tool(ToolDefinition(
            name="search_workspace",
            description="Semantic search over workspace files via RAG",
            function=self._wrap_search_workspace,
            requires_approval=False,
            parameters=["query"],
        ))

        logger.info("Registered Tier 1 tools")

    def register_tier2_tools(self) -> None:
        """
        Register all Tier 2 (Permissioned) tools.

        Tier 2 tools:
        - plan_terminal_cmd (generate CommandPlan for approval)
        - run_terminal_cmd (execute approved CommandPlan)
        - dependency_manager (detect tooling and propose installs)
        """
        # Terminal command planning (no approval - just creates plan)
        self.register_tool(ToolDefinition(
            name="plan_terminal_cmd",
            description="Generate terminal command plan with risk assessment (requires approval before execution)",
            function=self._wrap_plan_terminal_cmd,
            requires_approval=False,  # Planning doesn't need approval
            parameters=["command", "rationale"],
        ))

        # Terminal command execution (approval handled by master_graph)
        self.register_tool(ToolDefinition(
            name="run_terminal_cmd",
            description="Execute approved terminal command with timeout and output capture",
            function=self._wrap_run_terminal_cmd,
            requires_approval=True,  # Pause graph for approval
            parameters=["plan"],
        ))

        # Dependency manager (detection + proposals, no execution)
        self.register_tool(ToolDefinition(
            name="dependency_manager",
            description="Detect project dependencies and propose safe install commands",
            function=self._wrap_dependency_manager,
            requires_approval=False,  # Only detects and proposes, doesn't execute
            parameters=[],
        ))

        logger.info("Registered Tier 2 tools")

    def register_tier3_tools(self) -> None:
        """
        Register all Tier 3 (Agentic) tools.

        Tier 3 tools:
        - web_search (DuckDuckGo search for documentation and technical resources)
        - implement_feature (CrewAI: Planner → Coder → Reviewer)
        - diagnose_project (Deterministic + optional AutoGen debate)

        Context Containment:
        - CrewAI/AutoGen transcripts are NEVER returned to Master
        - Only structured outputs (PatchPlan, DiagnosisResult) are returned
        - Execution is offloaded to background threads (asyncio.to_thread)

        Toggle Controls:
        - Tools respect enable_crew and enable_autogen settings
        - Disabled tools return no-op responses with no spend
        """
        # Web search via DuckDuckGo
        self.register_tool(ToolDefinition(
            name="web_search",
            description="Search the web for documentation, Stack Overflow answers, and technical resources using DuckDuckGo",
            function=self._wrap_web_search,
            requires_approval=False,  # Web search is safe, no side effects
            parameters=["query"],
        ))

        # Feature implementation via CrewAI
        self.register_tool(ToolDefinition(
            name="implement_feature",
            description="Implement complex features via CrewAI (Planner → Coder → Reviewer). Offloaded to background thread.",
            function=self._wrap_implement_feature,
            requires_approval=False,  # Returns PatchPlan for separate approval flow
            parameters=["request"],
        ))

        # Project diagnostics via AutoGen
        self.register_tool(ToolDefinition(
            name="diagnose_project",
            description="Diagnose project health via deterministic checks + optional AutoGen debate. Offloaded to background thread.",
            function=self._wrap_diagnose_project,
            requires_approval=False,  # Returns structured JSON, no side effects
            parameters=[],  # All parameters optional
        ))

        logger.info("Registered Tier 3 tools")

    def invoke_tool(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> ToolOutput:
        """
        Invoke a registered tool.

        Args:
            tool_name: Name of tool to invoke.
            args: Tool arguments (validated against tool.parameters).

        Returns:
            ToolOutput with success/error status and result.

        Example:
            >>> result = registry.invoke_tool(
            ...     tool_name="search_workspace",
            ...     args={"query": "timer logic", "k": 5}
            ... )
            >>> result.success
            True
            >>> result.result  # List of search results
            [{'file_path': 'main.st', 'content': '...', ...}]
        """
        logger.info(f"Invoking tool: {tool_name} with args: {args}")

        try:
            # Validate tool exists
            if tool_name not in self.tools:
                return ToolOutput(
                    tool_name=tool_name,
                    success=False,
                    result="",
                    error=f"Tool not found: {tool_name}",
                    timestamp=datetime.now().isoformat()
                )

            tool = self.tools[tool_name]

            # Validate required parameters
            missing_params = [p for p in tool.parameters if p not in args]
            if missing_params:
                return ToolOutput(
                    tool_name=tool_name,
                    success=False,
                    result="",
                    error=f"Missing required parameters: {missing_params}",
                    timestamp=datetime.now().isoformat()
                )

            # Invoke tool function
            result = tool.function(args)

            # Wrap result in ToolOutput if not already
            if isinstance(result, ToolOutput):
                return result
            else:
                return ToolOutput(
                    tool_name=tool_name,
                    success=True,
                    result=result,
                    error=None,
                    timestamp=datetime.now().isoformat()
                )

        except Exception as e:
            logger.error(f"Tool invocation failed: {tool_name} - {e}", exc_info=True)
            return ToolOutput(
                tool_name=tool_name,
                success=False,
                result="",
                error=str(e),
                timestamp=datetime.now().isoformat()
            )

    def get_rag_manager(self) -> RAGManager:
        """
        Get or create RAG manager singleton.

        Returns:
            RAGManager instance for this project_root.
        """
        if self.rag_manager is None:
            self.rag_manager = RAGManager(self.project_root)
        return self.rag_manager

    # ========================================================================
    # TOOL WRAPPERS (adapt tool functions to registry interface)
    # ========================================================================

    def _wrap_file_ops(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrapper for manage_file_ops tool.

        Args:
            args: Dict with keys: operation, path, content (optional)

        Returns:
            Dict result from manage_file_ops.
        """
        return manage_file_ops(
            operation=args["operation"],
            path=args["path"],
            project_root=self.project_root,
            content=args.get("content"),
            rag_manager=self.get_rag_manager()
        )

    def _wrap_patch_preview(self, args: Dict[str, Any]) -> Any:
        """
        Wrapper for patch preview (apply_patch tool).

        This returns a PatchPlan for approval.
        Actual execution happens via execute_patch_approved().

        Args:
            args: Dict with key: diff

        Returns:
            PatchPlan model (for approval flow).
        """
        patch_plan = preview_patch(
            diff=args["diff"],
            project_root=self.project_root
        )
        return patch_plan  # Returns PatchPlan, not ToolOutput

    def _wrap_search_workspace(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Wrapper for search_workspace tool.

        Args:
            args: Dict with keys: query, k (optional)

        Returns:
            List of search results.
        """
        return search_workspace(
            query=args["query"],
            project_root=self.project_root,
            k=args.get("k", 5)
        )

    # ========================================================================
    # TIER 2 TOOL WRAPPERS
    # ========================================================================

    def _wrap_plan_terminal_cmd(self, args: Dict[str, Any]) -> Any:
        """
        Wrapper for plan_terminal_cmd tool.

        Args:
            args: Dict with keys: command, rationale

        Returns:
            CommandPlan model (for approval flow).
        """
        from src.tools.terminal import plan_terminal_cmd

        command_plan = plan_terminal_cmd(
            command=args["command"],
            rationale=args["rationale"],
            project_root=self.project_root,
        )
        return command_plan  # Returns CommandPlan, not ToolOutput

    def _wrap_run_terminal_cmd(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrapper for run_terminal_cmd tool.

        Args:
            args: Dict with key: plan (CommandPlan as dict)

        Returns:
            Dict result from run_terminal_cmd.
        """
        from src.tools.terminal import run_terminal_cmd
        from src.agents.state import CommandPlan

        # Reconstruct CommandPlan from dict
        if isinstance(args["plan"], CommandPlan):
            plan = args["plan"]
        else:
            plan = CommandPlan(**args["plan"])

        return run_terminal_cmd(
            plan=plan,
            project_root=self.project_root,
        )

    def _wrap_dependency_manager(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrapper for dependency_manager tool.

        Args:
            args: Dict (no args required)

        Returns:
            Dict result from dependency_manager.
        """
        from src.tools.deps import dependency_manager

        return dependency_manager(project_root=self.project_root)

    # ========================================================================
    # TIER 3 TOOL WRAPPERS
    # ========================================================================

    def _wrap_web_search(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Wrapper for web_search tool (DuckDuckGo).

        Args:
            args: Dict with keys: query, num_results (optional)

        Returns:
            List of search result dicts.
        """
        from src.tools.web_search import web_search

        return web_search(
            query=args["query"],
            num_results=args.get("num_results", 5)
        )

    def _wrap_implement_feature(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrapper for implement_feature tool (CrewAI).

        This is an async tool that must be awaited by the caller.
        The actual execution is offloaded to a background thread via asyncio.to_thread.

        Args:
            args: Dict with keys: request, context (optional)

        Returns:
            Dict with patch_plans, summary, verification_steps, metadata.
        """
        from src.tools.builder_crew import implement_feature
        import asyncio

        # implement_feature is async, so we need to run it in the event loop
        # If called from async context, return coroutine directly
        # If called from sync context, run in new event loop
        try:
            loop = asyncio.get_running_loop()
            # Running in async context, return awaitable
            return implement_feature(
                request=args["request"],
                project_root=self.project_root,
                context=args.get("context")
            )
        except RuntimeError:
            # No running loop, create new one (sync context)
            return asyncio.run(implement_feature(
                request=args["request"],
                project_root=self.project_root,
                context=args.get("context")
            ))

    def _wrap_diagnose_project(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrapper for diagnose_project tool (AutoGen).

        This is an async tool that must be awaited by the caller.
        The actual execution is offloaded to a background thread via asyncio.to_thread.

        Args:
            args: Dict with keys: focus_area (optional), context (optional)

        Returns:
            Dict with risk_level, findings, prioritized_fixes, verification_steps, metadata.
        """
        from src.tools.auditor_swarm import diagnose_project
        import asyncio

        # diagnose_project is async, so we need to run it in the event loop
        try:
            loop = asyncio.get_running_loop()
            # Running in async context, return awaitable
            return diagnose_project(
                focus_area=args.get("focus_area"),
                project_root=self.project_root,
                context=args.get("context")
            )
        except RuntimeError:
            # No running loop, create new one (sync context)
            return asyncio.run(diagnose_project(
                focus_area=args.get("focus_area"),
                project_root=self.project_root,
                context=args.get("context")
            ))

    def execute_patch_approved(self, patch_plan: Any) -> ToolOutput:
        """
        Execute an approved patch.

        This is called by Master Graph after user approval.

        Args:
            patch_plan: PatchPlan model from preview_patch.

        Returns:
            ToolOutput with execution result.
        """
        try:
            result = execute_patch(
                plan=patch_plan,
                project_root=self.project_root,
                rag_manager=self.get_rag_manager()
            )

            return ToolOutput(
                tool_name="apply_patch",
                success=result["status"] == "success",
                result=result,
                error=result.get("error"),
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Patch execution failed: {e}", exc_info=True)
            return ToolOutput(
                tool_name="apply_patch",
                success=False,
                result="",
                error=str(e),
                timestamp=datetime.now().isoformat()
            )

    def execute_terminal_cmd_approved(self, command_plan: Any) -> ToolOutput:
        """
        Execute an approved terminal command.

        This is called by Master Graph after user approval.

        Args:
            command_plan: CommandPlan model from plan_terminal_cmd.

        Returns:
            ToolOutput with execution result.
        """
        try:
            from src.tools.terminal import run_terminal_cmd
            from src.agents.state import CommandPlan

            # Ensure we have a CommandPlan instance
            if not isinstance(command_plan, CommandPlan):
                command_plan = CommandPlan(**command_plan)

            result = run_terminal_cmd(
                plan=command_plan,
                project_root=self.project_root,
            )

            return ToolOutput(
                tool_name="run_terminal_cmd",
                success=result.get("exit_code", -1) == 0 and not result.get("timed_out", False),
                result=result,
                error=result.get("stderr") if result.get("exit_code", -1) != 0 else None,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Terminal command execution failed: {e}", exc_info=True)
            return ToolOutput(
                tool_name="run_terminal_cmd",
                success=False,
                result="",
                error=str(e),
                timestamp=datetime.now().isoformat()
            )

    # ========================================================================
    # INTROSPECTION
    # ========================================================================

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all registered tools with metadata.

        Returns:
            List of dicts with tool metadata.

        Example:
            >>> tools = registry.list_tools()
            >>> tools[0]
            {
                'name': 'manage_file_ops',
                'description': '...',
                'requires_approval': False,
                'parameters': ['operation', 'path']
            }
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "requires_approval": tool.requires_approval,
                "parameters": tool.parameters,
            }
            for tool in self.tools.values()
        ]

    def get_tool_schemas(self, mode: str = "agent") -> List[Dict[str, Any]]:
        """
        Get OpenAI-format tool schemas for function calling.

        Filters tools based on mode:
        - "agent": All tools (default)
        - "ask": Read-only tools (search_workspace, manage_file_ops read, web_search)
        - "plan": Planning tools (search_workspace, manage_file_ops read)

        Args:
            mode: Operational mode ("agent", "ask", or "plan").

        Returns:
            List of OpenAI function calling schemas.

        Example:
            >>> schemas = registry.get_tool_schemas(mode="agent")
            >>> schemas[0]
            {
                "type": "function",
                "function": {
                    "name": "manage_file_ops",
                    "description": "...",
                    "parameters": {...}
                }
            }
        """
        # Define tool schemas in OpenAI format
        all_schemas = {
            "manage_file_ops": {
                "type": "function",
                "function": {
                    "name": "manage_file_ops",
                    "description": "Create, read, update, delete, or list files in the workspace. All operations are restricted to project root.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["create", "read", "update", "delete", "list"],
                                "description": "File operation to perform"
                            },
                            "path": {
                                "type": "string",
                                "description": "File or directory path relative to project root"
                            },
                            "content": {
                                "type": "string",
                                "description": "File content (required for create/update operations)"
                            }
                        },
                        "required": ["operation", "path"]
                    }
                }
            },
            "apply_patch": {
                "type": "function",
                "function": {
                    "name": "apply_patch",
                    "description": "Generate and preview a unified diff patch for code changes. Requires user approval before application. Use this for modifying existing files.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "diff": {
                                "type": "string",
                                "description": "Unified diff format patch (--- a/file.ext\\n+++ b/file.ext\\n@@ -1,3 +1,4 @@\\n ...)"
                            }
                        },
                        "required": ["diff"]
                    }
                }
            },
            "search_workspace": {
                "type": "function",
                "function": {
                    "name": "search_workspace",
                    "description": "Semantic search over workspace files using RAG. Returns relevant code excerpts with file paths and context.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query (e.g., 'timer logic', 'motor control function')"
                            },
                            "k": {
                                "type": "integer",
                                "description": "Number of results to return (default: 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            "plan_terminal_cmd": {
                "type": "function",
                "function": {
                    "name": "plan_terminal_cmd",
                    "description": "Generate a terminal command plan with risk assessment. Requires user approval before execution. Use for running builds, tests, installs, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Shell command to execute (e.g., 'pip install pytest', 'npm run build')"
                            },
                            "rationale": {
                                "type": "string",
                                "description": "Explanation of why this command is needed"
                            }
                        },
                        "required": ["command", "rationale"]
                    }
                }
            },
            "dependency_manager": {
                "type": "function",
                "function": {
                    "name": "dependency_manager",
                    "description": "Detect project dependencies and tooling (venv, package.json, requirements.txt). Proposes safe installation commands.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            "web_search": {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for documentation, tutorials, Stack Overflow answers, and technical resources using DuckDuckGo. Use when workspace search returns no results or when user asks about external libraries/frameworks.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (e.g., 'Flet ExpansionTile documentation', 'IEC 61131-3 TON timer example', 'Siemens TIA Portal timer examples')"
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "Number of results to return (default: 5, max: 10)",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            "implement_feature": {
                "type": "function",
                "function": {
                    "name": "implement_feature",
                    "description": "Delegate complex feature implementation to CrewAI subsystem (Planner → Coder → Reviewer). Returns structured PatchPlan for approval.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "request": {
                                "type": "string",
                                "description": "Feature request description (e.g., 'Add conveyor control logic with 5s delay timer')"
                            },
                            "context": {
                                "type": "string",
                                "description": "Additional context or constraints (optional)"
                            }
                        },
                        "required": ["request"]
                    }
                }
            },
            "diagnose_project": {
                "type": "function",
                "function": {
                    "name": "diagnose_project",
                    "description": "Run project health diagnostics via AutoGen debate. Returns structured findings with prioritized fixes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "focus_area": {
                                "type": "string",
                                "description": "Specific area to focus on (e.g., 'syntax errors', 'dependencies', 'best practices'). Optional."
                            },
                            "context": {
                                "type": "string",
                                "description": "Additional context (optional)"
                            }
                        },
                        "required": []
                    }
                }
            }
        }

        # Filter based on mode
        if mode == "ask":
            # Ask mode: Read-only tools
            allowed_tools = ["search_workspace", "manage_file_ops", "web_search"]
        elif mode == "plan":
            # Plan mode: Planning tools only
            allowed_tools = ["search_workspace", "manage_file_ops"]
        else:
            # Agent mode: All tools
            allowed_tools = list(all_schemas.keys())

        # Return filtered schemas for registered tools
        schemas = []
        for tool_name in allowed_tools:
            if tool_name in self.tools and tool_name in all_schemas:
                schemas.append(all_schemas[tool_name])

        return schemas


__all__ = [
    "ToolRegistry",
    "ToolDefinition",
]
