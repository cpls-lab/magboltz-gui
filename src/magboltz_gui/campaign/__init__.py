"""Parameter-sweep campaign support for Magboltz-GUI."""

from magboltz_gui.campaign.campaign import CampaignPlan, CampaignRun, generate_runs
from magboltz_gui.campaign.runner import CampaignCancelled, CampaignExecutionResult, SerialCampaignRunner
from magboltz_gui.campaign.sweep import ExplicitSweep, LinearSweep, LogSweep, SweepMode, SweepParameter

__all__ = [
    "CampaignExecutionResult",
    "CampaignCancelled",
    "CampaignPlan",
    "CampaignRun",
    "ExplicitSweep",
    "LinearSweep",
    "LogSweep",
    "SerialCampaignRunner",
    "SweepMode",
    "SweepParameter",
    "generate_runs",
]
