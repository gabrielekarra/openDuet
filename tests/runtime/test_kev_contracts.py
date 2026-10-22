"""Portable regressions retained from the native Kev/learning implementation."""

from types import SimpleNamespace

import numpy as np
import pytest

from openduet.kev import learning, specialist
from openduet.kev.adapter import decisions_from_logits, record_for
from openduet.kev.schema import Bool, Choice


@pytest.mark.parametrize("bad", [[float("nan"), 1], [-1, 2], [0, 0], [1, 2, 3]])
def test_invalid_calibration_cannot_authorize_an_action(bad):
    with pytest.raises(ValueError, match="invalid Kev probability"):
        decisions_from_logits(
            [Bool("act", "Should act?")],
            [(0, False)],
            [np.array([0, 1])],
            temperature=2.406,
            calibrators=[SimpleNamespace(transform=lambda _: np.asarray([bad]))],
            elapsed_ms=1,
        )


def test_uncertainty_is_selected_probability_without_relative_confidence():
    result = decisions_from_logits(
        [Bool("act", "Should act?")],
        [(0, False)],
        [np.array([0, 0])],
        temperature=2.406,
        calibrators=[None],
        elapsed_ms=1,
    )[0]
    assert result.value is False and result.confidence == 0.5
    assert result.raw_probabilities == {"false": 0.5, "true": 0.5}


@pytest.mark.parametrize(
    "approved,dismissed,expired,sign",
    [(1, 1, 0, 0), (0, 12, 0, 1), (12, 0, 0, -1), (5, 5, 0, 0), (0, 0, 6, 0)],
)
def test_adaptive_floor_uses_prior_minimum_labels_and_weak_timeout(approved, dismissed, expired, sign):
    value = learning.floor_offset(learning.KindStats("mail.received", approved, dismissed, expired))
    assert (value > 0) - (value < 0) == sign
    assert -learning.MAX_LOWER <= value <= learning.MAX_RAISE


def test_specialist_hash_and_multilingual_subject_features_remain_stable():
    assert specialist._index("bias") == 65716
    event = {
        "kind": "mail.received",
        "app": "mail",
        "payload": {"sender": "Techmeme <news@techmeme.com>", "subject": "Re: Daily", "body": "Is it?"},
    }
    assert {
        "from:news@techmeme.com",
        "domain:techmeme.com",
        "from:automated",
        "subj:is_reply",
        "body:question",
    } <= set(specialist.feature_names(event))
    assert specialist.normalized_subject("R: Re: Contratto") == "contratto"


def test_debiased_rows_keep_exact_opaque_labels():
    q = Choice("target", "Which?", ("event:42", "none"), debias=True)
    record, owners = record_for("context", [q])
    assert record["questions"][1]["options"] == ["none", "event:42"]
    result = decisions_from_logits(
        [q], owners, [np.array([3, 0]), np.array([0, 3])], temperature=2.406, calibrators=[None], elapsed_ms=1
    )[0]
    assert result.value == "event:42" and result.confidence > 0.95
