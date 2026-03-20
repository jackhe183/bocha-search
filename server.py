import os
import json

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 加载 .env 文件，必须在读取环境变量之前调用
load_dotenv()

server = FastMCP("bocha-search-mcp")

# 模块加载时读取一次，MCP 每次启动都是独立进程，无需动态刷新
BOCHA_API_KEY = os.environ.get("BOCHA_API_KEY", "")

HEADERS = {
    "Authorization": f"Bearer {BOCHA_API_KEY}",
    "Content-Type": "application/json",
}


def _check_key() -> str | None:
    """API Key 缺失时返回错误字符串，否则返回 None。"""
    if not BOCHA_API_KEY:
        return "Error: BOCHA_API_KEY 未配置，请在 .env 文件中设置。"
    return None


@server.tool()
async def bocha_web_search(
    query: str,
    freshness: str = "noLimit",
    count: int = 10,
) -> str:
    """Search the web via Bocha and return titles, URLs, summaries, and dates.

    Args:
        query: Search query string.
        freshness: Time range filter. Options: noLimit, oneDay, oneWeek, oneMonth,
                   oneYear, YYYY-MM-DD, or YYYY-MM-DD..YYYY-MM-DD. Default: noLimit.
        count: Number of results to return (1–50). Default: 10.
    """
    if err := _check_key():
        return err

    payload = {"query": query, "summary": True, "freshness": freshness, "count": count}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.bochaai.com/v1/web-search",
                headers=HEADERS,
                json=payload,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()

        pages = data.get("data", {}).get("webPages", {}).get("value", [])
        if not pages:
            return "No results found."

        return "\n\n".join(
            f"Title: {r['name']}\n"
            f"URL: {r['url']}\n"
            f"Summary: {r.get('summary', '')}\n"
            f"Published: {r.get('datePublished', 'N/A')}\n"
            f"Site: {r.get('siteName', 'N/A')}"
            for r in pages
        )

    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"Request error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@server.tool()
async def bocha_ai_search(
    query: str,
    freshness: str = "noLimit",
    count: int = 10,
) -> str:
    """Semantic search via Bocha AI, returns web results plus structured domain cards
    (e.g. weather, news, healthcare, train tickets).

    Args:
        query: Search query string.
        freshness: Time range filter. Options: noLimit, oneDay, oneWeek, oneMonth, oneYear.
                   Default: noLimit.
        count: Number of results to return (1–50). Default: 10.
    """
    if err := _check_key():
        return err

    payload = {
        "query": query,
        "freshness": freshness,
        "count": count,
        "answer": False,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.bochaai.com/v1/ai-search",
                headers=HEADERS,
                json=payload,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()  # Fixed: was shadowing the httpx response variable

        results = []
        for msg in data.get("messages", []):
            ctype = msg.get("content_type", "")
            raw = msg.get("content", "{}")

            if ctype == "webpage":
                try:
                    content = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
                for r in content.get("value", []):
                    results.append(
                        f"Title: {r['name']}\n"
                        f"URL: {r['url']}\n"
                        f"Summary: {r.get('summary', '')}\n"
                        f"Published: {r.get('datePublished', 'N/A')}\n"
                        f"Site: {r.get('siteName', 'N/A')}"
                    )
            elif ctype != "image" and raw not in ("{}", ""):
                # 结构化卡片（天气、火车票等），直接透传给 agent
                results.append(raw)

        return "\n\n".join(results) if results else "No results found."

    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"Request error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    server.run()