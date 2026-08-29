"""
OFDM-PAPR-LinkSim
=================

Core pipeline orchestration layer.

This module defines the execution engine for the OFDM-PAPR-LinkSim
research framework.  It coordinates the communication-system blocks but
does not implement communication algorithms itself.

The architectural authority for this module is ``core.types``.

That rule is intentional:

    types.py
        ↓
    pipeline.py
        ↓
    blocks / papr_methods / analyzers / scenarios

NOT:

    pipeline.py
        ↓
    force types.py to adapt later

The data contracts defined in ``core.types`` therefore determine the
shape and semantics of the pipeline.

-------------------------------------------------------------------------------
PIPELINE ARCHITECTURE
-------------------------------------------------------------------------------

Transmitter:

    source
        ↓
    encoder                    [optional / identity]
        ↓
    interleaver                [optional / identity]
        ↓
    modulator
        ↓
    OFDM modulator
        ↓
    TransmitFrame

PAPR:

    TransmitFrame
        ↓
    PAPR processor / analyzer
        ↓
    PAPRResult

Channel:

    TransmitFrame.waveform
        ↓
    channel
        ↓
    ChannelOutput

Receiver:

    ChannelOutput
        ↓
    synchronizer               [optional / identity]
        ↓
    equalizer                  [optional / identity]
        ↓
    OFDM demodulator
        ↓
    OFDM-domain result
        ↓
    data-subcarrier extraction
        ↓
    demodulator
        ↓
    deinterleaver              [optional / identity]
        ↓
    decoder                    [optional / identity]
        ↓
    ReceiveFrame

Analysis:

    TransmitFrame
        +
    ReceiveFrame
        +
    source_bits
        ↓
    analyzers
        ↓
    ExperimentResult

-------------------------------------------------------------------------------
DESIGN PRINCIPLES
-------------------------------------------------------------------------------

1. ``core.types`` is the source of truth for data contracts.

2. Required stages never silently become identity functions.

3. Optional stages may use identity behaviour when explicitly allowed.

4. ``fail_on_missing_stage`` controls optional-stage policy only.

5. The source seed is owned by the pipeline invocation.

6. ``SimulationMetadata.seed`` must agree with the actual execution seed.

7. ``SimulationMetadata`` is validated before the experiment starts.

8. A fresh ``PipelineContext`` belongs to every execution.

9. ``ReceiveFrame`` is constructed exactly once, at the end of the
   receiver chain.

10. The OFDM demodulator must return an OFDM-domain result contract,
    not a prematurely completed ``ReceiveFrame``.

11. ``OFDMGrid.get_data_symbols()`` is used as the canonical extraction
    mechanism.

12. ``ChannelOutput`` is the canonical channel boundary.

13. ``TransmitFrame`` is the canonical transmitter boundary.

14. ``ExperimentResult`` is the canonical experiment boundary.

15. No algorithmic implementation belongs in this module.

16. No global random state is used.

17. No global mutable execution state is used.

18. Components are dependency-injected.

19. Components can be replaced independently for research experiments.

20. Stage-1 uncoded/no-interleaving experiments remain first-class.

-------------------------------------------------------------------------------
STAGE-1 CONTRACT
-------------------------------------------------------------------------------

The locked baseline is:

    CodingType.NONE
    InterleavingType.NONE
    PAPRMethod.NONE
    ChannelType.AWGN
    EqualizerType.NONE

with QPSK as the primary baseline modulation.

The architecture nevertheless preserves:

    source_bits
    coded_bits
    interleaved_bits

inside ``TransmitFrame`` so future LDPC / Polar / Turbo / interleaving
implementations do not require an architectural rewrite.

-------------------------------------------------------------------------------
IMPORTANT CONTRACT WITH types.py
-------------------------------------------------------------------------------

``TransmitFrame`` already contains:

    source_bits
    coded_bits
    interleaved_bits
    modulation_symbols
    ofdm_grid
    waveform

``ReceiveFrame`` already contains:

    received_waveform
    ofdm_grid
    equalized_symbols
    demodulated_bits
    decoded_bits

``ChannelOutput`` already contains:

    signal
    snr_db
    channel_type
    noise_power
    channel_gain

``ExperimentResult`` already contains:

    metadata
    papr
    ccdf
    papr_statistics
    ber
    evm
    psd
    constellation
    notes
    extra

The pipeline therefore does not invent replacement containers for these
objects.

-------------------------------------------------------------------------------
TEMPORARY OFDM DEMODULATION CONTRACT
-------------------------------------------------------------------------------

At the moment ``types.py`` does not expose a dedicated
``OFDMDemodulationResult`` container.

Until that formal type is introduced, this module uses the structural
``OFDMDemodResultLike`` Protocol.

The expected result is:

    received_waveform : OFDMSignal
    ofdm_grid         : OFDMGrid
    equalized_symbols : ComplexArray

When ``types.py`` eventually introduces:

    OFDMDemodulationResult

the Protocol can be removed and the concrete type imported instead.

The receiver architecture itself does not need to change.
"""

from __future__ import annotations

# =============================================================================
# Standard library imports
# =============================================================================

from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Mapping,
    MutableMapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeAlias,
    runtime_checkable,
)

# =============================================================================
# Third-party imports
# =============================================================================

import numpy as np

# =============================================================================
# Project contracts
# =============================================================================

from .types import (
    BitArray,
    ChannelOutput,
    ComplexArray,
    ExperimentResult,
    OFDMGrid,
    OFDMSignal,
    PAPRResult,
    ReceiveFrame,
    SimulationMetadata,
    TransmitFrame,
    validate_bits,
    validate_complex_signal,
    validate_fft_size,
    validate_oversampling,
    validate_positive_integer,
)


# =============================================================================
# Public type aliases
# =============================================================================

BitsStage: TypeAlias = Callable[..., BitArray]

SymbolStage: TypeAlias = Callable[..., ComplexArray]

SourceStage: TypeAlias = Callable[..., BitArray]

OFDMModulatorStage: TypeAlias = Callable[..., TransmitFrame]

ChannelStage: TypeAlias = Callable[..., ChannelOutput]

PAPRStage: TypeAlias = Callable[..., Any]

SynchronizerStage: TypeAlias = Callable[..., Any]

EqualizerStage: TypeAlias = Callable[..., Any]

DemodulatorStage: TypeAlias = Callable[..., BitArray]

AnalyzerStage: TypeAlias = Callable[..., Any]

GenericStage: TypeAlias = Callable[..., Any]


# =============================================================================
# OFDM demodulator structural contract
# =============================================================================


@runtime_checkable
class OFDMDemodResultLike(Protocol):
    """
    Temporary structural contract for OFDM demodulator output.

    This protocol deliberately mirrors the information already represented
    by the core types:

        received waveform
        OFDM frequency-domain grid
        equalized data representation

    It does NOT contain demodulated bits.

    Demodulated bits belong to the subsequent demodulator stage.

    It does NOT contain decoded bits.

    Decoded bits belong to the subsequent decoder stage.

    This separation is important because the OFDM demodulator is a waveform
    / frequency-domain operation, whereas demodulation and decoding are
    bit-domain operations.
    """

    received_waveform: OFDMSignal
    ofdm_grid: OFDMGrid
    equalized_symbols: ComplexArray


# =============================================================================
# Pipeline exceptions
# =============================================================================


class PipelineError(RuntimeError):
    """
    Base exception for pipeline execution failures.
    """


class PipelineConfigurationError(PipelineError):
    """
    Raised when the pipeline is incorrectly assembled.
    """


class PipelineStageError(PipelineError):
    """
    Raised when an injected stage violates its execution contract.
    """


class PipelineValidationError(PipelineError):
    """
    Raised when a stage returns structurally invalid data.
    """


# =============================================================================
# Identity stages
# =============================================================================


def _identity_bits(
    bits: BitArray,
    **_: Any,
) -> BitArray:
    """
    Identity operation for optional bit-processing stages.

    Used for the Stage-1:

        encoder
        interleaver
        deinterleaver
        decoder

    No numerical transformation is performed.
    """

    return np.asarray(bits)


def _identity_stage(
    value: Any,
    **_: Any,
) -> Any:
    """
    Generic identity operation for optional signal-domain stages.

    This is scientifically valid only where disabling the stage means
    "do nothing", such as:

        synchronization disabled
        equalization disabled
    """

    return value


# =============================================================================
# Pipeline execution context
# =============================================================================


@dataclass(slots=True)
class PipelineContext:
    """
    Mutable transient state for one pipeline execution.

    The context is intentionally separate from ``ExperimentResult``.

    ``ExperimentResult`` is a public scientific result.

    ``PipelineContext`` is an internal execution record.

    A fresh context is created for every call to ``OFDMChain.run()``.
    """

    source_bits: Optional[BitArray] = None

    transmit_frame: Optional[TransmitFrame] = None

    receive_frame: Optional[ReceiveFrame] = None

    channel_output: Optional[ChannelOutput] = None

    papr_result: Optional[PAPRResult] = None

    analysis_results: Dict[str, Any] = field(
        default_factory=dict
    )

    intermediate: Dict[str, Any] = field(
        default_factory=dict
    )

    stage_trace: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    def mark(
        self,
        stage_name: str,
    ) -> None:
        """
        Record successful completion of a pipeline stage.
        """

        if not isinstance(stage_name, str):
            raise TypeError(
                "stage_name must be a string."
            )

        if not stage_name.strip():
            raise ValueError(
                "stage_name cannot be empty."
            )

        self.stage_trace.append(
            stage_name
        )

    def store(
        self,
        name: str,
        value: Any,
    ) -> None:
        """
        Store an intermediate execution object.
        """

        if not isinstance(name, str):
            raise TypeError(
                "Intermediate result name must be a string."
            )

        if not name.strip():
            raise ValueError(
                "Intermediate result name cannot be empty."
            )

        self.intermediate[name] = value

    def get(
        self,
        name: str,
        default: Any = None,
    ) -> Any:
        """
        Retrieve an intermediate execution object.
        """

        return self.intermediate.get(
            name,
            default,
        )

    def warn(
        self,
        message: str,
    ) -> None:
        """
        Store a non-fatal pipeline diagnostic.
        """

        if not isinstance(message, str):
            raise TypeError(
                "Pipeline warning must be a string."
            )

        if message:
            self.warnings.append(
                message
            )

    def reset(self) -> None:
        """
        Clear all transient execution state.
        """

        self.source_bits = None
        self.transmit_frame = None
        self.receive_frame = None
        self.channel_output = None
        self.papr_result = None

        self.analysis_results.clear()
        self.intermediate.clear()
        self.stage_trace.clear()
        self.warnings.clear()


# =============================================================================
# Pipeline options
# =============================================================================


@dataclass(frozen=True, slots=True)
class PipelineOptions:
    """
    Runtime execution switches.

    Scientific configuration does not belong here.

    Scientific parameters such as:

        FFT size
        modulation
        SNR
        channel model
        PAPR method
        coding
        interleaving

    belong to the scenario/configuration layer and are represented in
    ``SimulationMetadata`` / ``ConfigSnapshot``.

    These options only control execution flow.
    """

    run_papr: bool = True

    run_channel: bool = True

    run_receiver: bool = True

    run_analysis: bool = True

    fail_on_missing_stage: bool = False

    validate_metadata_consistency: bool = True

    validate_frame_consistency: bool = True

    preserve_context_diagnostics: bool = True

    def __post_init__(self) -> None:
        """
        Validate runtime flags.
        """

        for name in (
            "run_papr",
            "run_channel",
            "run_receiver",
            "run_analysis",
            "fail_on_missing_stage",
            "validate_metadata_consistency",
            "validate_frame_consistency",
            "preserve_context_diagnostics",
        ):
            value = getattr(
                self,
                name,
            )

            if not isinstance(value, bool):
                raise TypeError(
                    f"{name} must be a boolean."
                )


# =============================================================================
# Pipeline components
# =============================================================================


@dataclass(slots=True)
class PipelineComponents:
    """
    Dependency-injected communication-system components.

    Required components
    -------------------

    Always required:

        source
        modulator
        ofdm_modulator

    Conditionally required:

        papr_processor
            when run_papr=True

        channel
            when run_channel=True

        ofdm_demodulator
            when run_receiver=True

        demodulator
            when run_receiver=True

    Optional components
    -------------------

        encoder
        interleaver
        synchronizer
        equalizer
        deinterleaver
        decoder

    Optional components use identity behaviour when:

        fail_on_missing_stage=False

    and fail explicitly when:

        fail_on_missing_stage=True

    ``papr_processor`` is NOT treated as an identity stage.

    PAPR processing is a scientific operation and therefore must be
    explicitly supplied whenever PAPR execution is enabled.
    """

    source: Optional[SourceStage] = None

    encoder: Optional[BitsStage] = None

    interleaver: Optional[BitsStage] = None

    modulator: Optional[SymbolStage] = None

    ofdm_modulator: Optional[OFDMModulatorStage] = None

    papr_processor: Optional[PAPRStage] = None

    channel: Optional[ChannelStage] = None

    synchronizer: Optional[SynchronizerStage] = None

    equalizer: Optional[EqualizerStage] = None

    ofdm_demodulator: Optional[GenericStage] = None

    demodulator: Optional[DemodulatorStage] = None

    deinterleaver: Optional[BitsStage] = None

    decoder: Optional[BitsStage] = None

    analyzers: MutableMapping[
        str,
        AnalyzerStage,
    ] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """
        Validate component registration.
        """

        for name in (
            "source",
            "encoder",
            "interleaver",
            "modulator",
            "ofdm_modulator",
            "papr_processor",
            "channel",
            "synchronizer",
            "equalizer",
            "ofdm_demodulator",
            "demodulator",
            "deinterleaver",
            "decoder",
        ):
            component = getattr(
                self,
                name,
            )

            if component is not None and not callable(
                component
            ):
                raise TypeError(
                    f"Pipeline component '{name}' must be callable."
                )

        if self.analyzers is None:
            raise TypeError(
                "analyzers cannot be None."
            )

        for name, analyzer in self.analyzers.items():
            if not isinstance(name, str):
                raise TypeError(
                    "Analyzer names must be strings."
                )

            if not name.strip():
                raise ValueError(
                    "Analyzer names cannot be empty."
                )

            if not callable(analyzer):
                raise TypeError(
                    f"Analyzer '{name}' must be callable."
                )


# =============================================================================
# OFDM Chain
# =============================================================================


@dataclass(slots=True)
class OFDMChain:
    """
    High-level deterministic OFDM simulation orchestrator.

    This class coordinates injected components.

    It does not implement:

        modulation mathematics
        FFT/IFFT mathematics
        channel mathematics
        PAPR mathematics
        synchronization algorithms
        equalization algorithms
        coding algorithms
        BER mathematics
        EVM mathematics
        PSD mathematics

    Those responsibilities remain in their respective modules.
    """

    components: PipelineComponents

    options: PipelineOptions = field(
        default_factory=PipelineOptions
    )

    # =========================================================================
    # Construction
    # =========================================================================

    def __post_init__(self) -> None:
        """
        Validate the pipeline assembly itself.
        """

        if not isinstance(
            self.components,
            PipelineComponents,
        ):
            raise TypeError(
                "components must be a PipelineComponents instance."
            )

        if not isinstance(
            self.options,
            PipelineOptions,
        ):
            raise TypeError(
                "options must be a PipelineOptions instance."
            )

    # =========================================================================
    # Required component resolution
    # =========================================================================

    def _require_component(
        self,
        component: Optional[Callable[..., Any]],
        name: str,
    ) -> Callable[..., Any]:
        """
        Resolve a mandatory pipeline component.

        Mandatory components never fall back to identity.

        This distinction is fundamental.

        A missing OFDM modulator, channel or demodulator is not equivalent
        to a disabled operation.
        """

        if component is None:
            raise PipelineConfigurationError(
                f"Required pipeline stage '{name}' "
                "is not configured."
            )

        if not callable(component):
            raise PipelineConfigurationError(
                f"Pipeline stage '{name}' "
                "must be callable."
            )

        return component

    # =========================================================================
    # Optional component resolution
    # =========================================================================

    def _optional_component(
        self,
        component: Optional[Callable[..., Any]],
        name: str,
        *,
        identity: Callable[..., Any],
    ) -> Callable[..., Any]:
        """
        Resolve an optional component.

        Missing optional stages either:

            fail

        or:

            become an explicit identity operation

        according to ``fail_on_missing_stage``.
        """

        if component is not None:
            if not callable(component):
                raise PipelineConfigurationError(
                    f"Optional pipeline stage '{name}' "
                    "must be callable."
                )

            return component

        if self.options.fail_on_missing_stage:
            raise PipelineConfigurationError(
                f"Optional pipeline stage '{name}' "
                "is not configured and "
                "fail_on_missing_stage=True."
            )

        return identity

    # =========================================================================
    # Source validation
    # =========================================================================

    @staticmethod
    def _validate_n_bits(
        n_bits: int,
    ) -> int:
        """
        Validate the requested source length.
        """

        if not isinstance(
            n_bits,
            (int, np.integer),
        ):
            raise TypeError(
                "n_bits must be an integer."
            )

        n_bits = int(n_bits)

        if n_bits <= 0:
            raise ValueError(
                "n_bits must be positive."
            )

        return n_bits

    # =========================================================================
    # Seed validation
    # =========================================================================

    @staticmethod
    def _validate_seed(
        seed: int,
    ) -> int:
        """
        Validate and normalize the experiment seed.

        The project uses positive seeds in ``SimulationMetadata``.
        """

        if not isinstance(
            seed,
            (int, np.integer),
        ):
            raise TypeError(
                "seed must be an integer."
            )

        seed = int(seed)

        if seed <= 0:
            raise ValueError(
                "seed must be positive."
            )

        return seed

    # =========================================================================
    # Metadata validation
    # =========================================================================

    def _validate_metadata(
        self,
        *,
        metadata: SimulationMetadata,
        seed: int,
    ) -> None:
        """
        Validate metadata before executing the experiment.

        The pipeline does not mutate metadata.

        Instead, it verifies that the execution request is compatible
        with the metadata describing the resulting experiment.
        """

        if not isinstance(
            metadata,
            SimulationMetadata,
        ):
            raise TypeError(
                "metadata must be a SimulationMetadata instance."
            )

        if metadata.seed != seed:
            raise PipelineValidationError(
                "Execution seed does not match "
                "SimulationMetadata.seed: "
                f"execution={seed}, "
                f"metadata={metadata.seed}."
            )

        if metadata.n_ofdm_symbols <= 0:
            raise PipelineValidationError(
                "metadata.n_ofdm_symbols must be positive."
            )

        validate_fft_size(
            metadata.fft_size
        )

        validate_oversampling(
            metadata.oversampling
        )

    # =========================================================================
    # Source stage
    # =========================================================================

    def generate_source_bits(
        self,
        *,
        n_bits: int,
        rng: np.random.Generator,
        **kwargs: Any,
    ) -> BitArray:
        """
        Generate source bits.

        The source implementation owns the actual generation policy.

        The pipeline only owns:

            RNG injection
            shape validation
            bit-domain validation
        """

        n_bits = self._validate_n_bits(
            n_bits
        )

        if not isinstance(
            rng,
            np.random.Generator,
        ):
            raise TypeError(
                "rng must be a numpy.random.Generator."
            )

        source = self._require_component(
            self.components.source,
            "source",
        )

        try:
            bits = source(
                n_bits=n_bits,
                rng=rng,
                **kwargs,
            )
        except Exception as exc:
            raise PipelineStageError(
                "Source stage failed."
            ) from exc

        bits = np.asarray(
            bits
        )

        if bits.size != n_bits:
            raise PipelineValidationError(
                "Source returned an unexpected number "
                f"of bits: expected={n_bits}, "
                f"received={bits.size}."
            )

        validate_bits(
            bits
        )

        return bits

    # =========================================================================
    # Bit-stage execution
    # =========================================================================

    def _run_bit_stage(
        self,
        *,
        stage: Callable[..., Any],
        name: str,
        bits: BitArray,
        **kwargs: Any,
    ) -> BitArray:
        """
        Execute a bit-processing stage and validate its output.
        """

        try:
            output = stage(
                bits,
                **kwargs,
            )
        except Exception as exc:
            raise PipelineStageError(
                f"Bit-processing stage '{name}' failed."
            ) from exc

        output = np.asarray(
            output
        )

        validate_bits(
            output
        )

        return output

    # =========================================================================
    # Modulator execution
    # =========================================================================

    def _run_modulator(
        self,
        *,
        bits: BitArray,
        **kwargs: Any,
    ) -> ComplexArray:
        """
        Execute digital modulation.
        """

        modulator = self._require_component(
            self.components.modulator,
            "modulator",
        )

        try:
            symbols = modulator(
                bits,
                **kwargs,
            )
        except Exception as exc:
            raise PipelineStageError(
                "Modulation stage failed."
            ) from exc

        symbols = np.asarray(
            symbols
        )

        if not np.iscomplexobj(
            symbols
        ):
            raise PipelineValidationError(
                "modulator must return a "
                "complex-valued NumPy array."
            )

        if symbols.size == 0:
            raise PipelineValidationError(
                "modulator returned an empty symbol array."
            )

        return symbols

    # =========================================================================
    # OFDM modulator execution
    # =========================================================================

    def _run_ofdm_modulator(
        self,
        *,
        symbols: ComplexArray,
        source_bits: BitArray,
        coded_bits: BitArray,
        interleaved_bits: BitArray,
        rng: np.random.Generator,
        **kwargs: Any,
    ) -> TransmitFrame:
        """
        Execute OFDM modulation.

        The OFDM modulator owns construction of the canonical
        ``TransmitFrame``.

        The pipeline verifies that the returned object is exactly the
        contract declared by ``core.types``.
        """

        ofdm_modulator = self._require_component(
            self.components.ofdm_modulator,
            "ofdm_modulator",
        )

        try:
            frame = ofdm_modulator(
                symbols,
                source_bits=source_bits,
                coded_bits=coded_bits,
                interleaved_bits=interleaved_bits,
                rng=rng,
                **kwargs,
            )
        except Exception as exc:
            raise PipelineStageError(
                "OFDM modulation stage failed."
            ) from exc

        if not isinstance(
            frame,
            TransmitFrame,
        ):
            raise PipelineValidationError(
                "ofdm_modulator must return "
                "a TransmitFrame instance."
            )

        return frame

    # =========================================================================
    # Transmitter
    # =========================================================================

    def run_transmitter(
        self,
        *,
        source_bits: BitArray,
        rng: np.random.Generator,
        **kwargs: Any,
    ) -> TransmitFrame:
        """
        Execute the complete transmitter.

        Pipeline:

            source
              ↓
            encoder
              ↓
            interleaver
              ↓
            modulator
              ↓
            OFDM modulator
              ↓
            TransmitFrame

        In Stage-1:

            encoder      = identity
            interleaver  = identity

        The fields are nevertheless retained in TransmitFrame because
        the core type explicitly preserves the complete data lineage.
        """

        validate_bits(
            source_bits
        )

        encoder = self._optional_component(
            self.components.encoder,
            "encoder",
            identity=_identity_bits,
        )

        interleaver = self._optional_component(
            self.components.interleaver,
            "interleaver",
            identity=_identity_bits,
        )

        coded_bits = self._run_bit_stage(
            stage=encoder,
            name="encoder",
            bits=source_bits,
            **kwargs,
        )

        interleaved_bits = self._run_bit_stage(
            stage=interleaver,
            name="interleaver",
            bits=coded_bits,
            **kwargs,
        )

        symbols = self._run_modulator(
            bits=interleaved_bits,
            **kwargs,
        )

        frame = self._run_ofdm_modulator(
            symbols=symbols,
            source_bits=source_bits,
            coded_bits=coded_bits,
            interleaved_bits=interleaved_bits,
            rng=rng,
            **kwargs,
        )

        if self.options.validate_frame_consistency:
            self._validate_transmit_frame_lineage(
                frame,
                source_bits=source_bits,
                coded_bits=coded_bits,
                interleaved_bits=interleaved_bits,
                modulation_symbols=symbols,
            )

        return frame

    # =========================================================================
    # TransmitFrame validation
    # =========================================================================

    @staticmethod
    def _validate_transmit_frame_lineage(
        frame: TransmitFrame,
        *,
        source_bits: BitArray,
        coded_bits: BitArray,
        interleaved_bits: BitArray,
        modulation_symbols: ComplexArray,
    ) -> None:
        """
        Verify that the returned TransmitFrame preserves the data lineage
        established by the pipeline.

        The arrays are compared by content rather than object identity.
        """

        if not np.array_equal(
            frame.source_bits,
            source_bits,
        ):
            raise PipelineValidationError(
                "TransmitFrame.source_bits does not match "
                "the source stage output."
            )

        if not np.array_equal(
            frame.coded_bits,
            coded_bits,
        ):
            raise PipelineValidationError(
                "TransmitFrame.coded_bits does not match "
                "the encoder output."
            )

        if not np.array_equal(
            frame.interleaved_bits,
            interleaved_bits,
        ):
            raise PipelineValidationError(
                "TransmitFrame.interleaved_bits does not match "
                "the interleaver output."
            )

        if not np.array_equal(
            frame.modulation_symbols,
            modulation_symbols,
        ):
            raise PipelineValidationError(
                "TransmitFrame.modulation_symbols does not match "
                "the modulation output."
            )

    # =========================================================================
    # PAPR
    # =========================================================================

    def run_papr(
        self,
        transmit_frame: TransmitFrame,
        *,
        rng: np.random.Generator,
        **kwargs: Any,
    ) -> PAPRResult:
        """
        Execute the configured PAPR operation.

        The PAPR component may internally perform:

            measurement
            reduction
            analysis

        but the canonical scalar measurement returned by this pipeline
        boundary is ``PAPRResult``.

        The PAPR definition itself belongs to ``core.types`` and the
        PAPR implementation module.
        """

        processor = self._require_component(
            self.components.papr_processor,
            "papr_processor",
        )

        try:
            result = processor(
                transmit_frame,
                rng=rng,
                **kwargs,
            )
        except Exception as exc:
            raise PipelineStageError(
                "PAPR stage failed."
            ) from exc

        if not isinstance(
            result,
            PAPRResult,
        ):
            raise PipelineValidationError(
                "papr_processor must return "
                "a PAPRResult instance."
            )

        return result

    # =========================================================================
    # Channel
    # =========================================================================

    def run_channel(
        self,
        transmit_frame: TransmitFrame,
        *,
        rng: np.random.Generator,
        **kwargs: Any,
    ) -> ChannelOutput:
        """
        Execute the configured channel.

        The canonical channel boundary is ``ChannelOutput``.

        The pipeline deliberately does not pass an arbitrary ``Any`` object
        into the receiver.
        """

        channel = self._require_component(
            self.components.channel,
            "channel",
        )

        try:
            output = channel(
                transmit_frame,
                rng=rng,
                **kwargs,
            )
        except Exception as exc:
            raise PipelineStageError(
                "Channel stage failed."
            ) from exc

        if not isinstance(
            output,
            ChannelOutput,
        ):
            raise PipelineValidationError(
                "channel must return "
                "a ChannelOutput instance."
            )

        return output

    # =========================================================================
    # Synchronization
    # =========================================================================

    def _run_synchronizer(
        self,
        channel_output: ChannelOutput,
        *,
        rng: np.random.Generator,
        **kwargs: Any,
    ) -> Any:
        """
        Execute synchronization.

        Synchronization is optional because the Stage-1 baseline can use
        an already aligned AWGN link.
        """

        synchronizer = self._optional_component(
            self.components.synchronizer,
            "synchronizer",
            identity=_identity_stage,
        )

        try:
            return synchronizer(
                channel_output,
                rng=rng,
                **kwargs,
            )
        except Exception as exc:
            raise PipelineStageError(
                "Synchronization stage failed."
            ) from exc

    # =========================================================================
    # Equalization
    # =========================================================================

    def _run_equalizer(
        self,
        synchronized: Any,
        *,
        **kwargs: Any,
    ) -> Any:
        """
        Execute frequency-domain equalization.

        Equalization is optional in the Stage-1 AWGN baseline.
        """

        equalizer = self._optional_component(
            self.components.equalizer,
            "equalizer",
            identity=_identity_stage,
        )

        try:
            return equalizer(
                synchronized,
                **kwargs,
            )
        except Exception as exc:
            raise PipelineStageError(
                "Equalization stage failed."
            ) from exc

    # =========================================================================
    # OFDM demodulator
    # =========================================================================

    def _run_ofdm_demodulator(
        self,
        equalized_input: Any,
        *,
        **kwargs: Any,
    ) -> OFDMDemodResultLike:
        """
        Execute the OFDM demodulator.

        IMPORTANT:

        This stage does NOT construct ReceiveFrame.

        It returns the OFDM-domain representation required by subsequent
        receiver stages.

        The final ReceiveFrame is constructed only after:

            OFDM demodulation
            ↓
            data-symbol extraction
            ↓
            symbol demodulation
            ↓
            deinterleaving
            ↓
            decoding

        This exactly matches the ReceiveFrame contract in types.py.
        """

        demodulator = self._require_component(
            self.components.ofdm_demodulator,
            "ofdm_demodulator",
        )

        try:
            result = demodulator(
                equalized_input,
                **kwargs,
            )
        except Exception as exc:
            raise PipelineStageError(
                "OFDM demodulator stage failed."
            ) from exc

        if not isinstance(
            result,
            OFDMDemodResultLike,
        ):
            raise PipelineValidationError(
                "ofdm_demodulator must return an object "
                "implementing OFDMDemodResultLike."
            )

        validate_complex_signal(
            result.received_waveform.samples
        )

        if not isinstance(
            result.ofdm_grid,
            OFDMGrid,
        ):
            raise PipelineValidationError(
                "ofdm_demodulator result.ofdm_grid "
                "must be an OFDMGrid instance."
            )

        symbols = np.asarray(
            result.equalized_symbols
        )

        if not np.iscomplexobj(
            symbols
        ):
            raise PipelineValidationError(
                "ofdm_demodulator result.equalized_symbols "
                "must be complex-valued."
            )

        if symbols.size == 0:
            raise PipelineValidationError(
                "ofdm_demodulator returned empty "
                "equalized_symbols."
            )

        return result

    # =========================================================================
    # Data symbol extraction
    # =========================================================================

    @staticmethod
    def _extract_data_symbols(
        demod_result: OFDMDemodResultLike,
    ) -> ComplexArray:
        """
        Extract data-bearing subcarriers using the canonical OFDMGrid API.

        ``OFDMGrid.get_data_symbols()`` is authoritative.

        We do not use:

            hasattr(...)
            ad-hoc attribute discovery
            private fields
            guessed layouts

        This is one of the places where pipeline.py explicitly follows
        the contract established by types.py.
        """

        grid = demod_result.ofdm_grid

        data_symbols = grid.get_data_symbols()

        data_symbols = np.asarray(
            data_symbols
        )

        if not np.iscomplexobj(
            data_symbols
        ):
            raise PipelineValidationError(
                "OFDMGrid.get_data_symbols() "
                "must return complex-valued symbols."
            )

        if data_symbols.size == 0:
            raise PipelineValidationError(
                "OFDMGrid.get_data_symbols() "
                "returned an empty array."
            )

        return data_symbols

    # =========================================================================
    # Symbol demodulator
    # =========================================================================

    def _run_demodulator(
        self,
        symbols: ComplexArray,
        *,
        **kwargs: Any,
    ) -> BitArray:
        """
        Convert equalized data symbols back to bits.
        """

        demodulator = self._require_component(
            self.components.demodulator,
            "demodulator",
        )

        try:
            bits = demodulator(
                symbols,
                **kwargs,
            )
        except Exception as exc:
            raise PipelineStageError(
                "Symbol demodulator stage failed."
            ) from exc

        bits = np.asarray(
            bits
        )

        validate_bits(
            bits
        )

        return bits

    # =========================================================================
    # Receiver
    # =========================================================================

    def run_receiver(
        self,
        channel_output: ChannelOutput,
        *,
        rng: np.random.Generator,
        **kwargs: Any,
    ) -> ReceiveFrame:
        """
        Execute the complete receiver.

        Canonical sequence:

            ChannelOutput
                ↓
            Synchronizer
                ↓
            Equalizer
                ↓
            OFDM demodulator
                ↓
            OFDMGrid.get_data_symbols()
                ↓
            symbol demodulator
                ↓
            deinterleaver
                ↓
            decoder
                ↓
            ReceiveFrame

        ``ReceiveFrame`` is constructed only here, at the end.

        This is deliberate and is now a locked architectural rule.
        """

        if not isinstance(
            channel_output,
            ChannelOutput,
        ):
            raise TypeError(
                "channel_output must be a ChannelOutput instance."
            )

        synchronized = self._run_synchronizer(
            channel_output,
            rng=rng,
            **kwargs,
        )

        equalized = self._run_equalizer(
            synchronized,
            **kwargs,
        )

        demod_result = self._run_ofdm_demodulator(
            equalized,
            **kwargs,
        )

        data_symbols = self._extract_data_symbols(
            demod_result
        )

        demodulated_bits = self._run_demodulator(
            data_symbols,
            **kwargs,
        )

        deinterleaver = self._optional_component(
            self.components.deinterleaver,
            "deinterleaver",
            identity=_identity_bits,
        )

        decoder = self._optional_component(
            self.components.decoder,
            "decoder",
            identity=_identity_bits,
        )

        deinterleaved_bits = self._run_bit_stage(
            stage=deinterleaver,
            name="deinterleaver",
            bits=demodulated_bits,
            **kwargs,
        )

        decoded_bits = self._run_bit_stage(
            stage=decoder,
            name="decoder",
            bits=deinterleaved_bits,
            **kwargs,
        )

        # ---------------------------------------------------------------------
        # FINAL ReceiveFrame CONSTRUCTION
        # ---------------------------------------------------------------------
        #
        # Do not move this construction into the OFDM demodulator.
        #
        # ReceiveFrame is a complete receiver-side result container and
        # therefore belongs after the complete receiver chain.
        #

        receive_frame = ReceiveFrame(
            received_waveform=demod_result.received_waveform,
            ofdm_grid=demod_result.ofdm_grid,
            equalized_symbols=np.asarray(
                demod_result.equalized_symbols
            ),
            demodulated_bits=demodulated_bits,
            decoded_bits=decoded_bits,
        )

        return receive_frame

    # =========================================================================
    # Analysis
    # =========================================================================

    def run_analysis(
        self,
        *,
        transmit_frame: Optional[TransmitFrame],
        receive_frame: Optional[ReceiveFrame],
        source_bits: Optional[BitArray],
        metadata: SimulationMetadata,
        context: Optional[PipelineContext] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Execute all registered analyzers.

        Every analyzer receives the same explicit experiment context.

        This avoids hidden dependencies between analyzers.
        """

        results: Dict[str, Any] = {}

        for name, analyzer in self.components.analyzers.items():

            if not callable(
                analyzer
            ):
                raise PipelineConfigurationError(
                    f"Analyzer '{name}' must be callable."
                )

            try:
                results[name] = analyzer(
                    transmit_frame=transmit_frame,
                    receive_frame=receive_frame,
                    source_bits=source_bits,
                    metadata=metadata,
                    context=context,
                    **kwargs,
                )
            except Exception as exc:
                raise PipelineStageError(
                    f"Analyzer '{name}' failed."
                ) from exc

        return results

    # =========================================================================
    # Analysis normalization
    # =========================================================================

    @staticmethod
    def _normalize_analysis_results(
        analysis_results: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """
        Normalize analyzer output into a plain dictionary.

        The pipeline intentionally does not assume that every analyzer
        returns the same type.
        """

        if not isinstance(
            analysis_results,
            Mapping,
        ):
            raise PipelineValidationError(
                "Analysis results must be a mapping."
            )

        return dict(
            analysis_results
        )

    # =========================================================================
    # ExperimentResult assembly
    # =========================================================================

    @staticmethod
    def _build_experiment_result(
        *,
        metadata: SimulationMetadata,
        papr_result: Optional[PAPRResult],
        analysis_results: Mapping[str, Any],
        context: Optional[PipelineContext],
    ) -> ExperimentResult:
        """
        Build the canonical ExperimentResult.

        Known result channels map directly to fields already defined by
        core.types.ExperimentResult.

        Unknown analyzer outputs are preserved in ``extra``.
        """

        known_keys = {
            "papr",
            "ccdf",
            "papr_statistics",
            "ber",
            "evm",
            "psd",
            "constellation",
            "notes",
        }

        normalized = dict(
            analysis_results
        )

        analysis_papr = normalized.get(
            "papr"
        )

        if (
            papr_result is None
            and analysis_papr is not None
        ):
            if isinstance(
                analysis_papr,
                PAPRResult,
            ):
                papr_result = analysis_papr

        extra = {
            key: value
            for key, value in normalized.items()
            if key not in known_keys
        }

        if context is not None:
            if context.warnings:
                extra.setdefault(
                    "pipeline_warnings",
                    list(context.warnings),
                )

            if context.stage_trace:
                extra.setdefault(
                    "pipeline_stage_trace",
                    list(context.stage_trace),
                )

        return ExperimentResult(
            metadata=metadata,
            papr=papr_result,
            ccdf=normalized.get(
                "ccdf"
            ),
            papr_statistics=normalized.get(
                "papr_statistics"
            ),
            ber=normalized.get(
                "ber"
            ),
            evm=normalized.get(
                "evm"
            ),
            psd=normalized.get(
                "psd"
            ),
            constellation=normalized.get(
                "constellation"
            ),
            notes=str(
                normalized.get(
                    "notes",
                    ""
                )
            ),
            extra=extra,
        )

    # =========================================================================
    # Frame / metadata consistency
    # =========================================================================

    def _validate_transmit_metadata(
        self,
        *,
        frame: TransmitFrame,
        metadata: SimulationMetadata,
    ) -> None:
        """
        Validate the transmitter frame against SimulationMetadata.

        Only properties explicitly represented by the core contract are
        checked here.
        """

        if frame.ofdm_grid.n_symbols != metadata.n_ofdm_symbols:
            raise PipelineValidationError(
                "TransmitFrame OFDM symbol count does not match "
                "SimulationMetadata.n_ofdm_symbols: "
                f"frame={frame.ofdm_grid.n_symbols}, "
                f"metadata={metadata.n_ofdm_symbols}."
            )

        if frame.ofdm_grid.fft_size != metadata.fft_size:
            raise PipelineValidationError(
                "TransmitFrame FFT size does not match "
                "SimulationMetadata.fft_size: "
                f"frame={frame.ofdm_grid.fft_size}, "
                f"metadata={metadata.fft_size}."
            )

        waveform = frame.waveform

        if waveform.fft_size != metadata.fft_size:
            raise PipelineValidationError(
                "TransmitFrame waveform FFT size does not match "
                "SimulationMetadata.fft_size."
            )

        if waveform.oversampling != metadata.oversampling:
            raise PipelineValidationError(
                "TransmitFrame waveform oversampling does not match "
                "SimulationMetadata.oversampling."
            )

    # =========================================================================
    # Receive consistency
    # =========================================================================

    def _validate_receive_consistency(
        self,
        *,
        transmit_frame: TransmitFrame,
        receive_frame: ReceiveFrame,
    ) -> None:
        """
        Validate receiver-side structural consistency.
        """

        if (
            receive_frame.ofdm_grid.fft_size
            != transmit_frame.ofdm_grid.fft_size
        ):
            raise PipelineValidationError(
                "ReceiveFrame FFT size does not match "
                "TransmitFrame FFT size."
            )

        if (
            receive_frame.ofdm_grid.n_symbols
            != transmit_frame.ofdm_grid.n_symbols
        ):
            raise PipelineValidationError(
                "ReceiveFrame OFDM symbol count does not match "
                "TransmitFrame OFDM symbol count."
            )

        if (
            receive_frame.received_waveform.fft_size
            != transmit_frame.waveform.fft_size
        ):
            raise PipelineValidationError(
                "ReceiveFrame waveform FFT size does not match "
                "TransmitFrame waveform FFT size."
            )

        if (
            receive_frame.received_waveform.oversampling
            != transmit_frame.waveform.oversampling
        ):
            raise PipelineValidationError(
                "ReceiveFrame waveform oversampling does not match "
                "TransmitFrame waveform oversampling."
            )

    # =========================================================================
    # PAPR metadata consistency
    # =========================================================================

    @staticmethod
    def _validate_papr_result(
        result: PAPRResult,
    ) -> None:
        """
        Validate the PAPR result against the core contract.

        Most mathematical invariants are already enforced by PAPRResult.
        This method exists as an explicit pipeline boundary check.
        """

        if not isinstance(
            result,
            PAPRResult,
        ):
            raise TypeError(
                "result must be a PAPRResult."
            )

        if result.n_samples_used <= 0:
            raise PipelineValidationError(
                "PAPRResult.n_samples_used must be positive."
            )

        if not result.cp_excluded:
            raise PipelineValidationError(
                "PAPR pipeline requires CP-excluded PAPR measurement."
            )

    # =========================================================================
    # Context diagnostics
    # =========================================================================

    @staticmethod
    def _attach_context(
        context: PipelineContext,
        *,
        stage: str,
        value: Any,
    ) -> None:
        """
        Store a named intermediate result and mark its stage complete.
        """

        context.store(
            stage,
            value,
        )

        context.mark(
            stage
        )

    # =========================================================================
    # Full experiment
    # =========================================================================

    def run(
        self,
        *,
        n_bits: int,
        seed: int,
        metadata: SimulationMetadata,
        **kwargs: Any,
    ) -> ExperimentResult:
        """
        Execute one complete deterministic experiment.

        Parameters
        ----------
        n_bits:
            Number of source bits.

        seed:
            Positive deterministic experiment seed.

        metadata:
            Immutable experiment metadata from ``core.types``.

        Returns
        -------
        ExperimentResult
            Canonical result container defined by ``core.types``.

        Execution ownership
        -------------------

        This method owns the experiment-level RNG:

            rng = np.random.default_rng(seed)

        The same generator is explicitly injected into stochastic stages.

        This prevents hidden global RNG state and makes a single execution
        reproducible.
        """

        n_bits = self._validate_n_bits(
            n_bits
        )

        seed = self._validate_seed(
            seed
        )

        if not isinstance(
            metadata,
            SimulationMetadata,
        ):
            raise TypeError(
                "metadata must be a SimulationMetadata instance."
            )

        if self.options.validate_metadata_consistency:
            self._validate_metadata(
                metadata=metadata,
                seed=seed,
            )

        rng = np.random.default_rng(
            seed
        )

        context = PipelineContext()

        # =====================================================================
        # Phase 1 — Source
        # =====================================================================

        source_bits = self.generate_source_bits(
            n_bits=n_bits,
            rng=rng,
            **kwargs,
        )

        context.source_bits = source_bits

        self._attach_context(
            context,
            stage="source",
            value=source_bits,
        )

        # =====================================================================
        # Phase 2 — Transmitter
        # =====================================================================

        transmit_frame = self.run_transmitter(
            source_bits=source_bits,
            rng=rng,
            **kwargs,
        )

        context.transmit_frame = transmit_frame

        self._attach_context(
            context,
            stage="transmitter",
            value=transmit_frame,
        )

        if self.options.validate_frame_consistency:
            self._validate_transmit_metadata(
                frame=transmit_frame,
                metadata=metadata,
            )

        # =====================================================================
        # Phase 3 — PAPR
        # =====================================================================

        papr_result: Optional[PAPRResult] = None

        if self.options.run_papr:

            papr_result = self.run_papr(
                transmit_frame,
                rng=rng,
                **kwargs,
            )

            self._validate_papr_result(
                papr_result
            )

            context.papr_result = papr_result

            self._attach_context(
                context,
                stage="papr",
                value=papr_result,
            )

        # =====================================================================
        # Phase 4 — Channel
        # =====================================================================

        channel_output: Optional[ChannelOutput] = None

        if self.options.run_channel:

            channel_output = self.run_channel(
                transmit_frame,
                rng=rng,
                **kwargs,
            )

            context.channel_output = channel_output

            self._attach_context(
                context,
                stage="channel",
                value=channel_output,
            )

        # =====================================================================
        # Phase 5 — Receiver
        # =====================================================================

        receive_frame: Optional[ReceiveFrame] = None

        if (
            self.options.run_channel
            and self.options.run_receiver
        ):

            if channel_output is None:
                raise PipelineError(
                    "Receiver execution requires "
                    "a ChannelOutput."
                )

            receive_frame = self.run_receiver(
                channel_output,
                rng=rng,
                **kwargs,
            )

            context.receive_frame = receive_frame

            self._attach_context(
                context,
                stage="receiver",
                value=receive_frame,
            )

            if self.options.validate_frame_consistency:
                self._validate_receive_consistency(
                    transmit_frame=transmit_frame,
                    receive_frame=receive_frame,
                )

        # =====================================================================
        # Phase 6 — Analysis
        # =====================================================================

        analysis_results: Dict[str, Any] = {}

        if self.options.run_analysis:

            analysis_results = self.run_analysis(
                transmit_frame=transmit_frame,
                receive_frame=receive_frame,
                source_bits=source_bits,
                metadata=metadata,
                context=context,
                **kwargs,
            )

            analysis_results = (
                self._normalize_analysis_results(
                    analysis_results
                )
            )

            context.analysis_results.update(
                analysis_results
            )

            self._attach_context(
                context,
                stage="analysis",
                value=analysis_results,
            )

        # =====================================================================
        # Phase 7 — Result assembly
        # =====================================================================

        result = self._build_experiment_result(
            metadata=metadata,
            papr_result=papr_result,
            analysis_results=analysis_results,
            context=(
                context
                if self.options.preserve_context_diagnostics
                else None
            ),
        )

        context.mark(
            "result"
        )

        return result

    # =========================================================================
    # Transmitter-only experiment
    # =========================================================================

    def run_transmitter_only(
        self,
        *,
        n_bits: int,
        seed: int,
        metadata: SimulationMetadata,
        **kwargs: Any,
    ) -> ExperimentResult:
        """
        Execute a transmitter/PAPR-only experiment.

        This mode is useful for PAPR research where no channel or receiver
        is required.

        The canonical ExperimentResult is still used.
        """

        if not isinstance(
            metadata,
            SimulationMetadata,
        ):
            raise TypeError(
                "metadata must be a SimulationMetadata instance."
            )

        seed = self._validate_seed(
            seed
        )

        n_bits = self._validate_n_bits(
            n_bits
        )

        if self.options.validate_metadata_consistency:
            self._validate_metadata(
                metadata=metadata,
                seed=seed,
            )

        rng = np.random.default_rng(
            seed
        )

        context = PipelineContext()

        source_bits = self.generate_source_bits(
            n_bits=n_bits,
            rng=rng,
            **kwargs,
        )

        context.source_bits = source_bits

        self._attach_context(
            context,
            stage="source",
            value=source_bits,
        )

        transmit_frame = self.run_transmitter(
            source_bits=source_bits,
            rng=rng,
            **kwargs,
        )

        context.transmit_frame = transmit_frame

        self._attach_context(
            context,
            stage="transmitter",
            value=transmit_frame,
        )

        if self.options.validate_frame_consistency:
            self._validate_transmit_metadata(
                frame=transmit_frame,
                metadata=metadata,
            )

        papr_result: Optional[PAPRResult] = None

        if self.options.run_papr:
            papr_result = self.run_papr(
                transmit_frame,
                rng=rng,
                **kwargs,
            )

            self._validate_papr_result(
                papr_result
            )

            context.papr_result = papr_result

            self._attach_context(
                context,
                stage="papr",
                value=papr_result,
            )

        analysis_results: Dict[str, Any] = {}

        if self.options.run_analysis:

            analysis_results = self.run_analysis(
                transmit_frame=transmit_frame,
                receive_frame=None,
                source_bits=source_bits,
                metadata=metadata,
                context=context,
                **kwargs,
            )

            analysis_results = (
                self._normalize_analysis_results(
                    analysis_results
                )
            )

            context.analysis_results.update(
                analysis_results
            )

            self._attach_context(
                context,
                stage="analysis",
                value=analysis_results,
            )

        return self._build_experiment_result(
            metadata=metadata,
            papr_result=papr_result,
            analysis_results=analysis_results,
            context=(
                context
                if self.options.preserve_context_diagnostics
                else None
            ),
        )

    # =========================================================================
    # Receiver-only execution
    # =========================================================================

    def run_receiver_only(
        self,
        *,
        channel_output: ChannelOutput,
        seed: int,
        **kwargs: Any,
    ) -> ReceiveFrame:
        """
        Execute only the receiver.

        Useful for isolated receiver tests and unit/integration tests.

        This method does not fabricate a TransmitFrame or ExperimentResult.
        It returns the canonical ReceiveFrame contract directly.
        """

        if not isinstance(
            channel_output,
            ChannelOutput,
        ):
            raise TypeError(
                "channel_output must be a ChannelOutput instance."
            )

        seed = self._validate_seed(
            seed
        )

        rng = np.random.default_rng(
            seed
        )

        return self.run_receiver(
            channel_output,
            rng=rng,
            **kwargs,
        )

    # =========================================================================
    # Analyzer registration
    # =========================================================================

    def register_analyzer(
        self,
        name: str,
        analyzer: AnalyzerStage,
    ) -> None:
        """
        Register an analyzer dynamically.

        This is intentionally a small convenience API.

        Scientific result typing remains controlled by ExperimentResult.
        """

        if not isinstance(
            name,
            str,
        ):
            raise TypeError(
                "Analyzer name must be a string."
            )

        name = name.strip()

        if not name:
            raise ValueError(
                "Analyzer name cannot be empty."
            )

        if not callable(
            analyzer
        ):
            raise TypeError(
                "analyzer must be callable."
            )

        self.components.analyzers[
            name
        ] = analyzer

    # =========================================================================
    # Analyzer removal
    # =========================================================================

    def unregister_analyzer(
        self,
        name: str,
    ) -> None:
        """
        Remove a registered analyzer.

        Missing names are ignored intentionally.
        """

        if not isinstance(
            name,
            str,
        ):
            raise TypeError(
                "Analyzer name must be a string."
            )

        self.components.analyzers.pop(
            name,
            None,
        )

    # =========================================================================
    # Component availability
    # =========================================================================

    def configured_stages(
        self,
    ) -> Dict[str, bool]:
        """
        Return the configuration state of every pipeline stage.

        This is diagnostic information only.
        """

        return {
            "source": self.components.source is not None,
            "encoder": self.components.encoder is not None,
            "interleaver": (
                self.components.interleaver is not None
            ),
            "modulator": (
                self.components.modulator is not None
            ),
            "ofdm_modulator": (
                self.components.ofdm_modulator is not None
            ),
            "papr_processor": (
                self.components.papr_processor is not None
            ),
            "channel": (
                self.components.channel is not None
            ),
            "synchronizer": (
                self.components.synchronizer is not None
            ),
            "equalizer": (
                self.components.equalizer is not None
            ),
            "ofdm_demodulator": (
                self.components.ofdm_demodulator is not None
            ),
            "demodulator": (
                self.components.demodulator is not None
            ),
            "deinterleaver": (
                self.components.deinterleaver is not None
            ),
            "decoder": (
                self.components.decoder is not None
            ),
            "analyzers": bool(
                self.components.analyzers
            ),
        }

    # =========================================================================
    # Configuration diagnostics
    # =========================================================================

    def validate_configuration(
        self,
    ) -> None:
        """
        Validate that the current component configuration is compatible
        with the current PipelineOptions.

        This method does not execute any signal processing.
        """

        self._require_component(
            self.components.source,
            "source",
        )

        self._require_component(
            self.components.modulator,
            "modulator",
        )

        self._require_component(
            self.components.ofdm_modulator,
            "ofdm_modulator",
        )

        if self.options.run_papr:
            self._require_component(
                self.components.papr_processor,
                "papr_processor",
            )

        if self.options.run_channel:
            self._require_component(
                self.components.channel,
                "channel",
            )

        if self.options.run_receiver:

            if not self.options.run_channel:
                raise PipelineConfigurationError(
                    "run_receiver=True requires "
                    "run_channel=True."
                )

            self._require_component(
                self.components.ofdm_demodulator,
                "ofdm_demodulator",
            )

            self._require_component(
                self.components.demodulator,
                "demodulator",
            )

        for name, analyzer in self.components.analyzers.items():
            if not callable(
                analyzer
            ):
                raise PipelineConfigurationError(
                    f"Analyzer '{name}' must be callable."
                )

    # =========================================================================
    # Required stage names
    # =========================================================================

    @staticmethod
    def required_stage_names() -> Tuple[str, ...]:
        """
        Return unconditional required stage names.
        """

        return (
            "source",
            "modulator",
            "ofdm_modulator",
        )

    # =========================================================================
    # Optional stage names
    # =========================================================================

    @staticmethod
    def optional_stage_names() -> Tuple[str, ...]:
        """
        Return optional stage names.
        """

        return (
            "encoder",
            "interleaver",
            "synchronizer",
            "equalizer",
            "deinterleaver",
            "decoder",
        )

    # =========================================================================
    # Conditional stage names
    # =========================================================================

    @staticmethod
    def conditional_stage_names() -> Tuple[str, ...]:
        """
        Return stages whose requirement depends on PipelineOptions.
        """

        return (
            "papr_processor",
            "channel",
            "ofdm_demodulator",
            "demodulator",
        )

    # =========================================================================
    # Pipeline description
    # =========================================================================

    @staticmethod
    def architecture() -> Tuple[str, ...]:
        """
        Return the canonical execution architecture.
        """

        return (
            "source",
            "encoder",
            "interleaver",
            "modulator",
            "ofdm_modulator",
            "papr",
            "channel",
            "synchronizer",
            "equalizer",
            "ofdm_demodulator",
            "data_symbol_extraction",
            "demodulator",
            "deinterleaver",
            "decoder",
            "analysis",
            "result",
        )


# =============================================================================
# Public API
# =============================================================================


__all__ = [
    # Exceptions
    "PipelineError",
    "PipelineConfigurationError",
    "PipelineStageError",
    "PipelineValidationError",

    # Type aliases
    "BitsStage",
    "SymbolStage",
    "SourceStage",
    "OFDMModulatorStage",
    "ChannelStage",
    "PAPRStage",
    "SynchronizerStage",
    "EqualizerStage",
    "DemodulatorStage",
    "AnalyzerStage",
    "GenericStage",

    # Temporary demodulation contract
    "OFDMDemodResultLike",

    # Execution state
    "PipelineContext",

    # Configuration
    "PipelineOptions",
    "PipelineComponents",

    # Main orchestrator
    "OFDMChain",
]
