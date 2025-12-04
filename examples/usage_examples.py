"""
AI Agent + MCP Server Usage Examples
"""

import asyncio
import os
from src.mcp_server.server import MCPServer
from src.ai_agent.agent import FinancialAnalystAgent
from src.core.database import get_db


def initialize_services():
    """Initialize services"""
    db = next(get_db())
    mcp_server = MCPServer(db_session=db, cache_enabled=True)
    agent = FinancialAnalystAgent(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        mcp_server=mcp_server
    )
    return agent, mcp_server, db


async def example_simple_query():
    """Example: Simple financial query"""
    agent, mcp_server, db = initialize_services()
    try:
        result = await agent.analyze(user_query="What is ROE?", company_id=None)
        print(f"Response: {result.get('response')}")
    finally:
        db.close()


async def example_company_analysis():
    """Example: Company financial analysis"""
    agent, mcp_server, db = initialize_services()
    try:
        result = await agent.analyze(
            user_query="Analyze TSMC (2330) financial health",
            company_id="2330"
        )
        print(f"Task ID: {result['task_id']}")
        print(f"Tools: {result['metadata']['tools_executed']}")
    finally:
        db.close()


def list_available_tools():
    """List all available tools"""
    agent, mcp_server, db = initialize_services()
    try:
        tools = mcp_server.list_tools()
        print(f"Available tools: {len(tools)}")
        for tool in tools:
            print(f"- {tool['name']}: {tool['description']}")
    finally:
        db.close()


async def main():
    """Main program"""
    examples = {
        "1": example_simple_query,
        "2": example_company_analysis,
        "3": list_available_tools,
    }
    choice = input("Choose example (1-3, default 3): ").strip() or "3"
    if choice in examples:
        func = examples[choice]
        if asyncio.iscoroutinefunction(func):
            await func()
        else:
            func()


if __name__ == "__main__":
    asyncio.run(main())
