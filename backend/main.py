from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
import logging
import datetime
import hashlib
from memory_manager import get_memory_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ 配置 ============
SERVER_URL = "http://129.211.164.244:8000"
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

@app.on_event("startup")
async def startup_event():
    """启动时预加载模型和索引"""
    logger.info("=" * 60)
    logger.info("后端服务启动中...")
    logger.info("=" * 60)
    logger.info("正在预加载RAG模型和索引...")
    
    try:
        # 预加载记忆管理器（这会加载embedding模型）
        memory_manager = get_memory_manager()
        logger.info("✓ Embedding模型加载成功")
        logger.info("✓ 向量缓存加载成功")
        logger.info("✓ FAISS索引加载成功")
        logger.info("=" * 60)
        logger.info("后端服务启动完成，准备接收请求")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"启动时加载模型失败: {e}", exc_info=True)
        raise

# 请求模型
class ChatRequest(BaseModel):
    message: str
    conversation_history: List[dict] = []
    temperature: float = 0.7
    conversation_id: Optional[str] = None  # 可选的对话ID，用于RAG检索

class ConversationSyncRequest(BaseModel):
    """对话同步请求"""
    messages: List[dict] = []
    title: Optional[str] = None
    updatedAt: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: Optional[str] = None  # 返回对话ID

@app.get("/")
async def root():
    return {"message": "心理医生聊天 API 运行中"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求 - 使用RAG检索相关历史并转发到云服务器"""
    try:
        # 获取记忆管理器
        memory_manager = get_memory_manager()
        
        # 确定对话ID
        conversation_id = request.conversation_id
        if not conversation_id:
            # 从历史消息中提取或生成
            if request.conversation_history:
                # 尝试从历史消息中找到conversation_id
                for msg in request.conversation_history:
                    if 'conversation_id' in msg:
                        conversation_id = msg['conversation_id']
                        break
                
                # 如果没有，基于第一条消息生成
                if not conversation_id:
                    first_msg = request.conversation_history[0]
                    content = first_msg.get('content', '')
                    conversation_id = hashlib.md5(content.encode()).hexdigest()[:16]
            else:
                # 新对话，基于当前消息生成ID
                conversation_id = hashlib.md5(request.message.encode()).hexdigest()[:16]
        
        # 使用RAG构建优化的上下文
        logger.info(f"对话ID: {conversation_id}, 历史消息数: {len(request.conversation_history)}, 当前消息: {request.message[:50]}...")
        
        # 为历史消息添加时间戳（如果没有）
        enriched_history = []
        for i, msg in enumerate(request.conversation_history):
            enriched_msg = msg.copy()
            if 'timestamp' not in enriched_msg and 'created_at' not in enriched_msg:
                timestamp = (datetime.datetime.now() - datetime.timedelta(
                    minutes=len(request.conversation_history) - i
                )).isoformat()
                enriched_msg['timestamp'] = timestamp
            enriched_msg['conversation_id'] = conversation_id
            enriched_history.append(enriched_msg)
        
        # 使用RAG构建上下文
        messages = memory_manager.build_context(
            conversation_id=conversation_id,
            current_message=request.message,
            conversation_history=enriched_history
        )
        
        # 发送请求到云服务器
        url = f"{SERVER_URL}/chat"
        data = {
            "messages": messages,
            "temperature": request.temperature
        }
        
        logger.info(f"发送到云服务器: {len(messages)} 条消息")
        
        response = requests.post(url, json=data, timeout=TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"收到云服务器响应: {result.get('response', '')[:50]}...")
            
            # 注意：不在这里保存消息，因为前端会同步完整的对话数据
            # 这里只用于RAG检索，完整数据以前端同步为准
            
            return ChatResponse(
                response=result["response"],
                conversation_id=conversation_id
            )
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
        logger.error(f"处理请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/conversation/{conversation_id}")
async def sync_conversation(conversation_id: str, request: ConversationSyncRequest):
    """同步对话（以前端数据为准）"""
    try:
        memory_manager = get_memory_manager()
        
        logger.info(f"收到同步请求: conversation_id={conversation_id}, 消息数量={len(request.messages)}")
        
        # 构建元数据
        metadata = {
            'updated_at': request.updatedAt or datetime.datetime.now().isoformat(),
            'title': request.title
        }
        
        success = memory_manager.sync_conversation(
            conversation_id=conversation_id,
            messages=request.messages,
            metadata=metadata
        )
        
        if success:
            logger.info(f"对话 {conversation_id} 同步成功")
            return {"status": "success", "message": f"对话 {conversation_id} 已同步"}
        else:
            logger.error(f"对话 {conversation_id} 同步失败")
            raise HTTPException(status_code=500, detail="同步对话失败")
    except Exception as e:
        logger.error(f"同步对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    try:
        memory_manager = get_memory_manager()
        success = memory_manager.delete_conversation(conversation_id)
        
        if success:
            return {"status": "success", "message": f"对话 {conversation_id} 已删除"}
        else:
            raise HTTPException(status_code=404, detail=f"对话 {conversation_id} 不存在")
    except Exception as e:
        logger.error(f"删除对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations")
async def list_conversations():
    """列出所有对话（用于调试）"""
    try:
        memory_manager = get_memory_manager()
        conversations = {}
        for conv_id, conv_data in memory_manager.memory.items():
            conversations[conv_id] = {
                'message_count': len(conv_data.get('messages', [])),
                'metadata': conv_data.get('metadata', {})
            }
        return {"conversations": conversations, "count": len(conversations)}
    except Exception as e:
        logger.error(f"列出对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # 使用8001端口，避免与云服务器SSH隧道冲突
    uvicorn.run(app, host="0.0.0.0", port=8001)
