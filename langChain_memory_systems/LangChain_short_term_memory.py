"""
LangChain Short-Term Memory (Conversation Buffer) Implementation
================================================================

This module demonstrates how ConversationBufferMemory works in LangChain
to maintain context across multiple tool calls in a travel planning agent.

WHAT THIS DEMONSTRATES:
-----------------------
1. ConversationBufferMemory retains FULL conversation history
2. Agent can reference previous context (cities, dates, preferences)
3. Multi-step conversations where context from earlier messages is needed
4. Verbose logging showing memory state and tool usage

HOW TO SET UP API KEYS:
-----------------------
Create a .env file in the project root with:
    SERP_API=your_serpapi_key
    OPENAI_API_KEY=your_openai_key
    AMADEUS_API_KEY=your_amadeus_key
    AMADEUS_API_SECRET=your_amadeus_secret

HOW TO RUN:
-----------
    cd /Volumes/vibecoding/LangChain/langChain_memory_systems
    python LangChain_short_term_memory.py

HOW TO READ DEBUG OUTPUT:
-------------------------
Look for these markers in the output:
    [TOOL CALLED]     - Which tool is being invoked
    [PARAMETERS]      - What parameters are passed to the tool
    [MEMORY CONTEXT]  - Conversation history being used
    [TOOL RESPONSE]   - Summary of what the tool returned
    [MEMORY STATE]    - Current state of conversation buffer

APIS USED:
----------
1. SerpAPI       - Web search for destination information (requires API key)
2. Open-Meteo    - Weather data (FREE, no API key needed)
3. Amadeus       - Flight search (FREE test environment)
4. Amadeus       - Hotel search (FREE test environment)

Author: LangChain Learning Repository
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool, StructuredTool
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# API Keys from environment
SERP_API_KEY = os.getenv("SERP_API")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

# Amadeus Test Environment URLs
AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_FLIGHT_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"
AMADEUS_HOTEL_LIST_URL = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
AMADEUS_HOTEL_OFFERS_URL = "https://test.api.amadeus.com/v3/shopping/hotel-offers"

# Global variable to store Amadeus access token
_amadeus_token: Optional[str] = None
_token_expiry: Optional[datetime] = None


# =============================================================================
# LOGGING UTILITIES
# =============================================================================

def log_separator():
    """Print a visual separator for logs."""
    print("\n" + "=" * 70)


def log_tool_call(tool_name: str, parameters: Dict[str, Any], memory_context: str = ""):
    """Log when a tool is called with parameters and memory context."""
    log_separator()
    print(f"[TOOL CALLED]: {tool_name}")
    print(f"[PARAMETERS]: {json.dumps(parameters, indent=2)}")
    if memory_context:
        print(f"[MEMORY CONTEXT]: {memory_context}")
    print("-" * 70)


def log_tool_response(tool_name: str, response_summary: str):
    """Log the tool response summary."""
    print(f"[TOOL RESPONSE]: {response_summary}")
    log_separator()


def log_memory_state(memory: ConversationBufferMemory):
    """Log the current state of conversation buffer memory."""
    print("\n" + "~" * 70)
    print("[MEMORY STATE] - Conversation Buffer Contents:")
    print("~" * 70)

    # Get memory variables
    memory_vars = memory.load_memory_variables({})
    history = memory_vars.get("chat_history", [])

    if history:
        for msg in history:
            if hasattr(msg, 'type'):
                role = "Human" if msg.type == "human" else "AI"
                content = msg.content if hasattr(msg, 'content') else str(msg)
                print(f"{role}: {content[:200]}..." if len(str(content)) > 200 else f"{role}: {content}")
    else:
        print("(Empty - No conversation history yet)")

    print("~" * 70 + "\n")


# =============================================================================
# AMADEUS AUTHENTICATION
# =============================================================================

def get_amadeus_token() -> str:
    """
    Get Amadeus OAuth2 access token.

    Uses client credentials flow to obtain access token.
    Token is cached and reused until expiry.

    Returns:
        str: Valid access token for Amadeus API

    Raises:
        Exception: If authentication fails
    """
    global _amadeus_token, _token_expiry

    # Check if we have a valid cached token
    if _amadeus_token and _token_expiry and datetime.now() < _token_expiry:
        return _amadeus_token

    # Request new token
    print("[AMADEUS AUTH] Requesting new access token...")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_API_KEY,
        "client_secret": AMADEUS_API_SECRET
    }

    response = requests.post(AMADEUS_AUTH_URL, headers=headers, data=data)

    if response.status_code == 200:
        token_data = response.json()
        _amadeus_token = token_data["access_token"]
        # Token expires in 1799 seconds, we'll refresh 5 minutes early
        expires_in = token_data.get("expires_in", 1799)
        _token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)
        print(f"[AMADEUS AUTH] Token obtained successfully (expires in {expires_in}s)")
        return _amadeus_token
    else:
        error_msg = f"Failed to get Amadeus token: {response.status_code} - {response.text}"
        print(f"[AMADEUS AUTH ERROR] {error_msg}")
        raise Exception(error_msg)


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

def serp_search(query: str) -> str:
    """
    Search the web using SerpAPI for destination information.

    Args:
        query: Search query string

    Returns:
        str: Search results summary
    """
    log_tool_call(
        tool_name="SERP API (Web Search)",
        parameters={"query": query},
        memory_context="Using search to find information about destinations"
    )

    try:
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": SERP_API_KEY,
            "engine": "google",
            "num": 5  # Get top 5 results
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()

            # Extract organic results
            results = []
            organic_results = data.get("organic_results", [])[:5]

            for i, result in enumerate(organic_results, 1):
                title = result.get("title", "No title")
                snippet = result.get("snippet", "No description")
                results.append(f"{i}. {title}\n   {snippet}")

            # Also get answer box if available
            answer_box = data.get("answer_box", {})
            answer = answer_box.get("answer") or answer_box.get("snippet") or ""

            result_text = ""
            if answer:
                result_text += f"Quick Answer: {answer}\n\n"

            result_text += "Search Results:\n" + "\n\n".join(results)

            log_tool_response("SERP API", f"Found {len(organic_results)} results for '{query}'")
            return result_text

        else:
            error_msg = f"Search failed with status {response.status_code}"
            log_tool_response("SERP API", error_msg)
            return error_msg

    except Exception as e:
        error_msg = f"Search error: {str(e)}"
        log_tool_response("SERP API", error_msg)
        return error_msg


def get_weather(location: str) -> str:
    """
    Get weather information using Open-Meteo API.

    Args:
        location: City name or location

    Returns:
        str: Weather information for the location
    """
    log_tool_call(
        tool_name="Open-Meteo API (Weather)",
        parameters={"location": location},
        memory_context=f"Getting weather for location: {location}"
    )

    try:
        # First, geocode the location
        geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
        geocode_params = {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json"
        }

        geo_response = requests.get(geocode_url, params=geocode_params)

        if geo_response.status_code != 200:
            error_msg = f"Geocoding failed: {geo_response.status_code}"
            log_tool_response("Open-Meteo API", error_msg)
            return error_msg

        geo_data = geo_response.json()

        if not geo_data.get("results"):
            error_msg = f"Location '{location}' not found"
            log_tool_response("Open-Meteo API", error_msg)
            return error_msg

        # Get coordinates
        loc = geo_data["results"][0]
        lat = loc["latitude"]
        lon = loc["longitude"]
        city_name = loc.get("name", location)
        country = loc.get("country", "")

        # Get weather data
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
            "timezone": "auto",
            "forecast_days": 7
        }

        weather_response = requests.get(weather_url, params=weather_params)

        if weather_response.status_code != 200:
            error_msg = f"Weather API failed: {weather_response.status_code}"
            log_tool_response("Open-Meteo API", error_msg)
            return error_msg

        weather_data = weather_response.json()
        current = weather_data.get("current", {})
        daily = weather_data.get("daily", {})

        # Format weather response
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle",
            53: "Moderate drizzle", 55: "Dense drizzle", 61: "Slight rain",
            63: "Moderate rain", 65: "Heavy rain", 71: "Slight snow",
            73: "Moderate snow", 75: "Heavy snow", 80: "Slight rain showers",
            81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with hail"
        }

        current_code = current.get("weather_code", 0)
        current_condition = weather_codes.get(current_code, "Unknown")

        result = f"""
Weather for {city_name}, {country}:

CURRENT CONDITIONS:
- Temperature: {current.get('temperature_2m', 'N/A')}°C (feels like {current.get('apparent_temperature', 'N/A')}°C)
- Conditions: {current_condition}
- Humidity: {current.get('relative_humidity_2m', 'N/A')}%
- Wind Speed: {current.get('wind_speed_10m', 'N/A')} km/h

7-DAY FORECAST:
"""

        dates = daily.get("time", [])[:7]
        max_temps = daily.get("temperature_2m_max", [])[:7]
        min_temps = daily.get("temperature_2m_min", [])[:7]
        precip = daily.get("precipitation_probability_max", [])[:7]
        codes = daily.get("weather_code", [])[:7]

        for i, date in enumerate(dates):
            day_condition = weather_codes.get(codes[i] if i < len(codes) else 0, "Unknown")
            result += f"- {date}: {min_temps[i] if i < len(min_temps) else 'N/A'}°C to {max_temps[i] if i < len(max_temps) else 'N/A'}°C, {day_condition}, Rain: {precip[i] if i < len(precip) else 'N/A'}%\n"

        log_tool_response("Open-Meteo API", f"Weather data retrieved for {city_name}")
        return result

    except Exception as e:
        error_msg = f"Weather error: {str(e)}"
        log_tool_response("Open-Meteo API", error_msg)
        return error_msg


def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1
) -> str:
    """
    Search for flights using Amadeus Flight Offers API.

    Args:
        origin: Origin airport IATA code (e.g., 'JFK', 'LAX')
        destination: Destination airport IATA code
        departure_date: Departure date in YYYY-MM-DD format
        return_date: Optional return date for round trips
        adults: Number of adult passengers (default 1)

    Returns:
        str: Flight offers summary
    """
    log_tool_call(
        tool_name="Amadeus Flight Offers API",
        parameters={
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "adults": adults
        },
        memory_context="Searching for flight offers"
    )

    try:
        # Get authentication token
        token = get_amadeus_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "adults": adults,
            "currencyCode": "USD",
            "max": 5  # Get top 5 offers
        }

        if return_date:
            params["returnDate"] = return_date

        response = requests.get(AMADEUS_FLIGHT_URL, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            offers = data.get("data", [])

            if not offers:
                result = "No flights found for the specified route and dates."
                log_tool_response("Amadeus Flight API", result)
                return result

            result = f"Flight Offers from {origin.upper()} to {destination.upper()}:\n\n"

            for i, offer in enumerate(offers[:5], 1):
                price = offer.get("price", {})
                total = price.get("total", "N/A")
                currency = price.get("currency", "USD")

                itineraries = offer.get("itineraries", [])

                result += f"OPTION {i}: {total} {currency}\n"

                for j, itinerary in enumerate(itineraries):
                    trip_type = "Outbound" if j == 0 else "Return"
                    duration = itinerary.get("duration", "N/A")
                    segments = itinerary.get("segments", [])

                    result += f"  {trip_type} (Duration: {duration}):\n"

                    for seg in segments:
                        dep = seg.get("departure", {})
                        arr = seg.get("arrival", {})
                        carrier = seg.get("carrierCode", "N/A")
                        flight_num = seg.get("number", "N/A")

                        result += f"    - {carrier}{flight_num}: {dep.get('iataCode', 'N/A')} ({dep.get('at', 'N/A')}) -> {arr.get('iataCode', 'N/A')} ({arr.get('at', 'N/A')})\n"

                result += "\n"

            log_tool_response("Amadeus Flight API", f"Found {len(offers)} flight offers")
            return result

        else:
            error_data = response.json() if response.text else {}
            errors = error_data.get("errors", [{}])
            error_detail = errors[0].get("detail", response.text) if errors else response.text
            error_msg = f"Flight search failed: {response.status_code} - {error_detail}"
            log_tool_response("Amadeus Flight API", error_msg)
            return error_msg

    except Exception as e:
        error_msg = f"Flight search error: {str(e)}"
        log_tool_response("Amadeus Flight API", error_msg)
        return error_msg


def search_hotels(
    city_code: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 1
) -> str:
    """
    Search for hotels using Amadeus Hotel Search API.

    Args:
        city_code: City IATA code (e.g., 'PAR' for Paris, 'NYC' for New York)
        check_in_date: Check-in date in YYYY-MM-DD format
        check_out_date: Check-out date in YYYY-MM-DD format
        adults: Number of adult guests (default 1)

    Returns:
        str: Hotel offers summary
    """
    log_tool_call(
        tool_name="Amadeus Hotel Search API",
        parameters={
            "city_code": city_code,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults
        },
        memory_context="Searching for hotel accommodations"
    )

    try:
        # Get authentication token
        token = get_amadeus_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Step 1: Get hotels in the city
        hotel_list_params = {
            "cityCode": city_code.upper(),
            "radius": 10,
            "radiusUnit": "KM",
            "hotelSource": "ALL"
        }

        list_response = requests.get(AMADEUS_HOTEL_LIST_URL, headers=headers, params=hotel_list_params)

        hotel_ids = []
        if list_response.status_code == 200:
            list_data = list_response.json()
            hotels = list_data.get("data", [])[:10]  # Get first 10 hotels
            hotel_ids = [h.get("hotelId") for h in hotels if h.get("hotelId")]

        if not hotel_ids:
            # Provide fallback response with general information
            result = f"""
Hotel Search for {city_code.upper()}:

Note: Unable to retrieve specific hotel listings for this city code.
This may be due to:
- Invalid city code (use IATA codes like 'PAR' for Paris, 'NYC' for New York)
- Limited data in Amadeus test environment

Suggestions:
- For Paris, try: PAR
- For New York, try: NYC
- For London, try: LON
- For Tokyo, try: TYO

The test environment has limited hotel data. For production use, more hotels would be available.
"""
            log_tool_response("Amadeus Hotel API", "No hotels found or invalid city code")
            return result

        # Step 2: Get hotel offers
        offers_params = {
            "hotelIds": ",".join(hotel_ids[:5]),  # Limit to 5 hotels for speed
            "checkInDate": check_in_date,
            "checkOutDate": check_out_date,
            "adults": adults,
            "currency": "USD"
        }

        offers_response = requests.get(AMADEUS_HOTEL_OFFERS_URL, headers=headers, params=offers_params)

        if offers_response.status_code == 200:
            offers_data = offers_response.json()
            hotel_offers = offers_data.get("data", [])

            if not hotel_offers:
                result = f"No hotel offers found in {city_code.upper()} for the specified dates."
                log_tool_response("Amadeus Hotel API", result)
                return result

            result = f"Hotel Offers in {city_code.upper()} ({check_in_date} to {check_out_date}):\n\n"

            for i, hotel in enumerate(hotel_offers[:5], 1):
                hotel_info = hotel.get("hotel", {})
                hotel_name = hotel_info.get("name", "Unknown Hotel")

                offers = hotel.get("offers", [])
                if offers:
                    offer = offers[0]
                    price = offer.get("price", {})
                    total = price.get("total", "N/A")
                    currency = price.get("currency", "USD")

                    room = offer.get("room", {})
                    room_type = room.get("typeEstimated", {})
                    room_category = room_type.get("category", "Standard")
                    beds = room_type.get("beds", "N/A")
                    bed_type = room_type.get("bedType", "N/A")

                    result += f"{i}. {hotel_name}\n"
                    result += f"   Price: {total} {currency} (total stay)\n"
                    result += f"   Room: {room_category}, {beds} {bed_type} bed(s)\n\n"

            log_tool_response("Amadeus Hotel API", f"Found {len(hotel_offers)} hotel offers")
            return result

        else:
            error_data = offers_response.json() if offers_response.text else {}
            errors = error_data.get("errors", [{}])
            error_detail = errors[0].get("detail", offers_response.text) if errors else offers_response.text
            error_msg = f"Hotel search failed: {offers_response.status_code} - {error_detail}"
            log_tool_response("Amadeus Hotel API", error_msg)
            return error_msg

    except Exception as e:
        error_msg = f"Hotel search error: {str(e)}"
        log_tool_response("Amadeus Hotel API", error_msg)
        return error_msg


# =============================================================================
# TOOL DEFINITIONS FOR LANGCHAIN
# =============================================================================

def create_tools() -> List[Tool]:
    """
    Create LangChain tool objects for the agent.

    Returns:
        List[Tool]: List of tools available to the agent
    """
    tools = [
        Tool(
            name="web_search",
            func=serp_search,
            description="""Search the web for information about travel destinations, attractions,
            activities, restaurants, local customs, and general travel advice.
            Use this to find information about places the user wants to visit.
            Input should be a search query string."""
        ),
        Tool(
            name="get_weather",
            func=get_weather,
            description="""Get current weather and 7-day forecast for a location.
            Useful for checking weather conditions at travel destinations.
            Input should be a city name or location (e.g., 'Paris', 'New York', 'Tokyo').
            Returns temperature, conditions, humidity, and forecast."""
        ),
        Tool(
            name="search_flights",
            func=lambda query: _parse_and_search_flights(query),
            description="""Search for available flights between two cities.
            Input should be a string in format: 'origin|destination|departure_date|return_date(optional)|adults'
            Example: 'JFK|CDG|2024-06-15|2024-06-22|2' for round trip
            Example: 'LAX|LHR|2024-07-01||1' for one-way
            Use IATA airport codes (JFK, LAX, CDG, LHR, NRT, etc.)
            Dates should be in YYYY-MM-DD format."""
        ),
        Tool(
            name="search_hotels",
            func=lambda query: _parse_and_search_hotels(query),
            description="""Search for available hotels in a city.
            Input should be a string in format: 'city_code|check_in_date|check_out_date|adults'
            Example: 'PAR|2024-06-15|2024-06-22|2' for Paris
            Use IATA city codes (PAR=Paris, NYC=New York, LON=London, TYO=Tokyo, etc.)
            Dates should be in YYYY-MM-DD format."""
        ),
    ]

    return tools


def _parse_and_search_flights(query: str) -> str:
    """Helper to parse flight search query string."""
    try:
        parts = query.split("|")
        if len(parts) < 3:
            return "Invalid format. Use: origin|destination|departure_date|return_date(optional)|adults"

        origin = parts[0].strip()
        destination = parts[1].strip()
        departure_date = parts[2].strip()
        return_date = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
        adults = int(parts[4].strip()) if len(parts) > 4 and parts[4].strip() else 1

        return search_flights(origin, destination, departure_date, return_date, adults)
    except Exception as e:
        return f"Error parsing flight search: {str(e)}. Use format: origin|destination|departure_date|return_date|adults"


def _parse_and_search_hotels(query: str) -> str:
    """Helper to parse hotel search query string."""
    try:
        parts = query.split("|")
        if len(parts) < 3:
            return "Invalid format. Use: city_code|check_in_date|check_out_date|adults"

        city_code = parts[0].strip()
        check_in = parts[1].strip()
        check_out = parts[2].strip()
        adults = int(parts[3].strip()) if len(parts) > 3 and parts[3].strip() else 1

        return search_hotels(city_code, check_in, check_out, adults)
    except Exception as e:
        return f"Error parsing hotel search: {str(e)}. Use format: city_code|check_in_date|check_out_date|adults"


# =============================================================================
# AGENT SETUP WITH CONVERSATION BUFFER MEMORY
# =============================================================================

def create_agent_with_memory():
    """
    Create a LangChain agent with ConversationBufferMemory.

    Returns:
        tuple: (agent_executor, memory) - The agent and its memory object
    """
    print("\n" + "=" * 70)
    print("INITIALIZING TRAVEL PLANNING AGENT WITH CONVERSATION BUFFER MEMORY")
    print("=" * 70)

    # Initialize the LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=OPENAI_API_KEY
    )
    print("[INIT] LLM initialized: gpt-4o-mini")

    # Create tools
    tools = create_tools()
    print(f"[INIT] Tools loaded: {[t.name for t in tools]}")

    # Create Conversation Buffer Memory
    # This retains the FULL conversation history
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="output"
    )
    print("[INIT] ConversationBufferMemory initialized")
    print("       - Stores FULL conversation history")
    print("       - Memory key: 'chat_history'")
    print("       - Returns messages as list")

    # Create agent prompt with memory
    prompt_template = """You are a helpful travel planning assistant. You help users plan trips by:
1. Searching for destination information
2. Checking weather conditions
3. Finding flights
4. Finding hotels

You have access to the conversation history, so you can reference previous context.
When the user refers to "there" or "that place" or a destination mentioned earlier,
use the conversation history to understand which location they mean.

IMPORTANT: Always use IATA codes for airports and cities:
- Paris: CDG (airport), PAR (city)
- New York: JFK/LGA/EWR (airports), NYC (city)
- London: LHR/LGW (airports), LON (city)
- Tokyo: NRT/HND (airports), TYO (city)
- Los Angeles: LAX (airport/city)

TOOLS:
{tools}

TOOL NAMES: {tool_names}

CONVERSATION HISTORY:
{chat_history}

INSTRUCTIONS:
- Use the conversation history to maintain context
- When the user refers to a previously mentioned city, remember it
- Be helpful and proactive in suggesting next steps

USER INPUT: {input}

To use a tool, use this format:
Thought: [your reasoning about what to do]
Action: [tool name]
Action Input: [input to the tool]

When you have a final answer:
Thought: I now have enough information to respond
Final Answer: [your response to the user]

Begin!

Thought: {agent_scratchpad}"""

    prompt = PromptTemplate(
        input_variables=["input", "chat_history", "tools", "tool_names", "agent_scratchpad"],
        template=prompt_template
    )

    # Create the ReAct agent
    agent = create_react_agent(llm, tools, prompt)

    # Create agent executor with memory
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
        return_intermediate_steps=True
    )

    print("[INIT] Agent executor created with memory integration")
    print("=" * 70 + "\n")

    return agent_executor, memory


# =============================================================================
# CONVERSATION HANDLER
# =============================================================================

def chat_with_agent(agent_executor: AgentExecutor, memory: ConversationBufferMemory, user_input: str) -> str:
    """
    Send a message to the agent and get a response.
    Logs memory state and tool usage for educational purposes.

    Args:
        agent_executor: The LangChain agent executor
        memory: The conversation buffer memory
        user_input: User's message

    Returns:
        str: Agent's response
    """
    print("\n" + "#" * 70)
    print(f"USER: {user_input}")
    print("#" * 70)

    # Log memory state BEFORE processing
    print("\n[PRE-PROCESSING] Memory state before handling this message:")
    log_memory_state(memory)

    try:
        # Invoke the agent
        response = agent_executor.invoke({"input": user_input})

        # Extract the output
        output = response.get("output", "I couldn't generate a response.")

        # Log memory state AFTER processing
        print("\n[POST-PROCESSING] Memory state after handling this message:")
        log_memory_state(memory)

        print("\n" + "#" * 70)
        print(f"ASSISTANT: {output}")
        print("#" * 70 + "\n")

        return output

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"\n[ERROR] {error_msg}")
        return error_msg


# =============================================================================
# DEMO / EXAMPLE USAGE
# =============================================================================

def run_demo():
    """
    Run a demonstration of the Conversation Buffer Memory system.

    This demo shows:
    1. User asks about a destination (uses SERP)
    2. User asks "what's the weather there?" (uses Open-Meteo, remembers city)
    3. User asks about flights (uses Amadeus Flight API, remembers destination)
    4. User asks about hotels (uses Amadeus Hotel API, remembers destination)
    """
    print("\n")
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*   LANGCHAIN CONVERSATION BUFFER MEMORY DEMONSTRATION" + " " * 13 + "*")
    print("*" + " " * 68 + "*")
    print("*   This demo shows how memory maintains context across tool calls" + " " * 2 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print("\n")

    # Create agent with memory
    agent_executor, memory = create_agent_with_memory()

    # Demo conversation - each message builds on previous context
    demo_messages = [
        # Step 1: Ask about a destination
        "I'm thinking about visiting Paris, France. What are the top attractions there?",

        # Step 2: Reference the destination implicitly (tests memory)
        "What's the weather like there right now?",

        # Step 3: Ask about flights (agent should remember Paris)
        "Can you find flights from New York to there for next week? Let's say departing June 15, 2024 and returning June 22, 2024. Just me traveling.",

        # Step 4: Ask about hotels (agent should remember Paris and dates)
        "Great! Now can you find me some hotels there for those same dates?",
    ]

    print("\n" + "=" * 70)
    print("STARTING DEMO CONVERSATION")
    print("=" * 70)
    print("""
This conversation demonstrates how ConversationBufferMemory works:

Message 1: User asks about Paris -> Agent uses web search
Message 2: User says "there" -> Agent remembers Paris from context
Message 3: User asks for flights -> Agent uses remembered destination
Message 4: User asks for hotels -> Agent uses remembered destination AND dates

Watch the [MEMORY STATE] sections to see how conversation history accumulates!
""")
    print("=" * 70)

    for i, message in enumerate(demo_messages, 1):
        print(f"\n\n{'>'*35} MESSAGE {i}/4 {'<'*35}")
        response = chat_with_agent(agent_executor, memory, message)

        # Pause between messages for readability
        print(f"\n{'='*70}")
        print(f"Message {i} complete. The agent has now stored this exchange in memory.")
        print(f"{'='*70}")

    print("\n\n")
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*   DEMO COMPLETE!" + " " * 50 + "*")
    print("*" + " " * 68 + "*")
    print("*   Key Observations:" + " " * 47 + "*")
    print("*   - Memory retained ALL conversation history" + " " * 22 + "*")
    print("*   - Agent referenced 'Paris' even when user said 'there'" + " " * 9 + "*")
    print("*   - Dates and preferences were carried across messages" + " " * 11 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)


def interactive_mode():
    """
    Run the agent in interactive mode for testing.
    """
    print("\n")
    print("*" * 70)
    print("*   INTERACTIVE MODE - Travel Planning Agent" + " " * 22 + "*")
    print("*   Type 'quit' or 'exit' to end the conversation" + " " * 16 + "*")
    print("*   Type 'memory' to see current memory state" + " " * 20 + "*")
    print("*" * 70)
    print("\n")

    agent_executor, memory = create_agent_with_memory()

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye! Have a great trip!")
                break

            if user_input.lower() == 'memory':
                print("\n[CURRENT MEMORY STATE]")
                log_memory_state(memory)
                continue

            chat_with_agent(agent_executor, memory, user_input)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys

    print("\n" + "=" * 70)
    print("LangChain Short-Term Memory (Conversation Buffer) Demo")
    print("=" * 70)

    # Check for required environment variables
    missing_vars = []
    if not SERP_API_KEY:
        missing_vars.append("SERP_API")
    if not OPENAI_API_KEY:
        missing_vars.append("OPENAI_API_KEY")
    if not AMADEUS_API_KEY:
        missing_vars.append("AMADEUS_API_KEY")
    if not AMADEUS_API_SECRET:
        missing_vars.append("AMADEUS_API_SECRET")

    if missing_vars:
        print(f"\n[WARNING] Missing environment variables: {', '.join(missing_vars)}")
        print("Some features may not work. Please check your .env file.")

    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        # Run the demo by default
        run_demo()

    print("\n" + "=" * 70)
    print("Program finished.")
    print("=" * 70 + "\n")
