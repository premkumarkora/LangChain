# Streamlit Short-Term Memory Implementation Guide

## Overview
This application is a **Travel Planning Assistant** built with **Streamlit** and **LangChain**. It demonstrates the concept of **Short-Term Memory** (specifically *Conversation Buffer Memory*) in LLM applications. The agent remembers previous context (like locations "Paris" or "Tokyo") to answer follow-up questions effectively.

## Core Concepts

### 1. Conversation Buffer Memory
The core feature of this implementation is how it handles memory. Unlike stateless API calls, this application explicitly manages conversation history.
*   **Mechanism**: It maintains a growing list of `HumanMessage` and `AIMessage` objects in `st.session_state.memory_messages`.
*   **Context Passing**: For every new user input, the **entire** conversation history is passed to the LLM. This allows the model to "remember" what was discussed previously.
*   **Visual Debugging**: The sidebar ("Memory Buffer") displays this raw history, giving users a transparent view of what the AI "knows".

### 2. Tools & Capabilities
The agent is equipped with four specific tools to assist with travel planning:
*   **`web_search`**: Performs Google searches via **SerpAPI** for real-time information (attractions, restaurants).
*   **`get_weather`**: Fetches real-time and forecast weather data using the **Open-Meteo API**.
*   **`search_flights`**: Generates *simulated* flight data (prices, airlines, timings) for demonstration purposes.
*   **`search_hotels`**: Generates *simulated* hotel data (ratings, amenities, prices) for demonstration purposes.

### 3. Agent Architecture
*   **Model**: Uses `gpt-4o-mini` for fast and cost-effective responses.
*   **System Prompt**: Defines the persona ("Travel Planning Assistant") and explicitly instructs the model to use conversation history for context (e.g., resolving "there" to the previously mentioned city).
*   **Execution Loop**: A custom `run_agent` function handles the "ReAct-like" loop:
    1.  LLM decides to call a tool.
    2.  Code executes the tool.
    3.  Tool output is fed back to the LLM.
    4.  Repeat until the LLM generates a final answer.

## Key Files & Structure

*   **`streamlit_short_term_memory.py`**: The main entry point containing all logic.
    *   **Dependency Injection**: Loads API keys from `.env`.
    *   **Tool Definitions**: Decorator-based (`@tool`) definitions for agent capabilities.
    *   **UI Logic**: Streamlit calls for layout, sidebar, and chat interfaces.

## Implementation Flow Diagram

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#ff9a00', 'edgeLabelBackground':'#ffffff', 'tertiaryColor': '#fff0f0'}}}%%
graph TD
    subgraph UI [Streamlit User Interface]
        direction TB
        User((User)) -->|Input Query| Input[Chat Input]
        Input -->|Append| Session[st.session_state.messages]
        Sidebar[Sidebar Memory View] -.->|Reads| Session
    end

    subgraph Logic [Application Logic]
        direction TB
        Init[Initialize Agent] -->|Create| LLM[ChatOpenAI + Tools]
        Input -->|Pass History| AgentLoop{Run Agent Loop}
        
        AgentLoop -->|Thinking...| Decision[LLM Decision]
        
        Decision -- "Needs Info" --> ToolCall{{Execute Tool}}
        ToolCall -->|Web Search| API1[SerpAPI]
        ToolCall -->|Weather| API2[Open-Meteo API]
        ToolCall -->|Flights/Hotels| Mock[Mock Data Gen]
        
        API1 & API2 & Mock -->|Result| ToolOutput[Tool Output]
        ToolOutput -->|Feed Back| AgentLoop
        
        Decision -- "Final Answer" --> Response[Generate Response]
    end

    subgraph State [State Management]
        History[(Conversation History)]
        Response -->|Update| History
        History -->|Context for Next Turn| AgentLoop
    end

    Response -->|Display| UIOutput[Chat Message UI]
    
    style User fill:#2ecc71,stroke:#27ae60,color:white
    style Input fill:#3498db,stroke:#2980b9,color:white
    style AgentLoop fill:#9b59b6,stroke:#8e44ad,color:white
    style ToolCall fill:#e74c3c,stroke:#c0392b,color:white
    style API1 fill:#f1c40f,stroke:#f39c12,color:black
    style API2 fill:#f1c40f,stroke:#f39c12,color:black
    style Mock fill:#f1c40f,stroke:#f39c12,color:black
    style History fill:#34495e,stroke:#2c3e50,color:white
    style Response fill:#1abc9c,stroke:#16a085,color:white
```
