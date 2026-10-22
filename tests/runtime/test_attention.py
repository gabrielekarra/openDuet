import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from openduet.attention import policy
from openduet.config import Config
from openduet.kev import learning, specialist
from openduet.kev.adapter import decisions_from_logits, record_for
from openduet.kev.schema import Bool, Choice, Decision, Score
from openduet.runtime import Runtime
from openduet.store import Store


def answer(name, value, confidence=0.98):
    if isinstance(value, bool):
        labels, kind, key = ["false", "true"], "bool", str(value).lower()
    elif isinstance(value, int):
        labels, kind, key = [str(i) for i in range(1, 6)], "score", str(value)
    else:
        labels, kind, key = ["request", "newsletter", "FYI"], "choice", value
    probabilities = {
        label: confidence if label == key else (1 - confidence) / (len(labels) - 1) for label in labels
    }
    return Decision(name, kind, value, probabilities, probabilities, confidence, 1, 1)


@pytest.mark.parametrize(
    "values,context,expected",
    [
        ({}, {}, "brief"),
        ({"message_type": answer("message_type", "newsletter")}, {}, "ignore"),
        ({"message_type": answer("message_type", "newsletter", 0.5)}, {}, "brief"),
        ({"urgency": answer("urgency", 5), "asks_user": answer("asks_user", True)}, {}, "interrupt"),
        (
            {"urgency": answer("urgency", 5), "asks_user": answer("asks_user", True)},
            {"quiet": True},
            "notify_silent",
        ),
        (
            {"urgency": answer("urgency", 5), "asks_user": answer("asks_user", True)},
            {"busy": True},
            "notify_silent",
        ),
        (
            {"urgency": answer("urgency", 5), "asks_user": answer("asks_user", True)},
            {"capped": True},
            "notify_silent",
        ),
        (
            {"urgency": answer("urgency", 5), "asks_user": answer("asks_user", True)},
            {"paused": True},
            "brief",
        ),
        ({"urgency": answer("urgency", 5, 0.5), "asks_user": answer("asks_user", True)}, {}, "brief"),
        ({"asks_user": answer("asks_user", True)}, {}, "prepare"),
        ({"prepare": answer("prepare", True)}, {}, "prepare"),
        ({"urgency": answer("urgency", 2)}, {}, "brief"),
        (
            {"urgency": answer("urgency", 5), "asks_user": answer("asks_user", True)},
            {"muted": True},
            "ignore",
        ),
    ],
)
def test_deterministic_policy_every_branch(values, context, expected):
    outcome = policy({"kind": "mail.received"}, values, 0.65, context)
    assert outcome["action"] == expected


def test_pointer_schema_preserves_ranges_debias_and_probability():
    import numpy as np

    questions = [
        Bool("reply", "Needs a reply?"),
        Score("urgency", "Urgency?", 3, 5),
        Choice("target", "Which?", ("opaque:42", "none"), debias=True),
    ]
    record, owners = record_for("Untrusted event", questions)
    assert record["questions"][0]["options"] == ["no", "yes"]
    assert record["questions"][-1]["options"] == ["none", "opaque:42"]
    rows = [np.array(row) for row in ([0, 4], [0, 4, 0], [4, 0], [0, 4])]
    decisions = decisions_from_logits(
        questions, owners, rows, temperature=2, calibrators=[None] * 3, elapsed_ms=3
    )
    assert [value.value for value in decisions] == [True, 4, "opaque:42"]
    assert all(sum(value.probabilities.values()) == pytest.approx(1) for value in decisions)


@pytest.fixture
def runtime(tmp_path):
    return Runtime(Config(data_dir=tmp_path), Store(tmp_path))


async def test_urgent_event_once_restart_and_fallback(runtime):
    runtime.attention.configure(
        {
            "working_days": list(range(7)),
            "working_start": "00:00",
            "working_end": "23:59",
            "quiet_start": "23:59",
            "quiet_end": "00:00",
        }
    )
    runtime.telegram.save(connected=True, paired=True, owner_id=1, owner_chat=1)

    async def readouts(event, context):
        return [answer("urgency", 5), answer("asks_user", True)]

    runtime.attention.readouts = readouts
    runtime.attention.events.ingest(
        "gmail",
        [
            {
                "id": "urgent",
                "subject": "Urgent request",
                "sender": "Marco <marco@example.test>",
                "text": "Please confirm before noon.",
            }
        ],
    )
    row = runtime.store.rows("SELECT * FROM connector_events")[0]
    await runtime.attention.triage(row)
    await runtime.attention.triage(row)
    assert len(runtime.store.rows("SELECT * FROM decisions")) == 1
    assert len(runtime.store.rows("SELECT * FROM telegram_outbox")) == 1
    assert runtime.store.rows("SELECT * FROM decisions")[0]["sender"] == "marco@example.test"
    await runtime.close()


async def test_missing_kev_is_brief_only(runtime):
    runtime.attention.events.ingest("gmail", [{"id": "urgent", "text": "urgent urgent urgent!"}])
    await runtime.attention.triage(runtime.store.rows("SELECT * FROM connector_events")[0])
    decision = runtime.store.rows("SELECT * FROM decisions")[0]
    assert decision["action"] == "brief" and decision["tier"] == "fallback"
    assert runtime.store.rows("SELECT * FROM telegram_outbox") == []
    await runtime.close()


async def test_three_dismissals_mute_sender_and_undo_resets_count(runtime):
    now = time.time()
    for index in range(3):
        runtime.store.execute(
            "INSERT INTO decisions(decision_id,event_id,ts,kind,app,sender,action,response,response_reason,readouts,event_payload) VALUES(?,?,?,?,?,?,'interrupt','dismiss','user','[]','{}')",
            (str(index), str(index), now - 10 + index, "mail.received", "gmail", "marco@example.test"),
        )
    with runtime.store.db() as db:
        personal = learning.Personalizer(db)
        assert len(personal.muted) == 1
        assert personal.muted_sender(
            {"kind": "mail.received", "payload": {"sender": "Marco <marco@example.test>"}}
        )
        personal.forget(personal.muted[0].rule_id)
        assert personal.muted == []
    runtime.attention.forget()
    assert runtime.store.rows("SELECT * FROM labels") == []
    await runtime.close()


async def test_specialist_requires_held_out_agreement(runtime):
    assert specialist._verdict(specialist.Metrics(personal_labels=29))[0] is False
    assert (
        specialist._verdict(
            specialist.Metrics(
                personal_labels=40, validation=10, accuracy=0.99, teacher_accuracy=0.8, quiet_precision=0.94
            )
        )[0]
        is False
    )
    assert (
        specialist._verdict(
            specialist.Metrics(
                personal_labels=40, validation=10, accuracy=0.99, teacher_accuracy=0.8, quiet_precision=0.98
            )
        )[0]
        is True
    )
    examples = [
        specialist.Example(
            str(i),
            time.time() - 100 + i,
            {"kind": "mail.received", "payload": {"sender": "news@example.test", "body": "newsletter"}},
            0,
            1,
            "user",
            False,
        )
        for i in range(20)
    ]
    trained = specialist.train(examples)
    assert not trained.enabled
    await runtime.close()


async def test_brief_local_time_dst_and_no_duplicate_fold(runtime):
    runtime.attention.configure(
        {"timezone": "Europe/Rome", "brief_time": "02:30", "working_days": list(range(7))}
    )
    spring = datetime(2026, 3, 29, 3, 0, tzinfo=ZoneInfo("Europe/Rome")).timestamp()
    assert await runtime.attention.brief(now=spring) is None
    # Forced delivery creates one task and the local-day claim survives a restart.
    task = await runtime.attention.brief(force=True, now=spring)
    assert task
    assert await runtime.attention.brief(now=spring + 60) is None
    fall = datetime(2026, 10, 25, 2, 30, tzinfo=ZoneInfo("Europe/Rome"), fold=0).timestamp()
    await runtime.attention.brief(force=True, now=fall)
    assert await runtime.attention.brief(now=fall + 3600) is None
    await runtime.close()


async def test_forgetting_connector_deletes_learning_and_events(runtime):
    runtime.attention.events.ingest("gmail", [{"id": "one", "text": "A fixture"}])
    await runtime.attention.triage(runtime.store.rows("SELECT * FROM connector_events")[0])
    runtime.attention.forget_connector("gmail")
    assert runtime.store.rows("SELECT * FROM decisions") == []
    assert runtime.store.rows("SELECT * FROM connector_events") == []
    await runtime.close()
