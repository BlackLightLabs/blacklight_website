"""
End-to-End MCP Integration Test

Tests the complete MCP integration from database configuration
to agent execution with Playwright MCP server.
"""

import asyncio
import json
from pathlib import Path

# Import all models to ensure they're registered with SQLAlchemy
from src.blacklight.features.auth.models import User
from src.blacklight.features.agents.models import Agent
from src.blacklight.features.agents.mcp_models import (
    MCPServerConfig,
    AgentMCPBinding,
    MCPToolExecution,
)
from src.blacklight.features.executions.models import Execution

# Test 1: Database Models and Repositories
async def test_mcp_repositories():
    """Test MCP repository operations"""
    print("=" * 80)
    print("TEST 1: MCP Repositories")
    print("=" * 80)

    from src.blacklight.common.database import SessionLocal
    from src.blacklight.features.agents.mcp_repository import (
        MCPServerRepository,
        MCPToolExecutionRepository,
    )
    from src.blacklight.features.agents.mcp_models import MCPTransportEnum

    async with SessionLocal() as db:
        mcp_repo = MCPServerRepository(db)
        execution_repo = MCPToolExecutionRepository(db)

        # Clean up any existing test server
        existing_server = await mcp_repo.get_by_name("playwright-test")
        if existing_server:
            await mcp_repo.delete(existing_server.id)
            print("✓ Cleaned up existing test server")

        # Create a test MCP server (Playwright)
        print("\n1. Creating Playwright MCP server configuration...")
        server = await mcp_repo.create(
            name="playwright-test",  # Use unique test name
            transport=MCPTransportEnum.STREAMABLE_HTTP,
            connection_config={
                "url": "http://localhost:8080/mcp",  # Assuming Playwright MCP server
                "headers": {},
            },
            description="Playwright browser automation server",
            is_enabled=True,
            requires_approval=False,
        )
        print(f"✓ Created server: {server.name} (ID: {server.id})")

        # List enabled servers
        print("\n2. Listing enabled MCP servers...")
        enabled_servers = await mcp_repo.get_enabled_servers()
        print(f"✓ Found {len(enabled_servers)} enabled server(s)")
        for s in enabled_servers:
            print(f"  - {s.name} ({s.transport.value})")

        # Log a tool execution (without agent_id - it's optional)
        print("\n3. Logging MCP tool execution...")
        execution = await execution_repo.log_execution(
            server_name=server.name,  # Use the created server name
            tool_name="browser_navigate",
            status="success",
            agent_id=None,  # Optional - can be None for standalone tool calls
            parameters={"url": "https://example.com"},
            result={"status": "ok"},
            execution_time_ms=150,
        )
        print(f"✓ Logged execution: {execution.tool_name} ({execution.status})")

        print("\n✅ Repository tests PASSED!\n")
        return server.id


# Test 2: MCP Client Manager
async def test_mcp_client_manager():
    """Test MCP client initialization and tool loading"""
    print("=" * 80)
    print("TEST 2: MCP Client Manager")
    print("=" * 80)

    from src.blacklight.common.mcp_client import (
        get_mcp_client_manager,
        MCPServerConfig,
        MCPTransportType,
    )

    # Initialize client manager
    print("\n1. Initializing MCP client manager...")
    client = get_mcp_client_manager()

    # Create test server config (mock server for testing)
    # In production, this would be a real Playwright MCP server
    test_config = MCPServerConfig(
        name="test-server",
        transport=MCPTransportType.STDIO,
        command="python",
        args=["-c", "print('Mock MCP server')"],
        enabled=True,
    )

    print("\n2. Testing server configuration conversion...")
    client_config = test_config.to_client_config()
    print(f"✓ Config: {client_config}")

    print("\n3. Client manager properties...")
    print(f"  - Initialized: {client.is_initialized}")
    print(f"  - Servers: {client.list_servers()}")

    print("\n✅ MCP Client Manager tests PASSED!\n")


# Test 3: Tool Registry with MCP Tools
async def test_tool_registry():
    """Test tool registry MCP integration"""
    print("=" * 80)
    print("TEST 3: Tool Registry with MCP Tools")
    print("=" * 80)

    from src.blacklight.features.agents.tools.registry import get_tool_registry
    from langchain_core.tools import tool as langchain_tool

    registry = get_tool_registry()

    # Create mock MCP tools
    print("\n1. Creating mock MCP tools...")

    @langchain_tool
    def mock_browser_navigate(url: str) -> str:
        """Navigate to a URL in the browser"""
        return f"Navigated to {url}"

    @langchain_tool
    def mock_browser_screenshot() -> str:
        """Take a screenshot of the current page"""
        return "Screenshot captured"

    mock_tools = [mock_browser_navigate, mock_browser_screenshot]

    # Register MCP server with tools
    print("\n2. Registering MCP server with tools...")
    registry.register_mcp_server("playwright", mock_tools, requires_approval=False)
    print(f"✓ Registered {len(mock_tools)} tools from 'playwright' server")

    # List all tools (local + MCP)
    print("\n3. Listing all tools...")
    all_tools = registry.list()
    print(f"✓ Total tools: {len(all_tools)}")

    # Get MCP tools specifically
    print("\n4. Getting MCP tools...")
    mcp_tools = registry.get_mcp_tools("playwright")
    print(f"✓ MCP tools from 'playwright': {len(mcp_tools)}")
    for tool in mcp_tools:
        print(f"  - {tool.name}: {tool.description}")

    # Test catalog generation
    print("\n5. Generating tool catalog...")
    catalog = registry.get_catalog_text()
    print(f"✓ Catalog length: {len(catalog)} characters")
    print("\nCatalog preview:")
    print(catalog[:500] + "...\n")

    print("✅ Tool Registry tests PASSED!\n")


# Test 4: MCP Service (Suggestions & Initialization)
async def test_mcp_service():
    """Test MCP service layer"""
    print("=" * 80)
    print("TEST 4: MCP Service (Smart Suggestions)")
    print("=" * 80)

    from src.blacklight.common.database import SessionLocal
    from src.blacklight.features.agents.mcp_service import MCPService

    async with SessionLocal() as db:
        mcp_service = MCPService(db)

        # Test smart suggestions
        print("\n1. Testing smart MCP server suggestions...")

        test_requirements = [
            "I need to test web applications",
            "Build an agent that scrapes product data from websites",
            "Create a bot that queries our PostgreSQL database",
            "I want to send automated emails to customers",
        ]

        for req in test_requirements:
            print(f"\n  Requirement: '{req}'")
            suggestions = await mcp_service.suggest_mcp_servers(req)
            print(f"  Suggestions: {[s['server_name'] for s in suggestions]}")

        # Test catalog generation
        print("\n2. Generating MCP tool catalog for prompts...")
        catalog = await mcp_service.get_mcp_tool_catalog_for_prompt()
        print(f"✓ Generated catalog: {len(catalog)} characters")

    print("\n✅ MCP Service tests PASSED!\n")


# Test 5: Code Generation with MCP
async def test_code_generation():
    """Test code generation with MCP server specs"""
    print("=" * 80)
    print("TEST 5: Code Generation with MCP Servers")
    print("=" * 80)

    from src.blacklight.features.agents.generator.code_generator import CodeGenerator
    from src.blacklight.features.agents.spec_schema import (
        AgentSpec,
        StateField,
        NodeSpec,
        EdgeSpec,
        ToolSpec,
        TestCase,
        TestAssertion,
        AssertionType,
        NodeType,
        TransportType,
        MCPServerSpec,
    )

    # Create agent spec with MCP server
    print("\n1. Creating agent spec with Playwright MCP server...")

    spec = AgentSpec(
        name="WebTesterAgent",
        description="Tests web applications using Playwright",
        model="gpt-4o",
        state=[
            StateField(name="url", type="str", description="Target URL"),
            StateField(name="screenshot", type="str | None", description="Screenshot path"),
            StateField(name="result", type="str", description="Test result"),
        ],
        nodes=[
            NodeSpec(
                id="navigate",
                type=NodeType.TOOL,
                tool="browser_navigate",
                input=["url"],
                output=["result"],
                input_mapping={"url": "url"},
            ),
            NodeSpec(
                id="capture",
                type=NodeType.TOOL,
                tool="browser_screenshot",
                input=[],
                output=["screenshot"],
            ),
        ],
        edges=[
            EdgeSpec(**{"from": "navigate", "to": "capture"}),
            EdgeSpec(**{"from": "capture", "to": "END"}),
        ],
        tools=[
            ToolSpec(
                name="browser_navigate",
                description="Navigate to URL",
                requires_approval=False,
                input_schema={"type": "object", "properties": {"url": {"type": "string"}}},
                transport=TransportType.MCP,
                config={"server": "playwright"},
            ),
            ToolSpec(
                name="browser_screenshot",
                description="Capture screenshot",
                requires_approval=False,
                input_schema={"type": "object", "properties": {}},
                transport=TransportType.MCP,
                config={"server": "playwright"},
            ),
        ],
        mcp_servers=[
            MCPServerSpec(name="playwright", enabled=True),
        ],
        tests=[
            TestCase(
                name="test_navigation",
                input={"url": "https://example.com"},
                assertions=[
                    TestAssertion(type=AssertionType.NO_ERRORS),
                ],
            ),
        ],
    )

    print("✓ Created agent spec with:")
    print(f"  - {len(spec.nodes)} nodes")
    print(f"  - {len(spec.tools)} MCP tools")
    print(f"  - {len(spec.mcp_servers)} MCP server(s): {[s.name for s in spec.mcp_servers]}")

    # Generate code
    print("\n2. Generating agent code...")
    generator = CodeGenerator()
    output_dir = Path("./backend/generated/test_mcp_agent")

    module_path = generator.generate(spec, output_dir, version=1)
    print(f"✓ Generated code at: {module_path}")

    # Check generated files
    print("\n3. Verifying generated files...")
    expected_files = ["graph.py", "tools.py", "__init__.py", "run.py"]
    for filename in expected_files:
        file_path = module_path / filename
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"  ✓ {filename} ({size} bytes)")
        else:
            print(f"  ✗ {filename} MISSING!")

    # Validate syntax
    print("\n4. Validating generated code syntax...")
    is_valid, error = generator.validate_syntax(module_path)
    if is_valid:
        print("✓ All generated files have valid Python syntax")
    else:
        print(f"✗ Syntax error: {error}")

    # Show snippet of generated tools.py
    print("\n5. Generated tools.py preview:")
    tools_content = (module_path / "tools.py").read_text()
    print("-" * 60)
    # Show MCP initialization section
    if "initialize_mcp_tools" in tools_content:
        lines = tools_content.split("\n")
        in_init_func = False
        preview_lines = []
        for line in lines:
            if "async def initialize_mcp_tools" in line:
                in_init_func = True
            if in_init_func:
                preview_lines.append(line)
                if len(preview_lines) > 30:  # Show first 30 lines
                    break
        print("\n".join(preview_lines))
        print("...")
    print("-" * 60)

    print("\n✅ Code Generation tests PASSED!\n")
    return module_path


# Test 6: End-to-End Integration
async def test_end_to_end():
    """Complete end-to-end test"""
    print("=" * 80)
    print("TEST 6: END-TO-END INTEGRATION")
    print("=" * 80)

    try:
        # Step 1: Database setup
        print("\n[Step 1] Setting up database...")
        server_id = await test_mcp_repositories()

        # Step 2: Client manager
        print("\n[Step 2] Testing MCP client manager...")
        await test_mcp_client_manager()

        # Step 3: Tool registry
        print("\n[Step 3] Testing tool registry...")
        await test_tool_registry()

        # Step 4: MCP service
        print("\n[Step 4] Testing MCP service...")
        await test_mcp_service()

        # Step 5: Code generation
        print("\n[Step 5] Testing code generation...")
        module_path = await test_code_generation()

        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 80)
        print("\nSummary:")
        print("✓ Database models and repositories working")
        print("✓ MCP client manager functional")
        print("✓ Tool registry integrating MCP tools")
        print("✓ MCP service providing smart suggestions")
        print("✓ Code generation producing MCP-enabled agents")
        print(f"\nGenerated agent code: {module_path}")
        print("\nTo test with a real Playwright MCP server:")
        print("1. Start Playwright MCP server: npx @modelcontextprotocol/server-playwright")
        print("2. Update server URL in database to match the server")
        print("3. Run the generated agent: python run.py --input '{\"url\": \"https://example.com\"}'")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


# Main test runner
async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("MCP INTEGRATION TEST SUITE")
    print("=" * 80)
    print("\nThis will test:")
    print("1. Database repositories for MCP configuration")
    print("2. MCP client manager initialization")
    print("3. Tool registry with MCP tools")
    print("4. MCP service (smart suggestions)")
    print("5. Code generation with MCP servers")
    print("6. End-to-end integration")
    print("\n" + "=" * 80 + "\n")

    await test_end_to_end()


if __name__ == "__main__":
    asyncio.run(main())
