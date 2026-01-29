# LangChain + MCP Tutorial (FREE APIs!)

A complete, production-ready example demonstrating how to build LangChain agents that connect to multiple MCP (Model Context Protocol) servers using **completely FREE APIs**.

## What You'll Learn

- What MCP is and why it's useful
- How to create MCP servers with FastMCP
- How to connect LangChain agents to multiple MCP servers
- Best practices for modular AI tool systems

## APIs Used (All FREE!)

| Service | Purpose | API Key Needed? | Free Tier |
|---------|---------|-----------------|-----------|
| **Open-Meteo** | Weather data | **No!** | 10,000 req/day |
| **NewsData.io** | News articles | Yes (free signup) | 200 req/day |
| **OpenAI** | LLM (gpt-4o-mini) | Yes | $5 free credits |

## Project Structure

```
langChain_MCP/
├── weather_server.py      # MCP Server: Weather (Open-Meteo - FREE!)
├── news_server.py         # MCP Server: News (NewsData.io - FREE tier)
├── utils_server.py        # MCP Server: Calculator, Time (NO API!)
├── agent_main.py          # LangChain agent using all servers
├── without_mcp_example.py # Comparison: Same thing WITHOUT MCP
├── requirements.txt       # Python dependencies
├── .env.example          # API key template
├── .gitignore            # Prevents committing secrets
└── README.md             # This file
```

## Quick Start (5 Minutes!)

### 1. Navigate to the project

```bash
cd langChain_MCP
```

### 2. Create virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate    # macOS/Linux
# OR: venv\Scripts\activate  # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get your API keys

#### OpenAI (Required)
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign up or sign in
3. Create a new API key
4. Copy the key

#### NewsData.io (Optional but recommended)
1. Go to [NewsData.io](https://newsdata.io/register)
2. Sign up with your email
3. Verify your email
4. Copy your API key from the dashboard

#### Open-Meteo (Weather)
**No API key needed!** It just works!

### 5. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```env
OPENAI_API_KEY=sk-your-openai-key-here
NEWSDATA_API_KEY=your-newsdata-key-here  # Optional
```

### 6. Run the agent!

```bash
python agent_main.py
```

## Example Queries

Try these to see the agent use multiple tools:

```
"What's the weather in London and find any news about UK weather?"
```
→ Uses: `get_weather` + `search_news`

```
"Get the 5-day forecast for Tokyo and search for technology news"
```
→ Uses: `get_forecast` + `search_news`

```
"What time is it in New York and what's the weather there?"
```
→ Uses: `get_current_time` + `get_weather`

```
"Calculate 15% of 299.99"
```
→ Uses: `calculate`

## Understanding MCP

### What is MCP?

**Model Context Protocol (MCP)** is a standard way to connect AI models to external tools. Think of it as a "USB for AI" - a universal interface that works with any MCP-compatible system.

### Architecture

```
    ┌─────────────────────────────────────────────────────────────┐
    │                     Your Question                           │
    │     "What's the weather in London and find UK news?"        │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                 LangChain ReAct Agent                       │
    │                   (gpt-4o-mini)                             │
    │                                                             │
    │  Thinks: "I need weather AND news tools"                    │
    │  Acts: Calls appropriate MCP servers                        │
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
    │               │ │               │ │               │
    │ • get_weather │ │ • search_news │ │ • calculate   │
    │ • get_forecast│ │ • headlines   │ │ • time        │
    └───────┬───────┘ └───────┬───────┘ └───────────────┘
            │                 │                 │
            ▼                 ▼                 │
    ┌───────────────┐ ┌───────────────┐        │
    │  Open-Meteo   │ │ NewsData.io   │   (Local)
    │    (FREE!)    │ │  (FREE tier)  │
    └───────────────┘ └───────────────┘
```

### Why Use MCP?

| Without MCP | With MCP |
|-------------|----------|
| All tools in one file | Tools in separate servers |
| Hard to maintain | Easy to maintain |
| Can't reuse tools | Tools reusable anywhere |
| Adding tools = big changes | Adding tools = 1 config line |

### Comparison: See It Yourself!

Run the non-MCP version to compare:

```bash
python without_mcp_example.py
```

Notice how much more code is needed when everything is in one file!

## Available Tools

### Weather Server (Open-Meteo - FREE!)

| Tool | Description |
|------|-------------|
| `get_weather(city)` | Current weather for a city |
| `get_forecast(city, days)` | Multi-day weather forecast |
| `get_weather_by_coordinates(lat, lon)` | Weather for exact coordinates |

### News Server (NewsData.io - 200 free/day)

| Tool | Description |
|------|-------------|
| `search_news(query)` | Search for news articles |
| `get_headlines(category, country)` | Top headlines by category |
| `get_news_by_country(country, topic)` | Country-specific news |

### Utils Server (No API needed!)

| Tool | Description |
|------|-------------|
| `calculate(expression)` | Safe math evaluation |
| `get_current_time(timezone)` | Current time anywhere |
| `convert_timezone(time, from, to)` | Timezone conversion |
| `convert_temperature(val, from, to)` | Temperature conversion |

## Adding Your Own MCP Server

One of MCP's key benefits is how easy it is to add new servers!

### Step 1: Create your server file

```python
# my_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
async def my_tool(param: str) -> str:
    """Description of what this tool does."""
    return f"Result for {param}"

if __name__ == "__main__":
    mcp.run()
```

### Step 2: Add ONE line to the agent config

In `agent_main.py`:

```python
MCP_SERVERS = {
    "weather": {...},
    "news": {...},
    "utils": {...},
    # Just add this:
    "myserver": {
        "command": "python",
        "args": ["my_server.py"],
        "transport": "stdio",
    },
}
```

That's it! The agent automatically discovers and uses your new tools.

## Troubleshooting

### "OPENAI_API_KEY not set"

- Make sure you created `.env` from `.env.example`
- Check that you added your actual API key
- Don't use quotes around the key value

### "NEWSDATA_API_KEY not set"

- This is optional - weather and utils tools still work
- Get your free key at: https://newsdata.io/register

### Weather tools not working

- Open-Meteo doesn't need an API key
- Check your internet connection
- Try a well-known city like "London" or "Tokyo"

### Import errors

- Make sure you activated your virtual environment
- Run `pip install -r requirements.txt` again

### MCP server won't start

- Check Python is in your PATH
- Verify all files exist in the same directory
- Check for syntax errors with `python weather_server.py`

## API Documentation Links

- **Open-Meteo**: https://open-meteo.com/en/docs
- **NewsData.io**: https://newsdata.io/documentation
- **MCP Specification**: https://spec.modelcontextprotocol.io/
- **LangChain MCP**: https://python.langchain.com/docs/integrations/tools/mcp

## License

MIT License - Use freely for learning and building!

---

## Architecture Diagram

```mermaid
flowchart TB
    subgraph USER["👤 USER LAYER"]
        Q[/"🎯 User Query<br/>'What's the weather in London<br/>and find UK news?'"/]
    end

    subgraph AGENT["🤖 LANGCHAIN AGENT LAYER"]
        LLM["🧠 LangChain ReAct Agent<br/>(gpt-4o-mini)<br/>Thinks → Acts → Observes"]
    end

    subgraph ADAPTER["🔌 MCP ADAPTER LAYER"]
        MCP["⚡ langchain-mcp-adapters<br/>Routes requests to correct server"]
    end

    subgraph SERVERS["🖥️ MCP SERVERS LAYER"]
        direction LR
        subgraph WS["☀️ Weather Server"]
            W1["get_weather(city)"]
            W2["get_forecast(city, days)"]
            W3["get_weather_by_coords(lat, lon)"]
        end
        subgraph NS["📰 News Server"]
            N1["search_news(query)"]
            N2["get_headlines(category)"]
            N3["get_news_by_country(country)"]
        end
        subgraph US["🛠️ Utils Server"]
            U1["calculate(expression)"]
            U2["get_current_time(tz)"]
            U3["convert_temperature()"]
        end
    end

    subgraph APIS["🌐 EXTERNAL APIs"]
        direction LR
        API1[("🌤️ Open-Meteo<br/>FREE!<br/>No API Key")]
        API2[("📡 NewsData.io<br/>FREE Tier<br/>200 req/day")]
        API3[("💻 Local<br/>No API<br/>Needed")]
    end

    subgraph RESPONSE["✅ RESPONSE LAYER"]
        R[/"📋 Final Answer<br/>'London is 15°C with rain.<br/>Here are the UK news...'"/]
    end

    Q --> LLM
    LLM <--> MCP
    MCP <--> WS
    MCP <--> NS
    MCP <--> US
    WS --> API1
    NS --> API2
    US --> API3
    API1 --> MCP
    API2 --> MCP
    API3 --> MCP
    LLM --> R

    style Q fill:#3B82F6,color:#fff,stroke:#1D4ED8,stroke-width:3px
    style LLM fill:#F97316,color:#fff,stroke:#C2410C,stroke-width:3px
    style MCP fill:#8B5CF6,color:#fff,stroke:#6D28D9,stroke-width:3px
    style WS fill:#06B6D4,color:#fff,stroke:#0891B2,stroke-width:2px
    style NS fill:#EC4899,color:#fff,stroke:#BE185D,stroke-width:2px
    style US fill:#10B981,color:#fff,stroke:#059669,stroke-width:2px
    style API1 fill:#22D3EE,color:#000,stroke:#06B6D4,stroke-width:2px
    style API2 fill:#F472B6,color:#000,stroke:#EC4899,stroke-width:2px
    style API3 fill:#34D399,color:#000,stroke:#10B981,stroke-width:2px
    style R fill:#84CC16,color:#000,stroke:#65A30D,stroke-width:3px
    style USER fill:#EFF6FF,stroke:#3B82F6,stroke-width:2px
    style AGENT fill:#FFF7ED,stroke:#F97316,stroke-width:2px
    style ADAPTER fill:#F5F3FF,stroke:#8B5CF6,stroke-width:2px
    style SERVERS fill:#F0FDFA,stroke:#14B8A6,stroke-width:2px
    style APIS fill:#ECFDF5,stroke:#10B981,stroke-width:2px
    style RESPONSE fill:#F7FEE7,stroke:#84CC16,stroke-width:2px
```

### Diagram Legend

| Layer | Color | Description |
|-------|-------|-------------|
| 🔵 **User Layer** | Blue | Your natural language question to the agent |
| 🟠 **Agent Layer** | Orange | LangChain ReAct Agent powered by gpt-4o-mini |
| 🟣 **Adapter Layer** | Purple | langchain-mcp-adapters routes to correct servers |
| 🔷 **Weather Server** | Cyan | MCP server for weather tools (Open-Meteo) |
| 🩷 **News Server** | Pink | MCP server for news tools (NewsData.io) |
| 🟢 **Utils Server** | Green | MCP server for utilities (local, no API) |
| 🟩 **Response** | Lime | Final combined answer from the agent |

### Data Flow

1. **User** sends a natural language query
2. **LangChain Agent** reasons about which tools are needed
3. **MCP Adapter** routes requests to appropriate MCP servers
4. **MCP Servers** call their respective APIs or perform local operations
5. **Results** flow back through the adapter to the agent
6. **Agent** combines all results into a coherent final answer

---

**Happy coding!** 🚀

If this helped you understand MCP, consider starring the repo!
