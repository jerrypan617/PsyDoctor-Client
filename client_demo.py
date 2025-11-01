import requests
import sys
import os
import hashlib
import datetime
from typing import List, Dict

backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from memory_manager import MemoryManager  # type: ignore
except ImportError:
    print(f"错误: 无法导入memory_manager模块")
    print(f"请确保backend/memory_manager.py存在")
    sys.exit(1)

SERVER_URL = "http://129.211.164.244:8000"
TIMEOUT = 60

conversation_history: List[Dict] = []
conversation_id: str = None
memory_manager = MemoryManager(
    storage_path=os.path.join(os.path.dirname(__file__), "backend", "conversation_memory.json")
)

def generate_conversation_id(message: str) -> str:
    """生成对话ID"""
    return hashlib.md5(message.encode()).hexdigest()[:16]

def chat(message: str, temperature: float = 0.7):
    """与心理医生对话 - 使用RAG检索相关历史"""
    global conversation_history, conversation_id
    
    # 确定对话ID
    if not conversation_id:
        conversation_id = generate_conversation_id(message)
    
    # 为历史消息添加时间戳和conversation_id（如果没有）
    enriched_history = []
    for i, msg in enumerate(conversation_history):
        enriched_msg = msg.copy()
        if 'timestamp' not in enriched_msg and 'created_at' not in enriched_msg:
            timestamp = (datetime.datetime.now() - datetime.timedelta(
                minutes=len(conversation_history) - i
            )).isoformat()
            enriched_msg['timestamp'] = timestamp
        enriched_msg['conversation_id'] = conversation_id
        enriched_history.append(enriched_msg)
    
    # 使用RAG构建优化的上下文
    print(f"[RAG] 对话ID: {conversation_id}, 历史消息数: {len(enriched_history)}")
    
    messages = memory_manager.build_context(
        conversation_id=conversation_id,
        current_message=message,
        conversation_history=enriched_history
    )
    
    url = f"{SERVER_URL}/chat"
    data = {
        "messages": messages,
        "temperature": temperature
    }
    
    try:
        response = requests.post(url, json=data, timeout=TIMEOUT)
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "")
            
            # 保存对话历史到memory_manager
            user_msg = {
                "role": "user",
                "content": message,
                "timestamp": datetime.datetime.now().isoformat(),
                "conversation_id": conversation_id
            }
            assistant_msg = {
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.datetime.now().isoformat(),
                "conversation_id": conversation_id
            }
            
            # 添加到本地历史
            conversation_history.append(user_msg)
            conversation_history.append(assistant_msg)
            
            # 同步到memory_manager
            memory_manager.sync_conversation(
                conversation_id=conversation_id,
                messages=conversation_history,
                metadata={
                    'updated_at': datetime.datetime.now().isoformat(),
                    'title': message[:50] if len(message) > 50 else message
                }
            )
            
            return response_text
        else:
            return f"错误: {response.status_code}"
    except Exception as e:
        return f"连接错误: {e}"

def reset_conversation():
    """重置对话历史"""
    global conversation_history, conversation_id
    conversation_history = []
    conversation_id = None
    print("\n[系统] 对话已重置")

if __name__ == "__main__":
    print("=" * 60)
    print("心理医生聊天客户端 (RAG增强版)")
    print("=" * 60)
    print("提示: 输入 'quit' 或 'exit' 退出, 输入 'reset' 重置对话")
    print("=" * 60)
    
    while True:
        message = input("\n你: ").strip()
        
        if message.lower() in ['quit', 'exit', '退出', 'q']:
            print("\n医生: 感谢你的咨询，再见。")
            break
        
        if message.lower() in ['reset', '重置', 'r']:
            reset_conversation()
            continue
        
        if not message:
            continue
        
        print("\n[系统] 正在思考...")
        reply = chat(message)
        print(f"\n医生: {reply}")
