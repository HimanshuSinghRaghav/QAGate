"""Import side-effect module: pulls every handler into the registry."""
from app.services.checks import behaviour, factual, verbatim  # noqa: F401
from app.services.checks.base import get_handler, registered

__all__ = ["get_handler", "registered"]
