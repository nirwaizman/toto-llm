#!/usr/bin/env python3
"""
שרת LLM מקומי לטוטו — מגיש לElevenLabs Agent עם הקשר מלא
פורט: 8002
"""
import json, os, asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import anthropic

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

# טען זיכרון מלא של טוטו
def load_memory():
    mem = []
    paths = [
        "/Users/weizman/.openclaw/workspace/MEMORY.md",
        "/Users/weizman/.openclaw/workspace/USER.md",
        "/Users/weizman/.openclaw/workspace/SOUL.md",
    ]
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                content = f.read()[:3000]  # 3K per file
            mem.append(f"=== {os.path.basename(p)} ===\n{content}")
        except:
            pass
    # יומן היום
    import datetime
    today = datetime.date.today().strftime("%Y-%m-%d")
    day_path = f"/Users/weizman/.openclaw/workspace/memory/{today}.md"
    try:
        with open(day_path, encoding="utf-8") as f:
            mem.append(f"=== TODAY {today} ===\n{f.read()[:2000]}")
    except:
        pass
    return "\n\n".join(mem)

MEMORY = load_memory()

SYSTEM = f"""אתה טוטו — עוזר AI אישי של ניר ויצמן. אתה חכם, חם וישיר.
ענה תמיד בעברית אלא אם פונים אליך באנגלית.
תשובות קצרות וממוקדות — 1-3 משפטים. אל תשתמש ב-markdown או אימוג'י.

להלן המידע המלא שלך על ניר:

{MEMORY}
"""

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass  # שקט

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        messages = [m for m in body.get("messages", []) if m["role"] != "system"]
        stream = body.get("stream", True)

        if stream:
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            with client.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=300,
                system=SYSTEM,
                messages=messages,
            ) as s:
                msg_id = f"chatcmpl_{id(s)}"
                for text in s.text_stream:
                    chunk = {"id": msg_id, "object": "chat.completion.chunk",
                             "created": 0, "model": CLAUDE_MODEL,
                             "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}]}
                    self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
        else:
            resp = client.messages.create(
                model=CLAUDE_MODEL, max_tokens=300,
                system=SYSTEM, messages=messages)
            text = resp.content[0].text
            out = {"id": "chatcmpl_1", "object": "chat.completion",
                   "created": 0, "model": CLAUDE_MODEL,
                   "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]}
            data = json.dumps(out).encode()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

if __name__ == "__main__":
    print("🐾 טוטו LLM Server פועל על פורט 8002")
    print(f"זיכרון טעון: {len(MEMORY)} תווים")
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8002))), Handler).serve_forever()
