"""Logic for analyzing metadata to identify common prefixes and suffixes."""

from collections import Counter
from typing import Any

from src.item_info import ItemInfo
from src.metadata_index import MetadataIndex
from src.sanitizer import Sanitizer
from src.tokenizer import Tokenizer


class Analyzer:
    """Analyzes item names and hierarchies to find naming patterns."""

    def __init__(
        self,
        tokenizer: Tokenizer,
        sanitizer: Sanitizer,
        metadata_index: MetadataIndex,
        config: dict[str, Any],
    ) -> None:
        """Initialize the analyzer with necessary components and config."""
        self.tokenizer = tokenizer
        self.sanitizer = sanitizer
        self.metadata_index = metadata_index
        self.config = config

        self.prefix_counts: Counter[str] = Counter()
        self.suffix_counts: Counter[str] = Counter()
        self.base_class_counts: Counter[str] = Counter()

        # Normalize stop tokens
        raw_stop = config.get("rules", {}).get("stop_tokens", [])
        self.stop_tokens = {sanitizer.normalize(t) for t in raw_stop}

        self.global_items: list[str] = []

    def analyze(self, items: list[ItemInfo]) -> None:
        """Analyze a list of ItemInfo objects."""
        self.global_items = []
        # Clear counters? Or accumulator?
        # Assuming analyze is called once.

        for item in items:
            ns = getattr(item, "namespace", None)
            if not ns or ns == "Global":
                self.global_items.append(item.uid)
                self._process_item(item)

    def _process_item(self, item: ItemInfo) -> None:
        """Process a single ItemInfo to update frequency counts."""
        name = item.name
        tokens = self.tokenizer.tokenize(name)

        if not tokens:
            return

        # Prefix
        prefix = self.sanitizer.normalize(tokens[0])
        self.prefix_counts[prefix] += 1

        # Suffix
        suffix = self.sanitizer.normalize(tokens[-1])
        self.suffix_counts[suffix] += 1

        # Base Class
        base = self.metadata_index.get_base_class(item.uid)
        if base:
            self.base_class_counts[base] += 1

        # Interfaces
        for iface in self.metadata_index.get_interfaces(item.uid):
            self.base_class_counts[iface] += 1

    def get_top_prefixes(self, k: int, min_size: int) -> list[str]:
        """Return the top k prefixes occurring at least min_size times."""
        candidates = []
        for token, count in self.prefix_counts.items():
            if count >= min_size and token not in self.stop_tokens:
                candidates.append((token, count))

        # Sort by count DESC, then token ASC
        candidates.sort(key=lambda x: (-x[1], x[0]))

        return [c[0] for c in candidates[:k]]

    def get_strong_suffixes(self, min_size: int) -> set[str]:
        """Return suffixes occurring at least min_size times."""
        valid = set()
        for token, count in self.suffix_counts.items():
            if count >= min_size and token not in self.stop_tokens:
                valid.add(token)
        return valid
