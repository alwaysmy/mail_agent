"""本地验证 mcp_mail.py：起 stdio server，列工具并调用 list/read。"""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).parent


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(HERE / "mcp_mail.py")])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("== 工具列表（含 description）==")
            for t in tools.tools:
                print(f"- {t.name}")
                print(f"  {t.description}")

            print("\n== list (最近 1 封) ==")
            r = await session.call_tool("list", {"n": 1})
            print(r.content[0].text[:300])


if __name__ == "__main__":
    asyncio.run(main())
