from __future__ import annotations

import os
from copy import deepcopy

import streamlit as st

from . import core


def upgrade_state_to_v162(state: dict) -> dict:
    state = deepcopy(state)
    state["meta"]["version"] = "v16.7"
    state["meta"]["title"] = "Aegis C2 Quantum Dual Use — v16.7"

    state.setdefault("configured_authority_mode", state.get("authority_mode", "Approval Required"))
    state.setdefault("authority_state", {"configured": state.get("authority_mode", "Approval Required"), "effective": state.get("authority_mode", "Approval Required"), "source": "Configured policy", "reason": "No runtime override active.", "effective_operator": state.get("authority_config", {}).get("operator_name", "operator_1")})
    state.setdefault("authority_escalation_state", {"current_operator": state.get("authority_config", {}).get("operator_name", "operator_1"), "current_level": 0, "last_event_step": -999, "last_title": "", "last_text": "", "active": False})
    state.setdefault("resilience_config", {
        "comms_mode": "Nominal",
        "remote_link_quality": 1.0,
        "gps_quality": 1.0,
        "sensor_fusion_quality": 1.0,
        "degraded_latency_steps": 1,
        "local_fallback_enabled": True,
        "local_operator_name": "local_cell_alpha",
        "queue_actions_when_link_lost": True,
        "allow_emergency_local_release": True,
    })
    state.setdefault("resilience_state", {
        "fallback_active": False,
        "degraded": False,
        "last_transition_step": 0,
        "notes": [],
        "queued_local_actions": [],
    })
    state.setdefault("cognitive_config", {
        "max_operator_load": 1.0,
        "pending_weight": 0.20,
        "critical_weight": 0.20,
        "swarm_weight": 0.16,
        "comms_weight": 0.18,
        "missile_weight": 0.10,
        "overload_threshold": 0.72,
        "collapse_threshold": 0.88,
        "recommend_condensed_view": True,
    })
    state.setdefault("cognitive_state", {
        "score": 0.0,
        "band": "LOW",
        "driver_breakdown": {},
        "ui_mode": "Normal",
        "recommendations": [],
    })
    state.setdefault("audit_config", {
        "autosave_every_step": True,
        "max_replay_frames": 200,
        "include_full_world": False,
        "export_hashes": True,
    })
    state.setdefault("audit_state", {
        "frames": [],
        "last_export_path": None,
        "last_replay_path": None,
    })
    state.setdefault("quantum_interface", {
        "status": "Not engaged",
        "mode": "Classical baseline",
        "candidate_problem": None,
        "last_payload": None,
        "notes": [
            "Architecture prepared for future optimisation adapter.",
            "No quantum decision path is active in live mission execution.",
            "Operational decisions remain classical and explainable.",
        ],
    })
    state["explanations"].setdefault("resilience_notes", [])
    state["explanations"].setdefault("cognitive_load_notes", [])
    state["explanations"].setdefault("audit_notes", [])
    state["explanations"].setdefault("quantum_notes", [])
    state.setdefault("kill_chain_config", {"reengage_cooldown_steps": 1, "max_engagement_attempts_before_escalation": 2, "allow_same_launcher_reengage": True, "shoot_look_shoot": True, "persistent_reengagement": True, "step_time_budget_s": 0.20})
    state.setdefault("kill_assurance_state", {"watchlist": [], "escalation_notes": [], "resolved_log": []})
    state.setdefault("runtime_metrics", {"last_step_time_s": 0.0})
    state.setdefault("integration_config", {
        "mode": "LOCAL_ONLY",
        "active_adapters": ["mirror_live_tracks", "demo_radar_feed"],
        "merge_validated_tracks": False,
        "accept_unverified": False,
        "staleness_steps": 2,
        "simulate_latency_ms": 120,
        "protocol": "Internal",
    })
    state.setdefault("integration_state", {
        "status": "Prepared",
        "trust_level": "VERIFIED_ONLY",
        "last_ingest_step": 0,
        "last_ingest_time": None,
        "source_count": 0,
        "record_count": 0,
        "feed_notes": [],
        "latest_records": [],
        "adapter_status": {},
    })
    state["explanations"].setdefault("integration_notes", [])
    state.setdefault("impact_markers", [])
    state["explanations"].setdefault("kill_chain_notes", [])
    state["explanations"].setdefault("decision_trace", [])
    state.setdefault("adversarial_config", {
        "enabled": True,
        "maneuver_intensity": 0.22,
        "sensor_noise_km": 0.20,
        "deception_probability": 0.18,
        "terrain_mask_probability": 0.12,
        "spawn_reinforcement_step": 6,
        "reinforcement_count": 2,
        "pk_adversarial_penalty": 0.08,
    })
    state.setdefault("adversarial_state", {
        "enabled": True,
        "reinforcement_spawned": False,
        "last_notes": [],
        "jink_events": [],
        "deception_events": [],
    })
    state["explanations"].setdefault("adversarial_notes", [])

    state.setdefault("degradation_config", {
        "sensor_1_offline": False,
        "shorad_2_offline": False,
        "show_coverage_gap": True,
        "auto_gap_alert": True,
        "leak_step_limit": 20,
    })
    state.setdefault("coverage_state", {
        "integrity_pct": 100,
        "gap_detected": False,
        "gap_assets": [],
        "notes": [],
    })
    state.setdefault("quantum_config", {
        "enabled": False,
        "solver_mode": "Simulated Annealing",
        "latency_ms": 12,
    })
    state["explanations"].setdefault("coverage_notes", [])
    state["explanations"].setdefault("degradation_notes", [])

    state.setdefault("shadow_config", {
        "enabled": True,
        "profile": "Coverage-First AI",
        "compare_against_current_authority": True,
        "assumed_reaction_time_saved_s": 4.0,
        "protocol_labels": "Internal",
    })
    state.setdefault("shadow_state", {
        "enabled": True,
        "mode": "Parallel read-only advisory",
        "last_summary": {},
        "last_notes": [],
        "history": [],
        "last_active": {},
        "last_shadow": {},
        "last_comparison": {},
    })
    state.setdefault("doctrine_export_state", {
        "last_export_path": None,
    })
    state.setdefault("authority_config", {}).setdefault("escalation_chain", [state.get("authority_config", {}).get("operator_name", "operator_1"), "operator_2", "operator_3"])
    state.setdefault("authority_config", {}).setdefault("escalation_tti_steps", 10.0)
    state.setdefault("authority_config", {}).setdefault("auto_release_after_chain_exhausted", True)
    state.setdefault("adaptive_doctrine_config", {
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
    })
    state.setdefault("adaptive_doctrine_state", {
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
    })
    state.setdefault("operator_consequence_state", {
        "last_event_step": -999,
        "last_title": "",
        "last_text": "",
        "severity": "info",
        "risk_delta_pct": 0.0,
        "coverage_delta_pct": 0.0,
        "expected_damage_delta_pct": 0.0,
        "counterfactual": "",
    })
    return state


def make_default_state() -> dict:
    state = core.make_default_state()
    state = upgrade_state_to_v162(state)
    if os.environ.get("AEGIS_DEMO_MODE", "0") == "1":
        state = core.apply_demo_mode(state)
        state = upgrade_state_to_v162(state)
        state["meta"]["title"] += " [DEMO]"

    state.setdefault("shadow_config", {
        "enabled": True,
        "profile": "Coverage-First AI",
        "compare_against_current_authority": True,
        "assumed_reaction_time_saved_s": 4.0,
        "protocol_labels": "Internal",
    })
    state.setdefault("shadow_state", {
        "enabled": True,
        "mode": "Parallel read-only advisory",
        "last_summary": {},
        "last_notes": [],
        "history": [],
        "last_active": {},
        "last_shadow": {},
        "last_comparison": {},
    })
    state.setdefault("doctrine_export_state", {
        "last_export_path": None,
    })
    return state


def reset_state() -> None:
    st.session_state.world_state = make_default_state()
    st.session_state.pop("aegis_v166_initialized", None)
    st.session_state.pop("aegis_v164_version", None)


def get_world() -> dict:
    if "world_state" not in st.session_state:
        reset_state()
    world = st.session_state.world_state
    core.bind_world(world)
    return world
