"""Baseline AI scientist package exports."""

from baseline_ai_scientist.hypothesis_generator import CandidateModel, generate_hypotheses
from baseline_ai_scientist.naive_scientist import NaiveAIScientist, NaiveScientistConfig

__all__ = ["CandidateModel", "generate_hypotheses", "NaiveAIScientist", "NaiveScientistConfig"]
