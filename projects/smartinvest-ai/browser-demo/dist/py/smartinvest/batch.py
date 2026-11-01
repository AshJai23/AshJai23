"""Bounded, offline CSV screening. No raw message or firm data in summaries."""
from __future__ import annotations

import csv
import io
from collections import Counter

from .detection import ENGINE_VERSION, scan_offer

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 500
ALLOWED_COLUMNS = {"sample_id", "offer_text", "website_url", "claimed_firm"}
SUMMARY_COLUMNS = ["row_number", "screening_status", "verification_status", "indicator_count", "finding_codes", "error"]


def screen_csv(data: bytes) -> dict:
    if not isinstance(data, bytes):
        raise TypeError("Upload must be CSV bytes")
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Provide a non-empty CSV no larger than 2 MiB")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must use UTF-8 encoding") from exc
    if "\x00" in text:
        raise ValueError("NUL characters are not supported")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    try:
        headers = reader.fieldnames
        if not headers or len(headers) != len(set(headers)) or any(x not in ALLOWED_COLUMNS for x in headers):
            raise ValueError("Use unique columns: sample_id, offer_text, website_url, claimed_firm")
        if not ({"offer_text", "website_url"} & set(headers)):
            raise ValueError("CSV needs offer_text or website_url")
        rows, counts = [], Counter()
        for row_number, row in enumerate(reader, 1):
            if row_number > MAX_ROWS:
                raise ValueError("CSV exceeds the 500-row limit; no partial batch is returned")
            record = {"row_number": row_number, "screening_status": "input_error",
                      "verification_status": "not_checked", "indicator_count": 0,
                      "finding_codes": "", "error": ""}
            if None in row or any(value is None for value in row.values()):
                record["error"] = "Row does not match the CSV header"
            else:
                try:
                    result = scan_offer(row.get("offer_text", ""), row.get("website_url", ""), row.get("claimed_firm", ""))
                except (ValueError, TypeError) as exc:
                    # Engine validation errors contain no raw input content.
                    record["error"] = str(exc)
                else:
                    codes = sorted({finding.code for finding in result.findings})
                    counts.update(codes)
                    record.update(screening_status=result.screening_status,
                                  indicator_count=len(result.findings), finding_codes="; ".join(codes))
            rows.append(record)
    except csv.Error as exc:
        raise ValueError("Malformed CSV; check quotes and field sizes") from exc
    if not rows:
        raise ValueError("CSV contains no data rows")
    summary = {
        "total_rows": len(rows),
        "rows_with_indicators": sum(x["screening_status"] == "warning_signals_detected" for x in rows),
        "rows_without_configured_indicators": sum(x["screening_status"] == "no_configured_indicators_detected" for x in rows),
        "input_error_rows": sum(x["screening_status"] == "input_error" for x in rows),
    }
    return {"engine_version": ENGINE_VERSION, "mode": "offline_user_supplied_csv",
            "verification_status": "not_checked", "summary": summary,
            "indicator_row_counts": dict(sorted(counts.items())), "rows": rows,
            "limitations": ["Counts are screening outcomes, not fraud labels or measured accuracy.",
                            "No indicators does not establish safety. No firm was verified.",
                            "Only generated row numbers are returned; raw messages, firms, URLs and supplied sample IDs are excluded."]}


def summary_csv(report: dict) -> bytes:
    """Export only allowlisted generated fields, never user-supplied text/IDs."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=SUMMARY_COLUMNS)
    writer.writeheader()
    for row in report["rows"]:
        writer.writerow({key: row[key] for key in SUMMARY_COLUMNS})
    return output.getvalue().encode("utf-8")
