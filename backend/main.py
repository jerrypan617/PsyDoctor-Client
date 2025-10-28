from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import requests

# ============ 配置 ============
SERVER_URL = "http://129.211.218.58:8000"
TIMEOUT = 60
# ==============================

app = FastAPI(title="心理医生聊天 API - 云服务器代理")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 请求模型
class ChatRequest(BaseModel):
    message: str
    conversation_history: List[dict] = []
    temperature: float = 0.7

class ChatResponse(BaseModel):
    response: str

@app.get("/")
async def root():
    return {"message": "心理医生聊天 API 运行中"}

@app.options("/chat")
async def chat_options():
    """处理 CORS 预检请求"""
    return {"message": "OK"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求 - 转发到云服务器"""
    try:
        # 构建消息列表（格式与 client.py 保持一致）
        messages = []
        
        # 添加对话历史
        if request.conversation_history:
            messages = request.conversation_history.copy()
        else:
            # 如果没历史，初始化系统消息
            messages = [
                {
                    "role": "system",
                    "content": "你是一位专业的心理医生，擅长倾听和提供建议。请用温和、理解、专业的方式与来访者交流。"
                }
            ]
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": request.message})
        
        # 发送请求到云服务器
        url = f"{SERVER_URL}/chat"
        data = {
            "messages": messages,
            "temperature": request.temperature
        }
        
        response = requests.post(url, json=data, timeout=TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            return ChatResponse(response=result["response"])
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"云服务器错误: {response.status_code}"
            )
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="请求超时，请稍后再试")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="无法连接到云服务器")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
