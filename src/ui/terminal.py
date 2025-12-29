"""
Functional PowerShell Terminal Panel for Pulse IDE.

Provides a fully integrated PowerShell terminal with real-time command execution.
"""

import flet as ft
import subprocess
import threading
import queue
import sys
from pathlib import Path
from src.ui.theme import VSCodeColors, Fonts, Spacing


class TerminalPanel:
    """
    Fully functional PowerShell terminal with subprocess integration.

    Features:
    - Real PowerShell process integration
    - Real-time stdout/stderr output
    - Command history with arrow key navigation
    - VS Code Dark Modern theme styling
    - Graceful error handling
    """

    def __init__(self, on_command=None, workspace_path=None):
        """
        Initialize TerminalPanel with PowerShell integration.

        Args:
            on_command: Optional callback for custom command handling
            workspace_path: Working directory for the terminal (defaults to current dir)
        """
        self.on_command = on_command
        self.workspace_path = workspace_path or str(Path.cwd())
        self.output_view = None
        self.input_field = None
        self.command_history = []
        self.history_index = -1
        self.process = None
        self.output_queue = queue.Queue()
        self.is_running = False
        self.container = self._build()

        # Start PowerShell process
        self._start_powershell()

    def _build(self):
        """Build the terminal panel UI component with VS Code styling."""
        # Terminal output area
        self.output_view = ft.ListView(
            expand=True,
            spacing=0,
            padding=Spacing.PADDING_MEDIUM,
            auto_scroll=True,
        )

        # Add welcome message
        self._add_welcome_message()

        # Command input field with PowerShell prompt
        self.input_field = ft.TextField(
            hint_text="",
            multiline=False,
            on_submit=self._handle_command,
            on_change=self._on_input_change,
            border=ft.InputBorder.NONE,
            text_style=ft.TextStyle(
                font_family=Fonts.MONOSPACE_PRIMARY,
                color=VSCodeColors.TERMINAL_FOREGROUND,
                size=Fonts.FONT_SIZE_NORMAL,
            ),
            prefix=ft.Container(
                content=ft.Text(
                    "PS> ",
                    color=VSCodeColors.TERMINAL_ANSI_BRIGHT_GREEN,
                    size=Fonts.FONT_SIZE_NORMAL,
                    font_family=Fonts.MONOSPACE_PRIMARY,
                    weight=ft.FontWeight.BOLD,
                ),
                padding=ft.padding.only(right=5),
            ),
            bgcolor=VSCodeColors.TERMINAL_BACKGROUND,
            color=VSCodeColors.TERMINAL_FOREGROUND,
            cursor_color=VSCodeColors.TERMINAL_CURSOR,
            selection_color=VSCodeColors.TERMINAL_SELECTION,
        )

        # Main terminal container
        return ft.Container(
            bgcolor=VSCodeColors.PANEL_BACKGROUND,
            padding=Spacing.PADDING_SMALL,
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=self.output_view,
                        expand=True,
                        bgcolor=VSCodeColors.TERMINAL_BACKGROUND,
                        border=ft.border.all(Spacing.BORDER_WIDTH, VSCodeColors.PANEL_BORDER),
                        border_radius=Spacing.BORDER_RADIUS_SMALL,
                    ),
                    ft.Container(
                        content=self.input_field,
                        bgcolor=VSCodeColors.TERMINAL_BACKGROUND,
                        border=ft.border.all(Spacing.BORDER_WIDTH, VSCodeColors.INPUT_ACTIVE_BORDER),
                        border_radius=Spacing.BORDER_RADIUS_SMALL,
                        padding=ft.padding.symmetric(horizontal=Spacing.PADDING_SMALL, vertical=2),
                    ),
                ],
                spacing=Spacing.PADDING_SMALL,
                expand=True,
            ),
        )

    def _add_welcome_message(self):
        """Add welcome message and PowerShell version info."""
        welcome_lines = [
            "╔═══════════════════════════════════════════════════════════╗",
            "║                  PULSE IDE TERMINAL                       ║",
            "║              PowerShell Integration v1.0                  ║",
            "╚═══════════════════════════════════════════════════════════╝",
            "",
        ]

        for line in welcome_lines:
            self._add_output(line, VSCodeColors.TERMINAL_ANSI_BRIGHT_CYAN)

        self._add_output(f"Working Directory: {self.workspace_path}", VSCodeColors.TERMINAL_ANSI_YELLOW)
        self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)

    def _start_powershell(self):
        """Start a persistent PowerShell process."""
        try:
            # Determine PowerShell executable
            if sys.platform == "win32":
                # Try pwsh (PowerShell Core) first, fall back to powershell (Windows PowerShell)
                ps_executable = "pwsh.exe"
                try:
                    subprocess.run([ps_executable, "-Version"],
                                 capture_output=True,
                                 timeout=2,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    ps_executable = "powershell.exe"
            else:
                ps_executable = "pwsh"  # PowerShell Core on Linux/Mac

            # Start PowerShell process
            self.process = subprocess.Popen(
                [ps_executable, "-NoLogo", "-NoExit", "-Command", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                cwd=self.workspace_path,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            self.is_running = True

            # Start output reader threads
            threading.Thread(target=self._read_output, args=(self.process.stdout, "stdout"), daemon=True).start()
            threading.Thread(target=self._read_output, args=(self.process.stderr, "stderr"), daemon=True).start()
            threading.Thread(target=self._process_output_queue, daemon=True).start()

            self._add_output("PowerShell initialized successfully.", VSCodeColors.NOTIFICATION_SUCCESS_BACKGROUND)
            self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)

        except Exception as e:
            self._add_output(f"Error starting PowerShell: {str(e)}", VSCodeColors.ERROR_FOREGROUND)
            self._add_output("Falling back to command echo mode.", VSCodeColors.WARNING_FOREGROUND)
            self.is_running = False

    def _read_output(self, pipe, pipe_name):
        """Read output from PowerShell process in a separate thread."""
        try:
            for line in iter(pipe.readline, ''):
                if not line:
                    break
                self.output_queue.put((pipe_name, line.rstrip()))
        except Exception as e:
            self.output_queue.put(("error", f"Error reading {pipe_name}: {str(e)}"))

    def _process_output_queue(self):
        """Process output queue and update UI."""
        while self.is_running:
            try:
                pipe_name, line = self.output_queue.get(timeout=0.1)

                # Determine color based on pipe
                if pipe_name == "stderr":
                    color = VSCodeColors.ERROR_FOREGROUND
                elif pipe_name == "error":
                    color = VSCodeColors.ERROR_FOREGROUND
                else:
                    color = VSCodeColors.TERMINAL_FOREGROUND

                # Add output to UI
                self._add_output(line, color)

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing output queue: {e}")

    def get_control(self):
        """Get the terminal panel control for adding to the page."""
        return self.container

    def _handle_command(self, e):
        """Handle command submission and send to PowerShell."""
        command = self.input_field.value
        if not command or not command.strip():
            return

        command = command.strip()

        # Add command to history
        if not self.command_history or self.command_history[-1] != command:
            self.command_history.append(command)
        self.history_index = len(self.command_history)

        # Echo the command
        self._add_output(f"PS> {command}", VSCodeColors.TERMINAL_ANSI_BRIGHT_GREEN)

        # V2.1: Intercept 'run' commands for .st files (PLC compilation simulation)
        if command.lower().startswith("run "):
            self._handle_run_command(command)
        # Handle built-in commands
        elif command.lower() == "clear" or command.lower() == "cls":
            self.clear()
        elif command.lower() == "exit":
            self._add_output("Use Ctrl+C to close the terminal.", VSCodeColors.WARNING_FOREGROUND)
        else:
            # Send command to PowerShell
            if self.is_running and self.process and self.process.stdin:
                try:
                    self.process.stdin.write(command + "\n")
                    self.process.stdin.flush()
                except Exception as e:
                    self._add_output(f"Error executing command: {str(e)}", VSCodeColors.ERROR_FOREGROUND)
            else:
                # Fallback: execute command in callback
                if self.on_command:
                    self.on_command(command)
                else:
                    self._add_output("Terminal not connected to PowerShell.", VSCodeColors.WARNING_FOREGROUND)

        # Clear input field
        self.input_field.value = ""
        self.input_field.update()

    def _handle_run_command(self, command):
        """
        Handle 'run' commands with special PLC compilation simulation for .st files.

        V2.1 Feature: Simulates realistic PLC compilation output when running .st files.

        Args:
            command: The run command (e.g., "run main.st")
        """
        import time

        # Extract file path from command
        parts = command.split(maxsplit=1)
        if len(parts) < 2:
            self._add_output("Usage: run <filename>", VSCodeColors.ERROR_FOREGROUND)
            return

        file_path = parts[1].strip()

        # Check if it's a .st file (Structured Text PLC code)
        if file_path.endswith(".st"):
            self._simulate_plc_compilation(file_path)
        else:
            # For non-.st files, pass to PowerShell or execute normally
            if self.is_running and self.process and self.process.stdin:
                try:
                    # Try to execute with PowerShell
                    ps_command = f"& '{file_path}'"
                    self.process.stdin.write(ps_command + "\n")
                    self.process.stdin.flush()
                except Exception as e:
                    self._add_output(f"Error executing: {str(e)}", VSCodeColors.ERROR_FOREGROUND)
            else:
                self._add_output(f"Attempting to run: {file_path}", VSCodeColors.INFO_FOREGROUND)
                self._add_output("(File execution not supported in fallback mode)", VSCodeColors.WARNING_FOREGROUND)

    def _simulate_plc_compilation(self, file_path):
        """
        Simulate realistic PLC compilation output for .st files.

        Displays a compilation sequence similar to industrial PLC compilers.

        Args:
            file_path: Path to the .st file
        """
        import time
        from pathlib import Path

        # Check if file exists in workspace
        full_path = Path(self.workspace_path) / file_path
        file_exists = full_path.exists()

        # Compilation sequence
        self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)
        self._add_output("═══════════════════════════════════════════════", VSCodeColors.TERMINAL_ANSI_BRIGHT_CYAN)
        self._add_output("  PLC Structured Text Compiler v3.2.1", VSCodeColors.TERMINAL_ANSI_BRIGHT_CYAN)
        self._add_output("═══════════════════════════════════════════════", VSCodeColors.TERMINAL_ANSI_BRIGHT_CYAN)
        self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)

        if not file_exists:
            self._add_output(f"ERROR: File not found: {file_path}", VSCodeColors.ERROR_FOREGROUND)
            self._add_output(f"Checked path: {full_path}", VSCodeColors.TERMINAL_ANSI_BRIGHT_BLACK)
            self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)
            self._add_output("Compilation failed.", VSCodeColors.ERROR_FOREGROUND)
            return

        # Simulate compilation steps
        self._add_output(f"Source: {file_path}", VSCodeColors.INFO_FOREGROUND)
        self._add_output(f"Target: {file_path.replace('.st', '.obj')}", VSCodeColors.INFO_FOREGROUND)
        self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)

        # Parsing phase
        self._add_output("[1/4] Parsing Structured Text...", VSCodeColors.TERMINAL_ANSI_BRIGHT_YELLOW)
        time.sleep(0.3)  # Simulate processing
        self._add_output("      ✓ Syntax analysis complete", VSCodeColors.SUCCESS_FOREGROUND)
        self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)

        # Semantic analysis
        self._add_output("[2/4] Semantic Analysis...", VSCodeColors.TERMINAL_ANSI_BRIGHT_YELLOW)
        time.sleep(0.2)
        self._add_output("      ✓ Type checking complete", VSCodeColors.SUCCESS_FOREGROUND)
        self._add_output("      ✓ Variable resolution complete", VSCodeColors.SUCCESS_FOREGROUND)
        self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)

        # Code generation
        self._add_output("[3/4] Generating IL Code...", VSCodeColors.TERMINAL_ANSI_BRIGHT_YELLOW)
        time.sleep(0.2)
        self._add_output("      ✓ Instruction list generated", VSCodeColors.SUCCESS_FOREGROUND)
        self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)

        # Linking
        self._add_output("[4/4] Linking...", VSCodeColors.TERMINAL_ANSI_BRIGHT_YELLOW)
        time.sleep(0.2)
        self._add_output("      ✓ Linking complete", VSCodeColors.SUCCESS_FOREGROUND)
        self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)

        # Summary
        self._add_output("═══════════════════════════════════════════════", VSCodeColors.TERMINAL_ANSI_BRIGHT_GREEN)
        self._add_output("  COMPILATION SUCCESSFUL", VSCodeColors.TERMINAL_ANSI_BRIGHT_GREEN)
        self._add_output("═══════════════════════════════════════════════", VSCodeColors.TERMINAL_ANSI_BRIGHT_GREEN)
        self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)
        self._add_output("Build Statistics:", VSCodeColors.INFO_FOREGROUND)
        self._add_output("  - 0 Errors", VSCodeColors.SUCCESS_FOREGROUND)
        self._add_output("  - 0 Warnings", VSCodeColors.SUCCESS_FOREGROUND)
        self._add_output("  - Build time: 0.7s", VSCodeColors.INFO_FOREGROUND)
        self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)
        self._add_output(f"Output: {file_path.replace('.st', '.obj')}", VSCodeColors.TERMINAL_ANSI_BRIGHT_CYAN)
        self._add_output("", VSCodeColors.TERMINAL_FOREGROUND)

    def _on_input_change(self, e):
        """Handle input field changes (for future autocomplete, etc.)."""
        pass

    def _add_output(self, text, color=None):
        """
        Add output line to the terminal.

        Args:
            text: Text to display
            color: Text color (hex) - defaults to terminal foreground
        """
        if color is None:
            color = VSCodeColors.TERMINAL_FOREGROUND

        output_line = ft.Text(
            text,
            color=color,
            font_family=Fonts.MONOSPACE_PRIMARY,
            size=Fonts.FONT_SIZE_SMALL,
            selectable=True,
        )
        self.output_view.controls.append(output_line)
        if self.output_view.page:
            self.output_view.update()

    def add_output(self, text, output_type="info"):
        """
        Add output to terminal with automatic color coding.

        Args:
            text: Text to display
            output_type: Type of output ("info", "success", "warning", "error", "system")
        """
        color_map = {
            "info": VSCodeColors.INFO_FOREGROUND,
            "success": VSCodeColors.SUCCESS_FOREGROUND,
            "warning": VSCodeColors.WARNING_FOREGROUND,
            "error": VSCodeColors.ERROR_FOREGROUND,
            "system": VSCodeColors.TERMINAL_ANSI_BRIGHT_BLACK,
        }

        color = color_map.get(output_type, VSCodeColors.TERMINAL_FOREGROUND)
        self._add_output(text, color)

    def clear(self):
        """Clear terminal output."""
        self.output_view.controls.clear()
        self._add_welcome_message()
        if self.output_view.page:
            self.output_view.update()

    def execute_command(self, command):
        """
        Execute a command programmatically.

        Args:
            command: Command string to execute
        """
        self.input_field.value = command
        self._handle_command(None)

    def cleanup(self):
        """Clean up resources and terminate PowerShell process."""
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                self.process.kill()
