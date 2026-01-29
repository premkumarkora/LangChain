# CLAUDE.md - AI Assistant Guide for LangChain ReAct Agent Project

## Project Overview

This is a **LangChain ReAct (Reasoning + Acting) Agent** example project that demonstrates how to build AI agents using LangChain and LangGraph with OpenAI's language models.

**Purpose:** Provides a minimal working example of a ReAct agent with streaming capabilities for observing agent reasoning in real-time.

## Repository Structure

```
/home/user/LangChain/
├── main.py              # Simple entry point with hello message
├── re_act_example.py    # Core ReAct agent implementation
├── pyproject.toml       # Project metadata and dependencies
├── uv.lock              # Locked dependency versions
├── .python-version      # Python version specification (3.12)
├── .gitignore           # Git exclusion rules
├── README.md            # Project documentation (empty)
└── CLAUDE.md            # This file
```

## Key Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ | Runtime |
| langchain-openai | >=1.1.7 | OpenAI integration for LangChain |
| langgraph | >=1.0.7 | Graph-based agent workflow orchestration |
| dotenv | >=0.9.9 | Environment variable management |
| uv | - | Package manager (fast Python installer) |

## Development Setup

### Prerequisites
- Python 3.12 or higher
- `uv` package manager (recommended) or `pip`
- OpenAI API key

### Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### Environment Configuration

Create a `.env` file in the project root with required API keys:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

**Important:** The `.env` file is gitignored and should never be committed.

## Running the Project

```bash
# Run the main entry point
python main.py

# Run the ReAct agent example
python re_act_example.py
```

## Code Architecture

### ReAct Agent Pattern (`re_act_example.py`)

The project uses LangGraph's prebuilt `create_react_agent` function:

1. **Environment Loading:** Uses `python-dotenv` to load API keys from `.env`
2. **LLM Initialization:** Creates a `ChatOpenAI` instance with `gpt-4o-mini` model at temperature 0 (deterministic)
3. **Agent Creation:** Uses `create_react_agent(llm, tools)` to build the agent
4. **Streaming Execution:** Processes responses via `.stream()` for real-time output

### Code Flow
```
load_dotenv() → Define tools → Initialize LLM → Create agent → Stream responses
```

## Coding Conventions

### Style Guidelines
- Use Python 3.12+ syntax and features
- Place imports at the top of files
- Load environment variables early using `load_dotenv()`
- Prefer functional patterns over classes for simple use cases
- Use zero temperature for deterministic LLM outputs when consistency is needed

### File Organization
- Keep related functionality in single files for simplicity
- Entry points should be clearly named (`main.py`, `*_example.py`)
- Configuration in `pyproject.toml`, secrets in `.env`

### Import Order
1. Standard library imports
2. Third-party imports (langchain, langgraph, etc.)
3. Local imports
4. Environment setup (`load_dotenv()`)

## Adding New Features

### Adding Tools to the Agent

To extend the agent with custom tools, modify `re_act_example.py`:

```python
from langchain_core.tools import tool

@tool
def my_custom_tool(input: str) -> str:
    """Description of what this tool does."""
    return f"Processed: {input}"

tools = [my_custom_tool]  # Add tool to the list
```

### Creating New Agent Examples

1. Create a new file with descriptive name (e.g., `search_agent_example.py`)
2. Follow the same pattern: load env, define tools, create agent, stream
3. Document the purpose at the top of the file

## Dependencies

### Adding Dependencies

```bash
# Using uv
uv add package-name

# This automatically updates pyproject.toml and uv.lock
```

### Key Dependency Notes

- **langchain-openai:** Provides `ChatOpenAI` and OpenAI embeddings
- **langgraph:** Provides `create_react_agent` and workflow orchestration
- **langgraph-prebuilt:** Contains pre-built agent templates
- **dotenv:** Handles `.env` file loading

## Testing

**Note:** No test framework is currently configured. When adding tests:

1. Add pytest to dev dependencies: `uv add --dev pytest`
2. Create a `tests/` directory
3. Name test files with `test_` prefix
4. Run with `pytest`

## Common Tasks

### Modifying the LLM Model

In `re_act_example.py`, change the model parameter:

```python
llm = ChatOpenAI(model="gpt-4o", temperature=0)  # Use GPT-4o instead
```

### Adjusting Agent Behavior

- **Temperature:** 0 for deterministic, 0.7-1.0 for creative responses
- **Model:** `gpt-4o-mini` (fast/cheap) vs `gpt-4o` (more capable)

### Debugging Agent Reasoning

The streaming loop shows agent thought process:
```python
for chunk in agent_executor.stream({"messages": [...]}):
    print(chunk)  # Shows intermediate steps and reasoning
```

## Git Workflow

- **Main development branch:** Follow project's branch naming conventions
- **Commits:** Use descriptive commit messages
- **Never commit:** `.env`, API keys, or secrets

## Troubleshooting

### Common Issues

1. **Missing API Key:** Ensure `.env` file exists with `OPENAI_API_KEY`
2. **Import Errors:** Run `uv sync` to install dependencies
3. **Python Version:** Ensure Python 3.12+ is being used (check with `python --version`)

### Environment Variables Not Loading

Ensure `load_dotenv()` is called before using environment variables:
```python
from dotenv import load_dotenv
load_dotenv()  # Must be called before accessing os.environ
```

## Project Status

This is an **early-stage example project** with:
- Basic ReAct agent implementation
- No production features (logging, error handling, etc.)
- No test suite
- Minimal documentation

## Future Development Areas

Potential areas for expansion:
- Adding custom tools (web search, calculator, file operations)
- Implementing memory/conversation history
- Adding error handling and logging
- Creating multi-agent workflows
- Building a CLI or web interface
