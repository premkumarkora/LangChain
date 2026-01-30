"""Streamlit Demo: LangChain Short-Term Memory (Conversation Buffer)"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, List
from dotenv import load_dotenv
import streamlit as st

from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_classic.memory import ConversationBufferMemory
from langchain_classic.tools import Tool
from langchain_classic.prompts import PromptTemplate

load_dotenv()

# API Keys
SERP_API_KEY = os.getenv("SERP_API")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

# Amadeus URLs
AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_FLIGHT_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"
AMADEUS_HOTEL_LIST_URL = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
AMADEUS_HOTEL_OFFERS_URL = "https://test.api.amadeus.com/v3/shopping/hotel-offers"

_amadeus_token: Optional[str] = None
_token_expiry: Optional[datetime] = None


def get_amadeus_token() -> str:
    global _amadeus_token, _token_expiry
    if _amadeus_token and _token_expiry and datetime.now() < _token_expiry:
        return _amadeus_token

    response = requests.post(
        AMADEUS_AUTH_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials", "client_id": AMADEUS_API_KEY, "client_secret": AMADEUS_API_SECRET}
    )

    if response.status_code == 200:
        token_data = response.json()
        _amadeus_token = token_data["access_token"]
        _token_expiry = datetime.now() + timedelta(seconds=token_data.get("expires_in", 1799) - 300)
        return _amadeus_token
    raise Exception(f"Failed to get Amadeus token: {response.status_code}")


def serp_search(query: str) -> str:
    try:
        response = requests.get("https://serpapi.com/search", params={"q": query, "api_key": SERP_API_KEY, "engine": "google", "num": 5})
        if response.status_code == 200:
            data = response.json()
            results = [f"{i}. {r.get('title', 'No title')}\n   {r.get('snippet', '')}" for i, r in enumerate(data.get("organic_results", [])[:5], 1)]
            answer = data.get("answer_box", {}).get("answer") or data.get("answer_box", {}).get("snippet") or ""
            return (f"Quick Answer: {answer}\n\n" if answer else "") + "Search Results:\n" + "\n\n".join(results)
        return f"Search failed: {response.status_code}"
    except Exception as e:
        return f"Search error: {str(e)}"


def get_weather(location: str) -> str:
    try:
        geo_response = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": location, "count": 1, "language": "en", "format": "json"})
        if geo_response.status_code != 200 or not geo_response.json().get("results"):
            return f"Location '{location}' not found"

        loc = geo_response.json()["results"][0]
        weather_response = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": loc["latitude"], "longitude": loc["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
            "timezone": "auto", "forecast_days": 7
        })

        if weather_response.status_code != 200:
            return f"Weather API failed: {weather_response.status_code}"

        data = weather_response.json()
        current = data.get("current", {})
        daily = data.get("daily", {})

        weather_codes = {0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Foggy", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain", 95: "Thunderstorm"}

        result = f"**Weather for {loc.get('name')}, {loc.get('country')}:**\n\n"
        result += f"🌡️ Temperature: {current.get('temperature_2m')}°C (feels like {current.get('apparent_temperature')}°C)\n"
        result += f"☁️ Conditions: {weather_codes.get(current.get('weather_code', 0), 'Unknown')}\n"
        result += f"💧 Humidity: {current.get('relative_humidity_2m')}%\n"
        result += f"💨 Wind: {current.get('wind_speed_10m')} km/h\n\n**7-Day Forecast:**\n"

        for i, date in enumerate(daily.get("time", [])[:7]):
            result += f"- {date}: {daily.get('temperature_2m_min', [])[i]}°C to {daily.get('temperature_2m_max', [])[i]}°C\n"
        return result
    except Exception as e:
        return f"Weather error: {str(e)}"


def search_flights(origin: str, destination: str, departure_date: str, return_date: Optional[str] = None, adults: int = 1) -> str:
    try:
        token = get_amadeus_token()
        params = {"originLocationCode": origin.upper(), "destinationLocationCode": destination.upper(), "departureDate": departure_date, "adults": adults, "currencyCode": "USD", "max": 5}
        if return_date:
            params["returnDate"] = return_date

        response = requests.get(AMADEUS_FLIGHT_URL, headers={"Authorization": f"Bearer {token}"}, params=params)

        if response.status_code == 200:
            offers = response.json().get("data", [])
            if not offers:
                return "No flights found."

            result = f"**Flights from {origin.upper()} to {destination.upper()}:**\n\n"
            for i, offer in enumerate(offers[:5], 1):
                price = offer.get("price", {})
                result += f"**Option {i}: ${price.get('total', 'N/A')} {price.get('currency', 'USD')}**\n"
                for j, itin in enumerate(offer.get("itineraries", [])):
                    trip = "Outbound" if j == 0 else "Return"
                    result += f"  {trip} ({itin.get('duration')}):\n"
                    for seg in itin.get("segments", []):
                        result += f"    ✈️ {seg.get('carrierCode')}{seg.get('number')}: {seg['departure']['iataCode']} → {seg['arrival']['iataCode']}\n"
                result += "\n"
            return result
        return f"Flight search failed: {response.status_code}"
    except Exception as e:
        return f"Flight search error: {str(e)}"


def search_hotels(city_code: str, check_in_date: str, check_out_date: str, adults: int = 1) -> str:
    try:
        token = get_amadeus_token()
        headers = {"Authorization": f"Bearer {token}"}

        list_response = requests.get(AMADEUS_HOTEL_LIST_URL, headers=headers, params={"cityCode": city_code.upper(), "radius": 10, "radiusUnit": "KM"})
        hotel_ids = [h.get("hotelId") for h in list_response.json().get("data", [])[:5] if h.get("hotelId")] if list_response.status_code == 200 else []

        if not hotel_ids:
            return f"No hotels found in {city_code.upper()}. Try: PAR, NYC, LON, TYO"

        offers_response = requests.get(AMADEUS_HOTEL_OFFERS_URL, headers=headers, params={"hotelIds": ",".join(hotel_ids), "checkInDate": check_in_date, "checkOutDate": check_out_date, "adults": adults, "currency": "USD"})

        if offers_response.status_code == 200:
            hotels = offers_response.json().get("data", [])
            if not hotels:
                return "No hotel offers available."

            result = f"**Hotels in {city_code.upper()} ({check_in_date} to {check_out_date}):**\n\n"
            for i, hotel in enumerate(hotels[:5], 1):
                name = hotel.get("hotel", {}).get("name", "Unknown")
                offers = hotel.get("offers", [])
                if offers:
                    price = offers[0].get("price", {})
                    result += f"🏨 **{i}. {name}**\n   💰 ${price.get('total', 'N/A')} {price.get('currency', 'USD')}\n\n"
            return result
        return f"Hotel search failed: {offers_response.status_code}"
    except Exception as e:
        return f"Hotel search error: {str(e)}"


def _parse_flights(query: str) -> str:
    parts = query.split("|")
    if len(parts) < 3:
        return "Use format: origin|destination|departure_date|return_date|adults"
    return search_flights(parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip() if len(parts) > 3 and parts[3].strip() else None, int(parts[4]) if len(parts) > 4 and parts[4].strip() else 1)


def _parse_hotels(query: str) -> str:
    parts = query.split("|")
    if len(parts) < 3:
        return "Use format: city_code|check_in|check_out|adults"
    return search_hotels(parts[0].strip(), parts[1].strip(), parts[2].strip(), int(parts[3]) if len(parts) > 3 and parts[3].strip() else 1)


def create_tools() -> List[Tool]:
    return [
        Tool(name="web_search", func=serp_search, description="Search web for travel info. Input: search query string."),
        Tool(name="get_weather", func=get_weather, description="Get weather for a location. Input: city name (e.g., 'Paris')."),
        Tool(name="search_flights", func=_parse_flights, description="Search flights. Input: 'origin|destination|departure_date|return_date|adults' (e.g., 'JFK|CDG|2024-06-15|2024-06-22|2')"),
        Tool(name="search_hotels", func=_parse_hotels, description="Search hotels. Input: 'city_code|check_in|check_out|adults' (e.g., 'PAR|2024-06-15|2024-06-22|2')"),
    ]


def create_agent():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)
    tools = create_tools()
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key="output")

    prompt = PromptTemplate(
        input_variables=["input", "chat_history", "tools", "tool_names", "agent_scratchpad"],
        template="""You are a travel planning assistant with access to conversation history.
Reference previous context when users say "there" or mention earlier destinations.

IATA codes: Paris(CDG/PAR), New York(JFK/NYC), London(LHR/LON), Tokyo(NRT/TYO)

TOOLS: {tools}
TOOL NAMES: {tool_names}
CONVERSATION HISTORY: {chat_history}

USER INPUT: {input}

Format:
Thought: [reasoning]
Action: [tool name]
Action Input: [input]

When done:
Thought: I have enough information
Final Answer: [response]

Begin!
Thought: {agent_scratchpad}"""
    )

    agent = create_react_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=False, handle_parsing_errors=True, max_iterations=5, return_intermediate_steps=True)
    return executor, memory


def get_memory_display(memory):
    """Format memory for display"""
    memory_vars = memory.load_memory_variables({})
    history = memory_vars.get("chat_history", [])

    if not history:
        return "📭 *Empty - No conversation history yet*"

    display = ""
    for msg in history:
        if hasattr(msg, 'type'):
            role = "🧑 Human" if msg.type == "human" else "🤖 AI"
            content = msg.content if hasattr(msg, 'content') else str(msg)
            content = content[:300] + "..." if len(content) > 300 else content
            display += f"**{role}:** {content}\n\n"
    return display


# Streamlit App
st.set_page_config(page_title="Short-Term Memory Demo", page_icon="🧠", layout="wide")

st.title("🧠 LangChain Short-Term Memory Demo")
st.markdown("""
This demo shows how **ConversationBufferMemory** maintains context across messages.
The agent remembers everything you've said and can reference previous context.
""")

# Sidebar - Memory visualization
with st.sidebar:
    st.header("📚 Memory Buffer")
    st.markdown("*Watch how conversation history accumulates*")
    st.divider()

    if "memory" in st.session_state:
        st.markdown(get_memory_display(st.session_state.memory))
    else:
        st.markdown("📭 *Start a conversation to see memory*")

    st.divider()
    if st.button("🗑️ Clear Memory", use_container_width=True):
        for key in ["messages", "agent", "memory"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Info expander
with st.expander("ℹ️ How Short-Term Memory Works", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **What is ConversationBufferMemory?**
        - Stores the **complete** conversation history
        - Every message (human + AI) is retained
        - Sent to LLM with each new request
        - Enables contextual references ("there", "that place")
        """)
    with col2:
        st.markdown("""
        **Try this conversation flow:**
        1. "Tell me about Paris"
        2. "What's the weather there?" *(references Paris)*
        3. "Find flights from NYC to there" *(still knows Paris)*
        4. "What about hotels?" *(remembers destination + dates)*
        """)

# Initialize agent
if "agent" not in st.session_state:
    with st.spinner("Initializing Travel Agent..."):
        st.session_state.agent, st.session_state.memory = create_agent()
        st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about travel destinations, weather, flights, or hotels..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = st.session_state.agent.invoke({"input": prompt})
                output = response.get("output", "I couldn't generate a response.")

                # Show tool usage if any
                steps = response.get("intermediate_steps", [])
                if steps:
                    with st.expander("🔧 Tools Used", expanded=False):
                        for action, result in steps:
                            st.markdown(f"**{action.tool}**: `{action.tool_input}`")
                            st.text(result[:500] + "..." if len(str(result)) > 500 else result)

                st.markdown(output)
                st.session_state.messages.append({"role": "assistant", "content": output})
            except Exception as e:
                st.error(f"Error: {str(e)}")

    st.rerun()

# Footer
st.divider()
st.caption("💡 The sidebar shows the raw memory buffer - notice how it grows with each exchange!")
