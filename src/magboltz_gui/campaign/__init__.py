"""Parameter-sweep campaign support for Magboltz-GUI."""

from magboltz_gui.campaign.campaign import CampaignMode, CampaignPlan, CampaignRun, generate_runs
from magboltz_gui.campaign.runner import CampaignExecutionResult, SerialCampaignRunner
from magboltz_gui.campaign.sweep import ExplicitSweep, LinearSweep, LogSweep, SweepParameter

__all__ = [
    "CampaignExecutionResult",
    "CampaignMode",
    "CampaignPlan",
    "CampaignRun",
    "ExplicitSweep",
    "LinearSweep",
    "LogSweep",
    "SerialCampaignRunner",
    "SweepParameter",
    "generate_runs",
]
