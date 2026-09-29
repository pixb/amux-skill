# amux — long-tail API reference

Verified against the route registrations in the deployed server's source
(`crates/amux-server/src/api/*`). SKILL.md's core families live there; this
file is the per-route detail for everything else.

Every call: `curl -sk` (self-signed cert) +
`-H "Authorization: Bearer $AMUX_AUTH_TOKEN"`. Only `/health` and `/` skip the
token. If a route 404s, read `GET /api/debug/routes` — the live table wins over
this file.

---

## Email (Mail.app bridge)

```bash
# inbox: params account, count (default 20), days (lookback, default 7)
curl -sk "$AMUX_URL/api/email/inbox?account=<addr>&count=20&days=7"
curl -sk "$AMUX_URL/api/email/message/<msg-id>"
curl -sk "$AMUX_URL/api/email/search?q=..."
curl -sk "$AMUX_URL/api/email/log"                     # send log

# send / reply (reply takes message_id from the inbox response)
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"to":"x@example.com","subject":"Hi","body":"...","from":"<addr>"}' "$AMUX_URL/api/email/send"
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"message_id":"<msg-id>","body":"Thanks!","reply_all":false}' "$AMUX_URL/api/email/reply"

# approval flow (some sends need an operator's approval first)
curl -sk "$AMUX_URL/api/email/approvals"
curl -sk -X POST "$AMUX_URL/api/email/approve/<id>"
curl -sk -X POST "$AMUX_URL/api/email/reject/<id>"
curl -sk "$AMUX_URL/api/email/approval/<id>"           # fate of one approval

# message intel (merged into this router)
curl -sk "$AMUX_URL/api/email/themes"
curl -sk -X POST "$AMUX_URL/api/email/themes/refresh"
curl -sk "$AMUX_URL/api/email/ranked"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"msg_id":"<id>"}' "$AMUX_URL/api/email/annotate"
```

> **Route drift:** `/api/email/sync` and `/api/email/events` do not exist in
> this server's source (searched: no registration anywhere) — an older doc
> lists them; calling them 404s. Calendar events go through `/api/cal-events`
> below.

## Gmail (direct Gmail API, OAuth — separate from Mail.app)

```bash
curl -sk "$AMUX_URL/api/gmail/accounts"        # connected accounts
curl -sk "$AMUX_URL/api/gmail/auth"            # -> open the returned URL to approve
curl -sk -X DELETE "$AMUX_URL/api/gmail/account"
curl -sk "$AMUX_URL/api/gmail/inbox"
curl -sk "$AMUX_URL/api/gmail/labels"
curl -sk "$AMUX_URL/api/gmail/thread/<thread-id>"
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"to":"x@example.com","subject":"Hi","body":"..."}' "$AMUX_URL/api/gmail/send"
```

## Calendar (plain event store, one-way `.ics` out)

```bash
curl -sk "$AMUX_URL/api/cal-events"            # list
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"title":"Standup","start":"2026-09-01T09:00:00Z"}' "$AMUX_URL/api/cal-events"
curl -sk -X PATCH -H 'Content-Type: application/json' \
  -d '{"location":"Room 2"}' "$AMUX_URL/api/cal-events/<evt-id>"
curl -sk -X DELETE "$AMUX_URL/api/cal-events/<evt-id>"
curl -sk "$AMUX_URL/api/calendar.ics"          # read-only feed
```

Only `title` + `start` are required on create; `end`, `location`,
`description`, `rrule`, `all_day` are optional. This store does **not** sync
back from Google — it is a standalone CRUD store plus an export feed.

## Telegram

```bash
curl -sk "$AMUX_URL/api/telegram/status"        # token set, mapping count, last poll, routing counts
curl -sk "$AMUX_URL/api/telegram/mappings"      # chat <-> session links
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"chat_id":123456,"session":"SESSION_NAME"}' "$AMUX_URL/api/telegram/mappings"
curl -sk -X DELETE "$AMUX_URL/api/telegram/mappings/<chat-id>"
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"session":"SESSION_NAME","text":"reply","parse_mode":"HTML"}' "$AMUX_URL/api/telegram/send"
```

- Inbound: the bot long-polls; a chat links itself by sending
  `/link <session-name>`, or you pre-link with `POST /mappings`.
- `@lane_name` at the start of a message routes it to that lane instead of the
  sender's mapped session.
- Outbound `{"session":...}` resolves to whichever chat linked it most
  recently; pass `chat_id` to target explicitly. There is no automatic
  forwarding of everything a session says — sending is always an explicit call.

## Browser automation

```bash
# live backend = YOUR real Chrome (real logins/IP); default profile = parallel work
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"backend":"live","url":"https://example.com"}' "$AMUX_URL/api/browser/start"
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"profile":"default","url":"https://example.com"}' "$AMUX_URL/api/browser/start"

curl -sk -X POST -H 'Content-Type: application/json' -d '{"url":"https://example.com"}' "$AMUX_URL/api/browser/navigate"
curl -sk "$AMUX_URL/api/browser/screenshot"                      # JSON with a path — read it with your file tool
curl -sk -H "X-Amux-Session: $AMUX_SESSION" "$AMUX_URL/api/browser/state"

# grounded click: use a ref + observation_id from /state, and say what you expect
curl -sk -X POST -H 'Content-Type: application/json' -H "X-Amux-Session: $AMUX_SESSION" \
  -d '{"action":"click","ref":"e12","observation_id":"<from /state>","expect":{"url_contains":"/done","timeout_ms":5000}}' \
  "$AMUX_URL/api/browser/action"
curl -sk -X POST -H 'Content-Type: application/json' -H "X-Amux-Session: $AMUX_SESSION" \
  -d '{"action":"input","ref":"e5","observation_id":"<from /state>","text":"hello"}' "$AMUX_URL/api/browser/action"

# fallbacks: coordinates / text / keys / JS
curl -sk -X POST -H 'Content-Type: application/json' -d '{"action":"click","x":640,"y":400}' "$AMUX_URL/api/browser/action"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"action":"type","text":"hello"}' "$AMUX_URL/api/browser/action"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"action":"key","key":"Enter"}' "$AMUX_URL/api/browser/action"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"action":"eval","script":"document.title"}' "$AMUX_URL/api/browser/action"

curl -sk -X POST -H 'Content-Type: application/json' -d '{"task":"Find the latest invoice"}' "$AMUX_URL/api/browser/agent"
curl -sk -H "X-Amux-Session: $AMUX_SESSION" "$AMUX_URL/api/browser/profiles"
curl -sk "$AMUX_URL/api/browser/profile-access?level=worker&name=$AMUX_SESSION"
curl -sk "$AMUX_URL/api/browser/history"
curl -sk -X POST "$AMUX_URL/api/browser/stop"
```

409 `stale_document`/`stale_observation` → observe again. 409
`disabled`/`obscured` → fix the page (or `force:true`). 422 → dispatched but
the `expect` did not hold. Every click reports `observed_effect`.

## CRM / people

```bash
curl -sk "$AMUX_URL/api/crm/contacts"                    # list
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"name":"Name","company":"X","email":"...","notes":"context"}' "$AMUX_URL/api/crm/contacts"
curl -sk "$AMUX_URL/api/crm/contacts/<id>"
curl -sk -X PATCH -H 'Content-Type: application/json' -d '{"email":"..."}' "$AMUX_URL/api/crm/contacts/<id>"
curl -sk -X DELETE "$AMUX_URL/api/crm/contacts/<id>"
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"kind":"note","body":"discussed partnership"}' "$AMUX_URL/api/crm/contacts/<id>/interactions"
curl -sk -X PATCH -H 'Content-Type: application/json' -d '{"body":"..."}' "$AMUX_URL/api/crm/interactions/<iid>"
curl -sk "$AMUX_URL/api/crm/followups"
```

## Journal (entries + media)

```bash
curl -sk "$AMUX_URL/api/journal"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"title":"...","body":"..."}' "$AMUX_URL/api/journal"
curl -sk "$AMUX_URL/api/journal/<JRN-N>"
curl -sk -X PATCH -H 'Content-Type: application/json' -d '{"body":"..."}' "$AMUX_URL/api/journal/<JRN-N>"
curl -sk -X DELETE "$AMUX_URL/api/journal/<JRN-N>"
curl -sk "$AMUX_URL/api/journal/tags"
curl -sk "$AMUX_URL/api/journal/config"
curl -sk -X POST "$AMUX_URL/api/journal/import"

# media is JSON + base64 (NOT multipart) — accepts a data: URL prefix
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"data":"data:image/png;base64,iVBORw0K...","name":"photo.jpg"}' "$AMUX_URL/api/journal/<JRN-N>/media"
curl -sk "$AMUX_URL/api/journal/media/<MEDIA-ID>"        # serve
curl -sk -X DELETE "$AMUX_URL/api/journal/media/<MEDIA-ID>"
```

## Files — two different contracts, both intentional

Pick by shape, not habit:

```bash
# /api/fs — path-contained, MULTIPART upload, accepts any method on its verbs
curl -sk "$AMUX_URL/api/fs/list?path=."
curl -sk -X POST -H 'Content-Type: application/json' -d '{"path":"a/b"}' "$AMUX_URL/api/fs/mkdir"
curl -sk -X POST -F "file=@local.txt" -F "dir=/some/dir" "$AMUX_URL/api/fs/upload"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"path":"..."}' "$AMUX_URL/api/fs/read"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"path":"..."}' "$AMUX_URL/api/fs/open"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"from":"a","to":"b"}' "$AMUX_URL/api/fs/rename"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"path":"..."}' "$AMUX_URL/api/fs/delete"
curl -sk "$AMUX_URL/api/fs/search?q=..."
curl -sk "$AMUX_URL/api/fs/resolve?path=relative/from/output"

# /api/files — rooted at $HOME (AMUX_FILES_ROOT), RAW BODY upload
curl -sk "$AMUX_URL/api/files?path=some/dir"
curl -sk "$AMUX_URL/api/files/download?path=some/file" -o out
curl -sk -X POST --data-binary @local.txt "$AMUX_URL/api/files/upload?path=dir/file"
```

## Org / team

```bash
curl -sk "$AMUX_URL/api/org"                    # GET creates the singleton row
curl -sk -X PATCH -H 'Content-Type: application/json' -d '{"name":"..."}' "$AMUX_URL/api/org"
curl -sk "$AMUX_URL/api/org/members"
curl -sk -X DELETE "$AMUX_URL/api/org/members/<id>"
curl -sk "$AMUX_URL/api/org/invites"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"email":"..."}' "$AMUX_URL/api/org/invites"
curl -sk -X DELETE "$AMUX_URL/api/org/invites/<token>"
curl -sk "$AMUX_URL/api/org/teams"
```

## Groups

```bash
curl -sk "$AMUX_URL/api/groups"                              # list
curl -sk "$AMUX_URL/api/groups/<name>/config"
curl -sk -X PATCH -H 'Content-Type: application/json' \
  -d '{"goal":"...","department":"sales","kpis":["..."]}' "$AMUX_URL/api/groups/<name>/config"
```

Groups are derived live from each session's `CC_TAGS`, never a stored list.
A caller sending `X-Amux-Worker` only sees same-tag sessions; a caller without
the header (the dashboard) sees everything. `/api/tags` is the same list with
every sub-path 404ing on purpose.

## Torrents (aria2c JSON-RPC behind it)

```bash
curl -sk "$AMUX_URL/api/torrents"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"uri":"magnet:..."}' "$AMUX_URL/api/torrents"
curl -sk "$AMUX_URL/api/torrents/config"
curl -sk "$AMUX_URL/api/torrents/<gid>"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"action":"pause"}' "$AMUX_URL/api/torrents/<gid>/<action>"
curl -sk "$AMUX_URL/api/torrents/<gid>/file" -o out
```

If aria2c is not running every route answers 503 **with the exact start
command** — that is the how-to, not an error to route around.

## Graph (mind-map) / Map (locations)

```bash
curl -sk "$AMUX_URL/api/graph/fleet"          # projected live from sessions
curl -sk "$AMUX_URL/api/graph/board"
curl -sk "$AMUX_URL/api/graph/<id>"           # {"nodes":[...],"edges":[...]}
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"path":"/path/to/vault"}' "$AMUX_URL/api/graph/<id>/import-vault"   # REPLACES the graph

curl -sk "$AMUX_URL/api/map"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"pins":[...]}' "$AMUX_URL/api/map"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"lat":0,"lng":0,"label":"..."}' "$AMUX_URL/api/map/pins"
curl -sk "$AMUX_URL/api/map/search?q=coffee+near+me"
```

Two unrelated "map" concepts share the naming: the graph is node/edge, the map
is a file-backed pin map.

## SQL (same SQLite database, read-only unless you say otherwise)

```bash
curl -sk "$AMUX_URL/api/sql/schema"
curl -sk "$AMUX_URL/api/sql/rows?table=board"
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"sql":"SELECT * FROM board LIMIT 5","write":false}' "$AMUX_URL/api/sql"
```

The read/write split is enforced by SQLite itself (the connection is opened
`SQLITE_OPEN_READ_ONLY`), not by inspecting your query text. Prefer the
purpose-built API whenever one exists.

## Dictation / TTS

Both answer an honest 503 when their engine is not configured — audio/text is
never fabricated.

```bash
curl -sk -X POST --data-binary @audio.wav "$AMUX_URL/api/dictate"   # one-shot transcription
curl -sk "$AMUX_URL/api/dictation/history"
curl -sk "$AMUX_URL/api/dictation/history/<id>"
curl -sk -X POST -H 'Content-Type: application/json' -d '{"...":"..."}' "$AMUX_URL/api/dictation/history/<id>/edit"
curl -sk -X DELETE "$AMUX_URL/api/dictation/history/<id>"
curl -sk "$AMUX_URL/api/dictation/dict"       # GET list, POST add
curl -sk "$AMUX_URL/api/dictation/config"

curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"text":"Hello","voice_id":"..."}' "$AMUX_URL/api/tts"    # -> {url,size,engine,voice}
curl -sk "$AMUX_URL/api/tts/voices"
```

## Habits / weekly review / local models

```bash
curl -sk "$AMUX_URL/api/habits"                              # one JSON array; PUT replaces it whole
curl -sk "$AMUX_URL/api/review/week?days=7"
curl -sk "$AMUX_URL/api/review/digest?file=..."
curl -sk "$AMUX_URL/api/ollama/models"                       # [] when ollama is absent — never an error
```

## Connectors (generic OAuth/credential framework)

```bash
curl -sk "$AMUX_URL/api/connectors"                          # every provider + status (values masked)
curl -sk "$AMUX_URL/api/connectors/accounts"
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"key":"<k>","value":"<v>"}' "$AMUX_URL/api/connectors/<id>/credentials"
curl -sk -X POST "$AMUX_URL/api/connectors/<id>/test"
curl -sk "$AMUX_URL/api/connectors/<id>/auth"
```

`GET /api/connectors` also names which env vars each provider needs — read it
before guessing a credential name.

---

## Worker verbs beyond start/stop/send/peek

All under `/api/workers/{id}` unless noted, all needing the Bearer token:

| Verb | Method | What |
|---|---|---|
| `/pause` `/resume` `/wake` `/reset` `/clear` | POST | lifecycle controls |
| `/duplicate` | POST | twin of this worker |
| `/resize` | POST | pane size |
| `/keys` | POST | inject key sequence |
| `/report` | POST | worker reports its own state (harness protocol) |
| `/steer` | GET/POST/DELETE | list / queue / cancel steering messages |
| `/config` | PATCH | worker config |
| `/share` | any | share surface |
| `/instructions` | any | read or set instructions |
| `/memory` | any | read or write worker memory |
| `/git` | POST | checkout |
| `/git/commits` `/git/commit-detail` `/git/diff` | GET | read |
| `/git/dirty` `/git/push` `/git/commit-report` | POST | write |
| `/git/tracked-files` `/git/commit-guard` | any | read/guard |
| `/{id}/dead-letters` | GET | undelivered sends |

`/api/sessions/*` remains a legacy alias of part of this surface.

## Schedule routes and the fields this server refuses

```bash
curl -sk "$AMUX_URL/api/schedules"
curl -sk "$AMUX_URL/api/schedules/runs"        # recent runs
curl -sk "$AMUX_URL/api/schedules/audit"       # audit trail
curl -sk "$AMUX_URL/api/schedules/shell?session=<name>"
curl -sk "$AMUX_URL/api/schedules/<id>/output"
curl -sk -X POST "$AMUX_URL/api/schedules/<id>/run"      # run now
curl -sk -X POST "$AMUX_URL/api/schedules/<id>/skip"     # skip next
curl -sk -X PATCH -H 'Content-Type: application/json' -d '{"enabled":0}' "$AMUX_URL/api/schedules/<id>"
curl -sk -X DELETE "$AMUX_URL/api/schedules/<id>"
```

Creating a schedule with `watch`, `watch_timeout`, `done_pattern`, `done_action`,
`trigger_on`, or `trigger_sessions` returns **400 with `unhonoured`** — those
columns survive from the old Python server but nothing reads them (card
AMUX-2680). The server's own suggested replacement: have the worker report
completion, or disable the schedule from the session itself.

---

## Known route drift (checked in source, not present)

| Route | Status |
|---|---|
| `/api/notes*` | does not exist — notes are `/api/memories` |
| `/api/email/sync`, `/api/email/events` | no registration anywhere in this server |
| schedule `watch` / `done_pattern` / `done_action` / `trigger_on` | stored-columns era; POST with them is refused 400 |

If you find another one, add it here rather than working around it.
