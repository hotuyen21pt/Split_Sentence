"""UOS segmentation pipeline."""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence

from uos.io import load_gold_cases
from uos.records import build_record
from uos.validation import check_case

_ROOT = Path(__file__).resolve().parent
UOS_GOLD_CASES = _ROOT / "dataset" / "demo.apc"

ProgressFn = Callable[[int, Optional[int], float, str], None]
RecordFn = Callable[[dict], None]


def _default_progress(done: int, total: Optional[int], latency_s: float, sentence: str) -> None:
    preview = sentence[:60] + ("..." if len(sentence) > 60 else "")
    total_display = str(total) if total is not None else "?"
    print(f"  [{done}/{total_display}] {latency_s:.1f}s | {preview}", flush=True)


def segment_one(segmenter, sentence: str, aspect_term: str = "") -> "tuple[List[str], str]":
    if hasattr(segmenter, "segment_with_raw"):
        return segmenter.segment_with_raw(sentence, aspect_term)
    units = segmenter.segment(sentence, aspect_term)
    return list(units), ""


def run_gold_cases(segmenter, cases_path: Path = UOS_GOLD_CASES) -> List[dict]:
    cases = load_gold_cases(cases_path)
    rows: List[dict] = []
    for i, case in enumerate(cases):
        t0 = time.perf_counter()
        units, raw = segment_one(segmenter, case["sentence"])
        row = build_record(
            {"entity_id": "_case", "review_id": case["id"], "sentence_idx": i,
             "sentence": case["sentence"]},
            units, time.perf_counter() - t0, raw_response=raw,
            ok=check_case(case, units),
        )
        rows.append(row)
        print(f"  [{'OK' if row['metrics']['ok'] else 'FAIL'}] {case['id']}: {row['units']}", flush=True)
    return rows


def _process_one(segmenter, i: int, meta: dict) -> "tuple[int, dict]":
    t0 = time.perf_counter()
    try:
        aspect_term = meta.get("aspect_terms", "")
        units, raw = segment_one(segmenter, meta["sentence"], aspect_term)
    except Exception as exc:
        units = [meta["sentence"]]
        raw = f"ERROR: {exc}"
        print(f"  [ERROR] row {i}: {exc}", file=sys.stderr, flush=True)
    latency = time.perf_counter() - t0
    return i, build_record(meta, units, latency, raw_response=raw)


def run_corpus(
    segmenter,
    records: Iterable[dict],
    *,
    on_progress: Optional[ProgressFn] = _default_progress,
    on_record: Optional[RecordFn] = None,
    total: Optional[int] = None,
    workers: int = 8,
) -> List[dict]:
    record_list = list(records)
    total = total or len(record_list)
    rows: List[Optional[dict]] = [None] * len(record_list)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_process_one, segmenter, i, meta): i
            for i, meta in enumerate(record_list)
        }
        done = 0
        for future in as_completed(futures):
            i, row = future.result()
            rows[i] = row
            done += 1
            if on_record:
                on_record(row)
            if on_progress:
                on_progress(done, total, row["metrics"]["latency_s"], row["sentence"])

    return [r for r in rows if r is not None]
