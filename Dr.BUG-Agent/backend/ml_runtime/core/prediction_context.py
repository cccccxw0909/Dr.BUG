"""Prediction context export entry point.

Provides the PredictionContext import path for callers; definitions and field notes live in schemas.PredictionContext.
Belongs to the core layer and is used by the prediction UI, PredictionStateMachine, PredictionAgent, and ExplainerAgent.
"""

from __future__ import annotations

from .schemas import PredictionContext

__all__ = ["PredictionContext"]
