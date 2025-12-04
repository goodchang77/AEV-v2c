# src/api/main.py
from src.api.endpoints import agent  # 新增

app.include_router(agent.router)  # 新增