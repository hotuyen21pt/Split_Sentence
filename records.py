"""Build output records and corpus summaries."""
from __future__ import annotations

import statistics
from typing import Sequence

from uos.metrics import compute_sentence_unit_metrics
from uos.parsing import validate_units
from uos.validation import detect_warnings, unsupported_token_rate


def build_record(
    meta: dict,
    units: Sequence[str],
    latency_s: float,
    raw_response: str = "",
    *,
    ok: bool | None = None,
) -> dict:
    units = validate_units(meta["sentence"], list(units))
    token_recall, char_coverage, was_split = compute_sentence_unit_metrics(
        meta["sentence"], units
    )
    record = {
        "entity_id": meta["entity_id"],
        "review_id": meta["review_id"],
        "sentence_idx": meta["sentence_idx"],
        "text_column": meta.get("text_column", "sentence"),
        "sentence": meta["sentence"],
        "units": units,
        "warnings": detect_warnings(meta["sentence"], units),
        "raw_response": raw_response,
        "metrics": {
            "n_units": len(units),
            "was_split": was_split,
            "token_recall": round(token_recall, 4),
            "char_coverage": round(char_coverage, 4),
            "information_loss_token": round(1 - token_recall, 4),
            "information_loss_char": round(1 - char_coverage, 4),
            "unsupported_token_rate": round(
                unsupported_token_rate(meta["sentence"], units), 4
            ),
            "latency_s": round(latency_s, 3),
        },
    }
    if ok is not None:
        record["metrics"]["ok"] = ok
    record["aspect_terms"] = meta.get("aspect_terms", "")
    record["categories"]   = meta.get("categories", "")
    record["sentiments"]   = meta.get("sentiments", "")
    if meta.get("source_label"):
        record["source_label"] = meta["source_label"]
    if meta.get("source"):
        record["source"] = meta["source"]
    return record


def export_row(record: dict) -> dict:
    """Canonical row for results.jsonl."""
    metrics = {k: v for k, v in record["metrics"].items() if k != "ok"}
    row: dict = {
        "entity_id": record["entity_id"],
        "review_id": record["review_id"],
        "sentence_idx": record["sentence_idx"],
        "sentence": record["sentence"],
        "units": record["units"],
        "warnings": record["warnings"],
        "raw_response": record.get("raw_response") or "",
        "metrics": metrics,
    }
    row["aspect_terms"] = record.get("aspect_terms", "")
    row["categories"]   = record.get("categories", "")
    row["sentiments"]   = record.get("sentiments", "")
    text_column = record.get("text_column", "sentence")
    if text_column and text_column != "sentence":
        row["text_column"] = text_column
    if record.get("source_label"):
        row["source_label"] = record["source_label"]
    if record.get("source"):
        row["source"] = record["source"]
    return row


def _summarize_rows(rows: Sequence[dict]) -> dict:
    n = len(rows)
    return {
        "n_sentences": n,
        "split_rate": round(sum(1 for r in rows if r["metrics"]["was_split"]) / n, 4),
        "warning_rate": round(sum(1 for r in rows if r.get("warnings")) / n, 4),
        "units_per_sentence_mean": round(
            sum(r["metrics"]["n_units"] for r in rows) / n, 4
        ),
        "token_recall_mean": round(
            statistics.mean(r["metrics"]["token_recall"] for r in rows), 4
        ),
        "char_coverage_mean": round(
            statistics.mean(r["metrics"]["char_coverage"] for r in rows), 4
        ),
        "unsupported_token_rate_mean": round(
            statistics.mean(r["metrics"]["unsupported_token_rate"] for r in rows), 4
        ),
        "latency_s_mean": round(
            statistics.mean(r["metrics"]["latency_s"] for r in rows), 4
        ),
    }


def summarize(rows: Sequence[dict]) -> dict:
    """Single-source summary (backward compat)."""
    if not rows:
        return {}
    return _summarize_rows(rows)


def summarize_multi(
    sources: list[dict],
    all_rows: Sequence[dict],
) -> dict:
    """Multi-source summary.

    sources: [{"label": "space", "input_json": "...", "text_column": "..."}]
    all_rows: all rows in order, each row has "source_label"
    Returns {"per_source": {...}, "combined": {...}}
    """
    per_source: dict[str, dict] = {}
    for src in sources:
        label = src["label"]
        src_rows = [r for r in all_rows if r.get("source_label") == label]
        per_source[label] = {
            "input_json": src.get("input_json", ""),
            "text_column": src.get("text_column", ""),
            "stats": _summarize_rows(src_rows) if src_rows else {},
        }
    return {
        "per_source": per_source,
        "combined": _summarize_rows(list(all_rows)) if all_rows else {},
    }
