"""
Weather MCP Server (Using FREE Open-Meteo API)
===============================================

This MCP server provides weather tools using the Open-Meteo API.

WHY OPEN-METEO?
---------------
- 100% FREE - No API key required!
- No registration needed
- High-quality weather data
- Supports current weather + forecasts up to 16 days
- Rate limit: 10,000 requests/day (very generous)

API DOCUMENTATION:
------------------
- Main API: https://open-meteo.com/
- Geocoding: https://open-meteo.com/en/docs/geocoding-api
- Weather: https://open-meteo.com/en/docs

HOW THIS MCP SERVER WORKS:
--------------------------
1. User asks: "What's the weather in London?"
2. LangChain agent calls our `get_weather(city="London")` tool
3. This server receives the MCP request via stdio
4. We make TWO API calls:
   a) Geocoding API: Convert "London" -> coordinates (51.5, -0.12)
   b) Weather API: Get weather for those coordinates
5. We format the response and return it via MCP
6. Agent receives the result and uses it in its response

To run this server standalone (for testing):
    python weather_server.py
"""

import httpx
from datetime import datetime
from typing import Optional
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("weather-server")

# Open-Meteo API endpoints (NO API KEY NEEDED!)
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Weather code descriptions (WMO codes used by Open-Meteo)
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


async def _geocode_city(city: str) -> tuple[float, float, str, str] | None:
    """
    Convert a city name to coordinates using Open-Meteo's geocoding API.

    API Request Flow:
    -----------------
    Request:  GET https://geocoding-api.open-meteo.com/v1/search?name=London&count=1
    Response: {"results": [{"name": "London", "latitude": 51.5, "longitude": -0.12, ...}]}

    Returns:
        Tuple of (latitude, longitude, city_name, country) or None if not found
    """
    print(f"   📍 Geocoding: Looking up coordinates for '{city}'...")

    try:
        async with httpx.AsyncClient() as client:
            # Make geocoding request
            response = await client.get(
                GEOCODING_URL,
                params={
                    "name": city,
                    "count": 1,  # Get only the best match
                    "language": "en",
                    "format": "json"
                },
                timeout=10.0
            )

            if response.status_code != 200:
                print(f"   ❌ Geocoding failed with status {response.status_code}")
                return None

            data = response.json()
            results = data.get("results", [])

            if not results:
                print(f"   ❌ City '{city}' not found in geocoding database")
                return None

            # Get the first (best) match
            location = results[0]
            lat = location["latitude"]
            lon = location["longitude"]
            name = location["name"]
            country = location.get("country", "Unknown")

            print(f"   ✅ Found: {name}, {country} at ({lat}, {lon})")
            return (lat, lon, name, country)

    except Exception as e:
        print(f"   ❌ Geocoding error: {str(e)}")
        return None


def _format_current_weather(data: dict, city: str, country: str) -> str:
    """
    Format the Open-Meteo current weather response into readable text.

    The API returns data like:
    {
        "current": {
            "temperature_2m": 15.3,
            "relative_humidity_2m": 72,
            "weather_code": 2,
            "wind_speed_10m": 12.5,
            ...
        }
    }
    """
    try:
        current = data.get("current", {})

        temp = current.get("temperature_2m", "N/A")
        feels_like = current.get("apparent_temperature", temp)
        humidity = current.get("relative_humidity_2m", "N/A")
        weather_code = current.get("weather_code", 0)
        wind_speed = current.get("wind_speed_10m", "N/A")
        wind_dir = current.get("wind_direction_10m", "N/A")

        # Get weather description from code
        weather_desc = WEATHER_CODES.get(weather_code, "Unknown")

        return f"""
Weather for {city}, {country}:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌡️  Temperature: {temp}°C (feels like {feels_like}°C)
☁️  Conditions: {weather_desc}
💧 Humidity: {humidity}%
💨 Wind: {wind_speed} km/h (direction: {wind_dir}°)
"""
    except Exception as e:
        return f"Error formatting weather data: {str(e)}"


def _format_forecast(data: dict, city: str, country: str, days: int) -> str:
    """
    Format the Open-Meteo forecast response.

    The API returns daily data like:
    {
        "daily": {
            "time": ["2024-01-15", "2024-01-16", ...],
            "temperature_2m_max": [12.3, 14.5, ...],
            "temperature_2m_min": [5.2, 7.1, ...],
            ...
        }
    }
    """
    try:
        daily = data.get("daily", {})

        times = daily.get("time", [])
        temp_max = daily.get("temperature_2m_max", [])
        temp_min = daily.get("temperature_2m_min", [])
        weather_codes = daily.get("weather_code", [])
        precip_prob = daily.get("precipitation_probability_max", [])

        result = f"""
{days}-Day Forecast for {city}, {country}:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        for i in range(min(days, len(times))):
            date = times[i]
            # Parse and format date nicely
            dt = datetime.strptime(date, "%Y-%m-%d")
            day_name = dt.strftime("%A, %b %d")

            t_max = temp_max[i] if i < len(temp_max) else "N/A"
            t_min = temp_min[i] if i < len(temp_min) else "N/A"
            code = weather_codes[i] if i < len(weather_codes) else 0
            prob = precip_prob[i] if i < len(precip_prob) else "N/A"

            weather_desc = WEATHER_CODES.get(code, "Unknown")

            result += f"""
📅 {day_name}
   🌡️  High: {t_max}°C | Low: {t_min}°C
   ☁️  {weather_desc}
   🌧️  Precipitation chance: {prob}%
"""

        return result

    except Exception as e:
        return f"Error formatting forecast data: {str(e)}"


# =============================================================================
# MCP TOOLS - Exposed to LangChain agents via MCP protocol
# =============================================================================

@mcp.tool()
async def get_weather(city: str) -> str:
    """
    Get current weather for a city using the FREE Open-Meteo API.

    This tool fetches real-time weather data without requiring any API key.
    Use this when users ask about current weather conditions.

    Args:
        city: Name of the city (e.g., "London", "Tokyo", "New York")

    Returns:
        Current weather including temperature, conditions, humidity, and wind.

    Examples:
        - get_weather("London")
        - get_weather("Paris")
        - get_weather("New York")

    API Flow:
        1. Geocoding API: City name → Coordinates
        2. Weather API: Coordinates → Current weather data
    """
    print(f"\n🌤️  [Weather Server] Tool called: get_weather")
    print(f"   Parameter: city={city}")

    # Step 1: Convert city name to coordinates
    geo_result = await _geocode_city(city)
    if not geo_result:
        return f"Error: Could not find city '{city}'. Please check the spelling or try a larger nearby city."

    lat, lon, city_name, country = geo_result

    # Step 2: Get current weather for those coordinates
    try:
        print(f"   🌐 Fetching weather data from Open-Meteo...")

        async with httpx.AsyncClient() as client:
            # Request current weather data
            # See: https://open-meteo.com/en/docs for all available parameters
            response = await client.get(
                WEATHER_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": [
                        "temperature_2m",
                        "relative_humidity_2m",
                        "apparent_temperature",
                        "weather_code",
                        "wind_speed_10m",
                        "wind_direction_10m"
                    ],
                    "timezone": "auto"  # Automatically detect timezone
                },
                timeout=10.0
            )

            if response.status_code != 200:
                return f"Error: Weather API returned status {response.status_code}"

            data = response.json()
            result = _format_current_weather(data, city_name, country)
            print(f"   ✅ Successfully fetched current weather for {city_name}")
            return result

    except httpx.TimeoutException:
        return "Error: Request timed out. Please try again."
    except httpx.RequestError as e:
        return f"Error: Failed to connect to weather API: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error: {str(e)}"


@mcp.tool()
async def get_forecast(city: str, days: int = 5) -> str:
    """
    Get weather forecast for a city using the FREE Open-Meteo API.

    This tool fetches multi-day weather predictions without requiring any API key.
    Use this when users ask about future weather or forecasts.

    Args:
        city: Name of the city (e.g., "London", "Tokyo", "New York")
        days: Number of days to forecast (1-16, default: 5)

    Returns:
        Daily forecast with high/low temperatures, conditions, and precipitation chance.

    Examples:
        - get_forecast("London")           # 5-day forecast
        - get_forecast("Tokyo", 7)         # 7-day forecast
        - get_forecast("Berlin", 3)        # 3-day forecast
    """
    print(f"\n📅 [Weather Server] Tool called: get_forecast")
    print(f"   Parameters: city={city}, days={days}")

    # Validate days parameter
    days = max(1, min(16, days))  # Clamp between 1 and 16

    # Step 1: Geocode the city
    geo_result = await _geocode_city(city)
    if not geo_result:
        return f"Error: Could not find city '{city}'. Please check the spelling."

    lat, lon, city_name, country = geo_result

    # Step 2: Get forecast data
    try:
        print(f"   🌐 Fetching {days}-day forecast from Open-Meteo...")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                WEATHER_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": [
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "weather_code",
                        "precipitation_probability_max"
                    ],
                    "timezone": "auto",
                    "forecast_days": days
                },
                timeout=10.0
            )

            if response.status_code != 200:
                return f"Error: Weather API returned status {response.status_code}"

            data = response.json()
            result = _format_forecast(data, city_name, country, days)
            print(f"   ✅ Successfully fetched {days}-day forecast for {city_name}")
            return result

    except httpx.TimeoutException:
        return "Error: Request timed out. Please try again."
    except httpx.RequestError as e:
        return f"Error: Failed to connect to weather API: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error: {str(e)}"


@mcp.tool()
async def get_weather_by_coordinates(latitude: float, longitude: float) -> str:
    """
    Get current weather for specific coordinates using FREE Open-Meteo API.

    Use this when you have exact coordinates rather than a city name.
    Useful for precise locations or when city names are ambiguous.

    Args:
        latitude: Latitude coordinate (e.g., 51.5074 for London)
        longitude: Longitude coordinate (e.g., -0.1278 for London)

    Returns:
        Current weather for the specified coordinates.

    Examples:
        - get_weather_by_coordinates(35.6762, 139.6503)   # Tokyo
        - get_weather_by_coordinates(40.7128, -74.0060)   # New York
        - get_weather_by_coordinates(48.8566, 2.3522)     # Paris
    """
    print(f"\n📍 [Weather Server] Tool called: get_weather_by_coordinates")
    print(f"   Parameters: latitude={latitude}, longitude={longitude}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                WEATHER_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": [
                        "temperature_2m",
                        "relative_humidity_2m",
                        "apparent_temperature",
                        "weather_code",
                        "wind_speed_10m",
                        "wind_direction_10m"
                    ],
                    "timezone": "auto"
                },
                timeout=10.0
            )

            if response.status_code != 200:
                return f"Error: Weather API returned status {response.status_code}"

            data = response.json()

            # Format with coordinates since we don't have city name
            current = data.get("current", {})
            temp = current.get("temperature_2m", "N/A")
            feels_like = current.get("apparent_temperature", temp)
            humidity = current.get("relative_humidity_2m", "N/A")
            weather_code = current.get("weather_code", 0)
            wind_speed = current.get("wind_speed_10m", "N/A")

            weather_desc = WEATHER_CODES.get(weather_code, "Unknown")

            result = f"""
Weather at ({latitude}, {longitude}):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌡️  Temperature: {temp}°C (feels like {feels_like}°C)
☁️  Conditions: {weather_desc}
💧 Humidity: {humidity}%
💨 Wind: {wind_speed} km/h
"""
            print(f"   ✅ Successfully fetched weather for ({latitude}, {longitude})")
            return result

    except httpx.TimeoutException:
        return "Error: Request timed out. Please try again."
    except httpx.RequestError as e:
        return f"Error: Failed to connect to weather API: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error: {str(e)}"


# =============================================================================
# SERVER STARTUP
# =============================================================================

if __name__ == "__main__":
    print("🌤️  Starting Weather MCP Server (Open-Meteo - FREE, no API key!)")
    print("   Tools available: get_weather, get_forecast, get_weather_by_coordinates")
    print("   Waiting for MCP protocol messages via stdio...")
    mcp.run()
