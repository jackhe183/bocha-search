import asyncio
from server import bocha_web_search, bocha_ai_search

async def main():
    print("=== Web Search ===")
    result = await bocha_web_search("Claude Code MCP 使用教程", count=3)
    print(result)

    print("\n=== AI Search ===")
    result = await bocha_ai_search("今天北京天气", count=3)
    print(result)

asyncio.run(main())