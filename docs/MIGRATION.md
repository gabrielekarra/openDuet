# Portable runtime migration

The `bobb-mac-final` tag preserves the complete last native application and its
history before removal. The current branch uses Python, Telegram and the web
console. SwiftUI/BobbCore, the MLX generation daemon, continuous screen sensors,
native account readers, licensing, TTS, native packaging and VNC are retired.
The optional on-demand Python Mac bridge is retained.

Existing portable workspace data remains in `data_dir`. Messages, shared memory,
artifacts and internal schedules are retained. Custom schedules are visible in
Settings as check-ins; their scheduler remains active. New model-proposed
schedules require confirmation. Remove old `[computers.*]` VNC configuration
and `remote_session_seconds`; enable Mac access in Settings instead.

Native data formats are not silently imported. Stop the old native app first,
keep its data directory backed up, and export the memories/documents you want
to bring across. Use the console import/export endpoints for portable memory
and conversations. Do not run two agents against the same Mac simultaneously.

Provider keys, Telegram tokens and OAuth credentials entered in the new console
use the encrypted vault. Old license/signing artifacts have no function in the
new runtime. Removal from the working tree does not erase Git history; this
migration does not establish whether any historical key was ever used outside
development. Rotate any independently deployed secret through its provider.

Kev's inference source, pinned manifests, typed schema, learning and specialist
logic live in `openduet/kev/`. Its relevant design notes and historical benchmark
reports are preserved under `docs/kev/`; historical native paths are context,
not current run instructions. The separate `specialist/` research package is
retained and is not imported by the production runtime.
