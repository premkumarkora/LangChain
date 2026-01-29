"""
LangChain Agent with Multiple MCP Servers (FREE APIs!)
======================================================

This script demonstrates how to connect a LangChain agent to multiple
MCP (Model Context Protocol) servers using COMPLETELY FREE APIs.

ARCHITECTURE:
─────────────────────────────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────┐
    │                   YOUR QUESTION                              │
    │     "What's the weather in London and any UK news?"         │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                 LangChain ReAct Agent                       │
    │                   (gpt-4o-mini LLM)                         │
    │                                                             │
    │  The agent THINKS: "I need weather AND news tools"          │
    │  Then ACTS: Calls tools from different MCP servers          │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          │  langchain-mcp-adapters
                          │  (Routes requests to correct server)
                          │
    ┌─────────────────────▼───────────────────────────────────────┐
    │                 MCP Client Manager                          │
    │              (Manages all server connections)               │
    └───────┬─────────────────┬─────────────────┬─────────────────┘
            │                 │                 │
            ▼                 ▼                 ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │    Weather    │ │     News      │ │    Utils      │
    │  MCP Server   │ │  MCP Server   │ │  MCP Server   │
    │               │ │               │ │               │
    │ get_weather   │ │ search_news   │ │ calculate     │
    │ get_forecast  │ │ get_headlines │ │ get_time      │
    │               │ │               │ │ convert_temp  │
    └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
            │                 │                 │
            ▼                 ▼                 ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │  Open-Meteo   │ │ NewsData.io   │ │ (Local Python)│
    │    (FREE!)    │ │  (FREE tier)  │ │  (No API!)    │
    │  No API key!  │ │ 200 req/day   │ │               │
    └───────────────┘ └───────────────┘ └───────────────┘

APIs USED:
──────────
1. Open-Meteo (Weather): 100% FREE, no API key needed!
2. NewsData.io (News): FREE tier with 200 requests/day
3. Utils: No external API, runs locally

WHY MCP?
────────
- Modular: Each server is independent
- Reusable: Use the same servers with any MCP-compatible agent
- Scalable: Add new servers without changing agent code
- Secure: API keys stay in their respective servers

TO RUN:
───────
    python agent_main.py

For demo mode (runs preset queries):
    python agent_main.py --demo
"""

import os
import asyncio
from dotenv import load_dotenv

# LangChain imports
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# MCP adapter imports
from langchain_mcp_adapters.client import MultiServerMCPClient

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# MCP Server configurations
# Each server runs as a separate process and communicates via stdio
MCP_SERVERS = {
    # Weather server using FREE Open-Meteo API (no API key!)
    "weather": {
        "command": "python",
        "args": [os.path.join(SCRIPT_DIR, "weather_server.py")],
        "transport": "stdio",
    },
    # News server using FREE NewsData.io API (200 req/day)
    "news": {
        "command": "python",
        "args": [os.path.join(SCRIPT_DIR, "news_server.py")],
        "transport": "stdio",
    },
    # Utils server - no external API needed!
    "utils": {
        "command": "python",
        "args": [os.path.join(SCRIPT_DIR, "utils_server.py")],
        "transport": "stdio",
    },
}

# Example queries to demonstrate capabilities
EXAMPLE_QUERIES = [
    # Weather + News combination
    "What's the weather in London and find any news about UK weather?",

    # Forecast + Search
    "Get the 3-day weather forecast for Tokyo and search for technology news.",

    # Headlines + Weather
    "What are the top technology headlines today? Also, what's the weather in New York?",

    # Pure weather query
    "What's the current weather in Paris and Sydney?",

    # Utils + Weather
    "What time is it in Tokyo right now? And what's the weather there?",

    # Calculator
    "Calculate 15% of 299.99 for me.",

    # Timezone conversion
    "If it's 2pm in New York, what time is it in London and Tokyo?",
]


def print_banner():
    """Print the welcome banner."""
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║       LangChain + MCP Multi-Server Demo (FREE APIs!)         ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║                                                               ║
    ║  This demo uses COMPLETELY FREE APIs:                         ║
    ║                                                               ║
    ║  🌤️  Weather: Open-Meteo (NO API key needed!)                 ║
    ║  📰 News: NewsData.io (200 free requests/day)                ║
    ║  🔧 Utils: Local Python (calculator, time, etc.)             ║
    ║                                                               ║
    ║  The agent will automatically choose which tools to use      ║
    ║  based on your question!                                      ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)


def check_api_keys():
    """Check for required API keys and print status."""
    openai_key = os.getenv("OPENAI_API_KEY")
    newsdata_key = os.getenv("NEWSDATA_API_KEY")

    print("API Key Status:")
    print("─" * 50)

    if openai_key:
        print("✅ OPENAI_API_KEY: Set")
    else:
        print("❌ OPENAI_API_KEY: NOT SET (required for LLM)")
        return False

    if newsdata_key:
        print("✅ NEWSDATA_API_KEY: Set")
    else:
        print("⚠️  NEWSDATA_API_KEY: Not set (news tools won't work)")
        print("   Get free key at: https://newsdata.io/register")

    print("✅ Open-Meteo: No API key needed!")
    print("✅ Utils: No API key needed!")
    print("─" * 50)

    return True


async def run_agent():
    """
    Main function to initialize and run the LangChain agent.

    This demonstrates:
    1. Connecting to multiple MCP servers
    2. Creating a ReAct agent with MCP tools
    3. Streaming agent responses to show reasoning
    """
    print_banner()

    if not check_api_keys():
        print("\n❌ Please set OPENAI_API_KEY in your .env file")
        print("   See .env.example for instructions")
        return

    print("\n📡 Connecting to MCP servers...")

    # The MCP client manages connections to all servers
    # Using async context manager ensures proper startup/shutdown
    async with MultiServerMCPClient(MCP_SERVERS) as mcp_client:
        print("✅ Connected to all MCP servers!\n")

        # Get unified tool list from all connected servers
        # This is the magic - tools from different servers appear as one list
        tools = mcp_client.get_tools()

        print(f"🔧 Available tools ({len(tools)}):")
        for tool in tools:
            print(f"   • {tool.name}")
        print()

        # Initialize the LLM (gpt-4o-mini is cost-effective and capable)
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,  # Deterministic for reproducibility
        )

        # Create a ReAct agent
        # ReAct = Reason + Act: Agent thinks, acts, observes, repeats
        agent = create_react_agent(llm, tools)

        # Interactive loop
        print("=" * 60)
        print("  INTERACTIVE MODE")
        print("=" * 60)
        print("\nAsk questions that combine weather, news, and utility tools!")
        print("Commands: 'examples' to see sample queries, 'quit' to exit\n")

        while True:
            try:
                user_input = input("🧑 You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() == "quit":
                    print("\n👋 Goodbye!")
                    break

                if user_input.lower() == "examples":
                    print("\n📝 Example queries you can try:\n")
                    for i, query in enumerate(EXAMPLE_QUERIES, 1):
                        print(f"   {i}. {query}")
                    print()
                    continue

                print("\n🤖 Agent is thinking...")
                print("─" * 50)

                # Stream the agent's response to show its reasoning
                async for event in agent.astream_events(
                    {"messages": [("user", user_input)]},
                    version="v2"
                ):
                    event_type = event["event"]

                    # Show tool calls as they happen
                    if event_type == "on_tool_start":
                        tool_name = event["name"]
                        tool_input = event["data"].get("input", {})
                        print(f"\n🔧 Calling tool: {tool_name}")
                        print(f"   Input: {tool_input}")

                    # Show tool results
                    elif event_type == "on_tool_end":
                        output = event["data"].get("output", "")
                        # Truncate very long outputs
                        output_str = str(output)
                        if len(output_str) > 600:
                            print(f"   Output: {output_str[:600]}...")
                        else:
                            print(f"   Output: {output_str}")

                    # Show the final response
                    elif event_type == "on_chat_model_end":
                        output = event["data"].get("output")
                        if output and hasattr(output, "content"):
                            content = output.content
                            if content:
                                print(f"\n{'═' * 50}")
                                print(f"🤖 Agent: {content}")

                print("\n")

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                print("   Try again with a different query.\n")


async def run_demo():
    """
    Run a set of demo queries to showcase the agent's capabilities.
    """
    print_banner()

    if not check_api_keys():
        print("\n❌ Please set OPENAI_API_KEY in your .env file")
        return

    print("\n📡 Connecting to MCP servers...")

    async with MultiServerMCPClient(MCP_SERVERS) as mcp_client:
        print("✅ Connected!\n")

        tools = mcp_client.get_tools()
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        agent = create_react_agent(llm, tools)

        print("=" * 60)
        print("  DEMO MODE - Running Example Queries")
        print("=" * 60)

        # Run first 3 examples
        for i, query in enumerate(EXAMPLE_QUERIES[:3], 1):
            print(f"\n📝 Query {i}: {query}")
            print("─" * 50)

            try:
                result = await agent.ainvoke({"messages": [("user", query)]})
                final_msg = result["messages"][-1]
                print(f"\n🤖 Response:\n{final_msg.content}")
            except Exception as e:
                print(f"❌ Error: {str(e)}")

            print("\n" + "=" * 60)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        asyncio.run(run_demo())
    else:
        asyncio.run(run_agent())
