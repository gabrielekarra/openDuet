# OpenDuet on your Mac

[Guida in italiano](QUICKSTART-MAC.it.md). This guide installs release candidate
**0.4.0rc2** from its public, versioned source archive. Git is not required.
Verified wheels, source distributions and checksums are also available as
artifacts of the [distribution workflow](https://github.com/gabrielekarra/openDuet/actions/workflows/release.yml); artifact downloads require GitHub sign-in.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first.
On an Apple-silicon Mac, install OpenDuet and its local Kev backend:

```sh
uv tool install --python 3.12 'openduet[mac,mlx] @ https://github.com/gabrielekarra/openDuet/archive/refs/tags/v0.4.0rc2.tar.gz'
openduet setup --background --open
```

On an Intel Mac, use `openduet[mac,kev]` instead. The work model is your choice. The generated profile uses native Ollama with
`qwen3.5:4b`, a 16,384-token context, 2,048-token responses and temperature 0.2.
Install [Ollama](https://ollama.com/download) and run `ollama pull qwen3.5:4b`,
or choose a different local model, LM Studio or hosted API in Settings.
OpenDuet does not download either work-model or Kev weights without your action.

Setup creates a private installation under
`~/Library/Application Support/OpenDuet`, generates a private workspace token,
and starts a per-user login service. If the Kev extra is installed, its separate
service starts too. The browser opens a two-minute, one-use local sign-in link;
you do not need to paste the workspace token. Neither token nor link is placed
in a service command line. Re-running setup preserves data and credentials.

1. Follow the Telegram page to create a BotFather bot and pair your private account.
2. Open Settings, choose your work model and protocol, save, then press **Test
   connection**. OpenDuet checks an actual harmless tool call. The test uses a few
   model tokens; it does not send messages, modify files or access accounts.
   **Available models** lists the model IDs on compatible servers.
3. Enable Mac access. In macOS Privacy & Security, grant Accessibility and Screen
   Recording to the Python executable running the background service. Permission
   status is shown in Settings. Restart the service after granting permissions.
4. Ask your Telegram bot `/apps`, `/screen`, or “Apri Calcolatrice”. Approve
   interactions when requested. The Mac must stay awake and signed in.
5. For proactive decisions, open Proactivity and explicitly download the pinned
   Kev model. Connect the accounts you want it to read. Without Kev, the bot can
   still complete assignments and produce briefs, but does not interrupt you.

Useful commands:

```sh
openduet open                  # Fresh one-use sign-in, without restarting
openduet doctor                # Readiness and Mac permission report
openduet doctor --check-model  # Also perform a model/tool-call check
openduet service status
openduet service stop
openduet service start
openduet service uninstall     # Removes services, keeps your data
```

Private service logs are in the installation's `logs/` folder. `doctor` never
prints credentials. The local sign-in endpoint accepts only loopback clients
and hosts; remote console access still requires the normal workspace token or
an already authenticated session.

For upgrades, stop the services, select the new release and run its install
command with `uv tool install --force`, then run
`openduet setup --background --open` again to refresh interpreter paths. Back up
the installation before upgrading. The workspace database, vault key, attachments
and artifacts must be backed up together. See [Mac control](REMOTE-ACCESS.md) and
[self-hosting](SELF-HOSTING.md) for permissions, model resources and server deployment.
