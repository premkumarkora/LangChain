"""Streamlit Demo: LangChain Short-Term Memory (Conversation Buffer)"""

import os
import requests
import random
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
import streamlit as st

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

load_dotenv()

SERP_API_KEY = os.getenv("SERP_API")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


@tool
def web_search(query: str) -> str:
    """Search web for travel destination info. Use for attractions, restaurants, activities."""
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


@tool
def get_weather(location: str) -> str:
    """Get current weather and 7-day forecast. Input: city name like 'Paris' or 'Tokyo'."""
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

        weather_codes = {0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Foggy", 51: "Light drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain", 80: "Rain showers", 95: "Thunderstorm"}

        result = f"Weather for {loc.get('name')}, {loc.get('country')}:\n\n"
        result += f"Temperature: {current.get('temperature_2m')}°C (feels like {current.get('apparent_temperature')}°C)\n"
        result += f"Conditions: {weather_codes.get(current.get('weather_code', 0), 'Unknown')}\n"
        result += f"Humidity: {current.get('relative_humidity_2m')}%\n"
        result += f"Wind: {current.get('wind_speed_10m')} km/h\n\n7-Day Forecast:\n"

        for i, date in enumerate(daily.get("time", [])[:7]):
            cond = weather_codes.get(daily.get("weather_code", [])[i] if i < len(daily.get("weather_code", [])) else 0, "Unknown")
            result += f"- {date}: {daily.get('temperature_2m_min', [])[i]}°C to {daily.get('temperature_2m_max', [])[i]}°C, {cond}\n"
        return result
    except Exception as e:
        return f"Weather error: {str(e)}"


@tool
def search_flights(origin: str, destination: str, departure_date: str, return_date: str = "", adults: int = 1) -> str:
    """Search flights between cities. Dates in YYYY-MM-DD format."""
    airlines = ["Air France", "United", "Delta", "Emirates", "Lufthansa", "British Airways", "Singapore Airlines", "Qatar Airways"]

    result = f"Flights from {origin.upper()} to {destination.upper()} on {departure_date}:\n\n"

    for i in range(1, 4):
        airline = random.choice(airlines)
        price = random.randint(400, 1200)
        dep_hour = random.randint(6, 20)
        duration = random.randint(2, 14)
        stops = random.choice(["Nonstop", "1 stop", "1 stop"])

        result += f"Option {i}: ${price} USD\n"
        result += f"  {airline} - {stops}\n"
        result += f"  Departs: {dep_hour:02d}:00 | Duration: {duration}h\n\n"

    if return_date:
        result += f"\nReturn flights on {return_date} also available at similar prices."

    result += "\n(Demo data - actual prices may vary)"
    return result


@tool
def search_hotels(city: str, check_in_date: str, check_out_date: str, guests: int = 1) -> str:
    """Search hotels in a city. Dates in YYYY-MM-DD format."""
    hotel_types = [
        ("Grand", ["Hotel", "Palace", "Resort"]),
        ("The", ["Ritz", "Plaza", "Continental", "Marriott", "Hilton"]),
        ("Royal", ["Inn", "Suites", "Lodge"]),
        ("City", ["Center Hotel", "View Suites", "Park Hotel"])
    ]

    result = f"Hotels in {city} ({check_in_date} to {check_out_date}):\n\n"

    for i in range(1, 4):
        prefix, suffixes = random.choice(hotel_types)
        suffix = random.choice(suffixes)
        name = f"{prefix} {suffix} {city}"
        price = random.randint(80, 350)
        rating = round(random.uniform(3.5, 4.9), 1)

        result += f"{i}. {name}\n"
        result += f"   ${price}/night | Rating: {rating}/5\n"
        result += f"   Amenities: WiFi, Breakfast, Pool\n\n"

    result += "(Demo data - actual prices may vary)"
    return result


def create_agent():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)
    tools = [web_search, get_weather, search_flights, search_hotels]
    llm_with_tools = llm.bind_tools(tools)
    return llm_with_tools, tools


def process_tool_calls(response, tools):
    tool_results = []
    tool_map = {t.name: t for t in tools}

    for tool_call in response.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        if tool_name in tool_map:
            result = tool_map[tool_name].invoke(tool_args)
            tool_results.append({"name": tool_name, "args": tool_args, "result": result, "id": tool_call["id"]})

    return tool_results


def run_agent(llm_with_tools, tools, messages):
    system_msg = SystemMessage(content="""You are a travel planning assistant. You help users with destinations, weather, flights, and hotels.
Use the conversation history to understand context. When users say "there" or reference earlier topics, use that context.
Always provide helpful, concise responses based on tool results.""")

    full_messages = [system_msg] + messages
    response = llm_with_tools.invoke(full_messages)

    all_tool_results = []
    max_iterations = 5
    iteration = 0

    while response.tool_calls and iteration < max_iterations:
        iteration += 1
        tool_results = process_tool_calls(response, tools)
        all_tool_results.extend(tool_results)

        tool_messages = [ToolMessage(content=tr["result"], tool_call_id=tr["id"]) for tr in tool_results]
        full_messages = full_messages + [response] + tool_messages
        response = llm_with_tools.invoke(full_messages)

    return response.content, all_tool_results


def get_memory_display(messages):
    if not messages:
        return "*Empty - No conversation history yet*"

    display = ""
    for msg in messages:
        if isinstance(msg, HumanMessage):
            content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
            display += f"**Human:** {content}\n\n"
        elif isinstance(msg, AIMessage):
            content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
            display += f"**AI:** {content}\n\n"
    return display


st.set_page_config(page_title="Short-Term Memory Demo", page_icon=" ", layout="wide")

st.title("LangChain Short-Term Memory Demo")
st.markdown("This demo shows how **ConversationBufferMemory** maintains context across messages.")

with st.sidebar:
    st.header("Memory Buffer")
    st.markdown("*Watch how conversation history accumulates*")
    st.divider()

    if "memory_messages" in st.session_state and st.session_state.memory_messages:
        st.markdown(get_memory_display(st.session_state.memory_messages))
    else:
        st.markdown("*Start a conversation to see memory*")

    st.divider()
    if st.button("Clear Memory", use_container_width=True):
        for key in ["messages", "memory_messages", "llm", "tools"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

with st.expander("How Short-Term Memory Works", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **What is ConversationBufferMemory?**
        - Stores the **complete** conversation history
        - Every message (human + AI) is retained
        - Sent to LLM with each new request
        - Enables contextual references
        """)
    with col2:
        st.markdown("""
        **Try this flow:**
        1. "Tell me about Paris"
        2. "What's the weather there?"
        3. "Find flights from NYC to there"
        4. "What about hotels?"
        """)

if "llm" not in st.session_state:
    with st.spinner("Initializing..."):
        st.session_state.llm, st.session_state.tools = create_agent()
        st.session_state.messages = []
        st.session_state.memory_messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "tools_used" in message and message["tools_used"]:
            with st.expander("Tools Used"):
                for t in message["tools_used"]:
                    st.markdown(f"**{t['name']}**: `{t['args']}`")
                    st.text(t['result'][:500] + "..." if len(str(t['result'])) > 500 else t['result'])

if prompt := st.chat_input("Ask about travel destinations, weather, flights, or hotels..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.memory_messages.append(HumanMessage(content=prompt))

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                output, tool_results = run_agent(st.session_state.llm, st.session_state.tools, st.session_state.memory_messages)

                if tool_results:
                    with st.expander("Tools Used"):
                        for t in tool_results:
                            st.markdown(f"**{t['name']}**: `{t['args']}`")
                            st.text(t['result'][:500] + "..." if len(str(t['result'])) > 500 else t['result'])

                st.markdown(output)
                st.session_state.messages.append({"role": "assistant", "content": output, "tools_used": tool_results})
                st.session_state.memory_messages.append(AIMessage(content=output))
            except Exception as e:
                st.error(f"Error: {str(e)}")

    st.rerun()

st.divider()
st.caption("The sidebar shows the memory buffer - notice how it grows with each exchange!")
