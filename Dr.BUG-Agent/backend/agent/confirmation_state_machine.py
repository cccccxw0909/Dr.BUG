from __future__ import annotations

from typing import Set


HIGH_RISK_ACTIONS: Set[str] = {
    "create_training_job",
    "draft_training_job",
    "create_prediction_job",
    "draft_single_prediction",
    "create_recommendation_job",
    "create_report_job",
}


class ConfirmationStateMachine:
    def requires_confirmation(self, action_type: str) -> bool:
        return action_type in HIGH_RISK_ACTIONS

