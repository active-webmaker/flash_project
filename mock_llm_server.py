import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
import time
import uuid
from typing import List, Dict, Any, Optional

# Basic Pydantic models for OpenAI compatibility
from pydantic import BaseModel

class ToolCallFunction(BaseModel):
    name: str
    arguments: str

class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: ToolCallFunction

class ResponseMessage(BaseModel):
    role: str = "assistant"
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None

class Choice(BaseModel):
    index: int = 0
    message: ResponseMessage
    finish_reason: str

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str = "mock-llm-v1"
    choices: List[Choice]

app = FastAPI()

@app.post("/v1/chat/completions")
async def create_chat_completion(request: Request):
    """
    Mock OpenAI Chat Completion endpoint.
    It alternates between calling the first available tool and providing a final answer.
    """
    body = await request.json()
    messages = body.get("messages", [])
    tools = body.get("tools", [])
    
    print("\n--- Mock LLM Server Received Request ---")
    print(json.dumps(body, indent=2))
    
    # Check the last message to decide the action
    last_message = messages[-1] if messages else {}
    
    # If the last message was a tool response, give a final answer.
    if last_message.get("role") == "function" or last_message.get("role") == "tool":
        response_message = ResponseMessage(
            content="Mock LLM: Tool execution acknowledged. The task is complete."
        )
        finish_reason = "stop"
    # If tools are available and we haven't called one yet, call the first one.
    elif tools:
        first_tool_name = tools[0].get("function", {}).get("name", "unknown_tool")
        print(f"Mock LLM: Decided to call tool: {first_tool_name}")
        
        tool_call = ToolCall(
            id=f"call_{uuid.uuid4().hex[:6]}",
            function=ToolCallFunction(
                name=first_tool_name,
                arguments='{}'  # Send empty args for simplicity
            )
        )
        response_message = ResponseMessage(
            tool_calls=[tool_call]
        )
        finish_reason = "tool_calls"
    # Otherwise, just give a simple text response.
    else:
        response_message = ResponseMessage(
            content="Mock LLM: Hello! I am a mock server. The task is complete."
        )
        finish_reason = "stop"

    response = ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        created=int(time.time()),
        choices=[
            Choice(
                message=response_message,
                finish_reason=finish_reason
            )
        ]
    )
    
    print("\n--- Mock LLM Server Sending Response ---")
    print(response.model_dump_json(indent=2))
    
    return JSONResponse(content=response.model_dump(exclude_none=True))

@app.get("/v1/models")
async def list_models():
    """Mock models endpoint."""
    return JSONResponse(content={
        "object": "list",
        "data": [
            {"id": "mock-llm-v1", "object": "model", "created": int(time.time()), "owned_by": "mock"}
        ]
    })

if __name__ == "__main__":
    print("Starting Mock LLM Server...")
    print("OpenAI compatible API will be available at http://127.0.0.1:8008/v1")
    uvicorn.run(app, host="127.0.0.1", port=8008)
