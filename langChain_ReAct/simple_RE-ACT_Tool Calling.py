from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

# Define some tools for the agent to use
@tool
def get_weather(city: str) -> str:
    """Get the current weather for a given city."""
    # This is a mock function - in reality, you'd call a weather API
    weather_data = {
        "paris": "15°C and sunny",
        "london": "12°C and rainy",
        "new york": "8°C and cloudy"
    }
    return weather_data.get(city.lower(), "Weather data not available")

@tool
def calculate(expression: str) -> str:
    """Calculate a mathematical expression. Example: '2 + 2' or '10 * 5'"""
    try:
        result = eval(expression)
        return f"The result is: {result}"
    except Exception as e:
        return f"Error calculating: {str(e)}"

# Add tools to the list
tools = [get_weather, calculate]

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
agent_executor = create_react_agent(llm, tools)

# Interactive loop for user queries
while True:
    query = input("\nEnter your query (or 'quit' to exit): ")
    if query.lower() in ('quit', 'exit', 'q'):
        break

    print("\n" + "=" * 50)
    for chunk in agent_executor.stream({"messages": [("user", query)]}):
        # Check for agent messages (tool calls or final response)
        if "agent" in chunk:
            for msg in chunk["agent"]["messages"]:
                # Check if agent is calling a tool
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        print(f"\n[Calling Tool]: {tool_call['name']}")
                        print(f"[Input]: {tool_call['args']}")
                # Check for final response
                elif hasattr(msg, "content") and msg.content:
                    print(f"\n[Final Answer]: {msg.content}")

        # Check for tool responses
        if "tools" in chunk:
            for msg in chunk["tools"]["messages"]:
                print(f"[Tool Output]: {msg.content}")

    print("=" * 50)