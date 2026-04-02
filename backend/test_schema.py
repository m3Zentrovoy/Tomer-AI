from google.genai import types

try:
    content = types.LiveClientContent(
        tool_response=types.ToolResponse(
            function_responses=[]
        )
    )
    print("tool_response is valid")
except Exception as e:
    print(f"Exception logic 1: {e}")

try:
    content = types.LiveClientContent(
        tool_responses=[types.FunctionResponse(id="1", name="name", response={})]
    )
    print("tool_responses[] is valid")
except Exception as e:
    print(f"Exception logic 2: {e}")
