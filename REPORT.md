# Zero Hawk QA and Release Audit

> **Historical audit note:** The detailed matrix below records the earlier pre-combination audit. It is retained as project history and is not the release test result for the combined dashboard build. See the current validation summary immediately below.

## Combined build validation (2026-11-26)

- Python compile check: passed (`python -m compileall -q openprospect`).
- Editable package install using the already available build tools: passed (`python -m pip install -e ".[dev]" --no-build-isolation --no-deps`). A normal isolated install could not download build dependencies in this offline runner; fresh-machine install must still be checked on the user's PC.
- Automated tests: **54 passed** (`python -m pytest -q`).
- Dashboard navigation smoke test: all 17 primary sidebar routes returned HTTP 200 after local-token authentication.
- CLI smoke test: `zero-hawk --help` returned the expected command list.
- Autopilot: ON/OFF, saved configuration, 15-minute minimum interval, startup recovery and safe shutdown covered by regression tests.
- Remaining live checks: fresh Windows `run.bat` installation, live OpenStreetMap requests, actual AI provider login, SMTP/IMAP mailbox delivery and reply sync, WhatsApp pairing/send/receive, and Vercel/remote deployment. These require the user's machine, credentials, devices or external services and are not represented as passed.
- Product scope: Autopilot currently profiles saved public websites and records signals only. It does not yet autonomously discover prospects, enrich decision-makers, compose full campaign sequences, classify replies or send outreach.

---

**Audit date:** 2026-11-26  
**Audited ref:** `feat/full-platform-roadmap`  
**Audited commit at start:** `1b17fe57335f212d3f5d4124ed11e50a40fb5fc5`  
**Release verdict:** **BLOCKED — not a complete or production-ready outreach platform**

## Evidence rules and execution boundary

This audit used GitHub repository file retrieval, GitHub Actions run/job metadata and the Ubuntu/Python 3.12 job log. I did **not** have an execution shell attached to a fresh local clone, a browser session against a running dashboard, or access to the user's SMTP/IMAP accounts, WhatsApp device, DNS provider or test inbox. Therefore I do not claim local runtime, live-provider or browser end-to-end tests that were not performed.

GitHub Actions did perform a clean checkout and install on hosted runners. The actual workflow commands are in `.github/workflows/tests.yml`; this is useful CI evidence but is not the same as following the README quick start on the user's Windows machine.

## 1. Feature audit

| Feature / requirement | Status | Evidence / exact command or test | Responsible code |
|---|---|---|---|
| Fresh clone + README quick start on Windows | NOT TESTABLE | CI used `actions/checkout@v4`, then `python -m pip install -e ".[dev,mcp]"`; did not run `git clone` + `run.bat` on a clean user Windows machine. `run.bat` creates venv, installs `.[mcp]`, copies .env, launches dashboard. | `README.md`, `run.bat`, `pyproject.toml` |
| Dependency installation in CI | PASS | GitHub Actions command: `python -m pip install -e ".[dev,mcp]"`; Ubuntu/Python 3.12 log: “Successfully installed … openprospect-0.1.0 … mcp”. All six matrix jobs completed successfully. | `pyproject.toml`, `.github/workflows/tests.yml` |
| Test suite | PASS (CI only) | `python -m pytest -q` → `34 passed, 1 warning in 1.76s` on Ubuntu/Python 3.12. Six OS/Python matrix jobs succeeded. No local rerun performed. | `tests/`, `.github/workflows/tests.yml` |
| Linter | FAIL | No linter step or lint tool configured in `.github/workflows/tests.yml` or `pyproject.toml`. There is no lint command to run. | `.github/workflows/tests.yml`, `pyproject.toml` |
| Dashboard starts with one command | PARTIAL | `run.bat` ends with `openprospect dashboard`; not run on a fresh Windows clone in this audit. | `run.bat`, `openprospect/cli.py` |
| Loopback binding | PARTIAL | Code inspection: `openprospect dashboard` defaults to `127.0.0.1` and rejects a non-loopback `OPENPROSPECT_HOST`. No live socket/port scan was run. | `openprospect/cli.py`, `openprospect/security.py` |
| Private token access | PARTIAL | Code inspection: token link is printed; protected POST without cookie returns 401. Unauthenticated GET returns sign-in HTML with HTTP 200, not an HTTP rejection. No live HTTP test run. | `openprospect/security.py` |
| A. Train ARTCRAFT website + editable persisted config | PARTIAL | No live command run: `openprospect train https://artcraftstudio.vercel.app`. Heuristic extraction and save/edit code exists; persistence is file-based JSON. Restart persistence not exercised. | `openprospect/training.py`, `openprospect/training_routes.py` |
| A. LLM provider connection tests | NOT TESTABLE | No Ollama, Claude CLI, Codex CLI or API credentials were available. UI invokes a real provider test function; no provider response observed. | `openprospect/ai.py`, `openprospect/app.py` |
| B. Nairobi restaurant OSM discovery | NOT TESTABLE | No live command/request run. The discovery implementation calls Nominatim and Overpass and returns up to requested limit; no result count or sample rows observed. | `openprospect/discovery.py`, `openprospect/app.py` |
| B. Domain/phone dedupe | PARTIAL | Code inspection: discovery and CSV import call `find_company_duplicate(website, phone)`; no real Nairobi dataset was run and no duplicate before/after count observed. | `openprospect/db.py`, `openprospect/app.py` |
| B. robots.txt + rate limiting | PARTIAL | Website profiling/training checks robots.txt and fails closed on most fetch errors; OSM geocode/query calls have a process-local one-second delay. Not tested against a live robots policy or measured request log. | `openprospect/training.py`, `openprospect/discovery.py` |
| C. Profile 10 real companies and prove zero LLM calls | NOT TESTABLE | No ten-company dataset was run. Profiling code is deterministic and does not call `ask_ai`, but no runtime call-count instrumentation was collected. | `openprospect/profiling.py`, `openprospect/automation.py` |
| D. Enrich 10 companies with source URLs + E.164 Kenyan phones | FAIL | No dedicated enrichment pipeline/provider and no Kenyan E.164 normalization implementation found in the inspected discovery/profiling path. OSM strings are stored as found; no ten-company output or normalized phone proof. | `openprospect/discovery.py`, `openprospect/profiling.py`, `openprospect/db.py` |
| E. Email verification classifications | PARTIAL | Verification code performs syntax, disposable-domain, MX and optional SMTP RCPT/catch-all probes. No live five-case test was run. SMTP port 25 probing is frequently blocked; role accounts are flagged but can still become `verified` if SMTP accepts. | `openprospect/verification.py`, `openprospect/app.py` |
| E. Only deliverable recipients can queue | FAIL | SMTP send gate checks verified + non-catch-all, but draft creation/approval does not enforce deliverability; an unverified recipient can have a draft and can be approved. Actual send is blocked later. | `openprospect/app.py`, `openprospect/platform_routes.py`, `openprospect/messaging.py` |
| F. Three-contact sequences | FAIL | No sequence/step scheduler or sequence state machine exists in the inspected code. Draft creation is a single-message action. | `openprospect/app.py`, `openprospect/db.py` |
| F. Pre-send lint / no model call on invalid drafts | FAIL | No lint pipeline enforcing merge tags, banned phrases, max length, link count and verification before model/send. Training stores banned phrases but draft generation does not apply them. | `openprospect/app.py`, `openprospect/training.py`, `openprospect/ai.py` |
| G. SMTP real delivery, footer and unsubscribe headers | NOT TESTABLE | No test mailbox credentials or receiving inbox. Code constructs SMTP STARTTLS message with text unsubscribe footer, `List-Unsubscribe` and `List-Unsubscribe-Post`; no actual delivery/spam/header inspection observed. | `openprospect/messaging.py`, `openprospect/platform_routes.py` |
| G. Approval gate | PARTIAL | Send route checks draft status is `approved`; no end-to-end send test. | `openprospect/platform_routes.py`, `openprospect/messaging.py` |
| G. Daily limit | PARTIAL | Code counts `email_sent` activity events per day; no boundary test. Counter check and SMTP send are not an atomic reservation, so concurrent sends can exceed the cap. | `openprospect/messaging.py` |
| G. Office hours, jitter, global pause | FAIL | No office-hours scheduler, randomized send delay or global outbound pause for email delivery found. | `openprospect/messaging.py`, `openprospect/automation.py` |
| H. IMAP replies, classification, bounce/OOO and sequence stop | FAIL | IMAP imports unread messages only. It selects mailbox read-only, does not mark messages read, does not classify bounce/OOO/replies, and has no sequence stop state. Only a small opt-out phrase list is checked. | `openprospect/messaging.py`, `openprospect/conversations.py` |
| H. Suppression on opt-out | PARTIAL | Basic phrase match inserts sender into suppression table. No live inbound reply test; no shared cross-channel STOP handling. | `openprospect/messaging.py`, `openprospect/db.py` |
| I. WhatsApp pairing | NOT TESTABLE | No paired phone or test number. Baileys sidecar has pair endpoint, but no real pairing session was established. | `whatsapp-sidecar/server.js`, `openprospect/platform_routes.py` |
| I. WhatsApp send/receive | NOT TESTABLE | No real send/receive. Sidecar can send a text and forward inbound text events; no live device evidence. | `whatsapp-sidecar/server.js`, `openprospect/platform_routes.py` |
| I. WhatsApp session persistence | PARTIAL | Baileys uses multi-file auth state under local auth directory and .gitignore excludes it; restart/reconnect was not tested and files are not encrypted. | `whatsapp-sidecar/server.js`, `.gitignore` |
| I. WhatsApp approval gate | PARTIAL | Dashboard form requires an approval checkbox and sidecar checks `approved === true`; no live send tested. | `openprospect/platform_routes.py`, `whatsapp-sidecar/server.js` |
| I. WhatsApp daily cap, jitter, dedupe, STOP, auto-pause, delivery/read status | FAIL | No implementation found in sidecar send path. | `whatsapp-sidecar/server.js`, `openprospect/platform_routes.py` |
| I. Official WhatsApp Cloud API | NOT TESTABLE / NOT IMPLEMENTED | Connections page labels it disconnected; no Cloud API client, verified webhook or status callback implementation. Requires Meta app, token, phone-number ID and webhook configuration. | `openprospect/platform_routes.py`, `README.md` |
| J. Autonomous three-cycle staged pipeline | FAIL | `run_once` only profiles saved companies and saves signals; CLI runs one cycle. No staged discovery/enrichment/verification/writing/sending sequence or cycle-level activity feed. | `openprospect/automation.py`, `openprospect/cli.py` |
| J. Pause stops active work immediately | PARTIAL | Stop event checked between companies; cannot interrupt an in-flight HTTP profile request. No three-cycle pause test. | `openprospect/automation.py` |
| K. Unified cross-channel thread per contact | FAIL | Conversation key includes channel, so email and WhatsApp for the same phone/email cannot be one cross-channel thread. UI displays only last-message summary. | `openprospect/conversations.py`, `openprospect/platform_routes.py` |
| K. Reply composer, notes, statuses, Needs-you queue | FAIL | Not present in the inspected conversation schema/UI. | `openprospect/conversations.py`, `openprospect/platform_routes.py` |
| L. SPF/DMARC/MX DNS lookups | PARTIAL | DNS resolver implementation exists; no real domain was provided/run. DKIM is explicitly `not_tested`. SPF/DMARC presence is not policy validation. | `openprospect/compliance.py`, `openprospect/platform_routes.py` |
| L. Kenya Data Protection Act checklist | PARTIAL | UI renders an operational privacy checklist and mentions the Act/ODPC; it is not a legal assessment or certification. | `openprospect/compliance.py`, `openprospect/platform_routes.py` |

## 2. Dashboard QA

| Requested screen / capability | Status | Evidence / responsible path |
|---|---|---|
| Today | PARTIAL | Dynamic counts from SQLite in `openprospect/app.py`; not browser-tested. |
| Train | PARTIAL | Form and persisted JSON profile in `openprospect/training_routes.py`; not browser-tested. |
| Outbox | PARTIAL | Draft review/approval/send forms in `openprospect/app.py`; no live SMTP. |
| Inboxes / Conversations | FAIL | One minimal `/inbox` summary; no separate inbox management or full thread view. `openprospect/platform_routes.py`. |
| Signals | PARTIAL | Signals router exists; not browser-tested. `openprospect/signals_routes.py`. |
| Discover | PARTIAL | Form calls OSM; no live search. `openprospect/app.py`, `openprospect/discovery.py`. |
| Companies / Contacts / Campaigns | PARTIAL | CRUD and CSV routes exist; no full UI interaction test. `openprospect/app.py`. |
| Activity | PARTIAL | Reads activity rows from SQLite; not every stage emits the required events. `openprospect/app.py`, `openprospect/db.py`. |
| Usage | FAIL | No Usage screen or usage analytics route in navigation. |
| Controls | PARTIAL | Start/pause/run one profiling cycle only. `openprospect/platform_routes.py`, `openprospect/automation.py`. |
| Settings | PARTIAL | AI provider and suppression controls; no comprehensive settings management. `openprospect/app.py`. |
| Help | FAIL | No Help screen in navigation. |
| Dark/light mode | FAIL | CSS hardcodes dark color palette; no theme toggle. `openprospect/app.py`. |
| Phone-width layout | PARTIAL | Responsive CSS media query exists; not screenshot-tested. `openprospect/app.py`. |
| Command palette / global search / saved filters | FAIL | No implementation found in inspected app. |
| Bulk actions / kanban drag and drop | FAIL | No implementation found in inspected app. |
| CSV import/export | PARTIAL | Company/contact import/export routes exist; malformed CSV behavior and UI flows not exercised. `openprospect/app.py`. |
| Fresh-database onboarding wizard | FAIL | No onboarding wizard. |
| PWA install | FAIL | No manifest/service worker/install flow in repository tree. |
| Loading/empty/error states | PARTIAL | Some empty/error strings exist; not systematically implemented or browser-tested. |
| Console/network errors | NOT TESTABLE | No browser automation or live dashboard session available. |
| Lighthouse scores | NOT TESTABLE | No running deployment/browser session; no Lighthouse report produced. |
| Dark/light/phone screenshots for every screen | NOT TESTABLE | No screenshots were captured. |

## 3. Robustness and security

| Check | Status | Evidence / responsible path |
|---|---|---|
| Kill server mid-send / exactly-once delivery | FAIL | SMTP send occurs before draft status is updated. A crash after SMTP acceptance and before status update can permit duplicate send on retry. No durable idempotency key/outbox transaction. `openprospect/platform_routes.py`, `openprospect/messaging.py`. |
| Malformed CSV / oversized CSV | PARTIAL | 5 MB read cap and UTF-8 decoding; malformed row shape and CSV parser errors are not comprehensively handled. `openprospect/app.py`. |
| Unreachable website | PARTIAL | Network exceptions are surfaced for training/profile paths; not exercised against unreachable hosts. `openprospect/training.py`, `openprospect/profiling.py`. |
| Invalid phone | FAIL | Discovery stores phone text as supplied; no E.164 validation/normalization gate. WhatsApp sidecar strips non-digits and checks length only. `openprospect/discovery.py`, `whatsapp-sidecar/server.js`. |
| Huge page | PARTIAL | Training fetch caps response at 1.5 MB; not tested with oversized/streaming responses. `openprospect/training.py`. |
| SQL injection | PARTIAL | Inspected database paths generally use SQLite parameter binding; no systematic adversarial test run. `openprospect/db.py` and route modules. |
| XSS from scraped content | PARTIAL | Main dashboard uses `html.escape` in rendered values and Train screen uses escaping; no browser payload test. `openprospect/app.py`, `openprospect/training_routes.py`, `openprospect/platform_routes.py`. |
| SSRF / internal IP protection | FAIL | Host is resolved and checked before fetch, but urllib follows redirects before destination validation; DNS can also change between validation and connection. Robots fetch has the same redirect exposure. This is not a robust SSRF boundary. `openprospect/training.py`. |
| Prompt injection from scraped pages/replies | PARTIAL | Website text is passed as data in prompts, but no systematic untrusted-content isolation or adversarial tests. Inbound messages are not used to trigger sends in the current loop. `openprospect/app.py`, `openprospect/ai.py`, `openprospect/training.py`. |
| Secrets excluded from git | PARTIAL | `.gitignore` excludes .env, token, session, PEM/key and WhatsApp auth paths. No exhaustive git-history secret scan was performed. |
| Secrets encrypted at rest | FAIL | SMTP/API credentials are environment variables; local token/session files are not encrypted. WhatsApp Baileys auth state is stored as local files. |
| WhatsApp session restricted permissions | PARTIAL | Auth directory is gitignored, but no explicit directory/file permission hardening or encryption is applied. |
| Real send crash recovery | FAIL | No durable send state machine, SMTP idempotency, reconciliation or exactly-once guarantee. |

### SSRF release blocker detail

`openprospect/training.py` previously used `urllib.request.urlopen`, which automatically followed redirects before checking the final URL. During this audit, that redirect path was changed to a custom handler that validates each redirect target before following it, including robots.txt redirects. A regression test was added for a redirect to `127.0.0.1`. The current CI run is pending, and DNS rebinding between address validation and socket connection remains unresolved. Do not expose website training/profile to untrusted URLs until DNS resolution is pinned to the validated public address and tested.

## 4. Faked, misleading, or incomplete claims

1. README capability table contained literal `\\n` characters in the email/inbox/WhatsApp/automation/compliance rows. **Fixed in this audit.**
2. README previously said “No email or social message is sent” and “no email deliverability verification is implemented yet” while the branch contains SMTP send and verification paths. **Corrected in this audit.**
3. README's previous “not yet implemented” roadmap listed generic IMAP/SMTP and inbox sync as unavailable, despite partial implementations in this branch. **Replaced with specific unimplemented/untested limitations.**
4. Dashboard header says “No auto-send”; accurate for the autonomous loop, but SMTP and WhatsApp can send manually after explicit approval. Clarify that this is “No automatic campaign sending,” not “No sending.”
5. WhatsApp Connections text says Cloud API “not connected until…” but no Cloud API implementation exists. It is not merely awaiting credentials.
6. WhatsApp send is labelled approved, but approval is only a checkbox/boolean. There is no durable review record, recipient verification, suppression enforcement, rate cap, delay, duplicate guard or delivery status.
7. Email status “verified” is a heuristic SMTP RCPT result. It does not prove mailbox ownership or inbox delivery; role addresses are not categorically blocked.
8. DNS “pass” means a record was found, not that SPF/DMARC policy is valid, aligned or deliverable.
9. Conversation UI is described as unified, but channel is part of the conversation key; email and WhatsApp from one person are split.
10. Autonomous loop label can imply a full sales pipeline, but it only profiles saved websites and stores signals.
11. `pass` exception stubs observed during source inspection: `openprospect/security.py` (best-effort chmod), `openprospect/messaging.py` (content parse fallback and IMAP logout cleanup), and `openprospect/profiling.py` (ignore invalid local signal-rules JSON). These are exception-handling fallbacks, not evidence of completed feature logic.
12. Search attempts for `TODO`, `NotImplemented`, `mock`, `fake`, `simulate`, `lorem`, `pass` and `placeholder` via GitHub code search returned no results. GitHub code search indexes the default branch, not necessarily this feature branch; therefore that result is **not** an exhaustive scan. The source-level hits above are the hits actually verified.

## 5. Fixed during audit

| Fix | Commit |
|---|---|
| Reconcile contradictory README claims and enumerate missing/unverified integrations | `8b7aab4cebb56cb770f69c474f4af5c55af06e1d` |
| Repair the literal `\\n` sequence in the README capability table; verified the seven affected rows render as seven separate Markdown rows | `f73aac9c898a7c8fb581326611d03b56dd6424f2` |
| Validate each HTTP redirect target before following it in website and robots.txt fetches | `306f6ee21b28485d9c563e660773cce2213279a6` |
| Add a regression test for redirect-to-loopback rejection (CI run pending) | `c6c71406e2d85146b0e4247d20ed7ed432a43297` |
| Replace misleading “No auto-send” dashboard header with “No automatic campaign sending” while retaining explicit manual-send controls | `25924f43099388206bae99d51c78bf9ccb9a95ae` |
| Correct CLI status output so it no longer claims all outbound sending is disabled | `c1e52efe4c9892a9b07a68d9a6c68c4f515442e4` |

A limited code-level SSRF mitigation was added: redirects to private/loopback destinations are rejected before following. It is not a complete SSRF fix because DNS rebinding is still possible, and its new regression test has not yet passed in CI. The latest CI run for the redirect regression test, [45712416599](https://github.com/linkto254-bot/openprospect/actions/runs/45712416599), was pending when this report was updated; the previous full six-job success was run [45711353671](https://github.com/linkto254-bot/openprospect/actions/runs/45711353671) on the pre-audit branch head. The SSRF, delivery idempotency, WhatsApp safeguards and missing workflow features require implementation and dedicated regression tests before they can be marked fixed.

## 6. Needs my input

These are required only when the corresponding live integration test is scheduled. **Do not paste passwords, API keys, recovery codes or session files into chat or GitHub.** Put secrets only in the local ignored `.env` file or an appropriate secret manager.

- **SMTP/IMAP:** a dedicated test mailbox you control, SMTP/IMAP host and ports, app password or provider credentials entered locally, sender address, and a second test inbox. Confirm permission to send a test message.
- **WhatsApp pairing:** one test WhatsApp number/device you control and a second test recipient number you control. Pairing code must be entered by you on the phone. Do not send the auth directory.
- **Official WhatsApp Cloud API:** Meta developer app, WhatsApp Business Account, phone-number ID, access token stored locally, and public HTTPS webhook URL plus verification token. Not needed to test Baileys mode.
- **DNS:** the exact sending domain and, for DKIM, provider + selector(s). A domain name is safe to share; do not share DNS account credentials.
- **Browser/Lighthouse:** a running local dashboard on your machine or an approved test deployment URL and permission to inspect it.

## 7. Top 10 remaining risks / improvements (ranked)

1. **Critical — SSRF via redirects/DNS rebinding** in website fetch and robots fetch. Disable automatic redirects; validate every hop before connecting; pin safe resolved addresses.
2. **Critical — SMTP duplicate delivery on crash/retry.** Add durable outbox state, unique send IDs, pre-send reservation and reconciliation for uncertain SMTP outcomes.
3. **Critical — missing cross-channel suppression and WhatsApp STOP controls.** Centralize opt-outs across channels and enforce before every send.
4. **High — WhatsApp has no daily cap, jitter, duplicate protection, delivery/read callbacks or auto-pause.**
5. **High — email sequences, reply classification, bounce/OOO handling and sequence stop rules are absent.**
6. **High — no outbound office hours, jitter or global pause; daily cap is race-prone under concurrent sends.**
7. **High — conversation grouping is channel-specific; no full thread, reply composer, notes or Needs-you workflow.**
8. **High — no full staged autonomous pipeline; current loop only profiles existing records.**
9. **High — secrets/session state are not encrypted at rest; no production auth or multi-user model.**
10. **Medium — UI/product gaps and absent lint/accessibility/performance/browser regression pipeline.**

## 8. Final score

**0% of requested end-to-end features fully PASS in this audit.**

This score is deliberately strict. The Python CI suite passes, and several useful partial implementations exist, but no requested real-provider workflow was exercised end to end and multiple requirements are absent or unsafe. CI success is not a substitute for live workflow evidence.

**Release recommendation: DO NOT MERGE OR DEPLOY AS A complete autonomous outreach platform.** Keep the branch/PR open until the critical security and delivery risks are fixed and the user-provided integration tests are run.
