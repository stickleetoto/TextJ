"""Public language policy for TextJ.

Runtime (model) languages:

* ``ko-en`` — Korean + English (+ digits/punctuation) recognizer. Default.
  Intended for mixed Korean/English screens; callers do not need to know the
  image language in advance.
* ``en`` — English-only recognizer.

``korean`` is accepted as an alias of ``ko-en`` (backward compatibility).

Request option ``language`` is a *requirement*, not a model switch: ``auto``
(or omitted) uses whatever the runtime loaded; ``ko-en``/``korean`` requires a
Korean-capable runtime; ``en`` is satisfied by both runtimes.
"""

from __future__ import annotations

RUNTIME_LANGUAGES = ("ko-en", "en")
REQUEST_LANGUAGES = ("auto", "ko-en", "korean", "en")
ALIASES = {"korean": "ko-en", "ko": "ko-en", "kor": "ko-en"}

# Which request languages each loaded runtime language can serve.
COVERAGE = {
    "ko-en": frozenset({"ko-en", "en"}),
    "en": frozenset({"en"}),
}


def normalize_runtime_language(value: str) -> str:
    language = ALIASES.get(value.strip().lower(), value.strip().lower())
    if language not in RUNTIME_LANGUAGES:
        raise ValueError(
            f"unsupported language {value!r}; supported: {', '.join(RUNTIME_LANGUAGES)}"
            " (alias: korean -> ko-en)"
        )
    return language


def serves(runtime_language: str, requested: str | None) -> bool:
    if requested is None or requested == "auto":
        return True
    requested = ALIASES.get(requested, requested)
    return requested in COVERAGE.get(runtime_language, frozenset())
