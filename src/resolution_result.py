"""Data models for global namespace resolution results."""

from dataclasses import dataclass, field


@dataclass
class ResolutionResult:
    """Represents the outcome of resolving a global UID to a file path."""

    uid: str
    final_path: str
    winning_rule: str
    score: float
    cluster_key: str
    ambiguity: list[dict] = field(default_factory=list)
    initial_root: str = ""  # Pre-normalization root
