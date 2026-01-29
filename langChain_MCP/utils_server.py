"""
Utils MCP Server (BONUS - No API Key Needed!)
==============================================

This BONUS MCP server demonstrates that not all tools need external APIs.
It provides utility functions that run entirely locally.

WHY THIS SERVER EXISTS:
-----------------------
This server shows:
1. MCP tools can be simple local functions (no API required)
2. Adding new MCP servers is trivial
3. You can mix API-based and local tools seamlessly

ADDING NEW SERVERS IS EASY:
---------------------------
To add this server to your agent, just add ONE entry to the config:

    MCP_SERVERS = {
        "weather": {...},
        "news": {...},
        # Add this one line:
        "utils": {
            "command": "python",
            "args": ["utils_server.py"],
            "transport": "stdio",
        },
    }

That's it! The agent automatically discovers and uses all tools.

TOOLS PROVIDED:
---------------
- calculate: Safe math evaluation (no more LLM arithmetic errors!)
- get_current_time: Get time in any timezone
- convert_timezone: Convert between timezones
- convert_temperature: Convert between Celsius, Fahrenheit, Kelvin

NO API KEY REQUIRED - Everything runs locally!

To run this server standalone:
    python utils_server.py
"""

import math
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("utils-server")

# Timezone aliases for user convenience
TIMEZONE_ALIASES = {
    # Americas
    "new york": "America/New_York",
    "ny": "America/New_York",
    "nyc": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "la": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "denver": "America/Denver",
    "toronto": "America/Toronto",
    "vancouver": "America/Vancouver",
    "sao paulo": "America/Sao_Paulo",

    # Europe
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "rome": "Europe/Rome",
    "madrid": "Europe/Madrid",
    "amsterdam": "Europe/Amsterdam",
    "moscow": "Europe/Moscow",

    # Asia
    "tokyo": "Asia/Tokyo",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "singapore": "Asia/Singapore",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "dubai": "Asia/Dubai",
    "seoul": "Asia/Seoul",
    "bangkok": "Asia/Bangkok",

    # Oceania
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "auckland": "Pacific/Auckland",

    # Common abbreviations
    "utc": "UTC",
    "gmt": "UTC",
    "est": "America/New_York",
    "pst": "America/Los_Angeles",
    "cet": "Europe/Paris",
    "jst": "Asia/Tokyo",
}


# =============================================================================
# CALCULATOR TOOL
# =============================================================================

@mcp.tool()
async def calculate(expression: str) -> str:
    """
    Safely evaluate a mathematical expression.

    LLMs sometimes make arithmetic errors. This tool provides accurate
    calculations. Supports basic math, powers, roots, and trig functions.

    Args:
        expression: A mathematical expression to evaluate.
                   Supports: +, -, *, /, ** (power), sqrt(), sin(), cos(),
                            tan(), log(), log10(), abs(), round(), pi, e

    Returns:
        The calculated result or an error message.

    Examples:
        - calculate("2 + 2")                → 4
        - calculate("sqrt(16) + 5**2")      → 29
        - calculate("sin(pi/2)")            → 1
        - calculate("100 * 1.08")           → 108 (price + 8% tax)
        - calculate("15% of 289.99")        → Will be parsed as 289.99 * 0.15

    Note: This runs locally, no API needed!
    """
    print(f"\n🔢 [Utils Server] Tool called: calculate")
    print(f"   Expression: {expression}")

    # Define safe functions and constants
    safe_dict = {
        # Math functions
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,      # Natural log
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,
        "abs": abs,
        "round": round,
        "floor": math.floor,
        "ceil": math.ceil,
        "pow": pow,

        # Constants
        "pi": math.pi,
        "e": math.e,
    }

    try:
        # Pre-process the expression
        expr = expression.lower()

        # Handle "X% of Y" pattern
        import re
        percent_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)', expr)
        if percent_match:
            percent = float(percent_match.group(1))
            value = float(percent_match.group(2))
            result = value * (percent / 100)
            print(f"   ✅ Result: {result}")
            return f"Result: {percent}% of {value} = {result:.2f}"

        # Handle percentage symbol
        expr = re.sub(r'(\d+(?:\.\d+)?)\s*%', r'(\1/100)', expr)

        # Replace ^ with ** for power operations
        expr = expr.replace("^", "**")

        # Validate characters (security)
        allowed = set("0123456789+-*/().%, ")
        for char in expr:
            if char not in allowed and not char.isalpha():
                return f"Error: Invalid character '{char}' in expression"

        # Evaluate safely
        result = eval(expr, {"__builtins__": {}}, safe_dict)

        # Format result nicely
        if isinstance(result, float):
            if result == int(result):
                result = int(result)
            else:
                result = round(result, 10)

        print(f"   ✅ Result: {result}")
        return f"Result: {expression} = {result}"

    except ZeroDivisionError:
        return "Error: Division by zero"
    except ValueError as e:
        return f"Error: Math error - {str(e)}"
    except SyntaxError:
        return "Error: Invalid expression syntax"
    except Exception as e:
        return f"Error: Could not evaluate - {str(e)}"


# =============================================================================
# TIME TOOLS
# =============================================================================

@mcp.tool()
async def get_current_time(timezone: Optional[str] = None) -> str:
    """
    Get the current time, optionally in a specific timezone.

    Useful for time-sensitive queries or checking times around the world.
    Supports city names and timezone abbreviations.

    Args:
        timezone: The timezone to get time for. Accepts:
                  - City names: "London", "Tokyo", "New York", "Paris"
                  - Abbreviations: "UTC", "EST", "PST", "CET", "JST"
                  - IANA format: "America/New_York", "Europe/London"
                  If not specified, returns UTC time.

    Returns:
        Current date and time in the specified timezone.

    Examples:
        - get_current_time()                    → UTC time
        - get_current_time("Tokyo")             → Japan time
        - get_current_time("New York")          → Eastern US time
        - get_current_time("Europe/Paris")      → Paris time

    Note: This runs locally, no API needed!
    """
    print(f"\n🕐 [Utils Server] Tool called: get_current_time")
    print(f"   Timezone: {timezone or 'UTC'}")

    try:
        # Resolve timezone
        if timezone:
            tz_lower = timezone.lower().strip()
            # Check aliases first
            tz_name = TIMEZONE_ALIASES.get(tz_lower, timezone)
        else:
            tz_name = "UTC"

        # Get timezone object
        try:
            tz = ZoneInfo(tz_name)
        except KeyError:
            # Timezone not found - suggest alternatives
            suggestions = [k for k in TIMEZONE_ALIASES.keys() if timezone.lower() in k]
            if suggestions:
                return f"Error: Unknown timezone '{timezone}'. Did you mean: {', '.join(suggestions[:5])}?"
            return f"Error: Unknown timezone '{timezone}'. Try city names like 'London', 'Tokyo', 'New York' or IANA format like 'America/New_York'"

        # Get current time
        now = datetime.now(tz)

        result = f"""
Current Time ({tz_name}):
━━━━━━━━━━━━━━━━━━━━━━━━
📅 Date: {now.strftime('%A, %B %d, %Y')}
🕐 Time: {now.strftime('%I:%M:%S %p')} ({now.strftime('%H:%M:%S')} 24h)
🌍 UTC Offset: {now.strftime('%z')}
"""
        print(f"   ✅ Got time for {tz_name}")
        return result

    except Exception as e:
        return f"Error: Could not get time - {str(e)}"


@mcp.tool()
async def convert_timezone(
    time_str: str,
    from_timezone: str,
    to_timezone: str
) -> str:
    """
    Convert a time from one timezone to another.

    Useful for scheduling across timezones or understanding
    when events happen in different locations.

    Args:
        time_str: Time to convert in HH:MM format (24-hour)
        from_timezone: Source timezone (city name or IANA format)
        to_timezone: Target timezone (city name or IANA format)

    Returns:
        The converted time in both timezones.

    Examples:
        - convert_timezone("14:00", "London", "Tokyo")
        - convert_timezone("09:30", "New York", "Los Angeles")
        - convert_timezone("18:00", "Paris", "Sydney")

    Note: This runs locally, no API needed!
    """
    print(f"\n🌍 [Utils Server] Tool called: convert_timezone")
    print(f"   Converting {time_str} from {from_timezone} to {to_timezone}")

    try:
        # Resolve timezones
        from_tz_name = TIMEZONE_ALIASES.get(from_timezone.lower().strip(), from_timezone)
        to_tz_name = TIMEZONE_ALIASES.get(to_timezone.lower().strip(), to_timezone)

        try:
            from_tz = ZoneInfo(from_tz_name)
            to_tz = ZoneInfo(to_tz_name)
        except KeyError as e:
            return f"Error: Unknown timezone - {str(e).strip()}"

        # Parse time
        try:
            if ":" in time_str:
                parts = time_str.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
            else:
                return "Error: Invalid time format. Use HH:MM (24-hour)"
        except ValueError:
            return "Error: Invalid time format. Use HH:MM (24-hour)"

        # Create datetime in source timezone
        now = datetime.now()
        source_time = datetime(
            now.year, now.month, now.day,
            hour, minute, 0,
            tzinfo=from_tz
        )

        # Convert to target
        target_time = source_time.astimezone(to_tz)

        # Calculate time difference
        diff_hours = (target_time.utcoffset().total_seconds() -
                      source_time.utcoffset().total_seconds()) / 3600

        result = f"""
Timezone Conversion:
━━━━━━━━━━━━━━━━━━━━
⏰ {time_str} in {from_tz_name}
   ↓
⏰ {target_time.strftime('%H:%M')} in {to_tz_name}

📊 Time difference: {diff_hours:+.1f} hours
"""
        print(f"   ✅ Converted successfully")
        return result

    except Exception as e:
        return f"Error: Could not convert - {str(e)}"


# =============================================================================
# TEMPERATURE CONVERSION
# =============================================================================

@mcp.tool()
async def convert_temperature(
    value: float,
    from_unit: str,
    to_unit: str
) -> str:
    """
    Convert temperature between Celsius, Fahrenheit, and Kelvin.

    Useful when weather data is in a different unit than desired.

    Args:
        value: The temperature value to convert
        from_unit: Source unit - "celsius", "fahrenheit", or "kelvin" (or "c", "f", "k")
        to_unit: Target unit - "celsius", "fahrenheit", or "kelvin" (or "c", "f", "k")

    Returns:
        The converted temperature value.

    Examples:
        - convert_temperature(100, "celsius", "fahrenheit")  → 212°F
        - convert_temperature(32, "f", "c")                  → 0°C
        - convert_temperature(0, "c", "k")                   → 273.15 K

    Note: This runs locally, no API needed!
    """
    print(f"\n🌡️  [Utils Server] Tool called: convert_temperature")
    print(f"   Converting {value} from {from_unit} to {to_unit}")

    # Normalize unit names
    unit_map = {
        "c": "celsius", "celsius": "celsius",
        "f": "fahrenheit", "fahrenheit": "fahrenheit",
        "k": "kelvin", "kelvin": "kelvin"
    }

    from_u = unit_map.get(from_unit.lower().strip())
    to_u = unit_map.get(to_unit.lower().strip())

    if not from_u or not to_u:
        return "Error: Invalid unit. Use 'celsius' (c), 'fahrenheit' (f), or 'kelvin' (k)"

    try:
        # Convert to Celsius first (as intermediate)
        if from_u == "celsius":
            celsius = value
        elif from_u == "fahrenheit":
            celsius = (value - 32) * 5 / 9
        else:  # kelvin
            celsius = value - 273.15

        # Convert from Celsius to target
        if to_u == "celsius":
            result = celsius
        elif to_u == "fahrenheit":
            result = celsius * 9 / 5 + 32
        else:  # kelvin
            result = celsius + 273.15

        result = round(result, 2)

        # Unit symbols
        symbols = {"celsius": "°C", "fahrenheit": "°F", "kelvin": "K"}

        print(f"   ✅ Result: {result}")
        return f"Result: {value}{symbols[from_u]} = {result}{symbols[to_u]}"

    except Exception as e:
        return f"Error: Could not convert - {str(e)}"


# =============================================================================
# SERVER STARTUP
# =============================================================================

if __name__ == "__main__":
    print("🔧 Starting Utils MCP Server (NO API KEY NEEDED!)")
    print("   Tools available:")
    print("   - calculate: Safe math evaluation")
    print("   - get_current_time: Get time in any timezone")
    print("   - convert_timezone: Convert between timezones")
    print("   - convert_temperature: Convert C/F/K")
    print("   Waiting for MCP protocol messages via stdio...")
    mcp.run()
