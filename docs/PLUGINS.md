# Agent Skills and declarative plugins

OpenDuet loads `SKILL.md` YAML front matter (`name`, `description`) from the
operator's `skills_dir`, bundled skills and installed plugins. The base prompt
contains descriptions only. The model calls `load_skill` when it needs the body;
Declarative Markdown commands load as on-demand skills; skill text is guidance and cannot authorize an action or reveal credentials.

Bundles accept `plugin.json` or `.claude-plugin/plugin.json`, skills and optional
remote `.mcp.json` entries. Small-business preparation is bundled. Installing a
plugin adds skill and connection-directory suggestions without connecting an
account. The console previews ZIP contents before the owner clicks Install;
uninstall removes the installed files. Executable hooks, script commands, binaries,
symlinks, traversal paths and archive bombs are rejected. Arbitrary plugin code
does not run during installation.

Inspect or install from an operator-controlled local path:

```sh
uv run openduet-plugin ./my-plugin
uv run openduet-plugin ./my-plugin --install
```

For remote Git sources, first approve the exact HTTPS URL and pin a full commit:

```sh
uv run openduet-plugin https://github.com/example/plugin.git \
  --allow-source --revision FULL_40_CHARACTER_COMMIT
# Inspect the additions, then repeat with --install.
```

Git hooks/system configuration and interactive credential prompts are disabled.
A marketplace JSON can be inspected using its HTTPS URL and `--allow-source`;
select `--plugin NAME`. The selected repository needs its own source approval
and pinned revision. Relative marketplace repository paths must be downloaded
and reviewed locally first. A pinned Git marketplace repository also supports `--plugin NAME` for relative entries within that same reviewed repository. This supports the declarative subset of public
Claude plugin layouts; plugins depending on executable Claude hooks are rejected.

Default check-in suggestions must be explicitly confirmed as schedules through
chat or the console. Plugin installation never starts schedules or purchases.
The `suggest_connector` tool can propose a connection/plugin in a shared thread;
the owner chooses whether to connect it. The directory makes no claim to bundle
or verify every plugin in another product's marketplace.
