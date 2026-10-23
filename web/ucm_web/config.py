import os
from dataclasses import dataclass
from typing import Optional


# ---------------- CONFIG ----------------
#
# Every setting comes from an environment variable so that passwords never
# live in the repo. See web/README.md for the full list.

@dataclass(frozen=True)
class Config:

    mqtt_host: str = "nyit-ucm.nycmesh.net"
    mqtt_port: int = 1883
    mqtt_user: Optional[str] = None
    mqtt_password: Optional[str] = None

    mock: bool = False
    mock_nodes: int = 15
    mock_hz: float = 1.0

    replay_path: Optional[str] = None
    replay_speed: float = 1.0
    replay_max_gap: float = 5.0

    web_host: str = "127.0.0.1"
    web_port: int = 5002
    web_threads: int = 8

    # Limits that keep memory bounded no matter what is published.
    # The broker currently allows anonymous publishing, so anyone on the
    # mesh could send junk topics or huge payloads.
    max_nodes: int = 200
    max_payload_bytes: int = 4096

    @property
    def source_label(self):
        if self.mock:
            return "mock"
        if self.replay_path:
            return "replay"
        return f"{self.mqtt_host}:{self.mqtt_port}"

    @classmethod
    def from_env(cls):

        env = os.environ

        return cls(
            mqtt_host=env.get("UCM_MQTT_HOST", cls.mqtt_host),
            mqtt_port=int(env.get("UCM_MQTT_PORT", cls.mqtt_port)),
            mqtt_user=env.get("UCM_MQTT_USER") or None,
            mqtt_password=env.get("UCM_MQTT_PASSWORD") or None,
            mock=env.get("UCM_MOCK") == "1",
            mock_nodes=int(env.get("UCM_MOCK_NODES", cls.mock_nodes)),
            mock_hz=float(env.get("UCM_MOCK_HZ", cls.mock_hz)),
            replay_path=env.get("UCM_REPLAY") or None,
            replay_speed=float(env.get("UCM_REPLAY_SPEED", cls.replay_speed)),
            replay_max_gap=float(env.get("UCM_REPLAY_MAX_GAP", cls.replay_max_gap)),
            web_host=env.get("UCM_WEB_HOST", cls.web_host),
            web_port=int(env.get("UCM_WEB_PORT", cls.web_port)),
            web_threads=int(env.get("UCM_WEB_THREADS", cls.web_threads)),
            max_nodes=int(env.get("UCM_MAX_NODES", cls.max_nodes)),
            max_payload_bytes=int(env.get("UCM_MAX_PAYLOAD_BYTES", cls.max_payload_bytes)),
        )
