# Changelog

All notable Zero Hawk changes are recorded here.

## 0.3.0

- **New dashboard**: sidebar navigation (Work / Pipeline / System), light and dark themes, Ctrl/Cmd-K command palette, `G`-then-letter shortcuts, mobile drawer, installable PWA (manifest + service worker).
- **Today** is now a live setup checklist with funnel and stats; new **Usage** (funnel, sends per day, replies, bounces) and **Help** pages.
- **Fix:** Controls, Compliance, Inboxes, WhatsApp, unsubscribe and send routes were never mounted in `app.py`; they are now.
- **Pre-send lint** (merge tags, banned phrases, length, links, unverified recipient, spam words). Drafts that fail cannot be approved.
- **Send policy**: global kill switch on Controls, Mon-Fri office hours (default East Africa Time), jitter helper, enforced inside `send_email`.
- Kenyan **E.164 phone normalisation** helper.
- Dockerfile. 15 new tests (50 total).

## Unreleased — development branch

- Added an implementation plan and a full source-tree audit.
- Added first-party website training with robots.txt checks, bounded page reads, local JSON output and an editable Train screen.
- Added Claude Code CLI and Codex CLI provider adapters, local provider selection and a live connection-test action.
- Added private dashboard token sign-in, loopback Host validation, same-site mutation checks and ignored local token/session files.
- Added tests for training extraction, profile persistence, provider settings, dashboard authentication and evidence-backed signal profiling.
- Added configurable buying-signal detection, company opportunity scoring, and persistent evidence observations.
- The existing main-branch capabilities and gaps remain honestly documented; email and WhatsApp delivery are not yet implemented.


## ZERO HAWK combined dashboard + Autopilot hardening

- Integrated the redesigned Today/Outbox dashboard, navigation, themes, command palette, mobile drawer, PWA shell, lint gate and global send kill switch.
- Added a persistent Autopilot ON/OFF setting with a 15-minute minimum heartbeat, configurable batch size, last-cycle status and restart recovery.
- Kept Autopilot limited to public website profiling and signal capture; it never automatically sends email or WhatsApp messages.
- Added `ZERO_HAWK_*` environment names with fallback support for existing `OPENPROSPECT_*` configuration.
- Updated Docker and CI commands to use the `zero-hawk` entry point.
- Added regression tests for configuration compatibility and persisted Autopilot settings.
