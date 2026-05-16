"""Pending-action domain mutex: within a scope, keep only the latest per business domain."""

from __future__ import annotations

from typing import FrozenSet

# Training domain
TRAINING_PENDING_ACTION_TYPES: FrozenSet[str] = frozenset({"create_training_job", "draft_training_job"})

# Single-sample prediction domain (formal create vs draft are mutually exclusive)
SINGLE_SAMPLE_PREDICTION_PENDING_ACTION_TYPES: FrozenSet[str] = frozenset(
    {"create_prediction_job", "draft_single_prediction"}
)


def pending_domain_supersedes(new_action_type: str, existing_action_type: str) -> bool:
    """
    Whether a new pending supersedes an existing one (evaluated in-registry under the same scope).
    - Same training domain / same single-sample prediction domain: supersede each other
    - Else only identical action_type is mutually exclusive (reports/recommendations supersede same type)
    """
    if (
        new_action_type in TRAINING_PENDING_ACTION_TYPES
        and existing_action_type in TRAINING_PENDING_ACTION_TYPES
    ):
        return True
    if (
        new_action_type in SINGLE_SAMPLE_PREDICTION_PENDING_ACTION_TYPES
        and existing_action_type in SINGLE_SAMPLE_PREDICTION_PENDING_ACTION_TYPES
    ):
        return True
    return new_action_type == existing_action_type
