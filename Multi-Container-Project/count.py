import os
import json
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string, request
import redis

APP_NAME = "SiteScope"

# --- Flask & Redis ---
app = Flask(__name__)
redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = int(os.getenv("REDIS_PORT", 6379))
r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

# --- Keys ---
K_VISIT_COUNT = "vc:count"     # integer
K_VISITS_LIST = "vc:visits"    # list of JSON docs (newest first)

# --- Helpers ---
def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def get_total_count():
    val = r.get(K_VISIT_COUNT)
    return int(val) if val else 0

def list_visits(limit=100):
    raw = r.lrange(K_VISITS_LIST, 0, max(1, min(int(limit), 1000)) - 1)
    return [json.loads(x) for x in raw]

def create_visit(ip: str, ua: str):
    count_after = r.incr(K_VISIT_COUNT)
    doc = {
        "created_date": now_iso(),
        "ip_address": ip or "unknown",
        "user_agent": ua or "unknown",
        "count_after": count_after,
    }
    r.lpush(K_VISITS_LIST, json.dumps(doc))
    r.ltrim(K_VISITS_LIST, 0, 999)  # cap size
    return count_after, doc

# --- API ---
@app.route("/api/state")
def api_state():
    return jsonify({"name": APP_NAME, "count": get_total_count()})

@app.route("/api/visits")
def api_visits():
    limit = request.args.get("limit", "100")
    try:
        n = max(1, min(int(limit), 1000))
    except Exception:
        n = 100
    return jsonify({"items": list_visits(n), "total": get_total_count()})

@app.route("/api/analytics")
def api_analytics():
    items = list_visits(2000)

    def parse_dt(s):
        try:
            if s.endswith("Z"):
                s = s[:-1]
            return datetime.fromisoformat(s)
        except Exception:
            return None

    now = datetime.utcnow()
    today_key = now.strftime("%Y-%m-%d")
    last7_dt = [now - timedelta(days=i) for i in range(6, -1, -1)]
    last7_keys = [d.strftime("%Y-%m-%d") for d in last7_dt]
    last7_labels = [d.strftime("%b %d") for d in last7_dt]

    daily_counts = {k: 0 for k in last7_keys}
    hourly_counts = {f"{h:02d}:00": 0 for h in range(24)}

    for v in items:
        dt = parse_dt(v.get("created_date", ""))
        if not dt:
            continue
        dkey = dt.strftime("%Y-%m-%d")
        if dkey in daily_counts:
            daily_counts[dkey] += 1
        if dkey == today_key:
            hourly_counts[f"{dt.hour:02d}:00"] += 1

    daily = [{"date": lbl, "visits": daily_counts[k]} for k, lbl in zip(last7_keys, last7_labels)]
    hourly = [{"hour": h, "visits": hourly_counts[h]} for h in hourly_counts]
    hourly = [h for h in hourly if h["visits"] > 0]

    return jsonify({"daily": daily, "hourly": hourly})

@app.route("/api/incr", methods=["POST", "GET"])
def api_incr():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
    ua = request.headers.get("User-Agent", "unknown")
    count_after, doc = create_visit(ip, ua)
    return jsonify({"ok": True, "count": count_after, "visit": doc})

# --- THEME + UI (Dark/Light toggle, “Vue-like” cards & CTA) ---
BASE_CSS = """
<style>
  :root {
    /* shared */
    --radius: 14px;
    --border: 1px;
    --shadow: 0 12px 28px rgba(0,0,0,.18);

    /* dark default */
    --bg: #0b1220;              /* page bg */
    --muted: #9aa4b2;
    --text: #e6edf6;
    --card-text: #c9d4e0;
    --card-ring: rgba(148,163,184,.18);
    --kpi-blue: #7aa2ff;
    --kpi-green: #34d399;

    --card1: linear-gradient(135deg,#171f34 0%,#232b45 60%);
    --card1-spot: radial-gradient(600px 600px at 85% 10%, rgba(114,84,175,.3), transparent 60%);
    --card2: linear-gradient(135deg,#102a2a 0%,#102a2a 30%, #0d2a22 100%);
    --card2-spot: radial-gradient(600px 600px at 88% 8%, rgba(16,185,129,.18), transparent 60%);
    --btn-grad: linear-gradient(90deg,#5b8cff 0%,#8b5cf6 100%);
    --btn-text: #ffffff;
    --chip-blue-bg:#1f2a44; --chip-blue:#97b4ff;
    --chip-green-bg:#0f2b26; --chip-green:#61e1c5;
    --divider: rgba(148,163,184,.12);
  }
  [data-theme="light"] {
    --bg: #f7fafc;
    --muted: #4b5563;
    --text: #0f172a;
    --card-text: #334155;
    --card-ring: rgba(15,23,42,.08);
    --kpi-blue: #2563eb;
    --kpi-green: #059669;

    --card1: linear-gradient(135deg,#e8ecf7 0%,#e6e9f6 60%);
    --card1-spot: radial-gradient(600px 600px at 85% 10%, rgba(99,102,241,.16), transparent 60%);
    --card2: linear-gradient(135deg,#e9fbf7 0%,#e3f3ef 100%);
    --card2-spot: radial-gradient(600px 600px at 88% 8%, rgba(16,185,129,.16), transparent 60%);
    --btn-grad: linear-gradient(90deg,#3b82f6 0%,#8b5cf6 100%);
    --btn-text: #ffffff;
    --chip-blue-bg:#e6ecff; --chip-blue:#1d4ed8;
    --chip-green-bg:#e6fff8; --chip-green:#047857;
    --divider: rgba(2,6,23,.08);
  }

  html,body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,'Helvetica Neue',Arial}
  body{background:var(--bg); color:var(--text);}
  a{text-decoration:none}

  .container{max-width:1200px;margin:0 auto;padding:24px;}
  .hdr{display:flex;gap:12px;align-items:center;justify-content:space-between;margin-bottom:20px}
  .brand{font-weight:800;font-size:28px;background:linear-gradient(90deg,#60a5fa, #a78bfa);-webkit-background-clip:text;background-clip:text;color:transparent}
  .nav{display:flex;gap:8px}
  .pill{padding:10px 14px;border-radius:12px;border:var(--border) solid var(--card-ring);color:var(--text)}

  .grid{display:grid;grid-template-columns:1fr;gap:20px}
  @media(min-width:900px){.grid{grid-template-columns:1fr 1fr}}

  .card{position:relative;border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;border:var(--border) solid var(--card-ring)}
  .card .inner{position:relative;padding:24px}
  .card h3{display:flex;align-items:center;gap:10px;margin:0 0 6px 0}
  .muted{color:var(--muted)}
  .kpi{font-weight:800;line-height:1}

  .c1{background:var(--card1)}
  .c1::after{content:"";position:absolute;inset:0;background:var(--card1-spot);pointer-events:none}
  .kpi-blue{color:var(--kpi-blue)}

  .c2{background:var(--card2)}
  .c2::after{content:"";position:absolute;inset:0;background:var(--card2-spot);pointer-events:none}
  .kpi-green{color:var(--kpi-green)}
  .chip{display:inline-flex;align-items:center;gap:8px;border-radius:14px;padding:10px;border:var(--border) solid var(--card-ring);color:var(--text);}

  .btn{display:inline-flex;align-items:center;gap:8px;padding:10px 16px;border-radius:12px;background:var(--btn-grad);color:var(--btn-text);font-weight:700;border:none;cursor:pointer}
  .btn:disabled{opacity:.6;cursor:not-allowed}

  .row{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-top:var(--border) solid var(--divider)}
  .row:first-child{border-top:0}
  .row:hover{background:rgba(255,255,255,.02)}
  .recent{border-radius:var(--radius);border:var(--border) solid var(--card-ring);overflow:hidden}
  .recent-h{display:flex;align-items:center;gap:10px;padding:14px 18px;border-bottom:var(--border) solid var(--divider)}
  .ip{font-size:12px;color:var(--muted);display:flex;gap:6px;align-items:center}

  .toggle{display:flex;align-items:center;gap:10px}
  .tbtn{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:12px;border:var(--border) solid var(--card-ring);background:transparent;color:var(--text);cursor:pointer}

  /* Landing specific */
  .hero-card{
      max-width: 980px;margin: 48px auto;background: #ffffff10;
      border-radius: var(--radius); border: var(--border) solid var(--card-ring);
      box-shadow: var(--shadow); overflow:hidden; position:relative;
      backdrop-filter: blur(12px);
  }
  .hero-card::after{
      content:""; position:absolute; inset:0;
      background: radial-gradient(700px 700px at 80% -10%, rgba(99,102,241,.20), transparent 60%),
                  radial-gradient(700px 700px at -20% 120%, rgba(16,185,129,.18), transparent 60%);
      pointer-events:none;
  }
  .hero-inner{ padding: 48px 28px; background: var(--bg); }
  .logo-ring{ width:56px;height:56px;border-radius:14px;display:flex;align-items:center;justify-content:center;
              border:var(--border) solid var(--card-ring); background: #ffffff10; margin:0 auto 12px auto; }
  .title{ text-align:center; font-weight:800; letter-spacing:.2px; margin: 6px 0 8px 0; }
  .subtitle{ text-align:center; color:var(--muted); }
  .cta-row{ display:flex; gap:12px; justify-content:center; margin-top:20px; flex-wrap:wrap; }
</style>
"""

# ---------- LANDING (Home "/") ----------
LANDING_HTML = """
<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{{ name }} | Home</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
  {{ base_css|safe }}
</head>
<body>
  <div class="container" style="max-width:1100px;">
    <div class="hdr" style="margin-bottom:0">
      <div class="brand">{{ name }}</div>
      <div style="display:flex;gap:10px;align-items:center">
        <div class="toggle">
          <button id="theme-dark" class="tbtn">🌙 Dark</button>
          <button id="theme-light" class="tbtn">☀️ Light</button>
        </div>
        <nav class="nav">
          <a class="pill" href="/count">Count</a>
          <a class="pill" href="/analytics">Analytics</a>
        </nav>
      </div>
    </div>

    <div class="hero-card">
      <div class="hero-inner">
        <div class="logo-ring">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" style="color:#8b5cf6">
            <path d="M12 3a9 9 0 1 0 9 9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <circle cx="18" cy="6" r="2" fill="currentColor"/>
          </svg>
        </div>
        <h1 class="title" style="font-size:clamp(28px,5vw,42px);">Welcome to {{ name }}</h1>
        <p class="subtitle">A modern, containerized visit tracker with analytics. Click below to see the live counter.</p>

        <div class="cta-row">
          <a href="/count" class="btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M13 11h6M5 13l4 4L19 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            View Visit Count
          </a>
          <a href="/analytics" class="tbtn">Analytics</a>
        </div>
      </div>
    </div>
  </div>

  <script>
    function setTheme(mode){
      document.documentElement.setAttribute('data-theme', mode);
      localStorage.setItem('sitescope_theme', mode);
    }
    (function(){ setTheme(localStorage.getItem('sitescope_theme') || 'dark'); })();
    document.getElementById('theme-dark').addEventListener('click', ()=>setTheme('dark'));
    document.getElementById('theme-light').addEventListener('click', ()=>setTheme('light'));
  </script>
</body>
</html>
"""

# ---------- DASHBOARD (now at "/count") ----------
DASHBOARD_HTML = """
<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{{ name }} | Count</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
  {{ base_css|safe }}
</head>
<body>
  <div class="container">
    <!-- Header -->
    <div class="hdr">
      <div>
        <div class="brand">{{ name }}</div>
        <div class="muted" style="font-size:13px;margin-top:2px;">Track visits • Monitor activity • Analyze trends</div>
      </div>
      <div style="display:flex;gap:10px;align-items:center">
        <div class="toggle">
          <button id="theme-dark" class="tbtn">🌙 Dark</button>
          <button id="theme-light" class="tbtn">☀️ Light</button>
        </div>
        <nav class="nav">
          <a class="pill" href="/">Home</a>
          <a class="pill" href="/analytics">Analytics</a>
        </nav>
      </div>
    </div>

    <!-- KPI Cards -->
    <div class="grid">
      <!-- Total Page Views -->
      <div class="card c1">
        <div class="inner">
          <h3>
            <span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:10px;background:rgba(99,102,241,.2);color:#9aa5ff;border:var(--border) solid var(--card-ring)">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M2 12s4-8 10-8 10 8 10 8-4 8-10 8-10-8-10-8Z" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>
            </span>
            <span style="font-weight:700">Total Page Views</span>
          </h3>
          <div id="kpi-total" class="kpi kpi-blue" style="font-size:64px;margin:12px 0 16px 0">{{ count }}</div>

          <button id="btn-visit" class="btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M13 11h6M5 13l4 4L19 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            Visit Page
          </button>
        </div>
      </div>

      <!-- Today's Activity -->
      <div class="card c2">
        <div class="inner">
          <h3>
            <span style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:10px;background:rgba(16,185,129,.18);color:#4ade80;border:var(--border) solid var(--card-ring)">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M3 12h6l3 7 3-14 3 7h3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </span>
            <span style="font-weight:700">Today's Activity</span>
          </h3>
          <div id="kpi-today" class="kpi kpi-green" style="font-size:64px;margin:12px 0 6px 0">0</div>
          <div class="muted" id="kpi-today-label" style="margin-bottom:12px">visits today</div>

          <div class="chip" style="margin-top:6px;">
            <strong>Growth Rate:</strong>
            <span id="kpi-growth" class="muted">0% of total</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Activity -->
    <div class="recent" style="margin-top:22px;">
      <div class="recent-h">
        <span style="display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:8px;background:var(--chip-blue-bg);color:var(--chip-blue)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 8v4l3 3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </span>
        <strong>Recent Activity</strong>
        <span class="muted" style="margin-left:auto;font-size:12px;">Auto-refreshes</span>
      </div>
      <div id="recent-list"></div>
    </div>
  </div>

  <script>
    // Theme toggle
    function setTheme(mode){
      document.documentElement.setAttribute('data-theme', mode);
      localStorage.setItem('sitescope_theme', mode);
    }
    (function(){ setTheme(localStorage.getItem('sitescope_theme') || 'dark'); })();
    document.getElementById('theme-dark').addEventListener('click', ()=>setTheme('dark'));
    document.getElementById('theme-light').addEventListener('click', ()=>setTheme('light'));

    async function j(u, o){ const r = await fetch(u, o); return r.json(); }
    function fmtDate(s){
      try{ const d = new Date(s);
        return [d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'}),
                d.toLocaleDateString([], {month:'short', day:'numeric'})];
      }catch{ return ['--:--','—']; }
    }

    async function loadState(){
      const st = await j('/api/state');
      const list = await j('/api/visits?limit=999');

      const total = st.count || 0;
      document.getElementById('kpi-total').textContent = Intl.NumberFormat().format(total);

      const todayStr = new Date().toDateString();
      const items = (list.items || []);
      const todayCount = items.filter(v => new Date(v.created_date).toDateString() === todayStr).length;
      document.getElementById('kpi-today').textContent = todayCount.toString();
      document.getElementById('kpi-today-label').textContent = todayCount === 1 ? 'visit today' : 'visits today';
      const growth = total > 0 ? ((todayCount/total)*100).toFixed(1)+'% of total' : '0% of total';
      document.getElementById('kpi-growth').textContent = growth;

      const container = document.getElementById('recent-list');
      container.innerHTML = '';
      if(items.length === 0){
        container.innerHTML = '<div class="row" style="justify-content:center;color:var(--muted)">No visits yet — refresh the page.</div>';
      }else{
        items.slice(0, 14).forEach(v=>{
          const [t, d] = fmtDate(v.created_date);
          const ip = v.ip_address ? v.ip_address : 'Unknown IP';
          const idx = (list.total || 0) - (v.count_after || 0) + 1;
          container.insertAdjacentHTML('beforeend', `
            <div class="row">
              <div style="display:flex;align-items:center;gap:12px">
                <div style="width:36px;height:36px;border-radius:999px;background:var(--chip-blue-bg);color:var(--chip-blue);display:flex;align-items:center;justify-content:center">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z" stroke="currentColor" stroke-width="2"/><path d="M2 22a10 10 0 0 1 20 0" stroke="currentColor" stroke-width="2"/></svg>
                </div>
                <div>
                  <div style="font-weight:600">Page Visit #${idx}</div>
                  <div class="ip"><svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 4a6 6 0 1 1 0 12A6 6 0 0 1 12 6Z"/></svg>${ip}</div>
                </div>
              </div>
              <div style="text-align:right">
                <div style="font-weight:600">${t}</div>
                <div class="muted" style="font-size:12px">${d}</div>
              </div>
            </div>
          `);
        });
      }
    }

    // Increment button (AJAX)
    const btn = document.getElementById('btn-visit');
    btn.addEventListener('click', async ()=>{
      btn.disabled = True;
      try{
        await j('/api/incr', { method:'POST' });
        await loadState();
      } finally { btn.disabled = False; }
    });

    // Initial load (server already incremented on render)
    loadState();
    setInterval(loadState, 30000);
  </script>
</body>
</html>
"""

# ---------- ANALYTICS ----------
ANALYTICS_HTML = """
<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{{ name }} | Analytics</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  {{ base_css|safe }}
</head>
<body>
  <div class="container">
    <div class="hdr">
      <div class="brand">Analytics</div>
      <div style="display:flex;gap:10px;align-items:center">
        <div class="toggle">
          <button id="theme-dark" class="tbtn">🌙 Dark</button>
          <button id="theme-light" class="tbtn">☀️ Light</button>
        </div>
        <a class="pill" href="/">← Home</a>
      </div>
    </div>

    <div class="grid">
      <div class="card c1"><div class="inner"><div class="muted">Total Visits</div><div id="stat-total" class="kpi kpi-blue" style="font-size:44px">—</div></div></div>
      <div class="card c2"><div class="inner"><div class="muted">Today's Visits</div><div id="stat-today" class="kpi kpi-green" style="font-size:44px">—</div></div></div>
    </div>

    <div class="grid" style="margin-top:20px">
      <div class="card"><div class="inner"><div style="font-weight:700;margin-bottom:6px">Daily Visits (Last 7 Days)</div><canvas id="dailyChart" height="220"></canvas></div></div>
      <div class="card"><div class="inner"><div style="font-weight:700;margin-bottom:6px">Hourly Today</div><canvas id="hourlyChart" height="220"></canvas></div></div>
    </div>
  </div>

  <script>
    function setTheme(mode){
      document.documentElement.setAttribute('data-theme', mode);
      localStorage.setItem('sitescope_theme', mode);
    }
    (function(){ setTheme(localStorage.getItem('sitescope_theme') || 'dark'); })();
    document.getElementById('theme-dark').addEventListener('click', ()=>setTheme('dark'));
    document.getElementById('theme-light').addEventListener('click', ()=>setTheme('light'));

    let dailyChart, hourlyChart;
    async function j(u){ const r = await fetch(u); return r.json(); }

    async function load(){
      const st = await j('/api/state');
      const vis = await j('/api/visits?limit=2000');
      const an = await j('/api/analytics');

      document.getElementById('stat-total').textContent = st.count || 0;
      const todayStr = new Date().toDateString();
      const todayCount = (vis.items||[]).filter(v => new Date(v.created_date).toDateString() === todayStr).length;
      document.getElementById('stat-today').textContent = todayCount;

      const dCtx = document.getElementById('dailyChart').getContext('2d');
      if(dailyChart) dailyChart.destroy();
      dailyChart = new Chart(dCtx, {
        type: 'bar',
        data: { labels: (an.daily||[]).map(x=>x.date), datasets: [{ label: 'Visits', data: (an.daily||[]).map(x=>x.visits) }] },
        options: {
          responsive:true,
          scales:{ x:{ ticks:{color:getComputedStyle(document.documentElement).getPropertyValue('--muted')}, grid:{color:'rgba(148,163,184,.25)'} }, y:{ beginAtZero:true, ticks:{color:getComputedStyle(document.documentElement).getPropertyValue('--muted')}, grid:{color:'rgba(148,163,184,.25)'} } },
          plugins:{ legend:{ labels:{ color:getComputedStyle(document.documentElement).getPropertyValue('--muted') } } }
        }
      });

      const hCtx = document.getElementById('hourlyChart').getContext('2d');
      if(hourlyChart) hourlyChart.destroy();
      hourlyChart = new Chart(hCtx, {
        type: 'line',
        data: { labels: (an.hourly||[]).map(x=>x.hour), datasets: [{ label:'Visits', data:(an.hourly||[]).map(x=>x.visits) }] },
        options: {
          responsive:true,
          scales:{ x:{ ticks:{color:getComputedStyle(document.documentElement).getPropertyValue('--muted')}, grid:{color:'rgba(148,163,184,.25)'} }, y:{ beginAtZero:true, ticks:{color:getComputedStyle(document.documentElement).getPropertyValue('--muted')}, grid:{color:'rgba(148,163,184,.25)'} } },
          plugins:{ legend:{ labels:{ color:getComputedStyle(document.documentElement).getPropertyValue('--muted') } } }
        }
      });
    }
    load();
  </script>
</body>
</html>
"""

# --- Routes ---
@app.route("/")
def home():  # thumbnail landing; does NOT increment
    return render_template_string(LANDING_HTML, name=APP_NAME, base_css=BASE_CSS)

@app.route("/count")
def count_page():  # full dashboard; increments on refresh
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
    ua = request.headers.get("User-Agent", "unknown")
    count_after, _ = create_visit(ip, ua)
    return render_template_string(DASHBOARD_HTML, name=APP_NAME, base_css=BASE_CSS, count=count_after)

@app.route("/analytics")
def analytics():
    return render_template_string(ANALYTICS_HTML, name=APP_NAME, base_css=BASE_CSS)

# --- Main ---
if __name__ == "__main__":
    r.setnx(K_VISIT_COUNT, 0)
    app.run(host="0.0.0.0", port=5002)