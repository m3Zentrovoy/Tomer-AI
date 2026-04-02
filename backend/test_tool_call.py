import asyncio
import os
import httpx
from google import genai
from google.genai import types

async def get_weather(city: str) -> str:
    """Определяет текущую погоду в указанном городе.
    Args:
        city: Название города на английском (например, Tel Aviv, Moscow, Eilat).
    """
    try:
        # 1. Получаем координаты города
        geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
        async with httpx.AsyncClient() as client:
            geo_response = await client.get(geocode_url, params={"name": city, "count": 1})
            geo_response.raise_for_status()
            
            results = geo_response.json().get("results")
            if not results:
                return f"Не удалось найти город {city}."
                
            lat = results[0]["latitude"]
            lon = results[0]["longitude"]
            
        # 2. Получаем текущую погоду по координатам
        weather_url = "https://api.open-meteo.com/v1/forecast"
        async with httpx.AsyncClient() as client:
            weather_response = await client.get(
                weather_url, 
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,wind_speed_10m"
                }
            )
            weather_response.raise_for_status()
            
            data = weather_response.json()
            temp = data["current"]["temperature_2m"]
            wind = data["current"].get("wind_speed_10m", 0)
            
            return f"Погода в {city}: {temp} градусов цельсия. Ветер: {wind} км/ч."

    except Exception as e:
        return f"Ошибка при получении погоды: {str(e)}"

# Define it for Gemini
weather_declaration = types.FunctionDeclaration(
    name="get_weather",
    description="Узнает текущую погоду в любом городе мира",
    parameters=types.Schema(
        type="OBJECT",
        properties={"city": types.Schema(type="STRING", description="City name in English, ex: Tel Aviv")},
        required=["city"]
    )
)

async def test():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    config = types.LiveConnectConfig(
        tools=[{"function_declarations": [weather_declaration]}],
        system_instruction=types.Content(role="system", parts=[types.Part.from_text("If user asks about weather, call the tool.")])
    )
    print("Starting session...")
    async with client.aio.live.connect(model="gemini-2.5-flash-native-audio-latest", config=config) as session:
        await session.send(input="What is the weather in Tel Aviv? Only call the tool.")
        async for msg in session.receive():
            print("Received:")
            if msg.server_content:
                if msg.server_content.model_turn:
                    for part in msg.server_content.model_turn.parts:
                        print("  Text:", getattr(part, "text", None))
                        if part.executable_code:
                            print("  Code:", part.executable_code)
                elif msg.server_content.interrupted:
                    print("  Interrupted")
            if msg.tool_call:
                print("  TOOL CALL:", msg.tool_call)
                # execute it
                for fc in msg.tool_call.function_calls:
                    print(f"executing {fc.name} with {fc.args}")
                    result = await get_weather(**fc.args)
                    print("sending result:", result)
                    resp = types.LiveClientContent(
                        tool_response=types.ToolResponse(
                            function_responses=[types.FunctionResponse(
                                id=fc.id,
                                name=fc.name,
                                response={"result": result}
                            )]
                        )
                    )
                    await session.send(input=resp)
        print("Done")
asyncio.run(test())
