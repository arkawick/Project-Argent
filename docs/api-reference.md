# API Reference

Base URL: `http://localhost:8000`

All REST endpoints (except auth) require a `Bearer` JWT in the `Authorization` header.
Interactive docs with a built-in "Authorize" button: `http://localhost:8000/docs`

---

## Authentication

### POST `/api/auth/login`

Authenticate and receive a JWT. Uses OAuth2 password-flow form encoding.

**Request:**
```
Content-Type: application/x-www-form-urlencoded

username=admin&password=changeme
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Tokens expire after 8 hours (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).

### GET `/api/auth/me`

Returns the authenticated staff user.

```json
{ "username": "admin", "role": "staff" }
```

---

## LiveKit

### GET `/api/livekit/token`

Generate a LiveKit room token for the browser client.

**Query params:**

| Param | Required | Description |
|-------|----------|-------------|
| `room` | Yes | Room name / call ID |
| `identity` | No | Participant identity (default: `"user"`) |

**Response:**
```json
{
  "token": "eyJhbGci...",
  "url": "ws://localhost:7880"
}
```

### POST `/api/livekit/webhook`

LiveKit server webhook — handles `room_started`, `room_finished`, `participant_joined`, `participant_left` events. Not called by clients directly.

---

## Calls

### GET `/api/calls`

List calls with optional filters.

**Query params:** `status`, `agent_type`, `limit` (max 100, default 20), `offset`

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "livekit_room_id": "call-a1b2c3",
      "status": "completed",
      "started_at": "2024-01-15T10:30:00Z",
      "ended_at": "2024-01-15T10:35:12Z",
      "duration_secs": 312,
      "agent_type": "support_agent",
      "sentiment_score": -0.12,
      "outcome": "resolved",
      "transcript": [],
      "summary": null
    }
  ],
  "total": 42,
  "offset": 0,
  "limit": 20
}
```

### POST `/api/calls`

Create a call record manually.

```json
{ "livekit_room_id": "call-xyz", "customer_id": "uuid-or-null" }
```

### GET `/api/calls/{call_id}`

Get a single call with its full transcript.

### PATCH `/api/calls/{call_id}`

Update a call. Setting `status: "completed"` automatically sets `ended_at` and calculates `duration_secs`.

```json
{ "status": "completed", "outcome": "resolved", "summary": "User's refund was approved." }
```

### DELETE `/api/calls/{call_id}`

Soft-delete: sets `status = "deleted"`.

### GET `/api/calls/{call_id}/insights`

Per-turn analytics for a call.

```json
{
  "items": [
    {
      "turn_number": 1,
      "speaker": "user",
      "text": "I haven't received my order",
      "emotion": "frustrated",
      "emotion_conf": 0.87,
      "intent": "support",
      "intent_conf": 0.94,
      "latency_ms": 820,
      "barge_in": false
    }
  ]
}
```

### GET `/api/calls/{call_id}/transcript`

Raw transcript JSON for a call.

```json
{
  "call_id": "uuid",
  "transcript": [
    { "speaker": "agent", "text": "Hello! How can I help you today?", "ts": 0.0 },
    { "speaker": "user", "text": "I'd like to book an appointment.", "ts": 4.2 }
  ]
}
```

---

## Customers

### GET `/api/customers`

List customers. Filter by `tier` (vip/premium/standard) or `tag`. Paginated.

### POST `/api/customers`

Create a customer. Phone and email must be globally unique.

```json
{
  "name": "Sarah Chen",
  "phone": "+14155551234",
  "email": "sarah@example.com",
  "tier": "vip",
  "tags": ["enterprise", "high-value"]
}
```

### GET `/api/customers/{customer_id}`

Full customer profile.

### PATCH `/api/customers/{customer_id}`

Update name, tier, preferences, or tags.

### GET `/api/customers/{customer_id}/calls`

Last 10 calls for this customer. `?limit=N` to adjust.

### GET `/api/customers/{customer_id}/tickets`

All tickets for this customer. Optional `?status=open`.

### GET `/api/customers/{customer_id}/graph`

Neo4j-derived relationship data.

```json
{
  "customer_id": "uuid",
  "topics": ["billing", "refund request", "product upgrade"],
  "frustration_count": 2,
  "is_repeat_complainer": false
}
```

---

## Appointments

### GET `/api/appointments/slots`

Available 30-minute slots on weekdays 9–17 UTC.

**Query params:** `days_ahead` (1–30, default 7)

```json
{
  "slots": [
    { "datetime": "2024-01-16T09:00:00+00:00", "label": "Tuesday Jan 16 at 09:00 AM UTC" },
    { "datetime": "2024-01-16T09:30:00+00:00", "label": "Tuesday Jan 16 at 09:30 AM UTC" }
  ]
}
```

### GET `/api/appointments`

List appointments. Filter by `status`, `customer_id`. Paginated.

### POST `/api/appointments`

```json
{
  "customer_id": "uuid",
  "title": "Product demo",
  "scheduled_at": "2024-01-16T10:00:00Z",
  "duration_mins": 30
}
```

### PATCH `/api/appointments/{appointment_id}`

Reschedule or change status.

```json
{ "status": "confirmed", "scheduled_at": "2024-01-17T14:00:00Z" }
```

### DELETE `/api/appointments/{appointment_id}`

Sets `status = "cancelled"`.

---

## Tickets

### GET `/api/tickets`

List tickets. Filter by `status`, `priority`, `category`. Paginated.

### POST `/api/tickets`

```json
{
  "customer_id": "uuid",
  "title": "Order not delivered",
  "description": "Order #1234 placed 10 days ago, still not arrived.",
  "priority": "high",
  "category": "shipping"
}
```

### GET `/api/tickets/{ticket_id}`

Ticket detail including resolution text.

### PATCH `/api/tickets/{ticket_id}`

Update status or resolution. Setting `status: "resolved"` auto-sets `resolved_at`.

```json
{ "status": "resolved", "resolution": "Replacement shipment dispatched." }
```

---

## Analytics

All analytics endpoints are Redis-cached. Cache TTLs are noted per endpoint.

### GET `/api/analytics/overview`

Eight KPIs. **Cache: 30 s.**

```json
{
  "total_calls": 247,
  "active_calls": 3,
  "avg_duration_secs": 284.5,
  "resolution_rate": 0.821,
  "avg_sentiment": -0.043,
  "total_customers": 512,
  "open_tickets": 14,
  "appointments_today": 6
}
```

### GET `/api/analytics/emotions`

Emotion distribution by day. **Cache: 30 s.**

**Query params:** `period` — `day | week | month | all` (default: `week`)

```json
{
  "period": "week",
  "data": [
    { "date": "2024-01-15 00:00:00+00:00", "emotion": "neutral", "count": 34 },
    { "date": "2024-01-15 00:00:00+00:00", "emotion": "frustrated", "count": 12 }
  ]
}
```

### GET `/api/analytics/intents`

Intent frequency. **Cache: 30 s.** Same `period` param.

```json
{
  "period": "week",
  "data": [
    { "intent": "support", "count": 89 },
    { "intent": "sales", "count": 67 }
  ]
}
```

### GET `/api/analytics/agents`

Per-agent performance stats. **Cache: 30 s.**

```json
{
  "data": [
    {
      "agent_type": "support_agent",
      "calls_handled": 89,
      "avg_sentiment": -0.21,
      "avg_duration_secs": 342.1,
      "resolution_rate": 0.79
    }
  ]
}
```

### GET `/api/analytics/customers`

Customer tier distribution and average lifetime value. **Cache: 60 s.**

```json
{
  "total_customers": 512,
  "avg_lifetime_value": 1847.32,
  "tier_distribution": [
    { "tier": "standard", "count": 390 },
    { "tier": "premium", "count": 98 },
    { "tier": "vip", "count": 24 }
  ]
}
```

### GET `/api/analytics/live`

Lightweight real-time snapshot. **Cache: 5 s.**

```json
{
  "active_calls": 3,
  "avg_latency_ms": 834.2
}
```

---

## WebSocket endpoints

WebSocket endpoints do not require JWT auth (designed for direct browser connections in the demo).

### WS `/ws/calls/{call_id}`

The primary voice call handler. Connect to start the agent session for the given room.

**Events pushed to browser:**

```json
{ "type": "transcript", "speaker": "agent", "text": "Hello! How can I help?", "emotion": null, "intent": null }
{ "type": "transcript", "speaker": "user", "text": "I need help with my order", "emotion": "frustrated", "intent": "support" }
{ "type": "turn_change", "state": "processing" }
{ "type": "agent_route", "agent": "support_agent", "confidence": 0.92 }
{ "type": "barge_in" }
```

**Message from browser to end the call:**
```json
{ "type": "end_call" }
```

### WS `/ws/dashboard`

Broadcasts aggregated live metrics every 2 seconds.

```json
{
  "type": "metrics",
  "active_calls": 3,
  "emotion_counts": [{ "emotion": "neutral", "count": 12 }, { "emotion": "frustrated", "count": 4 }],
  "intent_counts": [{ "intent": "support", "count": 8 }],
  "avg_latency_ms": 812.4
}
```
