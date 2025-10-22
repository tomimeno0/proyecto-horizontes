"""Reexporta el dashboard en vivo para FastAPI."""

from horizonte.governance.dashboard.live import router, metrics_stream

__all__ = ["router", "metrics_stream"]

