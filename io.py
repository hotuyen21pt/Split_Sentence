"""Load input records for UOS segmentation."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterator, List, Union

FLAT_TEXT_FALLBACKS = ("sentence", "review", "caption", "text", "comment")
FLAT_ID_FALLBACKS = ("json_file", "entity_id", "review_id", "id")


def detect_input_format(data: Any) -> str:
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return "space" if "reviews" in data[0] else "flat"
    return "flat"


def _first_json_array_item(path: Union[str, Path]) -> Any:
    try:
        import ijson  # type: ignore
    except ImportError as exc:
        raise RuntimeError("ijson is required for streaming UOS input: pip install ijson") from exc

    with open(path, "rb") as f:
        for item in ijson.items(f, "item"):
            return item
    return None


def detect_input_format_path(path: Union[str, Path]) -> str:
    path = Path(path)
    if path.suffix.lower() == ".apc":
        return "apc"
    first = _first_json_array_item(path)
    if isinstance(first, dict):
        return "space" if "reviews" in first else "flat"
    return "flat"


def resolve_text_column(fmt: str, text_column: str, sample: dict | None = None) -> str:
    if text_column:
        return text_column
    if fmt == "space":
        return "sentences"
    if sample:
        for key in FLAT_TEXT_FALLBACKS:
            if key in sample and isinstance(sample[key], str):
                return key
    return "sentence"


def resolve_id_column(id_column: str, sample: dict | None) -> str:
    if id_column:
        return id_column
    if sample:
        for key in FLAT_ID_FALLBACKS:
            if key in sample:
                return key
    return ""


def _make_row(**kwargs) -> dict:
    row = {
        "entity_id": kwargs["entity_id"],
        "review_id": kwargs["review_id"],
        "sentence_idx": kwargs["sentence_idx"],
        "text_column": kwargs["text_column"],
        "sentence": kwargs["sentence"],
    }
    if kwargs.get("source"):
        row["source"] = kwargs["source"]
    return row


def load_space_records(data: list, text_column: str, max_reviews: int, max_rows: int) -> List[dict]:
    out: List[dict] = []
    n_reviews = 0
    for ent in data:
        entity_id = str(ent.get("entity_id", ""))
        for rev in ent.get("reviews", []):
            if max_reviews and n_reviews >= max_reviews:
                return out
            n_reviews += 1
            review_id = str(rev.get("review_id", ""))
            if text_column == "sentences":
                for idx, text in enumerate(rev.get("sentences", [])):
                    if isinstance(text, str) and text.strip():
                        out.append(_make_row(
                            entity_id=entity_id, review_id=review_id, sentence_idx=idx,
                            sentence=text.strip(), text_column=text_column,
                        ))
                        if max_rows and len(out) >= max_rows:
                            return out
            else:
                raw = rev.get(text_column, "")
                if isinstance(raw, str) and raw.strip():
                    out.append(_make_row(
                        entity_id=entity_id, review_id=review_id, sentence_idx=0,
                        sentence=raw.strip(), text_column=text_column, source=rev,
                    ))
                    if max_rows and len(out) >= max_rows:
                        return out
    return out


def iter_space_records(
    path: Union[str, Path],
    text_column: str,
    max_reviews: int,
    max_rows: int,
) -> Iterator[dict]:
    try:
        import ijson  # type: ignore
    except ImportError as exc:
        raise RuntimeError("ijson is required for SPACE UOS input: pip install ijson") from exc

    col = resolve_text_column("space", text_column)
    n_reviews = 0
    n_rows = 0
    with open(path, "rb") as f:
        for ent in ijson.items(f, "item"):
            entity_id = str(ent.get("entity_id", ""))
            for rev in ent.get("reviews", []):
                if max_reviews and n_reviews >= max_reviews:
                    return
                n_reviews += 1
                review_id = str(rev.get("review_id", ""))
                if col == "sentences":
                    for idx, text in enumerate(rev.get("sentences", [])):
                        if isinstance(text, str) and text.strip():
                            yield _make_row(
                                entity_id=entity_id,
                                review_id=review_id,
                                sentence_idx=idx,
                                sentence=text.strip(),
                                text_column=col,
                            )
                            n_rows += 1
                            if max_rows and n_rows >= max_rows:
                                return
                else:
                    raw = rev.get(col, "")
                    if isinstance(raw, str) and raw.strip():
                        yield _make_row(
                            entity_id=entity_id,
                            review_id=review_id,
                            sentence_idx=0,
                            sentence=raw.strip(),
                            text_column=col,
                            source=rev,
                        )
                        n_rows += 1
                        if max_rows and n_rows >= max_rows:
                            return


def load_flat_records(data: list, text_column: str, id_column: str, max_rows: int) -> List[dict]:
    sample = data[0] if data else None
    col = resolve_text_column("flat", text_column, sample if isinstance(sample, dict) else None)
    id_col = resolve_id_column(id_column, sample if isinstance(sample, dict) else None)
    out: List[dict] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        raw = item.get(col, "")
        if not isinstance(raw, str) or not raw.strip():
            continue
        row_id = str(item.get(id_col, idx)) if id_col else str(idx)
        out.append(_make_row(
            entity_id=row_id, review_id=row_id, sentence_idx=idx,
            sentence=raw.strip(), text_column=col, source=item,
        ))
        if max_rows and len(out) >= max_rows:
            break
    return out


def _is_csv_apc(path: Path) -> bool:
    """Return True if the .apc file uses CSV format (sentence,aspect,category,sentiment)."""
    with open(path, encoding="utf-8") as f:
        first = f.readline().strip()
    # CSV format: has at least 3 commas or starts with a quote
    return first.startswith('"') or first.count(",") >= 3


def iter_apc_records(path: Union[str, Path], max_rows: int = 0) -> Iterator[dict]:
    """Yield records from a .apc file.

    Supports two formats:
    - CSV:  "sentence",aspect,category,sentiment  (one entry per line)
    - 4-line: sentence / aspect / category / sentiment  (legacy)
    """
    path = Path(path)
    if _is_csv_apc(path):
        yield from _iter_apc_csv(path, max_rows)
    else:
        yield from _iter_apc_4line(path, max_rows)


def _make_apc_row(row_idx: int, sentence: str, aspect: str, category: str, sentiment: str) -> dict:
    return {
        "entity_id":    str(row_idx),
        "review_id":    str(row_idx),
        "sentence_idx": row_idx,
        "text_column":  "sentence",
        "sentence":     sentence,
        "aspect_terms": aspect,
        "categories":   category,
        "sentiments":   sentiment,
        "raw_sentence": sentence,
    }


def _iter_apc_csv(path: Path, max_rows: int = 0) -> Iterator[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row_idx, row in enumerate(reader):
            if len(row) < 4:
                continue
            sentence, aspect, category, sentiment = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
            if not sentence:
                continue
            yield _make_apc_row(row_idx, sentence, aspect, category, sentiment)
            if max_rows and row_idx + 1 >= max_rows:
                return


def _iter_apc_4line(path: Path, max_rows: int = 0) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]
    idx = 0
    row_idx = 0
    while idx + 3 < len(lines):
        sentence  = lines[idx].strip()
        aspect    = lines[idx + 1].strip()
        category  = lines[idx + 2].strip()
        sentiment = lines[idx + 3].strip()
        idx += 4
        if not sentence:
            continue
        yield _make_apc_row(row_idx, sentence, aspect, category, sentiment)
        row_idx += 1
        if max_rows and row_idx >= max_rows:
            return


def iter_records(
    path: Union[str, Path],
    *,
    text_column: str = "",
    id_column: str = "",
    input_format: str = "auto",
    max_reviews: int = 0,
    max_rows: int = 0,
) -> Iterator[dict]:
    fmt = detect_input_format_path(path) if input_format == "auto" else input_format
    if fmt == "apc":
        yield from iter_apc_records(path, max_rows=max_rows or max_reviews)
        return
    if fmt == "space":
        yield from iter_space_records(path, resolve_text_column("space", text_column), max_reviews, max_rows)
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}")
    row_limit = max_rows or max_reviews
    yield from load_flat_records(data, text_column, id_column, row_limit)


def load_records(
    path: Union[str, Path],
    *,
    text_column: str = "",
    id_column: str = "",
    input_format: str = "auto",
    max_reviews: int = 0,
    max_rows: int = 0,
) -> List[dict]:
    return list(iter_records(
        path,
        text_column=text_column,
        id_column=id_column,
        input_format=input_format,
        max_reviews=max_reviews,
        max_rows=max_rows,
    ))


def load_gold_cases(path: Union[str, Path]) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
