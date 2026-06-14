"""
Replace $T$ in units with the actual aspect_terms value from results.jsonl.
Output is written to a new file — never overwrites the original.
"""

import json
import sys
from pathlib import Path


def next_available_path(base: Path) -> Path:
    if not base.exists():
        return base
    i = 1
    while True:
        candidate = base.with_stem(f"{base.stem}_{i}")
        if not candidate.exists():
            return candidate
        i += 1


def replace_T(input_path: Path, output_path: Path) -> None:
    safe_output = next_available_path(output_path)
    count = replaced = skipped = 0

    with input_path.open(encoding="utf-8") as fin, \
         safe_output.open("w", encoding="utf-8") as fout:

        for lineno, raw in enumerate(fin, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"[WARN] line {lineno}: skip — {e}")
                skipped += 1
                continue

            aspect = record.get("aspect_terms", "").strip()
            if not aspect:
                print(f"[WARN] line {lineno}: empty aspect_terms, $T$ left as-is")

            new_units = []
            for u in record.get("units", []):
                new_u = u.replace("$T$", aspect) if aspect else u
                if "$T$" in new_u:
                    print(f"[WARN] line {lineno}: $T$ still present after replace — unit={repr(u)!r}, aspect={repr(aspect)}")
                new_units.append(new_u)
                if new_u != u:
                    replaced += 1

            record["units"] = new_units
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    print(f"Processed {count} records | replaced {replaced} units | skipped {skipped} bad lines")
    print(f"Output → {safe_output}")


def find_latest_results(directory: Path) -> Path | None:
    """Return the most recently modified results*.jsonl in directory."""
    candidates = sorted(
        directory.glob("results*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def main() -> None:
    if len(sys.argv) == 3:
        input_path  = Path(sys.argv[1])
        output_path = Path(sys.argv[2])
    elif len(sys.argv) == 2:
        input_path  = Path(sys.argv[1])
        output_path = input_path.with_stem(input_path.stem + "_replaced")
    else:
        root     = Path(__file__).parent
        out_dir  = root / "output" / "test"
        # prefer results_1.jsonl, fall back to the most recent results*.jsonl
        default  = out_dir / "results_1.jsonl"
        input_path = default if default.exists() else find_latest_results(out_dir)
        if input_path is None:
            print(f"[ERROR] No results*.jsonl found in {out_dir}")
            sys.exit(1)
        output_path = out_dir / "results_replaced.jsonl"
        print(f"Input: {input_path}")

    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    replace_T(input_path, output_path)


if __name__ == "__main__":
    main()
