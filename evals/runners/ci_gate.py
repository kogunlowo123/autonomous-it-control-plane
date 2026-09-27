"""CI gate runner — runs evals and fails the build if thresholds are not met."""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Thresholds for CI gate
THRESHOLDS = {
    "recall@5": 0.80,
    "mrr": 0.65,
    "faithfulness_mean": 0.60,
}


def run_ci_gate(results: dict[str, float]) -> bool:
    """Check eval results against CI thresholds.

    Returns True if all thresholds pass, False if any fail.
    """
    all_pass = True
    for metric, threshold in THRESHOLDS.items():
        score = results.get(metric, 0.0)
        status = "PASS" if score >= threshold else "FAIL"
        if score < threshold:
            all_pass = False
        logger.info(
            "Eval gate: %s = %.4f (threshold=%.4f) [%s]",
            metric, score, threshold, status,
        )

    return all_pass


def load_eval_results(results_path: str) -> dict[str, float]:
    """Load eval results from a JSON file."""
    path = Path(results_path)
    if not path.exists():
        logger.error("Eval results file not found: %s", results_path)
        return {}

    with open(path) as f:
        return json.load(f)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    results_file = sys.argv[1] if len(sys.argv) > 1 else "eval_results.json"
    results = load_eval_results(results_file)

    if not results:
        logger.warning("No eval results to check — skipping CI gate")
        sys.exit(0)

    passed = run_ci_gate(results)
    if not passed:
        logger.error("Eval CI gate FAILED — one or more metrics below threshold")
        sys.exit(1)

    logger.info("Eval CI gate PASSED")
    sys.exit(0)
