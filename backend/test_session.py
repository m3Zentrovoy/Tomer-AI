import asyncio
import os
from google import genai
from google.genai import types

async def test():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    config = types.LiveConnectConfig(response_modalities=["AUDIO"])
    async with client.aio.live.connect(model="gemini-2.5-flash-native-audio-latest", config=config) as session:
        print("dir session:")
        print(dir(session))
        print("methods of session:")
        print([m for m in dir(session) if callable(getattr(session, m))])
        
asyncio.run(test())
