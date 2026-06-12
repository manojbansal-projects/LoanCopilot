"""
Langfuse Metrics Report — pulls all trace and observation data from Langfuse
and prints a structured analysis suitable for model evaluation.

Run from project root:
    python3 scripts/langfuse_metrics.py
"""
import sys, os, base64, urllib.request, json
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deployment.config import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST

if not LANGFUSE_PUBLIC_KEY:
    print("ERROR: LANGFUSE_PUBLIC_KEY not set in .env")
    sys.exit(1)

CREDS  = base64.b64encode(f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()).decode()
BASE   = LANGFUSE_HOST.rstrip("/")
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RESET  = "\033[0m"


def api(path: str) -> dict:
    req = urllib.request.Request(f"{BASE}{path}", headers={"Authorization": f"Basic {CREDS}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


# ── Fetch traces ──────────────────────────────────────────────────────────────
trace_data  = api("/api/public/traces?limit=100")
traces      = trace_data.get("data", [])
total_traces = trace_data.get("meta", {}).get("totalItems", len(traces))

# ── Fetch generation observations ────────────────────────────────────────────
gen_data = api("/api/public/observations?type=GENERATION&limit=100")
gens     = gen_data.get("data", [])

# ── Fetch scores ──────────────────────────────────────────────────────────────
try:
    score_data = api("/api/public/scores?limit=100")
    scores = score_data.get("data", [])
except Exception:
    scores = []

# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{'═'*66}{RESET}")
print(f"{BOLD}  LANGFUSE MODEL METRICS REPORT{RESET}")
print(f"{BOLD}  Generated: {datetime.now().strftime('%d %b %Y %H:%M')}{RESET}")
print(f"{BOLD}{'═'*66}{RESET}")

# ── 1. Overview ───────────────────────────────────────────────────────────────
costs     = [float(t.get("totalCost") or 0) for t in traces]
latencies = [float(t.get("latency") or 0) for t in traces if t.get("latency")]

total_cost = sum(costs)
avg_cost   = total_cost / max(1, len(traces))

print(f"\n{CYAN}1. OVERVIEW{RESET}")
print(f"   Total traces logged     : {total_traces}")
print(f"   Traces fetched          : {len(traces)}")
print(f"   Generation observations : {len(gens)}")
print(f"   Score records           : {len(scores)}")

# ── 2. Cost analysis ─────────────────────────────────────────────────────────
print(f"\n{CYAN}2. COST ANALYSIS{RESET}")
print(f"   Total cost              : ${total_cost:.4f}")
print(f"   Avg cost per trace      : ${avg_cost:.4f}")
if costs:
    print(f"   Max cost (single trace) : ${max(costs):.4f}")
    non_zero = [c for c in costs if c > 0]
    if non_zero:
        print(f"   Min cost (single trace) : ${min(non_zero):.4f}")

# Cost by day
by_day = defaultdict(float)
count_by_day = Counter()
for t in traces:
    day = (t.get("timestamp") or "")[:10]
    by_day[day] += float(t.get("totalCost") or 0)
    count_by_day[day] += 1

print(f"\n   Daily breakdown:")
for day in sorted(by_day.keys(), reverse=True):
    print(f"     {day}  {count_by_day[day]:3d} traces  ${by_day[day]:.4f}")

# ── 3. Token usage ────────────────────────────────────────────────────────────
in_tokens  = [int(g.get("usage", {}).get("input")  or 0) for g in gens]
out_tokens = [int(g.get("usage", {}).get("output") or 0) for g in gens]
tot_in  = sum(in_tokens)
tot_out = sum(out_tokens)

print(f"\n{CYAN}3. TOKEN USAGE{RESET}")
print(f"   Total input tokens      : {tot_in:,}")
print(f"   Total output tokens     : {tot_out:,}")
if gens:
    print(f"   Avg input per LLM call  : {tot_in // max(1, len(gens)):,}")
    print(f"   Avg output per LLM call : {tot_out // max(1, len(gens)):,}")
    print(f"   Input:Output ratio      : {tot_in / max(1, tot_out):.1f}:1")

# ── 4. Latency ────────────────────────────────────────────────────────────────
print(f"\n{CYAN}4. LATENCY (seconds, per trace){RESET}")
if latencies:
    lat_sorted = sorted(latencies)
    n = len(lat_sorted)
    p50 = lat_sorted[n // 2]
    p90 = lat_sorted[int(n * 0.90)]
    p95 = lat_sorted[int(n * 0.95)]
    avg = sum(latencies) / n
    print(f"   Avg latency             : {avg:.2f}s")
    print(f"   P50 latency             : {p50:.2f}s")
    print(f"   P90 latency             : {p90:.2f}s")
    print(f"   P95 latency             : {p95:.2f}s")
    print(f"   Max latency             : {max(latencies):.2f}s")
else:
    print("   No latency data available")

# ── 5. Model distribution ─────────────────────────────────────────────────────
models = Counter(g.get("model") or "unknown" for g in gens)
print(f"\n{CYAN}5. MODEL DISTRIBUTION{RESET}")
for model, cnt in models.most_common():
    pct = 100 * cnt / max(1, len(gens))
    print(f"   {model:30s}  {cnt:4d} calls  ({pct:.0f}%)")

# ── 6. Scores / RLHF ─────────────────────────────────────────────────────────
print(f"\n{CYAN}6. SCORES / FEEDBACK{RESET}")
if scores:
    by_name = defaultdict(list)
    for s in scores:
        by_name[s.get("name", "unknown")].append(float(s.get("value") or 0))
    for name, vals in sorted(by_name.items()):
        avg_v = sum(vals) / len(vals)
        print(f"   {name:30s}  n={len(vals):3d}  avg={avg_v:.3f}  min={min(vals):.2f}  max={max(vals):.2f}")
else:
    print("   No score data yet.")

# ── 7. Session coverage ───────────────────────────────────────────────────────
sessions_seen = Counter()
for t in traces:
    sid = t.get("sessionId") or "(no session)"
    sessions_seen[sid] += 1

print(f"\n{CYAN}7. SESSION COVERAGE{RESET}")
print(f"   Unique sessions         : {len(sessions_seen)}")
no_session = sessions_seen.get("(no session)", 0)
with_session = len(traces) - no_session
print(f"   Traces with session_id  : {with_session}  ({100*with_session//max(1,len(traces))}%)")
print(f"   Traces without session  : {no_session}  ({100*no_session//max(1,len(traces))}%)")
if no_session > 0:
    print(f"   {YELLOW}Note: session_id tagging has been fixed in langfuse_logger.py —{RESET}")
    print(f"   {YELLOW}future runs will properly group traces by session.{RESET}")

# ── 8. Top traces by cost ─────────────────────────────────────────────────────
print(f"\n{CYAN}8. TOP 5 TRACES BY COST{RESET}")
top5 = sorted(traces, key=lambda t: float(t.get("totalCost") or 0), reverse=True)[:5]
for t in top5:
    tid  = t.get("id", "")[:16]
    ts   = (t.get("timestamp") or "")[:16]
    cost = float(t.get("totalCost") or 0)
    inp  = str(t.get("input") or {})
    msg  = ""
    if isinstance(t.get("input"), dict):
        msgs = t["input"].get("messages", [])
        if msgs:
            msg = str(msgs[0].get("content", ""))[:60]
    print(f"   ${cost:.4f}  {ts}  {msg}")

# ── 9. Langfuse links ─────────────────────────────────────────────────────────
print(f"\n{CYAN}9. LANGFUSE LINKS{RESET}")
print(f"   Dashboard: {BASE}")
recent = sorted(traces, key=lambda t: t.get("timestamp", ""), reverse=True)[:5]
for t in recent:
    tid = t.get("id", "")
    ts  = (t.get("timestamp") or "")[:16]
    msg = ""
    if isinstance(t.get("input"), dict):
        msgs = t["input"].get("messages", [])
        if msgs:
            msg = str(msgs[0].get("content", ""))[:50]
    print(f"   {ts}  {BASE}/traces/{tid}  {msg}")

print(f"\n{BOLD}{'═'*66}{RESET}")
print(f"{GREEN}✓ Report complete.{RESET}\n")
