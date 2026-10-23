"""Refuse changed trained heads and overflow before any inference is dispatched."""

import hashlib
from types import SimpleNamespace

import pytest

from openduet.kev import models


def test_corrupt_head_is_refused_even_when_file_size_matches(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "ROOT", tmp_path)
    directory = tmp_path / "fixture--kev"
    directory.mkdir()
    head = directory / "head.pt"
    original = b"pinned trained head"
    head.write_bytes(original)
    entry = {
        "id": "fixture/kev",
        "files": [{"name": "head.pt", "size": len(original), "sha256": hashlib.sha256(original).hexdigest()}],
    }
    assert models.verify(entry) == directory
    head.write_bytes(b"changed trained hea")
    assert head.stat().st_size == len(original)
    with pytest.raises(ValueError, match="checksum"):
        models.verify(entry)


def test_state_over_4096_is_refused_without_truncation_or_inference():
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from openduet.kev.vendor.kev.model import ContextOverflow, encode

    class Tokenizer:
        def __call__(self, text, **kwargs):
            return SimpleNamespace(input_ids=[1] * len(text.split()))

        def convert_tokens_to_ids(self, text):
            return 2

    record = {"state": "token " * 4096, "questions": []}
    with pytest.raises(ContextOverflow) as error:
        encode(Tokenizer(), record, max_state=4096, max_branch=8192, strict=True)
    assert error.value.state_tokens == 4097 and error.value.max_state == 4096
    record["state"] = "token " * 4095
    encoded = encode(Tokenizer(), record, max_state=4096, max_branch=8192, strict=True)
    assert len(encoded["ids"]) == 4096
