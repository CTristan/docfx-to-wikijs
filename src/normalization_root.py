"""Data model for a normalization root during the clustering post-pass."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.item_info import ItemInfo
from src.project_token_boundaries import project_token_boundaries

if TYPE_CHECKING:
    from src.sanitizer import Sanitizer
    from src.tokenizer import Tokenizer


@dataclass
class NormalizationRoot:
    """Represents a potential folder (cluster root) during the normalization pass."""

    normalized_name: str  # canonical casing, pre-sanitization
    source_cluster_key: str
    items: list[ItemInfo] = field(default_factory=list)

    # Metadata computed during infrastructure phase
    sanitized_name: str = ""
    token_boundaries: set[int] = field(default_factory=set)
    boundaries_unknown: bool = False

    # Pre-merge size for utility guard and evaluation order
    pre_merge_size: int = 0

    # Optimization token
    scope_token: str = ""

    def __post_init__(self) -> None:
        """Set pre_merge_size based on initial items."""
        self.pre_merge_size = len(self.items)

    def compute_metadata(self, sanitizer: "Sanitizer", tokenizer: "Tokenizer") -> None:
        """Compute sanitized name and project token boundaries."""
        self.sanitized_name = sanitizer.normalize(self.normalized_name)

        # 1. Get boundaries from cluster key tokens
        # The source_cluster_key is what was used to create this root.
        # We tokenize it to get the "ideal" boundaries.
        tokens = tokenizer.tokenize(self.source_cluster_key)

        norm_boundaries = {0}
        curr = 0
        for t in tokens:
            curr += len(t)
            norm_boundaries.add(curr)

        # 2. Project boundaries
        # Note: source_cluster_key might be slightly different from normalized_name
        # (e.g. if normalized_name was produced by canonicalize_root_name)
        # But they should be aligned.

        s_bounds, success = project_token_boundaries(
            self.normalized_name, self.sanitized_name, norm_boundaries
        )

        if success:
            self.token_boundaries = s_bounds
            self.boundaries_unknown = False
        else:
            # 3. Escape Hatch
            # check if all items share the same token list
            if not self.items:
                self.boundaries_unknown = True
                return

            first_tokens = tokenizer.tokenize(self.items[0].name)
            all_same = True
            for item in self.items[1:]:
                if tokenizer.tokenize(item.name) != first_tokens:
                    all_same = False
                    break

            if all_same:
                # Use this shared token list to detect boundaries
                # (Still needs projection if sanitized_name differs)
                # For now, if projection failed once, we mark as unknown
                self.boundaries_unknown = True
            else:
                self.boundaries_unknown = True
