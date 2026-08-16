#!/usr/bin/env python3
import json, os
from http.server import HTTPServer, BaseHTTPRequestHandler
import anthropic

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
PORT = int(os.environ.get("PORT", 8080))

# זיכרון — מ-env var או ברירת מחדל
TOTO_MEMORY = os.environ.get("TOTO_MEMORY", """
ניר ויצמן, אבא לשישה ילדים: יולי (2008), ליאו (2009), ריי וריף תאומים (2017), אלי (2020), נאיה (2021).
גרוש ממיכל הקטנה (שחקנית). מלונות: אילת 34 חדרים, תאודור הרצל 10 ת"א.
עו"ד: מוני עזורה. חובות: קרן שקד 15-19M, מס הכנסה 3.7M, דיסקונט 1.5M.
כתובת: ארלוזורוב 17 דירה 123 ת"א. מייל: nirwaizman@gmail.com.
""")

SYSTEM = f"""אתה טוטו — עוזר AI אישי של ניר ויצמן.
אתה חכם, חם וישיר. ענה תמיד בעברית אלא אם פונים אליך באנגלית.
תשובות קצרות — 1-3 משפטים. ללא markdown או אימוג'י.

מידע על ניר:
{TOTO_MEMORY}
"""

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b'{}')
        messages = [m for m in body.get("messages", []) if m.get("role") != "system"]
        stream = body.get("stream", True)

        if stream:
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                with client.messages.stream(
                    model=CLAUDE_MODEL, max_tokens=300,
                    system=SYSTEM, messages=messages or [{"role":"user","content":"שלום"}]
                ) as s:
                    msg_id = f"chatcmpl_{id(s)}"
                    for text in s.text_stream:
                        chunk = {"id": msg_id, "object": "chat.completion.chunk",
                                 "created": 0, "model": CLAUDE_MODEL,
                                 "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}]}
                        self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                        self.wfile.flush()
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
            except Exception as e:
                self.wfile.write(f"data: {{\"error\": \"{e}\"}}\n\n".encode())
        else:
            try:
                resp = client.messages.create(
                    model=CLAUDE_MODEL, max_tokens=300,
                    system=SYSTEM, messages=messages or [{"role":"user","content":"שלום"}])
                text = resp.content[0].text
            except Exception as e:
                text = f"שגיאה: {e}"
            out = {"id": "chatcmpl_1", "object": "chat.completion",
                   "created": 0, "model": CLAUDE_MODEL,
                   "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]}
            data = json.dumps(out, ensure_ascii=False).encode()
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
    print(f"🐾 טוטו LLM Server פועל על פורט {PORT}")
    print(f"זיכרון: {len(TOTO_MEMORY)} תווים")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
