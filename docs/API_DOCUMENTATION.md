# HTTP API Documentation

Base URL depends on deployment (local default: `http://127.0.0.1:8000`). All payloads are JSON.

## `GET /`

Returns basic status information.

### Response (`200`)

```json
{
  "status": "ok",
  "message": "Backend is alive"
}
```

## `GET /health`

Returns deployment readiness metadata.

### Response (`200`)

```json
{
  "status": "ok"
}
```

## `POST /chat`

Stateful **only inside the transcript you send**: your client must replay the prior conversation every call.

### Request body

```json
{
  "messages": [
    { "role": "user", "content": "Hiring mid-level backend engineer Python + Postgres" },
    { "role": "assistant", "content": "What level of seniority and stakeholder exposure?" },
    { "role": "user", "content": "4 years IC, interacts with Product weekly" }
  ]
}
```

### Response body (strict)

```json
{
  "reply": "string",
  "recommendations": [
    {
      "name": "string",
      "url": "https://www.shl.com/...",
      "test_type": "K"
    }
  ],
  "end_of_conversation": false
}
```

### Semantics (evaluator-safe)

- `recommendations` is **always** an array (never `null`).
- When the agent is **clarifying**, **comparing without shortlisting**, or **refusing**, `recommendations` must be `[]`.
- When the agent **commits to a shortlist**, `recommendations` must contain **1–10** items.
- Every `url` + `name` must come from the official SHL catalog ingestion pipeline (this implementation enforces that by construction).

### Error behavior

- Malformed JSON / invalid schema → FastAPI `422` validation errors.
- Service not initialized → `503` (should not happen in healthy deployment).
