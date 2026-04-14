
from __future__ import annotations

from typing import Dict, List

REQUIRED_KEYS = {"source", "record_type", "track_id", "trust_level", "sovereign_scope", "latency_ms"}


def validate_records(records: List[Dict], accept_unverified: bool = False) -> Dict:
    valid, rejected, notes = [], [], []
    for record in records:
        missing = [key for key in REQUIRED_KEYS if key not in record]
        if missing:
            rejected.append({"record": record, "reason": f"missing keys: {', '.join(missing)}"})
            continue
        if record.get("trust_level") not in {"VERIFIED", "PARTNER"} and not accept_unverified:
            rejected.append({"record": record, "reason": "trust level rejected by policy"})
            continue
        valid.append(record)
    notes.append(f"Validated {len(valid)} records; rejected {len(rejected)}.")
    return {"valid": valid, "rejected": rejected, "notes": notes}
