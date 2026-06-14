"""Recompute metrics.json from an existing results.jsonl without re-running the pipeline."""

import json
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir.parent))  # d:\OneDrive\Documents → "import uos" works

from uos.records import summarize


def recompute(results_path: Path, metrics_path: Path) -> None:
    rows = []
    with results_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    # Load existing metrics to preserve model / prompt_version header
    header = {}
    if metrics_path.exists():
        existing = json.loads(metrics_path.read_text(encoding="utf-8"))
        header = {k: v for k, v in existing.items() if k != "summary"}

    output = {**header, "summary": summarize(rows)}
    metrics_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Updated {metrics_path}  ({len(rows)} sentences)")


def main() -> None:
    root = Path(__file__).parent
    results_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "output" / "test" / "results.jsonl"
    metrics_path = results_path.with_name("metrics.json")
    recompute(results_path, metrics_path)


if __name__ == "__main__":
    main()
