# /// script
# requires-python = ">=3.10"
# dependencies = ["fastmcp>=4,<5"]
# ///
"""Smoke-test the clinic-rules server WITHOUT Claude.

    uv run --python 3.12 --script mcp_servers/clinic_rules/smoke.py

It starts server.py over stdio, lists tools/resources/prompts, calls a tool and reads a resource.
If this passes but Claude cannot use the server, the problem is registration, not your code.
"""
import asyncio
from pathlib import Path

from fastmcp import Client

SERVER = Path(__file__).resolve().parent / "server.py"
# Launch exactly the way Claude Code will: through uv, so the server's own dependencies are installed.
CONFIG = {
    "mcpServers": {
        "clinic-rules": {"command": "uv", "args": ["run", "--python", "3.12", "--script", str(SERVER)]}
    }
}


async def main() -> None:
    async with Client(CONFIG) as c:
        print("TOOLS:", [t.name for t in await c.list_tools()])
        print("RESOURCES:", [str(r.uri) for r in await c.list_resources()])
        print("TEMPLATES:", [t.uri_template for t in await c.list_resource_templates()])
        print("PROMPTS:", [p.name for p in await c.list_prompts()])
        res = await c.call_tool("lookup_appointment_rules", {"topic": "cancel"})
        print("CALL lookup_appointment_rules('cancel'):\n" + res.content[0].text)
        rd = await c.read_resource("clinic://policies/rescheduling")
        print("READ clinic://policies/rescheduling:\n" + rd[0].text)
        try:
            await c.call_tool("list_upcoming_appointments", {"patient_id": 1})
        except Exception as e:  # not configured -> a clear tool error, not a crash
            print("DB TOOL (unconfigured) ->", type(e).__name__ + ":", str(e)[:120])


asyncio.run(main())
