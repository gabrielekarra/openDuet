"""Record-specific links and export citations must originate in the current task."""

import json

import pytest
from openpyxl import load_workbook

from openduet import artifacts, make
from openduet.citations import Sources
from openduet.store import Store


def test_collection_records_do_not_borrow_each_others_links(tmp_path):
    store = Store(tmp_path)
    task = store.new_task("main", "Summarize invoices", "local")
    sources = Sources(store)
    result = sources.register(
        task,
        "stripe",
        {
            "structuredContent": {
                "data": [
                    {"id": "in-1", "amount_due": 100, "hosted_invoice_url": "https://invoice.stripe.com/i/1"},
                    {"id": "in-2", "amount_due": 200, "hosted_invoice_url": "https://invoice.stripe.com/i/2"},
                ]
            }
        },
    )
    lookup = {row["id"]: row for row in sources.listing(task)}
    assert lookup[result["source_id"]]["url"] == ""
    first, second = result["sources"]
    assert first["source_id"] != second["source_id"]
    assert first["url"].endswith("/1") and second["url"].endswith("/2")
    assert json.loads(lookup[second["source_id"]]["excerpt"])["record"]["amount_due"] == 200
    assert sources.register(task, "stripe", result["data"])["sources"] == result["sources"]


def test_unknown_and_foreign_task_export_citations_are_rejected(tmp_path):
    store = Store(tmp_path)
    first = store.new_task("main", "First", "local")
    second = store.new_task("main", "Second", "local")
    source = Sources(store).register(first, "search", {"url": "https://example.test", "value": 12})[
        "source_id"
    ]
    for ident in (source, "invented"):
        with pytest.raises(ValueError, match="Unverified artifact source"):
            artifacts.create(store, tmp_path / "artifacts", second, "Rejected", "md", f"12 [^{ident}]")
    assert not store.rows("SELECT * FROM artifacts")


def test_numeric_workbook_cell_has_validated_source_link_and_comment(tmp_path, monkeypatch):
    store = Store(tmp_path)
    task = store.new_task("main", "Invoice total", "local")
    source = Sources(store).register(
        task, "invoice", {"url": "https://invoice.stripe.com/i/2", "amount": 200}
    )["source_id"]
    # This test verifies provenance; native recalculation is accepted separately.
    monkeypatch.setattr(make, "recalculate", lambda path: {"test": "source links only"})
    spec = {"sheets": [{"name": "Invoices", "cells": {"A1": {"value": 200, "source_ids": [source]}}}]}
    artifact = artifacts.create(
        store, tmp_path / "artifacts", task, "Sourced total", "xlsx", json.dumps(spec)
    )
    row = store.rows("SELECT filename FROM artifacts WHERE id=?", (artifact["id"],))[0]
    book = load_workbook(tmp_path / "artifacts" / row["filename"])
    cell = book["Invoices"]["A1"]
    assert cell.value == 200
    assert cell.hyperlink.target == "https://invoice.stripe.com/i/2"
    assert f"[^{source}]" in cell.comment.text
    book.close()
    spec["sheets"][0]["cells"]["A1"]["source_ids"] = ["foreign"]
    with pytest.raises(ValueError, match="source_ids"):
        artifacts.create(store, tmp_path / "artifacts", task, "Rejected", "xlsx", json.dumps(spec))
