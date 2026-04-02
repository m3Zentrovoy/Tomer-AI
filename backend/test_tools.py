from google.genai import types

def get_weather(city: str) -> str:
    """Returns weather for a given city."""
    return f"Weather in {city} is sunny."

config = types.LiveConnectConfig(tools=[get_weather])
print("Tools mapped:")
print(config.tools)
