"""Training execution: DomainTrainingPayload -> StateMachine / Programmer pipeline."""

from backend.training.feature_source import FeatureStrategy, resolve_feature_strategy

__all__ = ["FeatureStrategy", "resolve_feature_strategy"]
