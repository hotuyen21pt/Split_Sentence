"""Convert results.jsonl to CSV with columns: sentence, unit (one row per unit)."""
import argparse
import csv
import json
from pathlib import Path


def convert(input_path: Path, output_path: Path) -> int:
    records = []
    with open(input_path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    records.sort(key=lambda r: int(r.get("entity_id", 0)) if str(r.get("entity_id", "0")).isdigit() else 0)

    out_rows = []
    for i, record in enumerate(records, start=1):
        sentence = record.get("sentence", "")
        units = record.get("units", [])
        if not isinstance(units, list):
            units = [str(units)]
        entity_id = i
        for unit in units:
            out_rows.append({"entity_id": entity_id, "sentence": sentence, "unit": unit})

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["entity_id", "sentence", "unit"])
        writer.writeheader()
        writer.writerows(out_rows)

    return len(out_rows)


def main():
    p = argparse.ArgumentParser(description="Convert results.jsonl -> CSV (sentence, unit) one row per unit")
    p.add_argument("--input",  default="output/test/results.jsonl", help="Path to results.jsonl")
    p.add_argument("--output", default="output/test/results.csv",   help="Output CSV path")
    args = p.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n = convert(input_path, output_path)
    print(f"Done: {n} rows -> {output_path}")


if __name__ == "__main__":
    main()
