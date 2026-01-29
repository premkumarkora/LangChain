# LangChain Learning Repository

A comprehensive collection of tutorials and examples for learning LangChain concepts, from basic agent patterns to advanced memory systems.

---

## Project Structure

```
LangChain/
├── CLAUDE.md                          # This file - Project overview
├── langChain_MCP/                     # MCP (Model Context Protocol) Tutorial
│   ├── README.md                      # Complete MCP guide with diagrams
│   ├── without_mcp_example.md         # Traditional approach comparison
│   ├── agent_main.py                  # LangChain agent using MCP servers
│   ├── without_mcp_example.py         # Same agent WITHOUT MCP (for comparison)
│   ├── weather_server.py              # MCP Server: Weather (Open-Meteo)
│   ├── news_server.py                 # MCP Server: News (NewsData.io)
│   └── utils_server.py                # MCP Server: Calculator, Time
├── langChain_ReAct/                   # ReAct Pattern Tutorial
│   ├── simple_RE-ACT_Tool Calling.md  # ReAct pattern explanation
│   └── simple_RE-ACT_Tool Calling.py  # Simple ReAct implementation
├── langChain_memory_systems/          # Memory Systems Tutorial
│   └── LangChain_Memory.md            # Complete guide to memory types
├── .env                               # API keys (not committed)
├── main.py                            # Entry point
└── pyproject.toml                     # Project dependencies
```

---

## Modules Overview

### 1. LangChain MCP (`langChain_MCP/`)

**What you'll learn:**
- What MCP (Model Context Protocol) is and why it's useful
- How to create MCP servers with FastMCP
- How to connect LangChain agents to multiple MCP servers
- Best practices for modular AI tool systems

**Key Concepts:**
- MCP = "USB for AI" - a universal interface for tools
- Separates tools into independent, reusable servers
- Auto-discovery of tools from connected servers

**Files:**
| File | Description |
|------|-------------|
| `agent_main.py` | LangChain ReAct agent connecting to 3 MCP servers |
| `without_mcp_example.py` | Same functionality without MCP (monolithic approach) |
| `weather_server.py` | MCP server for weather tools (Open-Meteo API - FREE) |
| `news_server.py` | MCP server for news tools (NewsData.io - FREE tier) |
| `utils_server.py` | MCP server for utilities (calculator, time - no API) |

**APIs Used (All FREE):**
| Service | Purpose | API Key? | Free Tier |
|---------|---------|----------|-----------|
| Open-Meteo | Weather data | No | 10,000 req/day |
| NewsData.io | News articles | Yes | 200 req/day |
| OpenAI | LLM (gpt-4o-mini) | Yes | $5 free credits |

---

### 2. ReAct Pattern (`langChain_ReAct/`)

**What you'll learn:**
- What ReAct (Reason + Act) pattern is
- How LLMs reason about tool usage
- How tool calling works in LangChain
- Multi-tool parallel execution

**The ReAct Loop:**
```
User Query → LLM Reasons → Tool Called → Tool Returns → LLM Formulates Answer
```

**Key Concepts:**
- **Reason**: LLM decides which tool(s) to use
- **Act**: LLM generates tool calls with arguments
- **Observe**: LLM receives tool results
- **Respond**: LLM synthesizes final answer

**Example Flow:**
```
Query: "What is weather in Paris?"

1. LLM Reasons: "I need to call get_weather"
2. Tool Called: get_weather("paris")
3. Tool Returns: "15°C and sunny"
4. LLM Responds: "The weather in Paris is 15°C and sunny."
```

---

### 3. Memory Systems (`langChain_memory_systems/`)

**What you'll learn:**
- Why LLMs need memory (they're stateless by default!)
- Three types of memory and when to use each
- Trade-offs between cost, context, and retrieval

**The Core Problem:**
```
Without Memory:
User: "My name is John"
AI: "Nice to meet you!"
User: "What's my name?"
AI: "I don't know" 😕  ← LLMs forget everything between calls!
```

**Memory Types:**

| Type | Analogy | Best For |
|------|---------|----------|
| **Buffer Memory** | Open book test | Short conversations (<50 messages) |
| **Summary Memory** | Study notes | Long conversations, need full context |
| **Vector Memory** | Ctrl+F search | Long-term memory across sessions |

**Quick Comparison:**
```
Buffer Memory:  [All 1000 messages] → $$$$ cost
Summary Memory: [Summary] + [Last 10 messages] → $$ cost
Vector Memory:  [Only relevant messages found by search] → $ cost
```

---

## Quick Start

### 1. Setup Environment

```bash
cd /Volumes/vibecoding/LangChain
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # or use uv
```

### 2. Configure API Keys

Create `.env` file:
```env
OPENAI_API_KEY=sk-your-key-here
NEWSDATA_API_KEY=your-newsdata-key-here  # Optional
```

### 3. Run Examples

```bash
# MCP Agent
cd langChain_MCP
python agent_main.py

# Traditional Agent (comparison)
python without_mcp_example.py

# ReAct Example
cd ../langChain_ReAct
python "simple_RE-ACT_Tool Calling.py"
```

---

## Learning Path

**Recommended order:**

1. **Start with ReAct** (`langChain_ReAct/`)
   - Understand the basic Reason + Act pattern
   - See how tools are called and results processed

2. **Learn Memory Systems** (`langChain_memory_systems/`)
   - Understand why memory matters
   - Learn the three types and their trade-offs

3. **Master MCP** (`langChain_MCP/`)
   - Compare traditional vs MCP approaches
   - Build modular, reusable tool systems

---

## Key Diagrams

### MCP Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     Your Question                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 LangChain ReAct Agent                       │
│                   (gpt-4o-mini)                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│               langchain-mcp-adapters                        │
│            (Routes to correct server)                       │
└───────┬─────────────────┬─────────────────┬─────────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│    Weather    │ │     News      │ │    Utils      │
│  MCP Server   │ │  MCP Server   │ │  MCP Server   │
└───────────────┘ └───────────────┘ └───────────────┘
```

### ReAct Pattern
```
User Query
    │
    ▼
┌─────────────────┐
│   LLM Reasons   │  ← "I need to call get_weather"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Tool Called   │  ← get_weather("paris")
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Tool Returns   │  ← "15°C and sunny"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LLM Formulates  │  ← "The weather in Paris is 15°C and sunny"
│  Final Answer   │
└─────────────────┘
```

### Memory Comparison
```
Buffer:  [Msg1][Msg2][Msg3]...[Msg1000] → All to LLM ($$$)
Summary: [Summary of 1-990] + [991-1000] → Compressed ($$)
Vector:  [Search] → [Relevant msgs only] → Minimal ($)
```

---

## Technologies Used

- **LangChain** - Framework for building LLM applications
- **LangGraph** - State machines and agent orchestration
- **FastMCP** - Framework for building MCP servers
- **OpenAI GPT-4o-mini** - Language model
- **Open-Meteo** - Free weather API
- **NewsData.io** - Free news API

---

## Resources

- [LangChain Documentation](https://python.langchain.com/docs/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [LangGraph Guide](https://langchain-ai.github.io/langgraph/)
- [Open-Meteo API](https://open-meteo.com/en/docs)
- [NewsData.io API](https://newsdata.io/documentation)
