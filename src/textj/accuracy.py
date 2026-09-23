from __future__ import annotations


def normalize_metric_text(text: str) -> str:
    """Normalize text for repeatable OCR accuracy measurements."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def levenshtein_distance(reference: str, hypothesis: str) -> int:
    """Return character-level Levenshtein edit distance."""
    if reference == hypothesis:
        return 0
    if not reference:
        return len(hypothesis)
    if not hypothesis:
        return len(reference)

    if len(reference) < len(hypothesis):
        reference, hypothesis = hypothesis, reference

    previous = list(range(len(hypothesis) + 1))
    for i, ref_char in enumerate(reference, start=1):
        current = [i]
        for j, hyp_char in enumerate(hypothesis, start=1):
            insertion = current[j - 1] + 1
            deletion = previous[j] + 1
            substitution = previous[j - 1] + (ref_char != hyp_char)
            current.append(min(insertion, deletion, substitution))
        previous = current

    return previous[-1]


def character_error_rate(reference: str, hypothesis: str) -> float:
    """Return CER = edit distance / reference character count."""
    ref = normalize_metric_text(reference)
    hyp = normalize_metric_text(hypothesis)

    if not ref:
        return 0.0 if not hyp else 1.0

    return levenshtein_distance(ref, hyp) / len(ref)
