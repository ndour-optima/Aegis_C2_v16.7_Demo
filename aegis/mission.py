from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from . import core
from .integration.ingest import ingest_external_data


def _append_note(world: dict, key: str, text: str) -> None:
    world["explanations"].setdefault(key, [])
    world["explanations"][key].append(text)


def evaluate_resilience(world: dict) -> dict:
    cfg = world["resilience_config"]
    state = world["resilience_state"]
    state["notes"] = []
    degraded = cfg["comms_mode"] != "Nominal" or cfg["remote_link_quality"] < 0.75 or cfg["sensor_fusion_quality"] < 0.8 or cfg["gps_quality"] < 0.8
    fallback = False
    if cfg["comms_mode"] in ("Remote degraded", "Remote lost") and cfg.get("local_fallback_enabled", True):
        fallback = True
    if cfg["remote_link_quality"] < 0.45 and cfg.get("local_fallback_enabled", True):
        fallback = True

    if cfg["comms_mode"] == "Remote lost":
        state["notes"].append("Remote C2 link lost: local cell retains control authority.")
    elif cfg["comms_mode"] == "Remote degraded":
        state["notes"].append("Remote C2 degraded: latency and approval friction increased.")
    if cfg["sensor_fusion_quality"] < 0.8:
        state["notes"].append("Sensor fusion quality reduced: operator should rely on confidence bands more cautiously.")
    if cfg["gps_quality"] < 0.8:
        state["notes"].append("Navigation reference degraded: expect local position uncertainty and wider engagement caution.")

    if fallback and not state.get("fallback_active"):
        core.log_authority(f"Fallback transferred to {cfg['local_operator_name']} due to communications degradation.", "FALLBACK")
        state["last_transition_step"] = world["step"]
    elif (not fallback) and state.get("fallback_active"):
        core.log_authority("Remote control link restored; normal approval routing resumed.", "RECOVERY")
        state["last_transition_step"] = world["step"]

    state["degraded"] = degraded
    state["fallback_active"] = fallback
    world["authority_config"]["effective_operator_name"] = cfg["local_operator_name"] if fallback else world["authority_config"].get("operator_name", "operator_1")

    world["explanations"]["resilience_notes"] = list(state["notes"])
    return state


def evaluate_cognitive_load(world: dict) -> dict:
    cfg = world["cognitive_config"]
    alive = core.alive_threats()
    critical = 0
    for t in alive:
        crit = core.threat_criticality(t)
        if crit["band"] in ("HIGH", "CRITICAL"):
            critical += 1
    pending = len([r for r in world.get("pending_recommendations", []) if r.get("status") in ("SUGGESTED", "PENDING_APPROVAL")])
    missiles = len(world.get("missiles", []))
    swarm = len([t for t in alive if "swarm" in str(t.get("kind", ""))])
    comms_penalty = 1.0 - min(world["resilience_config"].get("remote_link_quality", 1.0), world["resilience_config"].get("sensor_fusion_quality", 1.0))

    breakdown = {
        "pending_queue": min(1.0, pending / 6.0) * cfg["pending_weight"],
        "critical_threats": min(1.0, critical / 4.0) * cfg["critical_weight"],
        "swarm_density": min(1.0, swarm / 8.0) * cfg["swarm_weight"],
        "comms_stress": max(0.0, comms_penalty) * cfg["comms_weight"],
        "missiles_in_flight": min(1.0, missiles / 6.0) * cfg["missile_weight"],
    }
    score = min(cfg["max_operator_load"], round(sum(breakdown.values()), 3))
    band = "LOW"
    if score >= cfg["collapse_threshold"]:
        band = "COLLAPSE RISK"
    elif score >= cfg["overload_threshold"]:
        band = "HIGH"
    elif score >= 0.45:
        band = "ELEVATED"

    recs = []
    ui_mode = "Normal"
    if band in ("HIGH", "COLLAPSE RISK"):
        ui_mode = "Condensed / Command"
        recs.append("Prioritise critical/high engagements and collapse low-value detail.")
        recs.append("Use batch approve/veto rather than one-by-one review when doctrine allows.")
    if world["resilience_state"].get("fallback_active"):
        recs.append("Display local fallback banner and suppress remote-only workflow assumptions.")
    if pending >= 4:
        recs.append("Operator queue is building; consider temporary auto-approval for critical threats only.")

    world["cognitive_state"] = {
        "score": score,
        "band": band,
        "driver_breakdown": breakdown,
        "ui_mode": ui_mode,
        "recommendations": recs,
    }
    world["explanations"]["cognitive_load_notes"] = [f"Load band {band} at score {score:.2f}."] + recs
    return world["cognitive_state"]




def resolve_authority_state(world: dict) -> dict:
    configured = world.get("configured_authority_mode", world.get("authority_mode", "Approval Required"))
    effective = configured
    source = "Configured policy"
    reason = "No runtime override active."
    approved = [r for r in world.get("pending_recommendations", []) if r.get("status") == "APPROVED"]
    actionable = [r for r in world.get("pending_recommendations", []) if r.get("status") in ("SUGGESTED", "PENDING_APPROVAL")]
    bases = " | ".join(str(r.get("authority_basis", "")) for r in approved).lower()
    if any(k in bases for k in ["hard-bind", "terminal", "emergency distance", "criticality-triggered", "critical override", "emergency auto"]):
        effective = "Emergency Auto-Fire"
        source = "Runtime safety override"
        reason = "Criticality, terminal range, or emergency-distance rule escalated authority."
    elif "overload" in bases or "leaky-defense" in bases:
        effective = "Approval Required"
        source = "Runtime safeguard"
        reason = "Operator-pressure safeguard elevated selected recommendations."
    elif world.get("adaptive_doctrine_state", {}).get("active"):
        effective = world.get("authority_mode", configured)
        source = "Adaptive doctrine engine"
        reason = world.get("adaptive_doctrine_state", {}).get("reason", "Adaptive doctrine relaxed engagement constraints.")
    elif configured == "Auto If High Confidence" and approved:
        effective = "Auto If High Confidence"
        source = "Confidence gate"
        reason = "Recommendations cleared the automatic confidence threshold."
    escalated = sorted([r for r in actionable if int(r.get("escalation_level", 0) or 0) > 0], key=lambda r: int(r.get("escalation_level", 0) or 0), reverse=True)
    operator = world.get("authority_escalation_state", {}).get("current_operator", world.get("authority_config", {}).get("operator_name", "operator_1"))
    if escalated:
        operator = escalated[0].get("effective_operator", operator)
        source = "Authority escalation layer"
        reason = f"Unapproved recommendation forwarded to {operator} after timeout."
    state = {
        "configured": configured,
        "effective": effective,
        "source": source,
        "reason": reason,
        "effective_operator": operator,
    }
    world["authority_state"] = state
    world.setdefault("authority_config", {})["effective_operator_name"] = operator
    world["effective_authority_mode"] = effective
    world.setdefault("explanations", {}).setdefault("authority_state_notes", [])
    world["explanations"]["authority_state_notes"] = [f"Configured authority: {configured}.", f"Effective authority: {effective}.", f"Authority source: {source}.", reason]
    pending = len(world.get("pending_recommendations", []))
    approved_count = len(approved)
    world.setdefault("explanations", {})["step_summary"] = f"{pending} recommendations | {approved_count} approved | authority={effective}"
    return state
def record_audit_frame(world: dict, source: str = "step") -> dict:
    if not world.get("audit_config", {}).get("autosave_every_step", True) and source == "step":
        return {}
    frame = {
        "step": world["step"],
        "time": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "destroyed_count": world.get("destroyed_count", 0),
        "doctrine_name": world.get("doctrine_name"),
        "authority_mode": world.get("effective_authority_mode", world.get("authority_mode")),
        "configured_authority_mode": world.get("configured_authority_mode", world.get("authority_mode")),
        "fallback_active": world.get("resilience_state", {}).get("fallback_active"),
        "cognitive_band": world.get("cognitive_state", {}).get("band"),
        "summary": world.get("explanations", {}).get("step_summary", ""),
        "event_count": len(world.get("event_log", [])),
        "pending_count": len(world.get("pending_recommendations", [])),
        "world": None,
        "world_compact": {
            "impact_markers": deepcopy(world.get("impact_markers", [])),
            "assets": deepcopy(world.get("assets", [])),
            "threats": deepcopy(world.get("threats", [])),
            "objectives": deepcopy(world.get("objectives", [])),
            "assignments": deepcopy(world.get("assignments", {})),
            "engagements": deepcopy(world.get("engagements", [])),
            "missiles": deepcopy(world.get("missiles", [])),
            "pending_recommendations": deepcopy(world.get("pending_recommendations", [])),
            "destroyed_count": world.get("destroyed_count", 0),
            "kill_assurance_state": deepcopy(world.get("kill_assurance_state", {})),
            "authority_state": deepcopy(world.get("authority_state", {})),
            "shadow_summary": deepcopy(world.get("shadow_state", {}).get("last_summary", {})),
            "shadow_comparison": deepcopy(world.get("shadow_state", {}).get("last_comparison", {})),
        },
    }
    digest_input = json.dumps({
        "step": frame["step"],
        "destroyed_count": frame["destroyed_count"],
        "pending_count": frame["pending_count"],
        "summary": frame["summary"],
    }, sort_keys=True).encode("utf-8")
    frame["hash"] = hashlib.sha256(digest_input).hexdigest()[:16]
    frames = world.setdefault("audit_state", {}).setdefault("frames", [])
    frames.append(frame)
    max_frames = int(world.get("audit_config", {}).get("max_replay_frames", 200))
    if len(frames) > max_frames:
        del frames[:-max_frames]
    world["explanations"]["audit_notes"] = [f"Replay frame captured for step {frame['step']} ({frame['hash']})."]
    return frame


def export_audit_bundle(world: dict, output_dir: str = "output") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output_dir) / f"aegis_v16_7_audit_{ts}.json"
    payload = {
        "meta": world["meta"],
        "step": world["step"],
        "audit_state": world.get("audit_state", {}),
        "event_log": world.get("event_log", []),
        "authority_log": world.get("authority_log", []),
        "override_log": world.get("override_log", []),
        "resilience_state": world.get("resilience_state", {}),
        "cognitive_state": world.get("cognitive_state", {}),
        "quantum_interface": world.get("quantum_interface", {}),
        "shadow_state": world.get("shadow_state", {}),
        "adaptive_doctrine_state": world.get("adaptive_doctrine_state", {}),
        "authority_state": world.get("authority_state", {}),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    world["audit_state"]["last_export_path"] = str(path)
    return str(path)


def export_replay_bundle(world: dict, output_dir: str = "output") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output_dir) / f"aegis_v16_7_replay_{ts}.json"
    frames = world.get("audit_state", {}).get("frames", [])
    payload = {
        "meta": world["meta"],
        "frame_count": len(frames),
        "frames": frames,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    world["audit_state"]["last_replay_path"] = str(path)
    return str(path)


def sync_quantum_interface(world: dict) -> dict:
    alive = core.alive_threats()
    pending = [r for r in world.get("pending_recommendations", []) if r.get("status") in ("SUGGESTED", "PENDING_APPROVAL")]
    qcfg = world.get("quantum_config", {})
    enabled = bool(qcfg.get("enabled", False))
    problem = {
        "candidate_problem": "engagement allocation" if alive else None,
        "threat_count": len(alive),
        "candidate_decisions": len(pending),
        "objective_count": len(world.get("objectives", [])),
        "status": "Simulated annealing advisory" if enabled else "Adapter-ready, classical mode only",
        "solver_mode": qcfg.get("solver_mode", "Simulated Annealing"),
        "latency_ms": qcfg.get("latency_ms", 12),
    }
    world["quantum_interface"]["candidate_problem"] = problem["candidate_problem"]
    world["quantum_interface"]["last_payload"] = problem
    world["quantum_interface"]["mode"] = ("Quantum-assisted advisory (simulated)" if enabled else "Classical baseline with pluggable optimisation adapter")
    world["quantum_interface"]["status"] = ("Simulated advisory ready" if enabled and alive else ("Prepared" if alive else "Idle"))
    world["explanations"]["quantum_notes"] = [
        "Quantum toggle is a narrative and architecture-readiness layer, not a live quantum claim.",
        f"Solver mode: {problem['solver_mode']} with simulated latency {problem['latency_ms']} ms.",
        ("Advisory optimisation is displayed as a what-if next-generation mode." if enabled else "Live decisions remain classical and explainable; the architecture is only adapter-ready for future optimisation modules."),
    ]
    return problem


def sync_integration_interface(world: dict) -> dict:
    result = ingest_external_data(world)
    world["explanations"]["integration_notes"] = list(result.get("notes", []))
    return result




def sync_shadow_mode(world: dict) -> dict:
    cfg = world.get("shadow_config", {})
    enabled = bool(cfg.get("enabled", True))
    profile = cfg.get("profile", "Coverage-First AI")
    snapshot = core.snapshot_world_state(world)
    active_pending = snapshot.get("pending_recommendations", [])

    if enabled:
        shadow_result = core.run_shadow_decision_pass(snapshot, cfg)
        comparison_bundle = core.compare_active_vs_shadow(snapshot, active_pending, shadow_result)
        comparison = comparison_bundle["comparison"]
        active = comparison_bundle["active"]
        summary = {
            "enabled": True,
            "mode": "Parallel read-only advisory",
            "profile": profile,
            "current_authority": world.get("effective_authority_mode", world.get("authority_mode")),
            "shadow_authority": shadow_result.get("authority_mode"),
            "live_doctrine": world.get("doctrine_name"),
            "shadow_doctrine": shadow_result.get("doctrine_name"),
            "active_threats": len(core.alive_threats()),
            "pending_recommendations": active.get("pending_count", 0),
            "agreement_pct": comparison.get("agreement_pct", 100.0),
            "estimated_missiles_saved": max(0, comparison.get("ammo_delta", 0)),
            "estimated_operator_actions_saved": comparison.get("operator_actions_current", 0),
            "estimated_reaction_time_live_s": float(cfg.get("assumed_reaction_time_saved_s", 4.0)) + 4.0,
            "estimated_reaction_time_shadow_s": 4.0,
            "missed_by_active": comparison.get("missed_by_active", []),
            "missed_by_shadow": comparison.get("missed_by_shadow", []),
            "protocol_labels": world.get("integration_config", {}).get("protocol", "Internal"),
            "diagnostic": comparison.get("diagnostic", "aligned"),
            "decision_alignment_label": ("HIGH" if comparison.get("agreement_pct", 100.0) >= 95 else ("MEDIUM" if comparison.get("agreement_pct", 100.0) >= 70 else "LOW")),
            "projected_outcome": {
                "time_gain_s": round(max(0.0, (float(cfg.get("assumed_reaction_time_saved_s", 4.0)))), 1),
                "coverage_delta": max(0, len(comparison.get("missed_by_active", [])) - len(comparison.get("missed_by_shadow", []))),
                "operator_actions_saved": comparison.get("operator_actions_current", 0),
            },
        }
        diagnostic = comparison.get("diagnostic", "aligned")
        notes = [
            f"Shadow profile {profile} ran from a deep-copied snapshot with doctrine {shadow_result.get('doctrine_name')}.",
            f"Agreement with live path: {comparison.get('agreement_pct', 100.0):.1f}%.",
            ("Live decision gap detected: shadow found viable engagements while the live path remained inactive." if diagnostic == "decision_gap_live_inactive" else (f"Shadow highlighted live misses on {', '.join(comparison.get('missed_by_active', []))}." if comparison.get('missed_by_active') else "Shadow found no missed targets versus the live path.")),
            (f"Priority divergence: {', '.join(comparison.get('priority_conflicts', [])[:4])}." if comparison.get('priority_conflicts') else "No asset-target priority divergence this step."),
        ]
        history = world.setdefault("shadow_state", {}).setdefault("history", [])
        new_entry = {
            "step": world.get("step", 0),
            "profile": profile,
            "active": active,
            "shadow": shadow_result,
            "comparison": comparison,
        }
        entry_signature = json.dumps(new_entry, sort_keys=True)
        last_signature = json.dumps(history[-1], sort_keys=True) if history else None
        if entry_signature != last_signature:
            history.append(new_entry)
        world["shadow_state"] = {
            "enabled": True,
            "mode": summary["mode"],
            "last_summary": summary,
            "last_notes": notes,
            "history": history[-200:],
            "last_active": active,
            "last_shadow": shadow_result,
            "last_comparison": comparison,
        }
    else:
        summary = {
            "enabled": False,
            "mode": "Disabled",
            "profile": profile,
            "agreement_pct": 100.0,
            "protocol_labels": world.get("integration_config", {}).get("protocol", "Internal"),
            "diagnostic": comparison.get("diagnostic", "aligned"),
            "decision_alignment_label": ("HIGH" if comparison.get("agreement_pct", 100.0) >= 95 else ("MEDIUM" if comparison.get("agreement_pct", 100.0) >= 70 else "LOW")),
        }
        notes = ["Shadow mode disabled."]
        state = world.setdefault("shadow_state", {})
        world["shadow_state"] = {
            "enabled": False,
            "mode": "Disabled",
            "last_summary": summary,
            "last_notes": notes,
            "history": state.get("history", []),
            "last_active": state.get("last_active", {}),
            "last_shadow": {},
            "last_comparison": {},
        }
    world["explanations"]["shadow_notes"] = notes
    return summary


def export_doctrine_bundle(world: dict, output_dir: str = "output") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output_dir) / f"aegis_v16_7_doctrine_{ts}.json"
    payload = {
        "meta": world.get("meta", {}),
        "doctrine_name": world.get("doctrine_name"),
        "authority_mode": world.get("effective_authority_mode", world.get("authority_mode")),
        "configured_authority_mode": world.get("configured_authority_mode", world.get("authority_mode")),
        "authority_config": world.get("authority_config", {}),
        "criticality_config": world.get("criticality_config", {}),
        "fire_control_config": world.get("fire_control_config", {}),
        "resilience_config": world.get("resilience_config", {}),
        "cognitive_config": world.get("cognitive_config", {}),
        "integration_config": world.get("integration_config", {}),
        "degradation_config": world.get("degradation_config", {}),
        "quantum_config": world.get("quantum_config", {}),
        "shadow_config": world.get("shadow_config", {}),
        "adaptive_doctrine_config": world.get("adaptive_doctrine_config", {}),
        "adaptive_doctrine_state": world.get("adaptive_doctrine_state", {}),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    world.setdefault("doctrine_export_state", {})["last_export_path"] = str(path)
    return str(path)



def sync_live_advisory_picture(world: dict, source: str = "manual") -> dict:
    """Bootstrap live recommendations for advisory/approval modes without advancing the simulation."""
    if world.get("step", 0) != 0:
        return {"activated": False, "reason": "step_nonzero"}
    if source not in ("app_load", "manual", "audit_export"):
        return {"activated": False, "reason": "source_skip"}
    if world.get("missiles") or world.get("engagements"):
        return {"activated": False, "reason": "live_activity_present"}
    if world.get("pending_recommendations"):
        return {"activated": False, "reason": "pending_already_present"}
    if not core.alive_threats():
        return {"activated": False, "reason": "no_alive_threats"}

    previous_summary = world.get("explanations", {}).get("step_summary", "")
    recs, assignments, ew_recommendation = core.build_candidate_assignments()
    core.queue_recommendations(assignments, ew_recommendation)
    core.evaluate_authority()
    core.queue_soft_reengagement_candidates()
    pending = len(world.get("pending_recommendations", []))
    approved = len([r for r in world.get("pending_recommendations", []) if r.get("status") == "APPROVED"] )
    if pending:
        world["explanations"]["step_summary"] = f"{pending} recommendations | {approved} approved | authority={world['authority_mode']}"
        world["explanations"].setdefault("decision_trace", []).append(
            f"Step {world['step']}: live advisory picture prepared without advancing simulation state."
        )
        world["explanations"].setdefault("authority_notes", []).append(
            "Decision gating separated from execution: recommendations prepared before any launch authority is exercised."
        )
    elif previous_summary:
        world["explanations"]["step_summary"] = previous_summary
    return {"activated": bool(pending), "pending": pending, "approved": approved, "reason": "bootstrap_live_advisory"}

def refresh_mission_layers(world: dict, source: str = "manual") -> None:
    sync_live_advisory_picture(world, source=source)
    evaluate_resilience(world)
    evaluate_cognitive_load(world)
    resolve_authority_state(world)
    sync_quantum_interface(world)
    sync_shadow_mode(world)
    resolve_authority_state(world)
    sync_integration_interface(world)

    if source in ("step", "audit_export", "replay_export", "manual", "app_load", "approve_high", "veto_high", "approve_selected", "veto_selected", "doctrine_export"):
        record_audit_frame(world, source=source)
