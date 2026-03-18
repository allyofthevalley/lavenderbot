import requests
from security import wrap_internet_content

async def tool_search_duckduckgo(query: str):
    """
    Uses DuckDuckGo's Instant Answer API to fetch summaries or definitions.
    Returns a short, friendly text result, wrapped as external content.
    """
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1&no_html=1"
    data = requests.get(url).json()

    result = ""

    # Direct summary
    if data.get("AbstractText"):
        result = data["AbstractText"]

    # Related topics (fallback)
    elif data.get("RelatedTopics"):
        for topic in data["RelatedTopics"]:
            if isinstance(topic, dict) and topic.get("Text"):
                result = topic["Text"]
                break

    if not result:
        result = "I couldn't find anything for that search."

    # Wrap as external content for safety
    return wrap_internet_content(result)
