# openai-agents-contextfetch

[ContextFetch](https://contextfetch.dev) web search and page reading as function tools for the
[OpenAI Agents SDK](https://openai.github.io/openai-agents-python/).

```bash
pip install openai-agents-contextfetch
export CONTEXTFETCH_API_KEY="your-api-key"  # optional: without a key, requests use the keyless tier
```

```python
from agents import Agent, Runner

from openai_agents_contextfetch import contextfetch_tools

agent = Agent(name="Researcher", instructions="Answer with sources.", tools=contextfetch_tools())
result = Runner.run_sync(agent, "What changed in the latest Python release?")
print(result.final_output)
```

## Tools

- `contextfetch_search(query, include_domains?, exclude_domains?, start_published_date?)`: web search. Returns a list
  of `{title, url, published_date, content}`, where `content` is the page as Markdown: by default only the parts
  relevant to the query.
- `contextfetch_read(url, query?)`: one page as Markdown. With `query`, only the parts relevant to it.

API errors (bad URL, no credits, rate limit) go back to the model as the tool output, with the API's message.

## Options

```python
contextfetch_tools(
    api_key=None,              # defaults to CONTEXTFETCH_API_KEY
    num_results=5,             # results per search, 1 to 25
    content="pruned_context",  # or "text" for whole pages
)
```

## Without this package

The same tools are available over MCP: `npx -y @contextfetch/mcp` with the SDK's `MCPServerStdio`.

## Tests

```bash
uv run --group test pytest tests                                   # unit tests, no network
CONTEXTFETCH_API_KEY=... uv run --group test pytest tests/test_live.py  # live, 2 credits
```

Tested with openai-agents 0.20.0, 0.22.0 and 0.24.0. MIT licensed.
