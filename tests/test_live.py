"""Live check against the real API (2 credits). Skipped unless CONTEXTFETCH_API_KEY is set."""

from __future__ import annotations

import json
import os

import pytest
from agents.tool_context import ToolContext

from openai_agents_contextfetch import contextfetch_tools

pytestmark = pytest.mark.skipif(not os.environ.get("CONTEXTFETCH_API_KEY"), reason="needs CONTEXTFETCH_API_KEY")


async def test_live() -> None:
    search, read = contextfetch_tools(num_results=2)

    async def invoke(tool, args):
        raw = json.dumps(args)
        return await tool.on_invoke_tool(ToolContext(None, tool_name=tool.name, tool_call_id="1", tool_arguments=raw), raw)

    results = await invoke(search, {"query": "python asyncio TaskGroup"})
    assert results and results[0]["url"].startswith("http") and results[0]["content"]
    page = await invoke(read, {"url": "https://docs.python.org/3/library/asyncio-task.html", "query": "TaskGroup"})
    assert "TaskGroup" in page
