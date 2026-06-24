"""
theater.py — vega
The vega Content Theater. Review every generated video/image before posting.
Runs at http://localhost:8888

Rule 13: Only shows real files that exist on disk. Never fakes content.
Rule 1: Videos are actually playable. Approval is actually recorded.

Usage:
    cd /Users/EverettN/mcp-media-ingestor
    python3 -m vega.theater

Author: Everett Christman / The Christman AI Project
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

logger = logging.getLogger("vega.theater")

VIDEO_DIR  = Path("/Users/EverettN/mcp-media-ingestor/vega_output/video")
POSTS_FILE = Path("/Users/EverettN/mcp-media-ingestor/vega/data/posts.json")
APPROVED_FILE = Path("/Users/EverettN/mcp-media-ingestor/vega/data/approved.json")

app = Flask(__name__, static_folder=None)


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_posts() -> list[dict]:
    if not POSTS_FILE.exists():
        return []
    with open(POSTS_FILE) as f:
        return json.load(f)

def save_posts(posts: list[dict]) -> None:
    with open(POSTS_FILE, "w") as f:
        json.dump(posts, f, indent=2)

def load_approved() -> list[dict]:
    if not APPROVED_FILE.exists():
        return []
    with open(APPROVED_FILE) as f:
        return json.load(f)

def save_approved(approved: list[dict]) -> None:
    with open(APPROVED_FILE, "w") as f:
        json.dump(approved, f, indent=2)

def scan_videos() -> list[dict]:
    """Scan video dir and sync with posts.json. Returns merged list."""
    posts = load_posts()
    posts_by_path = {p.get("file_path"): p for p in posts if p.get("file_path")}
    approved_ids = {a["post_id"] for a in load_approved()}

    videos = []
    if not VIDEO_DIR.exists():
        return videos

    for f in sorted(VIDEO_DIR.glob("*.mp4"), reverse=True):
        path_str = str(f)
        post = posts_by_path.get(path_str, {})
        videos.append({
            "filename":  f.name,
            "path":      path_str,
            "size_mb":   round(f.stat().st_size / 1_000_000, 1),
            "created":   datetime.fromtimestamp(f.stat().st_mtime).strftime("%b %d %I:%M %p"),
            "post_id":   post.get("id", f.stem),
            "platform":  post.get("platform", "unknown"),
            "prompt":    post.get("prompt", ""),
            "status":    post.get("status", "ready"),
            "approved":  post.get("id", f.stem) in approved_ids,
        })
    return videos


# ── API routes ─────────────────────────────────────────────────────────────────

@app.route("/api/videos")
def api_videos():
    return jsonify(scan_videos())

@app.route("/api/approve", methods=["POST"])
def api_approve():
    data = request.json or {}
    post_id = data.get("post_id")
    platforms = data.get("platforms", [])
    caption = data.get("caption", "")
    if not post_id:
        return jsonify({"error": "post_id required"}), 400

    approved = load_approved()
    # Remove existing entry for this post if re-approving
    approved = [a for a in approved if a["post_id"] != post_id]
    approved.append({
        "post_id":    post_id,
        "platforms":  platforms,
        "caption":    caption,
        "approved_at": datetime.utcnow().isoformat(),
    })
    save_approved(approved)
    logger.info(f"[vega.theater] Approved {post_id} for {platforms}")
    return jsonify({"status": "approved", "post_id": post_id})

@app.route("/api/skip", methods=["POST"])
def api_skip():
    data = request.json or {}
    post_id = data.get("post_id")
    if not post_id:
        return jsonify({"error": "post_id required"}), 400
    posts = load_posts()
    for p in posts:
        if p.get("id") == post_id or p.get("file_path", "").endswith(post_id):
            p["status"] = "skipped"
    save_posts(posts)
    return jsonify({"status": "skipped"})

@app.route("/video/<filename>")
def serve_video(filename):
    return send_from_directory(VIDEO_DIR, filename, mimetype="video/mp4")

@app.route("/")
def theater():
    return THEATER_HTML

@app.route("/api/queue")
def api_queue():
    return jsonify(load_approved())


# ── Theater HTML ───────────────────────────────────────────────────────────────

THEATER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>vega Theater — The Christman AI Project</title>
<style>
  :root {
    --bg:     #04040d;
    --panel:  #0a0a1a;
    --border: #1a1a3a;
    --blue:   #00d4ff;
    --gold:   #ffd700;
    --green:  #00ff88;
    --red:    #ff3355;
    --purple: #b06aff;
    --text:   #e0e0ff;
    --muted:  #4a4a7a;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Courier New', monospace;
    min-height: 100vh;
  }
  body::before {
    content:'';
    position:fixed; inset:0;
    background-image:
      linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events:none; z-index:0;
  }
  .wrap { position:relative; z-index:1; max-width:1400px; margin:0 auto; padding:24px; }

  header {
    text-align:center; padding:24px 0 16px;
    border-bottom:1px solid var(--border); margin-bottom:28px;
  }
  header h1 { font-size:2rem; color:var(--blue); letter-spacing:4px; text-transform:uppercase; }
  header p  { color:var(--muted); font-size:0.8rem; margin-top:6px; }

  .stats {
    display:flex; gap:16px; margin-bottom:28px; flex-wrap:wrap;
  }
  .stat {
    background:var(--panel); border:1px solid var(--border);
    padding:12px 20px; flex:1; min-width:140px; text-align:center;
  }
  .stat .val { font-size:1.8rem; font-weight:bold; }
  .stat .lbl { font-size:0.7rem; color:var(--muted); margin-top:4px; }
  .stat.blue .val  { color:var(--blue); }
  .stat.green .val { color:var(--green); }
  .stat.gold .val  { color:var(--gold); }
  .stat.red .val   { color:var(--red); }

  .grid {
    display:grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap:20px;
  }
  .card {
    background:var(--panel); border:1px solid var(--border);
    overflow:hidden; transition:border-color 0.2s;
  }
  .card:hover { border-color:var(--blue); }
  .card.approved { border-color:var(--green); }
  .card.skipped  { opacity:0.4; }

  .card video { width:100%; display:block; max-height:220px; object-fit:cover; background:#000; }

  .card-body { padding:14px; }
  .card-meta { font-size:0.7rem; color:var(--muted); margin-bottom:8px; display:flex; gap:8px; flex-wrap:wrap; }
  .badge {
    padding:2px 8px; font-size:0.65rem; text-transform:uppercase; letter-spacing:1px;
  }
  .badge.instagram { background:#833ab4; color:#fff; }
  .badge.tiktok    { background:#010101; color:#fff; border:1px solid #69c9d0; }
  .badge.linkedin  { background:#0077b5; color:#fff; }
  .badge.facebook  { background:#1877f2; color:#fff; }
  .badge.x         { background:#111; color:#fff; border:1px solid #555; }
  .badge.clapper   { background:#e8001c; color:#fff; }
  .badge.unknown   { background:var(--border); color:var(--muted); }
  .badge.approved-badge { background:var(--green); color:#000; }

  .prompt {
    font-size:0.78rem; color:var(--text); line-height:1.5;
    margin-bottom:10px; min-height:40px;
  }

  .caption-input {
    width:100%; background:var(--bg); border:1px solid var(--border);
    color:var(--text); font-family:inherit; font-size:0.75rem;
    padding:8px; margin-bottom:10px; resize:vertical; min-height:60px;
  }
  .caption-input:focus { outline:none; border-color:var(--blue); }

  .platform-pick { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px; }
  .platform-btn {
    padding:4px 10px; font-size:0.65rem; text-transform:uppercase;
    letter-spacing:1px; cursor:pointer; border:1px solid var(--border);
    background:transparent; color:var(--muted); font-family:inherit;
    transition:all 0.15s;
  }
  .platform-btn.selected { border-color:var(--blue); color:var(--blue); }

  .actions { display:flex; gap:8px; }
  .btn {
    flex:1; padding:8px; font-size:0.72rem; text-transform:uppercase;
    letter-spacing:2px; cursor:pointer; font-family:inherit; border:none;
    transition:opacity 0.15s;
  }
  .btn:hover { opacity:0.8; }
  .btn-approve { background:var(--green); color:#000; }
  .btn-skip    { background:var(--border); color:var(--muted); }

  .empty { text-align:center; padding:80px; color:var(--muted); }
  .refresh-btn {
    position:fixed; bottom:24px; right:24px;
    background:var(--blue); color:#000; border:none;
    padding:12px 20px; font-family:inherit; font-size:0.75rem;
    text-transform:uppercase; letter-spacing:2px; cursor:pointer;
    z-index:10;
  }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>⭐ vega Theater</h1>
    <p>The Christman AI Project — Review &amp; Approve Content Before Posting</p>
  </header>

  <div class="stats">
    <div class="stat blue">  <div class="val" id="stat-total">—</div><div class="lbl">Total Videos</div></div>
    <div class="stat green"> <div class="val" id="stat-approved">—</div><div class="lbl">Approved</div></div>
    <div class="stat gold">  <div class="val" id="stat-ready">—</div><div class="lbl">Ready to Review</div></div>
    <div class="stat red">   <div class="val" id="stat-skipped">—</div><div class="lbl">Skipped</div></div>
  </div>

  <div class="grid" id="grid">
    <div class="empty">Loading vega content...</div>
  </div>
</div>

<button class="refresh-btn" onclick="load()">↻ Refresh</button>

<script>
const PLATFORMS = ['instagram','tiktok','linkedin','facebook','x','clapper'];

async function load() {
  const res = await fetch('/api/videos');
  const videos = await res.json();

  const total    = videos.length;
  const approved = videos.filter(v => v.approved).length;
  const skipped  = videos.filter(v => v.status === 'skipped').length;
  const ready    = total - approved - skipped;

  document.getElementById('stat-total').textContent    = total;
  document.getElementById('stat-approved').textContent = approved;
  document.getElementById('stat-ready').textContent    = ready;
  document.getElementById('stat-skipped').textContent  = skipped;

  const grid = document.getElementById('grid');
  if (!videos.length) {
    grid.innerHTML = '<div class="empty">No videos yet — vega is working on it.</div>';
    return;
  }

  grid.innerHTML = videos.map(v => `
    <div class="card ${v.approved ? 'approved' : ''} ${v.status === 'skipped' ? 'skipped' : ''}" id="card-${v.post_id}">
      <video src="/video/${v.filename}" controls preload="metadata"></video>
      <div class="card-body">
        <div class="card-meta">
          <span class="badge ${v.platform}">${v.platform}</span>
          ${v.approved ? '<span class="badge approved-badge">✅ Approved</span>' : ''}
          <span style="margin-left:auto;color:var(--muted)">${v.created} · ${v.size_mb}MB</span>
        </div>
        <div class="prompt">${v.prompt || '(no prompt recorded)'}</div>
        <textarea class="caption-input" id="caption-${v.post_id}" placeholder="Write your caption here before approving...">${v.prompt || ''}</textarea>
        <div class="platform-pick" id="platforms-${v.post_id}">
          ${PLATFORMS.map(p => `
            <button class="platform-btn ${p === v.platform ? 'selected' : ''}"
              onclick="togglePlatform('${v.post_id}','${p}',this)">${p}</button>
          `).join('')}
        </div>
        <div class="actions">
          <button class="btn btn-approve" onclick="approve('${v.post_id}')">✅ Approve</button>
          <button class="btn btn-skip"    onclick="skip('${v.post_id}')">Skip</button>
        </div>
      </div>
    </div>
  `).join('');
}

function togglePlatform(postId, platform, btn) {
  btn.classList.toggle('selected');
}

function getSelectedPlatforms(postId) {
  const btns = document.querySelectorAll(`#platforms-${postId} .platform-btn.selected`);
  return Array.from(btns).map(b => b.textContent.trim());
}

async function approve(postId) {
  const platforms = getSelectedPlatforms(postId);
  const caption   = document.getElementById('caption-' + postId).value;
  if (!platforms.length) {
    alert('Select at least one platform before approving.');
    return;
  }
  await fetch('/api/approve', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ post_id: postId, platforms, caption })
  });
  document.getElementById('card-' + postId).classList.add('approved');
  load();
}

async function skip(postId) {
  await fetch('/api/skip', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ post_id: postId })
  });
  document.getElementById('card-' + postId).classList.add('skipped');
  load();
}

load();
setInterval(load, 60000); // auto-refresh every minute
</script>
</body>
</html>
"""

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("[vega.theater] Starting at http://localhost:8888")
    print("[vega.theater] Open your browser to review and approve content.")
    app.run(host="0.0.0.0", port=8888, debug=False)
