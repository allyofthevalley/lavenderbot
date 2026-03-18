import requests
from config import get_openweather_key

async def tool_weather(city: str):
    """Fetches current weather for a given city using OpenWeatherMap."""
    key = get_openweather_key()
    if not key:
        return "I don't have a weather API key configured yet."

    url = (
        f"http://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={key}&units=metric"
    )

    data = requests.get(url).json()

    # If the city isn't found
    if data.get("cod") != 200:
        return "I couldn’t find that place."

    temp = data["main"]["temp"]
    desc = data["weather"][0]["description"]

    return f"The weather in {city} is {temp}°C with {desc}."
