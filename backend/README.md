# 心理医生聊天后端

本后端作为代理，将请求转发到云服务器上的模型服务。

## 服务器配置

在 `main.py` 中配置云服务器地址：

```python
SERVER_URL = "http://129.211.218.58:8000"  # 你的云服务器地址
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行服务

```bash
python main.py
```

或使用 uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

服务将在 http://localhost:8000 启动

## 接口说明

- `POST /chat`: 接收聊天请求并转发到云服务器
  - 请求体: `{"message": "用户消息", "conversation_history": [], "temperature": 0.7}`
  - 返回: `{"response": "模型回复"}`
