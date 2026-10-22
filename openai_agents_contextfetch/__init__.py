"""ContextFetch web search and page reading tools for the OpenAI Agents SDK."""

from __future__ import annotations

from typing import Any, Literal

from agents import FunctionTool, RunContextWrapper, function_tool
from contextfetch import ContextFetch

__all__ = ("contextfetch_tools",)

Content = Literal["pruned_context", "text"]
"""`"pruned_context"`: only the parts of each page relevant to the query. `"text"`: the whole page as Markdown."""

_RESULT_KEY = {"pruned_context": "prunedContext", "text": "text"}


def _error_message(ctx: RunContextWrapper[Any], error: Exception) -> str:
    # The SDK's default hides the message; the API's error text tells the model what to fix.
    return f"ContextFetch error: {error}"


def contextfetch_tools(
    api_key: str | None = None,
    *,
    num_results: int = 5,
    content: Content = "pruned_context",
) -> list[FunctionTool]:
    """Returns the `contextfetch_search` and `contextfetch_read` function tools, sharing one client.

    Args:
        api_key: The ContextFetch API key. Defaults to the `CONTEXTFETCH_API_KEY` environment variable;
            without either, requests use the keyless tier.
        num_results: Results per search (1 to 25). Defaults to 5.
        content: Which page content search results carry. Defaults to `"pruned_context"`.

    API errors (bad URL, no credits, rate limit) are returned to the model as the tool output, with the API's message.
    """
    client = ContextFetch(api_key)
    key = _RESULT_KEY[content]

    # Sync functions: the SDK runs them in a worker thread (the contextfetch client is stdlib urllib).
    @function_tool(failure_error_function=_error_message)
    def contextfetch_search(
        query: str,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        start_published_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Searches the web and returns the top results with their page content as Markdown.

        Args:
            query: The web search query.
            include_domains: Only return results from these domains.
            exclude_domains: Never return results from these domains.
            start_published_date: Only return pages published on or after this date (YYYY-MM-DD).
        """
        response = client.search(
            query,
            num_results=num_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            start_published_date=start_published_date,
            text=content == "text",
            pruned_context=content == "pruned_context",
        )
        return [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "published_date": r.get("publishedDate"),
                "content": r.get(key) or "",
            }
            for r in response.get("results", [])
        ]

    @function_tool(failure_error_function=_error_message)
    def contextfetch_read(url: str, query: str | None = None) -> str:
        """Reads a web page and returns it as Markdown.

        Args:
            url: The URL of the page.
            query: If set, only the parts of the page relevant to this question are returned.
        """
        return client.read(url, query=query).markdown

    return [contextfetch_search, contextfetch_read]
