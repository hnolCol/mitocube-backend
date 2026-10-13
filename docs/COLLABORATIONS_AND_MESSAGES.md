# Collaboration Requests, Submission Explore & Message System

This document summarizes the backend features added in PR #105:

- **A) Collaboration requests** — users without access can request collaboration on a discovered submission; the request is approved by the submission owner and, optionally, by the requesting user's PI.
- **B) Submission explore** — a discovery endpoint that returns only the minimal metadata needed to find a submission and request collaboration.
- **C) Message system** — conversations between users, optionally linked to a submission ("chat with owner"), or standalone.

---

## A) Collaboration Requests

### Concept

Any authenticated user (role `STANDARD` or higher) who discovers an interesting submission — typically by title via the explore endpoint — but has no access to it, can create a **collaboration request**. The request is `pending` until it is approved. On approval, the requesting user (or all members of the requested research group) is added as a `COLLABORATES` collaborator of the submission and can naturally view it (in `/api/submissions/q`, in their submission scope, etc.).

### Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/collaborations/requests` | Create a pending collaboration request |
| `GET` | `/api/collaborations/requests` | List own pending requests |
| `GET` | `/api/collaborations/requests/pending` | List requests the current user can approve (owner/PI view; sits next to the consortium share requests) |
| `GET` | `/api/collaborations/requests/submissions/{submission_tag}` | All requests for a submission (owner/head-of-owner/curator only) |
| `POST` | `/api/collaborations/requests/{request_tag}/approve` | Approve a pending request |
| `POST` | `/api/collaborations/requests/{request_tag}/deny` | Deny a pending request |
| `GET` | `/api/collaborations/submissions/explore` | Discovery endpoint (see section B) |

### Request model (`CollaborationRequestInput`)

```jsonc
{
  "submission_tag": "subm-abc",          // required
  "message": "I would like to collaborate on ...",  // optional, free text
  "requested_for_user_tag": "user-xyz",  // optional; defaults to the requesting user
  "requested_for_group_tag": "rg-1"      // optional; group collaboration (see below)
}
```

### Approval rules

- **Who can approve/deny**: the **owner** of the submission, a **head (PI) of one of the owner's research groups**, a **head (PI) of the requesting user's research group**, or a **curator/admin**.
- **Single approval** (default): one approval by the owner side (or curator) grants access.
- **Two-sided approval** (setting enabled): the **owner side** and the **requester's PI** must *both* approve. Each side's approval is recorded (`owner_approved` / `pi_approved`); the request is granted only once both flags are set. A user who is both owner-side and PI of the requester approves both at once.

### Setting: PI approval

In `src/config/settings/general.py`:

```python
require_pi_approval_for_collaboration_requests : bool = False
```

- `False` (default): only the owner side must approve.
- `True`: the head (PI) of the requesting user's research group must approve **in addition** to the owner side.

Configurable via the environment variable `REQUIRE_PI_APPROVAL_FOR_COLLABORATION_REQUESTS=true`.

### Group collaboration

A request can target a whole research group via `requested_for_group_tag`. Guards:

- The requesting user must be a **member** of that group.
- On approval, **all group members** become `COLLABORATES` collaborators of the submission.
- Duplicate pending requests for the same user/group + submission are rejected with `409`.

### Data model (Neo4j)

```
(:User)-[:REQUESTED]->(:CollaborationRequest)-[:FOR_SUBMISSION]->(:Submission)
(:User)-[:COLLABORATES {created_at, via_collaboration_request}]->(:Submission)
```

- `CollaborationRequest` node properties: `tag`, `created_at`, `status` (`pending`/`approved`/`denied`), `requested_by`, `message`, `requested_for_user_tag`, `requested_for_group_tag`, plus approval bookkeeping (`owner_approved`, `pi_approved`, `approved_by`, `approved_at`, ...).
- Uniqueness constraint on `CollaborationRequest.tag`.
- On granting, the scope cache of every added collaborator is invalidated so access is effective immediately.

### Consistency with upfront collaborators

Collaborators defined **upfront** when posting a submission (`POST /api/submissions`, `NewSubmissionModel.collaborators`) and collaborators added later (`POST /api/submissions/{tag}/collaborators`) use the **same** `COLLABORATES` edge as approved collaboration requests. All three paths now consistently set `created_at` on the edge; the request path additionally sets `via_collaboration_request = true`. Access checks (`has_user_access`, scope queries) only look at the edge, so a request-granted user is indistinguishable from an upfront collaborator.

> Note: `set_collaborators(replace=True)` deletes **all** collaborator edges, including request-granted ones. The edge is the single source of truth for access.

---

## B) Submission Explore (Discovery Endpoint)

### `GET /api/collaborations/submissions/explore`

```
GET /api/collaborations/submissions/explore?search_string=mitochondria&limit=40
```

Returns submissions matching a title search **regardless of access** — this is deliberate: the purpose is to find submissions one does *not* yet have access to, in order to request collaboration.

**Deliberately separate from `/api/submissions/q`**: the normal query endpoint is scope-filtered (users only see what they can access). Mixing discovery into `/q` would leak inaccessible submissions into the normal query or require special-casing.

### Response (`SubmissionExploreModel`)

```jsonc
{
  "tag": "subm-abc",
  "title": "Mitochondrial proteostasis in aging mice",
  "state": 4,                            // latest IN_STATE state tag, null if none
  "created_at": 1717689000000.0,
  "owner_tag": "user-xyz",
  "owner_firstname": "Jane",
  "owner_lastname": "Doe",
  "owner_institute": "MPI Biology of Ageing",
  "research_group_tag": "rg-1",
  "research_group_text": "Mitochondrial Proteostasis",
  "research_group_institute": "MPI Biology of Ageing",
  "has_open_collaboration_request": false  // does a pending request by anyone exist?
}
```

Only non-sensitive discovery metadata is returned — never samples, quantifications, condition applications, or metatexts. Guests cannot use the endpoint (all endpoints require authentication).

---

## C) Message System

### Concept

Users can have **conversations** containing **messages**. A conversation may be linked to a submission (`ABOUT_SUBMISSION`) — the backend for a frontend "Chat with owner" button — or exist standalone between users. Only conversation participants can read/post (curators excepted for read access).

### Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/messages/conversations` | Create a conversation |
| `GET` | `/api/messages/conversations` | List own conversations (optional `submission_tag` filter) |
| `GET` | `/api/messages/conversations/{tag}` | Get one conversation |
| `GET` | `/api/messages/conversations/{tag}/messages` | Get messages (marks conversation read) |
| `POST` | `/api/messages/conversations/{tag}/messages` | Post a message |
| `POST` | `/api/messages/conversations/{tag}/read` | Mark conversation as read |
| `GET` | `/api/messages/conversations/{tag}/unread` | Unread message count |
| `GET` | `/api/messages/submissions/{submission_tag}/conversations` | Conversations linked to a submission (requires submission access) |

### Conversation creation (`ConversationInput`)

```jsonc
{
  "user_tags": ["owner-1"],        // required, at least 1; creator must be included
  "submission_tag": "subm-abc",   // optional; links the conversation to a submission
  "title": "Question about dataset", // optional
  "initial_message": "Hello!"     // optional; posted as the first message
}
```

- If `submission_tag` is set, the creating user must have access to that submission.
- All participants must exist; the creator is implicitly a participant.
- Guests cannot create conversations.

### Data model (Neo4j)

```
(:User)-[:PARTICIPATES]->(:Conversation)-[:ABOUT_SUBMISSION]->(:Submission)
(:Message)-[:IN_CONVERSATION]->(:Conversation)
(:User)-[:SENT]->(:Message)
```

- `Message` nodes carry `read_by` (list of user tags) for unread tracking; a sender's own messages are implicitly read.
- Uniqueness constraints on `Conversation.tag` and `Message.tag`.

### Suggested frontend flow ("Chat with owner")

1. User finds a submission via explore (B) but has no access.
2. Option 1: request collaboration (A) via `POST /api/collaborations/requests`.
3. Option 2: open a conversation with the owner via `POST /api/messages/conversations` with `submission_tag` set (requires submission access — so in practice this button is for users who *can* already view the submission, e.g. collaborators or group members, while the collaboration request is the path for users *without* access).

---

## Architecture / Code Layout

| Layer | Collaborations | Messages |
|---|---|---|
| Models | `src/config/models/collaborations.py` | `src/config/models/messages.py` |
| Abstract DB | `src/lib/database/abstract/Collaborations.py` (`CollaborationsABC`) | `src/lib/database/abstract/Messages.py` (`MessagesABC`) |
| Neo4j DB | `src/lib/database/neo4j/Collaborations.py` (`Neo4JCollaborations`) | `src/lib/database/neo4j/Messages.py` (`Neo4JMessages`) |
| Router | `src/routers/collaborations/collaboration.py` | `src/routers/messages/messages.py` |

- Both handlers are wired into `DatabaseABC` (with `NotImplementedError`/`TypeError` checks like all other handlers) and instantiated in `MCNeo4JDatabase` as `db.collaborations` and `db.messages`.
- Routers are registered in `src/app.py` (`collaboration`, `messages` in `router_sources`).
- Uniqueness constraints for the three new node labels (`CollaborationRequest`, `Conversation`, `Message`) are added in `src/lib/database/Neo4JDatabase.py`.
- The general setting lives in `src/config/settings/general.py`.

## Security Summary

- All new endpoints require authentication (`get_user_from_token`).
- Guests (`UserRolesEnum.GUEST`) cannot create collaboration requests or conversations.
- Explore returns **only** non-sensitive metadata; no sample/quantification/metatext data.
- Collaboration requests can only be created for the requesting user (or their own group) — never on behalf of arbitrary users.
- Approve/deny is restricted to the owner side, the requester's PI (when the setting is on), and curators.
- Message conversations are participant-only; curators may read for moderation purposes.
- Scope-cache invalidation runs on every access change so permissions take effect immediately.

## Testing

New unit tests (all passing, 143 total):

- `tests/units/test_collaboration_requests.py` — request creation, duplicate rejection, unknown-submission errors, approval (user & group), denial, double-approve protection, explore model field surface.
- `tests/units/test_messages.py` — conversation creation (with/without submission link, unknown participant), participant checks, message ordering, unread counts and mark-read.

Run with:

```bash
python -m pytest tests -q
```
