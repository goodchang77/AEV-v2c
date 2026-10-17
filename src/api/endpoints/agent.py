"""
AI Agent API端點

安全性：
- 所有端點需登入（get_current_user）；LLM 費用由伺服器支付，不可匿名使用
- 任務結果綁定擁有者，其他使用者查詢一律回 404
- 結果儲存有上限與 TTL，避免記憶體無限成長
- 每位使用者速率限制（429）與全域併發上限（503）
- 錯誤回應只含通用訊息與 error_id，不回傳例外內容
"""
import asyncio
import logging
import os
import threading
import time
import uuid
from collections import OrderedDict, deque
from typing import Any, Deque, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.endpoints.auth import get_current_user
from src.core.database import get_sync_session as get_db
from src.mcp_server.server import MCPServer
from src.ai_agent.agent import FinancialAnalystAgent
from src.models import User
from src.schemas.requests import AgentAnalysisRequest
from src.schemas.responses import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Agent"])

# ---------------------------------------------------------------------------
# 可調整的防護參數
# ---------------------------------------------------------------------------
AGENT_RATE_LIMIT_PER_MINUTE = 5      # 每位使用者每分鐘最多分析請求數
AGENT_RATE_WINDOW_SECONDS = 60
AGENT_MAX_CONCURRENT = 4             # 全域同時進行中的分析數
TASK_STORE_MAX_ENTRIES = 500         # 記憶體結果儲存上限
TASK_STORE_TTL_SECONDS = 3600        # 結果保留時間

# 初始化(單例模式)
_mcp_server = None
_agent = None


class _TaskStore:
    """有上限與 TTL 的記憶體任務結果儲存（task_id -> (owner, created_at, task)）"""

    def __init__(self, max_entries: int, ttl_seconds: int):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._data: "OrderedDict[str, Tuple[str, float, Dict[str, Any]]]" = OrderedDict()
        self._lock = threading.Lock()

    def _evict(self, now: float) -> None:
        expired = [k for k, (_, ts, _) in self._data.items() if now - ts > self.ttl_seconds]
        for k in expired:
            del self._data[k]
        while len(self._data) > self.max_entries:
            self._data.popitem(last=False)  # 移除最舊

    def put(self, task_id: str, owner_id: str, task: Dict[str, Any]) -> None:
        with self._lock:
            now = time.monotonic()
            self._data[task_id] = (owner_id, now, task)
            self._data.move_to_end(task_id)
            self._evict(now)

    def get(self, task_id: str, owner_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._evict(time.monotonic())
            entry = self._data.get(task_id)
            if entry is None or entry[0] != owner_id:
                return None
            return entry[2]

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, task_id: str) -> bool:
        return task_id in self._data


_task_store = _TaskStore(TASK_STORE_MAX_ENTRIES, TASK_STORE_TTL_SECONDS)

# 每位使用者的請求時間戳（滑動視窗）
_rate_buckets: Dict[str, Deque[float]] = {}
_rate_lock = threading.Lock()

# 全域併發上限：不排隊等待，滿載時直接回 503
_agent_semaphore = asyncio.Semaphore(AGENT_MAX_CONCURRENT)


def _owner_id(user: Any) -> str:
    return str(getattr(user, "user_id", ""))


def _check_rate_limit(owner_id: str) -> None:
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets.setdefault(owner_id, deque())
        while bucket and now - bucket[0] >= AGENT_RATE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= AGENT_RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="請求過於頻繁，請稍後再試",
                headers={"Retry-After": str(AGENT_RATE_WINDOW_SECONDS)},
            )
        bucket.append(now)
        # 清理閒置使用者，避免字典無限成長
        if len(_rate_buckets) > TASK_STORE_MAX_ENTRIES * 4:
            for key in [k for k, b in _rate_buckets.items() if not b]:
                del _rate_buckets[key]


def _reset_guards_for_tests() -> None:
    """測試用：清除速率限制與結果儲存"""
    with _rate_lock:
        _rate_buckets.clear()
    _task_store.clear()


def get_agent(db: Session = Depends(get_db)) -> FinancialAnalystAgent:
    """獲取AI Agent實例"""
    global _mcp_server, _agent
    
    if _mcp_server is None:
        _mcp_server = MCPServer(
            db_session=db,
            cache_enabled=os.getenv("MCP_CACHE_ENABLED", "true") == "true",
            max_concurrent_tools=int(os.getenv("MCP_MAX_CONCURRENT_TOOLS", "5"))
        )
    
    if _agent is None:
        _agent = FinancialAnalystAgent(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            mcp_server=_mcp_server,
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        )
    
    return _agent


@router.post("/analyze", response_model=StandardResponse)
async def analyze_company(
    request: AgentAnalysisRequest,
    current_user: User = Depends(get_current_user),
    agent: FinancialAnalystAgent = Depends(get_agent)
):
    """
    執行AI Agent分析（需登入）
    
    - **user_query**: 使用者問題
    - **company_id**: 公司代號(可選)
    - **context**: 額外上下文(可選)
    """
    owner_id = _owner_id(current_user)
    _check_rate_limit(owner_id)

    if _agent_semaphore.locked():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 分析服務忙碌中，請稍後再試",
        )

    async with _agent_semaphore:
        try:
            result = await agent.analyze(
                user_query=request.user_query,
                company_id=request.company_id,
                context=request.context
            )
        except Exception:
            error_id = uuid.uuid4().hex[:12]
            logger.exception("AI agent analysis failed (error_id=%s)", error_id)
            raise HTTPException(
                status_code=500,
                detail={"message": "AI 分析失敗，請稍後再試", "error_id": error_id},
            )

    # 存入任務儲存（綁定擁有者），供 /tasks/{task_id} 查詢
    task_id = str(result.get("task_id") or uuid.uuid4().hex)
    _task_store.put(task_id, owner_id, {
        "status": "completed",
        "result": result,
    })

    return StandardResponse(
        success=True,
        data=result,
        meta={
            "task_id": task_id,
            "task_type": result.get("task_type"),
            "tools_executed": len(result.get("metadata", {}).get("tools_executed", []))
        }
    )


@router.get("/tasks/{task_id}", response_model=StandardResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """查詢任務狀態與結果（僅限任務擁有者）"""
    task = _task_store.get(task_id, _owner_id(current_user))
    if task is None:
        raise HTTPException(status_code=404, detail="找不到任務")

    return StandardResponse(
        success=True,
        data={
            "task_id": task_id,
            "status": task["status"],
            "result": task["result"],
        }
    )


@router.get("/tools", response_model=StandardResponse)
async def list_available_tools(
    current_user: User = Depends(get_current_user),
    agent: FinancialAnalystAgent = Depends(get_agent)
):
    """列出所有可用工具（需登入）"""
    tools = agent.mcp_server.list_tools()
    
    return StandardResponse(
        success=True,
        data={"tools": tools},
        meta={"count": len(tools)}
    )
