"""Reexporta el dashboard en vivo para FastAPI."""

from horizonte.governance.dashboard.live import metrics_stream, router

__all__ = ["router", "metrics_stream"]

