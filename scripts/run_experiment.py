"""
Run different simulation scenarios (Papr, Rayleigh, etc.).
"""

import argparse
import sys
from pathlib import Path

from ofdm_linksim import ExperimentConfig, load_config, ExperimentResult
from ofdm_linksim.output import ResultWriter

def run_scenario(
    scenario_path: Path,
    *,
    seed: int,
    snr_db: float,
    output_dir: Path,
) -> ExperimentResult:
    cfg = load_config(str(scenario_path), enforce_reference=False)
    cfg.random.seed = seed
    cfg.snr.values = [snr_db]

    # (مثال ساده – در نسخه کامل‌تر از pipeline استفاده می‌کنیم)
    from ofdm_linksim.core.pipeline import PipelineContext
    ctx = PipelineContext(cfg)
    # ... شبیه‌سازی کامل ...

    result = ExperimentResult(...)  # placeholder برای تست
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, default=Path("scenarios/baseline.yaml"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--snr", type=float, default=20)
    parser.add_argument("--output", type=Path, default=Path("results/experiments"))
    args = parser.parse_args()

    result = run_scenario(args.scenario, seed=args.seed, snr_db=args.snr, output_dir=args.output)
    writer = ResultWriter(root=args.output)
    writer.write_experiment(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
