"""Executable local AgentTeams-compatible controller runtime.

This package runs real local worker subprocesses and persists a Matrix-shaped
event room.  It deliberately keeps the official AgentTeams boundary explicit:
local execution is real, but it is not evidence that the upstream Controller
or Matrix service was deployed.
"""

from .controller import LocalController, StaleApprovalError

__all__ = ["LocalController", "StaleApprovalError"]
