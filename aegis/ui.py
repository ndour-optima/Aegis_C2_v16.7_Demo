from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from . import core
from .mission import export_audit_bundle, export_doctrine_bundle, export_replay_bundle, refresh_mission_layers


def _inject_ui_polish() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 0.55rem; padding-bottom: 0.25rem; max-width: 96rem;}
        h1 {margin-bottom: 0.25rem; font-size: 1.65rem;}
        h3 {margin-bottom: 0.35rem;}
        div[data-testid="stMetric"] {
            background: rgba(15, 23, 42, 0.028);
            border: 1px solid rgba(100, 116, 139, 0.14);
            border-radius: 10px;
            padding: 0.20rem 0.38rem;
            min-height: 60px;
            margin-bottom: 0.10rem;
        }
        div[data-testid="stMetricLabel"] p {font-size: 0.68rem; font-weight: 700;}
        div[data-testid="stMetricValue"] {font-size: 0.92rem; line-height: 1.05;}
        .aegis-status-card {
            border: 1px solid rgba(100, 116, 139, 0.18);
            border-radius: 12px;
            padding: 0.42rem 0.60rem;
            margin: 0.08rem 0 0.28rem 0;
            background: linear-gradient(180deg, rgba(248,250,252,0.98), rgba(241,245,249,0.98));
        }
        .aegis-status-row {display:flex; gap:0.40rem; align-items:center; flex-wrap:wrap; margin-top:0.12rem;}
        .aegis-badge {
            display:inline-block; padding:0.18rem 0.54rem; border-radius:999px;
            font-size:0.74rem; font-weight:800; letter-spacing:0.03em;
            border:1px solid transparent;
        }
        .aegis-green {background:#ecfdf5; color:#166534; border-color:#86efac;}
        .aegis-orange {background:#fff7ed; color:#9a3412; border-color:#fdba74;}
        .aegis-red {background:#fef2f2; color:#991b1b; border-color:#fca5a5;}
        .aegis-blue {background:#eff6ff; color:#1d4ed8; border-color:#93c5fd;}
        .aegis-slate {background:#f8fafc; color:#334155; border-color:#cbd5e1;}
        .aegis-muted {color:#475569; font-size:0.77rem;}
        
        .aegis-ribbon {display:flex; gap:0.35rem; overflow-x:auto; padding:0.02rem 0 0.28rem 0; margin-top:0.03rem;}
        .aegis-top-priority {flex:1.35; min-width:330px; max-width:none;}
        .aegis-shadow-card {opacity:0.78; font-style:italic;}
        .aegis-history-card {min-width:180px; max-width:220px; opacity:0.92;}
        .aegis-alert-banner {border-radius:12px; padding:0.68rem 0.9rem; margin:0.10rem 0 0.35rem 0; border-left:6px solid #94a3b8; font-weight:800; letter-spacing:0.01em;}
        .aegis-alert-banner .sub {display:block; font-size:0.82rem; font-weight:600; margin-top:0.16rem; opacity:0.92;}
        .aegis-alert-critical {background:linear-gradient(90deg, rgba(127,29,29,0.12), rgba(254,242,242,0.98)); border-color:#dc2626; color:#7f1d1d;}
        .aegis-alert-warning {background:linear-gradient(90deg, rgba(245,158,11,0.15), rgba(255,247,237,0.98)); border-color:#f59e0b; color:#9a3412;}
        .aegis-alert-info {background:linear-gradient(90deg, rgba(37,99,235,0.10), rgba(239,246,255,0.98)); border-color:#2563eb; color:#1d4ed8;}

        .aegis-ribbon-item {
            min-width: 210px; max-width: 255px;
            border: 1px solid rgba(100,116,139,0.18);
            border-left: 4px solid #94a3b8;
            background: rgba(248,250,252,0.98);
            border-radius: 10px; padding: 0.30rem 0.44rem;
            box-shadow: 0 1px 2px rgba(15,23,42,0.04);
        }
        .aegis-ribbon-critical {border-left-color:#dc2626; background:#fef2f2;}
        .aegis-ribbon-warning {border-left-color:#f59e0b; background:#fff7ed;}
        .aegis-ribbon-info {border-left-color:#2563eb; background:#eff6ff;}
        .aegis-ribbon-title {font-size:0.66rem; font-weight:800; letter-spacing:0.03em; color:#0f172a;}
        .aegis-ribbon-text {font-size:0.75rem; color:#334155; line-height:1.18; margin-top:0.08rem;}
        .aegis-threat-board {border:1px solid rgba(100,116,139,0.16); border-radius:12px; background:linear-gradient(180deg, rgba(248,250,252,0.98), rgba(241,245,249,0.98)); padding:0.35rem 0.50rem; margin:0.12rem 0 0.25rem 0;}
        .aegis-threat-row {display:flex; gap:0.35rem; flex-wrap:wrap;}
        .aegis-threat-pill {padding:0.16rem 0.40rem; border-radius:999px; font-size:0.66rem; font-weight:800; border:1px solid rgba(100,116,139,0.16); background:#ffffff;}
        .aegis-threat-pill.critical {background:#fee2e2; color:#991b1b; border-color:#fca5a5;}
        .aegis-threat-pill.warning {background:#ffedd5; color:#9a3412; border-color:#fdba74;}
        .aegis-compact-band {display:flex; gap:0.40rem; flex-wrap:wrap; align-items:center; margin:0.10rem 0 0.22rem 0;}
        .aegis-chip {padding:0.18rem 0.44rem; border-radius:999px; font-size:0.68rem; font-weight:800; border:1px solid rgba(100,116,139,0.16); background:#ffffff; color:#0f172a;}
        .aegis-kpi-strip {display:flex; gap:0.40rem; flex-wrap:wrap; margin:0.05rem 0 0.22rem 0;}
        .aegis-kpi-chip {padding:0.16rem 0.44rem; border-radius:10px; background:rgba(15,23,42,0.03); border:1px solid rgba(100,116,139,0.12); font-size:0.70rem; color:#334155;}
        .aegis-kpi-chip b {color:#0f172a;}
        .aegis-dominance {
            border-left: 6px solid #94a3b8;
            border:1px solid rgba(100,116,139,0.18); border-radius:12px; padding:0.45rem 0.65rem;
            background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98));
            margin: 0.10rem 0 0.22rem 0;
        }
        .aegis-dominance-title {font-size:0.70rem; font-weight:800; letter-spacing:0.03em; color:#0f172a;}
        .aegis-dominance-main {font-size:1.08rem; font-weight:900; color:#0f172a; margin-top:0.16rem; line-height:1.15;}
        .aegis-dominance-sub {font-size:0.76rem; color:#334155; line-height:1.30; margin-top:0.14rem;}
        .aegis-dominance-grid {display:grid; grid-template-columns: 2.2fr 1.2fr; gap:0.55rem; align-items:start;}
        .aegis-mini-table {border:1px solid rgba(100,116,139,0.12); border-radius:10px; padding:0.30rem 0.40rem; background:#fff;}
        .aegis-mini-row {display:grid; grid-template-columns: 1fr 1fr 0.7fr 0.7fr 0.8fr; gap:0.28rem; font-size:0.70rem; padding:0.12rem 0; border-bottom:1px dashed rgba(148,163,184,0.24);} 
        .aegis-mini-row:last-child {border-bottom:none;}
        .aegis-mini-head {font-weight:800; color:#0f172a;}
        .aegis-state-strip {display:grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap:0.36rem; margin:0.08rem 0 0.16rem 0;}
        .aegis-state-card {border:1px solid rgba(100,116,139,0.16); border-radius:12px; padding:0.36rem 0.48rem; background:#fff;}
        .aegis-state-card.active {box-shadow:0 0 0 2px rgba(59,130,246,0.16) inset, 0 6px 18px rgba(15,23,42,0.06); transform:translateY(-1px);}
        .aegis-state-label {font-size:0.64rem; font-weight:900; letter-spacing:0.05em; color:#475569;}
        .aegis-state-main {font-size:0.86rem; font-weight:900; margin-top:0.10rem;}
        .aegis-state-sub {font-size:0.70rem; color:#475569; margin-top:0.10rem; line-height:1.18;}
        .aegis-flow-note {border:1px dashed rgba(100,116,139,0.24); border-radius:10px; padding:0.35rem 0.45rem; font-size:0.73rem; color:#334155; background:#fff; margin-bottom:0.18rem;}
        .aegis-queue-alert {border-radius:12px; padding:0.55rem 0.65rem; margin-bottom:0.22rem; font-size:0.85rem; font-weight:900; background:linear-gradient(90deg, rgba(239,68,68,0.12), rgba(255,247,237,0.98)); border-left:6px solid #dc2626; color:#7f1d1d;}
        .aegis-queue-card.focus {border:2px solid rgba(220,38,38,0.62); box-shadow:0 0 0 3px rgba(254,226,226,0.72), 0 8px 22px rgba(127,29,29,0.10);} 
        .aegis-queue-card.nextup {border:1.6px solid rgba(249,115,22,0.42);} 
        .aegis-queue-button-note {font-size:0.68rem; color:#475569; margin:-0.08rem 0 0.20rem 0;}
        div[data-testid="stButton"] > button[kind="primary"] {background:#166534; border-color:#166534; color:white; font-weight:800;}
        div[data-testid="stButton"] > button[kind="primary"]:hover {background:#14532d; border-color:#14532d; color:white;}

        .aegis-queue-card {border:1px solid rgba(100,116,139,0.16); border-radius:12px; padding:0.42rem 0.52rem; margin-bottom:0.28rem; background:#fff;}
        .aegis-queue-title {font-size:0.81rem; font-weight:900; color:#0f172a;}
        .aegis-queue-meta {font-size:0.72rem; color:#475569; margin-top:0.12rem; line-height:1.26;}
        .aegis-queue-priority {display:inline-block; padding:0.14rem 0.36rem; border-radius:999px; font-size:0.63rem; font-weight:900; margin-bottom:0.18rem;}
        .aegis-p1 {background:#fee2e2; color:#991b1b;}
        .aegis-p2 {background:#ffedd5; color:#9a3412;}
        .aegis-p3 {background:#eff6ff; color:#1d4ed8;}
        .aegis-side-summary {border:1px solid rgba(100,116,139,0.16); border-radius:12px; padding:0.45rem 0.55rem; background:linear-gradient(180deg, rgba(248,250,252,0.98), rgba(241,245,249,0.98)); margin-bottom:0.30rem;}
        .aegis-side-summary-title {font-size:0.70rem; font-weight:900; letter-spacing:0.04em; color:#475569;}
        .aegis-side-summary-main {font-size:0.92rem; font-weight:900; color:#0f172a; margin-top:0.14rem; line-height:1.2;}
        .aegis-side-summary-line {font-size:0.73rem; color:#334155; margin-top:0.10rem; line-height:1.25;}
        .aegis-map-note {font-size:0.71rem; color:#475569; margin:0.04rem 0 0.18rem 0;}
        [data-testid="stSidebar"] .block-container {padding-top:0.75rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _engine_health(world: dict) -> dict:
    load = float(world.get("cognitive_state", {}).get("score", 0.0))
    pending = len(_actionable_queue(world))
    if load >= 0.88 or pending >= 8:
        return {"label": "CRITICAL", "css": "aegis-red", "message": "High load – operator overload risk"}
    if load >= 0.72 or pending >= 4:
        return {"label": "DEGRADED", "css": "aegis-orange", "message": "High load – operator overload risk"}
    return {"label": "STABLE", "css": "aegis-green", "message": "Simulation advancing normally"}


def _kill_metric(world: dict) -> str:
    impacts = world.get("impact_markers", [])
    if not impacts:
        return "0%"
    hits = sum(1 for m in impacts if m.get("outcome") == "HIT")
    return f"{(100.0 * hits / max(1, len(impacts))):.0f}%"




def _automation_reasoning_trace(world: dict) -> list[str]:
    auth = world.get("authority_state", {})
    configured = auth.get("configured", world.get("configured_authority_mode", world.get("authority_mode", "Approval Required")))
    effective = auth.get("effective", world.get("authority_mode", configured))
    trace = [
        f"Configured authority: {configured}",
        f"Effective authority: {effective}",
        f"Authority source: {auth.get('source', 'Configured policy')}",
        auth.get("reason", "No runtime override active."),
    ]
    cs = world.get("cognitive_state", {})
    score = float(cs.get("score", 0.0))
    band = cs.get("band", "LOW")
    trace.append(f"Cognitive load {band} ({score:.2f}).")
    breakdown = cs.get("driver_breakdown", {})
    if breakdown:
        lead = sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True)[:2]
        if lead and lead[0][1] > 0:
            pretty = ", ".join(f"{k.replace('_', ' ')}={v:.2f}" for k, v in lead)
            trace.append(f"Primary load drivers: {pretty}.")
    pending = len(_actionable_queue(world))
    if pending:
        trace.append(f"Pending operator queue: {pending} recommendation(s).")
    missiles = len(world.get("missiles", []))
    if missiles:
        trace.append(f"Missiles in flight: {missiles}.")
    rs = world.get("resilience_state", {})
    if rs.get("degraded") or rs.get("fallback_active"):
        trace.append("Resilience mode active: degraded links or local fallback influencing control flow.")
    ads = world.get("adaptive_doctrine_state", {})
    if ads.get("active"):
        trace.append(f"Adaptive doctrine active: {ads.get('reason', 'constraint relaxation in effect.')}")
    summary = world.get("shadow_state", {}).get("last_summary", {})
    if summary.get("enabled"):
        diag = summary.get("diagnostic")
        if diag == "divergence" or summary.get("missed_by_active"):
            missed = ", ".join(summary.get("missed_by_active", [])[:3]) or "alternative priority set"
            trace.append(f"Shadow pressure: disagreement detected; AI highlights {missed} as live-path risk.")
        else:
            trace.append("Shadow pressure: live and advisory paths are aligned.")
    return trace


def _tactical_action_ribbon_df(world: dict) -> pd.DataFrame:
    entries = []
    for source_name, key in (("ACTION", "event_log"), ("AUTHORITY", "authority_log"), ("OVERRIDE", "override_log")):
        for item in world.get(key, []) or []:
            row = dict(item)
            row["source"] = source_name
            entries.append(row)
    # add reasoning-trace entries as synthetic timeline notes for current step
    auth = world.get("authority_state", {})
    for idx, note in enumerate(_automation_reasoning_trace(world), start=1):
        entries.append({
            "step": world.get("step", 0),
            "time": world.get("audit_state", {}).get("frames", [{}])[-1].get("time", "")[-8:] if world.get("audit_state", {}).get("frames") else "",
            "type": f"TRACE_{idx}",
            "text": note,
            "source": "TRACE",
        })
    if not entries:
        return pd.DataFrame(columns=["step", "time", "source", "type", "text"])
    df = pd.DataFrame(entries)
    # normalize time string for sort without expensive parsing
    def _sortkey(row):
        return (row.get("step", 0), str(row.get("time", "")), {"TRACE":3,"OVERRIDE":2,"AUTHORITY":1,"ACTION":0}.get(row.get("source","ACTION"),0))
    df["_sort"] = [ _sortkey(r) for _, r in df.iterrows() ]
    df = df.sort_values("_sort", ascending=False).drop(columns=["_sort"])
    cols=[c for c in ["step","time","source","type","text"] if c in df.columns]
    return df[cols]

def _top_threat_risks(world: dict, limit: int = 3) -> list[dict]:
    rows = []
    for t in core.alive_threats():
        crit = core.threat_criticality(t)
        rows.append({
            "threat_id": t.get("id"),
            "objective": t.get("target_objective"),
            "band": crit.get("band", "LOW"),
            "score": float(crit.get("score", 0.0)),
            "tti_steps": float(crit.get("tti_steps", 999.0)),
            "distance_km": float(crit.get("distance_to_objective", 999.0)),
        })
    rows.sort(key=lambda r: (-r["score"], r["tti_steps"], r["distance_km"]))
    return rows[:limit]


def _tension_alerts(world: dict) -> list[dict]:
    alerts = []
    top = _top_threat_risks(world, limit=2)
    if top:
        primary = top[0]
        sev = "critical" if primary.get("band") in ("HIGH", "CRITICAL") or primary.get("tti_steps", 999) <= 12 else "warning"
        alerts.append({
            "level": sev,
            "title": "CRITICAL THREAT" if sev == "critical" else "THREAT WATCH",
            "text": f"{primary['threat_id']} projected toward {primary['objective']} in ~{primary['tti_steps']:.1f} step(s). Immediate allocation review recommended.",
        })
    comp = world.get("shadow_state", {}).get("last_comparison", {})
    if comp.get("diagnostic") == "divergence":
        missed = ", ".join(comp.get("missed_by_active", [])[:2]) or "alternative targets"
        alerts.append({
            "level": "warning",
            "title": "SHADOW CHALLENGE",
            "text": f"AI advisory diverges from live path. Missed threat risk: {missed}. Consider re-evaluating target allocation before release.",
        })
    elif comp.get("diagnostic") == "aligned":
        alerts.append({
            "level": "info",
            "title": "SHADOW CONFIRMATION",
            "text": "AI advisory confirms the current engagement path and target prioritisation.",
        })
    auth = world.get("authority_state", {})
    esc = world.get("authority_escalation_state", {})
    if esc.get("active") and esc.get("last_text") and int(world.get("step", 0)) - int(esc.get("last_event_step", -999) or -999) <= 2:
        alerts.append({
            "level": "warning",
            "title": esc.get("last_title", "AUTHORITY ESCALATION"),
            "text": esc.get("last_text", ""),
        })
    elif auth.get("configured") != auth.get("effective"):
        alerts.append({
            "level": "info",
            "title": "AUTHORITY SHIFT",
            "text": f"Configured authority {auth.get('configured', 'n/a')} escalated to {auth.get('effective', 'n/a')} via {auth.get('source', 'runtime policy')}.",
        })
    return alerts[:3]


def _doctrine_shift_notice(world: dict) -> dict | None:
    ads = world.get("adaptive_doctrine_state", {})
    step = int(world.get("step", 0))
    shift_step = int(ads.get("last_shift_step", -999) or -999)
    if step - shift_step > 2:
        return None
    profile = str(ads.get("profile", "BASELINE") or "BASELINE")
    title = ads.get("last_shift_banner") or f"DOCTRINE SHIFT: {profile}"
    reason = ads.get("reason", "Adaptive doctrine updated for current pressure conditions.")
    level = "info"
    if profile in ("BREAKTHROUGH", "SURGE"):
        level = "warning"
    if profile == "AMMO_GUARD" or world.get("doctrine_name") == "Terminal Defense":
        level = "warning"
    return {"title": f"DOCTRINE SHIFT — {profile}", "text": f"{title}. {reason}", "level": level}


def _operator_consequence_notice(world: dict) -> dict | None:
    data = world.get("operator_consequence_state", {})
    step = int(world.get("step", 0))
    event_step = int(data.get("last_event_step", -999) or -999)
    if step - event_step > 2:
        return None
    if not data.get("last_text"):
        return None
    extra = []
    if float(data.get("risk_delta_pct", 0.0) or 0.0) > 0:
        extra.append(f"Risk +{float(data.get('risk_delta_pct',0.0)):.1f}%")
    if float(data.get("coverage_delta_pct", 0.0) or 0.0) > 0:
        extra.append(f"coverage -{float(data.get('coverage_delta_pct',0.0)):.1f}%")
    if float(data.get("expected_damage_delta_pct", 0.0) or 0.0) > 0:
        extra.append(f"expected damage +{float(data.get('expected_damage_delta_pct',0.0)):.1f}%")
    text = data.get("last_text", "")
    if extra:
        text += " " + " | ".join(extra)
    if data.get("counterfactual"):
        text += f" Counterfactual: {data.get('counterfactual')}"
    return {"title": data.get("last_title", "DELAY CONSEQUENCE"), "text": text, "level": data.get("severity", "warning")}


def _headline_ribbon_items(world: dict, limit: int = 5) -> list[dict]:
    items = []
    for special in (_doctrine_shift_notice(world), _operator_consequence_notice(world)):
        if special:
            items.append({"kind": special["level"], "title": special["title"], "text": special["text"]})
    for alert in _tension_alerts(world):
        items.append({"kind": alert["level"], "title": alert["title"], "text": alert["text"]})
    combined = []
    for source_name, key in (("ACTION", "event_log"), ("AUTHORITY", "authority_log"), ("OVERRIDE", "override_log")):
        for item in (world.get(key, []) or [])[-4:]:
            combined.append((item.get("step", 0), str(item.get("time", "")), source_name, item.get("type", ""), item.get("text", "")))
    combined.sort(reverse=True)
    for step, time_s, source, typ, msg in combined[: max(0, limit - len(items))]:
        level = "info"
        if typ in ("LEAK", "MISS", "CRITICAL_OVERRIDE") or "override" in typ.lower():
            level = "warning"
        if typ in ("KILL", "HIT"):
            level = "critical" if source == "ACTION" else "info"
        items.append({"kind": level, "title": f"{source} · STEP {step}", "text": msg})
    return items[:limit]


def _render_operational_tension(world: dict) -> None:
    for special in (_doctrine_shift_notice(world), _operator_consequence_notice(world)):
        if special:
            banner_css = {"critical": "aegis-alert-critical", "warning": "aegis-alert-warning", "info": "aegis-alert-info"}.get(special["level"], "aegis-alert-info")
            st.markdown(f'<div class="aegis-alert-banner {banner_css}">{special["title"]}<span class="sub">{special["text"]}</span></div>', unsafe_allow_html=True)
    alerts = _tension_alerts(world)
    if alerts:
        top = alerts[0]
        banner_css = {"critical": "aegis-alert-critical", "warning": "aegis-alert-warning", "info": "aegis-alert-info"}.get(top["level"], "aegis-alert-info")
        countdown = ""
        risks = _top_threat_risks(world, limit=1)
        if risks:
            countdown = f"<span class=\"sub\">Impact countdown: {str(risks[0]['objective']).upper()} in approximately {risks[0]['tti_steps']:.1f} step(s).</span>"
        st.markdown(f'<div class="aegis-alert-banner {banner_css}">{top["title"]} — {top["text"]}{countdown}</div>', unsafe_allow_html=True)
    ribbon = _headline_ribbon_items(world, limit=5)
    if ribbon:
        blocks = []
        for idx, item in enumerate(ribbon):
            css = {
                "critical": "aegis-ribbon-critical",
                "warning": "aegis-ribbon-warning",
                "info": "aegis-ribbon-info",
            }.get(item.get("kind", "info"), "aegis-ribbon-info")
            extra = []
            title = item.get("title", "UPDATE")
            if idx == 0:
                extra.append('aegis-top-priority')
            if "SHADOW" in title:
                extra.append('aegis-shadow-card')
            if title.startswith(("ACTION", "AUTHORITY", "OVERRIDE")):
                extra.append('aegis-history-card')
            extra_classes = " ".join(extra)
            item_text = item.get("text", "")
            blocks.append(
                f'<div class="aegis-ribbon-item {css} {extra_classes}"><div class="aegis-ribbon-title">{title}</div><div class="aegis-ribbon-text">{item_text}</div></div>'
            )
        st.markdown('<div class="aegis-ribbon">' + ''.join(blocks) + '</div>', unsafe_allow_html=True)

def _step_once(world: dict, delta: int) -> None:
    lock_key = "aegis_step_action_lock"
    if st.session_state.get(lock_key, False):
        return
    st.session_state[lock_key] = True
    try:
        core.step_world(delta)
        refresh_mission_layers(world, source="step")
        st.session_state["aegis_last_step_delta"] = delta
    finally:
        st.session_state[lock_key] = False


def _step_and_rerun(world: dict, delta: int) -> None:
    _step_once(world, delta)
    st.rerun()






def _actionable_queue(world: dict) -> list[dict]:
    return [r for r in world.get("pending_recommendations", []) if r.get("status") in ("PENDING_APPROVAL", "SUGGESTED")]

def _system_posture(world: dict) -> dict:
    rs = world.get("resilience_state", {})
    auth = world.get("authority_state", {})
    effective = auth.get("effective", world.get("authority_mode", "Approval Required"))
    pending = _actionable_queue(world)
    escalated = [r for r in pending if int(r.get("escalation_level", 0) or 0) > 0]
    if rs.get("fallback_active") or rs.get("degraded") or world.get("resilience_config", {}).get("comms_mode") != "Nominal":
        return {"state": "DEGRADED", "css": "aegis-orange", "reason": "Resilience constraints or degraded communications are active."}
    if escalated:
        op = world.get("authority_state", {}).get("effective_operator", world.get("authority_config", {}).get("operator_name", "operator_1"))
        return {"state": "ESCALATED", "css": "aegis-blue", "reason": f"Pending engagement forwarded to higher authority ({op})."}
    if pending:
        return {"state": "HOLD", "css": "aegis-red", "reason": f"{len(pending)} recommendation(s) waiting for operator action."}
    if effective in ("Auto If High Confidence", "Emergency Auto-Fire"):
        return {"state": "AUTO", "css": "aegis-blue", "reason": f"System may execute under {effective}."}
    return {"state": "READY", "css": "aegis-green", "reason": "No blocking approvals; system ready for next step."}


def _queue_priority_rank(rec: dict) -> tuple:
    tti = float(rec.get("tti_steps", 999.0) or 999.0)
    conf = float(rec.get("confidence", 0.0) or 0.0)
    status = rec.get("status", "")
    manual_penalty = 0 if status in ("PENDING_APPROVAL", "SUGGESTED") else 1
    return (manual_penalty, tti, -conf)


def _queue_priority_label(rec: dict, idx: int) -> tuple[str, str]:
    tti = float(rec.get("tti_steps", 999.0) or 999.0)
    if idx == 0 or tti <= 8:
        return ("P1 IMMEDIATE", "aegis-p1")
    if idx == 1 or tti <= 14:
        return ("P2 NEXT", "aegis-p2")
    return ("P3 WATCH", "aegis-p3")


def _render_system_state_strip(world: dict) -> None:
    posture = _system_posture(world)
    cards = []
    card_defs = [
        ("READY", "System can advance"),
        ("HOLD", "Operator must decide"),
        ("ESCALATED", "Higher authority reviewing"),
        ("AUTO", "Autonomous release enabled"),
        ("DEGRADED", "Fallback or comms issue"),
    ]
    for name, sub in card_defs:
        css = "aegis-slate"
        if name == "READY":
            css = "aegis-green"
        elif name == "HOLD":
            css = "aegis-red"
        elif name == "ESCALATED":
            css = "aegis-blue"
        elif name == "AUTO":
            css = "aegis-blue"
        elif name == "DEGRADED":
            css = "aegis-orange"
        active = " active" if posture["state"] == name else ""
        cards.append(
            f'<div class="aegis-state-card{active}"><div class="aegis-state-label">SYSTEM POSTURE</div><div class="aegis-state-main"><span class="aegis-badge {css}">{name}</span></div><div class="aegis-state-sub">{sub}</div></div>'
        )
    st.markdown('<div class="aegis-state-strip">' + ''.join(cards) + '</div>', unsafe_allow_html=True)


def _render_operator_queue_panel(world: dict, show_dataframe: bool = True) -> None:
    actionable = list(_actionable_queue(world))
    actionable = sorted(actionable, key=_queue_priority_rank)
    if not actionable:
        st.success("Queue clear. No pending operator actions.")
        return
    st.markdown('<div class="aegis-queue-alert">⚠ OPERATOR DECISION REQUIRED</div>', unsafe_allow_html=True)
    st.markdown('<div class="aegis-flow-note"><b>Operator flow:</b> review the highlighted P1 card first, approve or reject, then advance the scenario.</div>', unsafe_allow_html=True)
    for idx, rec in enumerate(actionable[:4]):
        tag, css = _queue_priority_label(rec, idx)
        asset = rec.get("asset_id", "?")
        target = rec.get("target_id", "?")
        obj = rec.get("objective_label", "?")
        tti = float(rec.get("tti_steps", 0.0) or 0.0)
        conf = float(rec.get("confidence", 0.0) or 0.0)
        status = str(rec.get("status", "")).replace("_", " ")
        rec_id = rec.get("rec_id", "")
        basis = rec.get("authority_basis", "")
        card_class = ' focus' if idx == 0 else (' nextup' if idx == 1 else '')
        operator = rec.get("effective_operator", world.get("authority_state", {}).get("effective_operator", world.get("authority_config", {}).get("operator_name", "operator_1")))
        st.markdown(f'<div class="aegis-queue-card{card_class}"><div class="aegis-queue-priority {css}">{tag}</div><div class="aegis-queue-title">{asset} → {target}</div><div class="aegis-queue-meta">Objective: <b>{obj}</b><br>TTI: <b>{tti:.1f}</b> · Confidence: <b>{conf:.2f}</b> · Status: <b>{status}</b><br>Basis: <b>{basis or "mission policy"}</b><br>Authority: <b>{operator}</b></div></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("Approve", key=f"approve::{rec_id}", use_container_width=True, type="primary"):
            core.approve_recommendation(rec_id)
            st.rerun()
        if c2.button("Reject", key=f"reject::{rec_id}", use_container_width=True):
            core.reject_recommendation(rec_id)
            st.rerun()
        st.markdown('<div class="aegis-queue-button-note">Approve commits release authority. Reject removes this recommendation from the immediate queue.</div>', unsafe_allow_html=True)
    if show_dataframe:
        pending = core.pending_df()
        if not pending.empty:
            preferred = [c for c in ["asset_id", "target_id", "objective_label", "tti_steps", "confidence", "status"] if c in pending.columns]
            st.caption("Full queue")
            st.dataframe(pending[preferred], use_container_width=True, hide_index=True, height=180)

def _render_side_mission_summary(world: dict) -> None:
    posture = _system_posture(world)
    risks = _top_threat_risks(world, limit=1)
    top = risks[0] if risks else None
    auth = world.get("authority_state", {})
    integrity = world.get("coverage_state", {}).get("integrity_pct", 100)
    pending = len(_actionable_queue(world))
    threats = len(core.alive_threats())
    missiles = len(world.get("missiles", []))
    danger = "No immediate threat window identified."
    if top:
        danger = f"TOP THREAT: {top['threat_id']} toward {str(top['objective']).upper()} · TTI {top['tti_steps']:.1f}"
    html = '<div class="aegis-side-summary">'
    html += '<div class="aegis-side-summary-title">DEMO SUMMARY</div>'
    html += f'<div class="aegis-side-summary-main">STATUS: {posture["state"]} | COVERAGE: {integrity}% | THREATS: {threats} | PENDING: {pending}</div>'
    html += f'<div class="aegis-side-summary-line"><b>{danger}</b></div>'
    ads = world.get("adaptive_doctrine_state", {})
    adapt = "Adaptive doctrine: baseline"
    if ads.get("active"):
        adapt = f"Adaptive doctrine: {ads.get('profile', 'ACTIVE')} · pressure {float(ads.get('last_pressure_score', 0.0)):.2f}"
        breakdown = ads.get("pressure_breakdown", {}) or {}
        top_parts = [f"{k.replace('_', ' ')} {float(v):.2f}" for k, v in sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True) if float(v) > 0][:3]
        if top_parts:
            adapt += " | " + ", ".join(top_parts)
    html += f'<div class="aegis-side-summary-line">Authority: {auth.get("effective", world.get("authority_mode", "n/a"))} · Operator: {auth.get("effective_operator", world.get("authority_config", {}).get("operator_name", "operator_1"))} | Missiles in flight: {missiles}</div>'
    html += f'<div class="aegis-side-summary-line">{adapt}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def render_sidebar(world: dict, reset_state_cb) -> None:
    st.sidebar.title("Mission Control")
    st.sidebar.caption("Demo-hardened controls. Core engine and approval logic remain unchanged.")

    quick1, quick2 = st.sidebar.columns(2)
    if quick1.button("Step +1", use_container_width=True):
        _step_and_rerun(world, 1)
    if quick2.button("Step +5", use_container_width=True):
        _step_and_rerun(world, 5)
    quick3, quick4 = st.sidebar.columns(2)
    if quick3.button("Reset", use_container_width=True):
        reset_state_cb()
    if quick4.button("Audit Export", use_container_width=True):
        refresh_mission_layers(world, source="audit_export")
        st.sidebar.success(f"Saved: {export_audit_bundle(world)}")

    with st.sidebar.expander("Primary controls", expanded=True):
        world["doctrine_name"] = st.selectbox(
            "Doctrine mode",
            list(core.DOCTRINES.keys()),
            help="Defines engagement philosophy. It shapes prioritisation, engagement timing, and how aggressively the system allocates scarce effectors.",
            index=list(core.DOCTRINES.keys()).index(world["doctrine_name"]),
        )
        authority_options = list(core.AUTHORITY_MODES.keys())
        configured_authority = world.get("configured_authority_mode", world.get("authority_mode", authority_options[0]))
        selected_authority = st.selectbox(
            "Authority mode",
            authority_options,
            help="Sets the balance between human approval and automated execution. Higher autonomy reduces response latency but relies more heavily on system confidence.",
            index=authority_options.index(configured_authority if configured_authority in authority_options else world.get("authority_mode", authority_options[0])),
        )
        world["configured_authority_mode"] = selected_authority
        world["authority_mode"] = selected_authority
        world["authority_config"]["operator_name"] = st.text_input(
            "Operator name",
            value=world["authority_config"].get("operator_name", "operator_1"),
        )

    with st.sidebar.expander("Authority and resilience", expanded=False):
        world["authority_config"]["auto_conf_threshold"] = st.slider(
            "Auto approval confidence", 0.50, 0.99, float(world["authority_config"].get("auto_conf_threshold", 0.82)), 0.01,
        )
        world["authority_config"]["emergency_distance_km"] = st.slider(
            "Emergency distance to objective (km)", 0.5, 5.0, float(world["authority_config"].get("emergency_distance_km", 2.5)), 0.1,
        )
        world["authority_config"]["veto_window_steps"] = st.slider(
            "Veto window (steps)", 1, 5, int(world["authority_config"].get("veto_window_steps", 2)), 1,
        )
        chain_default = world["authority_config"].get("escalation_chain", [world["authority_config"].get("operator_name", "operator_1"), "operator_2", "operator_3"])
        chain_str = ", ".join(chain_default if isinstance(chain_default, list) else [str(chain_default)])
        chain_input = st.text_input("Authority chain", value=chain_str, help="Comma-separated chain of command for timeout escalation.")
        world["authority_config"]["escalation_chain"] = [x.strip() for x in chain_input.split(",") if x.strip()]
        world["authority_config"]["escalation_tti_steps"] = st.slider("Escalate if TTI below", 4, 16, int(float(world["authority_config"].get("escalation_tti_steps", 10.0))), 1)
        world["authority_config"]["auto_release_after_chain_exhausted"] = st.checkbox("Auto-release if chain exhausted", value=bool(world["authority_config"].get("auto_release_after_chain_exhausted", True)))
        world["resilience_config"]["comms_mode"] = st.selectbox(
            "Communications posture",
            ["Nominal", "Remote degraded", "Remote lost"],
            index=["Nominal", "Remote degraded", "Remote lost"].index(world["resilience_config"].get("comms_mode", "Nominal")),
        )
        world["resilience_config"]["remote_link_quality"] = st.slider(
            "Remote link quality", 0.0, 1.0, float(world["resilience_config"].get("remote_link_quality", 1.0)), 0.01,
        )
        world["resilience_config"]["sensor_fusion_quality"] = st.slider(
            "Sensor fusion quality", 0.0, 1.0, float(world["resilience_config"].get("sensor_fusion_quality", 1.0)), 0.01,
        )
        world["resilience_config"]["gps_quality"] = st.slider(
            "Navigation / GPS quality", 0.0, 1.0, float(world["resilience_config"].get("gps_quality", 1.0)), 0.01,
        )
        world["resilience_config"]["local_fallback_enabled"] = st.checkbox(
            "Enable local fallback cell", value=bool(world["resilience_config"].get("local_fallback_enabled", True))
        )

    with st.sidebar.expander("Adaptive doctrine", expanded=False):
        world["adaptive_doctrine_config"]["enabled"] = st.checkbox(
            "Enable adaptive doctrine engine", value=bool(world["adaptive_doctrine_config"].get("enabled", True))
        )
        world["adaptive_doctrine_config"]["queue_pressure_threshold"] = st.slider(
            "Queue pressure trigger", 1, 5, int(world["adaptive_doctrine_config"].get("queue_pressure_threshold", 2)), 1
        )
        world["adaptive_doctrine_config"]["high_threat_tti_steps"] = st.slider(
            "High-threat TTI trigger", 6, 20, int(world["adaptive_doctrine_config"].get("high_threat_tti_steps", 12)), 1
        )
        world["adaptive_doctrine_config"]["swarm_surge_threshold"] = st.slider(
            "Swarm surge trigger", 2, 8, int(world["adaptive_doctrine_config"].get("swarm_surge_threshold", 4)), 1
        )
        world["adaptive_doctrine_config"]["ammo_guard_threshold"] = st.slider(
            "Ammo guard threshold", 1, 6, int(world["adaptive_doctrine_config"].get("ammo_guard_threshold", 3)), 1
        )
        ads = world.get("adaptive_doctrine_state", {})
        st.caption(f"Profile: {ads.get('profile', 'BASELINE')} | Active: {ads.get('active', False)} | Pressure: {float(ads.get('last_pressure_score', 0.0)):.2f}")
        breakdown = ads.get("pressure_breakdown", {}) or {}
        if breakdown:
            st.caption("Pressure drivers: " + ", ".join(f"{k.replace('_', ' ')}={float(v):.2f}" for k, v in sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True) if float(v) > 0))
        if ads.get("reason"):
            st.caption(ads.get("reason"))

    with st.sidebar.expander("Integration and scenario", expanded=False):
        if st.button("Replay Export", use_container_width=True):
            refresh_mission_layers(world, source="replay_export")
            st.success(f"Saved: {export_replay_bundle(world)}")
        if st.button("Doctrine Export JSON", use_container_width=True):
            refresh_mission_layers(world, source="doctrine_export")
            st.success(f"Saved: {export_doctrine_bundle(world)}")
        world["integration_config"]["mode"] = st.selectbox(
            "Integration mode",
            ["LOCAL_ONLY", "HYBRID", "AIR_GAPPED_REVIEW"],
            index=["LOCAL_ONLY", "HYBRID", "AIR_GAPPED_REVIEW"].index(world["integration_config"].get("mode", "LOCAL_ONLY")),
        )
        adapter_options = ["mirror_live_tracks", "demo_radar_feed", "coalition_demo_feed"]
        world["integration_config"]["active_adapters"] = st.multiselect(
            "Active feed adapters",
            adapter_options,
            default=world["integration_config"].get("active_adapters", ["mirror_live_tracks", "demo_radar_feed"]),
        )
        world["integration_config"]["merge_validated_tracks"] = st.checkbox(
            "Mark validated tracks merge-ready", value=bool(world["integration_config"].get("merge_validated_tracks", False))
        )
        world["integration_config"]["accept_unverified"] = st.checkbox(
            "Allow unverified feeds", value=bool(world["integration_config"].get("accept_unverified", False))
        )
        world["integration_config"]["protocol"] = st.selectbox(
            "Protocol", ["Internal", "STANAG 5516 / Link-16"],
            index=["Internal", "STANAG 5516 / Link-16"].index(world["integration_config"].get("protocol", "Internal"))
        )
        world["adversarial_config"]["enabled"] = st.checkbox(
            "Enable adversarial battlefield", value=bool(world["adversarial_config"].get("enabled", True))
        )
        world["adversarial_config"]["maneuver_intensity"] = st.slider(
            "Threat maneuver intensity", 0.0, 0.50, float(world["adversarial_config"].get("maneuver_intensity", 0.22)), 0.01,
        )
        world["adversarial_config"]["sensor_noise_km"] = st.slider(
            "Sensor uncertainty radius (km)", 0.0, 0.60, float(world["adversarial_config"].get("sensor_noise_km", 0.20)), 0.01,
        )
        world["adversarial_config"]["deception_probability"] = st.slider(
            "Deception probability", 0.0, 0.50, float(world["adversarial_config"].get("deception_probability", 0.18)), 0.01,
        )
        world["adversarial_config"]["terrain_mask_probability"] = st.slider(
            "Terrain mask probability", 0.0, 0.40, float(world["adversarial_config"].get("terrain_mask_probability", 0.12)), 0.01,
        )


def _render_header(world: dict) -> None:
    _inject_ui_polish()
    st.title(world["meta"]["title"])
    rs = world.get("resilience_state", {})
    cs = world.get("cognitive_state", {})
    eff_operator = world["authority_config"].get(
        "effective_operator_name", world["authority_config"].get("operator_name", "operator_1")
    )
    posture = _system_posture(world)
    if rs.get("fallback_active"):
        st.warning(
            f"Local fallback active. Effective control: {eff_operator}. Remote comms posture: {world['resilience_config']['comms_mode']}."
        )
    elif rs.get("degraded"):
        st.info(f"Degraded environment detected. Effective control: {eff_operator}. Cognitive band: {cs.get('band', 'LOW')}.")

    health = _engine_health(world)
    status_col, detail_col = st.columns([1.0, 4.0])
    with status_col:
        st.markdown(
            f"""
            <div class="aegis-status-card">
                <div class="aegis-muted"><strong>ENGINE HEALTH</strong></div>
                <div class="aegis-status-row">
                    <span class="aegis-badge {health['css']}">{health['label']}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with detail_col:
        st.markdown(
            f"""
            <div class="aegis-status-card">
                <div class="aegis-muted"><strong>FMV DEMO VIEW</strong></div>
                <div style="font-weight:800; margin-top:0.18rem;">{posture['state']} · {health['message']}</div>
                <div class="aegis-status-row aegis-muted">
                    <span>Operator: <strong>{eff_operator}</strong></span>
                    <span>Band: <strong>{cs.get('band', 'LOW')}</strong></span>
                    <span>Pending queue: <strong>{len(_actionable_queue(world))}</strong></span>
                    <span>Authority: <strong>{world.get('authority_state', {}).get('effective', world.get('authority_mode', 'Configured'))}</strong></span>
                </div>
                <div class="aegis-muted" style="margin-top:0.28rem; line-height:1.28;">{posture['reason']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    _render_system_state_strip(world)
    _render_operational_tension(world)

    comparison = world.get("shadow_state", {}).get("last_comparison", {})
    diagnostic = comparison.get("diagnostic", "aligned")
    if diagnostic == "aligned":
        decision_indicator = "HIGH"
    elif diagnostic in ("divergence", "shadow_conservative_gap"):
        decision_indicator = "MEDIUM"
    else:
        decision_indicator = "GAP"
    pending = len(_actionable_queue(world))
    missiles_in_flight = len(world.get("missiles", []))
    if pending > 0:
        tempo_indicator = "QUEUE"
    elif missiles_in_flight > 0:
        tempo_indicator = "TRACKING"
    else:
        tempo_indicator = "CLEAR"

    compact_line_one = [
        '<span class="aegis-chip">Step <b>{}</b></span>'.format(world.get("step", 0)),
        '<span class="aegis-chip">Threats <b>{}</b> / Destroyed <b>{}</b></span>'.format(len(core.alive_threats()), world.get("destroyed_count", 0)),
        '<span class="aegis-chip">Pending <b>{}</b></span>'.format(pending),
        '<span class="aegis-chip">Coverage <b>{}%</b></span>'.format(world.get("coverage_state", {}).get("integrity_pct", 100)),
    ]
    compact_line_two = [
        '<span class="aegis-kpi-chip">State <b>{}</b></span>'.format(posture.get("state", "READY")),
        '<span class="aegis-kpi-chip">Load <b>{:.2f}</b></span>'.format(cs.get("score", 0.0)),
        '<span class="aegis-kpi-chip">Kill <b>{}</b></span>'.format(_kill_metric(world)),
        '<span class="aegis-kpi-chip">Confidence <b>{}</b></span>'.format(decision_indicator),
        '<span class="aegis-kpi-chip">Tempo <b>{}</b></span>'.format(tempo_indicator),
    ]
    st.markdown('<div class="aegis-compact-band">' + ''.join(compact_line_one) + '</div>', unsafe_allow_html=True)
    st.markdown('<div class="aegis-kpi-strip">' + ''.join(compact_line_two) + '</div>', unsafe_allow_html=True)


def _operator_dominance_payload(world: dict) -> dict:
    pending = list(world.get("pending_recommendations", []))
    auth = world.get("authority_state", {})
    comp = world.get("shadow_state", {}).get("last_comparison", {})
    top = _top_threat_risks(world, limit=2)
    critical = top[0] if top else None
    action_required = "YES" if pending or comp.get("diagnostic") == "divergence" else "NO"
    lines = []
    if critical:
        lines.append(f"{critical['threat_id']} → {str(critical['objective']).upper()} IMPACT IN {critical['tti_steps']:.1f}")
    if len(top) > 1:
        second = top[1]
        lines.append(f"{second['threat_id']} → {str(second['objective']).upper()} IMPACT IN {second['tti_steps']:.1f}")
    headline = "CRITICAL WINDOW" if critical and critical.get('tti_steps', 999) <= 12 else "ACTION WINDOW"
    summary = f"Operator action required: {action_required}"
    if comp.get('diagnostic') == 'divergence':
        missed = ', '.join(comp.get('missed_by_active', [])[:2]) or 'alternative target set'
        summary += f" · Shadow warns on {missed}"
    summary += f" · Authority {auth.get('effective', world.get('authority_mode', 'n/a'))}"
    return {'headline': headline, 'lines': lines, 'summary': summary, 'pending': pending, 'critical': critical}


def _render_operator_dominance(world: dict) -> None:
    payload = _operator_dominance_payload(world)
    pending = payload['pending'][:2]
    lines = payload['lines'] or ["No immediate threat window identified."]
    critical = payload.get("critical")
    border = "#dc2626" if critical and critical.get("tti_steps", 999) <= 12 else ("#f59e0b" if critical else "#94a3b8")
    rows = []
    for r in pending:
        obj = str(r.get('objective_label', '')).replace(' / ', '/').split()[0]
        rows.append(
            '<div class="aegis-mini-row">'
            + f"<div>{r.get('asset_id','')}</div>"
            + f"<div>{r.get('target_id','')}</div>"
            + f"<div>{obj}</div>"
            + f"<div>{float(r.get('tti_steps',0.0)):.1f}</div>"
            + f"<div>{str(r.get('status','')).replace('_',' ')}</div>"
            + '</div>'
        )
    table_html = ''.join(rows) if rows else '<div class="aegis-mini-row"><div>-</div><div>-</div><div>-</div><div>-</div><div>CLEAR</div></div>'
    html = (
        f'<div class="aegis-dominance" style="border-left-color:{border}"><div class="aegis-dominance-grid"><div>'
        + f'<div class="aegis-dominance-title">{payload["headline"]}</div>'
        + f'<div class="aegis-dominance-main">{" | ".join(lines)}</div>'
        + f'<div class="aegis-dominance-sub">{payload["summary"]}</div>'
        + '</div><div class="aegis-mini-table">'
        + '<div class="aegis-mini-row aegis-mini-head"><div>Asset</div><div>Target</div><div>Obj</div><div>TTI</div><div>Status</div></div>'
        + table_html
        + '</div></div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def render_app(world: dict, reset_state_cb) -> None:
    _render_header(world)
    render_sidebar(world, reset_state_cb)
    _render_operator_dominance(world)

    top_risks = _top_threat_risks(world, limit=3)
    if top_risks:
        pills = []
        for idx, r in enumerate(top_risks, start=1):
            cls = "critical" if r.get("band") in ("HIGH", "CRITICAL") or r.get("tti_steps", 999) <= 12 else "warning"
            pills.append(f'<span class="aegis-threat-pill {cls}">P{idx} {str(r["objective"]).upper()} · TTI {r["tti_steps"]:.1f}</span>')
        st.markdown('<div class="aegis-threat-board"><div class="aegis-threat-row">' + ''.join(pills) + '</div></div>', unsafe_allow_html=True)

    left, right = st.columns([1.8, 1.15], gap="medium")
    with left:
        st.markdown('<div class="aegis-map-note"><b>Battlefield picture:</b> top-priority threats are emphasized; lower-value text clutter has been reduced for faster briefing readability.</div>', unsafe_allow_html=True)
        st.plotly_chart(core.render_battlefield(), use_container_width=True, config={"displayModeBar": False})
    with right:
        _render_side_mission_summary(world)
        st.subheader("Immediate operator queue")
        _render_operator_queue_panel(world, show_dataframe=False)

    with st.expander("Queue detail and mission impact", expanded=False):
        pending = core.pending_df()
        if not pending.empty:
            preferred = [c for c in ["asset_id", "target_id", "objective_label", "tti_steps", "confidence", "status", "authority_basis"] if c in pending.columns]
            st.dataframe(pending[preferred], use_container_width=True, hide_index=True)
        shadow = world.get("shadow_state", {})
        summary = shadow.get("last_summary", {})
        comparison = shadow.get("last_comparison", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Shadow profile", summary.get("profile", "n/a"))
        c2.metric("Alignment", f"{summary.get('agreement_pct', 100.0):.1f}%")
        c3.metric("Time gain", summary.get("projected_outcome", {}).get("time_gain_s", 0.0))
        c4.metric("Actions saved", summary.get("projected_outcome", {}).get("operator_actions_saved", summary.get("estimated_operator_actions_saved", 0)))
        if comparison.get("diagnostic") == "divergence":
            missed = ", ".join(comparison.get("missed_by_active", [])[:3]) or "alternative priority set"
            st.warning(f"Shadow challenge: low alignment with the live path. Missed threat risk: {missed}.")
        else:
            st.success("Shadow advisory aligned with the live path.")
        sdf = core.shadow_delta_df()
        if not sdf.empty:
            st.dataframe(sdf, use_container_width=True, hide_index=True)

    with st.expander("Automation reasoning and authority", expanded=False):
        left, right = st.columns([1.25, 1])
        with left:
            for note in _automation_reasoning_trace(world):
                st.write("- " + note)
            ribbon = _tactical_action_ribbon_df(world)
            if not ribbon.empty:
                st.dataframe(ribbon, use_container_width=True, hide_index=True, height=220)
        with right:
            st.subheader("Authority state")
            st.json(world.get("authority_state", {}), expanded=False)
            st.subheader("Cognitive state")
            st.json(world.get("cognitive_state", {}), expanded=False)

    with st.expander("Mission systems and resilience", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Coverage and pressure")
            st.dataframe(core.coverage_df(), use_container_width=True, hide_index=True)
            st.dataframe(core.assets_pressure_df(), use_container_width=True, hide_index=True)
        with c2:
            st.subheader("Assets and engagement state")
            st.dataframe(core.assets_health_df(), use_container_width=True, hide_index=True)
            st.dataframe(core.engagement_assets_df(), use_container_width=True, hide_index=True)
            if world.get("missiles"):
                st.dataframe(pd.DataFrame(world["missiles"]), use_container_width=True, hide_index=True, height=180)

    with st.expander("Integration, quantum readiness, scenario JSON", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Integration")
            st.json(world.get("integration_config", {}), expanded=False)
            st.subheader("Quantum readiness")
            st.json(world.get("quantum_interface", {}), expanded=False)
        with c2:
            st.subheader("Scenario JSON")
            st.json({
                "authority_state": world.get("authority_state", {}),
                "shadow_summary": world.get("shadow_state", {}).get("last_summary", {}),
                "pending": world.get("pending_recommendations", []),
            }, expanded=False)
