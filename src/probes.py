"""Engine truth layer — re-exports the shared client.

The Probes wrapper + generated protobuf stubs moved to /common/engine_client
(2026-07-22): lucena-plans' research harness was reaching directly into this
repo's source tree via sys.path hacks to get the same client, which broke
outright when this repo was renamed/moved from ~/Development/chess-lab. One
canonical copy now lives in the superrepo's /common, imported here (and by
lucena-plans) via the same sys.path-append-to-a-sibling convention
`backend/plans/service.py` already uses to reach lucena-plans/src.
"""
from __future__ import annotations

import sys
from pathlib import Path

_COMMON = Path(__file__).resolve().parents[2] / "common"   # src/ -> repo -> superrepo -> common
if str(_COMMON) not in sys.path:
    sys.path.append(str(_COMMON))

from engine_client.probes import (  # noqa: E402
    Probes, Line, Threat, ENGINE_ADDR, NODES, THREAT_NODES,
)

__all__ = ["Probes", "Line", "Threat", "ENGINE_ADDR", "NODES", "THREAT_NODES"]
