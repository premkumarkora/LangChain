"""
News MCP Server (Using FREE NewsData.io API)
=============================================

This MCP server provides news tools using the NewsData.io API.

WHY NEWSDATA.IO?
----------------
- FREE tier: 200 requests/day (generous for learning/testing)
- Simple registration (just email)
- Real-time news from 70,000+ sources
- Supports search, headlines, and category filtering
- Good documentation

GETTING YOUR FREE API KEY:
--------------------------
1. Go to: https://newsdata.io/register
2. Sign up with your email
3. Verify your email
4. Copy your API key from the dashboard
5. Add it to your .env file as NEWSDATA_API_KEY=your_key_here

API DOCUMENTATION:
------------------
- Docs: https://newsdata.io/documentation
- News endpoint: https://newsdata.io/api/1/news
- Parameters: apikey, q (query), country, category, language

HOW THIS MCP SERVER WORKS:
--------------------------
1. Agent asks for news (e.g., "Find news about AI")
2. Our tool receives the request via MCP
3. We call the NewsData.io API with the search query
4. We format the articles into readable text
5. Return the result via MCP protocol
6. Agent uses this in its response to the user

To run this server standalone:
    python news_server.py
"""

import os
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import httpx
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize MCP server
mcp = FastMCP("news-server")

# NewsData.io API configuration
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "")
NEWSDATA_BASE_URL = "https://newsdata.io/api/1"

# Valid categories for filtering
VALID_CATEGORIES = [
    "business", "entertainment", "environment", "food", "health",
    "politics", "science", "sports", "technology", "top", "world"
]


def _format_articles(articles: list, max_articles: int = 5) -> str:
    """
    Format news articles into readable text for the LLM.

    NewsData.io returns articles like:
    {
        "title": "Article Title",
        "description": "Brief description...",
        "source_id": "cnn",
        "pubDate": "2024-01-15 12:30:00",
        "link": "https://..."
    }
    """
    if not articles:
        return "No articles found matching your criteria."

    formatted = []
    for i, article in enumerate(articles[:max_articles], 1):
        title = article.get("title", "No title")
        description = article.get("description") or article.get("content", "No description available")
        source = article.get("source_id", "Unknown source")
        pub_date = article.get("pubDate", "Unknown date")
        link = article.get("link", "")

        # Clean up description (sometimes it's too long or has HTML)
        if description:
            # Remove any HTML tags (simple approach)
            import re
            description = re.sub(r'<[^>]+>', '', description)
            # Truncate if too long
            if len(description) > 250:
                description = description[:250] + "..."

        formatted.append(f"""
{i}. {title}
   📰 Source: {source} | 📅 {pub_date}
   {description}
   🔗 {link}
""")

    return "\n".join(formatted)


# =============================================================================
# MCP TOOLS - Exposed to LangChain agents
# =============================================================================

@mcp.tool()
async def search_news(query: str, language: str = "en") -> str:
    """
    Search for news articles matching a specific query.

    This tool searches across thousands of news sources for articles
    containing your search terms. Great for finding news about specific
    topics, events, companies, or people.

    Args:
        query: Search query (e.g., "artificial intelligence", "Tesla", "climate change")
               You can use AND, OR for complex queries.
        language: Language code for results (default: "en" for English)
                  Options: en, de, fr, es, it, pt, ru, zh, ja, ar, etc.

    Returns:
        A list of up to 5 relevant news articles with titles, descriptions, and links.

    Examples:
        - search_news("artificial intelligence")
        - search_news("London weather")
        - search_news("Tesla earnings")
        - search_news("Japan technology", "en")

    API Call:
        GET https://newsdata.io/api/1/news?apikey=XXX&q=query&language=en
    """
    print(f"\n🔍 [News Server] Tool called: search_news")
    print(f"   Parameters: query='{query}', language='{language}'")

    if not NEWSDATA_API_KEY:
        return """Error: NEWSDATA_API_KEY not set.

To get your FREE API key:
1. Go to https://newsdata.io/register
2. Sign up with your email
3. Copy your API key from the dashboard
4. Add to .env file: NEWSDATA_API_KEY=your_key_here"""

    try:
        print(f"   🌐 Searching NewsData.io for '{query}'...")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{NEWSDATA_BASE_URL}/news",
                params={
                    "apikey": NEWSDATA_API_KEY,
                    "q": query,
                    "language": language,
                },
                timeout=15.0
            )

            # Handle various response codes
            if response.status_code == 401:
                return "Error: Invalid API key. Please check your NEWSDATA_API_KEY."
            elif response.status_code == 429:
                return "Error: API rate limit exceeded. Free tier allows 200 requests/day."
            elif response.status_code != 200:
                return f"Error: API returned status {response.status_code}"

            data = response.json()

            # Check for API errors in response
            if data.get("status") == "error":
                error_msg = data.get("results", {}).get("message", "Unknown error")
                return f"Error from NewsData.io: {error_msg}"

            articles = data.get("results", [])
            total_results = data.get("totalResults", len(articles))

            result = f"Found {total_results} articles for '{query}':\n"
            result += "=" * 50
            result += _format_articles(articles)

            print(f"   ✅ Successfully found {len(articles)} articles")
            return result

    except httpx.TimeoutException:
        return "Error: Request timed out. Please try again."
    except httpx.RequestError as e:
        return f"Error: Failed to connect to news API: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error: {str(e)}"


@mcp.tool()
async def get_headlines(
    category: Optional[str] = None,
    country: str = "us"
) -> str:
    """
    Get the latest top news headlines.

    This tool fetches current headlines from major news sources.
    You can filter by category and/or country.

    Args:
        category: News category to filter. Options:
                  business, entertainment, environment, food, health,
                  politics, science, sports, technology, top, world
                  If not specified, returns general top headlines.
        country: 2-letter country code (default: "us")
                 Examples: us, gb, de, fr, jp, au, ca, in

    Returns:
        A list of current top headlines with sources and links.

    Examples:
        - get_headlines()                          # US general news
        - get_headlines("technology")              # Tech news
        - get_headlines("business", "gb")          # UK business news
        - get_headlines("sports", "de")            # German sports news

    API Call:
        GET https://newsdata.io/api/1/news?apikey=XXX&country=us&category=tech
    """
    print(f"\n📰 [News Server] Tool called: get_headlines")
    print(f"   Parameters: category={category}, country={country}")

    if not NEWSDATA_API_KEY:
        return """Error: NEWSDATA_API_KEY not set.

To get your FREE API key:
1. Go to https://newsdata.io/register
2. Sign up with your email
3. Copy your API key from the dashboard
4. Add to .env file: NEWSDATA_API_KEY=your_key_here"""

    # Validate category if provided
    if category and category.lower() not in VALID_CATEGORIES:
        return f"Error: Invalid category '{category}'. Valid options: {', '.join(VALID_CATEGORIES)}"

    try:
        print(f"   🌐 Fetching headlines from NewsData.io...")

        params = {
            "apikey": NEWSDATA_API_KEY,
            "country": country,
            "language": "en",
        }

        if category:
            params["category"] = category.lower()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{NEWSDATA_BASE_URL}/news",
                params=params,
                timeout=15.0
            )

            if response.status_code == 401:
                return "Error: Invalid API key. Please check your NEWSDATA_API_KEY."
            elif response.status_code == 429:
                return "Error: API rate limit exceeded. Free tier allows 200 requests/day."
            elif response.status_code != 200:
                return f"Error: API returned status {response.status_code}"

            data = response.json()

            if data.get("status") == "error":
                error_msg = data.get("results", {}).get("message", "Unknown error")
                return f"Error from NewsData.io: {error_msg}"

            articles = data.get("results", [])

            category_str = f" ({category})" if category else ""
            result = f"Top Headlines - {country.upper()}{category_str}:\n"
            result += "=" * 50
            result += _format_articles(articles)

            print(f"   ✅ Successfully fetched {len(articles)} headlines")
            return result

    except httpx.TimeoutException:
        return "Error: Request timed out. Please try again."
    except httpx.RequestError as e:
        return f"Error: Failed to connect to news API: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error: {str(e)}"


@mcp.tool()
async def get_news_by_country(country: str, topic: Optional[str] = None) -> str:
    """
    Get news from a specific country, optionally filtered by topic.

    Use this when you want news from a particular country or region.
    Good for finding local news or country-specific stories.

    Args:
        country: 2-letter country code
                 Examples: us (USA), gb (UK), de (Germany), fr (France),
                          jp (Japan), au (Australia), in (India), ca (Canada)
        topic: Optional search topic to filter results

    Returns:
        News articles from the specified country.

    Examples:
        - get_news_by_country("gb")                    # UK news
        - get_news_by_country("jp", "technology")      # Japan tech news
        - get_news_by_country("de", "economy")         # German economy news
    """
    print(f"\n🌍 [News Server] Tool called: get_news_by_country")
    print(f"   Parameters: country={country}, topic={topic}")

    if not NEWSDATA_API_KEY:
        return """Error: NEWSDATA_API_KEY not set.

To get your FREE API key:
1. Go to https://newsdata.io/register
2. Sign up with your email
3. Copy your API key from the dashboard"""

    try:
        print(f"   🌐 Fetching news from {country.upper()}...")

        params = {
            "apikey": NEWSDATA_API_KEY,
            "country": country,
            "language": "en",
        }

        if topic:
            params["q"] = topic

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{NEWSDATA_BASE_URL}/news",
                params=params,
                timeout=15.0
            )

            if response.status_code == 401:
                return "Error: Invalid API key. Please check your NEWSDATA_API_KEY."
            elif response.status_code == 429:
                return "Error: API rate limit exceeded. Free tier allows 200 requests/day."
            elif response.status_code != 200:
                return f"Error: API returned status {response.status_code}"

            data = response.json()

            if data.get("status") == "error":
                error_msg = data.get("results", {}).get("message", "Unknown error")
                return f"Error from NewsData.io: {error_msg}"

            articles = data.get("results", [])

            topic_str = f" about '{topic}'" if topic else ""
            result = f"News from {country.upper()}{topic_str}:\n"
            result += "=" * 50
            result += _format_articles(articles)

            print(f"   ✅ Successfully fetched {len(articles)} articles from {country.upper()}")
            return result

    except httpx.TimeoutException:
        return "Error: Request timed out. Please try again."
    except httpx.RequestError as e:
        return f"Error: Failed to connect to news API: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error: {str(e)}"


# =============================================================================
# SERVER STARTUP
# =============================================================================

if __name__ == "__main__":
    print("📰 Starting News MCP Server (NewsData.io - FREE tier: 200 req/day)")
    print("   Tools available: search_news, get_headlines, get_news_by_country")

    if not NEWSDATA_API_KEY:
        print("\n   ⚠️  WARNING: NEWSDATA_API_KEY not set!")
        print("   Get your free key at: https://newsdata.io/register")

    print("   Waiting for MCP protocol messages via stdio...")
    mcp.run()
