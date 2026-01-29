"""
LangChain Agent WITHOUT MCP (For Comparison)
=============================================

This file shows what building a multi-tool LangChain agent looks like
WITHOUT using MCP (Model Context Protocol).

PURPOSE:
────────
Compare this file with agent_main.py to see:
1. How much more code is needed to define tools directly
2. The maintenance burden of managing all tools in one file
3. Why MCP's modular approach is beneficial

KEY DIFFERENCES:
────────────────

┌─────────────────────────────────────────────────────────────────┐
│             WITHOUT MCP (this file)                             │
├─────────────────────────────────────────────────────────────────┤
│ • ~350 lines for 6 tools                                        │
│ • All tools defined in ONE giant file                           │
│ • All API calls inline with tool logic                          │
│ • Adding tools = modify this file                               │
│ • Can't easily share tools between projects                     │
│ • Everything tightly coupled                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│             WITH MCP (agent_main.py)                            │
├─────────────────────────────────────────────────────────────────┤
│ • ~150 lines of agent code                                      │
│ • Tools in SEPARATE server files                                │
│ • Clean separation of concerns                                  │
│ • Adding tools = new server file + 1 config line                │
│ • Tools reusable across projects                                │
│ • Loosely coupled, modular architecture                         │
└─────────────────────────────────────────────────────────────────┘

IMPORTANT: This file is for EDUCATIONAL comparison only.
The MCP approach (agent_main.py) is recommended for real projects.

To run this example:
    python without_mcp_example.py
"""

import os
import math
import httpx
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# Load environment variables
load_dotenv()

# API configurations (all in one place - harder to manage!)
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "")


# =============================================================================
# WEATHER TOOLS (Would be in weather_server.py with MCP)
# Notice: All this code would be in a separate file with MCP!
# =============================================================================

WEATHER_CODES = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 95: "Thunderstorm"
}


async def _geocode_city(city: str) -> tuple | None:
    """Geocode a city name to coordinates (inline helper)."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "en"},
                timeout=10.0
            )
            if response.status_code != 200:
                return None
            results = response.json().get("results", [])
            if not results:
                return None
            loc = results[0]
            return (loc["latitude"], loc["longitude"], loc["name"], loc.get("country", ""))
    except:
        return None


@tool
async def get_weather(city: str) -> str:
    """
    Get current weather for a city using Open-Meteo API.

    Args:
        city: Name of the city
    """
    print(f"\n🌤️  [Direct Tool] get_weather({city})")

    geo = await _geocode_city(city)
    if not geo:
        return f"Error: Could not find city '{city}'"

    lat, lon, name, country = geo

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": ["temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m"],
                    "timezone": "auto"
                },
                timeout=10.0
            )

            if response.status_code != 200:
                return f"Error: API returned {response.status_code}"

            data = response.json()
            current = data.get("current", {})
            temp = current.get("temperature_2m", "N/A")
            humidity = current.get("relative_humidity_2m", "N/A")
            code = current.get("weather_code", 0)
            wind = current.get("wind_speed_10m", "N/A")

            return f"Weather for {name}, {country}: {temp}°C, {WEATHER_CODES.get(code, 'Unknown')}, Humidity: {humidity}%, Wind: {wind} km/h"

    except Exception as e:
        return f"Error: {str(e)}"


@tool
async def get_forecast(city: str, days: int = 5) -> str:
    """
    Get weather forecast for a city.

    Args:
        city: Name of the city
        days: Number of days (1-7)
    """
    print(f"\n📅 [Direct Tool] get_forecast({city}, {days})")

    geo = await _geocode_city(city)
    if not geo:
        return f"Error: Could not find city '{city}'"

    lat, lon, name, country = geo

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": ["temperature_2m_max", "temperature_2m_min", "weather_code"],
                    "timezone": "auto",
                    "forecast_days": min(days, 7)
                },
                timeout=10.0
            )

            if response.status_code != 200:
                return f"Error: API returned {response.status_code}"

            data = response.json()
            daily = data.get("daily", {})
            times = daily.get("time", [])
            maxes = daily.get("temperature_2m_max", [])
            mins = daily.get("temperature_2m_min", [])

            result = f"Forecast for {name}, {country}:\n"
            for i, t in enumerate(times[:days]):
                result += f"  {t}: {maxes[i]}°C / {mins[i]}°C\n"
            return result

    except Exception as e:
        return f"Error: {str(e)}"


# =============================================================================
# NEWS TOOLS (Would be in news_server.py with MCP)
# =============================================================================

@tool
async def search_news(query: str) -> str:
    """
    Search for news articles.

    Args:
        query: Search query
    """
    print(f"\n🔍 [Direct Tool] search_news({query})")

    if not NEWSDATA_API_KEY:
        return "Error: NEWSDATA_API_KEY not set"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://newsdata.io/api/1/news",
                params={"apikey": NEWSDATA_API_KEY, "q": query, "language": "en"},
                timeout=15.0
            )

            if response.status_code != 200:
                return f"Error: API returned {response.status_code}"

            articles = response.json().get("results", [])
            if not articles:
                return "No articles found"

            result = f"News about '{query}':\n"
            for i, a in enumerate(articles[:3], 1):
                result += f"{i}. {a.get('title', 'No title')} ({a.get('source_id', 'Unknown')})\n"
            return result

    except Exception as e:
        return f"Error: {str(e)}"


@tool
async def get_headlines(category: str = "top", country: str = "us") -> str:
    """
    Get top news headlines.

    Args:
        category: News category (technology, business, sports, etc.)
        country: Country code (us, gb, etc.)
    """
    print(f"\n📰 [Direct Tool] get_headlines({category}, {country})")

    if not NEWSDATA_API_KEY:
        return "Error: NEWSDATA_API_KEY not set"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://newsdata.io/api/1/news",
                params={
                    "apikey": NEWSDATA_API_KEY,
                    "country": country,
                    "category": category,
                    "language": "en"
                },
                timeout=15.0
            )

            if response.status_code != 200:
                return f"Error: API returned {response.status_code}"

            articles = response.json().get("results", [])
            if not articles:
                return "No headlines found"

            result = f"Top {category} headlines ({country.upper()}):\n"
            for i, a in enumerate(articles[:3], 1):
                result += f"{i}. {a.get('title', 'No title')}\n"
            return result

    except Exception as e:
        return f"Error: {str(e)}"


# =============================================================================
# UTILITY TOOLS (Would be in utils_server.py with MCP)
# =============================================================================

@tool
async def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression.

    Args:
        expression: Math expression
    """
    print(f"\n🔢 [Direct Tool] calculate({expression})")

    safe_dict = {
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "pi": math.pi, "e": math.e, "abs": abs, "round": round
    }

    try:
        expr = expression.replace("^", "**")
        result = eval(expr, {"__builtins__": {}}, safe_dict)
        return f"Result: {expression} = {result}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
async def get_current_time(timezone: str = "UTC") -> str:
    """
    Get current time in a timezone.

    Args:
        timezone: Timezone name or city
    """
    print(f"\n🕐 [Direct Tool] get_current_time({timezone})")

    tz_map = {
        "new york": "America/New_York", "london": "Europe/London",
        "tokyo": "Asia/Tokyo", "paris": "Europe/Paris",
    }

    tz_name = tz_map.get(timezone.lower(), timezone)

    try:
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)
        return f"Time in {tz_name}: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e:
        return f"Error: {str(e)}"


# =============================================================================
# MAIN - Notice how ALL tools must be listed here manually!
# With MCP, this happens automatically from connected servers.
# =============================================================================

ALL_TOOLS = [
    get_weather,
    get_forecast,
    search_news,
    get_headlines,
    calculate,
    get_current_time,
]


async def main():
    """Run the agent WITHOUT MCP."""

    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   LangChain Agent WITHOUT MCP (For Comparison)                ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║                                                               ║
    ║  This demonstrates the TRADITIONAL approach.                  ║
    ║  Compare with agent_main.py to see MCP's benefits.            ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

    print("=" * 60)
    print("  CODE COMPARISON")
    print("=" * 60)
    print("""
    WITHOUT MCP (this file):
    ────────────────────────
    ✗ ~350 lines for 6 tools
    ✗ Everything in one file
    ✗ Hard to maintain
    ✗ Can't reuse tools easily

    WITH MCP (agent_main.py):
    ─────────────────────────
    ✓ ~150 lines of agent code
    ✓ Tools in separate servers
    ✓ Easy to maintain
    ✓ Tools reusable anywhere
    """)
    print("=" * 60)

    # Check for OpenAI key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ OPENAI_API_KEY not set in .env file")
        return

    # Initialize
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent = create_react_agent(llm, ALL_TOOLS)

    print(f"\n🔧 Tools: {len(ALL_TOOLS)}")
    for tool in ALL_TOOLS:
        print(f"   • {tool.name}")

    print("\nEnter a query (or 'quit' to exit):\n")

    while True:
        try:
            user_input = input("🧑 You: ").strip()

            if not user_input:
                continue
            if user_input.lower() == "quit":
                break

            print("\n🤖 Processing...\n")

            result = await agent.ainvoke({"messages": [("user", user_input)]})
            print(f"\n🤖 Agent: {result['messages'][-1].content}\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
