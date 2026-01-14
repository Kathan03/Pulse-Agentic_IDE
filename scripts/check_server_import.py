"""Quick test to verify server module imports correctly."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.server.main import app
    print("SUCCESS: Server module imports correctly!")
    print(f"App title: {app.title}")
    print(f"App version: {app.version}")
except Exception as e:
    print(f"ERROR: Failed to import server module: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
