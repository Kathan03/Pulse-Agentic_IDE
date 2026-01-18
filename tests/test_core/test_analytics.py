"""
Tests for Tool Usage Analytics.
"""
import pytest
import json
from src.core.analytics import ToolAnalytics, log_tool_usage, get_analytics_summary, reset_analytics

class TestToolAnalytics:
    @pytest.fixture
    def analytics(self, tmp_path):
        """Create analytics instance with temp path."""
        # Use a temp directory for the project root
        return ToolAnalytics(project_root=tmp_path)

    def test_log_and_persistence(self, analytics, tmp_path):
        """Test logging usage and JSON persistence."""
        # Log some usage
        analytics.log_tool_usage("test_tool", True, 100)
        analytics.log_tool_usage("test_tool", False, 50, error="Test error")
        
        # Verify file exists
        analytics_file = tmp_path / ".pulse" / "analytics.json"
        assert analytics_file.exists()
        
        # Verify content
        data = json.loads(analytics_file.read_text())
        assert len(data["tool_calls"]) == 2
        assert data["tool_calls"][0]["tool"] == "test_tool"
        assert data["tool_calls"][0]["success"] is True
        assert data["tool_calls"][0]["duration_ms"] == 100
        
        assert data["tool_calls"][1]["success"] is False
        assert data["tool_calls"][1]["error"] == "Test error"

    def test_summary_generation(self, analytics):
        """Test summary statistics calculation."""
        analytics.log_tool_usage("tool_a", True, 100)
        analytics.log_tool_usage("tool_a", True, 200)
        analytics.log_tool_usage("tool_b", False, 50)
        
        summary = analytics.get_summary()
        
        assert summary["total_calls"] == 3
        assert summary["total_success"] == 2
        assert summary["total_failures"] == 1
        assert summary["success_rate"] == 66.7
        
        # Check per-tool stats
        tool_a = summary["by_tool"]["tool_a"]
        assert tool_a["calls"] == 2
        assert tool_a["avg_duration_ms"] == 150
        
        tool_b = summary["by_tool"]["tool_b"]
        assert tool_b["calls"] == 1
        assert tool_b["failures"] == 1

    def test_global_convenience_functions(self, tmp_path, monkeypatch):
        """Test global convenience functions using a mocked global instance."""
        # Reset any existing global state
        reset_analytics(tmp_path)
        
        log_tool_usage("global_tool", True, 123, project_root=tmp_path)
        
        summary = get_analytics_summary(project_root=tmp_path)
        assert summary["total_calls"] == 1
        
        file_path = tmp_path / ".pulse" / "analytics.json"
        assert file_path.exists()
