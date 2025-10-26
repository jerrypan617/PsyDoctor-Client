# 心理医生聊天应用

一个美观、轻量级的心理医生聊天应用，使用 React + Tailwind CSS 前端和 FastAPI 后端。

## 项目结构

```
.
├── backend/          # FastAPI 后端
│   ├── main.py      # 主应用文件
│   └── requirements.txt
├── frontend/         # React 前端
│   ├── src/         # 源代码
│   ├── package.json
│   └── ...
└── README.md
```

## 快速开始

### 后端设置

1. 进入后端目录：
```bash
cd backend
```

2. 创建虚拟环境（推荐）：
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置云服务器地址（如果需要修改）：
编辑 `main.py` 中的 `SERVER_URL`：
```python
SERVER_URL = "http://118.195.153.228:8000"  # 你的云服务器地址
```

5. 运行后端：
```bash
python main.py
# 或
uvicorn main:app --reload
```

后端将在 http://localhost:8000 启动

### 前端设置

1. 进入前端目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 配置环境变量（可选）：
```bash
cp .env.example .env
# 如果后端不在 http://localhost:8000，请修改 VITE_API_URL
```

4. 运行前端：
```bash
npm run dev
```

前端将在 http://localhost:5173 启动

## 技术栈

- **前端**：
  - React 18
  - Tailwind CSS 3
  - Vite
  - Axios

- **后端**：
  - FastAPI
  - 连接云服务器模型 API
  - 作为代理转发请求

## 特性

- 🎨 现代化、美观的 UI 设计
- 💬 流畅的聊天体验
- 🚀 快速响应
- 📱 响应式设计
- 🎭 模拟专业心理医生对话

## 使用

1. 启动后端和前端
2. 在浏览器中打开 http://localhost:5173
3. 开始与心理医生聊天
