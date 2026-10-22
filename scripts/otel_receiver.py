"""Tiny local OTLP/HTTP-JSON receiver for Claude Code telemetry.

Terminal 1:   python scripts/otel_receiver.py
Terminal 2:   set these, then run claude as usual
   PowerShell:  $env:CLAUDE_CODE_ENABLE_TELEMETRY="1"; $env:OTEL_METRICS_EXPORTER="otlp"; $env:OTEL_LOGS_EXPORTER="otlp"
                $env:OTEL_EXPORTER_OTLP_PROTOCOL="http/json"; $env:OTEL_EXPORTER_OTLP_ENDPOINT="http://127.0.0.1:4318"
                $env:OTEL_METRIC_EXPORT_INTERVAL="2000"; $env:OTEL_LOGS_EXPORT_INTERVAL="1000"
   bash:        export CLAUDE_CODE_ENABLE_TELEMETRY=1 OTEL_METRICS_EXPORTER=otlp OTEL_LOGS_EXPORTER=otlp \
                       OTEL_EXPORTER_OTLP_PROTOCOL=http/json OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 \
                       OTEL_METRIC_EXPORT_INTERVAL=2000 OTEL_LOGS_EXPORT_INTERVAL=1000
Then summarize:  python scripts/otel_summary.py

Every POST body is appended to otel.jsonl as `<path><TAB><json>`. Listens on 127.0.0.1 only.
Privacy: prompts are redacted by default, but user.email and organization.id appear on every record.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer


class Server(HTTPServer):
    # Windows lets two processes bind the same port when address reuse is on; telemetry would then go to the
    # wrong (old) receiver silently. Refuse to start instead.
    allow_reuse_address = False


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        with open("otel.jsonl", "ab") as f:
            f.write(self.path.encode() + b"\t" + body.replace(b"\n", b" ") + b"\n")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("listening on http://127.0.0.1:4318, appending to otel.jsonl (Ctrl+C to stop)")
    try:
        Server(("127.0.0.1", 4318), Handler).serve_forever()
    except OSError as e:
        raise SystemExit(f"Port 4318 is already in use (an old receiver still running?): {e}")
