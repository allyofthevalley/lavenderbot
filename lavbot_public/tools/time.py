from datetime import datetime
import zoneinfo

async def tool_time():
    """
    Returns the current date and time in Ally's timezone (Vancouver).
    """
    tz = zoneinfo.ZoneInfo("America/Vancouver")
    now = datetime.now(tz)
    return now.strftime("It is %A, %B %d, %Y — %I:%M %p")
