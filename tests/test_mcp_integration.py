"""
MCP Server Integration Tests
=============================

測試 MCP Server 與 AI Agent 的整合功能
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from src.mcp_server.server import MCPServer
from src.mcp_server.tools import ToolResponse
from src.ai_agent.agent import FinancialAnalystAgent, AgentRole, TaskType
from src.core.database import get_db


# ===== Fixtures =====

@pytest.fixture(scope="session")
def event_loop():
    """創建事件迴圈"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def db_session():
    """測試用資料庫 session"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def mcp_server(db_session):
    """創建 MCP Server 實例"""
    server = MCPServer(
        db_session=db_session,
        cache_enabled=False,
        max_concurrent_tools=3
    )
    return server


class TestMCPServer:
    """測試 MCP Server 基礎功能"""

    def test_server_initialization(self, mcp_server):
        """測試伺服器初始化"""
        assert mcp_server is not None
        assert len(mcp_server.tools) > 0
        print(f"\nMCP Server initialized with {len(mcp_server.tools)} tools")

    def test_list_tools(self, mcp_server):
        """測試列出所有工具"""
        tools = mcp_server.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        print(f"\nFound {len(tools)} registered tools")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
