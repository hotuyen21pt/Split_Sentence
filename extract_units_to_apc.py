"""
Extract 'units' from a results.jsonl file and write them to a new .apc file.
The output file is never overwritten — a numeric suffix is added if the target exists.
"""

import json
import sys
from pathlib import Path


def next_available_path(base: Path) -> Path:
    """Return base if it doesn't exist, else base_1, base_2, ... until free."""
    if not base.exists():
        return base
    stem = base.stem
    suffix = base.suffix
    parent = base.parent
    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def extract_units_to_apc(input_path: Path, output_path: Path) -> None:
    safe_output = next_available_path(output_path)

    lines_written = 0
    with input_path.open(encoding="utf-8") as fin, \
         safe_output.open("w", encoding="utf-8") as fout:

        for lineno, raw in enumerate(fin, start=1):
            raw = raw.strip()
            if not raw:
                continue

            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"[WARN] line {lineno}: skipping invalid JSON — {exc}")
                continue

            units = record.get("units", [])
            aspect_terms = record.get("aspect_terms", "")
            categories = record.get("categories", "")
            sentiments = record.get("sentiments", "")

            for unit in units:
                fout.write(f"{unit}\n{aspect_terms}\n{categories}\n{sentiments}\n")
                lines_written += 4

    print(f"Wrote {lines_written // 4} entries ({lines_written} lines) → {safe_output}")


def main() -> None:
    if len(sys.argv) == 3:
        input_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2])
    elif len(sys.argv) == 2:
        input_path = Path(sys.argv[1])
        output_path = input_path.with_suffix(".apc")
    else:
        # default paths relative to this script
        script_dir = Path(__file__).parent
        input_path = script_dir / "output" / "test" / "results.jsonl"
        output_path = script_dir / "output" / "test" / "train_1.apc"

    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        sys.exit(1)

    extract_units_to_apc(input_path, output_path)


if __name__ == "__main__":
    main()
