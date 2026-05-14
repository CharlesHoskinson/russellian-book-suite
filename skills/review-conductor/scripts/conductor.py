"""Public entrypoint: run_panel(workspace, chapter_id, panel_path, dispatcher) -> verdict dict.

The dispatcher callable is invoked once per packet. In production, the caller
provides a dispatcher that issues a Task-tool call for each persona subagent;
in tests, the dispatcher writes a pre-canned review markdown to the packet's
output_path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from .aggregate_panel import run_aggregation
from .dispatch_panel import PanelPacket, build_packets
from .load_panel import load_panel


def run_panel(
    workspace: Path,
    chapter_id: str,
    panel_path: Path,
    dispatcher: Optional[Callable[[PanelPacket], None]] = None,
) -> dict:
    workspace = Path(workspace).resolve()
    panel = load_panel(panel_path)
    packets = build_packets(workspace, chapter_id, panel)
    if dispatcher is not None:
        for packet in packets:
            dispatcher(packet)
    return run_aggregation(workspace, chapter_id, panel)
