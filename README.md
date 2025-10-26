# PsyDoctor-Client

## File Structure

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

## Quick Start

### Backend

1. Enter Backend：
```bash
cd backend
```

2. Create Virtual Environment (Optional)：
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

3. Install Requirements：
```bash
pip install -r requirements.txt
```

4. Adjust the Server's IP（Optional）：
`SERVER_URL` in `main.py`：
```python
SERVER_URL = "http://{IP_ADDRESS}:8000"  # Your Cloud Server IP Address.
```

5. Run Backend：
```bash
python main.py
# Or
uvicorn main:app --reload
```

The backend will be running at `http://localhost:8000` .

### Frontend

1. Enter Frontend：
```bash
cd frontend
```

2. Install Requirements：
```bash
npm install
```

3. Run Frontend：
```bash
npm run dev
```

The frontend will be running at `http://localhost:5173` .
