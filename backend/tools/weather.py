import httpx
from loguru import logger

async def get_weather(city: str) -> str:
    """
    מחזיר את מזג האוויר הנוכחי והתחזית למחר בעיר (Return current weather and tomorrow's forecast).
    :param city: City name ALWAYS IN ENGLISH (e.g., 'Tel Aviv', 'Holon', 'Moscow'). Translate from Hebrew to English before calling.
    """
    logger.info(f"Запрос погоды для города: {city}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            geo_response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1}
            )
            geo_response.raise_for_status()
            
            geo_data = geo_response.json()
            results = geo_data.get("results")
            
            if not results:
                logger.info(f"Город {city} не найден")
                return f"מצטער, לא מצאתי את העיר {city} במערכת."
                
            lat = results[0]["latitude"]
            lon = results[0]["longitude"]
            city_found = results[0]["name"]
            
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=auto"
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            current = data.get("current", {})
            daily = data.get("daily", {})
            
            temp_now = current.get("temperature_2m", 0)
            
            # Helper to decode weather code
            def get_desc(code):
                if code == 0: return "שמשי (Ясно)"
                elif 1 <= code <= 3: return "מעונן חלקי (Облачно)"
                elif 45 <= code <= 48: return "ערפל (Туман)"
                elif 51 <= code <= 67: return "גשום (Дождь)"
                elif 71 <= code <= 77: return "שלג (Снег)"
                elif 80 <= code <= 82: return "ממטרים (Ливень)"
                elif code >= 95: return "סערה (Гроза)"
                return "רגיל (Обычно)"

            desc_now = get_desc(current.get("weather_code", 0))
            
            today_max = daily.get("temperature_2m_max", [0,0])[0]
            today_min = daily.get("temperature_2m_min", [0,0])[0]
            
            tom_max = daily.get("temperature_2m_max", [0,0])[1] if len(daily.get("temperature_2m_max", [])) > 1 else '?'
            tom_min = daily.get("temperature_2m_min", [0,0])[1] if len(daily.get("temperature_2m_min", [])) > 1 else '?'
            tom_desc = get_desc(daily.get("weather_code", [0,0])[1]) if len(daily.get("weather_code", [])) > 1 else '?'

            result = (
                f"Location: {city_found}. "
                f"Right now: {temp_now}°C, {desc_now}. "
                f"Today min/max: {today_min}°C to {today_max}°C. "
                f"Tomorrow min/max: {tom_min}°C to {tom_max}°C, {tom_desc}."
            )
            logger.info(f"Результат погоды: {result}")
            return result
            
    except Exception as e:
        logger.error(f"Ошибка получения погоды: {e}")
        return f"מצטער, הייתה לי שגיאה בבדיקת הרשת."

def get_weather_sync(city: str) -> str:
    """Synchronous wrapper for legacy SDKs"""
    import asyncio
    return asyncio.run(get_weather(city))
