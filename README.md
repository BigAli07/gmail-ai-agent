# Gmail AI Agent

A safety-first Python 3.12 agent that classifies unread Gmail inbox messages, creates review-only
reply drafts, sends a single important-email digest, and uses SQLite plus Gmail labels to prevent
duplicates. It never sends draft replies.

## Safety boundary

The source inbox is configured only through:

```dotenv
GMAIL_ACCOUNT_EMAIL=YOUR_SOURCE_GMAIL_ADDRESS
DIGEST_RECIPIENT_EMAIL=YOUR_DIGEST_RECIPIENT_EMAIL
```

After OAuth, the program calls Google's OpenID Connect `userinfo` endpoint and requires the
authenticated email to exactly match `GMAIL_ACCOUNT_EMAIL` (case-normalized). It performs this
check **before constructing the Gmail API client or reading/creating labels, messages, drafts, or
digests**. A mismatch exits with code 3 and a clear error.

This project never asks for, accepts, or stores a Gmail password. OAuth client configuration and
refresh tokens must remain outside version control.

## Architecture

`auth.py` owns OAuth and the identity gate; `gmail.py` is the only Gmail API adapter; `parser.py`
handles MIME; `classifier.py` applies precedence-ordered deterministic rules before an optional
structured OpenAI fallback; `drafts.py` creates threaded review-only replies; `digest.py` renders
escaped text and HTML; `state.py` supplies SQLite idempotency; `agent.py` coordinates safe state
transitions; and `cli.py` supplies locking and the command line.

Important messages are not marked read or processed until their digest is successfully sent. A
failed digest is retried. Durable message and draft IDs prevent duplicate delivery and drafts.
Low-priority messages are labeled and marked read after classification. In `DRY_RUN=true`, all
Gmail and local processing mutations are suppressed.

## Google Cloud and OAuth setup

1. Create a Google Cloud project and enable **Gmail API**.
2. Configure the OAuth consent screen. For a personal project, add the intended source Gmail
   address as a test user.
3. Create an **OAuth client ID → Desktop app** and download it as `credentials.json`.
4. Copy `.env.example` to `.env`, set the full source address in `GMAIL_ACCOUNT_EMAIL`, and leave
   `DRY_RUN=true`.
5. Install and authorize:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
gmail-ai-agent auth
```

The browser login is Google's OAuth page—not this application. Select the exact account configured
in `GMAIL_ACCOUNT_EMAIL`. The generated `token.json` contains sensitive refresh credentials and is
gitignored.

Required scopes:

- `gmail.modify`: list/read messages and apply labels/read state.
- `gmail.compose`: create drafts and send the digest.
- `openid` and `userinfo.email`: retrieve and verify the authenticated account identity.

These are the minimum practical scopes for the requested behavior. The agent does not request
full-mail access. If the OAuth app remains in Google's testing mode, test-user restrictions and
refresh-token expiration can interrupt long-running automation; production publishing or periodic
reauthorization may be necessary.

## Configuration

All settings are environment variables. Important values are documented in `.env.example`.
`OPENAI_API_KEY` is optional: obvious rules still work, while ambiguous mail safely becomes
low-priority when no key is present. Set a supported structured-output model in `OPENAI_MODEL`.
The confidence threshold defaults to `0.75`. To avoid scanning an old unread backlog, the agent
only queries unread inbox messages newer than `GMAIL_LOOKBACK_DAYS` (default `2`) and processes at
most `MAX_MESSAGES_PER_RUN` (default `200`) each run. Gmail returns the newest matching messages
first; older unread messages outside the lookback window are ignored.

## Run safely

Required first test:

```powershell
$env:DRY_RUN="true"; gmail-ai-agent run-once
```

Review the structured log previews. Dry run reads messages only; it does not create labels or
drafts, send a digest, mark messages read, or write processing state.

After reviewing results, enable writes and process once:

```powershell
$env:DRY_RUN="false"; gmail-ai-agent run-once
```

Drafts appear in Gmail's Drafts folder and always include `[REVIEW REQUIRED]` when personal input is
needed. Review and send them manually.

## Hourly scheduling

Cron (at minute 0):

```cron
0 * * * * cd /opt/gmail-ai-agent && /opt/gmail-ai-agent/.venv/bin/gmail-ai-agent run-once
```

Windows Task Scheduler:

```powershell
$agentLauncher = (Resolve-Path .\run-agent.cmd).Path
schtasks.exe /Create /SC HOURLY /MO 1 /ST 06:00 /ET 23:59 /TN "Gmail AI Agent" /TR "`"$agentLauncher`"" /F
schtasks.exe /Create /SC HOURLY /MO 1 /ST 00:00 /ET 01:00 /TN "Gmail AI Agent Late" /TR "`"$agentLauncher`"" /F
```

`run-agent.cmd` changes to the project directory before starting Python, ensuring relative paths
for `.env`, OAuth credentials, the token, lock, and SQLite database resolve correctly. The two
coordinated tasks run hourly from 6:00 AM through 1:00 AM the following night. They do not wake the
computer after the 1:00 AM run until 6:00 AM, and the lock prevents overlapping agent runs.

Docker (run hourly from the host scheduler; persist token and database):

```bash
docker build -t gmail-ai-agent .
docker run --rm --env-file .env \
  -v "$PWD/credentials.json:/app/credentials.json:ro" \
  -v "$PWD/token.json:/app/token.json" \
  -v "$PWD/data:/app/data" gmail-ai-agent run-once
```

Set `DATABASE_PATH=/app/data/gmail_agent.sqlite3` in the container environment. An exclusive
file lock makes an overlapping invocation exit cleanly.

## Rules and customization

Edit the ordered patterns in `src/gmail_agent/classifier.py`. SJSU, internships, and hackathons
are always important. Scholarships are important only when the same message is related to SJSU;
other scholarships are low priority. Messages conservatively identified as coming from an
individual person are important, while no-reply, automated, mailing-list, newsletter, and obvious
company senders do not qualify as human. Email bodies are passed as explicitly untrusted input and
cannot alter rules, recipients, secrets, or tool behavior. Attachment contents are not downloaded;
only safe filenames contribute to classification.

Coding and programming competitions are also always important. Recognized examples include
Codeforces, LeetCode contests, ICPC, AtCoder, CodeChef, HackerRank, Topcoder, Kaggle competitions,
Advent of Code, Meta Hacker Cup, and general coding, programming, developer, software, algorithm,
datathon, ideathon, capture-the-flag, or hackathon events. This content rule overrides sender type:
invitations from companies, marketing systems, mailing lists, and no-reply addresses are included
when the sender, subject, body, HTML, or attachment filename matches a competition or hackathon.

Apex Focus Group messages are explicitly low priority. This sender-specific exclusion runs before
all important-content rules.

## Testing

Tests use mocks and synthetic MIME data; they never access Gmail:

```powershell
ruff format --check .
ruff check .
mypy src
pytest --cov=gmail_agent
```

## Troubleshooting and privacy

- **OAuth mismatch:** remove `token.json`, confirm `GMAIL_ACCOUNT_EMAIL`, rerun `auth`, and select
  the intended Google account. No mailbox operation occurs on mismatch.
- **Refresh failure:** revoke the app token in Google Account security, delete `token.json`, and
  authorize again.
- **No digest:** an empty important set intentionally sends nothing; inspect structured logs.
- **Important message stays unread:** digest delivery failed; the next run safely retries it.
- Keep `.env`, `credentials.json`, `token.json`, the SQLite database, logs, and message previews
  private. Never commit them. Logs use IDs and decisions rather than full message bodies.

Limitations: rule-based summaries are extractive and brief; attachment bodies are not inspected;
Gmail sends the digest from the authenticated source account; scheduling is delegated to the host;
and real OAuth/Gmail integration requires the documented manual authorization.
