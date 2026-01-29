# LangChain Short-Term Memory (Conversation Buffer)

A comprehensive guide to implementing **ConversationBufferMemory** in LangChain with a practical travel planning agent example.

---

## Table of Contents

1. [What is Conversation Buffer Memory?](#what-is-conversation-buffer-memory)
2. [Why Do LLMs Need Memory?](#why-do-llms-need-memory)
3. [How Buffer Memory Works](#how-buffer-memory-works)
4. [Implementation Overview](#implementation-overview)
5. [Tools Implemented](#tools-implemented)
6. [Code Architecture](#code-architecture)
7. [Debug Output Guide](#debug-output-guide)
8. [Running the Demo](#running-the-demo)
9. [Key Concepts](#key-concepts)
10. [Trade-offs and Considerations](#trade-offs-and-considerations)

---

## What is Conversation Buffer Memory?

**ConversationBufferMemory** is the simplest form of memory in LangChain. It stores the **complete, unmodified conversation history** between the user and the AI assistant.

```
┌─────────────────────────────────────────────────────────────────┐
│                  CONVERSATION BUFFER MEMORY                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Message 1: User: "I want to visit Paris"                      │
│   Message 2: AI: "Paris is wonderful! Here are attractions..."  │
│   Message 3: User: "What's the weather there?"                  │
│   Message 4: AI: "The weather in Paris is 15°C..."              │
│   Message 5: User: "Find me flights"                            │
│   Message 6: AI: "Here are flights to Paris..."                 │
│   ... ALL messages stored ...                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Characteristics:
- **Complete History**: Every message is stored verbatim
- **No Compression**: Unlike summary memory, nothing is summarized or discarded
- **Full Context**: The LLM sees the entire conversation each time
- **Simple Implementation**: Easiest memory type to set up and understand

---

## Why Do LLMs Need Memory?

LLMs are **stateless by default** - they have no memory between API calls:

```
WITHOUT MEMORY:
┌──────────────────────────────────────────────────────────────┐
│ User: "My name is John"                                      │
│ AI: "Nice to meet you, John!"                                │
│                                                              │
│ [New API Call - Previous context is LOST]                    │
│                                                              │
│ User: "What's my name?"                                      │
│ AI: "I don't know your name."  ← LLM forgot everything!      │
└──────────────────────────────────────────────────────────────┘

WITH BUFFER MEMORY:
┌──────────────────────────────────────────────────────────────┐
│ User: "My name is John"                                      │
│ AI: "Nice to meet you, John!"                                │
│                                                              │
│ [Memory stores: User said "My name is John"]                 │
│                                                              │
│ User: "What's my name?"                                      │
│ AI: "Your name is John!"  ← Memory provides context!         │
└──────────────────────────────────────────────────────────────┘
```

### The Travel Planning Problem

In our travel planning agent, memory is essential:

```
User: "I'm thinking about visiting Paris"
       ↓
AI: [Searches for Paris attractions]
       ↓
User: "What's the weather THERE?"  ← "there" = Paris (from memory)
       ↓
AI: [Gets weather for Paris - remembered from context]
       ↓
User: "Find flights TO THERE"  ← Still remembers Paris
       ↓
AI: [Searches flights to Paris]
       ↓
User: "Hotels for THOSE DATES"  ← Remembers Paris AND dates
       ↓
AI: [Searches hotels in Paris for the mentioned dates]
```

Without memory, each "there" or "those dates" would be meaningless!

---

## How Buffer Memory Works

### Memory Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER MESSAGE                                │
│                    "What's the weather there?"                      │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CONVERSATION BUFFER                              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Human: I'm thinking about visiting Paris, France              │  │
│  │ AI: Paris is wonderful! Top attractions include...            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              +                                      │
│                    NEW MESSAGE APPENDED                             │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         LLM PROMPT                                  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ System: You are a travel planning assistant...                │  │
│  │                                                               │  │
│  │ CONVERSATION HISTORY:                                         │  │
│  │ Human: I'm thinking about visiting Paris, France              │  │
│  │ AI: Paris is wonderful! Top attractions include...            │  │
│  │                                                               │  │
│  │ USER INPUT: What's the weather there?                         │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LLM REASONING                                  │
│  "The user said 'there' - from conversation history,               │
│   I can see they mentioned Paris. I should get                      │
│   weather for Paris."                                               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      TOOL CALLED                                    │
│                   get_weather("Paris")                              │
└─────────────────────────────────────────────────────────────────────┘
```

### LangChain Memory Integration

```python
from langchain.memory import ConversationBufferMemory

# Create memory instance
memory = ConversationBufferMemory(
    memory_key="chat_history",    # Key used in prompt template
    return_messages=True,         # Return as message list (not string)
    output_key="output"           # Key for AI responses
)

# Memory automatically:
# 1. Stores each human message
# 2. Stores each AI response
# 3. Provides history to the agent on each call
```

---

## Implementation Overview

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                   │
│              "Find me hotels in Paris for June 15-22"               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AGENT EXECUTOR                                   │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              ConversationBufferMemory                         │  │
│  │  [Stores all previous messages for context]                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              ReAct Agent (GPT-4o-mini)                        │  │
│  │  [Reasons about which tool to use based on context]           │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   SERP API      │ │  Open-Meteo     │ │    Amadeus      │
│  (Web Search)   │ │   (Weather)     │ │ (Flights/Hotels)│
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### File Structure

```
langChain_memory_systems/
├── LangChain_Memory.md                 # General memory types overview
├── LangChain_short_term_memory.md      # This documentation
└── LangChain_short_term_memory.py      # Implementation (1000+ lines)
```

---

## Tools Implemented

### 1. SERP API (Web Search)

**Purpose**: Search the web for destination information, attractions, and travel advice.

```python
def serp_search(query: str) -> str:
    """
    Search the web using SerpAPI for destination information.

    Example:
        serp_search("top attractions in Paris France")

    Returns:
        Search results with titles and snippets
    """
```

**API Details**:
| Property | Value |
|----------|-------|
| Provider | SerpAPI |
| Endpoint | `https://serpapi.com/search` |
| Auth | API Key (SERP_API) |
| Free Tier | 100 searches/month |

---

### 2. Open-Meteo API (Weather)

**Purpose**: Get current weather and 7-day forecast for any location.

```python
def get_weather(location: str) -> str:
    """
    Get weather information using Open-Meteo API.

    Example:
        get_weather("Paris")

    Returns:
        Current conditions + 7-day forecast
    """
```

**API Details**:
| Property | Value |
|----------|-------|
| Provider | Open-Meteo |
| Endpoints | Geocoding + Weather Forecast |
| Auth | None required |
| Free Tier | 10,000 requests/day |

**Features**:
- Automatic geocoding (city name → coordinates)
- Current temperature, humidity, wind
- 7-day forecast with min/max temps
- Weather condition descriptions

---

### 3. Amadeus Flight Offers API

**Purpose**: Search for available flights between cities.

```python
def search_flights(
    origin: str,           # IATA code (e.g., "JFK")
    destination: str,      # IATA code (e.g., "CDG")
    departure_date: str,   # YYYY-MM-DD
    return_date: str,      # Optional, for round trips
    adults: int            # Number of passengers
) -> str:
```

**API Details**:
| Property | Value |
|----------|-------|
| Provider | Amadeus for Developers |
| Environment | Test (sandbox) |
| Auth | OAuth 2.0 (Client Credentials) |
| Endpoint | `https://test.api.amadeus.com/v2/shopping/flight-offers` |

**Authentication Flow**:
```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Client ID +    │ ──▶  │   Amadeus       │ ──▶  │  Access Token   │
│  Client Secret  │      │   Auth Server   │      │  (1799s TTL)    │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

---

### 4. Amadeus Hotel Search API

**Purpose**: Search for available hotels in a city.

```python
def search_hotels(
    city_code: str,        # IATA city code (e.g., "PAR")
    check_in_date: str,    # YYYY-MM-DD
    check_out_date: str,   # YYYY-MM-DD
    adults: int            # Number of guests
) -> str:
```

**API Details**:
| Property | Value |
|----------|-------|
| Provider | Amadeus for Developers |
| Environment | Test (sandbox) |
| Endpoints | Hotel List + Hotel Offers |

**Two-Step Process**:
```
Step 1: Get Hotel IDs        Step 2: Get Offers
┌─────────────────────┐      ┌─────────────────────┐
│ GET /hotels/by-city │ ──▶  │ GET /hotel-offers   │
│ cityCode=PAR        │      │ hotelIds=XXX,YYY    │
│                     │      │ checkInDate=...     │
└─────────────────────┘      └─────────────────────┘
```

---

## Code Architecture

### Core Components

```python
# 1. CONFIGURATION
SERP_API_KEY = os.getenv("SERP_API")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

# 2. LOGGING UTILITIES
def log_tool_call(tool_name, parameters, memory_context)
def log_tool_response(tool_name, response_summary)
def log_memory_state(memory)

# 3. AMADEUS AUTHENTICATION
def get_amadeus_token() -> str  # OAuth token with caching

# 4. TOOL IMPLEMENTATIONS
def serp_search(query) -> str
def get_weather(location) -> str
def search_flights(origin, destination, ...) -> str
def search_hotels(city_code, ...) -> str

# 5. LANGCHAIN TOOL DEFINITIONS
def create_tools() -> List[Tool]

# 6. AGENT SETUP
def create_agent_with_memory() -> (AgentExecutor, Memory)

# 7. CONVERSATION HANDLER
def chat_with_agent(agent_executor, memory, user_input) -> str

# 8. DEMO & INTERACTIVE MODES
def run_demo()
def interactive_mode()
```

### Memory Integration Code

```python
def create_agent_with_memory():
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Create tools
    tools = create_tools()

    # Create Conversation Buffer Memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="output"
    )

    # Create prompt with memory variable
    prompt = PromptTemplate(
        input_variables=["input", "chat_history", "tools", "tool_names", "agent_scratchpad"],
        template="""...
        CONVERSATION HISTORY:
        {chat_history}

        USER INPUT: {input}
        ..."""
    )

    # Create agent with memory
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,  # Memory attached here
        verbose=True
    )

    return agent_executor, memory
```

---

## Debug Output Guide

The implementation includes comprehensive logging. Here's how to read it:

### Log Markers

| Marker | Meaning |
|--------|---------|
| `[TOOL CALLED]` | Which tool is being invoked |
| `[PARAMETERS]` | Exact parameters passed to the tool |
| `[MEMORY CONTEXT]` | Relevant context from conversation history |
| `[TOOL RESPONSE]` | Summary of what the tool returned |
| `[MEMORY STATE]` | Full conversation buffer contents |
| `[PRE-PROCESSING]` | Memory state BEFORE handling message |
| `[POST-PROCESSING]` | Memory state AFTER handling message |

### Example Debug Output

```
######################################################################
USER: What's the weather there?
######################################################################

[PRE-PROCESSING] Memory state before handling this message:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
[MEMORY STATE] - Conversation Buffer Contents:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Human: I'm thinking about visiting Paris, France. What are the top attractions?
AI: Paris has many wonderful attractions! The top ones include the Eiffel Tower...
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

======================================================================
[TOOL CALLED]: Open-Meteo API (Weather)
[PARAMETERS]: {
  "location": "Paris"
}
[MEMORY CONTEXT]: Getting weather for location: Paris
----------------------------------------------------------------------
[TOOL RESPONSE]: Weather data retrieved for Paris
======================================================================

[POST-PROCESSING] Memory state after handling this message:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
[MEMORY STATE] - Conversation Buffer Contents:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Human: I'm thinking about visiting Paris, France. What are the top attractions?
AI: Paris has many wonderful attractions! The top ones include the Eiffel Tower...
Human: What's the weather there?
AI: The current weather in Paris is 15°C with partly cloudy skies...
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

######################################################################
ASSISTANT: The current weather in Paris is 15°C with partly cloudy skies...
######################################################################
```

---

## Running the Demo

### Prerequisites

1. **Environment Variables** (in `.env` file):
```env
SERP_API=your_serpapi_key
OPENAI_API_KEY=your_openai_key
AMADEUS_API_KEY=your_amadeus_key
AMADEUS_API_SECRET=your_amadeus_secret
```

2. **Dependencies**:
```bash
pip install langchain langchain-openai python-dotenv requests
```

### Running

```bash
# Demo mode (automated 4-step conversation)
cd /Volumes/vibecoding/LangChain/langChain_memory_systems
python LangChain_short_term_memory.py

# Interactive mode (chat with the agent)
python LangChain_short_term_memory.py --interactive
```

### Demo Conversation Flow

```
MESSAGE 1/4: "I'm thinking about visiting Paris, France. What are the top attractions?"
├── Tool: SERP API (web_search)
├── Action: Searches for Paris attractions
└── Memory: Stores question and answer

MESSAGE 2/4: "What's the weather like there right now?"
├── Tool: Open-Meteo (get_weather)
├── Action: Gets weather for "Paris" (remembered from context)
└── Memory: "there" resolved to Paris using conversation history

MESSAGE 3/4: "Can you find flights from New York to there for June 15-22?"
├── Tool: Amadeus Flight API (search_flights)
├── Action: Searches JFK → CDG for specified dates
└── Memory: "there" = Paris, dates stored for later

MESSAGE 4/4: "Great! Now can you find me some hotels there for those same dates?"
├── Tool: Amadeus Hotel API (search_hotels)
├── Action: Searches hotels in PAR for June 15-22
└── Memory: "there" = Paris, "those dates" = June 15-22
```

---

## Key Concepts

### 1. Implicit Reference Resolution

The agent uses memory to resolve implicit references:

| User Says | Agent Understands |
|-----------|-------------------|
| "there" | Paris (from earlier message) |
| "that city" | Paris (from context) |
| "those dates" | June 15-22 (from flight search) |
| "the same hotel" | Previously mentioned hotel |

### 2. Context Accumulation

```
Message 1: Context = {}
Message 2: Context = {destination: Paris}
Message 3: Context = {destination: Paris, dates: June 15-22, travelers: 1}
Message 4: Context = {destination: Paris, dates: June 15-22, travelers: 1, ...}
```

### 3. ReAct Pattern with Memory

```
User: "What's the weather there?"
                │
                ▼
┌─────────────────────────────────────────────┐
│ THOUGHT: User said "there". Looking at      │
│ conversation history, they mentioned Paris. │
│ I should get weather for Paris.             │
└─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│ ACTION: get_weather                         │
│ ACTION INPUT: Paris                         │
└─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│ OBSERVATION: Weather for Paris: 15°C...     │
└─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│ FINAL ANSWER: The weather in Paris is...    │
└─────────────────────────────────────────────┘
```

---

## Trade-offs and Considerations

### Buffer Memory: Pros and Cons

| Pros | Cons |
|------|------|
| Complete context available | Token usage grows linearly |
| Simple implementation | Expensive for long conversations |
| Perfect recall | May hit context limits |
| No information loss | Slower processing over time |

### When to Use Buffer Memory

**Good for:**
- Short conversations (< 50 messages)
- When every detail matters
- Prototyping and testing
- When cost isn't a concern

**Consider alternatives for:**
- Long conversations → Use Summary Memory
- Cross-session memory → Use Vector Memory
- Cost optimization → Use Window Memory

### Token Usage Comparison

```
Conversation Length    Buffer Memory Tokens    Summary Memory Tokens
──────────────────────────────────────────────────────────────────
10 messages            ~2,000 tokens           ~500 tokens
50 messages            ~10,000 tokens          ~800 tokens
100 messages           ~20,000 tokens          ~1,000 tokens
500 messages           ~100,000 tokens         ~1,500 tokens
                       (may exceed limit!)
```

### Memory Type Selection Guide

```
                    ┌─────────────────────────────┐
                    │  How long is conversation?  │
                    └─────────────┬───────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
        Short (<50)         Medium (50-200)      Long (>200)
              │                   │                   │
              ▼                   ▼                   ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │  Buffer Memory  │  │  Summary Memory │  │  Vector Memory  │
    │  (This guide)   │  │                 │  │                 │
    └─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## API Reference

### IATA Codes Used

**Airport Codes**:
| City | Airport | Code |
|------|---------|------|
| New York | JFK International | JFK |
| New York | LaGuardia | LGA |
| New York | Newark | EWR |
| Paris | Charles de Gaulle | CDG |
| London | Heathrow | LHR |
| Tokyo | Narita | NRT |
| Los Angeles | LAX | LAX |

**City Codes** (for hotels):
| City | Code |
|------|------|
| Paris | PAR |
| New York | NYC |
| London | LON |
| Tokyo | TYO |

---

## Summary

This implementation demonstrates:

1. **ConversationBufferMemory** stores complete conversation history
2. **Memory enables context** - agent can understand "there", "those dates", etc.
3. **ReAct pattern** - agent reasons about which tool to use
4. **Multi-tool coordination** - 4 different APIs working together
5. **Verbose logging** - see exactly what's happening with memory and tools

The travel planning agent shows how short-term memory is essential for natural, context-aware conversations where users don't want to repeat themselves.

---

## Next Steps

- Learn about **Summary Memory** for longer conversations
- Explore **Vector Memory** for cross-session persistence
- Combine memory types for optimal performance
- Add more tools (currency conversion, visa requirements, etc.)
