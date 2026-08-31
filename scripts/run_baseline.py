"""
OFDM-PAPR-LinkSim — Baseline Run Script
========================================

Run the locked Stage-1 baseline (QPSK + AWGN + no PAPR reduction).

Usage
-----
python scripts/run_baseline.py [--seed SEED] [--snr SNR] [--blocks N]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

from ofdm_linksim import (
    ExperimentConfig,
    load_baseline,
    ExperimentResult,
    compute_ber,
    compute_ccdf,
    compute_evm,
    compute_papr,
    make_papr_result,
)
from ofdm_linksim.core.types import PAPRResult
from ofdm_linksim.utils.random import source_rng

# =============================================================================
# Argument parsing
# =============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OFDM-PAPR baseline")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--snr", type=float, default=20.0, help="SNR (dB)")
    parser.add_argument("--blocks", type=int, default=1000, help="OFDM blocks")
    parser.add_argument("--output", type=Path, default=Path("results/baseline"))
    return parser.parse_args()


# =============================================================================
# Core simulation function
# =============================================================================

def run_baseline(
    cfg: ExperimentConfig,
    *,
    seed: int,
    snr_db: float,
    n_blocks: int,
) -> ExperimentResult:
    """Run the locked baseline simulation."""
    rng = source_rng(seed)
    cfg.random.seed = seed
    cfg.snr.values = [snr_db]

    # Generate source bits (Stage-1 uses random bits)
    n_bits = cfg.n_bits()
    source_bits = np.array(rng.integers(0, 2, size=n_bits), dtype=np.uint8)

    # Modulation (QPSK)
    from ofdm_linksim.modulation import modulate
    symbols = modulate(source_bits, mod=cfg.modulation.modulation_enum)

    # OFDM modulator
    from ofdm_linksim.ofdm_modulator import modulate_ofdm
    tx_frame = modulate_ofdm(
        symbols,
        source_bits=source_bits,
        coded_bits=source_bits,  # identity Stage-1
        interleaved_bits=source_bits,
        fft_size=cfg.ofdm.fft_size,
        oversampling=cfg.ofdm.oversampling_factor,
        cyclic_prefix_length=cfg.ofdm.cyclic_prefix_length,
    )

    # Channel (AWGN baseline)
    from ofdm_linksim.channel import channel
    rx_channel = channel(tx_frame, snr_db=snr_db, rng=rng)

    # OFDM demodulator
    from ofdm_linksim.ofdm_demodulator import ofdm_demodulator
    demod = ofdm_demodulator(
        rx_channel.signal,
        data_indices=tx_frame.ofdm_grid.data_indices,
        pilot_indices=tx_frame.ofdm_grid.pilot_indices,
        fft_size=cfg.ofdm.fft_size,
        oversampling=cfg.ofdm.oversampling_factor,
    )

    # Demodulation
    from ofdm_linksim.modulation import demodulate
    rx_bits = demodulate(demod.equalized_symbols, mod=cfg.modulation.modulation_enum)

    # Metrics
    ber_result = compute_ber(source_bits, rx_bits, snr_db=snr_db)
    papr_result: PAPRResult = compute_papr(tx_frame.waveform, snr_db=snr_db, rng=rng)
    evm_result = compute_evm(tx_frame.modulation_symbols, demod.equalized_symbols)

    # CCDF
    papr_list = np.random.uniform(0, 12, size=1000)  # placeholder for real PAPR list
    ccdf_result = compute_ccdf(papr_list)

    return ExperimentResult(
        metadata=SimulationMetadata(
            run_id=f"baseline_{datetime.now():%Y%m%d_%H%M%S}",
            scenario_name=cfg.scenario.name,
            scenario_version=cfg.scenario.version,
            fft_size=cfg.ofdm.fft_size,
            oversampling=cfg.ofdm.oversampling_factor,
            n_ofdm_symbols=n_blocks,
            modulation=cfg.modulation.modulation_enum,
            channel=cfg.channel.channel_enum,
            snr_definition=cfg.channel.snr_definition_enum,
            papr_method=cfg.papr.papr_method_enum,
            seed=seed,
            created_at=str(datetime.now()),
        ),
        ber=ber_result,
        papr=papr_result,
        evm=evm_result,
        ccdf=ccdf_result,
        notes="Stage-1 baseline run",
    )


# =============================================================================
# Main entry point
# =============================================================================

def main() -> int:
    args = parse_args()
    cfg = load_baseline()
    cfg.simulation.ofdm_blocks = args.blocks

    result = run_baseline(
        cfg=cfg,
        seed=args.seed,
        snr_db=args.snr,
        n_blocks=args.blocks,
    )

    # Save results
    from ofdm_linksim.output import ResultWriter
    writer = ResultWriter.from_config(cfg, root=args.output)
    report = writer.write_experiment(result, config=cfg)

    print(f"✅ Baseline completed!")
    print(f"   Run ID: {result.metadata.run_id}")
    print(f"   BER: {result.ber.ber:.2e}")
    print(f"   PAPR: {result.papr.papr_db:.2f} dB")
    print(f"   Report: {report.root / report.run_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
