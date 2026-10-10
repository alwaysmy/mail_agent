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
            print("== 工具列表 ==")
            for t in tools.tools:
                print(f"- {t.name}")

            print("\n== list (最近 2 封) ==")
            r = await session.call_tool("list", {"n": 2})
            print(r.content[0].text[:400])

            print("\n== read (第一封 UID) ==")
            first = r.content[0].text.split("UID:")[1].split("\n")[0].strip()
            r = await session.call_tool("read", {"uid": first, "max_chars": 300})
            print(r.content[0].text[:400])


if __name__ == "__main__":
    asyncio.run(main())
