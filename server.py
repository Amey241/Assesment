"""Dependency-free local web UI. Run `python server.py` and open localhost:8080."""
from __future__ import annotations
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from aster_agent import SupportAgent

agent = SupportAgent()
PAGE = """<!doctype html><html lang=en><meta name=viewport content='width=device-width,initial-scale=1'>
<title>Aster & Row Support</title><style>
:root{--ink:#14251e;--muted:#627069;--cream:#fbfaf6;--paper:#fff;--line:#d9e2dc;--green:#155e4b;--mint:#e8f4ee;--blue:#eef5ff;--shadow:0 12px 36px #16251b12}*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font:16px/1.5 Inter,ui-sans-serif,system-ui,sans-serif}.shell{max-width:780px;margin:auto;padding:24px 20px}.top{display:flex;align-items:center;gap:13px;margin-bottom:18px}.mark{width:40px;height:40px;border-radius:13px;display:grid;place-items:center;background:var(--green);color:white;font:700 19px Georgia,serif;box-shadow:var(--shadow)}h1{margin:0;font:700 25px Georgia,serif;letter-spacing:-.4px}.status{margin-left:auto;border:1px solid #b9dfcc;background:var(--mint);color:#185b43;border-radius:20px;padding:5px 10px;font-size:12px;font-weight:700}.panel{height:min(700px,calc(100vh - 100px));min-height:470px;background:var(--paper);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);display:flex;flex-direction:column;overflow:hidden}.chat-head{padding:14px 20px;border-bottom:1px solid var(--line);font-weight:700}.chat-head span{float:right;font-size:12px;color:var(--muted);font-weight:500}.messages{padding:20px;display:grid;gap:16px;flex:1;overflow-y:auto;align-content:start}.welcome{background:var(--mint);padding:15px;border-radius:14px}.welcome strong,.bubble strong{display:block;font-size:13px;margin-bottom:3px}.bubble{max-width:88%;padding:13px 15px;border-radius:14px;background:#f5f7f5;border:1px solid #e2e8e3}.user{margin-left:auto;background:var(--blue);border-color:#d4e2f5}.meta{display:block;margin-top:9px;font-size:12px;color:var(--muted)}.handoff{display:inline-block;margin-top:9px;font-size:12px;font-weight:700;color:#a74916}.composer{padding:12px 14px 14px;border-top:1px solid var(--line);background:#fcfdfc}.suggestions{display:flex;gap:7px;overflow-x:auto;padding:0 0 10px}.chip{white-space:nowrap;background:#f6f8f6;border:1px solid var(--line);border-radius:18px;padding:6px 10px;color:#254338;font:12px inherit;cursor:pointer}.chip:hover{border-color:var(--green);background:var(--mint)}.inputrow{display:flex;align-items:flex-end;gap:9px;border:1px solid #c8d5cc;border-radius:14px;background:white;padding:8px 8px 8px 13px}.inputrow:focus-within{border-color:var(--green);box-shadow:0 0 0 3px #155e4b18}textarea{border:0;outline:0;resize:none;width:100%;font:inherit;min-height:28px;max-height:120px}.send{border:0;border-radius:10px;background:var(--green);color:white;padding:9px 13px;font-weight:700;cursor:pointer}.send:disabled{opacity:.55}.hint{font-size:12px;color:var(--muted);margin:8px 2px 0}.typing{color:var(--muted);font-size:13px;padding:6px}@media(max-width:720px){.shell{padding:14px}.panel{height:calc(100vh - 78px);min-height:440px}.status{display:none}.chat-head span{display:none}}</style>
<body><div class=shell><header class=top><div class=mark>A</div><h1>Aster &amp; Row Support</h1><div class=status>● Online</div></header><main class=panel><div class=chat-head>Support conversation <span>Private &amp; session-only</span></div><div class=messages id=chat><div class=welcome><strong>Welcome to Aster &amp; Row</strong>How can I help today? I can check an order with its ID or explain our policies.</div></div><form class=composer><div class=suggestions aria-label='Suggested questions'><button class=chip type=button>Where is ORD-1007?</button><button class=chip type=button>How long to return a backpack?</button><button class=chip type=button>Do you ship to Canada?</button><button class=chip type=button>Is the Breeze Tumbler dishwasher safe?</button></div><div class=inputrow><textarea aria-label='Your question' required rows=1 placeholder='Ask about an order or policy…'></textarea><button class=send type=submit>Send</button></div><div class=hint>Press Enter to send · Shift + Enter for a new line</div></form></main></div>
<script>const sid=crypto.randomUUID(),chat=document.querySelector('#chat'),form=document.querySelector('form'),box=document.querySelector('textarea'),send=document.querySelector('.send');
function add(label,text,kind='',sources=[],handoff=false){const card=document.createElement('section'),name=document.createElement('strong'),body=document.createElement('div');card.className='bubble '+kind;name.textContent=label;body.textContent=text;card.append(name,body);if(sources.length){const meta=document.createElement('small');meta.className='meta';meta.textContent='Sources: '+sources.join(' · ');card.append(meta)}if(handoff){const note=document.createElement('small');note.className='handoff';note.textContent='Human assistance recommended';card.append(note)}chat.append(card);card.scrollIntoView({behavior:'smooth',block:'nearest'})}
async function ask(message){if(!message)return;add('You',message,'user');box.value='';box.style.height='auto';send.disabled=true;const typing=document.createElement('div');typing.className='typing';typing.textContent='Support is checking the available information…';chat.append(typing);try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,session_id:sid})});if(!r.ok)throw Error();const d=await r.json();typing.remove();add('Aster & Row Support',d.answer,'',d.sources,d.handoff)}catch{typing.remove();add('Aster & Row Support','I’m having trouble responding right now. Please try again.')}finally{send.disabled=false;box.focus()}}
form.onsubmit=e=>{e.preventDefault();ask(box.value.trim())};box.onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();form.requestSubmit()}};box.oninput=()=>{box.style.height='auto';box.style.height=Math.min(box.scrollHeight,120)+'px'};document.querySelectorAll('.chip').forEach(b=>b.onclick=()=>ask(b.textContent));</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/": self.send_error(404); return
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(PAGE.encode())
    def do_POST(self):
        if self.path != "/api/chat": self.send_error(404); return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 8000: raise ValueError("invalid request size")
            data = json.loads(self.rfile.read(size)); message = str(data["message"]).strip()
            if not message: raise ValueError("message is required")
            reply = agent.respond(message, str(data.get("session_id") or secrets.token_urlsafe(12)))
            payload = {"answer": reply.answer, "sources": reply.sources, "handoff": reply.handoff}
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(json.dumps(payload).encode())
        except (ValueError, KeyError, json.JSONDecodeError): self.send_error(400, "Send JSON with a non-empty message.")
    def log_message(self, fmt, *args): pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"Aster & Row Support is running at http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
