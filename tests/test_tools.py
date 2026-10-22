"""Unit tests: the SDK's HTTP call is patched, so nothing touches the network."""

from __future__ import annotations

import json
from typing import Any

import pytest
from agents import FunctionTool
from agents.tool_context import ToolContext
from contextfetch import ContextFetch, ContextFetchError

from openai_agents_contextfetch import contextfetch_tools

RESULTS = [
    {"url": "https://example.com/a", "title": "A", "publishedDate": "2026-01-02", "text": "# A", "prunedContext": "chunk A"},
    {"url": "https://example.com/b", "title": None, "text": "# B", "prunedContext": "chunk B"},
]


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    monkeypatch.delenv("CONTEXTFETCH_API_KEY", raising=False)

    def request(self: ContextFetch, method: str, path: str, body: Any = None, **_: Any) -> tuple[bytes, dict]:
        calls.append({"method": method, "path": path, "body": body, "api_key": self.api_key})
        if path.startswith("/r/https://missing"):
            raise ContextFetchError("not found", status=404)
        if path.startswith("/r/"):
            return b"# Page", {}
        return json.dumps({"results": RESULTS[: body["numResults"]]}).encode(), {}

    monkeypatch.setattr(ContextFetch, "_request", request)
    return calls


def _tools(**kwargs: Any) -> dict[str, FunctionTool]:
    return {t.name: t for t in contextfetch_tools(**kwargs)}


async def _invoke(tool: FunctionTool, args: dict[str, Any]) -> Any:
    raw = json.dumps(args)
    return await tool.on_invoke_tool(ToolContext(None, tool_name=tool.name, tool_call_id="1", tool_arguments=raw), raw)


def test_schemas() -> None:
    tools = _tools(api_key="k")
    assert set(tools) == {"contextfetch_search", "contextfetch_read"}
    search = tools["contextfetch_search"].params_json_schema
    assert "query" in search["required"]
    assert "YYYY-MM-DD" in search["properties"]["start_published_date"]["description"]
    assert "page" in tools["contextfetch_read"].description


async def test_search(calls: list[dict[str, Any]]) -> None:
    out = await _invoke(_tools(api_key="k", num_results=2)["contextfetch_search"], {"query": "q", "include_domains": ["example.com"]})
    assert out == [
        {"title": "A", "url": "https://example.com/a", "published_date": "2026-01-02", "content": "chunk A"},
        {"title": None, "url": "https://example.com/b", "published_date": None, "content": "chunk B"},
    ]
    assert calls == [
        {
            "method": "POST",
            "path": "/v1/search",
            "body": {"query": "q", "numResults": 2, "includeDomains": ["example.com"], "contents": {"pruned_context": True}},
            "api_key": "k",
        }
    ]


async def test_search_text_content_and_env_key(calls: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTEXTFETCH_API_KEY", "env-key")
    out = await _invoke(_tools(num_results=1, content="text")["contextfetch_search"], {"query": "q"})
    assert out[0]["content"] == "# A"
    assert calls[0]["body"]["contents"] == {"text": True}
    assert calls[0]["api_key"] == "env-key"


async def test_read(calls: list[dict[str, Any]]) -> None:
    out = await _invoke(_tools(api_key="k")["contextfetch_read"], {"url": "https://example.com/x", "query": "pricing"})
    assert out == "# Page"
    assert calls[0]["path"] == "/r/https://example.com/x?q=pricing"


async def test_error_goes_to_model(calls: list[dict[str, Any]]) -> None:
    out = await _invoke(_tools(api_key="k")["contextfetch_read"], {"url": "https://missing.example"})
    assert "not found" in out
