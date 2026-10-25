# OpenDuet launch kit

Prepared 25 October 2026. These are drafts and an execution plan, not a record of posts published or results obtained. Nothing has been submitted to a community from this kit.

Landing page: https://openduet.gabrielekarra.chatgpt.site

Source and installation: https://github.com/gabrielekarra/openDuet

Use the landing page for the visual tour and the repository for runnable source. The landing page is public. X posts below use its live URL; technical/community drafts retain the repository URL where runnable source is appropriate.

## The message

**EN:** Hand work to your Telegram bot. Choose the model behind it.

OpenDuet is an MIT-licensed, self-hosted Telegram assistant for tasks, files and actions you approve. Use a compatible local model or a hosted API. Optional Mac access adds on-demand screenshots and installed-app interactions with macOS permissions.

**IT:** Affida un compito al tuo bot Telegram. Scegli tu il modello.

OpenDuet è un assistente Telegram open source MIT e self-hosted: riceve compiti, crea file e ti chiede di approvare le azioni esterne. Puoi usare un modello locale compatibile oppure un’API. L’accesso Mac opzionale aggiunge screenshot su richiesta e interazioni con le app installate, con i permessi di macOS.

The first audience is developers and self-hosters who already run local models and want a useful handoff from their phone. Lead with a single request → review → file workflow, then explain model choice. Use the optional Mac bridge as a second demonstration after it has been exercised on the target Mac.

## Claims and evidence

| Say | Evidence or qualification |
| --- | --- |
| MIT-licensed and self-hosted | [License](../LICENSE), [self-hosting](SELF-HOSTING.md) |
| Local and API model support | Ollama, Anthropic and OpenAI-compatible adapters; models still need suitable context/tool capabilities. [Setup](QUICKSTART-MAC.md) |
| Tasks, files and external-action review | [Make](MAKE.md), [approval and transport validation](VALIDATION.md) |
| A separate browser for public websites | [Recorded actual Ubuntu VM acceptance](benchmarks/cloud-vm-acceptance-2026-10-24.json) and isolated-computer checks |
| Optional Mac screenshots and installed-app interaction | [Remote access](REMOTE-ACCESS.md); actual target-Mac permissions and end-to-end device acceptance remain required |
| Proactive briefs and attention decisions | [Proactivity](PROACTIVITY.md); Kev weights are an explicit download and require their own resource budget |
| A release candidate people can install | Versioned `v0.4.0rc4` source and Mac guide. No signed `.dmg` or published GitHub Release is promised |

Describe demo accounts, sample data and fixture models when they appear in a clip. A fixture-backed walkthrough is a product tour, not proof of live provider acceptance. The [post-closure checklist](PENDING-ACCEPTANCE.md) retains live bot/webview, issuer and historical-key checks. Closing all issues did not establish those facts.

Use “compatible local and API models”, rather than promising equal results with every LLM. OpenDuet is independent of Anthropic; do not claim full Claude Duet equivalence or partner Link/Shop Pay access. MIT does not remove model, API, hosting or Telegram-service costs and constraints. Telegram bot traffic passes through Telegram; local inference does not make that traffic end-to-end encrypted.

## X posts

Attach the short product clip to one post; label the clip “Sample workspace” when applicable. The text is under 280 characters even when counting the full repository URL.

**EN — 231 characters**

```text
Your Telegram bot can do more than chat.

OpenDuet takes tasks, returns files and asks you to approve external actions. Self-host it with a local model or an API.

MIT. Release candidate.
https://openduet.gabrielekarra.chatgpt.site
```

**IT — 241 characters**

```text
Il tuo bot Telegram può fare più che chattare.

OpenDuet riceve compiti, restituisce file e ti chiede di approvare le azioni esterne. Self-hosted, con modelli locali o API.

MIT. Release candidata.
https://openduet.gabrielekarra.chatgpt.site
```

Optional follow-up after someone asks how it works:

**EN**

```text
The work model is your choice: Ollama, LM Studio, an OpenAI-compatible server or a supported API.

Consequential actions go through review. Mac access is opt-in and needs macOS permissions.

Setup and measured limits are in the repo:
https://openduet.gabrielekarra.chatgpt.site
```

**IT**

```text
Il modello di lavoro lo scegli tu: Ollama, LM Studio, un server compatibile OpenAI o un’API supportata.

Le azioni esterne richiedono una revisione. L’accesso Mac è opzionale e richiede i permessi di macOS.

Guida e limiti:
https://openduet.gabrielekarra.chatgpt.site
```

## LinkedIn posts

Adapt the first-person affiliation to the actual person publishing. These drafts make no claim about years of development, customers or launch traction.

**EN**

```text
I’m sharing OpenDuet: an open-source assistant you can hand work to through your own Telegram bot.

Send a task, review an external action when it needs approval, and get the resulting document or file back. The work model can run locally through tools such as Ollama or LM Studio, or use a supported hosted API.

It is self-hosted and MIT-licensed. It also includes a separate browser and an optional Mac bridge for on-demand screenshots and installed apps, with the required macOS permissions.

This is a release candidate. The walkthrough uses sample accounts and data; the repository separates automated evidence from live account and device checks still to be completed.

If you try it, the most useful feedback is your model, installation platform and the first task that succeeded or failed.

Source, installation and measured limits:
https://github.com/gabrielekarra/openDuet
```

**IT**

```text
Presento OpenDuet: un assistente open source a cui puoi affidare lavoro dal tuo bot Telegram.

Invii un compito, rivedi le azioni esterne che richiedono approvazione e ricevi il documento o il file risultante. Il modello di lavoro può essere locale, per esempio tramite Ollama o LM Studio, oppure usare un’API supportata.

È self-hosted e ha licenza MIT. Include anche un browser separato e un accesso Mac opzionale per screenshot su richiesta e app installate, con i permessi richiesti da macOS.

È una release candidata. Il tour usa account e dati di esempio; nel repository sono distinte le prove automatiche dalle verifiche reali su account e dispositivi ancora da completare.

Se lo provi, il feedback più utile è: modello usato, piattaforma di installazione e primo compito riuscito o fallito.

Codice, installazione e limiti misurati:
https://github.com/gabrielekarra/openDuet
```

## Show HN: maker briefing, not text to paste

HN’s current [general guidelines](https://news.ycombinator.com/newsguidelines.html) prohibit generated or AI-edited submissions/comments and automated posting. The maker must write the actual title and first comment independently, in their own words. Do not paste or lightly edit this kit into HN.

The [Show HN guidelines](https://news.ycombinator.com/showhn.html) require something the author personally worked on that readers can try. Link runnable source/install instructions, not a landing-only or signup page. Be present to discuss it. Do not solicit votes, comments or submissions.

**Internal working title / titolo di lavoro:**

> Show HN: OpenDuet, a Telegram assistant for local and API models

**First maker comment — facts to cover, EN:**

- State your actual role and personal reason for making the project; supply your own experience.
- Explain the handoff: a private owner-paired Telegram bot, durable task, reviewable action, delivered file.
- Explain the model interface: native Ollama and Anthropic adapters, plus OpenAI-compatible servers and a validated text-tool protocol where appropriate.
- State the release candidate and installation requirements. Link the repository and the Mac quickstart; a shared demonstration bot is not supplied.
- Explain the isolated browser and opt-in Mac bridge. Distinguish a sample-workspace tour from a real owner-device run.
- Acknowledge unverified live provider/device checks, workload-dependent model quality and the separate Kev resource budget.
- Ask one technical question you actually want answered, chosen from your own experience with the build. Stay to answer replies.

**Primo commento maker — traccia IT:**

- Racconta il tuo ruolo e il problema che hai incontrato personalmente.
- Descrivi un compito completo: messaggio al bot privato, revisione, file consegnato.
- Spiega come scegli il modello e quali capacità gli servono.
- Collega codice e installazione, indicando che è una release candidata.
- Distingui browser isolato, ponte Mac opzionale e tour con dati di esempio.
- Riporta i limiti verificati e le prove reali ancora mancanti.
- Formula una domanda tecnica autentica e rimani disponibile per la discussione.

## Product Hunt submission

The official [launch guide](https://help.producthunt.com/en/articles/17350772-launch-guide) specifies 60 characters for the tagline and 260 for the description, plus product-in-use gallery media and a short demo. Featuring is a curation decision, not a promised outcome. Complete a fresh install and actual first-task handoff before scheduling a launch.

**EN tagline — 56 characters**

```text
A Telegram assistant that runs with your choice of model
```

**EN description — 247 characters**

```text
Hand off tasks in Telegram, get files back, and approve external actions. OpenDuet is MIT-licensed and self-hosted, with local or API models, an isolated browser, and opt-in Mac access. Release candidate; provider and device checks are documented.
```

**IT tagline — 51 characters**

```text
Un assistente Telegram con il modello che scegli tu
```

**IT description — 241 characters**

```text
Affida compiti via Telegram, ricevi file e approva le azioni esterne. OpenDuet è open source MIT e self-hosted: modelli locali o API, browser isolato e accesso Mac opzionale. Release candidata; verifiche di account e dispositivi documentate.
```

**Maker comment draft, EN**

```text
I’m sharing OpenDuet for people who already use local models and want to hand them work from their phone.

You connect your own BotFather bot, choose a model and send it a task. OpenDuet keeps task state, creates files and asks for review before consequential external actions. There is also an isolated browser and an opt-in Mac bridge.

This is an MIT-licensed release candidate. Models, API usage and hosting can have their own costs. The sample-workspace tour and measured validation are linked in the repository; live device and provider checks still have a separate checklist.

If you install it, tell me which model you used and where the first task worked or got stuck. That will help improve the next release.
```

**Bozza del commento maker, IT**

```text
Presento OpenDuet a chi usa già modelli locali e vuole affidare loro lavoro dal telefono.

Colleghi il tuo bot creato con BotFather, scegli il modello e invii un compito. OpenDuet conserva lo stato del lavoro, crea file e chiede una revisione prima delle azioni esterne rilevanti. Include anche un browser isolato e un ponte Mac opzionale.

È una release candidata con licenza MIT. Modelli, API e hosting possono avere costi propri. Il tour con dati di esempio e le verifiche misurate sono nel repository; le prove reali su dispositivi e provider hanno una checklist separata.

Se lo installi, indicami il modello usato e dove il primo compito è riuscito o si è bloccato: servirà a migliorare la prossima release.
```

Use up to three relevant topics available in the submission UI. Prepare four clear screenshots and the demo clip. The official [sharing guidance](https://help.producthunt.com/en/articles/2690626-how-do-i-share-my-post) permits organic sharing and forbids mass messaging for votes, vote incentives and coordinated voting. Ask for product feedback, not upvotes.

## Reddit: choose the right route first

Rules were checked on 25 October 2026; re-read them in the actual account before posting. Posting eligibility and account history have not been inspected.

- **r/LocalLLaMA:** the [official rules](https://old.reddit.com/r/LocalLLaMA/about/rules) prohibit primarily LLM-generated copy/code, forbid bots posing as humans, require disclosed affiliation and use a roughly 10% self-promotion guideline. The exception for non-native speakers covers disclosed translation/refinement. An AI-origin English draft does not become eligible merely by translating it. Use the technical facts above to write your own original account of actual local-model testing; do not paste this kit there. A mostly generated project may itself be ineligible under the rule; check with moderators before a promotional submission.
- **r/selfhosted:** the [official community sidebar](https://www.reddit.com/r/selfhosted/wiki/rules/) requires production-ready promoted apps with documentation. Rule 6 restricts projects younger than three months from first public presence to the current New Project Megathread. The old source history does not establish how long this renamed/public project has been public. With age and release-candidate eligibility unconfirmed, use the current megathread if its terms permit; do not assume a standalone launch post is allowed. The wiki body is disabled, but its official rules sidebar was visible during this check.

**Technical draft for a permitted self-hosting thread, EN**

```text
OpenDuet — MIT self-hosted Telegram assistant with local/API model support

Disclosure: I maintain OpenDuet. AI tools were used in development and in preparing this draft.

The project connects a BotFather bot you own to a persistent task workspace. You can hand it work from Telegram, review proposed external actions and get generated files back. It supports native Ollama and Anthropic adapters, OpenAI-compatible model servers, and a validated text-tool protocol for suitable models without native tool calling.

The stack is Python 3.12+, SQLite and a web console. The Compose deployment separates the workspace, Chromium computer, egress proxy, prototype origin and Kev attention service. Kev weights are downloaded explicitly and need their own memory budget; you can use the work model without loading Kev.

The Mac bridge is opt-in and requires Accessibility/Screen Recording permissions. Telegram bot messages pass through Telegram. A local work model does not make the messaging transport end-to-end encrypted.

This is a release candidate. Actual Chromium, Office, local-model, Mac login-service and VM-restart evidence is documented. Provider/bot fixtures are labelled separately, and live target-device, issuer and owner-webview checks remain in the acceptance checklist.

Source and installation:
https://github.com/gabrielekarra/openDuet

Useful feedback: your OS, model/protocol and the first reproducible task failure. Please keep tokens, pairing codes and private account data out of reports.
```

**Versione IT per una community che ammette l’italiano**

```text
OpenDuet — assistente Telegram self-hosted MIT con modelli locali o API

Disclosure: sviluppo e mantengo OpenDuet. Ho usato strumenti AI nello sviluppo e nella preparazione di questa bozza.

Collega un bot BotFather di tua proprietà a uno spazio di lavoro con compiti persistenti. Puoi affidare lavoro da Telegram, rivedere le azioni esterne proposte e ricevere i file generati. Supporta Ollama e Anthropic nativi, server compatibili OpenAI e un protocollo testuale validato per modelli adatti senza tool calling nativo.

Lo stack usa Python 3.12+, SQLite e una console web. Compose separa workspace, browser Chromium, proxy di uscita, origine dei prototipi e servizio di attenzione Kev. Il download dei pesi Kev è esplicito e richiede memoria dedicata; il modello di lavoro può essere usato senza caricare Kev.

Il ponte Mac è opzionale e richiede Accessibilità e Registrazione schermo. I messaggi del bot passano dai server Telegram: usare un modello locale non rende il trasporto end-to-end encrypted.

È una release candidata. Le prove misurate e i trasporti fixture sono distinti nella documentazione; alcune verifiche reali su dispositivi, issuer e webview del proprietario restano nella checklist.

Codice e installazione:
https://github.com/gabrielekarra/openDuet

Feedback utile: sistema operativo, modello/protocollo e primo errore riproducibile. Non pubblicare token, codici di pairing o dati di account privati.
```

## Seven-day execution plan

These are proposed actions, not scheduled posts. A channel is skipped when its account or community rules are not met. Start with owned/public project surfaces and voluntary testers, then expand after the first successful independent handoffs.

| Day | Publish or do | Evidence to retain |
| --- | --- | --- |
| 1 | Ship the landing page, labelled demo, source links and installation guide. Check every CTA on a phone. Publish one EN or IT post on an owned account when its text/media are approved. | Live URL, source revision and the actual post URL |
| 2 | Help a small set of people who voluntarily opt in install it. Observe one first task with a real model. Record friction instead of asking for stars. | Consented, redacted installation/task results; no tokens or private prompts in Git |
| 3 | Show one reproducible local-model workflow. Record model, version/protocol, hardware and elapsed time; label sample data. Share a narrow technical follow-up. | Reproduction steps and real measured result |
| 4 | If eligible, the maker writes and submits Show HN in their own words with runnable source and remains available. Otherwise use the time to fix onboarding. | Actual thread URL and concrete questions; no vote solicitation |
| 5 | Use the appropriate self-hosting megathread if its terms allow the release candidate. Use LocalLLaMA only after checking its generated-project and account-history rules. | The permitted thread URL and disclosed affiliation |
| 6 | If fresh-install/first-task checks pass, submit or schedule Product Hunt with clear gallery media and actual release status. Otherwise keep it as a saved draft and fix the blocking workflow. | Submission state, launch time and tested install steps |
| 7 | Publish a short factual changelog: what users tried, what failed, what shipped. Answer unresolved questions. Choose the next improvement from real task failures. | Actual aggregate counts and fixes, with sample/demo sessions excluded |

## Measurement sheet

Virality is an outcome to measure. No reach, install or retention result is claimed in this kit. A useful initial goal is a small set of independent first-task successes, followed by people returning to use the product.

| Metric | Definition | Source | Current result |
| --- | --- | --- | --- |
| Qualified visits | Visits from a known launch channel, excluding internal QA where distinguishable | Hosting analytics if configured, with `utm_source`, `utm_medium` and `utm_campaign`; otherwise mark unavailable | Not measured |
| Install intent | Actual outbound clicks to installation/source | Analytics only if implemented; a static page by itself supplies no central click count | Not measured |
| Install completion | A volunteer reports a working workspace and paired bot | Opt-in, redacted tester record | Not measured |
| First-task activation | An independent user finishes one task with their real chosen model and receives/opens its file | Opt-in result; exclude fixture demos and maintainer tests | Not measured |
| Activation rate | First-task activations divided by observed completed installs in the same cohort | Same opt-in cohort; state its size | Not measured |
| Seven-day return | Activated users who report another real task within seven days, divided by the eligible activated cohort | Opt-in follow-up, not inferred from site visits | Not measured |
| Source interest | Views/clones and stars, reported separately from active use | GitHub owner traffic view where available; public star count | Not measured |
| Friction | First failure grouped by installation, pairing, model, approval or artifact | Redacted user reports | Not measured |

Use campaign `openduet-rc4` and simple source values such as `x`, `linkedin`, `producthunt` and the actual permitted community. Query parameters alone do not implement analytics. Do not collect Telegram message contents or credentials for marketing measurement. Publish aggregate outcomes only when there is a real observation behind them.

## GitHub About settings

The connected integration returned HTTP 403 when updating repository metadata.
The README links are published through the normal source workflow. The owner
can set these About fields in GitHub repository settings:

- Website: https://openduet.gabrielekarra.chatgpt.site
- Description: Open-source AI assistant in your Telegram. Local or API models, finished files, reviewed actions. Self-hosted.
- Suggested topics: `telegram-bot`, `ai-agent`, `self-hosted`, `ollama`, `local-llm`, `mcp`, `macos`, `python`, `automation`, `open-source`.

No social/community post has been published by this kit.

## Repeat the public baseline

The first counter snapshot is in [baseline.json](launch/baseline.json).
Use the normal GitHub CLI setup and a new output name for each observation:

```sh
python scripts/launch_metrics.py --output metrics-next.json
```

The command refuses to overwrite an existing snapshot. Stars and forks are
repository counters; installs, activation and qualified visits remain unknown
until there is separate evidence. The launch page adds no tracking backend.
