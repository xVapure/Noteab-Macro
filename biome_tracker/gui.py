

from __future__ import annotations

from typing import Optional

from .core import BiomeTracker


def launch_app() -> BiomeTracker:
    """Start the biome tracker GUI application and return the running tracker instance."""
    return BiomeTracker()


def bind_global_hotkeys(tracker: BiomeTracker) -> None:
    """Compatibility no-op: hotkeys are already bound by the legacy core during initialization."""
    _ = tracker


def stop_app(tracker: Optional[BiomeTracker]) -> None:
    """Stop detection if the tracker instance exists."""
    if tracker is not None and getattr(tracker, "detection_running", False):
        tracker.stop_detection()
