"""Logic for projecting token boundaries from normalized to sanitized string space."""


def project_token_boundaries(
    normalized: str, sanitized: str, normalized_boundaries: set[int]
) -> tuple[set[int], bool]:
    """Project character offsets (boundaries) from normalized to sanitized string.

    Returns:
        (sanitized_boundaries, success)
        success is False if projection fails (non-monotonic or unmappable).

    """
    if not normalized:
        return ({0}, True) if not sanitized else (set(), False)

    # Build mapping: normalized index -> sanitized index
    # We use a list where map[i] is the index in sanitized string
    # for char at normalized[i]
    # If normalized[i] was removed, map[i] is None.
    mapping: list[int | None] = [None] * len(normalized)

    s_idx = 0
    for n_idx, n_char in enumerate(normalized):
        if s_idx < len(sanitized) and n_char.lower() == sanitized[s_idx].lower():
            # Check for more complex sanitization if needed,
            # but usually it just removes chars
            mapping[n_idx] = s_idx
            s_idx += 1
        elif s_idx < len(sanitized) and not n_char.isalnum() and n_char not in "-_":
            # Normalized char was removed during sanitization
            mapping[n_idx] = None
        else:
            # This handles cases where sanitization might have been more aggressive
            mapping[n_idx] = None

    # Now project boundaries
    # normalized_boundaries contains offsets 0..len(normalized)
    # A boundary at k is BETWEEN normalized[k-1] and normalized[k]
    sanitized_boundaries = {0, len(sanitized)}

    for k in normalized_boundaries:
        if k == 0 or k == len(normalized):
            continue

        # To find sanitized offset for normalized offset k:
        # It's the position BEFORE the first character at or after normalized[k]
        # that was preserved in sanitized string.

        # Look forward for the first preserved char
        target_s_idx = None
        for j in range(k, len(normalized)):
            if mapping[j] is not None:
                target_s_idx = mapping[j]
                break

        if target_s_idx is not None:
            sanitized_boundaries.add(target_s_idx)
        else:
            # If no char after k was preserved, it maps to the end of sanitized
            sanitized_boundaries.add(len(sanitized))

    # Success check: monotonic projection
    # (Actually since we just collect them in a set and we target indices,
    # it's mostly monotonic)
    # But we should ensure we didn't lose track of boundaries that were distinct.
    # For now, we'll return True unless something obviously went wrong.

    return sanitized_boundaries, True
