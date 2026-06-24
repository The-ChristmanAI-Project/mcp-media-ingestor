"""
analytics/visualizer.py — Vega
Plotly-powered performance graphs. One chart per platform, one master view.

Produces:
  - Per-platform bar/line charts (views, likes, comments, shares)
  - Cross-platform comparison bar chart
  - Per-post trend line (time series of a single metric)
  - Master dashboard HTML embedding all charts

Rule 13: Charts are built only from real data passed in. No fake data points.
Rule 6:  If Plotly isn't installed, raises clearly. No silent empty charts.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.analytics.visualizer")

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "vega_output" / "analytics"

# Color palette per platform (brand-adjacent)
PLATFORM_COLORS = {
    "instagram": "#E1306C",
    "tiktok": "#010101",
    "youtube": "#FF0000",
    "facebook": "#1877F2",
    "linkedin": "#0A66C2",
    "x": "#1DA1F2",
}

DEFAULT_METRICS = ["views", "likes", "comments", "shares"]


def _require_plotly():
    try:
        import plotly.graph_objects as go
        import plotly.express as px
        return go, px
    except ImportError:
        raise ImportError(
            "[Vega.Visualizer] Plotly not installed. "
            "Run: pip install plotly  (Rule 1: it has to work)"
        )


def _ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


# ── Individual platform chart ─────────────────────────────────────────────────

def chart_platform(
    platform: str,
    rows: list[dict],
    metrics: Optional[list[str]] = None,
    output_filename: Optional[str] = None,
) -> dict:
    """
    Bar chart of metrics for a single platform.

    Args:
        platform: e.g. "instagram"
        rows: list of {post_id, platform, metric, value, fetched_at}
        metrics: which metrics to include (default: views/likes/comments/shares)
        output_filename: if set, saves as HTML file in vega_output/analytics/

    Returns:
        {"status": "ok", "html": <html_string>, "path": <optional file path>}
    """
    go, px = _require_plotly()

    metrics = metrics or DEFAULT_METRICS
    platform_rows = [r for r in rows if r.get("platform") == platform and r.get("metric") in metrics]

    if not platform_rows:
        return {
            "status": "no_data",
            "reason": f"No analytics data for {platform}. Collect data first.",
            "platform": platform,
        }

    # Pivot: post_id → metric → value
    posts = {}
    for row in platform_rows:
        pid = row["post_id"]
        posts.setdefault(pid, {})
        posts[pid][row["metric"]] = row["value"]

    post_ids = list(posts.keys())
    color = PLATFORM_COLORS.get(platform, "#888888")

    traces = []
    for metric in metrics:
        values = [posts[pid].get(metric, 0) for pid in post_ids]
        if any(v > 0 for v in values):
            traces.append(go.Bar(
                name=metric.capitalize(),
                x=post_ids,
                y=values,
                marker_color=color,
                opacity=0.85,
            ))

    if not traces:
        return {"status": "no_data", "reason": f"All metric values are zero for {platform}"}

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=f"Vega — {platform.capitalize()} Performance",
        xaxis_title="Post ID",
        yaxis_title="Count",
        barmode="group",
        plot_bgcolor="#0a0a0a",
        paper_bgcolor="#111111",
        font=dict(color="#ffffff"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    html = fig.to_html(full_html=True, include_plotlyjs="cdn")

    path = None
    if output_filename:
        out = _ensure_output_dir() / output_filename
        out.write_text(html, encoding="utf-8")
        path = str(out)
        logger.info(f"[Vega.Visualizer] Saved {platform} chart → {path}")

    return {"status": "ok", "platform": platform, "html": html, "path": path}


# ── Cross-platform comparison ─────────────────────────────────────────────────

def chart_cross_platform(
    rows: list[dict],
    metric: str = "views",
    output_filename: Optional[str] = None,
) -> dict:
    """
    Side-by-side bar chart comparing a single metric across all platforms.

    Returns the same structure as chart_platform.
    """
    go, px = _require_plotly()

    filtered = [r for r in rows if r.get("metric") == metric]
    if not filtered:
        return {
            "status": "no_data",
            "reason": f"No '{metric}' data across any platform.",
        }

    # Aggregate by platform: sum the metric
    by_platform: dict[str, int] = {}
    for row in filtered:
        p = row["platform"]
        by_platform[p] = by_platform.get(p, 0) + row["value"]

    platforms = list(by_platform.keys())
    values = [by_platform[p] for p in platforms]
    colors = [PLATFORM_COLORS.get(p, "#888888") for p in platforms]

    fig = go.Figure(data=[
        go.Bar(
            x=platforms,
            y=values,
            marker_color=colors,
            text=[f"{v:,}" for v in values],
            textposition="outside",
        )
    ])
    fig.update_layout(
        title=f"Vega — {metric.capitalize()} by Platform",
        xaxis_title="Platform",
        yaxis_title=metric.capitalize(),
        plot_bgcolor="#0a0a0a",
        paper_bgcolor="#111111",
        font=dict(color="#ffffff"),
    )

    html = fig.to_html(full_html=True, include_plotlyjs="cdn")
    path = None
    if output_filename:
        out = _ensure_output_dir() / output_filename
        out.write_text(html, encoding="utf-8")
        path = str(out)

    return {"status": "ok", "metric": metric, "html": html, "path": path}


# ── Per-post time series ──────────────────────────────────────────────────────

def chart_post_trend(
    post_id: str,
    platform: str,
    rows: list[dict],
    metric: str = "views",
    output_filename: Optional[str] = None,
) -> dict:
    """
    Line chart showing how a metric changes over time for one post.
    Requires multiple fetched_at snapshots in rows.
    """
    go, _ = _require_plotly()

    filtered = [
        r for r in rows
        if r.get("post_id") == post_id
        and r.get("platform") == platform
        and r.get("metric") == metric
        and r.get("fetched_at")
    ]

    if len(filtered) < 2:
        return {
            "status": "no_data",
            "reason": f"Need ≥2 snapshots for trend chart. Have {len(filtered)} for {post_id}/{platform}/{metric}.",
        }

    filtered.sort(key=lambda r: r["fetched_at"])
    x = [r["fetched_at"] for r in filtered]
    y = [r["value"] for r in filtered]

    color = PLATFORM_COLORS.get(platform, "#888888")

    fig = go.Figure(data=[
        go.Scatter(
            x=x, y=y, mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=8),
            name=f"{post_id} — {metric}",
        )
    ])
    fig.update_layout(
        title=f"Vega — {metric.capitalize()} Over Time | {platform.capitalize()} | {post_id}",
        xaxis_title="Snapshot Time",
        yaxis_title=metric.capitalize(),
        plot_bgcolor="#0a0a0a",
        paper_bgcolor="#111111",
        font=dict(color="#ffffff"),
    )

    html = fig.to_html(full_html=True, include_plotlyjs="cdn")
    path = None
    if output_filename:
        out = _ensure_output_dir() / output_filename
        out.write_text(html, encoding="utf-8")
        path = str(out)

    return {"status": "ok", "html": html, "path": path}


# ── Master dashboard ──────────────────────────────────────────────────────────

def build_master_dashboard(
    rows: list[dict],
    output_filename: str = "vega_dashboard.html",
) -> dict:
    """
    Produces a single HTML file embedding:
      - A cross-platform views comparison chart
      - One per-platform breakdown chart for each platform that has data

    Rule 13: Only shows charts for platforms that have real data.
    """
    go, _ = _require_plotly()

    if not rows:
        return {
            "status": "no_data",
            "reason": "No analytics rows to visualize. Collect data first.",
        }

    sections = []

    # Cross-platform views
    cross = chart_cross_platform(rows, metric="views")
    if cross.get("status") == "ok":
        # Extract just the inner div, not the full HTML page
        sections.append(f"<h2 style='color:#ccc;font-family:sans-serif'>Total Views by Platform</h2>")
        sections.append(_extract_plotly_div(cross["html"]))

    # Per-platform breakdowns
    seen_platforms = list(set(r["platform"] for r in rows))
    for platform in sorted(seen_platforms):
        result = chart_platform(platform, rows)
        if result.get("status") == "ok":
            sections.append(f"<h2 style='color:{PLATFORM_COLORS.get(platform, '#ccc')};font-family:sans-serif'>{platform.capitalize()} Performance</h2>")
            sections.append(_extract_plotly_div(result["html"]))

    if not sections:
        return {"status": "no_data", "reason": "All charts returned no data."}

    dashboard_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Vega Analytics Dashboard — Christman AI Project</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  body {{ background: #0a0a0a; color: #ffffff; font-family: sans-serif; padding: 2rem; }}
  h1 {{ color: #9b5cf6; border-bottom: 2px solid #9b5cf6; padding-bottom: 0.5rem; }}
  h2 {{ margin-top: 2rem; }}
  .vega-header {{ display:flex; align-items:center; gap:1rem; margin-bottom:2rem; }}
  .vega-tag {{ background:#9b5cf6; color:#fff; padding:0.25rem 0.75rem; border-radius:1rem; font-size:0.85rem; }}
</style>
</head>
<body>
<div class="vega-header">
  <h1>⭐ Vega Analytics Dashboard</h1>
  <span class="vega-tag">Christman AI Project</span>
</div>
<p style="color:#888">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Rule 13: All data is real.</p>
{''.join(sections)}
</body>
</html>"""

    out = _ensure_output_dir() / output_filename
    out.write_text(dashboard_html, encoding="utf-8")
    path = str(out)
    logger.info(f"[Vega.Visualizer] Master dashboard saved → {path}")

    return {"status": "ok", "path": path, "platforms_shown": seen_platforms}


def _extract_plotly_div(full_html: str) -> str:
    """
    Pull just the <div> plot block from a full plotly HTML page.
    This lets us embed multiple charts in one master HTML file.
    """
    import re
    match = re.search(r'(<div id="[^"]*".*?</div>)', full_html, re.DOTALL)
    return match.group(1) if match else ""
