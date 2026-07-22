"""Engine truth layer — re-exports the shared client.

The Probes wrapper + generated protobuf stubs moved to /common/engine_client
(2026-07-22): lucena-plans' research harness was reaching directly into this
repo's source tree via sys.path hacks to get the same client, which broke
outright when this repo was renamed/moved from ~/Development/chess-lab. One
canonical copy now lives in the superrepo's /common, a properly
pip-installable package (`pip install -e ../common`, matching how
lucena-engine is already installed into this venv) — no sys.path
manipulation, no computed relative paths; CI provisions the install.
"""
from __future__ import annotations

from common.engine_client.probes import Probes, Line, Threat, ENGINE_ADDR, NODES, THREAT_NODES

__all__ = ["Probes", "Line", "Threat", "ENGINE_ADDR", "NODES", "THREAT_NODES"]
