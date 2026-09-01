"""
PAPR Reduction Method Registry
==============================

Central registry for PAPR reduction algorithms used by OFDM-LinkSim.

This module provides a single, well-defined interface between the OFDM
processing pipeline and individual PAPR reduction implementations.

Design goals
------------
1. Keep the main OFDM pipeline independent from concrete PAPR algorithms.
2. Provide a stable lookup mechanism for PAPR methods.
3. Support both fully implemented and optional algorithms.
4. Allow algorithms to be added without modifying the simulation pipeline.
5. Expose method metadata for experiment runners, reports, and dashboards.
6. Preserve the Stage-1 ``none`` reference as a locked baseline.
7. Fail clearly when an algorithm is requested but unavailable.
8. Keep compatibility with the original ``get_method()`` API.

Supported methods
-----------------
none
    Identity/reference processing. No PAPR reduction is performed.

clipping
    Amplitude clipping. Supports hard and soft clipping depending on the
    implementation in ``papr_methods.clipping``.

slm
    Selected Mapping. Multiple phase-rotated candidate signals are evaluated
    and the candidate with the lowest PAPR is selected.

pts
    Partial Transmit Sequence. The OFDM symbol is partitioned into sub-blocks
    and optimized phase factors are applied.

tone_reservation
    Tone Reservation. Reserved subcarriers are used to construct a
    cancellation signal.

ace
    Active Constellation Extension. Constellation points are modified within
    allowed regions to reduce peaks.

Architecture
------------
The registry stores the public ``process()`` function of every available
method. The lower-level ``apply_*`` functions are also exported for direct
use when required.

Typical usage
-------------

    from papr_methods.registry import get_method

    processor = get_method("clipping")
    result = processor(signal, ...)

or:

    processor = get_method(PAPRMethod.CLIPPING)
    result = processor(signal, ...)

Method discovery
----------------

    from papr_methods.registry import list_methods

    print(list_methods())

The registry intentionally uses string keys because configuration files,
CLI arguments, experiment definitions, and serialized scenarios typically
represent algorithms as strings.

Stage-1 baseline
----------------
``none`` is a special reference method.

It must remain available because it establishes the unprocessed OFDM
reference against which all PAPR-reduction techniques are compared.

The registry therefore treats ``none`` as a mandatory built-in method.

Optional methods
----------------
Phase-2/Phase-3 methods may not be available in every installation. Optional
imports are therefore isolated and failure to import one optional algorithm
does not prevent the entire simulator from starting.

Important
---------
Do not silently replace a requested method with ``none``. Such fallback would
invalidate experiments because a simulation configured for SLM, PTS, ACE, or
Tone Reservation could accidentally run the baseline algorithm.

Instead, requesting an unavailable method raises ``KeyError`` with a useful
diagnostic message.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from ofdm_linksim.core.types import PAPRMethod


# ============================================================================
# Public callable type
# ============================================================================

PAPRProcessor = Callable[..., Any]


# ============================================================================
# Registry metadata
# ============================================================================


@dataclass(frozen=True)
class PAPRMethodInfo:
    """
    Descriptive metadata associated with one PAPR method.

    Parameters
    ----------
    name:
        Canonical registry name.

    description:
        Human-readable description suitable for logs, reports, or dashboards.

    implemented:
        Indicates whether the implementation is currently available.

    stage:
        Development stage of the implementation.

    reference:
        Optional short literature/reference identifier.

    aliases:
        Alternative names accepted by the registry.

    baseline:
        Whether the method is the locked reference baseline.

    """

    name: str
    description: str
    implemented: bool
    stage: str
    reference: Optional[str] = None
    aliases: tuple[str, ...] = ()
    baseline: bool = False


# ============================================================================
# Internal registries
# ============================================================================

# Main callable registry.
#
# The registry intentionally stores only process() callables. The public
# pipeline should interact with algorithms through this normalized interface.
_REGISTRY: Dict[str, PAPRProcessor] = {}


# Metadata registry.
_INFO: Dict[str, PAPRMethodInfo] = {}


# Alias -> canonical-name mapping.
_ALIASES: Dict[str, str] = {}


# ============================================================================
# Normalization helpers
# ============================================================================


def _normalize_name(name: str | PAPRMethod) -> str:
    """
    Normalize a PAPR method identifier.

    Parameters
    ----------
    name:
        String name or ``PAPRMethod`` enum member.

    Returns
    -------
    str
        Canonicalized lookup key.

    Raises
    ------
    TypeError
        If ``name`` is neither a string nor ``PAPRMethod``.
    """

    if isinstance(name, PAPRMethod):
        key = name.value
    elif isinstance(name, str):
        key = name
    else:
        raise TypeError(
            "PAPR method name must be a string or PAPRMethod enum member; "
            f"got {type(name).__name__}."
        )

    key = key.strip().lower()

    if not key:
        raise ValueError("PAPR method name cannot be empty.")

    return key


def _canonical_name(name: str | PAPRMethod) -> str:
    """
    Resolve a method name or alias to its canonical registry name.
    """

    key = _normalize_name(name)

    return _ALIASES.get(key, key)


# ============================================================================
# Registration
# ============================================================================


def register_method(
    name: str | PAPRMethod,
    processor: PAPRProcessor,
    *,
    description: str = "",
    implemented: bool = True,
    stage: str = "custom",
    reference: Optional[str] = None,
    aliases: Iterable[str] = (),
    baseline: bool = False,
    overwrite: bool = False,
) -> None:
    """
    Register a PAPR processing method.

    This function makes the registry extensible. New PAPR algorithms can be
    added without changing the OFDM pipeline.

    Parameters
    ----------
    name:
        Canonical method name.

    processor:
        Callable implementing the method.

    description:
        Human-readable description.

    implemented:
        Whether the processor is ready for use.

    stage:
        Development stage, e.g. ``Stage-1``, ``Phase-2``.

    reference:
        Optional literature reference.

    aliases:
        Alternative names.

    baseline:
        Marks the method as the locked reference baseline.

    overwrite:
        If False, attempting to replace an existing method raises an error.

    Raises
    ------
    TypeError
        If processor is not callable.

    ValueError
        If name or aliases are invalid.

    KeyError
        If the method already exists and overwrite is False.
    """

    canonical = _normalize_name(name)

    if not callable(processor):
        raise TypeError(
            f"Processor for PAPR method {canonical!r} must be callable."
        )

    if not canonical:
        raise ValueError("Canonical PAPR method name cannot be empty.")

    if canonical in _REGISTRY and not overwrite:
        raise KeyError(
            f"PAPR method {canonical!r} is already registered."
        )

    normalized_aliases: list[str] = []

    for alias in aliases:
        alias_key = _normalize_name(alias)

        if alias_key == canonical:
            continue

        if alias_key in normalized_aliases:
            continue

        normalized_aliases.append(alias_key)

    # Prevent aliases from silently pointing to another method.
    for alias_key in normalized_aliases:
        existing_target = _ALIASES.get(alias_key)

        if existing_target is not None and existing_target != canonical:
            raise KeyError(
                f"PAPR alias {alias_key!r} already points to "
                f"{existing_target!r}."
            )

        if alias_key in _REGISTRY and alias_key != canonical:
            raise KeyError(
                f"PAPR alias {alias_key!r} conflicts with an existing "
                "canonical method."
            )

    _REGISTRY[canonical] = processor

    _INFO[canonical] = PAPRMethodInfo(
        name=canonical,
        description=description,
        implemented=implemented,
        stage=stage,
        reference=reference,
        aliases=tuple(normalized_aliases),
        baseline=baseline,
    )

    for alias_key in normalized_aliases:
        _ALIASES[alias_key] = canonical


# ============================================================================
# Unregistration
# ============================================================================


def unregister_method(
    name: str | PAPRMethod,
    *,
    allow_baseline: bool = False,
) -> None:
    """
    Remove a registered PAPR method.

    This is primarily intended for testing, plugin systems, or controlled
    experimentation.

    The baseline ``none`` method is protected by default.
    """

    canonical = _canonical_name(name)

    if canonical not in _REGISTRY:
        raise KeyError(
            f"PAPR method {canonical!r} is not registered."
        )

    info = _INFO.get(canonical)

    if info is not None and info.baseline and not allow_baseline:
        raise RuntimeError(
            "The Stage-1 baseline method 'none' is protected and cannot "
            "be unregistered unless allow_baseline=True."
        )

    _REGISTRY.pop(canonical, None)
    _INFO.pop(canonical, None)

    aliases_to_remove = [
        alias
        for alias, target in _ALIASES.items()
        if target == canonical
    ]

    for alias in aliases_to_remove:
        _ALIASES.pop(alias, None)


# ============================================================================
# Lookup
# ============================================================================


def get_method(name: str | PAPRMethod) -> PAPRProcessor:
    """
    Return the ``process()`` callable for a PAPR method.

    Parameters
    ----------
    name:
        Method name or ``PAPRMethod`` enum member.

    Returns
    -------
    callable
        Registered PAPR processor.

    Raises
    ------
    KeyError
        If the method is unknown or unavailable.

    Examples
    --------
    >>> processor = get_method("none")
    >>> processor = get_method(PAPRMethod.NONE)

    Notes
    -----
    This function intentionally does NOT fall back to another method.
    """

    canonical = _canonical_name(name)

    if canonical not in _REGISTRY:
        available = ", ".join(list_methods())

        raise KeyError(
            f"Unknown or unavailable PAPR method: {canonical!r}. "
            f"Available methods: [{available}]"
        )

    return _REGISTRY[canonical]


def has_method(name: str | PAPRMethod) -> bool:
    """
    Return True if a PAPR method is registered.
    """

    try:
        canonical = _canonical_name(name)
    except (TypeError, ValueError):
        return False

    return canonical in _REGISTRY


def is_method_available(name: str | PAPRMethod) -> bool:
    """
    Return True if a method is registered and marked implemented.

    This is useful for experiment configuration validation.
    """

    try:
        canonical = _canonical_name(name)
    except (TypeError, ValueError):
        return False

    if canonical not in _REGISTRY:
        return False

    info = _INFO.get(canonical)

    if info is None:
        return True

    return info.implemented


# ============================================================================
# Method listing
# ============================================================================


def list_methods() -> list[str]:
    """
    Return canonical names of all registered PAPR methods.

    The result is sorted for deterministic configuration files, logs,
    experiment reports, and tests.
    """

    return sorted(_REGISTRY.keys())


def list_aliases() -> dict[str, str]:
    """
    Return a copy of the alias-to-canonical-name mapping.
    """

    return dict(sorted(_ALIASES.items()))


def list_implemented_methods() -> list[str]:
    """
    Return only methods currently marked as implemented.
    """

    return sorted(
        name
        for name, info in _INFO.items()
        if info.implemented and name in _REGISTRY
    )


def list_baseline_methods() -> list[str]:
    """
    Return registered baseline methods.

    In the current architecture this should normally contain only ``none``.
    """

    return sorted(
        name
        for name, info in _INFO.items()
        if info.baseline and name in _REGISTRY
    )


# ============================================================================
# Metadata
# ============================================================================


def get_method_info(
    name: str | PAPRMethod,
) -> PAPRMethodInfo:
    """
    Return metadata for a registered PAPR method.
    """

    canonical = _canonical_name(name)

    if canonical not in _INFO:
        raise KeyError(
            f"No metadata registered for PAPR method {canonical!r}."
        )

    return _INFO[canonical]


def get_method_description(name: str | PAPRMethod) -> str:
    """
    Return the human-readable description of a PAPR method.
    """

    return get_method_info(name).description


def get_method_stage(name: str | PAPRMethod) -> str:
    """
    Return the development stage of a PAPR method.
    """

    return get_method_info(name).stage


def get_method_reference(
    name: str | PAPRMethod,
) -> Optional[str]:
    """
    Return the optional literature/reference identifier.
    """

    return get_method_info(name).reference


def method_metadata(
    name: str | PAPRMethod,
) -> Mapping[str, Any]:
    """
    Return method metadata as a read-only-style mapping.

    A new dictionary is returned so callers cannot mutate the registry's
    internal metadata.
    """

    info = get_method_info(name)

    return {
        "name": info.name,
        "description": info.description,
        "implemented": info.implemented,
        "stage": info.stage,
        "reference": info.reference,
        "aliases": list(info.aliases),
        "baseline": info.baseline,
    }


def all_method_metadata() -> dict[str, dict[str, Any]]:
    """
    Return metadata for every registered method.
    """

    return {
        name: dict(method_metadata(name))
        for name in list_methods()
    }


# ============================================================================
# Concrete method imports
# ============================================================================

# ---------------------------------------------------------------------------
# Stage-1 reference
# ---------------------------------------------------------------------------

from papr_methods.none import (  # noqa: E402
    apply_none,
    process as process_none,
)


# ---------------------------------------------------------------------------
# Clipping
# ---------------------------------------------------------------------------

from papr_methods.clipping import (  # noqa: E402
    apply_clipping,
    process as process_clipping,
)


# ---------------------------------------------------------------------------
# Selected Mapping
# ---------------------------------------------------------------------------

try:
    from papr_methods.slm import (  # noqa: E402
        apply_slm,
        process as process_slm,
    )
except Exception:  # pragma: no cover
    apply_slm = None  # type: ignore[assignment]
    process_slm = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Partial Transmit Sequence
# ---------------------------------------------------------------------------

try:
    from papr_methods.pts import (  # noqa: E402
        apply_pts,
        process as process_pts,
    )
except Exception:  # pragma: no cover
    apply_pts = None  # type: ignore[assignment]
    process_pts = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Tone Reservation
# ---------------------------------------------------------------------------

try:
    from papr_methods.tone_reservation import (  # noqa: E402
        apply_tone_reservation,
        process as process_tone_reservation,
    )
except Exception:  # pragma: no cover
    apply_tone_reservation = None  # type: ignore[assignment]
    process_tone_reservation = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Active Constellation Extension
# ---------------------------------------------------------------------------

try:
    from papr_methods.ace import (  # noqa: E402
        apply_ace,
        process as process_ace,
    )
except Exception:  # pragma: no cover
    apply_ace = None  # type: ignore[assignment]
    process_ace = None  # type: ignore[assignment]


# ============================================================================
# Built-in registrations
# ============================================================================


def _register_builtin_methods() -> None:
    """
    Register all built-in PAPR algorithms.

    This function is called exactly once when the module is imported.
    """

    # ------------------------------------------------------------------------
    # NONE
    # ------------------------------------------------------------------------

    register_method(
        PAPRMethod.NONE,
        process_none,
        description=(
            "Unprocessed OFDM reference. No PAPR reduction is applied."
        ),
        implemented=True,
        stage="Stage-1",
        aliases=(
            "identity",
            "baseline",
            "off",
            "no_papr",
        ),
        baseline=True,
    )

    # ------------------------------------------------------------------------
    # CLIPPING
    # ------------------------------------------------------------------------

    register_method(
        PAPRMethod.CLIPPING,
        process_clipping,
        description=(
            "Amplitude clipping for reducing high OFDM signal peaks."
        ),
        implemented=True,
        stage="Stage-1/Phase-2",
        aliases=(
            "clip",
            "amplitude_clipping",
        ),
        baseline=False,
    )

    # ------------------------------------------------------------------------
    # SLM
    # ------------------------------------------------------------------------

    if process_slm is not None:
        register_method(
            PAPRMethod.SLM,
            process_slm,
            description=(
                "Selected Mapping using multiple phase-rotated candidates "
                "and minimum-PAPR selection."
            ),
            implemented=True,
            stage="Phase-2",
            reference="SLM",
            aliases=(
                "selected_mapping",
                "selected-mapping",
            ),
        )

    # ------------------------------------------------------------------------
    # PTS
    # ------------------------------------------------------------------------

    if process_pts is not None:
        register_method(
            PAPRMethod.PTS,
            process_pts,
            description=(
                "Partial Transmit Sequence optimization using phase "
                "factors over OFDM sub-blocks."
            ),
            implemented=True,
            stage="Phase-2",
            reference="PTS",
            aliases=(
                "partial_transmit_sequence",
                "partial-transmit-sequence",
            ),
        )

    # ------------------------------------------------------------------------
    # Tone Reservation
    # ------------------------------------------------------------------------

    if process_tone_reservation is not None:
        register_method(
            PAPRMethod.TONE_RESERVATION,
            process_tone_reservation,
            description=(
                "Tone Reservation using reserved subcarriers to construct "
                "a peak-cancellation signal."
            ),
            implemented=True,
            stage="Phase-2",
            reference="Tone Reservation",
            aliases=(
                "tone-reservation",
                "tr",
                "tone_res",
            ),
        )

    # ------------------------------------------------------------------------
    # ACE
    # ------------------------------------------------------------------------

    if process_ace is not None:
        register_method(
            PAPRMethod.ACE,
            process_ace,
            description=(
                "Active Constellation Extension for reducing OFDM peaks "
                "while preserving the allowed constellation regions."
            ),
            implemented=True,
            stage="Phase-2",
            reference="ACE",
            aliases=(
                "active_constellation_extension",
                "active-constellation-extension",
            ),
        )


# Initialize built-in registry.
_register_builtin_methods()


# ============================================================================
# Registry diagnostics
# ============================================================================


def registry_status() -> dict[str, Any]:
    """
    Return a compact diagnostic snapshot of the registry.

    This is useful for startup logs, debugging, CI tests, and experiment
    reports.
    """

    methods = list_methods()

    return {
        "method_count": len(methods),
        "methods": methods,
        "implemented_methods": list_implemented_methods(),
        "baseline_methods": list_baseline_methods(),
        "aliases": list_aliases(),
    }


def validate_registry() -> None:
    """
    Validate registry consistency.

    Raises
    ------
    RuntimeError
        If the registry is internally inconsistent.

    Notes
    -----
    The Stage-1 baseline ``none`` is mandatory.
    """

    # The reference implementation must always exist.
    if PAPRMethod.NONE.value not in _REGISTRY:
        raise RuntimeError(
            "PAPR registry integrity failure: mandatory baseline "
            "'none' is not registered."
        )

    if PAPRMethod.NONE.value not in _INFO:
        raise RuntimeError(
            "PAPR registry integrity failure: baseline metadata is missing."
        )

    none_info = _INFO[PAPRMethod.NONE.value]

    if not none_info.baseline:
        raise RuntimeError(
            "PAPR registry integrity failure: 'none' must be marked "
            "as the baseline method."
        )

    # Every registered callable must have metadata.
    for name in _REGISTRY:
        if name not in _INFO:
            raise RuntimeError(
                f"PAPR registry integrity failure: method {name!r} "
                "has no metadata."
            )

        if not callable(_REGISTRY[name]):
            raise RuntimeError(
                f"PAPR registry integrity failure: method {name!r} "
                "processor is not callable."
            )

    # Every alias must point to a real canonical method.
    for alias, target in _ALIASES.items():
        if target not in _REGISTRY:
            raise RuntimeError(
                f"PAPR registry integrity failure: alias {alias!r} "
                f"points to missing method {target!r}."
            )

        if alias in _REGISTRY:
            raise RuntimeError(
                f"PAPR registry integrity failure: alias {alias!r} "
                "conflicts with a canonical method."
            )

    # Verify metadata aliases.
    for name, info in _INFO.items():
        for alias in info.aliases:
            if _ALIASES.get(alias) != name:
                raise RuntimeError(
                    f"PAPR registry integrity failure: metadata alias "
                    f"{alias!r} does not point to {name!r}."
                )


# Validate immediately so import-time corruption is caught early.
validate_registry()


# ============================================================================
# Public exports
# ============================================================================

__all__ = [
    # Types
    "PAPRProcessor",
    "PAPRMethodInfo",

    # Reference implementation
    "apply_none",
    "process_none",

    # Clipping
    "apply_clipping",
    "process_clipping",

    # Optional algorithms
    "apply_slm",
    "process_slm",
    "apply_pts",
    "process_pts",
    "apply_tone_reservation",
    "process_tone_reservation",
    "apply_ace",
    "process_ace",

    # Registry operations
    "register_method",
    "unregister_method",
    "get_method",
    "has_method",
    "is_method_available",

    # Listing
    "list_methods",
    "list_implemented_methods",
    "list_baseline_methods",
    "list_aliases",

    # Metadata
    "get_method_info",
    "get_method_description",
    "get_method_stage",
    "get_method_reference",
    "method_metadata",
    "all_method_metadata",

    # Diagnostics
    "registry_status",
    "validate_registry",

    # Enum
    "PAPRMethod",
]
