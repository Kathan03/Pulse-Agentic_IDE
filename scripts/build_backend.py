#!/usr/bin/env python3
"""
Build script for Pulse IDE Python backend.

Creates a standalone executable using PyInstaller that can be bundled
with the Electron app.

Usage:
    python scripts/build_backend.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
OUTPUT_DIR = PROJECT_ROOT / "backend-dist"

# PyInstaller options
PYINSTALLER_OPTIONS = [
    "--onefile",  # Single executable
    "--clean",    # Clean build
    "--noconfirm",  # Overwrite without asking
    f"--distpath={OUTPUT_DIR}",
    f"--workpath={PROJECT_ROOT / 'build' / 'pyinstaller'}",
    f"--specpath={PROJECT_ROOT / 'build'}",
    "--name=pulse-server",
    # Hidden imports for FastAPI/Uvicorn
    "--hidden-import=uvicorn.logging",
    "--hidden-import=uvicorn.loops",
    "--hidden-import=uvicorn.loops.auto",
    "--hidden-import=uvicorn.protocols",
    "--hidden-import=uvicorn.protocols.http",
    "--hidden-import=uvicorn.protocols.http.auto",
    "--hidden-import=uvicorn.protocols.websockets",
    "--hidden-import=uvicorn.protocols.websockets.auto",
    "--hidden-import=uvicorn.lifespan",
    "--hidden-import=uvicorn.lifespan.on",
    "--hidden-import=fastapi",
    "--hidden-import=starlette",
    "--hidden-import=pydantic",
    "--hidden-import=anyio",
    "--hidden-import=anyio._backends",
    "--hidden-import=anyio._backends._asyncio",
    # Additional dependencies
    "--hidden-import=langgraph",
    "--hidden-import=langchain",
    "--hidden-import=langchain_core",
    "--hidden-import=langchain_openai",
    "--hidden-import=langchain_anthropic",
]


def clean_output():
    """Remove previous build artifacts."""
    print("Cleaning previous build...")
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_backend():
    """Build the Python backend using PyInstaller."""
    print("Building Pulse backend...")

    # Entry point for the server
    entry_point = SRC_DIR / "server" / "main.py"

    if not entry_point.exists():
        print(f"Error: Entry point not found: {entry_point}")
        sys.exit(1)

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        *PYINSTALLER_OPTIONS,
        str(entry_point)
    ]

    print(f"Running: {' '.join(cmd[:5])}...")

    try:
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
        print("\nBuild completed successfully!")
        print(f"Output: {OUTPUT_DIR / 'pulse-server.exe'}")
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error code: {e.returncode}")
        sys.exit(1)


def verify_build():
    """Verify the build output exists."""
    exe_name = "pulse-server.exe" if sys.platform == "win32" else "pulse-server"
    exe_path = OUTPUT_DIR / exe_name

    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\nBuild verified:")
        print(f"  Executable: {exe_path}")
        print(f"  Size: {size_mb:.1f} MB")
        return True
    else:
        print(f"\nError: Expected output not found: {exe_path}")
        return False


def main():
    """Main entry point."""
    print("=" * 60)
    print("Pulse IDE Backend Build Script")
    print("=" * 60)

    # Ensure we're in the project root
    os.chdir(PROJECT_ROOT)

    # Run build steps
    clean_output()
    build_backend()

    if verify_build():
        print("\nBackend build complete. Ready for Electron packaging.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
