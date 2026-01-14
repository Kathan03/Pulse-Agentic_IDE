#!/usr/bin/env python
"""
Test script for Pulse IDE WebSocket Server.

Tests the WebSocket server end-to-end by:
1. Connecting to the server
2. Sending an agent request
3. Receiving and printing events
4. Handling the run result

Usage:
    # First, start the server in another terminal:
    python -m src.server.main

    # Then run this test:
    python scripts/test_websocket_server.py

    # Or with custom settings:
    python scripts/test_websocket_server.py --host 127.0.0.1 --port 8765
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import websockets
except ImportError:
    print("Error: websockets package not installed.")
    print("Run: pip install websockets")
    sys.exit(1)


async def test_health_endpoint(host: str, port: int):
    """Test the HTTP health endpoint."""
    import urllib.request
    import urllib.error

    url = f"http://{host}:{port}/api/health"
    print(f"\n[1] Testing health endpoint: {url}")

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            print(f"    Status: {data.get('status')}")
            print(f"    Version: {data.get('version')}")
            print("    Health check: PASSED")
            return True
    except urllib.error.URLError as e:
        print(f"    Error: {e}")
        print("    Health check: FAILED")
        return False


async def test_websocket_connection(host: str, port: int, project_root_path: str):
    """Test WebSocket connection and basic message flow."""
    uri = f"ws://{host}:{port}/ws"
    print(f"\n[2] Testing WebSocket connection: {uri}")

    try:
        async with websockets.connect(uri) as ws:
            # Receive connection confirmation
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            print(f"    Connected: {data.get('type')}")
            connection_id = data.get("payload", {}).get("connection_id")
            print(f"    Connection ID: {connection_id}")

            # Test ping/pong
            print("\n[3] Testing ping/pong...")
            ping_msg = {
                "type": "ping",
                "id": "ping-test-1",
                "timestamp": "2024-01-01T00:00:00",
                "payload": {}
            }
            await ws.send(json.dumps(ping_msg))
            pong = await asyncio.wait_for(ws.recv(), timeout=5)
            pong_data = json.loads(pong)
            print(f"    Received: {pong_data.get('type')}")
            if pong_data.get("type") == "pong":
                print("    Ping/pong: PASSED")
            else:
                print("    Ping/pong: FAILED")

            # Test agent request (ask mode for read-only)
            print("\n[4] Testing agent request (ask mode)...")
            agent_request = {
                "type": "agent_request",
                "id": "test-agent-1",
                "timestamp": "2024-01-01T00:00:00",
                "payload": {
                    "user_input": "What is Pulse IDE?",
                    "project_root": project_root_path,
                    "mode": "ask",
                    "max_iterations": 3
                }
            }
            await ws.send(json.dumps(agent_request))
            print(f"    Sent agent request with input: '{agent_request['payload']['user_input']}'")

            # Receive events until run_result
            print("\n[5] Receiving events...")
            event_count = 0
            timeout_seconds = 60

            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout_seconds)
                    data = json.loads(msg)
                    msg_type = data.get("type")
                    event_count += 1

                    if msg_type == "event":
                        event_type = data.get("payload", {}).get("event_type", "unknown")
                        print(f"    [{event_count}] Event: {event_type}")
                    elif msg_type == "run_result":
                        print(f"    [{event_count}] Run result received!")
                        payload = data.get("payload", {})
                        print(f"        Success: {payload.get('success')}")
                        print(f"        Response: {payload.get('response', '')[:200]}...")
                        print(f"        Files touched: {payload.get('files_touched', [])}")
                        break
                    elif msg_type == "error":
                        print(f"    [{event_count}] Error: {data.get('payload', {}).get('message')}")
                        break
                    elif msg_type == "approval_required":
                        print(f"    [{event_count}] Approval required (not expected in ask mode)")
                        # Auto-approve for testing
                        approval_type = data.get("payload", {}).get("approval_type")
                        run_id = data.get("payload", {}).get("run_id")
                        approval_response = {
                            "type": "approval_response",
                            "id": "approval-test-1",
                            "timestamp": "2024-01-01T00:00:00",
                            "payload": {
                                "run_id": run_id,
                                "approved": True,
                                "feedback": ""
                            }
                        }
                        await ws.send(json.dumps(approval_response))
                        print(f"        Auto-approved {approval_type}")
                    else:
                        print(f"    [{event_count}] {msg_type}: {data.get('payload', {})}")

            except asyncio.TimeoutError:
                print(f"    Timeout after {timeout_seconds}s waiting for events")

            print(f"\n    Total events received: {event_count}")
            print("    WebSocket test: PASSED")
            return True

    except websockets.exceptions.ConnectionClosed as e:
        print(f"    Connection closed: {e}")
        return False
    except Exception as e:
        print(f"    Error: {e}")
        return False


async def main(host: str, port: int, project_root_path: str):
    """Run all tests."""
    print("=" * 60)
    print("Pulse IDE WebSocket Server Test")
    print("=" * 60)
    print(f"Server: {host}:{port}")
    print(f"Project root: {project_root_path}")

    # Test health endpoint
    health_ok = await test_health_endpoint(host, port)
    if not health_ok:
        print("\nServer not responding. Is it running?")
        print(f"Start it with: python -m src.server.main --host {host} --port {port}")
        return False

    # Test WebSocket connection
    ws_ok = await test_websocket_connection(host, port, project_root_path)

    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Health check: {'PASSED' if health_ok else 'FAILED'}")
    print(f"  WebSocket:    {'PASSED' if ws_ok else 'FAILED'}")
    print("=" * 60)

    return health_ok and ws_ok


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test the Pulse IDE WebSocket server"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Server port (default: 8765)"
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=str(project_root),
        help="Project root path for agent requests"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = asyncio.run(main(args.host, args.port, args.project_root))
    sys.exit(0 if success else 1)
