import os, pickle, hashlib, tempfile, logging, json, asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()


from ingestion.pdf_ingestor import IngestionAgent
from embedding.embedder import ChunkingEmbedder
from utils.arxiv_downloader import download_arxiv_paper
from graph.agent_graph import paper_graph
from knowledge.schema import PaperKnowledge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib as _hl

_conn = None

def _get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(os.getenv("NEON_DATABASE_URL"))
    return _conn

def init_db():
    c = _get_conn()
    with c.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS user_papers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                title TEXT NOT NULL,
                knowledge_json TEXT NOT NULL,
                summary TEXT,
                flaws TEXT,
                comparison TEXT,
                ppt_filename TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            );
        """)
        c.commit()

def _hash(pw): return _hl.sha256(pw.encode()).hexdigest()

def db_signup(username, password):
    try:
        c = _get_conn()
        with c.cursor() as cur:
            cur.execute("INSERT INTO users (username, password_hash) VALUES (%s,%s)",
                        (username, _hash(password)))
            c.commit()
            return True
    except:
        _get_conn().rollback()
        return False

def db_login(username, password):
    c = _get_conn()
    with c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, username FROM users WHERE username=%s AND password_hash=%s",
                    (username, _hash(password)))
        row = cur.fetchone()
        return dict(row) if row else None

def db_save_paper(user_id, paper, summary, flaws, comparison, ppt_filename):
    """Always INSERT a new row and return its id."""
    expires = datetime.now() + timedelta(days=10)
    c = _get_conn()
    with c.cursor() as cur:
        cur.execute("""
            INSERT INTO user_papers
              (user_id, title, knowledge_json, summary, flaws, comparison, ppt_filename, expires_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (user_id, paper.title,
              json.dumps(paper.model_dump()),
              summary, flaws, comparison, ppt_filename, expires))
        pid = cur.fetchone()[0]
        c.commit()
        return pid

def db_get_papers(user_id):
    c = _get_conn()
    with c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, title, summary, flaws, comparison, ppt_filename, timestamp, knowledge_json
            FROM user_papers
            WHERE user_id=%s AND expires_at > NOW()
            ORDER BY timestamp DESC
        """, (user_id,))
        return [dict(r) for r in cur.fetchall()]

def db_get_paper(paper_id, user_id):
    c = _get_conn()
    with c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, title, knowledge_json, summary, flaws, comparison, ppt_filename, timestamp
            FROM user_papers
            WHERE id=%s AND user_id=%s AND expires_at > NOW()
        """, (paper_id, user_id))
        row = cur.fetchone()
        return dict(row) if row else None

# ═══════════════════════════════════════════════════════
#  REDIS CACHE  (optional — mirrors Streamlit cache fns)
# ═══════════════════════════════════════════════════════
try:
    import redis as _redis
    _rc = _redis.Redis(host=os.getenv("REDIS_HOST","localhost"),
                       port=int(os.getenv("REDIS_PORT",6379)),
                       db=0, decode_responses=True)
    _rc.ping()
    redis_client = _rc
    logger.info("✅ Redis connected")
except Exception:
    redis_client = None
    logger.warning("⚠️  Redis unavailable — caching disabled")

def _ck(title, query):
    return hashlib.md5(f"paper:{title}:query:{query}".encode()).hexdigest()

def get_cached(title, query):
    if not redis_client: return None
    try:
        raw = redis_client.get(_ck(title, query))
        return json.loads(raw) if raw else None
    except: return None

def set_cached(title, query, result):
    if not redis_client: return
    try:
        redis_client.setex(_ck(title, query), 3600, json.dumps(_safe(result)))
    except Exception as e:
        logger.warning(f"cache write: {e}")

# ═══════════════════════════════════════════════════════
#  LOCAL CHUNK STORE  (replaces st.session_state["chunks"])
# ═══════════════════════════════════════════════════════
CHUNK_DIR = Path(tempfile.gettempdir()) / "paperintel_chunks"
CHUNK_DIR.mkdir(exist_ok=True)

def _cpath(pid): return CHUNK_DIR / f"{pid}.pkl"

def save_chunks(pid, chunks):
    try:
        _cpath(pid).write_bytes(pickle.dumps(chunks))
        logger.info(f"✅ saved {len(chunks)} chunks pid={pid}")
    except Exception as e:
        logger.warning(f"chunk save: {e}")

def load_chunks(pid):
    try:
        p = _cpath(pid)
        if p.exists():
            ch = pickle.loads(p.read_bytes())
            logger.info(f"✅ loaded {len(ch)} chunks pid={pid}")
            return ch
    except Exception as e:
        logger.warning(f"chunk load: {e}")
    return []

# ═══════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════
def _safe(obj):
    """Make obj JSON-serialisable (same logic as Streamlit make_serializable)."""
    if isinstance(obj, (str,int,float,bool,type(None))): return obj
    if isinstance(obj, list):  return [_safe(i) for i in obj]
    if isinstance(obj, dict):  return {k: _safe(v) for k,v in obj.items()}
    if isinstance(obj, PaperKnowledge): return None
    return str(obj)

def deser(kj):
    """Deserialise knowledge_json → PaperKnowledge."""
    data = json.loads(kj)
    if isinstance(data, dict) and data.get("__type__") == "PaperKnowledge":
        data = {k:v for k,v in data.items() if k != "__type__"}
    return PaperKnowledge(**data)

def build_state(paper, query, chunks):
    """
    Mirrors paper_graph.invoke({...}) from the Streamlit app.
    Adds router_decision (was missing → KeyError in every agent).
    """
    from agents.router_agent import route_user_instruction
    try:    rd = route_user_instruction(query)
    except Exception as e:
        logger.warning(f"router fallback: {e}")
        rd = {"mode":"researcher","tasks":["summarize","insights"],"custom_instructions":""}
    return {
        "paper":paper, "user_instruction":query,
        "chunks": chunks or [],
        "router_decision": rd,
        "summary":"","insights":"","flaws":"","comparison":"",
        "qa_answer":"","ppt_outline":"","application":"",
        "mode": rd.get("mode","researcher"),
        "final_output":"","ppt_file":""
    }

# ═══════════════════════════════════════════════════════
#  SSE PIPELINE  (mirrors Streamlit spinner + paper_graph.invoke)
# ═══════════════════════════════════════════════════════
async def sse_pipeline(paper, query, chunks, user_id):
    steps = [
    "🧭 Summoning the AI Avengers because one brain cell ain’t enough…",
    "📚 Speed-reading papers like there’s an exam in 10 minutes…",
    "🧠 Translating academic gibberish into actual English…",
    "🔎 Politely judging the paper (but internally roasting it)…",
    "🌍 Comparing it with other papers like it's a reality show…",
    "✨ Packaging everything so it looks like I had my life together…",
]
    for msg in steps:
        yield f"data: {json.dumps({'type':'message','content':msg})}\n\n"
        await asyncio.sleep(0.7)

    try:
        def run():
            s = build_state(paper, query, chunks)
            return paper_graph.invoke(s)

        result = await asyncio.get_event_loop().run_in_executor(None, run)
        result = _safe(result)

        # cache (mirrors cache_response in Streamlit)
        set_cached(paper.title, query, result)

        # save (mirrors save_paper at end of Streamlit chat block)
        db_save_paper(user_id, paper,
                      result.get("summary",""),
                      result.get("flaws",""),
                      result.get("comparison",""),
                      result.get("ppt_file",""))

        result["from_cache"] = False
        yield f"data: {json.dumps({'type':'result','content':result})}\n\n"

    except Exception as e:
        import traceback; logger.error(traceback.format_exc())
        yield f"data: {json.dumps({'type':'error','content':str(e)})}\n\n"

# ═══════════════════════════════════════════════════════
#  HTML PAGES  (all inline — no templates/ folder needed)
# ═══════════════════════════════════════════════════════
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;width:100%;overflow:hidden}
body{font-family:'Inter',sans-serif;
     background:linear-gradient(135deg,
     color:
.glass{background:rgba(15,23,42,.6);backdrop-filter:blur(12px);
       border:1px solid rgba(0,212,255,.15);border-radius:12px}
.glass-s{background:rgba(10,14,39,.85);backdrop-filter:blur(16px);
          border:1px solid rgba(0,212,255,.2)}
.gt{background:linear-gradient(135deg,
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.gb{background:linear-gradient(135deg,
.btn{cursor:pointer;border:none;border-radius:8px;
     font-family:'Inter',sans-serif;font-weight:600;transition:all .2s}
.bp{background:linear-gradient(135deg,
.bp:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(0,212,255,.4)}
.bs{background:rgba(0,212,255,.08);border:1px solid rgba(0,212,255,.3);
    color:
.bs:hover{background:rgba(0,212,255,.15)}
input,textarea{width:100%;background:rgba(30,35,70,.4);
  border:1px solid rgba(0,212,255,.2);color:
  padding:10px 14px;border-radius:8px;
  font-family:'Inter',sans-serif;font-size:.9rem;transition:all .2s}
input:focus,textarea:focus{outline:none;border-color:rgba(0,212,255,.55);
  box-shadow:0 0 12px rgba(0,212,255,.12)}
input::placeholder,textarea::placeholder{color:
textarea{resize:none}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:rgba(30,35,70,.2);border-radius:6px}
::-webkit-scrollbar-thumb{background:linear-gradient(
.bu{background:linear-gradient(135deg,
    border-radius:18px 18px 4px 18px;padding:12px 16px;
    max-width:75%;margin-left:auto;word-break:break-word;font-size:.9rem}
.ba{background:rgba(15,23,42,.8);border:1px solid rgba(0,212,255,.15);
    border-radius:18px 18px 18px 4px;padding:14px 16px;
    max-width:85%;word-break:break-word;font-size:.9rem;line-height:1.7}
.bsy{background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.2);
     border-radius:10px;padding:10px 14px;font-size:.85rem;color:
.ber{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2);
     border-radius:10px;padding:10px 14px;font-size:.85rem;color:
.sb{width:260px;flex-shrink:0;display:flex;flex-direction:column;
    height:100%;border-right:1px solid rgba(0,212,255,.1);
    background:rgba(10,14,39,.7);overflow-y:auto;padding:14px}
.si{padding:9px 12px;border-radius:8px;cursor:pointer;
    font-size:.8rem;color:
    border:1px solid transparent;margin-bottom:4px;
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.si:hover{background:rgba(0,212,255,.08);border-color:rgba(0,212,255,.2);color:
.modal{position:fixed;inset:0;background:rgba(0,0,0,.6);
       backdrop-filter:blur(4px);z-index:100;
       display:flex;align-items:center;justify-content:center}
.mbox{background:rgba(10,14,39,.96);border:1px solid rgba(0,212,255,.25);
      border-radius:16px;padding:28px;width:370px;max-width:92vw}
.pt{width:100%;background:rgba(255,255,255,.08);border-radius:99px;
    height:6px;overflow:hidden;margin-top:10px}
.pf{height:100%;background:linear-gradient(90deg,
    border-radius:99px;transition:width .4s ease}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes fu{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.spin{animation:spin 1.2s linear infinite;display:inline-block}
.fu{animation:fu .3s ease}
details summary{cursor:pointer;list-style:none}
details summary::-webkit-details-marker{display:none}
</style>
"""

def page(body, title="PaperIntel AI"):
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
{CSS}
</head><body style="display:flex;flex-direction:column;height:100vh">
{body}
</body></html>"""

# ── Login page ─────────────────────────────────────────
def login_page():
    return page("""
<div style="display:flex;align-items:center;justify-content:center;height:100vh;padding:20px">
<div style="width:100%;max-width:420px">
  <div style="text-align:center;margin-bottom:28px">
    <div class="gt" style="font-size:2.2rem;font-weight:800">🧠 PaperIntel AI</div>
    <p style="color:#64748b;margin-top:6px;font-size:.88rem">Advanced Research Paper Assistant · Powered by Groq</p>
  </div>
  <div class="glass" style="padding:28px">
    <div style="display:flex;border-bottom:1px solid rgba(0,212,255,.15);margin-bottom:22px">
      <button class="btn" id="tl" onclick="tab('login')"
        style="flex:1;padding:10px;background:none;color:#00d4ff;
               border-bottom:2px solid
        🔑 Login</button>
      <button class="btn" id="ts" onclick="tab('signup')"
        style="flex:1;padding:10px;background:none;color:#64748b;
               border-bottom:2px solid transparent;border-radius:0;font-size:.88rem">
        ✍️ Sign Up</button>
    </div>

    <div id="pl">
      <div style="margin-bottom:12px">
        <label style="font-size:.78rem;color:#94a3b8;display:block;margin-bottom:5px">Username</label>
        <input id="lu" placeholder="Enter username" onkeydown="if(event.key==='Enter')login()">
      </div>
      <div style="margin-bottom:16px">
        <label style="font-size:.78rem;color:#94a3b8;display:block;margin-bottom:5px">Password</label>
        <input id="lp" type="password" placeholder="Enter password" onkeydown="if(event.key==='Enter')login()">
      </div>
      <div id="le" style="display:none;font-size:.82rem;border-radius:8px;padding:9px;margin-bottom:12px"></div>
      <button class="btn bp" style="width:100%" onclick="login()">Login</button>
    </div>

    <div id="ps" style="display:none">
      <div style="margin-bottom:12px">
        <label style="font-size:.78rem;color:#94a3b8;display:block;margin-bottom:5px">Username</label>
        <input id="su" placeholder="Choose username">
      </div>
      <div style="margin-bottom:12px">
        <label style="font-size:.78rem;color:#94a3b8;display:block;margin-bottom:5px">Password</label>
        <input id="sp" type="password" placeholder="Min 6 characters">
      </div>
      <div style="margin-bottom:16px">
        <label style="font-size:.78rem;color:#94a3b8;display:block;margin-bottom:5px">Confirm Password</label>
        <input id="sc" type="password" placeholder="Repeat password">
      </div>
      <div id="se" style="display:none;font-size:.82rem;border-radius:8px;padding:9px;margin-bottom:12px"></div>
      <button class="btn bp" style="width:100%" onclick="signup()">Create Account</button>
    </div>
  </div>
  <p style="text-align:center;color:#334155;font-size:.72rem;margin-top:14px">🧠 Professional Research Paper Intelligence</p>
</div></div>
<script>
function tab(t){
  document.getElementById('pl').style.display=t==='login'?'':'none';
  document.getElementById('ps').style.display=t==='signup'?'':'none';
  document.getElementById('tl').style.cssText='flex:1;padding:10px;background:none;border-radius:0;font-size:.88rem;border-bottom:2px solid '+(t==='login'?'#00d4ff':'transparent')+';color:'+(t==='login'?'#00d4ff':'#64748b');
  document.getElementById('ts').style.cssText='flex:1;padding:10px;background:none;border-radius:0;font-size:.88rem;border-bottom:2px solid '+(t==='signup'?'#00d4ff':'transparent')+';color:'+(t==='signup'?'#00d4ff':'#64748b');
}
function err(id,msg,ok){
  const e=document.getElementById(id);
  e.style.background=ok?'rgba(34,197,94,.08)':'rgba(239,68,68,.08)';
  e.style.border='1px solid '+(ok?'rgba(34,197,94,.25)':'rgba(239,68,68,.25)');
  e.style.color=ok?'#86efac':'#fca5a5';
  e.textContent=msg;e.style.display='';
}
async function login(){
  const u=document.getElementById('lu').value.trim(),p=document.getElementById('lp').value;
  if(!u||!p){err('le','Please fill in all fields');return}
  const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});
  const d=await r.json();
  if(r.ok) window.location.href='/dashboard';
  else err('le','❌ '+(d.error||'Login failed'));
}
async function signup(){
  const u=document.getElementById('su').value.trim(),p=document.getElementById('sp').value,c=document.getElementById('sc').value;
  if(!u||!p||!c){err('se','Please fill in all fields');return}
  if(p.length<6){err('se','Password must be at least 6 characters');return}
  if(p!==c){err('se',"Passwords don't match");return}
  const r=await fetch('/api/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p,confirm_password:c})});
  const d=await r.json();
  if(r.ok){err('se','✅ Account created! Please login.',true);setTimeout(()=>tab('login'),1600)}
  else err('se','❌ '+(d.error||'Signup failed'));
}
</script>""", "PaperIntel AI — Login")

# ── Dashboard page ─────────────────────────────────────
def dashboard_page(username, papers):
    items = ""
    for p in papers[:10]:
        t = (p.get("title","Untitled"))[:44]
        items += f'<div class="si" onclick="window.location.href=\'/paper/{p["id"]}\'" title="{p.get("title","")}">📄 {t}</div>'
    if not items:
        items = "<p style='color:#334155;font-size:.8rem;padding:8px'>No papers yet</p>"

    return page(f"""
<!-- navbar -->
<div class="glass-s" style="padding:12px 22px;display:flex;align-items:center;
     justify-content:space-between;flex-shrink:0;border-bottom:1px solid rgba(0,212,255,.1)">
  <div style="display:flex;align-items:center;gap:10px">
    <div class="gb" style="width:34px;height:34px;border-radius:9px;display:flex;align-items:center;justify-content:center">🧠</div>
    <div class="gt" style="font-weight:800;font-size:1.05rem">PaperIntel AI</div>
  </div>
  <div style="display:flex;align-items:center;gap:10px">
    <div class="glass" style="padding:5px 12px;border-radius:8px;font-size:.83rem">👤 {username}</div>
    <button class="btn bs" onclick="fetch('/api/logout',{{method:'POST'}}).then(()=>location.href='/')">Logout</button>
  </div>
</div>

<!-- body -->
<div style="display:flex;flex:1;overflow:hidden">

  <!-- sidebar: history (mirrors Streamlit sidebar) -->
  <div class="sb">
    <div style="font-size:.73rem;font-weight:600;color:#64748b;text-transform:uppercase;
                letter-spacing:.05em;margin-bottom:10px">📜 10-Day History</div>
    {items}
  </div>

  <!-- main: upload (mirrors Streamlit upload section) -->
  <div style="flex:1;overflow-y:auto;padding:36px 44px">
    <h2 style="font-weight:800;font-size:1.6rem;margin-bottom:6px">Welcome back 👋</h2>
    <p style="color:#64748b;margin-bottom:28px">Upload a PDF or paste an arXiv link to analyse a paper</p>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;max-width:680px;margin-bottom:24px">
      <!-- PDF upload -->
      <div class="glass" style="padding:26px;text-align:center;cursor:pointer;border-radius:14px;
           border:2px dashed rgba(0,212,255,.2);transition:all .2s"
           onclick="document.getElementById('fi').click()"
           onmouseenter="this.style.borderColor='rgba(0,212,255,.5)'"
           onmouseleave="this.style.borderColor='rgba(0,212,255,.2)'">
        <div class="gb" style="width:48px;height:48px;border-radius:50%;display:flex;
             align-items:center;justify-content:center;font-size:1.3rem;margin:0 auto 10px">📄</div>
        <div style="font-weight:600;margin-bottom:4px">Upload PDF</div>
        <div style="color:#64748b;font-size:.8rem">Click to browse</div>
        <input type="file" id="fi" accept=".pdf" style="display:none" onchange="upload(event)">
      </div>

      <!-- arXiv -->
      <div class="glass" style="padding:26px;border-radius:14px">
        <div class="gb" style="width:48px;height:48px;border-radius:50%;display:flex;
             align-items:center;justify-content:center;font-size:1.3rem;margin-bottom:10px">🔗</div>
        <div style="font-weight:600;margin-bottom:8px">From arXiv</div>
        <input id="ax" placeholder="arxiv.org/abs/2403.xxxxx" style="margin-bottom:9px">
        <button class="btn bp" style="width:100%;padding:9px" onclick="arxiv()">Download & Process</button>
      </div>
    </div>

    <div id="st" style="display:none;max-width:680px;border-radius:10px;padding:13px 16px;font-size:.87rem"></div>
  </div>
</div>

<script>
function status(msg,type){{
  const s=document.getElementById('st');
  const c={{info:['rgba(0,212,255,.06)','rgba(0,212,255,.2)','#7dd3fc'],
            ok:  ['rgba(34,197,94,.06)', 'rgba(34,197,94,.2)', '#86efac'],
            err: ['rgba(239,68,68,.06)', 'rgba(239,68,68,.2)', '#fca5a5']}}[type];
  s.style.background=c[0];s.style.border='1px solid '+c[1];s.style.color=c[2];
  s.innerHTML=msg;s.style.display='';
}}
async function upload(e){{
  const f=e.target.files[0]; if(!f) return;
  const fd=new FormData(); fd.append('file',f);
  status('<span class="spin">⚙️</span> Processing <strong>'+f.name+'</strong> — please wait…','info');
  try{{
    const r=await fetch('/api/upload',{{method:'POST',body:fd}});
    const d=await r.json();
    if(r.ok){{status('✅ Loaded: <strong>'+d.title+'</strong>','ok');setTimeout(()=>location.href='/paper/'+d.paper_id,1000)}}
    else status('❌ '+d.error,'err');
  }}catch(e){{status('❌ '+e.message,'err');}}
}}
async function arxiv(){{
  const url=document.getElementById('ax').value.trim();
  if(!url){{status('❌ Please enter an arXiv URL','err');return}}
  status('<span class="spin">⚙️</span> Downloading from arXiv…','info');
  try{{
    const r=await fetch('/api/arxiv',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{url}})}});
    const d=await r.json();
    if(r.ok){{status('✅ Loaded: <strong>'+d.title+'</strong>','ok');setTimeout(()=>location.href='/paper/'+d.paper_id,1000)}}
    else status('❌ '+d.error,'err');
  }}catch(e){{status('❌ '+e.message,'err');}}
}}
</script>
""", "PaperIntel AI — Dashboard")

# ── Chat page ──────────────────────────────────────────
def chat_page(username, paper_id, paper_title, papers):
    items = ""
    for p in papers[:10]:
        t   = (p.get("title","Untitled"))[:40]
        act = "background:rgba(0,212,255,.1);border-color:rgba(0,212,255,.3);color:#e2e8f0" if p.get("id")==paper_id else ""
        items += f'<div class="si" onclick="window.location.href=\'/paper/{p["id"]}\'" style="{act}" title="{p.get("title","")}">📄 {t}</div>'
    if not items:
        items = "<p style='color:#334155;font-size:.8rem'>No history</p>"

    return page(f"""
<!-- navbar -->
<div class="glass-s" style="padding:11px 22px;display:flex;align-items:center;
     justify-content:space-between;flex-shrink:0;border-bottom:1px solid rgba(0,212,255,.1)">
  <div style="display:flex;align-items:center;gap:10px;min-width:0">
    <a href="/dashboard" style="display:flex;align-items:center;gap:8px;text-decoration:none;flex-shrink:0">
      <div class="gb" style="width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center">🧠</div>
      <span class="gt" style="font-weight:800;font-size:.95rem">PaperIntel</span>
    </a>
    <div style="width:1px;height:18px;background:rgba(0,212,255,.15);flex-shrink:0"></div>
    <div style="min-width:0">
      <div style="font-size:.83rem;color:#cbd5e1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
           title="{paper_title}">{paper_title}</div>
      <div style="font-size:.68rem;color:#475569">Research Paper Analysis</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:9px;flex-shrink:0">
    <div class="glass" style="padding:5px 11px;border-radius:7px;font-size:.8rem">👤 {username}</div>
    <button class="btn bs" style="font-size:.8rem;padding:6px 13px"
      onclick="fetch('/api/logout',{{method:'POST'}}).then(()=>location.href='/')">Logout</button>
  </div>
</div>

<!-- body -->
<div style="display:flex;flex:1;overflow:hidden">

  <!-- sidebar (mirrors Streamlit sidebar) -->
  <div class="sb">
    <div style="font-size:.73rem;font-weight:600;color:#64748b;text-transform:uppercase;
                letter-spacing:.05em;margin-bottom:10px">📜 History</div>
    {items}
    <div style="margin-top:18px;border-top:1px solid rgba(0,212,255,.08);padding-top:14px">
      <div style="font-size:.73rem;color:#64748b;margin-bottom:8px;font-weight:600">⚡ Quick prompts</div>
      <button class="btn bs" style="width:100%;margin-bottom:6px;font-size:.76rem;text-align:left;padding:7px 11px"
        onclick="sq('Summarize this paper in bullet points')">📝 Summarize</button>
      <button class="btn bs" style="width:100%;margin-bottom:6px;font-size:.76rem;text-align:left;padding:7px 11px"
        onclick="sq('What are the main flaws in this research?')">🔍 Find Flaws</button>
      <button class="btn bs" style="width:100%;margin-bottom:6px;font-size:.76rem;text-align:left;padding:7px 11px"
        onclick="sq('Generate a professional PPT presentation')">📊 Make PPT</button>
      <button class="btn bs" style="width:100%;font-size:.76rem;text-align:left;padding:7px 11px"
        onclick="sq('What are real-world applications for clinicians and researchers?')">💼 Applications</button>
    </div>
  </div>

  <!-- chat center (mirrors st.chat_message blocks) -->
  <div style="flex:1;display:flex;flex-direction:column;overflow:hidden">
    <div id="msgs" style="flex:1;overflow-y:auto;padding:22px 28px;display:flex;flex-direction:column;gap:14px">
      <div id="ph" style="text-align:center;margin:auto;opacity:.35">
        <div style="font-size:1.8rem;margin-bottom:6px">🧠</div>
        <div style="font-size:.88rem;color:#64748b">Ask anything about this paper…</div>
      </div>
    </div>
    <!-- input bar -->
    <div class="glass-s" style="padding:14px 22px;flex-shrink:0;border-top:1px solid rgba(0,212,255,.1)">
      <div style="display:flex;gap:9px;align-items:flex-end;max-width:860px;margin:0 auto">
        <textarea id="q" rows="2" style="flex:1;max-height:110px"
          placeholder="Ask anything… (Ctrl+Enter to send)"
          oninput="this.style.height='auto';this.style.height=Math.min(this.scrollHeight,110)+'px'"
          onkeydown="if(event.ctrlKey&&event.key==='Enter')send()"></textarea>
        <button class="btn bp" style="flex-shrink:0;padding:11px 20px;height:46px" onclick="send()">Send ➤</button>
      </div>
    </div>
  </div>
</div>

<!-- loading modal (mirrors Streamlit spinner) -->
<div id="modal" class="modal" style="display:none">
  <div class="mbox">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
      <span class="spin" style="font-size:1.3rem">⚙️</span>
      <div class="gt" style="font-weight:700;font-size:1rem">Analysing paper…</div>
    </div>
    <div id="mlog" style="max-height:150px;overflow-y:auto;display:flex;flex-direction:column;gap:5px"></div>
    <div class="pt"><div class="pf" id="pf" style="width:0%"></div></div>
    <div style="display:flex;justify-content:space-between;font-size:.72rem;color:#475569;margin-top:5px">
      <span id="pl">Starting…</span><span id="pp">0%</span>
    </div>
  </div>
</div>

<script>
const PID={paper_id};
let busy=false;

function sq(q){{document.getElementById('q').value=q;document.getElementById('q').focus();}}

function clr(){{const p=document.getElementById('ph');if(p)p.remove();}}

function msg(role,html){{
  clr();
  const w=document.getElementById('msgs');
  const d=document.createElement('div');d.className='fu';
  if(role==='user')       d.innerHTML='<div style="display:flex;justify-content:flex-end"><div class="bu">'+html+'</div></div>';
  else if(role==='sys')   d.innerHTML='<div class="bsy">'+html+'</div>';
  else if(role==='err')   d.innerHTML='<div class="ber">❌ '+html+'</div>';
  else                    d.innerHTML='<div class="ba">'+html+'</div>';
  w.appendChild(d);
  setTimeout(()=>w.scrollTop=w.scrollHeight,40);
}}

function md(t){{
  return t
    .replace(/\*\*(.*?)\*\*/g,'<strong style="color:#7dd3fc">$1</strong>')
    .replace(/\*(.*?)\*/g,'<em>$1</em>')
    .replace(/•\\s/g,'<span style="color:#00d4ff">• </span>')
    .replace(/\\n/g,'<br>');
}}

function logStep(m){{
  const b=document.getElementById('mlog');
  const r=document.createElement('div');
  r.style.cssText='font-size:.78rem;color:#94a3b8;display:flex;align-items:center;gap:5px';
  r.innerHTML='<span style="color:#00d4ff;font-size:.65rem">✔</span>'+m;
  b.appendChild(r);b.scrollTop=b.scrollHeight;
}}

function prog(pct,lbl){{
  document.getElementById('pf').style.width=pct+'%';
  document.getElementById('pp').textContent=pct+'%';
  document.getElementById('pl').textContent=lbl||'';
}}

async function send(){{
  if(busy)return;
  const q=document.getElementById('q').value.trim();if(!q)return;
  busy=true;
  msg('user',q);
  document.getElementById('q').value='';
  document.getElementById('q').style.height='auto';

  // show modal (mirrors st.spinner)
  document.getElementById('modal').style.display='flex';
  document.getElementById('mlog').innerHTML='';
  prog(0,'Starting…');

  let n=0;
  try{{
    const res=await fetch('/api/chat',{{
      method:'POST',headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{paper_id:PID,query:q}})
    }});
    if(!res.ok) throw new Error('HTTP '+res.status);

    const reader=res.body.getReader();const dec=new TextDecoder();let buf='';
    while(true){{
      const {{done,value}}=await reader.read();if(done)break;
      buf+=dec.decode(value);
      const lines=buf.split('\\n');buf=lines.pop();
      for(const line of lines){{
        if(!line.startsWith('data: '))continue;
        let data;try{{data=JSON.parse(line.slice(6));}}catch{{continue;}}

        if(data.type==='message'){{
          n++;logStep(data.content);
          prog(Math.min(n*15,90),data.content.slice(0,38)+'…');
        }}
        else if(data.type==='cached'){{
          logStep(data.content);
        }}
        else if(data.type==='result'){{
          prog(100,'Done!');
          document.getElementById('modal').style.display='none';
          const r=data.content;

          if(r.from_cache) msg('sys','⚡ Loaded from cache');

          // mirrors st.expander("💼 Real-World Applications")
          if(r.application) msg('ai',
            '<details open><summary style="font-weight:600;color:#00d4ff;margin-bottom:6px">💼 Real-World Applications</summary>'
            +'<div style="margin-top:8px">'+md(r.application)+'</div></details>');

          // mirrors st.expander("📊 PPT Outline")
          if(r.ppt_outline){{
            msg('ai',
              '<details open><summary style="font-weight:600;color:#00d4ff;margin-bottom:6px">📊 PPT Outline</summary>'
              +'<div style="margin-top:8px">'+md(r.ppt_outline)+'</div></details>');
            if(r.ppt_file)
              msg('sys','✅ PPT ready — <a href="/api/download-ppt/'+PID+'" style="color:#00d4ff;font-weight:600">⬇️ Download PowerPoint</a>');
          }}

          // mirrors st.markdown(final_response)
          const resp=r.final_output||r.summary||'✅ Analysis complete.';
          msg('ai',md(resp));
        }}
        else if(data.type==='error'){{
          document.getElementById('modal').style.display='none';
          msg('err',data.content);
        }}
      }}
    }}
  }}catch(e){{
    document.getElementById('modal').style.display='none';
    msg('err',e.message);
  }}finally{{busy=false;}}
}}
</script>
""", f"PaperIntel — {paper_title[:40]}")

# ═══════════════════════════════════════════════════════
#  APP
# ═══════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 PaperIntel AI starting…")
    init_db()
    yield

app = FastAPI(title="PaperIntel AI", lifespan=lifespan)
app.add_middleware(SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY","paperintel-secret-change-me"))

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def get_user(request: Request):
    u = request.session.get("user")
    if not u: raise HTTPException(401, "Not authenticated")
    return u

# ── auth ──────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse("/dashboard" if request.session.get("user") else "/login", 302)

@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    if request.session.get("user"): return RedirectResponse("/dashboard", 302)
    return HTMLResponse(login_page())

@app.post("/api/login")
async def post_login(request: Request):
    d = await request.json()
    u, p = d.get("username","").strip(), d.get("password","")
    if not u or not p: return JSONResponse({"error":"Missing credentials"}, 400)
    user = db_login(u, p)
    if not user: return JSONResponse({"error":"Invalid credentials"}, 401)
    request.session["user"] = user
    return JSONResponse({"success": True})

@app.post("/api/signup")
async def post_signup(request: Request):
    d = await request.json()
    u, p, c = d.get("username","").strip(), d.get("password",""), d.get("confirm_password","")
    if not u or not p or not c: return JSONResponse({"error":"Missing fields"}, 400)
    if p != c:      return JSONResponse({"error":"Passwords don't match"}, 400)
    if len(p) < 6:  return JSONResponse({"error":"Password must be at least 6 characters"}, 400)
    if db_signup(u, p): return JSONResponse({"success": True})
    return JSONResponse({"error":"Username already taken"}, 409)

@app.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"success": True})

# ── dashboard ─────────────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = request.session.get("user")
    if not user: return RedirectResponse("/login", 302)
    papers = db_get_papers(user["id"])
    return HTMLResponse(dashboard_page(user["username"], papers))

# ── upload ────────────────────────────────────────────
@app.post("/api/upload")
async def upload(request: Request, file: UploadFile = File(...),
                 user: dict = Depends(get_user)):
    pdf_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read()); pdf_path = tmp.name

        def ingest():
            paper  = IngestionAgent(use_grobid=True).ingest(pdf_path)
            chunks = ChunkingEmbedder().chunk_and_embed(paper)
            return paper, chunks

        paper, chunks = await asyncio.get_event_loop().run_in_executor(None, ingest)
        pid = db_save_paper(user["id"], paper, "", "", "", "")
        save_chunks(pid, chunks)
        logger.info(f"✅ upload '{paper.title}' pid={pid} chunks={len(chunks)}")
        return JSONResponse({"status":"success","paper_id":pid,"title":paper.title})

    except Exception as e:
        logger.error(e)
        if "429" in str(e) or "rate limit" in str(e).lower():
            return JSONResponse({"error":"API rate limit — please retry later"}, 429)
        return JSONResponse({"error":str(e)}, 500)
    finally:
        if pdf_path and os.path.exists(pdf_path): os.unlink(pdf_path)

@app.post("/api/arxiv")
async def arxiv(request: Request, user: dict = Depends(get_user)):
    pdf_path = None
    try:
        body = await request.json()
        url  = body.get("url","").strip()
        if not url: return JSONResponse({"error":"Missing arXiv URL"}, 400)

        def dl():
            path   = download_arxiv_paper(url)
            paper  = IngestionAgent(use_grobid=True).ingest(path)
            chunks = ChunkingEmbedder().chunk_and_embed(paper)
            return path, paper, chunks

        pdf_path, paper, chunks = await asyncio.get_event_loop().run_in_executor(None, dl)
        pid = db_save_paper(user["id"], paper, "", "", "", "")
        save_chunks(pid, chunks)
        return JSONResponse({"status":"success","paper_id":pid,"title":paper.title})
    except Exception as e:
        logger.error(e); return JSONResponse({"error":str(e)}, 500)
    finally:
        if pdf_path and os.path.exists(pdf_path):
            try: os.unlink(pdf_path)
            except: pass

# ── paper view ────────────────────────────────────────
@app.get("/paper/{paper_id}", response_class=HTMLResponse)
async def view_paper(paper_id: int, request: Request, user: dict = Depends(get_user)):
    row = db_get_paper(paper_id, user["id"])
    if not row: return HTMLResponse("<h2 style='color:red;padding:40px'>Paper not found — please re-upload.</h2>")
    paper  = deser(row["knowledge_json"])
    papers = db_get_papers(user["id"])
    return HTMLResponse(chat_page(user["username"], paper_id, paper.title, papers))

# ── chat stream ───────────────────────────────────────
@app.post("/api/chat")
async def chat(request: Request, user: dict = Depends(get_user)):
    # Read EVERYTHING before StreamingResponse — body is gone inside generator
    try:    body = await request.json()
    except: return JSONResponse({"error":"Bad request body"}, 400)

    paper_id = body.get("paper_id")
    query    = body.get("query","").strip()
    if not paper_id or not query:
        return JSONResponse({"error":"Missing paper_id or query"}, 400)

    row = db_get_paper(paper_id, user["id"])
    if not row: return JSONResponse({"error":"Paper not found — please re-upload."}, 404)
    paper = deser(row["knowledge_json"])

    # mirrors: cached = get_cached_response(...)
    cached = get_cached(paper.title, query)
    if cached:
        cached["from_cache"] = True
        async def cgen():
            yield f"data: {json.dumps({'type':'cached','content':'⚡ Loaded from cache!'})}\n\n"
            yield f"data: {json.dumps({'type':'result','content':cached})}\n\n"
        return StreamingResponse(cgen(), media_type="text/event-stream")

    chunks = load_chunks(paper_id)
    if not chunks: logger.warning(f"⚠️ no chunks for pid={paper_id}")

    return StreamingResponse(
        sse_pipeline(paper, query, chunks, user["id"]),
        media_type="text/event-stream"
    )

# ── ppt download ──────────────────────────────────────
@app.get("/api/download-ppt/{paper_id}")
async def download_ppt(paper_id: int, user: dict = Depends(get_user)):
    row = db_get_paper(paper_id, user["id"])
    if not row: return JSONResponse({"error":"Paper not found"}, 404)
    ppt = row.get("ppt_filename","")
    if not ppt or not os.path.exists(ppt):
        return JSONResponse({"error":"PPT not found — generate it first via chat."}, 404)
    return FileResponse(ppt, filename="Paper_Presentation.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")

@app.exception_handler(HTTPException)
async def http_exc(r, exc):
    return JSONResponse(status_code=exc.status_code, content={"error":exc.detail})

@app.get("/health")
async def health():
    return JSONResponse({"status":"ok","redis":redis_client is not None})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_fastapi:app", host="0.0.0.0", port=8000, reload=True)