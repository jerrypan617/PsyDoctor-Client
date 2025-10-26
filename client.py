import requests

# ============ 配置 ============
SERVER_URL = "http://118.195.153.228:8000"
TIMEOUT = 60
# ==============================

def chat(message, temperature=0.7):
    """与心理医生对话"""
    url = f"{SERVER_URL}/chat"
    
    data = {
        "messages": [{"role": "user", "content": message}],
        "temperature": temperature
    }
    
    try:
        response = requests.post(url, json=data, timeout=TIMEOUT)
        if response.status_code == 200:
            return response.json()["response"]
        else:
            return f"错误: {response.status_code}"
    except Exception as e:
        return f"连接错误: {e}"

if __name__ == "__main__":
    
    while True:
        message = input("\n你: ").strip()
        
        if message.lower() in ['quit', 'exit', '退出', 'q']:
            print("医生: 感谢你的咨询，再见。")
            break
        
        if not message:
            continue
        reply = chat(message)
        print(f"\n医生: {reply}")

