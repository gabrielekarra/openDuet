# Proactivity and learning

Connect email directly with a provider app password, or connect an MCP server
and configure a **read-only** poll tool in Connections. See
[account setup](CONNECTORS.md).
Polling stores versioned events, durable pagination cursors and content hashes.
Unchanged records do not create new events; changed calendar records retain an
edit event. Gmail, Microsoft mail, calendar and Slack wire fields have
normalizers; generic MCP servers can return the documented event contract.

Each event carries `id`, `source`, `kind`, timestamp, actors, subject, bounded
text, links and an untrusted payload. No continuously sampled desktop data enters
this stream. Configure timezone, language, work/quiet hours, morning brief
(default 07:30 local), optional evening report, VIP/always/never rules and caps.
Local-date claims prevent duplicate scheduled runs across restarts and DST.

Kev is the decision model, separate from the selected work LLM. Bool, Score and
Choice answers carry calibrated probabilities. Host policy uses the weakest
confidence among answers actually used, checks personal floors, quiet/busy
state, pauses, muted senders and daily interruption caps, then chooses:

| Result | Behavior |
| --- | --- |
| ignore | Keep an explainable decision, no notification |
| brief | Candidate for the next selected 3–7-item brief |
| prepare | Create a task that delivers finished draft/prep work |
| notify_silent | Deliver without notification sound |
| interrupt | Deliver an urgent actionable event within the cap |

Delivered urgent items are not repeated as new items in the morning brief.
When Kev is missing, unavailable or invalid, the fallback is brief-only; the
ordinary LLM does not silently replace the per-event judge. Work-model tokens
and Kev decisions have separate counters.

Urgent interruption requires a confident binary answer to whether attention is
needed now. The probability of one exact 1–5 urgency rating is not used as the
probability that a message is time-critical. Both question wording and labelled
evaluation corpora are fingerprinted in real benchmark reports.

Sent messages can establish commitments only after a typed promise decision.
Dates are parsed deterministically in English/Italian relative to the sent
message and timezone. Sent threads explicitly awaiting replies can prepare one
quiet nudge after three working days; a later reply suppresses it. Calendar overlaps and
a configurable travel buffer supply facts for conflict decisions; any proposed
move still needs approval. Busy state is refreshed from current calendar events.

Explicit useful/dismiss feedback adjusts per-kind floors after six labels using
a Beta(2,2) prior and bounded changes. Three consecutive explicit sender
dismissals mute the sender; an approval resets the streak. Users can undo/reset
rules. Exact reply/thread identifiers provide strong implicit positive labels;
weak timeout evidence cannot mute a sender. The NumPy personal specialist uses
held-out labels and a 95% quiet-precision gate before it can suppress events.
It is retrained daily and keeps shadow checks. It never learns from its own
quiet decisions or unavailable-Kev fallback as teacher evidence. Forgetting also
excludes prior teacher decisions from future training. Per-connector cadence
can be changed in chat or the console; initiatives can be snoozed or dismissed.

Proactivity shows decisions, readouts, probabilities, thresholds, tier, reason,
commitments and learned rules. `/why` replies and inline feedback explain the
stored decision without an LLM call; `/quiet` lists held-back decisions. Text
retention defaults to 30 days. Disconnecting a connector removes its events,
labels, commitments and related learned sender overrides and invalidates the
specialist. Resetting learning also removes its model file.

Live usefulness and calibration must be evaluated with your own accounts and
labels. [Kev evaluation](kev/README.md) separates those results from synthetic
adapter regression tests.
