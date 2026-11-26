# OpenProspect implementation plan

> Independent implementation. Sellbird is used only as a feature reference; no Sellbird code, prompts, or assets are copied. OpenProspect remains AGPL-3.0.

## Initial audit (2026-11-25)

- [x] Read the current README and packaging metadata.
- [x] Read Sellbird's public README and the requested pipeline, approval/sending, and dashboard guides for feature-level comparison only.
- [x] Complete a recursive source-tree and module/test audit before implementation.
- [x] Record baseline test results and identify existing API, CLI, database, frontend, and security boundaries.

### What exists (confirmed from README and packaging)

- FastAPI local dashboard on loopback, CLI entry point, Python 3.11+ package.
- SQLite-backed company/contact/campaign/outbox/activity workflows.
- Free OpenStreetMap Overpass + Nominatim discovery.
- Basic public homepage research and extraction of visible text, email and phone strings.
- Manual contacts, campaign records, CSV company/contact export.
- Ollama and optional Anthropic/OpenAI-compatible AI drafting.
- Approval/reject state for drafts (approval does not send).
- Exact-email suppression list.
- Optional MCP server with search/save/AI tools.
- pytest and GitHub Actions are described in the README; must verify implementation and coverage.
- Existing README explicitly discloses missing enrichment, verification, mailbox sync, reply handling and outbound delivery.

### Confirmed gaps from the requested target

- Product training workflow and editable product/ICP/offer/voice configuration.
- Provider adapters for Claude Code CLI and Codex CLI; provider connection checks and settings UI.
- Configurable buying signals, full multi-page site profiling, scoring and provenance.
- Decision-maker/contact enrichment, E.164 normalization, email-pattern learning and verification classifications.
- Editable Markdown playbooks, per-contact multi-step sequences, WhatsApp copy and deterministic pre-send lint.
- Real Gmail/Microsoft 365/SMTP sending, approval/autopilot controls, throttling, office hours, warmup, unsubscribe headers/endpoints and suppression enforcement.
- IMAP sync, thread matching, bounce/auto-reply/reply classification and unified conversations.
- WhatsApp sidecar pairing/sending/receiving and optional official Cloud API mode.
- Autonomous run loop, scheduler, activity trail, pause controls and usage accounting.
- Full dashboard navigation, analytics, onboarding, search, saved filters, bulk actions, kanban, PWA and CSV import/export.
- Compliance/DNS checks, Docker, changelog, comprehensive tests and end-to-end CI.

## Delivery checklist

### Foundation and security
- [x] Audit every tracked source, test, docs and workflow file.
- [x] Capture CI test results: 21 tests passed on Ubuntu and Windows for Python 3.11, 3.12 and 3.13 (workflow run 45681819890).
- [x] Keep secrets, database files, mailbox credentials and WhatsApp sessions out of Git; harden .gitignore.
- [ ] Add encrypted local secret/session storage and private token dashboard authentication.
- [ ] Preserve loopback-only binding, host validation and CSRF/origin protections.
- [ ] Add migration-safe SQLAlchemy/SQLite data model and backup/export path.
- [ ] Keep all optional integrations explicitly Not connected until credentials and live checks succeed.

### 1. Training
- [ ] `openprospect train <url>` fetches a site and extracts product, buyers, pricing, proof, voice and objections.
- [x] Persist editable local training configuration (unit-tested local JSON save/load and edit).
- [ ] Train screen edits ICP, offer, banned phrases, signature, language and CTA.
- [ ] Pluggable Ollama, Claude Code CLI, Codex CLI and user-supplied OpenAI-compatible providers.
- [ ] Settings provider selection and real Test connection action.

### 2. Discovery
- [ ] Free Overpass/Nominatim discovery by category and city, including Nairobi, Mombasa and Kisumu.
- [x] CSV import and manual company creation (company CSV import tested; contact CSV import implemented but not yet separately tested).
- [x] Dedupe by normalized domain and phone (unit-tested for domain and Kenyan phone formats).
- [ ] Store source URL, company identity, category, address, website, phone, published email and socials.
- [ ] robots.txt compliance, bounded concurrency, caching and per-host rate limits.

### 3. Signals and profiling
- [ ] Fetch homepage, contact and about pages without LLM calls.
- [x] Detect no website, stale site, mobile viewport, missing booking/ordering, SSL, slow response, WhatsApp and hiring-page signals (fixture-tested).
- [x] User-editable built-in weights and custom keyword signals with evidence links (fixture-tested).
- [x] Explainable company score with evidence URL, confidence and persisted observation history (tested).

### 4. Enrichment
- [ ] Extract public decision makers and contacts only from company-owned pages/public listings.
- [ ] Extract email, phone, WhatsApp, tel links, schema.org and contact forms.
- [ ] Normalize Kenyan numbers to E.164 with tests.

### 5. Email verification
- [ ] Syntax, disposable domain, MX and role-account checks.
- [ ] Catch-all detection and optional bounded SMTP RCPT probe where network policy permits.
- [ ] Honest verified/risky/guess/invalid labels.
- [ ] Learn domain email patterns and label generated addresses as guesses.
- [ ] Sending gate accepts deliverable addresses only.

### 6. Writing
- [ ] Generate personalized email sequences from evidence and trained product context.
- [ ] Editable Markdown templates and playbooks/skills folder.
- [ ] Deterministic lint rejects merge tags, banned phrases, overlong copy, excess links and unverified recipients.
- [ ] Generate concise WhatsApp variants.

### 7. Email sending
- [ ] Real Gmail OAuth/app-password, Microsoft 365 and generic SMTP adapters.
- [ ] Approval-first Outbox; explicit Autopilot opt-in.
- [ ] Per-mailbox daily limits, warmup ramp, recipient-local office hours and jitter.
- [ ] Global pause/kill switch.
- [ ] Mandatory sender footer, List-Unsubscribe and List-Unsubscribe-Post headers, unsubscribe endpoint.
- [ ] Persistent suppression list enforced in all channels and stages.
- [ ] Track sent, bounced, replied and unsubscribed outcomes.

### 8. Mailbox sync and replies
- [ ] IMAP sync per mailbox and thread matching.
- [ ] Detect bounce, auto-reply and out-of-office.
- [ ] Classify interested, objection, question, not now, wrong person and stop.
- [ ] Immediately suppress opt-outs and stop sequences on replies.
- [ ] Draft non-opt-out responses into approval Outbox.

### 9. WhatsApp
- [ ] Node/Baileys sidecar with phone-number pairing code (no QR-only workflow).
- [ ] Encrypted persistent session and live connection status.
- [ ] Text send/receive, delivery/read state and unified inbox integration.
- [ ] Official WhatsApp Cloud API mode with template support and honest connection state.
- [ ] Only business-published contact numbers eligible for outreach.
- [ ] Per-message approval by default; low daily cap and gradual ramp.
- [ ] Random 45–180 second delay, variation checks, mandatory STOP line and instant STOP suppression.
- [ ] Failure-spike circuit breaker and visible unofficial-client ban warning.

### 10. Conversations
- [ ] Unified email/WhatsApp inbox grouped by contact.
- [ ] AI reply drafts, notes and deal statuses.
- [ ] Needs-you queue and sequence stop/resume controls.

### 11. Autonomous loop
- [ ] `openprospect run` and dashboard Start/Pause.
- [ ] Budget-aware/throttled stage selection across discovery, profile, enrich, verify, write, send, sync and replies.
- [ ] Every operation recorded in Activity with outcome and provenance.

### 12. Dashboard
- [ ] Today, Your company/Train, Outbox, Inboxes, Conversations, Signals, Discover, Companies, Contacts, Campaigns, Activity, Usage, Controls, Settings and Help.
- [ ] Consistent responsive design, light/dark mode, transitions, loading/empty states.
- [ ] Keyboard shortcuts, Ctrl/Cmd-K command palette and global search.
- [ ] Saved filters, bulk actions and drag/drop pipeline kanban.
- [ ] Funnel, daily sends, reply/bounce rates, campaign performance and deliverability charts.
- [ ] First-run onboarding with live checks.
- [ ] Installable PWA and phone-friendly layout.
- [ ] CSV import/export for all supported records.

### 13. Compliance and deliverability
- [ ] Kenya Data Protection Act 2019/ODPC lawful-basis and opt-out checklist.
- [ ] Real DNS SPF/DKIM/DMARC lookups with pass/fail evidence.
- [ ] Warmup and responsible sending guidance.

### 14. Quality and release
- [ ] Tests for every pipeline stage and security-sensitive behavior.
- [ ] CI workflow on supported Python versions and platforms.
- [ ] Docker option.
- [ ] Clean README with honest 5-minute quick start and accurate capability status.
- [ ] CHANGELOG maintained.
- [ ] Small logical commits on this feature branch; phase PRs only after real tests pass.
- [ ] Real SMTP test to a user-controlled mailbox and real WhatsApp pairing/test only after user supplies credentials and completes pairing.
- [ ] Do not claim end-to-end completion until each applicable item is implemented and tested.


## Audit notes

The recursive tree currently contains only the README, license, packaging/launcher files, one CI workflow, eight Python package modules, and one test module. There is no frontend build system, migrations folder, Docker configuration, changelog, playbook directory, or docs folder in OpenProspect's current tree.

Key implementation risks found during source review:
- Dashboard routes currently have no private-token authentication or CSRF/origin protection.
- Website profiling currently fetches only the homepage and does not enforce robots.txt or robustly constrain redirects/private-network destinations.
- Discovery uses Nominatim and Overpass directly with no explicit pacing/cache/retry policy and dedupes only by name/location at the route layer.
- AI providers are environment-variable based; there is no connection test UI or CLI provider adapter.
- Existing "approved" drafts are only local state and are not sent; README correctly discloses this.
- The database is direct SQLite with ad-hoc table creation, not SQLAlchemy migrations.
- Existing tests cover basic database/dashboard/API/suppression behavior only. No test execution environment is exposed by the GitHub file connector; CI must supply the executable verification.


## Verified implementation progress (2026-11-25)

- GitHub Actions workflow run **45681114435** completed successfully: 6/6 matrix jobs passed (Ubuntu/Windows × Python 3.11/3.12/3.13); each test run reported 18 passed.
- Implemented and tested private dashboard token exchange, HttpOnly/SameSite session cookie, loopback Host rejection, local provider settings, missing CLI reporting, training data parsing/persistence, unsafe URL rejection, domain/phone deduplication and company CSV import.
- Implemented but not yet verified against a real user website: the live `openprospect train <url>` fetch flow.
- Implemented but not yet verified with live provider credentials: Claude Code, Codex, Ollama and OpenAI-compatible connection tests.
- No real SMTP delivery, IMAP reply sync or WhatsApp pairing/sending has been performed. Those capabilities remain unavailable and must not be presented as connected.
- The current dashboard is still the existing server-rendered HTML UI with incremental routes; the full requested dashboard redesign is outstanding.


## Latest verified phase (2026-11-25)

- GitHub Actions workflow run **45681819890** completed successfully: 6/6 matrix jobs passed (Ubuntu/Windows × Python 3.11/3.12/3.13); each test run reported 21 passed.
- Website profiling now reads the homepage and up to two relevant same-site pages, checks robots.txt, and extracts public email/phone strings without an LLM.
- Added deterministic buying signals for HTTPS, mobile viewport declaration, schema markup, WhatsApp links, booking/ordering, contact pages, stale copyright years, slow homepage response and hiring pages.
- Added editable built-in signal weights and custom keyword rules, evidence links, confidence values, an explainable opportunity score and persistent observation history.
- The full requested feature set remains incomplete; see unchecked items above. No live outbound messaging capability has been added.


## Platform implementation additions (2026-11-26)

The following code has now been added on this feature branch. These are implementation notes, not claims of live account connectivity or completed end-to-end validation.

- SMTP STARTTLS sender reads credentials from environment variables, requires an explicit approved draft, a verified non-catch-all recipient and a non-suppressed address; adds List-Unsubscribe headers and a configurable daily cap (default 25, maximum 100).
- Public GET and RFC 8058-style POST unsubscribe handlers add the address to the local suppression list.
- IMAP SSL sync imports unread text messages, records inbound opt-out phrases as suppressions, and writes to the unified inbox store.
- A shared conversation schema and dashboard Inbox page are present for email and WhatsApp events.
- Optional Node 20+ Baileys sidecar supports phone-number pairing-code requests, explicit text sends, connection status and inbound webhook forwarding. This is unofficial WhatsApp Web connectivity; official Cloud API support is not included.
- A local autonomous loop and `openprospect run` command profile saved companies and record buying signals. It intentionally does not autonomously send messages.
- Responsive dark dashboard styling and navigation for Inbox, Controls, Compliance, Connections and WhatsApp have been added.
- DNS checks report SPF, DMARC and MX records; DKIM is explicitly marked not tested without a provider selector. Privacy readiness checklist is operational guidance only.
- Added tests for unified conversation storage, mailbox configuration status, privacy checklist and paused-by-default automation.

### Validation and remaining release gates

- [ ] Confirm latest GitHub Actions run passes on the current branch head (all Python and OS matrix jobs).
- [ ] Test SMTP against a mailbox controlled by the user, including unsubscribe and suppression.
- [ ] Test IMAP with a mailbox controlled by the user and confirm thread/reply behavior.
- [ ] Install the sidecar, pair a user-controlled WhatsApp account and test inbound/outbound messaging.
- [ ] Validate SPF/DKIM/DMARC alignment for the actual sending domain.
- [ ] Finish full reply classification, bounce processing, message status callbacks, campaign stop/resume and safe retry handling.
- [ ] Expand the automation pipeline beyond website profiling, keeping all outbound communication approval-gated.
- [ ] Finish advanced dashboard functions (global search/command palette, analytics charts, saved filters, bulk operations, kanban and PWA).
- [ ] Review the unsubscribe deployment model: dashboard remains loopback-only, while a production public unsubscribe endpoint needs a separately hardened deployment architecture.
- [ ] Do not merge until the test matrix and live integration checks are complete.
