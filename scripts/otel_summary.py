"""Per-session cost, tokens and tool-call summary from otel.jsonl (written by scripts/otel_receiver.py).

    python scripts/otel_summary.py [otel.jsonl]

Only log events are used: metrics are cumulative counters and would double-count.
Cross-check against `claude -p --output-format json` (total_cost_usd, usage): the numbers match.
"""
import collections
import json
import sys


def value(v: dict):
    for key in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if key in v:
            return float(v[key]) if key in ("intValue", "doubleValue") else v[key]
    return None


sessions: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
tools: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)

path = sys.argv[1] if len(sys.argv) > 1 else "otel.jsonl"
try:
    lines = open(path, encoding="utf-8").read().splitlines()
except FileNotFoundError:
    sys.exit(f"{path} not found. Run scripts/otel_receiver.py and use claude with telemetry enabled first.")

for line in lines:
    url, _, body = line.partition("\t")
    if not url.endswith("/v1/logs"):
        continue
    for resource in json.loads(body).get("resourceLogs", []):
        for scope in resource.get("scopeLogs", []):
            for record in scope.get("logRecords", []):
                a = {x["key"]: value(x["value"]) for x in record.get("attributes", [])}
                event, sid = a.get("event.name", ""), a.get("session.id", "?")
                s = sessions[sid]
                if event == "api_request":
                    s["api_calls"] += 1
                    s["cost_usd"] += a.get("cost_usd", 0) or 0
                    for k in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens"):
                        s[k] += a.get(k, 0) or 0
                elif event == "tool_result":
                    s["tool_calls"] += 1
                    tools[sid][a.get("tool_name", "?") + (" (failed)" if a.get("success") == "false" else "")] += 1

if not sessions:
    sys.exit("no log events found yet (wait one export interval, then run again)")
total = 0.0
for sid, s in sessions.items():
    total += s["cost_usd"]
    print(
        f"session {sid[:8]}: ${s['cost_usd']:.4f} | {s['api_calls']} api calls | in {int(s['input_tokens'])} "
        f"out {int(s['output_tokens'])} cache_read {int(s['cache_read_tokens'])} "
        f"cache_write {int(s['cache_creation_tokens'])} | {s['tool_calls']} tool calls {dict(tools[sid])}"
    )
print(f"\ntotal: ${total:.4f} across {len(sessions)} session(s)")
