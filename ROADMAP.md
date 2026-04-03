# PyTigo Roadmap

## Current official API v3 coverage

Implemented and tested against the documented Tigo REST API v3:
- `GET /users/login`
- `GET /users/logout`
- `GET /users/{id}`
- `GET /systems`
- `GET /systems/view?id=`
- `GET /systems/layout?id=`
- `GET /objects/system?system_id=`
- `GET /objects/types`
- `GET /sources/system?system_id=`
- `GET /data/summary?system_id=`
- `GET /data/aggregate?...`
- `GET /data/combined?...`
- `GET /alerts/system?system_id=`
- `GET /alerts/types`

Also confirmed from the documentation and live behavior:
- `GET /systems/{id}` works as an alternate system view route
- `systems/view` supports documented `include=` values

## Undocumented or under-documented live API behavior to explore

These were observed live or inferred from live behavior, but are not clearly documented as first-class endpoints in the reviewed API PDF.

### 1. `GET /sources/{source_id}`
Observed live behavior:
- returns `402 Payment Required` for the tested source id
- indicates the route likely exists and may be premium-gated

Questions to explore:
- Is this an official but undocumented detail endpoint?
- What payload shape does it return for accounts with required access?
- Does it expose gateway/source detail beyond `sources/system`?

### 2. Response envelope metadata on list endpoints
Observed live behavior:
- list-style responses such as `systems` and `alerts/system` return `_links` and `_meta`

Questions to explore:
- Which endpoints consistently return `_links` / `_meta`?
- Should PyTigo expose list envelope objects directly rather than only item lists?
- Are there undocumented pagination semantics beyond the PDF examples?

### 3. Additional login payload fields
Observed live behavior:
- `users/login` returned a `refresh_token` field in addition to documented auth data

Questions to explore:
- Is `refresh_token` officially supported for later refresh flows?
- Is there an undocumented refresh endpoint?
- Should PyTigo model this only as opaque data until a refresh flow is confirmed?

### 4. Premium-gated or account-tier specific routes/features
Observed live behavior:
- at least one route (`/sources/{id}`) appears to exist but may require premium access

Questions to explore:
- Are there more premium-only endpoints not present in the PDF?
- Which documented endpoints vary by user/account tier?
- How should PyTigo surface premium-gated responses cleanly?

## Non-goals for now

These are not part of the active API-v3-only implementation:
- portal scraping fallbacks
- inferred analytics or health scores
- exporter-specific convenience layers
- undocumented endpoints without confirmed stable semantics
