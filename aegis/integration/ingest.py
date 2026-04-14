
from __future__ import annotations

from datetime import datetime

from .adapters import build_adapter_registry
from .validation import validate_records


def ingest_external_data(world: dict) -> dict:
    cfg = world.get("integration_config", {})
    state = world.setdefault("integration_state", {})
    registry = build_adapter_registry()
    active_ids = cfg.get("active_adapters", [])

    raw_records = []
    adapter_status = {}
    for adapter_id in active_ids:
        adapter = registry.get(adapter_id)
        if adapter is None:
            adapter_status[adapter_id] = {"status": "missing"}
            continue
        records = adapter.fetch(world)
        raw_records.extend(records)
        adapter_status[adapter_id] = {
            "status": "ok",
            "records": len(records),
            "trust_level": getattr(adapter, "trust_level", "unknown"),
            "sovereign_scope": getattr(adapter, "sovereign_scope", "unknown"),
        }

    validation = validate_records(raw_records, accept_unverified=cfg.get("accept_unverified", False))
    valid_records = validation["valid"]
    state["status"] = "Connected" if active_ids else "Idle"
    state["trust_level"] = "VERIFIED_ONLY" if not cfg.get("accept_unverified", False) else "MIXED_ALLOWED"
    state["last_ingest_step"] = world.get("step", 0)
    state["last_ingest_time"] = datetime.now().isoformat(timespec="seconds")
    state["source_count"] = len([a for a in adapter_status.values() if a.get("status") == "ok"])
    state["record_count"] = len(valid_records)
    state["latest_records"] = valid_records[:25]
    state["adapter_status"] = adapter_status
    notes = [
        f"Integration mode {cfg.get('mode', 'LOCAL_ONLY')} with {state['source_count']} active source(s).",
        f"{state['record_count']} validated record(s) available to the sovereign integration layer.",
    ] + validation.get("notes", [])
    if cfg.get("merge_validated_tracks", False):
        state["feed_notes"] = notes + ["Validated tracks are marked merge-ready for downstream mission logic."]
    else:
        state["feed_notes"] = notes + ["Validated tracks are held at the adapter boundary for safe review."]
    return {
        "status": state["status"],
        "source_count": state["source_count"],
        "record_count": state["record_count"],
        "notes": state["feed_notes"],
        "adapter_status": adapter_status,
    }
