"""Synthetic inputs and safe loading for recovered host scripts."""

import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SENSOR = ROOT / "blue-team/zeek/libexec"
CONTROL = (
    ROOT / "infrastructure/blueguard-pipeline/control-plane/rootfs"
    / "usr/local/libexec"
)


def load_script(name, path):
    """Load an extensionless Python script without running its __main__ block."""
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    # The ingester sets umask at import time. Restore it for the test process.
    previous_umask = os.umask(0o077)
    try:
        loader.exec_module(module)
    finally:
        os.umask(previous_umask)
    return module


def connection(uid="Csynthetic1", ts=1795000000.0):
    return {
        "ts": ts,
        "uid": uid,
        "id.orig_h": "192.0.2.10",
        "id.orig_p": 43210,
        "id.resp_h": "198.51.100.20",
        "id.resp_p": 443,
        "proto": "tcp",
        "orig_bytes": 1200,
        "resp_bytes": 80,
        "missed_bytes": 0,
    }


def jsonl(*records):
    return b"".join(
        json.dumps(record, separators=(",", ":")).encode() + b"\n"
        for record in records
    )
