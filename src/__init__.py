"""Grounded chess-mistake explanations: engine probes -> two-axis fact sheet
-> constrained LLM lexicalization -> mechanical verification."""
from .factsheet import build, FactSheet
from .lexicalize import explain
from .probes import Probes
