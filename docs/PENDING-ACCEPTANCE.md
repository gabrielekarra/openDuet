# Remaining acceptance steps — 24 October 2026

These are the remaining issue criteria, not features silently marked completed.
Do not send credentials in issues or chat. Private live reports stay outside Git.

| Issue | Missing prerequisite/evidence | Concrete validation path |
| --- | --- | --- |
| #12 | An accessible VM run with collected startup/recovery results. The first local QEMU cloud-init boot could not clone GitHub through the managed network; the proxy/CA retry's result was not collected before the terminal became unavailable. No provider VM was provisioned. | Apply [cloud-init](../deploy/cloud-init.yaml) to an Ubuntu VM as described in [self-hosting](SELF-HOSTING.md). Confirm cloud-init completes, all Compose services become healthy, authenticated workspace access works, and the separate computer can read a public page. Restart Docker and reboot the guest, checking health and persistent workspace data after each. Preserve managed proxy and CA settings. A local VM result must be labelled as such. |
| #15 | Published, passing schema/transport fixtures for each service; the pending local test changes could not be collected. Gusto also requires enforced isolation and confirmation for all calls before enablement. | Use the [17 setup entries](LAUNCH-CONNECTORS.md). Finish the pending per-service fixture changes and run the full runtime suite/CI. For an account check, discover actual read tools and use [openduet-check-connectors --live](CONNECTOR-ACCEPTANCE.md); fixture names are not provider canonical names. |
| #18 | An eligible Stripe Issuing sandbox/test account, approved cardholder and authenticated test webhooks. No issuer credentials are configured. | Follow the purchase prerequisites in [security](SECURITY.md) and the configuration fields in [the wallet endpoint](../openduet/product_extras.py), keeping the feature off outside the test. Verify no card before approval, exact approved currency/amount/merchant/expiry, checkout receipt and cancellation after use. Retain only redacted provider event IDs/statuses. The mock transport is not a provider sandbox. |
| #26 | Owner attestation about historical development-key use. The repository cannot establish deployment history. | Confirm that no real production credential was derived from the historical key; if it was, rotate/revoke it in the actual issuer/deployment and record that completion without key material. Never reuse the retired key. |
| #39 | An actual user's empty-install → paired-owner Telegram measurement. No real BotFather token or user-device result is available here. | Follow the [Mac quickstart](QUICKSTART-MAC.it.md), start the timer at token entry, connect and pair in Telegram, and record elapsed time (target under 2 minutes). Do not include the token, pairing link/code or screenshots containing them in evidence. |
| #44 | The owner's paired Telegram client plus a working public HTTPS deployment. A loopback fixture does not exercise the Telegram webview. | Set the workspace's HTTPS public_url as in [self-hosting](SELF-HOSTING.md), open Tasks and Make from inside Telegram without entering a workspace token, then confirm disconnect/revocation removes access. Existing tests cover stale/tampered/wrong-owner initData. |
| #5 | #26. Native source retirement and naming cleanup are otherwise accounted for. | Close after the historical-key criterion is resolved. The owner's approved on-demand Mac bridge remains. |
| #31 | #39 and #44. | Close after the actual onboarding and owner-webview checks. |
| #4 | #12, #15, #18 and #31, plus the recorded retirement boundary. | Review the live issue criteria and [capability differences](CLAUDE-DUET-RESEARCH.md); do not assert universal Claude Duet equivalence. |

## Target Mac acceptance

Remote control of the owner's own Mac still needs that Mac signed in, awake and
running OpenDuet, with Accessibility and Screen Recording granted to the actual
service interpreter. Run `openduet doctor`, then send `/apps` and `/screen` to
the paired bot, request an installed app such as Calculator, and approve an
interaction with its observed controls. Confirm the screenshot arrives in the
private chat and disabling Mac access stops commands. The
[remote-access guide](REMOTE-ACCESS.md) explains the permissions and sleep limits.

## Kev boundaries retained after closure

#32's exact-label server-port criterion is satisfied by the real BF16/MLX fixed
reference (64/64 labels), and #30's implementation children are complete.
This does not make INT8 universally exact: one seed answer still differs.
Consumer-GPU performance, the owner's 16 GiB Mac budget, sustained personal-event
throughput and real-account calibration remain unmeasured. Use the
[precision-specific commands and reports](kev/README.md) for those measurements.
