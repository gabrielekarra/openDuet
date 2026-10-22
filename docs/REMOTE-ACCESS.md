# Control your own Mac through Telegram

Run the portable OpenDuet process **on the Mac you want to control**. Install
`uv sync --locked --extra mac`, start OpenDuet, pair your private Telegram owner
and enable Mac access in Settings. A cloud deployment's separate browser is a
different computer; it cannot control an unconnected Mac.

In macOS System Settings → Privacy & Security, grant **Accessibility** and
**Screen Recording** to the Python executable or terminal running OpenDuet.
macOS may require restarting that process after changing permissions. Screen
Recording captures the logged-in session; it cannot unlock the login screen.

Examples:

- `/apps` lists permitted installed apps and exact bundle identifiers.
- `/screen` captures the main display as a PNG on demand and sends it privately with `sendPhoto`.
- “Apri Calcolatrice” lets the work model select and open the installed app.
- “Apri Note e prepara una nota con questi punti…” uses fresh accessible
  controls. Typing, clicking and other interactions require the displayed
  exact-action approval. The agent must observe again after each action.

Password managers and keychain applications are excluded. Screen capture needs Screen Recording; control observations and actions need Accessibility. Secure text controls
are excluded from observations. A screenshot is delivered as an attachment;
its pixels are not inserted into text history. Uploaded images reach the chosen
model only when its vision setting is explicitly enabled.

The Mac must remain on, signed in and connected. While access is enabled,
OpenDuet uses `caffeinate -i` to inhibit idle sleep; closing the service releases
it. Closing the laptop lid or manually sleeping/shutting down the Mac can still
stop remote commands. Telegram long polling needs no public port or inbound
connection. Disable Mac access or disconnect the bot to revoke access.

There is no live screen sharing, VNC, noVNC, external screen server, background
screen recorder or automatic capture when an app changes. macOS permissions and
application-specific accessible controls must be checked on the target Mac;
Linux fixtures cannot establish those hardware results.
