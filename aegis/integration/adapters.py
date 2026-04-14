
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class ExternalFeedAdapter:
    adapter_id: str
    trust_level: str = "VERIFIED"
    sovereign_scope: str = "LOCAL"

    def fetch(self, world: dict) -> List[Dict]:
        return []


class MirrorLiveTracksAdapter(ExternalFeedAdapter):
    def __init__(self) -> None:
        super().__init__(adapter_id="mirror_live_tracks", trust_level="VERIFIED", sovereign_scope="LOCAL")

    def fetch(self, world: dict) -> List[Dict]:
        records = []
        for threat in world.get("threats", []):
            if not threat.get("alive", True):
                continue
            records.append({
                "source": self.adapter_id,
                "record_type": "track",
                "track_id": threat["id"],
                "x": threat["x"],
                "y": threat["y"],
                "vx": threat.get("vx", 0.0),
                "vy": threat.get("vy", 0.0),
                "confidence": threat.get("confidence", 0.0),
                "classification": threat.get("kind", "unknown"),
                "target_objective": threat.get("target_objective"),
                "trust_level": self.trust_level,
                "sovereign_scope": self.sovereign_scope,
                "latency_ms": 40,
            })
        return records


class DemoRadarFeedAdapter(ExternalFeedAdapter):
    def __init__(self) -> None:
        super().__init__(adapter_id="demo_radar_feed", trust_level="VERIFIED", sovereign_scope="NATIONAL")

    def fetch(self, world: dict) -> List[Dict]:
        step = world.get("step", 0)
        return [{
            "source": self.adapter_id,
            "record_type": "sensor_health",
            "track_id": f"radar_status_{step}",
            "x": world.get("objectives", [{}])[0].get("x", 0.0),
            "y": world.get("objectives", [{}])[0].get("y", 0.0),
            "confidence": 0.99,
            "classification": "RADAR_HEALTH",
            "target_objective": None,
            "trust_level": self.trust_level,
            "sovereign_scope": self.sovereign_scope,
            "latency_ms": world.get("integration_config", {}).get("simulate_latency_ms", 120),
            "note": "National radar feed adapter heartbeat",
        }]


class CoalitionDemoFeedAdapter(ExternalFeedAdapter):
    def __init__(self) -> None:
        super().__init__(adapter_id="coalition_demo_feed", trust_level="PARTNER", sovereign_scope="COALITION")

    def fetch(self, world: dict) -> List[Dict]:
        return [{
            "source": self.adapter_id,
            "record_type": "advisory",
            "track_id": f"coalition_hint_{world.get('step', 0)}",
            "x": None,
            "y": None,
            "confidence": 0.78,
            "classification": "ADVISORY",
            "target_objective": "hq",
            "trust_level": self.trust_level,
            "sovereign_scope": self.sovereign_scope,
            "latency_ms": 250,
            "note": "Partner feed advisory: monitor HQ approach corridor.",
        }]


def build_adapter_registry() -> dict:
    adapters = [MirrorLiveTracksAdapter(), DemoRadarFeedAdapter(), CoalitionDemoFeedAdapter()]
    return {adapter.adapter_id: adapter for adapter in adapters}


class SovereignAdapter:
    """Terminology mapping layer for NATO / Link-16 style labels without changing internal engine variables."""

    NATO_MAPPING = {
        "Track_Number": "id",
        "J3.2_Position": "pos",
        "J12.0_Status": "status",
        "Engagement_Auth": "authority_mode",
    }

    @staticmethod
    def ingest_link16(j_message: Dict) -> Dict:
        return {
            "id": j_message.get("TN", j_message.get("track_id")),
            "pos": (j_message.get("Lat", j_message.get("x")), j_message.get("Lon", j_message.get("y")), j_message.get("Alt", 0)),
            "type": j_message.get("Category", j_message.get("classification", "Unknown")),
            "status": j_message.get("Assignment_Status", j_message.get("status", "PENDING")),
            "timestamp": j_message.get("Timestamp"),
        }

    @staticmethod
    def export_status(internal_state: Dict) -> Dict:
        return {
            "Message_Type": "J12.6_Target_Assignment",
            "TN": internal_state.get("id") or internal_state.get("target_id"),
            "Assignment_Status": "ENGAGED" if internal_state.get("locked") or internal_state.get("status") == "APPROVED" else "PENDING",
            "Weapon_Type": internal_state.get("weapon_type", internal_state.get("action_type", "SHORAD")),
        }


def export_tdl_records(world: dict) -> List[Dict]:
    records = []
    for rec in world.get("pending_recommendations", []):
        payload = {
            "id": rec.get("target_id"),
            "target_id": rec.get("target_id"),
            "status": rec.get("status"),
            "action_type": rec.get("action_type"),
            "locked": rec.get("status") == "APPROVED",
        }
        records.append(SovereignAdapter.export_status(payload))
    return records
