import math
import json
import random
import time
from copy import deepcopy
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go

random.seed(42)

DOCTRINES = {
    "Strict Deconfliction": {"max_assets_per_target": 1, "allow_redundancy_when_one_threat_left": True, "retask_margin": 0.18, "distance_weight": 0.04, "prefer_spread": True},
    "Balanced": {"max_assets_per_target": 1, "allow_redundancy_when_one_threat_left": True, "retask_margin": 0.12, "distance_weight": 0.035, "prefer_spread": True},
    "Aggressive": {"max_assets_per_target": 2, "allow_redundancy_when_one_threat_left": True, "retask_margin": 0.08, "distance_weight": 0.03, "prefer_spread": False},
    "Terminal Defense": {"max_assets_per_target": 2, "allow_redundancy_when_one_threat_left": True, "retask_margin": 0.05, "distance_weight": 0.02, "prefer_spread": False},
}
AUTHORITY_MODES = {
    "Full Manual": "Every recommendation waits for operator approval.",
    "Approval Required": "Recommendations queue for approval or veto.",
    "Auto If High Confidence": "Auto-approve above confidence threshold.",
    "Emergency Auto-Fire": "Auto-fire imminent threats near objectives.",
}

def make_default_state():
    return {
        "meta": {"version": "v16.7", "title": "Aegis C2 Quantum Dual Use — v16.7"},
        "step": 0,
        "destroyed_count": 0,
        "history": [],
        "doctrine_name": "Balanced",
        "authority_mode": "Approval Required",
        "authority_config": {
            "auto_conf_threshold": 0.82,
            "emergency_distance_km": 2.5,
            "veto_window_steps": 2,
            "operator_name": "operator_1",
            "escalation_chain": ["operator_1", "operator_2", "operator_3"],
            "escalation_tti_steps": 10.0,
            "auto_release_after_chain_exhausted": True,
        },
        "fire_control_config": {
            "single_shot_default": True,
            "allow_salvo_on_high_value": True,
            "allow_salvo_on_terminal": True,
            "salvo_size_high_value": 2,
            "salvo_size_terminal": 2,
            "hold_if_missile_in_flight": True,
            "retarget_after_miss_steps": 3,
            "reengage_after_miss_only": True,
            "missile_base_flight_steps": 3,
            "one_target_per_launcher": True,
            "strict_fire_control_lock": True,
            "coverage_first": True,
            "adaptive_reengagement": True,
            "reengage_priority_bonus": 0.18,
            "reengage_same_target_window": 3,
            "post_miss_same_launcher_penalty": 0.05,
            "launcher_economy": True,
            "economy_swarm_threshold": 6,
            "economy_last_missile_reserve": 1,
        },
        "engagement_state": {"assets": {}, "targets": {}},
        "kill_chain_config": {
            "reengage_cooldown_steps": 1,
            "max_engagement_attempts_before_escalation": 2,
            "allow_same_launcher_reengage": True,
            "shoot_look_shoot": True,
            "persistent_reengagement": True,
            "step_time_budget_s": 0.20
        },
        "kill_assurance_state": {
            "watchlist": [],
            "escalation_notes": [],
            "resolved_log": []
        },
        "runtime_metrics": {"last_step_time_s": 0.0},
        "adaptive_doctrine_config": {
            "enabled": True,
            "stagnation_steps": 2,
            "expiry_window_steps": 3,
            "expiry_trigger_count": 2,
            "restore_clear_steps": 2,
            "relaxed_auto_conf_threshold": 0.55,
            "min_step_before_activation": 3,
            "queue_pressure_threshold": 2,
            "high_threat_tti_steps": 12,
            "swarm_surge_threshold": 4,
            "ammo_guard_threshold": 3,
            "pressure_restore_steps": 2,
        },
        "adaptive_doctrine_state": {
            "active": False,
            "reason": "",
            "trigger": "",
            "strategy": "",
            "activated_step": None,
            "clear_steps": 0,
            "no_assignment_streak": 0,
            "baseline": {},
            "profile": "BASELINE",
            "last_pressure_score": 0.0,
            "last_shift_summary": "",
            "last_shift_step": -999,
            "last_shift_banner": "",
            "pressure_breakdown": {},
        },
        "operator_consequence_state": {
            "last_event_step": -999,
            "last_title": "",
            "last_text": "",
            "severity": "info",
            "risk_delta_pct": 0.0,
            "coverage_delta_pct": 0.0,
            "expected_damage_delta_pct": 0.0,
            "counterfactual": "",
        },
        "authority_escalation_state": {
            "current_operator": "operator_1",
            "current_level": 0,
            "last_event_step": -999,
            "last_title": "",
            "last_text": "",
            "active": False,
        },
        "quantum_config": {
            "enabled": False,
            "solver_mode": "Simulated Annealing",
            "latency_ms": 12,
        },
        "shadow_config": {
            "enabled": True,
            "profile": "Aggressive AI",
            "compare_against_current_authority": True,
            "assumed_reaction_time_saved_s": 4.0,
            "protocol_labels": "Internal",
            "divergence_tuning": 0.12,
            "confidence_bias": 0.04,
        },
        "shadow_state": {
            "enabled": True,
            "mode": "Parallel read-only advisory",
            "last_summary": {},
            "last_notes": [],
            "history": [],
            "last_active": {},
            "last_shadow": {},
            "last_comparison": {},
        },
        "doctrine_export_state": {
            "last_export_path": None,
        },
        "degradation_config": {
            "sensor_1_offline": False,
            "shorad_2_offline": False,
            "show_coverage_gap": True,
            "auto_gap_alert": True,
            "leak_step_limit": 20,
        },
        "coverage_state": {
            "integrity_pct": 100,
            "gap_detected": False,
            "gap_assets": [],
            "notes": [],
        },

        "adversarial_config": {
            "enabled": True,
            "maneuver_intensity": 0.22,
            "sensor_noise_km": 0.20,
            "deception_probability": 0.18,
            "terrain_mask_probability": 0.12,
            "spawn_reinforcement_step": 6,
            "reinforcement_count": 2,
            "pk_adversarial_penalty": 0.08,
        },
        "adversarial_state": {
            "enabled": True,
            "reinforcement_spawned": False,
            "last_notes": [],
            "jink_events": [],
            "deception_events": [],
        },
        "pressure_config": {
            "track_capacity": 4,
            "max_pending_before_overload": 3,
            "overload_pk_penalty": 0.15,
            "decision_delay_pk_penalty_per_step": 0.06,
            "missiles_per_shorad": 3,
            "reload_time_steps": 2,
            "ew_duty_cycle_max": 3,
            "ew_cooldown_steps": 2,
            "operator_overload_autofallback": True,
        },
        "config": {
            "defended_radius_km": 2.0,
            "ew_radius_km": 3.0,
            "ew_threshold": 0.72,
            "missile_speed_progress": 0.34,
            "missile_min_progress": 0.18,
            "swarm_cohesion": 0.85,
            "evasion_strength": 0.35,
            "split_trigger_distance_km": 5.0,
            "base_pk": 0.72,
            "ew_disrupt_prob": 0.62,
            "uncertainty_noise": 0.08,
            "objective_weight_strength": 0.55,
        },
        "assets": [
            {"id": "shorad_1", "x": 2.0, "y": 1.0, "kind": "SHORAD", "ready": True, "status": "online", "missiles_left": 3, "reserve_missiles": 3, "reload_counter": 0},
            {"id": "shorad_2", "x": 1.8, "y": -0.8, "kind": "SHORAD", "ready": True, "status": "online", "missiles_left": 3, "reserve_missiles": 3, "reload_counter": 0},
            {"id": "ew_1", "x": 0.7, "y": 0.3, "kind": "EW", "ready": True, "status": "online", "duty_used": 0, "cooldown_counter": 0},
            {"id": "sensor_1", "x": 0.2, "y": 0.0, "kind": "SENSOR", "ready": True, "status": "online"},
        ],
        "objectives": [
            {"id": "hq", "x": 0.0, "y": 0.0, "kind": "OBJECTIVE", "label": "HQ / Core C2", "value": 1.00, "status": "protected"},
            {"id": "radar", "x": -0.8, "y": 1.6, "kind": "OBJECTIVE", "label": "Radar Node", "value": 0.72, "status": "protected"},
            {"id": "ammo", "x": 1.4, "y": -1.8, "kind": "OBJECTIVE", "label": "Ammo / Logistics", "value": 0.88, "status": "protected"},
            {"id": "decoy", "x": -1.6, "y": -1.3, "kind": "OBJECTIVE", "label": "Decoy Vehicle", "value": 0.30, "status": "protected"},
        ],
        "threats": [
            {"id": "threat_1", "x": 10.8, "y": 2.0, "vx": -0.55, "vy": -0.04, "kind": "THREAT:swarm", "altitude_m": 250, "ew_susceptibility": 0.82, "alive": True, "behavior": "cohesive", "degraded": False, "confidence": 0.92, "target_objective": "radar", "fuel_steps": 24, "steps_alive": 0, "escaped": False},
            {"id": "threat_2", "x": 12.0, "y": 0.8, "vx": -0.58, "vy": -0.02, "kind": "THREAT:swarm", "altitude_m": 240, "ew_susceptibility": 0.86, "alive": True, "behavior": "cohesive", "degraded": False, "confidence": 0.89, "target_objective": "hq", "fuel_steps": 24, "steps_alive": 0, "escaped": False},
            {"id": "threat_3", "x": 9.2, "y": 3.2, "vx": -0.42, "vy": -0.10, "kind": "THREAT:loitering", "altitude_m": 600, "ew_susceptibility": 0.60, "alive": True, "behavior": "loiter", "degraded": False, "confidence": 0.83, "target_objective": "radar", "fuel_steps": 24, "steps_alive": 0, "escaped": False},
            {"id": "threat_4", "x": 11.4, "y": -1.5, "vx": -0.62, "vy": 0.06, "kind": "THREAT:swarm", "altitude_m": 220, "ew_susceptibility": 0.78, "alive": True, "behavior": "cohesive", "degraded": False, "confidence": 0.88, "target_objective": "ammo", "fuel_steps": 24, "steps_alive": 0, "escaped": False},
        ],
        "assignments": {},
        "engagements": [],
        "ew_effects": [],
        "missiles": [],
        "impact_markers": [],
        "combat_state": {},
        "pending_recommendations": [],
        "event_log": [],
        "authority_log": [],
        "override_log": [],
        "criticality_config": {
            "critical_distance_km": 3.0,
            "terminal_distance_km": 1.4,
            "high_value_threshold": 0.85,
            "criticality_weight": 0.22,
            "tti_weight": 0.18,
            "override_confidence_floor": 0.68,
            "hard_bind_emergency_autofire": True,
            "override_medium_threshold": 0.65,
            "auto_override_on_critical": True,
            "auto_override_on_terminal": True
        },
        "explanations": {
            "asset_decisions": [], "retask_decisions": [], "doctrine_notes": [], "candidate_scores": [],
            "ew_decision": None, "step_summary": "", "swarm_notes": [], "outcome_notes": [],
            "objective_notes": [], "authority_notes": [], "pressure_notes": [], "override_notes": [], "allocation_trace": [], "coverage_trace": [], "coverage_first_proof": [], "reengagement_notes": [], "launcher_economy_notes": [], "kill_chain_notes": [], "adversarial_notes": [], "coverage_notes": [], "degradation_notes": []
        },
    }

def apply_demo_mode(state):
    state["doctrine_name"] = "Balanced"
    state["authority_mode"] = "Emergency Auto-Fire"
    state["authority_config"]["auto_conf_threshold"] = 0.80
    state["authority_config"]["emergency_distance_km"] = 3.0
    state["fire_control_config"]["reengage_after_miss_only"] = True
    state["fire_control_config"]["missile_base_flight_steps"] = 3
    state["pressure_config"]["missiles_per_shorad"] = 4
    state["config"]["base_pk"] = 0.74
    state["config"]["missile_speed_progress"] = 0.32
    state["meta"]["title"] += " [DEMO]"
    return state

world = None

def bind_world(world_state):
    global world
    world = world_state

def log_event(text, etype="INFO"):
    world["event_log"].append({"step": world["step"], "time": datetime.now().strftime("%H:%M:%S"), "type": etype, "text": text})

def log_authority(text, atype="AUTH"):
    world["authority_log"].append({"step": world["step"], "time": datetime.now().strftime("%H:%M:%S"), "type": atype, "text": text})

def log_override(text, otype="OVERRIDE"):
    world["override_log"].append({"step": world["step"], "time": datetime.now().strftime("%H:%M:%S"), "type": otype, "text": text})

def _operator_chain():
    cfg = world.get("authority_config", {})
    chain = cfg.get("escalation_chain", [cfg.get("operator_name", "operator_1"), "operator_2", "operator_3"])
    if isinstance(chain, str):
        chain = [x.strip() for x in chain.split(",") if x.strip()]
    chain = list(chain) if chain else [cfg.get("operator_name", "operator_1")]
    if cfg.get("operator_name") and chain[0] != cfg.get("operator_name"):
        chain = [cfg.get("operator_name")] + [c for c in chain if c != cfg.get("operator_name")]
    return chain

def _effective_operator_name():
    esc = world.get("authority_escalation_state", {}) or {}
    return esc.get("current_operator") or world.get("authority_config", {}).get("operator_name", "operator_1")

def _escalation_threshold_tti():
    return float(world.get("authority_config", {}).get("escalation_tti_steps", 10.0))

def _consequence_metrics(rec):
    tti = float(rec.get("tti_steps", 999.0) or 999.0)
    objective = str(rec.get("objective_label", rec.get("objective_value", "objective"))).lower()
    crit = str(rec.get("criticality_band", "LOW")).upper()
    urgency = max(0.0, 18.0 - min(18.0, tti))
    base = 6.0 + urgency * 2.1
    if "hq" in objective or "core" in objective:
        base += 10.0
    elif "radar" in objective:
        base += 7.0
    elif "ammo" in objective or "logistics" in objective:
        base += 5.0
    if crit == "CRITICAL":
        base += 7.0
    elif crit == "HIGH":
        base += 4.0
    risk_delta = round(min(45.0, base), 1)
    coverage_delta = round(min(30.0, 4.0 + urgency * 1.6 + (6.0 if "radar" in objective else 0.0)), 1)
    expected_damage = round(min(60.0, risk_delta * (1.15 if "hq" in objective or "core" in objective else 0.9)), 1)
    ideal_tti = tti + float(world.get("authority_config", {}).get("veto_window_steps", 2)) + 2.0
    counterfactual = f"Without delay, {rec.get('target_id', 'the threat')} would likely have remained on a controlled intercept path around TTI {ideal_tti:.1f}; with delay, the live risk window compressed to TTI {tti:.1f}."
    return {
        "risk_delta_pct": risk_delta,
        "coverage_delta_pct": coverage_delta,
        "expected_damage_delta_pct": expected_damage,
        "counterfactual": counterfactual,
    }


def get_entity_pos(entity_id):
    for obj in world["assets"] + world["threats"] + world["objectives"]:
        if obj["id"] == entity_id:
            return obj["x"], obj["y"]
    return None, None

def get_asset(asset_id):
    for a in world["assets"]:
        if a["id"] == asset_id:
            return a
    return None

def get_threat(threat_id):
    for t in world["threats"]:
        if t["id"] == threat_id:
            return t
    return None

def get_objective(obj_id):
    for o in world["objectives"]:
        if o["id"] == obj_id:
            return o
    return None

def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def alive_threats():
    return [t for t in world["threats"] if t.get("alive", True)]

def distance_to_asset(asset_id, threat_id):
    ax, ay = get_entity_pos(asset_id)
    tx, ty = get_entity_pos(threat_id)
    if None in (ax, ay, tx, ty):
        return 999.0
    return dist(ax, ay, tx, ty)

def distance_to_objective(threat):
    obj = get_objective(threat["target_objective"])
    if not obj:
        return dist(0.0, 0.0, threat["x"], threat["y"])
    return dist(obj["x"], obj["y"], threat["x"], threat["y"])

def current_doctrine():
    return DOCTRINES[world["doctrine_name"]]

def objective_value(threat):
    obj = get_objective(threat["target_objective"])
    return obj["value"] if obj else 0.5

def desired_salvo_size(threat_id):
    threat = get_threat(threat_id)
    if not threat:
        return 1
    crit = threat_criticality(threat)
    fc = world["fire_control_config"]
    if fc.get("allow_salvo_on_terminal", True) and crit["terminal"]:
        return max(1, int(fc.get("salvo_size_terminal", 2)))
    if fc.get("allow_salvo_on_high_value", True) and objective_value(threat) >= world["criticality_config"]["high_value_threshold"]:
        return max(1, int(fc.get("salvo_size_high_value", 2)))
    if fc.get("single_shot_default", True):
        return 1
    return 2 if crit["band"] in ("HIGH", "CRITICAL") else 1

def recent_miss_info(threat_id):
    state = world.get("combat_state", {}).get(threat_id, {})
    if state.get("last_outcome") != "MISS":
        return None
    miss_step = state.get("last_kill_attempt_step")
    if miss_step is None:
        return None
    steps_since = world.get("step", 0) - miss_step
    return {"steps_since_miss": steps_since, "engaged_by": list(state.get("engaged_by", []))}

def launcher_economy_adjustment(threat_id, alive_count):
    fc = world["fire_control_config"]
    threat = get_threat(threat_id)
    if not threat or not fc.get("launcher_economy", True):
        return {"cap": desired_salvo_size(threat_id), "rule": "none", "reason": ""}
    crit = threat_criticality(threat)
    desired = desired_salvo_size(threat_id)
    if crit.get("terminal"):
        return {"cap": desired, "rule": "terminal_preserved", "reason": f"launcher economy preserved full salvo on {threat_id}: terminal threat"}
    shorads = [a for a in world["assets"] if a["kind"] == "SHORAD"]
    ready_launchers = sum(1 for a in shorads if a.get("ready", True) and a.get("missiles_left", 0) > 0)
    total_missiles = sum(max(0, a.get("missiles_left", 0)) for a in shorads)
    reserve = int(fc.get("economy_last_missile_reserve", 1))
    if total_missiles <= ready_launchers * reserve:
        return {"cap": 1, "rule": "reserve_preservation", "reason": f"launcher economy limited {threat_id} to single-shot to preserve last-missile reserve"}
    if alive_count >= int(fc.get("economy_swarm_threshold", 6)) and desired > 1:
        return {"cap": 1, "rule": "swarm_economy", "reason": f"launcher economy limited {threat_id} to single-shot under swarm pressure ({alive_count} viable threats)"}
    return {"cap": desired, "rule": "economy_not_binding", "reason": ""}

def allocation_cap_for_target(threat_id, alive_count):
    threat = get_threat(threat_id)
    if not threat:
        return 1
    fc = world["fire_control_config"]
    desired = desired_salvo_size(threat_id)
    crit = threat_criticality(threat)
    high_value = objective_value(threat) >= world["criticality_config"]["high_value_threshold"]
    economy = launcher_economy_adjustment(threat_id, alive_count)
    desired = min(desired, economy.get("cap", desired))
    if economy.get("reason"):
        world["explanations"].setdefault("launcher_economy_notes", []).append(economy["reason"])
    if fc.get("coverage_first", True):
        # Default to one launcher per target; only allow redundancy when tactically justified.
        if alive_count <= 1:
            return desired
        if crit.get("terminal") or (high_value and desired > 1):
            return desired
        return 1
    return desired

def coverage_first_duplication_decision(threat_id, uncovered_viable_targets):
    threat = get_threat(threat_id)
    desired = desired_salvo_size(threat_id)
    crit = threat_criticality(threat) if threat else {"terminal": False, "band": "LOW"}
    high_value = objective_value(threat) >= world["criticality_config"]["high_value_threshold"] if threat else False
    uncovered_viable_targets = sorted(set(uncovered_viable_targets))

    # v15.4 strict override discipline:
    # coverage-first remains binding even for critical/high-value targets.
    # The only exception while uncovered viable targets remain is terminal defense.
    if crit.get("terminal"):
        return {
            "allowed": True,
            "rule": "terminal_exception",
            "reason": f"second launcher allowed on {threat_id}: terminal exception under strict override discipline",
            "desired_salvo": desired,
            "terminal": True,
            "high_value": high_value,
            "uncovered_viable_targets": uncovered_viable_targets,
        }
    if uncovered_viable_targets:
        return {
            "allowed": False,
            "rule": "coverage_first_block_strict",
            "reason": f"critical override blocked by coverage-first on {threat_id}: uncovered viable targets remain {uncovered_viable_targets}",
            "desired_salvo": desired,
            "terminal": False,
            "high_value": high_value,
            "uncovered_viable_targets": uncovered_viable_targets,
        }
    economy = launcher_economy_adjustment(threat_id, len(alive_threats()))
    if economy.get("cap", desired) <= 1 and not crit.get("terminal"):
        return {
            "allowed": False,
            "rule": economy.get("rule", "launcher_economy"),
            "reason": economy.get("reason", f"second launcher blocked on {threat_id}: launcher economy active"),
            "desired_salvo": min(desired, economy.get("cap", desired)),
            "terminal": False,
            "high_value": high_value,
            "uncovered_viable_targets": [],
        }
    if high_value and desired > 1:
        return {
            "allowed": True,
            "rule": "high_value_salvo_allowed_after_coverage",
            "reason": f"second launcher allowed on {threat_id}: high-value target with desired_salvo={desired} after full coverage",
            "desired_salvo": desired,
            "terminal": False,
            "high_value": True,
            "uncovered_viable_targets": [],
        }
    return {
        "allowed": True,
        "rule": "no_other_viable_target",
        "reason": f"second launcher allowed on {threat_id}: no other viable uncovered target exists",
        "desired_salvo": desired,
        "terminal": False,
        "high_value": high_value,
        "uncovered_viable_targets": [],
    }

def ensure_combat_state_defaults(threat_id=None):
    combat = world.setdefault("combat_state", {})
    ids = [threat_id] if threat_id else [t["id"] for t in world.get("threats", [])]
    for tid in ids:
        state = combat.setdefault(tid, {})
        state.setdefault("state", "IDLE")
        state.setdefault("last_outcome", None)
        state.setdefault("last_action", "")
        state.setdefault("next_action", "Monitor")
        state.setdefault("last_shot_step", None)
        state.setdefault("last_kill_attempt_step", None)
        state.setdefault("awaiting_assessment", False)
        state.setdefault("engaged_by", [])
        state.setdefault("engagement_attempts", 0)
        state.setdefault("needs_reengagement", False)
        state.setdefault("reengage_after_step", 0)
        state.setdefault("resolved", False)

def ensure_adversarial_defaults():
    cfg = world.setdefault("adversarial_config", {})
    cfg.setdefault("enabled", True)
    cfg.setdefault("maneuver_intensity", 0.22)
    cfg.setdefault("sensor_noise_km", 0.20)
    cfg.setdefault("deception_probability", 0.18)
    cfg.setdefault("terrain_mask_probability", 0.12)
    cfg.setdefault("spawn_reinforcement_step", 6)
    cfg.setdefault("reinforcement_count", 2)
    cfg.setdefault("pk_adversarial_penalty", 0.08)

    state = world.setdefault("adversarial_state", {})
    state.setdefault("enabled", bool(cfg.get("enabled", True)))
    state.setdefault("reinforcement_spawned", False)
    state.setdefault("last_notes", [])
    state.setdefault("jink_events", [])
    state.setdefault("deception_events", [])

    world.setdefault("explanations", {}).setdefault("adversarial_notes", [])
    for t in world.get("threats", []):
        t.setdefault("terrain_masked", False)
        t.setdefault("deception_active", False)
        t.setdefault("maneuver_level", 0.0)
        t.setdefault("track_noise_km", 0.0)
        t.setdefault("spawned_reinforcement", False)


def spawn_adversarial_reinforcements():
    ensure_adversarial_defaults()
    cfg = world.get("adversarial_config", {})
    state = world.get("adversarial_state", {})
    if not cfg.get("enabled", True) or state.get("reinforcement_spawned"):
        return
    if world.get("step", 0) < int(cfg.get("spawn_reinforcement_step", 6)):
        return
    count = int(cfg.get("reinforcement_count", 2))
    base_idx = len(world.get("threats", [])) + 1
    for i in range(count):
        sign = 1 if i % 2 == 0 else -1
        tid = f"threat_{base_idx + i}"
        threat = {
            "id": tid, "x": 12.8 + 0.5 * i, "y": sign * (1.4 + 0.6 * i),
            "vx": -0.72, "vy": -0.05 * sign, "kind": "THREAT:swarm",
            "altitude_m": 260, "ew_susceptibility": 0.74, "alive": True,
            "behavior": "cohesive", "degraded": False, "confidence": 0.78,
            "target_objective": "hq" if i == 0 else "radar",
            "terrain_masked": False, "deception_active": False, "maneuver_level": 0.18,
            "track_noise_km": 0.0, "spawned_reinforcement": True,
        }
        world.setdefault("threats", []).append(threat)
        ensure_combat_state_defaults(tid)
    state["reinforcement_spawned"] = True
    note = f"Adversarial reinforcement wave injected at step {world.get('step', 0)} ({count} new threats)."
    state.setdefault("last_notes", []).append(note)
    world["explanations"].setdefault("adversarial_notes", []).append(note)
    log_event(note, "ADVERSARY_SURGE")


def apply_adversarial_battlefield():
    ensure_adversarial_defaults()
    cfg = world.get("adversarial_config", {})
    state = world.get("adversarial_state", {})
    state["enabled"] = bool(cfg.get("enabled", True))
    state["last_notes"] = []
    if not cfg.get("enabled", True):
        return

    spawn_adversarial_reinforcements()

    for t in alive_threats():
        inflight = [m for m in world.get("missiles", []) if m.get("to") == t["id"] and m.get("status") == "IN_FLIGHT"]
        critical = threat_criticality(t)
        t["terrain_masked"] = False
        t["deception_active"] = False
        t["track_noise_km"] = 0.0

        if inflight or critical.get("terminal"):
            sign = 1 if ((world.get("step", 0) + len(t["id"])) % 2 == 0) else -1
            delta = float(cfg.get("maneuver_intensity", 0.22)) * (1.25 if critical.get("terminal") else 1.0)
            t["vy"] += sign * delta
            t["maneuver_level"] = round(min(1.0, t.get("maneuver_level", 0.0) + delta), 2)
            if t.get("behavior") != "split":
                t["behavior"] = "adversarial_evade"
            note = f"{t['id']} executed adversarial jink under pressure."
            state.setdefault("jink_events", []).append({"step": world.get("step", 0), "threat_id": t["id"], "type": "jink"})
            state["last_notes"].append(note)

        if random.random() < float(cfg.get("terrain_mask_probability", 0.12)):
            t["terrain_masked"] = True
            t["confidence"] = max(0.42, t.get("confidence", 0.8) - 0.12)
            t["track_noise_km"] = max(t.get("track_noise_km", 0.0), float(cfg.get("sensor_noise_km", 0.20)))
            state["last_notes"].append(f"{t['id']} used terrain masking and reduced track quality.")

        if random.random() < float(cfg.get("deception_probability", 0.18)):
            t["deception_active"] = True
            t["confidence"] = max(0.36, t.get("confidence", 0.8) - 0.16)
            t["track_noise_km"] = max(t.get("track_noise_km", 0.0), float(cfg.get("sensor_noise_km", 0.20)) * 1.4)
            state.setdefault("deception_events", []).append({"step": world.get("step", 0), "threat_id": t["id"], "type": "spoof"})
            state["last_notes"].append(f"{t['id']} activated deceptive track behavior.")

    world["explanations"]["adversarial_notes"] = state.get("last_notes", [])


def update_kill_assurance_state():
    ensure_combat_state_defaults()
    cfg = world.get("kill_chain_config", {})
    watchlist = []
    escalation_notes = []
    for t in alive_threats():
        state = world["combat_state"].setdefault(t["id"], {})
        inflight = [m for m in world.get("missiles", []) if m.get("to") == t["id"] and m.get("status") == "IN_FLIGHT"]
        if inflight:
            state["state"] = "MISSILE_IN_FLIGHT"
            state["awaiting_assessment"] = True
            state["needs_reengagement"] = False
        elif state.get("last_outcome") == "MISS":
            cooldown_remaining = max(0, int(state.get("reengage_after_step", 0)) - int(world.get("step", 0)))
            if cooldown_remaining <= 0 and cfg.get("persistent_reengagement", True):
                state["needs_reengagement"] = True
                state["state"] = "REENGAGE_REQUIRED"
            else:
                state["state"] = "REENGAGE_COOLDOWN"
        elif state.get("engagement_attempts", 0) == 0:
            state["needs_reengagement"] = True
            state["state"] = "UNENGAGED"
        else:
            state["needs_reengagement"] = False
            if state.get("state") in ("HIT", "RESOLVED"):
                state["resolved"] = True
            else:
                state["state"] = state.get("state", "TRACKING")

        if state.get("needs_reengagement"):
            entry = {
                "threat_id": t["id"],
                "attempts": state.get("engagement_attempts", 0),
                "last_outcome": state.get("last_outcome"),
                "reengage_after_step": state.get("reengage_after_step", 0),
                "distance_to_objective": round(distance_to_objective(t), 2),
                "criticality_band": threat_criticality(t)["band"],
            }
            watchlist.append(entry)
            if state.get("engagement_attempts", 0) >= int(cfg.get("max_engagement_attempts_before_escalation", 2)):
                note = f"{t['id']} requires escalation after {state.get('engagement_attempts', 0)} attempts."
                escalation_notes.append(note)
    world["kill_assurance_state"] = {
        "watchlist": watchlist,
        "escalation_notes": escalation_notes,
        "resolved_log": world.get("kill_assurance_state", {}).get("resolved_log", []),
    }
    world["explanations"]["kill_chain_notes"] = [
        f"{w['threat_id']} awaiting persistent re-engagement after {w['attempts']} attempt(s)." for w in watchlist
    ] + escalation_notes


def refresh_engagement_state():
    targets = {}
    assets = {}
    world.setdefault("combat_state", {})
    ensure_combat_state_defaults()
    for a in world["assets"]:
        inflight = [m for m in world["missiles"] if m["from"] == a["id"] and m.get("status") == "IN_FLIGHT"]
        assets[a["id"]] = {
            "missile_in_flight": bool(inflight),
            "in_flight_to": inflight[0]["to"] if inflight else None,
            "in_flight_steps": max([world["step"] - m.get("approved_step", world["step"]) for m in inflight], default=0),
            "ready": a.get("ready", True),
            "missiles_left": a.get("missiles_left", 0),
            "last_target": world["combat_state"].get(a["id"], {}).get("last_target"),
            "last_outcome": world["combat_state"].get(a["id"], {}).get("last_outcome"),
        }
    for t in alive_threats():
        inflight = [m for m in world["missiles"] if m["to"] == t["id"] and m.get("status") == "IN_FLIGHT"]
        state = world["combat_state"].setdefault(t["id"], {})
        ensure_combat_state_defaults(t["id"])
        if inflight:
            state["state"] = "MISSILE_IN_FLIGHT"
            state["awaiting_assessment"] = True
            state["engaged_by"] = sorted({m["from"] for m in inflight})
        elif state.get("awaiting_assessment"):
            state["state"] = "ASSESSMENT_PENDING"
        else:
            state["state"] = state.get("state", "IDLE") if state.get("state") != "MISSILE_IN_FLIGHT" else "IDLE"
            state["engaged_by"] = state.get("engaged_by", [])
        targets[t["id"]] = {
            "state": state.get("state", "IDLE"),
            "in_flight_count": len(inflight),
            "assets_committed": state.get("engaged_by", []),
            "awaiting_outcome": bool(inflight) or state.get("awaiting_assessment", False),
            "desired_salvo": desired_salvo_size(t["id"]),
            "tti_steps": estimate_time_to_impact_steps(t),
            "last_outcome": state.get("last_outcome"),
            "last_shot_step": state.get("last_shot_step"),
            "engagement_attempts": state.get("engagement_attempts", 0),
            "needs_reengagement": state.get("needs_reengagement", False),
            "reengage_after_step": state.get("reengage_after_step", 0),
        }
    world["engagement_state"] = {"assets": assets, "targets": targets}

def fire_control_hold_reason(asset_id, threat_id):
    fc = world["fire_control_config"]
    refresh_engagement_state()
    astate = world["engagement_state"]["assets"].get(asset_id, {})
    tstate = world["engagement_state"]["targets"].get(threat_id, {})
    combat = world.get("combat_state", {}).get(threat_id, {})
    if fc.get("strict_fire_control_lock", True) and fc.get("one_target_per_launcher", True) and astate.get("missile_in_flight"):
        current = astate.get("in_flight_to")
        return f"asset {asset_id} strict fire-control lock: missile unresolved to {current}"
    if fc.get("hold_if_missile_in_flight", True) and astate.get("missile_in_flight"):
        current = astate.get("in_flight_to")
        return f"asset {asset_id} holding fire: missile already in flight to {current}"
    if tstate.get("in_flight_count", 0) >= tstate.get("desired_salvo", 1):
        return f"target {threat_id} already has sufficient missiles in flight ({tstate.get('in_flight_count',0)}/{tstate.get('desired_salvo',1)})"
    if fc.get("reengage_after_miss_only", True) and combat.get("awaiting_assessment") and tstate.get("in_flight_count", 0) == 0:
        return f"target {threat_id} awaiting assessment before re-engagement"
    if combat.get("reengage_after_step", 0) > world.get("step", 0):
        cooldown_step = combat.get("reengage_after_step", 0)
        return f"target {threat_id} in re-engagement cooldown until step {cooldown_step}"
    return None

def reset_explanations():
    world["explanations"] = {
        "asset_decisions": [], "retask_decisions": [], "doctrine_notes": [], "candidate_scores": [],
        "ew_decision": None, "step_summary": "", "swarm_notes": [], "outcome_notes": [],
        "objective_notes": [], "authority_notes": [], "pressure_notes": [], "override_notes": [],
        "allocation_trace": [], "coverage_trace": [], "coverage_first_proof": [],
        "reengagement_notes": [], "launcher_economy_notes": [], "kill_chain_notes": [], "decision_trace": [], "coverage_notes": [], "degradation_notes": [], "shadow_notes": []
    }



def apply_degradation_state():
    cfg = world.get("degradation_config", {})
    notes = []
    for a in world.get("assets", []):
        sensor_offline = a["id"] == "sensor_1" and cfg.get("sensor_1_offline", False)
        launcher_offline = a["id"] == "shorad_2" and cfg.get("shorad_2_offline", False)
        launcher_disconnected = a["id"] == "shorad_2" and cfg.get("shorad_2_comms_lost", False)
        if sensor_offline or launcher_offline:
            a["status"] = "offline"
            a["ready"] = False
        elif launcher_disconnected:
            a["status"] = "disconnected"
            a["ready"] = False
        elif a.get("status") in ("offline", "disconnected"):
            a["status"] = "online"
            if a["kind"] != "SHORAD" or a.get("missiles_left", 0) > 0:
                a["ready"] = True
        if a["kind"] == "SENSOR" and a.get("status") == "offline":
            world["resilience_config"]["sensor_fusion_quality"] = min(world["resilience_config"].get("sensor_fusion_quality", 1.0), 0.45)
            notes.append(f"{a['id']} offline: fused track quality degraded and uncertainty widened.")
        if a["kind"] == "SHORAD" and a.get("status") == "offline":
            notes.append(f"{a['id']} offline: local coverage gap opened in its sector.")
        if a["kind"] == "SHORAD" and a.get("status") == "disconnected":
            notes.append(f"{a['id']} communication loss: assignments rerouted to remaining connected launchers.")
    world["explanations"]["degradation_notes"] = notes


def update_coverage_state():
    notes = []
    gap_assets = []
    shorads = [a for a in world.get("assets", []) if a.get("kind") == "SHORAD"]
    online = [a for a in shorads if a.get("status", "online") == "online" and a.get("ready", False)]
    integrity = 100 if not shorads else round(100 * len(online) / len(shorads))
    for a in shorads:
        if a.get("status") != "online":
            gap_assets.append(a["id"])
            notes.append(f"Coverage gap around {a['id']} due to {a.get('status', 'degraded')} asset status.")
    world["coverage_state"] = {
        "integrity_pct": integrity,
        "gap_detected": bool(gap_assets),
        "gap_assets": gap_assets,
        "notes": notes,
    }
    world["explanations"]["coverage_notes"] = notes


def enforce_threat_termination():
    leak_limit = int(world.get("degradation_config", {}).get("leak_step_limit", 20))
    survivors = []
    for t in world.get("threats", []):
        if not t.get("alive", True):
            survivors.append(t)
            continue
        t["steps_alive"] = int(t.get("steps_alive", 0)) + 1
        t["fuel_steps"] = int(t.get("fuel_steps", 24)) - 1
        d_obj = distance_to_objective(t)
        if d_obj <= 0.45:
            t["alive"] = False
            t["escaped"] = True
            log_event(f"{t['id']} leaked through defense and impacted {t['target_objective']}", "LEAK")
            world["explanations"]["outcome_notes"].append(f"{t['id']} reached its defended objective; leaky defense recorded.")
        elif t["fuel_steps"] <= 0 or t["steps_alive"] > leak_limit:
            t["alive"] = False
            t["escaped"] = True
            log_event(f"{t['id']} left engagement basket after lifecycle termination", "TERMINATE")
    # keep records for replay but remove dead unresolved stale assignments later

def update_asset_pressure_state():
    for a in world["assets"]:
        if a["kind"] == "SHORAD":
            if a["reload_counter"] > 0:
                a["reload_counter"] -= 1
                if a["reload_counter"] == 0 and a["missiles_left"] <= 0:
                    refill = min(a.get("reserve_missiles", 0), world["pressure_config"]["missiles_per_shorad"])
                    if refill > 0:
                        a["missiles_left"] = refill
                        a["reserve_missiles"] = max(0, a.get("reserve_missiles", 0) - refill)
                        a["ready"] = a.get("status", "online") == "online"
                        world["explanations"]["pressure_notes"].append(f"{a['id']} completed reload cycle with {refill} missile(s).")
                    else:
                        a["status"] = "empty"
                        a["ready"] = False
                        world["explanations"]["pressure_notes"].append(f"{a['id']} exhausted all missiles and cannot reload further.")
            if a["missiles_left"] <= 0 and a["reload_counter"] == 0 and a.get("status", "online") == "online":
                if a.get("reserve_missiles", 0) > 0:
                    a["reload_counter"] = world["pressure_config"]["reload_time_steps"]
                    a["ready"] = False
                    world["explanations"]["pressure_notes"].append(f"{a['id']} entered reload for {a['reload_counter']} step(s).")
                else:
                    a["status"] = "empty"
                    a["ready"] = False
                    world["explanations"]["pressure_notes"].append(f"{a['id']} is combat-empty.")
        if a["kind"] == "EW":
            if a["cooldown_counter"] > 0:
                a["cooldown_counter"] -= 1
                a["ready"] = False
                if a["cooldown_counter"] == 0:
                    a["duty_used"] = 0
                    a["ready"] = True
                    world["explanations"]["pressure_notes"].append(f"{a['id']} EW cooldown complete.")
            elif a["duty_used"] >= world["pressure_config"]["ew_duty_cycle_max"]:
                a["cooldown_counter"] = world["pressure_config"]["ew_cooldown_steps"]
                a["ready"] = False
                world["explanations"]["pressure_notes"].append(f"{a['id']} EW saturated; cooldown engaged.")

def threat_speed_km_step(threat):
    return max(0.05, math.hypot(threat.get("vx", 0.0), threat.get("vy", 0.0)))

def estimate_time_to_impact_steps(threat):
    d_obj = max(distance_to_objective(threat), 0.05)
    return round(d_obj / threat_speed_km_step(threat), 2)

def criticality_band(score):
    if score >= 1.20:
        return "CRITICAL"
    if score >= 0.88:
        return "HIGH"
    if score >= 0.58:
        return "MEDIUM"
    return "LOW"

def threat_criticality(threat):
    cfg = world["criticality_config"]
    d_obj = max(distance_to_objective(threat), 0.05)
    tti = estimate_time_to_impact_steps(threat)
    obj_val = objective_value(threat)
    distance_factor = min(1.0, cfg["critical_distance_km"] / d_obj)
    tti_factor = min(1.0, 3.0 / max(tti, 0.25))
    swarm_bonus = 0.10 if threat["kind"] == "THREAT:swarm" else 0.04
    altitude_bonus = 0.08 if threat.get("altitude_m", 999) < 300 else 0.02
    terminal_bonus = 0.25 if d_obj <= cfg["terminal_distance_km"] else 0.0
    behavior_bonus = 0.10 if threat.get("behavior") in ("split", "evading") else 0.0
    degraded_penalty = 0.06 if threat.get("degraded", False) else 0.0
    score = (0.38 * obj_val) + (0.26 * distance_factor) + (0.18 * tti_factor) + swarm_bonus + altitude_bonus + terminal_bonus + behavior_bonus - degraded_penalty
    score = round(max(0.05, min(1.6, score)), 3)
    return {
        "score": score,
        "band": criticality_band(score),
        "tti_steps": tti,
        "distance_to_objective": round(d_obj, 2),
        "terminal": d_obj <= cfg["terminal_distance_km"],
        "critical_objective": obj_val >= cfg["high_value_threshold"],
    }

def criticality_sort_key(threat):
    c = threat_criticality(threat)
    return (c["score"], -c["tti_steps"])

def sensor_overload_factor():
    load = len(alive_threats())
    cap = world["pressure_config"]["track_capacity"]
    if load <= cap:
        return 0.0
    overload = min(1.0, (load - cap) / max(cap, 1))
    world["explanations"]["pressure_notes"].append(f"Sensor/track overload: {load} threats vs capacity {cap}.")
    return overload

def threat_priority(threat):
    d_obj = max(distance_to_objective(threat), 0.2)
    base = 1.0 / d_obj
    swarm_bonus = 0.25 if threat["kind"] == "THREAT:swarm" else 0.08
    altitude_bonus = 0.15 if threat.get("altitude_m", 0) < 350 else 0.03
    proximity_bonus = 0.18 if d_obj < 4.0 else 0.0
    evasive_penalty = 0.03 if threat.get("behavior") == "evading" else 0.0
    split_bonus = 0.07 if threat.get("behavior") == "split" else 0.0
    degraded_bonus = 0.02 if threat.get("degraded", False) else 0.0
    obj_bonus = objective_value(threat) * world["config"]["objective_weight_strength"]
    overload_penalty = 0.05 * sensor_overload_factor()
    return round(base + swarm_bonus + altitude_bonus + proximity_bonus + split_bonus + degraded_bonus + obj_bonus - evasive_penalty - overload_penalty, 4)

def recommended_effect_for(threat):
    ew = get_asset("ew_1")
    if ew and ew.get("ready", True):
        d = distance_to_asset("ew_1", threat["id"])
        if d <= world["config"]["ew_radius_km"] and threat["ew_susceptibility"] >= world["config"]["ew_threshold"]:
            return "EW"
    return "KINETIC"

def compute_recommendations():
    rows = []
    for t in alive_threats():
        obj = get_objective(t["target_objective"])
        crit = threat_criticality(t)
        state = world.get("combat_state", {}).get(t["id"], {})
        rows.append({
            "threat_id": t["id"], "priority": threat_priority(t), "effect": recommended_effect_for(t),
            "distance_to_objective": round(distance_to_objective(t), 2), "kind": t["kind"],
            "behavior": t.get("behavior", "unknown"), "degraded": t.get("degraded", False),
            "confidence": t.get("confidence", 0.0), "target_objective": t["target_objective"],
            "objective_label": obj["label"] if obj else "Unknown", "objective_value": obj["value"] if obj else 0.0,
            "criticality": crit["score"], "criticality_band": crit["band"], "tti_steps": crit["tti_steps"], "terminal": crit["terminal"],
            "engagement_attempts": state.get("engagement_attempts", 0), "needs_reengagement": state.get("needs_reengagement", False),
            "last_outcome": state.get("last_outcome"), "fuel_steps": t.get("fuel_steps", 0), "steps_alive": t.get("steps_alive", 0)
        })
    rows.sort(key=lambda r: (-r["criticality"], -r["priority"], r["distance_to_objective"]))
    return rows

def doctrine_max_assets_for_target(tid, alive_count):
    doctrine = current_doctrine()
    threat = get_threat(tid)
    obj_val = objective_value(threat) if threat else 0.0
    if alive_count <= 1 and doctrine["allow_redundancy_when_one_threat_left"]:
        return 2
    if obj_val >= 0.85:
        return 2
    if world["doctrine_name"] == "Terminal Defense":
        threat = get_threat(tid)
        if threat and distance_to_objective(threat) <= max(world["config"]["defended_radius_km"] * 2.0, 4.0):
            return 2
    return doctrine["max_assets_per_target"]

def build_candidate_assignments():
    doctrine = current_doctrine()
    recs = compute_recommendations()
    rec_map = {r["threat_id"]: r for r in recs}
    world["engagements"] = []
    world["ew_effects"] = []
    world["explanations"]["doctrine_notes"].append(f"Doctrine={world['doctrine_name']} | prefer_spread={doctrine['prefer_spread']} | strict_lock={world['fire_control_config'].get('strict_fire_control_lock', True)} | coverage_first={world['fire_control_config'].get('coverage_first', True)}")

    if not recs:
        world["explanations"]["step_summary"] = "No active threats."
        return [], {}, None

    for r in recs:
        world["explanations"]["objective_notes"].append(
            f"{r['threat_id']} evaluated against {r['objective_label']} (value {r['objective_value']:.2f}) at {r['distance_to_objective']:.2f} km."
        )

    ew_recommendation = None
    ew_asset = get_asset("ew_1")
    if ew_asset and ew_asset.get("ready", True):
        for r in recs:
            t = get_threat(r["threat_id"])
            ew_distance = round(distance_to_asset("ew_1", r["threat_id"]), 2)
            if r["effect"] == "EW":
                ew_recommendation = {
                    "type": "EW", "from": "ew_1", "to": r["threat_id"],
                    "confidence": round(min(0.95, 0.55 + 0.35 * t["ew_susceptibility"]), 2),
                    "reason": f"EW selected: range {ew_distance} km, susceptibility {t['ew_susceptibility']:.2f}, objective={r['objective_label']}"
                }
                world["explanations"]["ew_decision"] = ew_recommendation
                break
    if ew_recommendation is None:
        world["explanations"]["ew_decision"] = {"selected_target": None, "reason": "No EW target met criteria or EW unavailable."}

    refresh_engagement_state()
    shorads = [a for a in world["assets"] if a["kind"] == "SHORAD" and a.get("ready", True) and a.get("status", "online") == "online"]
    kinetic = [r for r in recs if r["effect"] == "KINETIC"]
    alive_count = len(kinetic)
    if not kinetic:
        return recs, {}, ew_recommendation

    top_priority = max(x["priority"] for x in kinetic)
    candidates = []
    for a in shorads:
        if a["missiles_left"] <= 0:
            continue
        astate = world["engagement_state"]["assets"].get(a["id"], {})
        if astate.get("missile_in_flight"):
            current_target = astate.get("in_flight_to")
            world["explanations"]["pressure_notes"].append(f"{a['id']} remains kinetically committed to {current_target}; generating non-blocking follow-on recommendations only.")
        for r in kinetic:
            target_state = world["engagement_state"]["targets"].get(r["threat_id"], {})
            if target_state.get("in_flight_count", 0) >= target_state.get("desired_salvo", 1):
                world["explanations"]["pressure_notes"].append(f"{r['threat_id']} fire-control hold: sufficient missiles already in flight ({target_state.get('in_flight_count',0)}/{target_state.get('desired_salvo',1)}).")
                continue
            d = distance_to_asset(a["id"], r["threat_id"])
            base_score = r["priority"]
            penalty = doctrine["distance_weight"] * d
            adj = 0.0
            crit_bonus = world["criticality_config"]["criticality_weight"] * r["criticality"]
            tti_bonus = world["criticality_config"]["tti_weight"] * min(1.0, 3.0 / max(r["tti_steps"], 0.25))
            parts = [f"base={base_score:.4f}", f"distance_penalty=-{penalty:.4f}", f"criticality_bonus=+{crit_bonus:.4f}", f"tti_bonus=+{tti_bonus:.4f}", f"objective={r['objective_label']} value={r['objective_value']:.2f}"]
            if r.get("needs_reengagement"):
                ka_bonus = 0.10 + 0.03 * min(3, int(r.get("engagement_attempts", 0)))
                adj += ka_bonus
                parts.append(f"persistent_kill_chain_bonus=+{ka_bonus:.4f}")
            elif r.get("engagement_attempts", 0) == 0:
                first_shot_bonus = 0.04
                adj += first_shot_bonus
                parts.append(f"first_shot_bonus=+{first_shot_bonus:.4f}")
            miss_info = recent_miss_info(r["threat_id"])
            if world["fire_control_config"].get("adaptive_reengagement", True) and miss_info:
                window = int(world["fire_control_config"].get("reengage_same_target_window", 3))
                if miss_info["steps_since_miss"] <= window:
                    bonus = float(world["fire_control_config"].get("reengage_priority_bonus", 0.18)) * max(0.25, 1.0 - 0.2 * miss_info["steps_since_miss"])
                    adj += bonus
                    parts.append(f"reengage_bonus=+{bonus:.4f}")
                    world["explanations"].setdefault("reengagement_notes", []).append(f"{r['threat_id']} prioritized for adaptive re-engagement after miss ({miss_info['steps_since_miss']} step(s) ago).")
                    if a["id"] in miss_info.get("engaged_by", []):
                        same_penalty = float(world["fire_control_config"].get("post_miss_same_launcher_penalty", 0.05))
                        adj -= same_penalty
                        parts.append(f"same_launcher_penalty=-{same_penalty:.4f}")
            if doctrine["prefer_spread"] and len(kinetic) >= len(shorads):
                adj += 0.02
                parts.append("spread_bonus=+0.0200")
            if (not doctrine["prefer_spread"]) and r["priority"] == top_priority:
                adj += 0.03
                parts.append("focus_bonus=+0.0300")
            if r["objective_value"] >= 0.85:
                adj += 0.02
                parts.append("critical_objective_bonus=+0.0200")
            if r["criticality_band"] == "CRITICAL":
                adj += 0.06
                parts.append("critical_band_bonus=+0.0600")
            elif r["criticality_band"] == "HIGH":
                adj += 0.03
                parts.append("high_band_bonus=+0.0300")
            if r["terminal"]:
                adj += 0.05
                parts.append("terminal_bonus=+0.0500")
            if rec_map[r["threat_id"]]["degraded"]:
                adj += 0.015
            score = base_score - penalty + adj + crit_bonus + tti_bonus
            candidates.append({"asset_id": a["id"], "threat_id": r["threat_id"], "priority": r["priority"], "distance_km": round(d, 2), "score": round(score, 4), "reason": " | ".join(parts), "objective_label": r["objective_label"], "objective_value": r["objective_value"], "criticality": r["criticality"], "criticality_band": r["criticality_band"], "tti_steps": r["tti_steps"], "terminal": r["terminal"]})
    candidates.sort(key=lambda x: (-x["score"], x["asset_id"], x["threat_id"]))
    world["explanations"]["candidate_scores"] = candidates

    new_assignments = {}
    used_assets = set()
    target_load = {}
    for c in candidates:
        aid, tid = c["asset_id"], c["threat_id"]
        if aid in used_assets:
            continue
        cap = min(doctrine_max_assets_for_target(tid, alive_count), allocation_cap_for_target(tid, alive_count), world["engagement_state"]["targets"].get(tid, {}).get("desired_salvo", 1))
        in_flight_count = world["engagement_state"]["targets"].get(tid, {}).get("in_flight_count", 0)
        current_commitment = target_load.get(tid, 0) + in_flight_count

        remaining_assets = {x["asset_id"] for x in candidates if x["asset_id"] not in used_assets}
        uncovered_viable_targets = sorted({
            x["threat_id"]
            for x in candidates
            if x["asset_id"] in remaining_assets
            and x["threat_id"] != tid
            and (target_load.get(x["threat_id"], 0) + world["engagement_state"]["targets"].get(x["threat_id"], {}).get("in_flight_count", 0)) < 1
        })

        if world["fire_control_config"].get("coverage_first", True) and current_commitment >= 1:
            dup = coverage_first_duplication_decision(tid, uncovered_viable_targets)
            trace = {
                "asset_id": aid,
                "threat_id": tid,
                "decision": "allow_duplicate" if dup["allowed"] else "block_duplicate",
                "rule": dup["rule"],
                "reason": dup["reason"],
                "desired_salvo": dup["desired_salvo"],
                "current_commitment": current_commitment,
                "uncovered_viable_targets": dup["uncovered_viable_targets"],
            }
            world["explanations"]["coverage_trace"].append(trace)
            world["explanations"]["coverage_first_proof"].append(trace)
            if not dup["allowed"]:
                world["explanations"]["pressure_notes"].append(dup["reason"])
                continue
        else:
            proof = {
                "asset_id": aid,
                "threat_id": tid,
                "decision": "first_launcher",
                "rule": "coverage_first_default",
                "reason": f"first launcher assigned to {tid} under coverage-first default",
                "desired_salvo": world["engagement_state"]["targets"].get(tid, {}).get("desired_salvo", 1),
                "current_commitment": current_commitment,
                "uncovered_viable_targets": uncovered_viable_targets,
            }
            world["explanations"]["coverage_trace"].append(proof)
            world["explanations"]["coverage_first_proof"].append(proof)

        if current_commitment >= cap:
            world["explanations"]["allocation_trace"].append({"asset_id": aid, "threat_id": tid, "decision": "blocked_cap", "cap": cap, "current_commitment": current_commitment})
            continue

        if doctrine["prefer_spread"] and len(kinetic) >= len(shorads) and target_load.get(tid, 0) >= 1 and objective_value(get_threat(tid)) < 0.85:
            world["explanations"]["allocation_trace"].append({"asset_id": aid, "threat_id": tid, "decision": "blocked_doctrine_spread", "reason": "doctrine prefer_spread kept launcher on uncovered targets"})
            continue
        confidence = round(max(0.45, min(0.97, 0.45 + 0.12 * c["score"] - 0.10 * sensor_overload_factor())), 2)
        allocation_reason = c["reason"]
        if current_commitment >= 1:
            last_cov = world["explanations"]["coverage_trace"][-1] if world["explanations"]["coverage_trace"] else {}
            allocation_reason = allocation_reason + f" | anti_overconcentration={last_cov.get('rule','n/a')}"
        new_assignments[aid] = {"to": tid, "confidence": confidence, "reason": allocation_reason, "objective_label": c["objective_label"], "objective_value": c["objective_value"], "criticality": c["criticality"], "criticality_band": c["criticality_band"], "tti_steps": c["tti_steps"], "terminal": c["terminal"]}
        used_assets.add(aid)
        target_load[tid] = target_load.get(tid, 0) + 1
        world["explanations"]["allocation_trace"].append({"asset_id": aid, "threat_id": tid, "decision": "assigned", "current_commitment_before": current_commitment, "current_commitment_after": target_load[tid] + in_flight_count, "cap": cap, "uncovered_viable_targets": uncovered_viable_targets})
        world["explanations"]["asset_decisions"].append({"asset_id": aid, "assigned_to": tid, "score": c["score"], "priority": c["priority"], "distance_km": c["distance_km"], "reason": allocation_reason})
    return recs, new_assignments, ew_recommendation

def queue_recommendations(assignments, ew_recommendation):
    prev_map = {r.get("rec_id"): r for r in world.get("pending_recommendations", [])}
    world["pending_recommendations"] = []
    for aid, rec in assignments.items():
        rec_id = f"{aid}->{rec['to']}"
        prev = prev_map.get(rec_id, {})
        created_step = int(prev.get("created_step", world["step"]))
        world["pending_recommendations"].append({
            "rec_id": rec_id, "action_type": "KINETIC", "asset_id": aid, "target_id": rec["to"],
            "status": prev.get("status", "SUGGESTED") if prev.get("status") in ("PENDING_APPROVAL", "SUGGESTED", "APPROVED") else "SUGGESTED",
            "created_step": created_step, "expires_step": created_step + world["authority_config"]["veto_window_steps"],
            "confidence": rec["confidence"], "reason": rec["reason"], "objective_label": rec["objective_label"], "objective_value": rec["objective_value"], "authority_basis": prev.get("authority_basis", ""),
            "criticality": rec.get("criticality", 0.0), "criticality_band": rec.get("criticality_band", "LOW"), "tti_steps": rec.get("tti_steps", 99.0), "terminal": rec.get("terminal", False),
            "engagement_attempts": world.get("combat_state", {}).get(rec["to"], {}).get("engagement_attempts", 0),
            "fire_control_status": "READY_TO_FIRE",
            "age_steps": max(0, int(world["step"]) - created_step),
        })
    if ew_recommendation:
        rec_id = f"{ew_recommendation['from']}->{ew_recommendation['to']}"
        prev = prev_map.get(rec_id, {})
        created_step = int(prev.get("created_step", world["step"]))
        world["pending_recommendations"].append({
            "rec_id": rec_id, "action_type": "EW", "asset_id": ew_recommendation["from"], "target_id": ew_recommendation["to"],
            "status": prev.get("status", "SUGGESTED") if prev.get("status") in ("PENDING_APPROVAL", "SUGGESTED", "APPROVED") else "SUGGESTED",
            "created_step": created_step, "expires_step": created_step + world["authority_config"]["veto_window_steps"],
            "confidence": ew_recommendation["confidence"], "reason": ew_recommendation["reason"],
            "objective_label": get_objective(get_threat(ew_recommendation["to"])["target_objective"])["label"] if get_threat(ew_recommendation["to"]) else "",
            "objective_value": objective_value(get_threat(ew_recommendation["to"])) if get_threat(ew_recommendation["to"]) else 0.0, "authority_basis": prev.get("authority_basis", ""),
            "criticality": threat_criticality(get_threat(ew_recommendation["to"]))["score"] if get_threat(ew_recommendation["to"]) else 0.0,
            "criticality_band": threat_criticality(get_threat(ew_recommendation["to"]))["band"] if get_threat(ew_recommendation["to"]) else "LOW",
            "tti_steps": threat_criticality(get_threat(ew_recommendation["to"]))["tti_steps"] if get_threat(ew_recommendation["to"]) else 99.0,
            "terminal": threat_criticality(get_threat(ew_recommendation["to"]))["terminal"] if get_threat(ew_recommendation["to"]) else False,
            "fire_control_status": "READY_TO_FIRE",
            "age_steps": max(0, int(world["step"]) - created_step),
        })

def recommendation_is_emergency(rec):
    threat = get_threat(rec["target_id"])
    return bool(threat) and distance_to_objective(threat) <= world["authority_config"]["emergency_distance_km"]

def recommendation_needs_override(rec):
    cfg = world["criticality_config"]
    return (
        (cfg["auto_override_on_terminal"] and rec.get("terminal", False))
        or (cfg["auto_override_on_critical"] and rec.get("criticality_band") == "CRITICAL")
        or (rec.get("criticality", 0.0) >= cfg.get("override_medium_threshold", 0.65))
    )

def evaluate_authority():
    mode = world["authority_mode"]
    thr = world["authority_config"]["auto_conf_threshold"]
    pending_count = 0
    for rec in world["pending_recommendations"]:
        if rec["status"] in ("VETOED", "EXPIRED", "APPROVED"):
            continue
        pending_count += 1
        if mode == "Full Manual":
            rec["status"] = "PENDING_APPROVAL"
            rec["authority_basis"] = "manual mode requires operator approval"
        elif mode == "Approval Required":
            if rec.get("criticality_band") in ("HIGH", "CRITICAL") and (rec.get("tti_steps", 99) <= 2.0 or rec.get("engagement_attempts", 0) >= 1 or rec.get("age_steps", 0) >= 1):
                rec["status"] = "APPROVED"
                rec["authority_basis"] = "leaky-defense safeguard auto-approved"
                log_authority(f"{rec['rec_id']} auto-approved by leaky-defense safeguard", "LEAK_GUARD")
            else:
                rec["status"] = "PENDING_APPROVAL"
                rec["authority_basis"] = "approval required mode"
        elif mode == "Auto If High Confidence":
            if rec["confidence"] >= thr:
                rec["status"] = "APPROVED"
                rec["authority_basis"] = f"auto-approved because confidence {rec['confidence']:.2f} >= threshold {thr:.2f}"
                log_authority(f"{rec['rec_id']} auto-approved", "AUTO_APPROVE")
            else:
                rec["status"] = "PENDING_APPROVAL"
                rec["authority_basis"] = "below confidence threshold"
        elif mode == "Emergency Auto-Fire":
            if world["criticality_config"].get("hard_bind_emergency_autofire", True):
                rec["status"] = "APPROVED"
                if rec.get("terminal", False):
                    rec["authority_basis"] = "hard-bind override: terminal threat auto-fired"
                    log_authority(f"{rec['rec_id']} terminal hard-bind auto-approved", "TERMINAL_OVERRIDE")
                    log_override(f"{rec['rec_id']} terminal hard-bind executed against {rec['target_id']}", "TERMINAL_OVERRIDE")
                elif recommendation_is_emergency(rec):
                    rec["authority_basis"] = "hard-bind override: emergency distance auto-fired"
                    log_authority(f"{rec['rec_id']} emergency-distance hard-bind auto-approved", "EMERGENCY_AUTO")
                    log_override(f"{rec['rec_id']} emergency-distance hard-bind executed against {rec['target_id']}", "EMERGENCY_AUTO")
                elif recommendation_needs_override(rec):
                    rec["authority_basis"] = "hard-bind override: criticality-triggered auto-fired"
                    log_authority(f"{rec['rec_id']} criticality hard-bind auto-approved", "CRITICAL_OVERRIDE")
                    log_override(f"{rec['rec_id']} criticality hard-bind executed against {rec['target_id']}", "CRITICAL_OVERRIDE")
                else:
                    rec["authority_basis"] = "hard-bind auto-fire: approved without confidence gate"
                    log_authority(f"{rec['rec_id']} hard-bind auto-approved", "AUTO_APPROVE")
                    log_override(f"{rec['rec_id']} hard-bind executed against {rec['target_id']}", "AUTO_APPROVE")
            elif recommendation_needs_override(rec) and rec["confidence"] >= world["criticality_config"]["override_confidence_floor"]:
                rec["status"] = "APPROVED"
                if rec.get("terminal", False):
                    rec["authority_basis"] = "critical override: terminal threat auto-approved"
                    log_authority(f"{rec['rec_id']} terminal override auto-approved", "TERMINAL_OVERRIDE")
                    log_override(f"{rec['rec_id']} terminal override executed against {rec['target_id']}", "TERMINAL_OVERRIDE")
                else:
                    rec["authority_basis"] = "critical override: critical target auto-approved"
                    log_authority(f"{rec['rec_id']} critical override auto-approved", "CRITICAL_OVERRIDE")
                    log_override(f"{rec['rec_id']} critical override executed against {rec['target_id']}", "CRITICAL_OVERRIDE")
            elif recommendation_is_emergency(rec):
                rec["status"] = "APPROVED"
                rec["authority_basis"] = "auto-approved due to emergency distance rule"
                log_authority(f"{rec['rec_id']} emergency auto-approved", "EMERGENCY_AUTO")
            elif rec["confidence"] >= thr:
                rec["status"] = "APPROVED"
                rec["authority_basis"] = "auto-approved by confidence threshold"
                log_authority(f"{rec['rec_id']} confidence auto-approved", "AUTO_APPROVE")
            else:
                rec["status"] = "PENDING_APPROVAL"
                rec["authority_basis"] = "pending approval"
    if world["pressure_config"]["operator_overload_autofallback"] and pending_count > world["pressure_config"]["max_pending_before_overload"]:
        for rec in world["pending_recommendations"]:
            if rec["status"] == "PENDING_APPROVAL" and rec["confidence"] >= max(0.70, thr - 0.05):
                rec["status"] = "APPROVED"
                rec["authority_basis"] = "auto-approved due to operator overload fallback"
                log_authority(f"{rec['rec_id']} overload auto-approved", "OVERLOAD_AUTO")
                if rec.get("criticality_band") in ("HIGH", "CRITICAL"):
                    log_override(f"{rec['rec_id']} approved under overload fallback for {rec['criticality_band']} threat", "OVERLOAD_OVERRIDE")
                world["explanations"]["pressure_notes"].append("Operator overload fallback engaged.")
    for rec in world["pending_recommendations"]:
        world["explanations"]["authority_notes"].append(f"{rec['rec_id']} | status={rec['status']} | {rec.get('authority_basis','')} | band={rec.get('criticality_band','LOW')} | tti={rec.get('tti_steps',99.0)}")
        if rec.get("criticality_band") in ("HIGH", "CRITICAL"):
            world["explanations"]["override_notes"].append(f"{rec['rec_id']} tagged {rec.get('criticality_band')} (TTI {rec.get('tti_steps',99.0)} steps).")

def approve_recommendation(rec_id):
    for rec in world["pending_recommendations"]:
        if rec["rec_id"] == rec_id and rec["status"] in ("SUGGESTED", "PENDING_APPROVAL"):
            rec["status"] = "APPROVED"
            rec["authority_basis"] = f"approved by {_effective_operator_name()}"
            log_authority(f"{rec_id} approved by {_effective_operator_name()}", "MANUAL_APPROVE")
            if rec.get("criticality_band") in ("HIGH", "CRITICAL"):
                log_override(f"{rec_id} manually approved for {rec.get('criticality_band')} threat", "MANUAL_OVERRIDE")

def veto_recommendation(rec_id):
    for rec in world["pending_recommendations"]:
        if rec["rec_id"] == rec_id and rec["status"] in ("SUGGESTED", "PENDING_APPROVAL"):
            rec["status"] = "VETOED"
            rec["authority_basis"] = f"vetoed by {_effective_operator_name()}"
            log_authority(f"{rec_id} vetoed by {_effective_operator_name()}", "MANUAL_VETO")
            log_override(f"{rec_id} vetoed by operator", "MANUAL_VETO")

def expire_recommendations():
    chain = _operator_chain()
    esc_state = world.setdefault("authority_escalation_state", {"current_operator": chain[0], "current_level": 0, "last_event_step": -999, "last_title": "", "last_text": "", "active": False})
    for rec in world["pending_recommendations"]:
        rec["age_steps"] = max(0, int(world["step"]) - int(rec.get("created_step", world["step"])))
        if rec["status"] in ("SUGGESTED", "PENDING_APPROVAL") and world["step"] > rec["expires_step"]:
            consequence = world.setdefault("operator_consequence_state", {"last_event_step": -999, "last_title": "", "last_text": "", "severity": "info", "risk_delta_pct": 0.0, "coverage_delta_pct": 0.0, "expected_damage_delta_pct": 0.0, "counterfactual": ""})
            target_id = rec.get("target_id", "unknown threat")
            tti = float(rec.get("tti_steps", 999.0) or 999.0)
            obj = rec.get("objective_label", rec.get("objective_value", "objective"))
            level = int(rec.get("escalation_level", 0) or 0)
            has_next = level + 1 < len(chain)
            if has_next and (tti <= _escalation_threshold_tti() or rec.get("criticality_band") in ("HIGH", "CRITICAL") or str(world.get("configured_authority_mode", world.get("authority_mode", "Approval Required"))) == "Approval Required"):
                next_op = chain[level + 1]
                rec["status"] = "PENDING_APPROVAL"
                rec["escalation_level"] = level + 1
                rec["effective_operator"] = next_op
                rec["authority_basis"] = f"escalated to {next_op} after timeout"
                rec["created_step"] = int(world.get("step", 0))
                rec["expires_step"] = int(world.get("step", 0)) + max(1, int(world.get("authority_config", {}).get("veto_window_steps", 2)))
                esc_state.update({
                    "current_operator": next_op,
                    "current_level": level + 1,
                    "last_event_step": int(world.get("step", 0)),
                    "last_title": "AUTHORITY ESCALATION",
                    "last_text": f"{target_id} escalated from {chain[level]} to {next_op} after timeout at TTI {tti:.1f}.",
                    "active": True,
                })
                log_authority(f"{rec['rec_id']} escalated to {next_op} after timeout", "ESCALATE")
                continue
            metrics = _consequence_metrics(rec)
            consequence.update({"last_event_step": int(world.get("step", 0)), "last_title": "DELAY CONSEQUENCE", "severity": "warning" if tti <= 14 else "info", **metrics})
            if rec.get("criticality_band") in ("HIGH", "CRITICAL") and world.get("authority_config", {}).get("auto_release_after_chain_exhausted", True):
                rec["status"] = "APPROVED"
                rec["authority_basis"] = "expired into auto-approval to prevent leaky defense"
                msg = f"{target_id} remained inside the decision window at TTI {tti:.1f}; safety guard auto-approved to avoid a leak. Risk +{metrics['risk_delta_pct']:.1f}% | coverage -{metrics['coverage_delta_pct']:.1f}% if held."
                consequence.update({"last_text": msg})
                log_authority(f"{rec['rec_id']} expired into leak-prevention auto-approval", "EXPIRE_GUARD")
            else:
                rec["status"] = "EXPIRED"
                rec["authority_basis"] = "expired without operator action"
                msg = f"Approval window expired for {target_id}; target remains active against {obj} with TTI {tti:.1f}. Risk +{metrics['risk_delta_pct']:.1f}% | coverage -{metrics['coverage_delta_pct']:.1f}% | expected damage +{metrics['expected_damage_delta_pct']:.1f}%."
                consequence.update({"last_text": msg})
                log_authority(f"{rec['rec_id']} expired", "EXPIRE")

def apply_approved_recommendations():
    world["assignments"] = {}
    world["engagements"] = []
    world["ew_effects"] = []
    world.setdefault("combat_state", {})
    ensure_combat_state_defaults()
    for rec in world["pending_recommendations"]:
        if rec["status"] != "APPROVED":
            continue
        if rec["action_type"] == "EW":
            ew_asset = get_asset(rec["asset_id"])
            if ew_asset and ew_asset.get("ready", True):
                world["ew_effects"].append({"source": rec["asset_id"], "radius": world["config"]["ew_radius_km"], "active": True, "approved_step": world["step"], "created_step": rec["created_step"]})
                world["engagements"].append({"type": "ew", "from": rec["asset_id"], "to": rec["target_id"], "status": "active"})
                ew_asset["duty_used"] += 1
            continue
        asset = get_asset(rec["asset_id"])
        if not asset or asset.get("status", "online") != "online" or asset.get("missiles_left", 0) <= 0:
            rec["fire_control_status"] = "UNAVAILABLE"
            continue
        hold_reason = fire_control_hold_reason(rec["asset_id"], rec["target_id"])
        if hold_reason:
            if "missile" in hold_reason or "holding fire" in hold_reason or "strict fire-control lock" in hold_reason:
                rec["fire_control_status"] = "QUEUED_IN_FLIGHT"
                rec["queue_reason"] = hold_reason
                world["explanations"]["pressure_notes"].append(f"Queued follow-on: {hold_reason}")
            else:
                rec["fire_control_status"] = "HOLD"
                rec["authority_basis"] = f"{rec.get('authority_basis','')} | fire-control hold"
                world["explanations"]["pressure_notes"].append(hold_reason)
            continue
        if asset and asset.get("ready", True) and asset.get("missiles_left", 0) > 0:
            world["assignments"][rec["asset_id"]] = rec["target_id"]
            world["engagements"].append({"type": "kinetic", "from": rec["asset_id"], "to": rec["target_id"], "status": "launched", "created_step": rec["created_step"], "approved_step": world["step"]})
            asset["missiles_left"] -= 1
            rec["fire_control_status"] = "LAUNCHED"
            flight_steps = max(2, int(world["fire_control_config"].get("missile_base_flight_steps", 3) + 0.30 * distance_to_asset(rec["asset_id"], rec["target_id"])))
            pk0 = 0.0
            world["missiles"].append({
                "id": f"m_{rec['asset_id']}_{rec['target_id']}_{world['step']}",
                "from": rec["asset_id"], "to": rec["target_id"],
                "progress": 0.0, "pk_estimate": pk0,
                "created_step": rec["created_step"], "approved_step": world["step"],
                "flight_steps_total": flight_steps, "flight_steps_elapsed": 0,
                "status": "IN_FLIGHT"
            })
            ensure_combat_state_defaults(rec["target_id"])
            target_state = world["combat_state"].setdefault(rec["target_id"], {})
            target_state["state"] = "MISSILE_IN_FLIGHT"
            target_state["awaiting_assessment"] = True
            target_state["last_shot_step"] = world["step"]
            target_state["engagement_attempts"] = int(target_state.get("engagement_attempts", 0)) + 1
            target_state["needs_reengagement"] = False
            target_state["reengage_after_step"] = world["step"]
            target_state["engaged_by"] = sorted(set(target_state.get("engaged_by", [])) | {rec["asset_id"]})
            asset_state = world["combat_state"].setdefault(rec["asset_id"], {})
            asset_state["last_target"] = rec["target_id"]
            asset_state["last_outcome"] = "LAUNCHED"
            log_event(f"{rec['asset_id']} launched on {rec['target_id']}", "LAUNCH")
            world["explanations"].setdefault("decision_trace", []).append(f"Step {world['step']}: {rec['asset_id']} launched on {rec['target_id']} under {world['authority_mode']} (confidence {rec['confidence']:.2f}).")
            if asset["missiles_left"] <= 0:
                asset["ready"] = False
    refresh_engagement_state()

def swarm_center():
    swarms = [t for t in alive_threats() if t["kind"] == "THREAT:swarm"]
    if not swarms:
        return None
    return (sum(t["x"] for t in swarms)/len(swarms), sum(t["y"] for t in swarms)/len(swarms))

def retarget_threats_to_objectives():
    for t in alive_threats():
        obj = get_objective(t["target_objective"])
        if not obj:
            continue
        dx = obj["x"] - t["x"]; dy = obj["y"] - t["y"]; mag = max((dx*dx + dy*dy) ** 0.5, 0.1)
        t["vx"] += 0.01 * dx / mag; t["vy"] += 0.02 * dy / mag

def apply_swarm_behavior():
    center = swarm_center() or (0.0, 0.0)
    ew_active = bool(world["ew_effects"])
    for t in alive_threats():
        d_obj = distance_to_objective(t); d_ew = distance_to_asset("ew_1", t["id"])
        if t["kind"] != "THREAT:swarm":
            if t.get("behavior") == "loiter":
                obj = get_objective(t["target_objective"])
                if obj: t["vy"] += 0.03 if obj["y"] > t["y"] else -0.03
            continue
        if ew_active and d_ew <= world["config"]["ew_radius_km"] + 0.8:
            t["behavior"] = "evading"; sign = 1 if t["y"] >= center[1] else -1
            t["vy"] += sign * world["config"]["evasion_strength"] * 0.08; t["vx"] *= 0.95
        elif d_obj <= world["config"]["split_trigger_distance_km"]:
            t["behavior"] = "split"; sign = 1 if t["y"] >= get_objective(t["target_objective"])["y"] else -1; t["vy"] += sign * 0.05
        else:
            t["behavior"] = "cohesive"; dy = center[1] - t["y"]; t["vy"] += max(min(dy * 0.03 * world["config"]["swarm_cohesion"], 0.03), -0.03)

def move_threats():
    retarget_threats_to_objectives()
    for t in world["threats"]:
        if not t.get("alive", True):
            continue
        speed_factor = 0.78 if t.get("degraded", False) else 1.0
        if t.get("terrain_masked", False):
            speed_factor *= 0.92
        t["x"] += t.get("vx", -0.3) * speed_factor
        t["y"] += t.get("vy", 0.0) * speed_factor
    enforce_threat_termination()

def apply_ew():
    for ew in world["ew_effects"]:
        sx, sy = get_entity_pos(ew["source"])
        delay = max(0, world["step"] - ew.get("created_step", world["step"]))
        delay_penalty = delay * world["pressure_config"]["decision_delay_pk_penalty_per_step"]
        for t in alive_threats():
            if dist(sx, sy, t["x"], t["y"]) <= ew["radius"] and t["ew_susceptibility"] >= world["config"]["ew_threshold"]:
                roll = random.random()
                disrupt_prob = world["config"]["ew_disrupt_prob"] + 0.15 * (t["ew_susceptibility"] - world["config"]["ew_threshold"]) - delay_penalty
                disrupt_prob = max(0.05, min(0.95, disrupt_prob))
                if roll <= disrupt_prob * 0.45:
                    t["alive"] = False; world["destroyed_count"] += 1; log_event(f"{t['id']} neutralized by EW mission-kill", "EW_KILL")
                elif roll <= disrupt_prob:
                    t["degraded"] = True; t["confidence"] = max(0.35, t.get("confidence", 0.8) - 0.18); t["vx"] *= 0.82; t["vy"] *= 0.82; log_event(f"{t['id']} degraded by EW", "EW_DEGRADE")

def missile_pk(missile, target):
    d = distance_to_asset(missile["from"], target["id"])
    base = world["config"]["base_pk"]
    range_penalty = min(0.22, 0.02 * d)
    altitude_penalty = 0.10 if target.get("altitude_m", 0) > 500 else 0.0
    evade_penalty = 0.14 if target.get("behavior") in ("evading", "adversarial_evade") else 0.0
    split_penalty = 0.06 if target.get("behavior") == "split" else 0.0
    degrade_bonus = 0.12 if target.get("degraded", False) else 0.0
    adversarial_penalty = 0.0
    if target.get("terrain_masked", False):
        adversarial_penalty += 0.05
    if target.get("deception_active", False):
        adversarial_penalty += float(world.get("adversarial_config", {}).get("pk_adversarial_penalty", 0.08))
    adversarial_penalty += min(0.12, 0.08 * float(target.get("maneuver_level", 0.0)))
    crit = threat_criticality(target)
    objective_bonus = 0.04 if objective_value(target) >= 0.85 else 0.0
    criticality_bonus = 0.06 if crit["band"] == "CRITICAL" else (0.03 if crit["band"] == "HIGH" else 0.0)
    terminal_bonus = 0.04 if crit["terminal"] else 0.0
    delay_steps = max(0, missile.get("approved_step", world["step"]) - missile.get("created_step", missile.get("approved_step", world["step"])))
    delay_penalty = delay_steps * world["pressure_config"]["decision_delay_pk_penalty_per_step"]
    overload_penalty = sensor_overload_factor() * world["pressure_config"]["overload_pk_penalty"]
    noise = random.uniform(-world["config"]["uncertainty_noise"], world["config"]["uncertainty_noise"])
    pk = base - range_penalty - altitude_penalty - evade_penalty - split_penalty - delay_penalty - overload_penalty - adversarial_penalty + degrade_bonus + objective_bonus + criticality_bonus + terminal_bonus + noise
    return max(0.05, min(0.95, pk))

def advance_missiles():
    new_list = []
    world.setdefault("combat_state", {})
    ensure_combat_state_defaults()
    for m in world["missiles"]:
        tgt = get_threat(m["to"])
        if not tgt or not tgt.get("alive", True):
            continue
        total = max(1, int(m.get("flight_steps_total", world["fire_control_config"].get("missile_base_flight_steps", 3))))
        m["flight_steps_elapsed"] = m.get("flight_steps_elapsed", 0) + 1
        progress = m["flight_steps_elapsed"] / total
        if tgt.get("behavior") == "evading":
            progress *= 0.92
        m["progress"] = max(world["config"].get("missile_min_progress", 0.18), min(1.0, progress))
        m["pk_estimate"] = missile_pk(m, tgt)
        if m["flight_steps_elapsed"] >= total or m["progress"] >= 1.0:
            m["status"] = "IMPACT"
            log_event(f"{m['from']} impact on {tgt['id']} — resolving outcome", "IMPACT")
            ensure_combat_state_defaults(tgt["id"])
            state = world["combat_state"].setdefault(tgt["id"], {})
            state["last_kill_attempt_step"] = world["step"]
            state["state"] = "ASSESSMENT_PENDING"
            roll = random.random()
            impact_x, impact_y = tgt["x"], tgt["y"]
            if roll <= m["pk_estimate"]:
                tgt["alive"] = False
                world["destroyed_count"] += 1
                state["last_outcome"] = "HIT"
                state["last_action"] = f"{m['from']} impact -> HIT"
                state["next_action"] = "Threat resolved"
                state["awaiting_assessment"] = False
                state["state"] = "RESOLVED"
                state["needs_reengagement"] = False
                state["resolved"] = True
                state["engaged_by"] = []
                world.setdefault("kill_assurance_state", {}).setdefault("resolved_log", []).append({"step": world["step"], "threat_id": tgt["id"], "outcome": "HIT"})
                world.setdefault("impact_markers", []).append({"step": world["step"], "threat_id": tgt["id"], "asset_id": m["from"], "x": impact_x, "y": impact_y, "outcome": "HIT", "label": "HIT"})
                world["explanations"]["outcome_notes"].append(f"{tgt['id']} destroyed by {m['from']}.")
                world["explanations"].setdefault("decision_trace", []).append(f"Step {world['step']}: {m['from']} intercept on {tgt['id']} resolved as HIT; threat removed from the battlespace.")
                log_event(f"{tgt['id']} destroyed by {m['from']}", "KILL")
            else:
                if not tgt.get("degraded", False):
                    tgt["degraded"] = True
                    tgt["confidence"] = max(0.40, tgt.get("confidence", 0.8) - 0.10)
                    log_event(f"{tgt['id']} survived intercept but was degraded", "MISS_DEGRADE")
                else:
                    log_event(f"{tgt['id']} survived intercept", "MISS")
                state["last_outcome"] = "MISS"
                state["last_action"] = f"{m['from']} impact -> MISS"
                state["next_action"] = "Re-engage after cooldown"
                state["awaiting_assessment"] = False
                state["state"] = "REENGAGE_REQUIRED"
                state["needs_reengagement"] = True
                state["resolved"] = False
                state["reengage_after_step"] = world["step"] + int(world.get("kill_chain_config", {}).get("reengage_cooldown_steps", 1))
                world.setdefault("impact_markers", []).append({"step": world["step"], "threat_id": tgt["id"], "asset_id": m["from"], "x": impact_x, "y": impact_y, "outcome": "MISS", "label": "MISS"})
                world["explanations"]["outcome_notes"].append(f"{tgt['id']} survived intercept and was flagged for persistent re-engagement.")
                world["explanations"].setdefault("decision_trace", []).append(f"Step {world['step']}: {m['from']} intercept on {tgt['id']} resolved as MISS; persistent kill chain re-engagement armed for step {state['reengage_after_step']}.")
            for aid in state.get("engaged_by", []):
                world["combat_state"].setdefault(aid, {})["last_outcome"] = state["last_outcome"]
        else:
            m["status"] = "IN_FLIGHT"
            new_list.append(m)
    world["missiles"] = new_list

def update_objective_status():
    for obj in world["objectives"]: obj["status"] = "protected"
    for t in alive_threats():
        obj = get_objective(t["target_objective"])
        if not obj: continue
        d = distance_to_objective(t)
        if d <= 1.0: obj["status"] = "under attack"
        elif d <= 3.0 and obj["status"] != "under attack": obj["status"] = "threatened"

def remove_stale_assignments():
    alive_ids = {t["id"] for t in alive_threats()}
    world["assignments"] = {aid: tid for aid, tid in world["assignments"].items() if tid in alive_ids}

def queue_soft_reengagement_candidates():
    fc = world.get("fire_control_config", {})
    if not fc.get("adaptive_reengagement", True):
        return
    existing_ids = {r.get("rec_id") for r in world.get("pending_recommendations", [])}
    for t in alive_threats():
        tstate = world.get("engagement_state", {}).get("targets", {}).get(t["id"], {})
        if tstate.get("in_flight_count", 0) <= 0:
            continue
        if float(tstate.get("tti_steps", 99.0)) > 8.0:
            continue
        assets = [a for a in world.get("assets", []) if a.get("kind") == "SHORAD" and a.get("status", "online") == "online" and a.get("missiles_left", 0) > 0]
        if not assets:
            continue
        best = min(assets, key=lambda a: distance_to_asset(a["id"], t["id"]))
        rec_id = f"standby::{best['id']}->{t['id']}"
        if rec_id in existing_ids:
            continue
        crit = threat_criticality(t)
        world.setdefault("pending_recommendations", []).append({
            "rec_id": rec_id,
            "action_type": "KINETIC",
            "asset_id": best["id"],
            "target_id": t["id"],
            "status": "SUGGESTED",
            "created_step": world["step"],
            "expires_step": world["step"] + max(1, world["authority_config"].get("veto_window_steps", 2)),
            "confidence": round(max(0.5, min(0.9, 0.58 + 0.08 * crit.get("score", 0.0))), 2),
            "reason": f"Standby second-shot candidate while missile remains in flight to {t['id']}",
            "objective_label": get_objective(t["target_objective"])["label"] if get_objective(t["target_objective"]) else "",
            "objective_value": objective_value(t),
            "authority_basis": "soft kill-assurance standby",
            "criticality": crit.get("score", 0.0),
            "criticality_band": crit.get("band", "LOW"),
            "tti_steps": crit.get("tti_steps", 99.0),
            "terminal": crit.get("terminal", False),
            "engagement_attempts": world.get("combat_state", {}).get(t["id"], {}).get("engagement_attempts", 0),
            "fire_control_status": "STANDBY_SECOND_SHOT",
            "age_steps": 0,
            "queue_reason": "soft_reengagement_candidate",
        })
        world["explanations"].setdefault("reengagement_notes", []).append(
            f"Standby second-shot candidate prepared for {t['id']} while current missile remains in flight."
        )
        existing_ids.add(rec_id)

def _adaptive_breakthrough_selection():
    pending = [r for r in world.get("pending_recommendations", []) if r.get("status") == "APPROVED"]
    if not pending:
        return None
    pending.sort(key=lambda r: (
        1 if r.get("terminal") else 0,
        float(r.get("criticality", 0.0)),
        float(r.get("confidence", 0.0)),
        -float(r.get("tti_steps", 99.0))
    ), reverse=True)
    selected = pending[0]
    selected_target = selected.get("target_id")
    selected_asset = selected.get("asset_id")
    for rec in pending[1:]:
        rec["status"] = "PENDING_APPROVAL"
        rec["authority_basis"] = "adaptive doctrine held for single-strike breakthrough"
        rec["fire_control_status"] = "HELD_FOR_BREAKTHROUGH"
        rec["queue_reason"] = f"single-strike breakthrough reserved for {selected_asset}->{selected_target}"
    world.setdefault("explanations", {}).setdefault("doctrine_notes", []).append(
        f"Adaptive doctrine selected single-strike breakthrough {selected_asset}->{selected_target}."
    )
    log_authority(f"Adaptive doctrine selected single-strike breakthrough {selected_asset}->{selected_target}", "ADAPTIVE_BREAKTHROUGH")
    return selected


def _restore_adaptive_baseline():
    cfg = world.get("adaptive_doctrine_state", {})
    baseline = cfg.get("baseline", {})
    if not baseline:
        return
    world["doctrine_name"] = baseline.get("doctrine_name", world.get("doctrine_name", "Balanced"))
    world["configured_authority_mode"] = baseline.get("configured_authority_mode", world.get("configured_authority_mode", world.get("authority_mode", "Approval Required")))
    world["authority_mode"] = world.get("configured_authority_mode", world.get("authority_mode", "Approval Required"))
    world["authority_config"]["auto_conf_threshold"] = baseline.get("auto_conf_threshold", world["authority_config"].get("auto_conf_threshold", 0.82))
    fc = world.get("fire_control_config", {})
    for k, v in baseline.get("fire_control_config", {}).items():
        fc[k] = v
    cfg["active"] = False
    cfg["reason"] = "Adaptive doctrine restored to baseline after stable engagement activity."
    cfg["activated_step"] = None
    cfg["clear_steps"] = 0
    cfg["trigger"] = ""
    cfg["strategy"] = ""
    cfg["baseline"] = {}
    cfg["last_shift_step"] = int(world.get("step", 0))
    cfg["last_shift_banner"] = "Doctrine restored to baseline"
    world.setdefault("explanations", {}).setdefault("doctrine_notes", []).append("Adaptive doctrine restored to baseline.")
    log_authority("Adaptive doctrine restored to baseline after stable activity.", "ADAPTIVE_RESTORE")


def _adaptive_threat_snapshot():
    alive = alive_threats()
    risks = []
    for t in alive:
        crit = threat_criticality(t)
        risks.append({
            "threat_id": t.get("id"),
            "band": crit.get("band", "LOW"),
            "score": float(crit.get("score", 0.0)),
            "tti_steps": float(crit.get("tti_steps", 999.0)),
            "objective": t.get("target_objective", "?"),
            "kind": str(t.get("kind", "")),
        })
    risks.sort(key=lambda r: (-r["score"], r["tti_steps"]))
    return risks


def _adaptive_pressure_score(risks, actionable_count: int) -> float:
    state = world.setdefault("adaptive_doctrine_state", {})
    breakdown = {
        "top_threat": 0.0,
        "tti_urgency": 0.0,
        "swarm_density": 0.0,
        "queue_load": 0.0,
        "ammo_scarcity": 0.0,
        "expiry_friction": 0.0,
    }
    score = 0.0
    if risks:
        top = risks[0]
        breakdown["top_threat"] = min(0.45, float(top["score"]) * 0.45)
        score += breakdown["top_threat"]
        if top["tti_steps"] <= 12:
            breakdown["tti_urgency"] += 0.20
        if top["tti_steps"] <= 8:
            breakdown["tti_urgency"] += 0.15
        score += breakdown["tti_urgency"]
    swarm_count = len([r for r in risks if "swarm" in r.get("kind", "")])
    if swarm_count >= 4:
        breakdown["swarm_density"] = 0.12
    elif swarm_count >= 3:
        breakdown["swarm_density"] = 0.07
    score += breakdown["swarm_density"]
    breakdown["queue_load"] = min(0.18, actionable_count * 0.08)
    score += breakdown["queue_load"]
    ammo_total = sum(int(a.get("missiles_left", 0)) for a in world.get("assets", []) if a.get("kind") == "SHORAD")
    if ammo_total <= 3:
        breakdown["ammo_scarcity"] = 0.10 if ammo_total > 1 else 0.16
    score += breakdown["ammo_scarcity"]
    current_step = int(world.get("step", 0))
    recent_expiries = 0
    expiry_window = int(world.get("adaptive_doctrine_config", {}).get("expiry_window_steps", 3))
    for item in reversed(world.get("authority_log", [])):
        if not str(item.get("type", "")).startswith("EXPIRE"):
            continue
        if int(item.get("step", -999)) < current_step - expiry_window:
            break
        recent_expiries += 1
    if recent_expiries:
        breakdown["expiry_friction"] = min(0.14, 0.07 * recent_expiries)
        score += breakdown["expiry_friction"]
    state["pressure_breakdown"] = {k: round(v, 3) for k, v in breakdown.items()}
    return round(min(1.0, score), 3)


def _apply_adaptive_profile(profile: str, reason: str, trigger: str):
    state = world.setdefault("adaptive_doctrine_state", {})
    if not state.get("baseline"):
        state["baseline"] = {
            "doctrine_name": world.get("doctrine_name"),
            "configured_authority_mode": world.get("configured_authority_mode", world.get("authority_mode")),
            "auto_conf_threshold": world.get("authority_config", {}).get("auto_conf_threshold", 0.82),
            "fire_control_config": {
                "hold_if_missile_in_flight": world.get("fire_control_config", {}).get("hold_if_missile_in_flight", True),
                "one_target_per_launcher": world.get("fire_control_config", {}).get("one_target_per_launcher", True),
                "strict_fire_control_lock": world.get("fire_control_config", {}).get("strict_fire_control_lock", True),
                "coverage_first": world.get("fire_control_config", {}).get("coverage_first", True),
                "allow_salvo_on_terminal": world.get("fire_control_config", {}).get("allow_salvo_on_terminal", True),
                "allow_salvo_on_high_value": world.get("fire_control_config", {}).get("allow_salvo_on_high_value", True),
            },
        }
    fc = world.get("fire_control_config", {})
    auth_cfg = world.get("authority_config", {})
    if profile == "BREAKTHROUGH":
        world["doctrine_name"] = "Aggressive"
        world["configured_authority_mode"] = "Emergency Auto-Fire"
        world["authority_mode"] = "Emergency Auto-Fire"
        auth_cfg["auto_conf_threshold"] = min(float(auth_cfg.get("auto_conf_threshold", 0.82)), 0.55)
        fc["coverage_first"] = True
        fc["strict_fire_control_lock"] = False
        fc["hold_if_missile_in_flight"] = False
        fc["one_target_per_launcher"] = True
        fc["allow_salvo_on_terminal"] = True
        fc["allow_salvo_on_high_value"] = True
        strategy = "single_strike_breakthrough"
        shift_summary = "Aggressive doctrine and emergency auto-fire enabled for breakthrough protection."
    elif profile == "SURGE":
        world["doctrine_name"] = "Aggressive"
        world["configured_authority_mode"] = state.get("baseline", {}).get("configured_authority_mode", world.get("configured_authority_mode", "Approval Required"))
        world["authority_mode"] = world["configured_authority_mode"]
        auth_cfg["auto_conf_threshold"] = min(float(auth_cfg.get("auto_conf_threshold", 0.82)), 0.65)
        fc["coverage_first"] = True
        fc["strict_fire_control_lock"] = False
        fc["hold_if_missile_in_flight"] = True
        fc["one_target_per_launcher"] = True
        fc["allow_salvo_on_terminal"] = True
        fc["allow_salvo_on_high_value"] = False
        strategy = "swarm_surge_distribution"
        shift_summary = "Aggressive allocation with wider spread enabled for swarm surge conditions."
    elif profile == "AMMO_GUARD":
        world["doctrine_name"] = "Terminal Defense"
        world["configured_authority_mode"] = state.get("baseline", {}).get("configured_authority_mode", world.get("configured_authority_mode", "Approval Required"))
        world["authority_mode"] = world["configured_authority_mode"]
        auth_cfg["auto_conf_threshold"] = max(float(auth_cfg.get("auto_conf_threshold", 0.82)), 0.78)
        fc["coverage_first"] = True
        fc["strict_fire_control_lock"] = True
        fc["hold_if_missile_in_flight"] = True
        fc["one_target_per_launcher"] = True
        fc["allow_salvo_on_terminal"] = False
        fc["allow_salvo_on_high_value"] = False
        strategy = "ammo_conservation_terminal_focus"
        shift_summary = "Terminal-defense posture engaged to conserve effectors and protect critical objectives."
    else:
        return
    state["active"] = True
    state["profile"] = profile
    state["reason"] = reason
    state["trigger"] = trigger
    state["strategy"] = strategy
    state["activated_step"] = int(world.get("step", 0))
    state["clear_steps"] = 0
    state["last_shift_summary"] = shift_summary
    state["last_shift_step"] = int(world.get("step", 0))
    state["last_shift_banner"] = shift_summary
    world.setdefault("explanations", {}).setdefault("doctrine_notes", []).append(f"Adaptive doctrine engaged [{profile}]: {reason}")
    log_authority(f"Adaptive doctrine [{profile}] engaged: {reason}", "ADAPTIVE_DOCTRINE")


def evaluate_adaptive_doctrine():
    adc = world.get("adaptive_doctrine_config", {})
    state = world.setdefault("adaptive_doctrine_state", {})
    if not adc.get("enabled", True):
        return
    current_step = int(world.get("step", 0))
    risks = _adaptive_threat_snapshot()
    actionable = [r for r in world.get("pending_recommendations", []) if r.get("status") in ("PENDING_APPROVAL", "SUGGESTED")]
    missiles = len(world.get("missiles", []))
    has_assignments = bool(world.get("assignments"))
    ammo_total = sum(int(a.get("missiles_left", 0)) for a in world.get("assets", []) if a.get("kind") == "SHORAD")
    if risks and missiles == 0 and (not has_assignments):
        state["no_assignment_streak"] = int(state.get("no_assignment_streak", 0)) + 1
    else:
        state["no_assignment_streak"] = 0
    pressure = _adaptive_pressure_score(risks, len(actionable))
    state["last_pressure_score"] = pressure
    expiry_window = int(adc.get("expiry_window_steps", 3))
    expiry_trigger = int(adc.get("expiry_trigger_count", 2))
    recent_expiries = 0
    for item in reversed(world.get("authority_log", [])):
        if item.get("type") != "EXPIRE":
            continue
        if int(item.get("step", -999)) < current_step - expiry_window:
            break
        recent_expiries += 1

    if not state.get("active"):
        if current_step < int(adc.get("min_step_before_activation", 3)):
            return
        trigger = None
        profile = None
        reason = None
        top = risks[0] if risks else None
        swarm_count = len([r for r in risks if "swarm" in r.get("kind", "")])
        if top and top.get("tti_steps", 999.0) <= float(adc.get("high_threat_tti_steps", 12)) and pressure >= 0.62:
            trigger = "terminal_breakthrough"
            profile = "BREAKTHROUGH"
            reason = f"Top threat {top['threat_id']} closing on {top['objective']} in {top['tti_steps']:.1f} steps under high pressure {pressure:.2f}."
        elif (len(actionable) >= int(adc.get("queue_pressure_threshold", 2)) and swarm_count >= max(3, int(adc.get("swarm_surge_threshold", 4)) - 1)) or (swarm_count >= max(3, int(adc.get("swarm_surge_threshold", 4)) - 1) and len([r for r in risks if float(r.get("tti_steps", 999.0)) <= float(adc.get("high_threat_tti_steps", 12)) + 2]) >= 2):
            trigger = "swarm_surge"
            profile = "SURGE"
            reason = f"Queue pressure {len(actionable)} with swarm density {swarm_count} triggered wider aggressive allocation."
        elif ammo_total <= int(adc.get("ammo_guard_threshold", 3)) and len(risks) >= 2:
            trigger = "ammo_guard"
            profile = "AMMO_GUARD"
            reason = f"Remaining interceptor stock {ammo_total} requires terminal-defense conservation logic."
        elif int(state.get("no_assignment_streak", 0)) >= int(adc.get("stagnation_steps", 2)):
            trigger = "stagnation"
            profile = "BREAKTHROUGH"
            reason = f"No valid assignments for {state['no_assignment_streak']} consecutive steps."
        elif recent_expiries >= expiry_trigger:
            trigger = "expiry_detected"
            profile = "BREAKTHROUGH"
            reason = f"{recent_expiries} recent recommendation expiries signalled decision paralysis."
        if profile:
            _apply_adaptive_profile(profile, reason, trigger)
        return

    # active: decide whether to sustain, rotate profile, or restore
    profile = state.get("profile", "BREAKTHROUGH")
    top = risks[0] if risks else None
    if profile != "AMMO_GUARD" and ammo_total <= int(adc.get("ammo_guard_threshold", 3)) and len(risks) >= 2:
        _apply_adaptive_profile("AMMO_GUARD", f"Interceptor stock dropped to {ammo_total}; switching to terminal-defense conservation.", "ammo_guard")
        return
    if profile == "SURGE" and top and top.get("tti_steps", 999.0) <= float(adc.get("high_threat_tti_steps", 12)) and pressure >= 0.62:
        _apply_adaptive_profile("BREAKTHROUGH", f"Surge conditions converted into breakthrough risk on {top['threat_id']} ({top['tti_steps']:.1f} steps).", "terminal_breakthrough")
        return
    if missiles > 0 or has_assignments:
        state["clear_steps"] = int(state.get("clear_steps", 0)) + 1
    else:
        state["clear_steps"] = 0
    sustain_pressure = pressure >= 0.45 or len(actionable) >= 1 or (top and top.get("tti_steps", 999.0) <= 14)
    if sustain_pressure:
        state["clear_steps"] = 0
    if int(state.get("clear_steps", 0)) >= int(adc.get("restore_clear_steps", 2)):
        _restore_adaptive_baseline()


def step_world(n=1):
    for _ in range(n):
        step_started = time.perf_counter()
        world["step"] += 1
        reset_explanations()
        apply_degradation_state()
        update_coverage_state()
        refresh_engagement_state()
        update_asset_pressure_state()
        expire_recommendations()
        evaluate_adaptive_doctrine()
        apply_swarm_behavior()
        apply_adversarial_battlefield()
        move_threats()
        recs, assignments, ew_recommendation = build_candidate_assignments()
        queue_recommendations(assignments, ew_recommendation)
        evaluate_authority()
        if world.get("adaptive_doctrine_state", {}).get("active"):
            _adaptive_breakthrough_selection()
        queue_soft_reengagement_candidates()
        apply_approved_recommendations()
        apply_ew()
        advance_missiles()
        update_kill_assurance_state()
        refresh_engagement_state()
        update_objective_status()
        remove_stale_assignments()
        actionable_pending = len([r for r in world['pending_recommendations'] if r.get('status') in ('PENDING_APPROVAL', 'SUGGESTED')])
        world["explanations"]["step_summary"] = f"{actionable_pending} actionable | {len([r for r in world['pending_recommendations'] if r['status']=='APPROVED'])} approved | authority={world['authority_mode']}"
        world.setdefault("runtime_metrics", {})["last_step_time_s"] = round(time.perf_counter() - step_started, 4)
        world["history"].append({
            "step": world["step"], "active_threats": len(alive_threats()), "assignments": deepcopy(world["assignments"]),
            "authority_mode": world["authority_mode"], "pending": deepcopy(world["pending_recommendations"])
        })



def assets_health_df():
    rows = []
    for a in world.get("assets", []):
        rows.append({
            "asset_id": a["id"],
            "kind": a.get("kind"),
            "status": a.get("status", "online"),
            "ready": a.get("ready", False),
            "missiles_left": a.get("missiles_left", None),
            "reserve_missiles": a.get("reserve_missiles", None),
            "reload_counter": a.get("reload_counter", None),
        })
    return pd.DataFrame(rows)


def coverage_df():
    state = world.get("coverage_state", {})
    return pd.DataFrame([{
        "integrity_pct": state.get("integrity_pct", 100),
        "gap_detected": state.get("gap_detected", False),
        "gap_assets": ", ".join(state.get("gap_assets", [])),
        "notes": " | ".join(state.get("notes", [])),
    }])

def build_tracks_df():
    rows = []
    for a in world["assets"]:
        rows.append({"id": a["id"], "x": a["x"], "y": a["y"], "kind": a["kind"], "behavior": f"ready={a.get('ready',True)}", "degraded": False, "confidence": 1.0})
    for o in world["objectives"]:
        rows.append({"id": o["id"], "x": o["x"], "y": o["y"], "kind": f"OBJECTIVE:{o['status']}", "behavior": o["label"], "degraded": False, "confidence": o["value"]})
    for t in world["threats"]:
        if t.get("alive", True):
            rows.append({"id": t["id"], "x": t["x"], "y": t["y"], "kind": t["kind"], "behavior": t.get("behavior","unknown"), "degraded": t.get("degraded",False), "confidence": t.get("confidence",0.0)})
    df = pd.DataFrame(rows)
    if df.empty: return df
    color_map = {"THREAT:swarm":"#e74c3c","THREAT:loitering":"#f39c12","SHORAD":"#2e86de","EW":"#8e44ad","SENSOR":"#16a085","OBJECTIVE:protected":"#7f8c8d","OBJECTIVE:threatened":"#f1c40f","OBJECTIVE:under attack":"#c0392b"}
    symbol_map = {"THREAT:swarm":"circle","THREAT:loitering":"circle-open","SHORAD":"triangle-up","EW":"square","SENSOR":"diamond","OBJECTIVE:protected":"star","OBJECTIVE:threatened":"star-square","OBJECTIVE:under attack":"hexagram"}
    df["color"] = df["kind"].map(color_map).fillna("gray")
    df["symbol"] = df["kind"].map(symbol_map).fillna("circle")
    df["size"] = df.apply(lambda row: 14 if str(row["kind"]).startswith("OBJECTIVE") else (13 if row["degraded"] else (16 if row["kind"] in ("SHORAD","EW","SENSOR") else 11)), axis=1)
    return df

def add_circle(fig, x, y, r, line_color, fill_color):
    fig.add_shape(type="circle", x0=x-r, y0=y-r, x1=x+r, y1=y+r, line=dict(color=line_color, width=1), fillcolor=fill_color, layer="below")

def render_battlefield():
    fig = go.Figure()

    def cycle_position(idx: int, options: list[str]) -> str:
        return options[idx % len(options)]

    add_circle(fig, 0.0, 0.0, world["config"]["defended_radius_km"], "rgba(60,60,60,0.5)", "rgba(120,120,120,0.05)")
    for a in world.get("assets", []):
        if a.get("kind") == "SHORAD" and a.get("status") in ("offline", "disconnected") and world.get("degradation_config", {}).get("show_coverage_gap", True):
            fig.add_shape(type="circle", x0=a["x"]-1.4, y0=a["y"]-1.4, x1=a["x"]+1.4, y1=a["y"]+1.4, line=dict(color="rgba(220,53,69,0.8)", width=2, dash="dash"), fillcolor="rgba(220,53,69,0.06)")

    if not world.get("assets"):
        st.warning("No assets found in state")
    if not world.get("threats"):
        st.warning("No threats found in state")

    for ew in world.get("ew_effects", []):
        x, y = get_entity_pos(ew["source"])
        if x is not None and y is not None:
            add_circle(fig, x, y, ew["radius"], "rgba(142,68,173,0.7)", "rgba(142,68,173,0.10)")

    for t in alive_threats():
        obj = get_objective(t["target_objective"])
        if obj:
            fig.add_trace(go.Scatter(
                x=[t["x"], obj["x"]], y=[t["y"], obj["y"]], mode="lines",
                line=dict(color="rgba(120,120,120,0.38)", width=1.2, dash="dot"),
                showlegend=False, hoverinfo="skip"
            ))
        if t.get("track_noise_km", 0.0) > 0:
            add_circle(fig, t["x"], t["y"], t.get("track_noise_km", 0.0), "rgba(255,165,0,0.35)", "rgba(255,165,0,0.05)")

    objective_styles = {
        "hq": dict(size=16, color="#7f8c8d", symbol="star", text="top center"),
        "default": dict(size=13, color="#7f8c8d", symbol="star", text="top center"),
    }
    for o in world.get("objectives", []):
        sty = objective_styles.get(o["id"], objective_styles["default"])
        fig.add_trace(go.Scatter(
            x=[o["x"]], y=[o["y"]], mode="markers+text", text=[o["id"]],
            textposition=sty["text"],
            marker=dict(size=sty["size"], color=sty["color"], symbol=sty["symbol"], line=dict(width=1, color="black")),
            name="Objectives", legendgroup="Objectives", showlegend=(o is world.get("objectives", [None])[0]),
            hovertext=f"{o['label']}<br>value={o['value']:.2f}<br>status={o['status']}", hoverinfo="text"
        ))

    asset_styles = {
        "SHORAD": dict(color="#2e86de", symbol="triangle-up", size=15),
        "EW": dict(color="#8e44ad", symbol="square", size=14),
        "SENSOR": dict(color="#16a085", symbol="diamond", size=14),
    }
    asset_positions = ["top center", "bottom center", "middle right", "middle left"]
    for i, a in enumerate(world.get("assets", [])):
        sty = asset_styles.get(a["kind"], dict(color="gray", symbol="circle", size=12)).copy()
        if a.get("status") in ("offline", "disconnected"):
            sty["color"] = "#95a5a6"
        hover = f"{a['id']}<br>{a['kind']}<br>ready={a.get('ready', True)}"
        if a["kind"] == "SHORAD":
            hover += f"<br>missiles_left={a.get('missiles_left', 0)}<br>reserve_missiles={a.get('reserve_missiles', 0)}<br>status={a.get('status', 'online')}"
        fig.add_trace(go.Scatter(
            x=[a["x"]], y=[a["y"]], mode="markers+text", text=[a["id"]], textposition=cycle_position(i, asset_positions),
            marker=dict(size=sty["size"], color=sty["color"], symbol=sty["symbol"], line=dict(width=1, color="black")),
            textfont=dict(size=11),
            name=a["kind"], legendgroup=a["kind"], showlegend=(i == next((j for j,x in enumerate(world.get("assets", [])) if x["kind"] == a["kind"]), i)),
            hovertext=hover, hoverinfo="text"
        ))

    threat_styles = {
        "THREAT:swarm": dict(color="#e74c3c", symbol="circle", size=11),
        "THREAT:loitering": dict(color="#f39c12", symbol="circle-open", size=12),
    }
    alive = alive_threats()
    threat_positions = ["top center", "bottom center", "middle right", "middle left"]
    ranked = []
    for t in alive:
        crit = threat_criticality(t)
        ranked.append((t["id"], crit.get("score", 0.0), crit.get("band", "LOW"), crit.get("tti_steps", 999.0)))
    ranked.sort(key=lambda x: (-x[1], x[3]))
    rank_map = {tid: idx+1 for idx, (tid, _, _, _) in enumerate(ranked)}
    band_map = {tid: band for tid, _, band, _ in ranked}
    for i, t in enumerate(alive):
        sty = threat_styles.get(t["kind"], dict(color="red", symbol="circle", size=10)).copy()
        rank = rank_map.get(t["id"], 99)
        band = band_map.get(t["id"], "LOW")
        line_color = "black"
        line_width = 1
        if rank == 1:
            sty["size"] += 5
            line_color = "#b91c1c"
            line_width = 3
            add_circle(fig, t["x"], t["y"], 0.28, "rgba(220,38,38,0.55)", "rgba(220,38,38,0.08)")
        elif rank == 2:
            sty["size"] += 3
            line_color = "#ea580c"
            line_width = 2
            add_circle(fig, t["x"], t["y"], 0.22, "rgba(249,115,22,0.45)", "rgba(249,115,22,0.06)")
        hover = f"{t['id']}<br>{t['kind']}<br>target={t['target_objective']}<br>confidence={t.get('confidence', 0):.2f}<br>priority_rank={rank}<br>criticality_band={band}"
        label = "" if rank > 3 else (t["id"] if rank == 3 else f"{t['id']} ★")
        fig.add_trace(go.Scatter(
            x=[t["x"]], y=[t["y"]], mode="markers+text", text=[label], textposition=cycle_position(i, threat_positions),
            marker=dict(size=sty["size"], color=sty["color"], symbol=sty["symbol"], line=dict(width=line_width, color=line_color)),
            textfont=dict(size=11),
            name=t["kind"], legendgroup=t["kind"], showlegend=(i == next((j for j,x in enumerate(alive) if x["kind"] == t["kind"]), i)),
            hovertext=hover, hoverinfo="text"
        ))

    for t in alive:
        if t.get("terrain_masked") or t.get("deception_active"):
            radius = max(0.18, float(t.get("track_noise_km", 0.0)) + 0.08)
            color = "rgba(241,196,15,0.30)" if t.get("terrain_masked") else "rgba(231,76,60,0.22)"
            add_circle(fig, t["x"], t["y"], radius, color, "rgba(0,0,0,0)")

    for rec in world.get("pending_recommendations", []):
        status = rec.get("status", "")
        fire_state = str(rec.get("fire_control_status", ""))
        if status not in ("PENDING_APPROVAL", "SUGGESTED", "APPROVED"):
            continue
        x1, y1 = get_entity_pos(rec.get("asset_id"))
        x2, y2 = get_entity_pos(rec.get("target_id"))
        if None in (x1, y1, x2, y2):
            continue
        if status in ("PENDING_APPROVAL", "SUGGESTED"):
            color = "rgba(245,158,11,0.72)"
            dash = "dash"
            width = 2.0
        elif fire_state.startswith("QUEUED") or fire_state == "STANDBY_SECOND_SHOT":
            color = "rgba(37,99,235,0.62)"
            dash = "dash"
            width = 2.2
        else:
            continue
        fig.add_trace(go.Scatter(
            x=[x1, x2], y=[y1, y2], mode="lines",
            line=dict(color=color, width=width, dash=dash),
            showlegend=False, hoverinfo="skip"
        ))

    for e in world.get("engagements", []):
        x1, y1 = get_entity_pos(e["from"])
        x2, y2 = get_entity_pos(e["to"])
        if None in (x1, y1, x2, y2):
            continue
        target_state = world.get("combat_state", {}).get(e["to"], {})
        color = "rgba(46,134,222,0.78)" if e["type"] == "kinetic" else "rgba(142,68,173,0.82)"
        dash = "dash" if target_state.get("needs_reengagement") else "solid"
        width = 3.2 if target_state.get("needs_reengagement") else 2.3
        fig.add_trace(go.Scatter(x=[x1, x2], y=[y1, y2], mode="lines", line=dict(color=color, width=width, dash=dash), showlegend=False, hoverinfo="skip"))
        if target_state.get("needs_reengagement"):
            xm = x1 + (x2 - x1) * 0.55
            ym = y1 + (y2 - y1) * 0.55
            fig.add_trace(go.Scatter(x=[xm], y=[ym], mode="text", text=["RE-ENGAGE"], textposition="top center", textfont=dict(color="#d35400", size=11), showlegend=False, hoverinfo="skip"))

    missile_positions = ["top right", "bottom left", "top left", "bottom right"]
    for i, m in enumerate(world.get("missiles", [])):
        x1, y1 = get_entity_pos(m["from"])
        x2, y2 = get_entity_pos(m["to"])
        if None in (x1, y1, x2, y2):
            continue
        p = m.get("progress", 0)
        xm = x1 + (x2 - x1) * p
        ym = y1 + (y2 - y1) * p
        fig.add_trace(go.Scatter(
            x=[xm], y=[ym], mode="markers",
            marker=dict(size=8, color="#111827", symbol="x"), showlegend=False,
            hovertext=f"{m['from']} -> {m['to']}<br>status={m.get('status','IN_FLIGHT')}<br>pk={m.get('pk_estimate',0):.2f}", hoverinfo="text"
        ))

    impact_positions = {"HIT": ["top right", "bottom left"], "MISS": ["bottom right", "top left"]}
    for i, mark in enumerate([mk for mk in world.get("impact_markers", []) if world.get("step", 0) - mk.get("step", 0) <= 3]):
        color = "#27ae60" if mark.get("outcome") == "HIT" else "#c0392b"
        symbol = "circle" if mark.get("outcome") == "HIT" else "x"
        pos = cycle_position(i, impact_positions.get(mark.get("outcome"), ["top center"]))
        fig.add_trace(go.Scatter(
            x=[mark["x"]], y=[mark["y"]], mode="markers+text", text=[mark.get("outcome", "")], textposition=pos,
            marker=dict(size=13, color=color, symbol=symbol, line=dict(width=1, color="black")), textfont=dict(size=11), showlegend=False,
            hovertext=f"{mark.get('threat_id')} resolved as {mark.get('outcome')} by {mark.get('asset_id')} at step {mark.get('step')}", hoverinfo="text"
        ))

    fig.update_layout(
        title="Battlefield picture",
        height=580,
        xaxis_title="",
        yaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, font=dict(size=10)),
        margin=dict(l=10, r=10, t=48, b=8),
        hoverlabel=dict(bgcolor="white"),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_xaxes(range=[-2.5, 14], zeroline=False, showticklabels=False, gridcolor="rgba(148,163,184,0.10)")
    fig.update_yaxes(range=[-4.5, 4.5], scaleanchor="x", scaleratio=1, zeroline=False, showticklabels=False, gridcolor="rgba(148,163,184,0.10)")
    return fig

def pending_df():
    return pd.DataFrame(world["pending_recommendations"]) if world["pending_recommendations"] else pd.DataFrame(columns=["rec_id","action_type","asset_id","target_id","status","confidence","authority_basis"])

def assets_pressure_df():
    rows = []
    for a in world["assets"]:
        row = {"asset_id": a["id"], "kind": a["kind"], "ready": a.get("ready", True)}
        if a["kind"] == "SHORAD":
            row["missiles_left"] = a.get("missiles_left", 0); row["reload_counter"] = a.get("reload_counter", 0)
        if a["kind"] == "EW":
            row["duty_used"] = a.get("duty_used", 0); row["cooldown_counter"] = a.get("cooldown_counter", 0)
        rows.append(row)
    return pd.DataFrame(rows)


def kill_chain_df():
    rows = []
    for t in world.get("threats", []):
        state = world.get("combat_state", {}).get(t["id"], {})
        if not t.get("alive", True) and not state:
            continue
        next_action = state.get("next_action", "Threat resolved" if not t.get("alive", True) else ("Re-engage" if state.get("needs_reengagement") else "Monitor"))
        rows.append({
            "threat_id": t["id"],
            "alive": t.get("alive", True),
            "status": state.get("state", "ACTIVE" if t.get("alive", True) else "RESOLVED"),
            "attempts": state.get("engagement_attempts", 0),
            "last_outcome": state.get("last_outcome"),
            "last_action": state.get("last_action", ""),
            "next_action": next_action,
            "reengage_after_step": state.get("reengage_after_step", 0),
            "engaged_by": ", ".join(state.get("engaged_by", [])) if state.get("engaged_by") else "",
        })
    return pd.DataFrame(rows)


def decision_trace_df():
    rows = []
    for idx, line in enumerate(world.get("explanations", {}).get("decision_trace", []), start=1):
        rows.append({"seq": idx, "trace": line})
    return pd.DataFrame(rows)



def engagement_targets_df():
    targets = world.get("engagement_state", {}).get("targets", {})
    return pd.DataFrame([{"target_id": k, **v} for k, v in targets.items()])


def engagement_assets_df():
    assets = world.get("engagement_state", {}).get("assets", {})
    return pd.DataFrame([{"asset_id": k, **v} for k, v in assets.items()])


def snapshot_world_state(world_state=None):
    source = world if world_state is None else world_state
    return deepcopy(source)


def _shadow_profile_params(profile):
    profile = profile or "Coverage-First AI"
    if profile == "Aggressive AI":
        return {"doctrine_name": "Aggressive", "authority_mode": "Auto If High Confidence", "auto_conf_threshold": 0.74, "default_confidence_bias": 0.04}
    if profile == "Conservative AI":
        return {"doctrine_name": "Strict Deconfliction", "authority_mode": "Approval Required", "auto_conf_threshold": 0.90, "default_confidence_bias": -0.04}
    return {"doctrine_name": "Balanced", "authority_mode": "Approval Required", "auto_conf_threshold": 0.82, "default_confidence_bias": 0.00}


def _summarize_pending_recommendations(pending):
    rows = []
    for rec in pending or []:
        rows.append({
            "rec_id": rec.get("rec_id"),
            "action_type": rec.get("action_type"),
            "asset_id": rec.get("asset_id"),
            "target_id": rec.get("target_id"),
            "status": rec.get("status"),
            "confidence": rec.get("confidence", 0.0),
            "criticality_band": rec.get("criticality_band", "LOW"),
            "authority_basis": rec.get("authority_basis", ""),
            "reason": rec.get("reason", ""),
        })
    return rows




def _build_shadow_synthetic_rec(asset_id, threat, profile, confidence_bias=0.0, tuning=0.0):
    crit = threat_criticality(threat)
    base_conf = 0.54 + 0.10 * crit.get("score", 0.0) + confidence_bias
    confidence = max(0.35, min(0.98, base_conf))
    obj = get_objective(threat.get("target_objective"))
    objective_label = obj["label"] if obj else "Unknown"
    objective_value = obj["value"] if obj else 0.0
    return {
        "rec_id": f"{asset_id}->{threat['id']}",
        "action_type": "KINETIC",
        "asset_id": asset_id,
        "target_id": threat["id"],
        "status": "PENDING_APPROVAL",
        "confidence": round(confidence, 2),
        "criticality_band": crit.get("band", "LOW"),
        "authority_basis": "shadow divergence advisory",
        "reason": f"shadow divergence advisory | profile={profile} | tuning={tuning:.2f} | objective={objective_label} value={objective_value:.2f}",
        "criticality": crit.get("score", 0.0),
        "tti_steps": crit.get("tti_steps", 99.0),
        "objective_label": objective_label,
        "objective_value": objective_value,
        "terminal": crit.get("terminal", False),
    }


def _apply_shadow_divergence(sim_world, actions, profile, tuning, confidence_bias):
    if not actions:
        return actions
    for rec in actions:
        rec["confidence"] = round(max(0.35, min(0.98, float(rec.get("confidence", 0.0)) + confidence_bias)), 2)
    if tuning <= 0.0:
        return actions

    alive = [deepcopy(t) for t in sim_world.get("threats", []) if t.get("alive", True)]
    targeted = {r.get("target_id") for r in actions if r.get("target_id")}
    if profile == "Aggressive AI":
        alt = [t for t in sorted(alive, key=criticality_sort_key, reverse=True) if t.get("id") not in targeted]
        if alt and actions and tuning >= 0.05:
            replacement = _build_shadow_synthetic_rec(actions[-1].get("asset_id", "shadow_asset"), alt[0], profile, confidence_bias + min(0.05, tuning / 2.0), tuning)
            replacement["status"] = actions[-1].get("status", "PENDING_APPROVAL")
            actions[-1] = replacement
    elif profile == "Conservative AI":
        if len(actions) > 1 and tuning >= 0.05:
            actions.sort(key=lambda r: (float(r.get("confidence", 0.0)), float(r.get("objective_value", 0.0))))
            trimmed = max(1, len(actions) - 1)
            actions = actions[-trimmed:]
    else:
        candidates = [t for t in sorted(alive, key=criticality_sort_key, reverse=True) if t.get("id") not in targeted]
        if candidates and actions and tuning >= 0.12:
            replacement = _build_shadow_synthetic_rec(actions[-1].get("asset_id", "shadow_asset"), candidates[0], profile, confidence_bias, tuning)
            replacement["status"] = actions[-1].get("status", "PENDING_APPROVAL")
            actions[-1] = replacement
    return actions
def run_shadow_decision_pass(state_snapshot, shadow_config=None):
    shadow_config = shadow_config or {}
    profile = shadow_config.get("profile", "Coverage-First AI")
    params = _shadow_profile_params(profile)
    sim_world = deepcopy(state_snapshot)
    sim_world.setdefault("shadow_state", {})
    sim_world.setdefault("shadow_config", {}).update(shadow_config)
    sim_world["doctrine_name"] = params["doctrine_name"]
    sim_world["authority_mode"] = params["authority_mode"]
    sim_world.setdefault("authority_config", {})["auto_conf_threshold"] = params["auto_conf_threshold"]

    tuning = float(shadow_config.get("divergence_tuning", 0.08))
    confidence_bias = float(shadow_config.get("confidence_bias", params.get("default_confidence_bias", 0.0)))

    previous_world = world
    try:
        bind_world(sim_world)
        recs, assignments, ew_recommendation = build_candidate_assignments()
        queue_recommendations(assignments, ew_recommendation)
        evaluate_authority()
        pending = deepcopy(sim_world.get("pending_recommendations", []))
        approved = [r for r in pending if r.get("status") == "APPROVED"]
        actions = _summarize_pending_recommendations(pending)
        actions = _apply_shadow_divergence(sim_world, actions, profile, tuning, confidence_bias)
        return {
            "enabled": bool(shadow_config.get("enabled", True)),
            "profile": profile,
            "doctrine_name": sim_world.get("doctrine_name"),
            "authority_mode": sim_world.get("authority_mode"),
            "recommendations": actions,
            "approved_count": len([r for r in actions if r.get("status") == "APPROVED"]),
            "pending_count": len([r for r in actions if r.get("status") in ("SUGGESTED", "PENDING_APPROVAL", "QUEUED_IN_FLIGHT", "STANDBY_SECOND_SHOT")]),
            "projected_ammo_commit": len([r for r in actions if r.get("action_type") == "KINETIC" and r.get("status") == "APPROVED"]),
            "target_ids": sorted({r.get("target_id") for r in actions if r.get("target_id")}),
            "asset_ids": sorted({r.get("asset_id") for r in actions if r.get("asset_id")}),
        }
    finally:
        bind_world(previous_world)


def compare_active_vs_shadow(state_snapshot, active_pending, shadow_result):
    active_actions = _summarize_pending_recommendations(active_pending)
    active_targets = sorted({r.get("target_id") for r in active_actions if r.get("target_id")})
    shadow_targets = sorted(set(shadow_result.get("target_ids", [])))
    active_pairs = {(r.get("asset_id"), r.get("target_id")) for r in active_actions if r.get("asset_id") and r.get("target_id")}
    shadow_pairs = {(r.get("asset_id"), r.get("target_id")) for r in shadow_result.get("recommendations", []) if r.get("asset_id") and r.get("target_id")}
    union = active_pairs | shadow_pairs
    agreement_pct = round(100.0 * len(active_pairs & shadow_pairs) / max(1, len(union)), 1)
    active_missiles = len([r for r in active_actions if r.get("action_type") == "KINETIC" and r.get("status") == "APPROVED"])
    shadow_missiles = int(shadow_result.get("projected_ammo_commit", 0))
    pending_count = len([r for r in active_actions if r.get("status") in ("SUGGESTED", "PENDING_APPROVAL")])
    missed_by_active = sorted(set(shadow_targets) - set(active_targets))
    missed_by_shadow = sorted(set(active_targets) - set(shadow_targets))
    priority_conflicts = sorted([f"{a}->{t}" for (a, t) in shadow_pairs ^ active_pairs])

    summary = "Shadow and active engine aligned."
    diagnostic = "aligned"
    if not active_actions and shadow_targets:
        summary = "Decision gap detected — shadow identified viable engagements absent from the live path."
        diagnostic = "decision_gap_live_inactive"
    elif active_targets and not shadow_targets:
        summary = "Live path acted while shadow remained conservative."
        diagnostic = "shadow_conservative_gap"
    elif agreement_pct < 99.9:
        summary = "Shadow engine diverged from the live decision path."
        diagnostic = "divergence"

    comparison = {
        "step": state_snapshot.get("step", 0),
        "agreement_pct": agreement_pct,
        "active_targets": active_targets,
        "shadow_targets": shadow_targets,
        "missed_by_active": missed_by_active,
        "missed_by_shadow": missed_by_shadow,
        "priority_conflicts": priority_conflicts,
        "operator_actions_current": pending_count,
        "operator_actions_shadow": 0 if shadow_result.get("enabled", True) else pending_count,
        "ammo_delta": active_missiles - shadow_missiles,
        "diagnostic": diagnostic,
        "summary": summary,
    }
    return {
        "active": {
            "recommendations": active_actions,
            "target_ids": active_targets,
            "asset_ids": sorted({r.get("asset_id") for r in active_actions if r.get("asset_id")}),
            "approved_count": len([r for r in active_actions if r.get("status") == "APPROVED"]),
            "pending_count": pending_count,
            "projected_ammo_commit": active_missiles,
        },
        "shadow": shadow_result,
        "comparison": comparison,
    }


def shadow_history_df():
    history = world.get("shadow_state", {}).get("history", [])
    if not history:
        return pd.DataFrame(columns=["step", "profile", "agreement_pct", "ammo_delta", "missed_by_active", "priority_conflicts", "summary"])
    rows = []
    for entry in history[::-1]:
        cmp = entry.get("comparison", {})
        rows.append({
            "step": entry.get("step"),
            "profile": entry.get("profile"),
            "agreement_pct": cmp.get("agreement_pct"),
            "ammo_delta": cmp.get("ammo_delta"),
            "missed_by_active": ", ".join(cmp.get("missed_by_active", [])),
            "priority_conflicts": ", ".join(cmp.get("priority_conflicts", [])[:4]),
            "summary": cmp.get("summary", ""),
        })
    return pd.DataFrame(rows)


def shadow_delta_df():
    shadow = world.get("shadow_state", {})
    comparison = shadow.get("last_comparison", {})
    summary = shadow.get("last_summary", {})
    if not summary:
        return pd.DataFrame(columns=["metric", "current", "shadow_ai"])
    active = shadow.get("last_active", {})
    shadow_side = shadow.get("last_shadow", {})
    rows = [
        {"metric": "Operator actions", "current": comparison.get("operator_actions_current", active.get("pending_count", 0)), "shadow_ai": comparison.get("operator_actions_shadow", 0)},
        {"metric": "Projected kinetic commitments", "current": active.get("projected_ammo_commit", 0), "shadow_ai": shadow_side.get("projected_ammo_commit", 0)},
        {"metric": "Recommendation agreement %", "current": 100.0, "shadow_ai": comparison.get("agreement_pct", 100.0)},
        {"metric": "Approved recommendations", "current": active.get("approved_count", 0), "shadow_ai": shadow_side.get("approved_count", 0)},
        {"metric": "Estimated reaction time (s)", "current": float(summary.get("estimated_reaction_time_live_s", 0.0)), "shadow_ai": float(summary.get("estimated_reaction_time_shadow_s", 0.0))},
    ]
    return pd.DataFrame(rows)


def doctrine_payload():
    return {
        "meta": world.get("meta", {}),
        "doctrine_name": world.get("doctrine_name"),
        "authority_mode": world.get("authority_mode"),
        "authority_config": world.get("authority_config", {}),
        "criticality_config": world.get("criticality_config", {}),
        "fire_control_config": world.get("fire_control_config", {}),
        "resilience_config": world.get("resilience_config", {}),
        "cognitive_config": world.get("cognitive_config", {}),
        "integration_config": world.get("integration_config", {}),
        "degradation_config": world.get("degradation_config", {}),
        "quantum_config": world.get("quantum_config", {}),
        "shadow_config": world.get("shadow_config", {}),
    }

def adversarial_df():
    rows = []
    for t in world.get("threats", []):
        rows.append({
            "threat_id": t["id"],
            "alive": t.get("alive", True),
            "behavior": t.get("behavior"),
            "maneuver_level": t.get("maneuver_level", 0.0),
            "terrain_masked": t.get("terrain_masked", False),
            "deception_active": t.get("deception_active", False),
            "track_noise_km": round(float(t.get("track_noise_km", 0.0)), 2),
            "confidence": round(float(t.get("confidence", 0.0)), 2),
            "spawned_reinforcement": t.get("spawned_reinforcement", False),
        })
    return pd.DataFrame(rows)

def export_snapshot():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"output/aegis_v15_7_export_{ts}.json"
    payload = {
        "meta": world["meta"], "step": world["step"], "destroyed_count": world["destroyed_count"], "doctrine_name": world["doctrine_name"], "authority_mode": world["authority_mode"],
        "authority_config": world["authority_config"], "pressure_config": world["pressure_config"], "assets": world["assets"], "objectives": world["objectives"], "threats": world["threats"],
        "assignments": world["assignments"], "pending_recommendations": world["pending_recommendations"], "event_log": world["event_log"], "authority_log": world["authority_log"],
        "override_log": world.get("override_log", []), "engagement_state": world.get("engagement_state", {}), "combat_state": world.get("combat_state", {}), "missiles": world.get("missiles", []),
        "history": world["history"], "config": world["config"], "fire_control_config": world["fire_control_config"], "explanations": world["explanations"],
        "assignment_records": world["explanations"].get("allocation_trace", []),
        "coverage_trace": world["explanations"].get("coverage_trace", []),
        "coverage_first_proof": world["explanations"].get("coverage_first_proof", [])
    }
    with open(path, "w", encoding="utf-8") as f: json.dump(payload, f, indent=2)
    return path

