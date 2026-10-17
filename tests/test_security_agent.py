"""
AI Agent 端點安全性測試：全部以假 Agent 取代，不呼叫任何 LLM / 網路 / DB。
"""

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from src.ai_agent import agent as agent_core
from src.ai_agent.agent import FinancialAnalystAgent, MAX_AGENT_TOOL_STEPS, TaskType
from src.api.endpoints import agent as agent_api
from src.api.endpoints.auth import get_current_user
from src.main import app

SECRET_DETAIL = "internal-detail-/srv/secret/path-db-password-hint"


class FakeAgent:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls = 0
        self.mcp_server = SimpleNamespace(list_tools=lambda: [{"name": "t"}])

    async def analyze(self, user_query, company_id=None, context=None):
        self.calls += 1
        if self.fail:
            raise RuntimeError(SECRET_DETAIL)
        return {
            "task_id": agent_core.new_task_id(),
            "task_type": "q_and_a",
            "user_query": user_query,
            "company_id": company_id,
            "plan": {},
            "tool_results": {},
            "final_answer": "ok",
            "metadata": {"tools_executed": []},
        }


def _user_from_header(request: Request):
    uid = request.headers.get("X-Test-User")
    if not uid:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return SimpleNamespace(user_id=uid, is_active=True, role="user")


@pytest.fixture
def fake_agent():
    return FakeAgent()


@pytest.fixture
def client(fake_agent):
    agent_api._reset_guards_for_tests()
    app.dependency_overrides[agent_api.get_agent] = lambda: fake_agent
    app.dependency_overrides[get_current_user] = _user_from_header
    yield TestClient(app)
    app.dependency_overrides.pop(agent_api.get_agent, None)
    app.dependency_overrides.pop(get_current_user, None)
    agent_api._reset_guards_for_tests()


def _analyze(client, user="alice"):
    return client.post(
        "/api/v1/agent/analyze",
        json={"user_query": "分析 2330 的財務狀況"},
        headers={"X-Test-User": user},
    )


def test_anonymous_requests_are_rejected_by_real_auth():
    """不覆寫 get_current_user：未帶 token 必須 401，且不得建立/呼叫 agent"""
    called = MagicMock()

    def _agent_should_not_be_built():
        called()
        return FakeAgent()

    app.dependency_overrides[agent_api.get_agent] = _agent_should_not_be_built
    try:
        c = TestClient(app)
        assert c.post("/api/v1/agent/analyze", json={"user_query": "x"}).status_code == 401
        assert c.get("/api/v1/agent/tasks/abc").status_code == 401
        assert c.get("/api/v1/agent/tools").status_code == 401
        assert not called.called
    finally:
        app.dependency_overrides.pop(agent_api.get_agent, None)


def test_owner_can_read_task_but_other_user_gets_404(client):
    r = _analyze(client, "alice")
    assert r.status_code == 200
    task_id = r.json()["meta"]["task_id"]

    own = client.get(f"/api/v1/agent/tasks/{task_id}", headers={"X-Test-User": "alice"})
    assert own.status_code == 200
    assert own.json()["data"]["result"]["final_answer"] == "ok"

    other = client.get(f"/api/v1/agent/tasks/{task_id}", headers={"X-Test-User": "mallory"})
    assert other.status_code == 404
    assert "ok" not in other.text


def test_rate_limit_returns_429(client, fake_agent):
    for _ in range(agent_api.AGENT_RATE_LIMIT_PER_MINUTE):
        assert _analyze(client, "alice").status_code == 200
    r = _analyze(client, "alice")
    assert r.status_code == 429
    assert fake_agent.calls == agent_api.AGENT_RATE_LIMIT_PER_MINUTE
    # 其他使用者不受影響
    assert _analyze(client, "bob").status_code == 200


def test_concurrency_cap_returns_503(client, monkeypatch):
    sem = asyncio.Semaphore(1)
    monkeypatch.setattr(agent_api, "_agent_semaphore", sem)
    sem._value = 0  # 模擬已滿載
    r = _analyze(client, "alice")
    assert r.status_code == 503


def test_error_body_is_generic_with_error_id(client, fake_agent):
    fake_agent.fail = True
    r = _analyze(client, "alice")
    assert r.status_code == 500
    assert SECRET_DETAIL not in r.text
    assert "RuntimeError" not in r.text
    detail = r.json()["detail"]
    assert detail["error_id"]
    assert detail["message"]


def test_task_ids_unique_under_rapid_calls(client):
    ids = {_analyze(client, f"user{i}").json()["meta"]["task_id"] for i in range(50)}
    assert len(ids) == 50
    for tid in ids:
        assert len(tid) == 32 and int(tid, 16) >= 0


def test_new_task_id_is_unique_and_unpredictable():
    ids = [agent_core.new_task_id() for _ in range(5000)]
    assert len(set(ids)) == len(ids)
    assert all(uuid.UUID(hex=i).version == 4 for i in ids[:20])


def test_task_store_is_bounded_and_expires(monkeypatch):
    store = agent_api._TaskStore(max_entries=3, ttl_seconds=10)
    clock = [1000.0]
    monkeypatch.setattr(agent_api.time, "monotonic", lambda: clock[0])
    for i in range(5):
        store.put(f"t{i}", "alice", {"i": i})
    assert len(store) == 3
    assert store.get("t0", "alice") is None          # 最舊的被淘汰
    assert store.get("t4", "alice") == {"i": 4}
    assert store.get("t4", "bob") is None             # 非擁有者
    clock[0] += 11
    assert store.get("t4", "alice") is None           # 過期
    assert len(store) == 0


def _bare_agent():
    """建立不連線 Anthropic 的 agent 實例（略過 __init__）"""
    a = object.__new__(FinancialAnalystAgent)
    a.mcp_server = MagicMock()
    a.client = MagicMock()
    a.model = "test"
    a.system_prompt = ""
    return a


def test_agent_analyze_caps_tool_steps_and_does_not_log_query(monkeypatch):
    a = _bare_agent()
    many_tools = [f"tool_{i}" for i in range(50)]
    a._classify_task = AsyncMock(return_value=TaskType.Q_AND_A)
    a._plan_task = AsyncMock(return_value={"reasoning": "r", "tools": many_tools, "tool_inputs": {}})
    a._execute_tools = AsyncMock(return_value={})
    a._synthesize_answer = AsyncMock(return_value="answer")

    logged = []
    monkeypatch.setattr(
        agent_core, "logger",
        SimpleNamespace(
            info=lambda *args, **kw: logged.append((args, kw)),
            warning=lambda *args, **kw: logged.append((args, kw)),
            error=lambda *args, **kw: logged.append((args, kw)),
        ),
    )
    query = "非常機密的投資問題-UNIQUE-MARKER"
    result = asyncio.run(a.analyze(user_query=query))

    executed_tools = a._execute_tools.call_args.args[0]
    assert len(executed_tools) == MAX_AGENT_TOOL_STEPS
    assert result["metadata"]["total_steps"] == MAX_AGENT_TOOL_STEPS
    assert "UNIQUE-MARKER" not in repr(logged)
    started = [kw for args, kw in logged if args and args[0] == "Analysis started"][0]
    assert started["query_length"] == len(query)
    assert len(started["query_sha256"]) == 12


def test_agent_analyze_rapid_calls_produce_unique_ids():
    a = _bare_agent()
    a._classify_task = AsyncMock(return_value=TaskType.Q_AND_A)
    a._plan_task = AsyncMock(return_value={"reasoning": "", "tools": [], "tool_inputs": {}})
    a._execute_tools = AsyncMock(return_value={})
    a._synthesize_answer = AsyncMock(return_value="answer")

    async def run_many():
        return await asyncio.gather(*[a.analyze(user_query="q") for _ in range(100)])

    results = asyncio.run(run_many())
    assert len({r["task_id"] for r in results}) == 100
