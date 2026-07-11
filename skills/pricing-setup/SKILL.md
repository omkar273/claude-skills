---
name: pricing-setup
description: >
  Set up FlexPrice features, plans, and usage-based pricing by reading any external pricing page URL.
  Use this skill whenever the user wants to: create FlexPrice features from a pricing page, set up a plan
  with usage-based charges from a competitor or partner pricing URL, onboard a new API product into FlexPrice,
  model API pricing (tokens, characters, audio, pages, requests) in FlexPrice, redo or update existing pricing,
  clone a plan, create multiple plans (Starter/Pro/Business), delete and recreate pricing, or says anything like
  "set up pricing for X", "create features and a plan for Y's API", "model Z's pricing in FlexPrice",
  "import pricing from [URL]", "add [product] to FlexPrice", "redo the pricing", "delete and recreate",
  "clone this plan as Pro", or "create a Starter/Pro/Business tier". Always trigger this skill rather
  than improvising the API calls — it encodes hard-won field requirements and API quirks that are easy to miss.
---

# FlexPrice Pricing Setup from a Pricing Page

This skill guides you through reading any SaaS/API pricing page and turning it into FlexPrice features,
plans, and usage-based prices via the REST API.

## What you'll build

- **One metered Feature per model/service** with meter, reporting_unit, and correct aggregation field
- **One or more Plans** (e.g. Starter / Pro / Business)
- **One usage-based Price per feature per plan**, priced at the base unit rate

---

## Step 0 — Gather credentials

Ask the user for (if not already provided):
- **Pricing page URL** (or inline pricing data)
- **FlexPrice API key** — `x-api-key` header
- **FlexPrice base URL** — default: `https://api.cloud.flexprice.io/v1`
- **Plan name(s)** — default: `"API Pricing"`. Multiple plans (Starter/Pro/Business) are supported.
- **Currency** — 3-char ISO lowercase (`inr`, `usd`, `eur`). Infer from pricing page if obvious.

---

## Step 1 — Fetch and parse the pricing page

Fetch with `mcp__workspace__web_fetch`. If the page is client-rendered (returns an empty shell),
switch to `mcp__Claude_in_Chrome__navigate` + `mcp__Claude_in_Chrome__get_page_text`.

Extract every billable model/service:

| Field | Example |
|---|---|
| Display name | "Text to Speech" |
| Price amount | 30 |
| Pricing unit | "per 10K characters" |
| Notes | "rounded up to nearest second" |

For LLM models with **separate input / cached / output** rates → create **3 features per model**
(suffixed `- Input Tokens`, `- Cached Input Tokens`, `- Output Tokens`).

---

## Step 2 — Map pricing units to meter config + price amount

Price at the **base unit level** — no `transform_quantity`. Divide the published rate by the
stated unit quantity to get the per-unit amount. Use `reporting_unit` so the UI shows friendly units.

**`reporting_unit` formula (empirically verified):** `display_value = raw_value / conversion_rate`

The API docs say `reporting_unit_value = raw * conversion_rate` but the system actually **divides**.
`conversion_rate` = number of base units per 1 reporting unit.

**Rule of thumb for reporting_unit:**
- Only use it when the display unit is meaningfully different from the tracking unit AND the numbers look good visually.
- Tokens (raw count) and characters (raw count) display fine as-is — rounding artefacts make fractional display ugly. **Do not set reporting_unit for tokens or characters.**
- Seconds → hours is the main useful case: `3600 seconds → "1 hour"` looks much better than `"3600 seconds"`.

| Published pricing | Agg `field` | `unit_singular` | Price `amount` | `reporting_unit` |
|---|---|---|---|---|
| $X per 1M tokens | `input_tokens` / `output_tokens` / `cached_input_tokens` | `token` | `X / 1_000_000` | **omit** — show raw token count |
| $X per 10K characters | `characters` | `character` | `X / 10_000` | **omit** — show raw character count |
| $X per hour (audio) | `seconds` | `second` | `X / 3_600` | `{unit_singular: "hour", unit_plural: "hours", conversion_rate: 3_600}` ✓ |
| $X per minute (audio/calls) | `seconds` | `second` | `X / 60` | `{unit_singular: "minute", unit_plural: "minutes", conversion_rate: 60}` ✓ |
| $X per page | `pages` | `page` | `X` | omit — page is already natural |
| $X per request / image / message | `requests` / `images` / `messages` | matching | `X` | omit |

Use Python's `Decimal` for exact per-unit price amounts to avoid float drift:
```python
from decimal import Decimal
def per_million(x): return str(Decimal(str(x)) / Decimal("1000000"))
def per_10k(x):     return str(Decimal(str(x)) / Decimal("10000"))
def per_sec(x):     return str(Decimal(str(x)) / Decimal("3600"))
```

---

## Step 3 — Naming conventions

### LLM models — shared event name, different aggregation fields

All token types for a single model share **one event name**. The aggregation field
distinguishes input vs. output vs. cached within that event:

```
event_name  = "{model_slug}"            # e.g. "gpt_4o"
field       = "input_tokens"            # or "output_tokens" / "cached_input_tokens"
lookup_key  = "{model_slug}_input"      # or _output / _cached_input
```

### Other services

| Service type | `event_name` | `lookup_key` |
|---|---|---|
| TTS | `tts_{variant}` | `tts_{variant}` |
| STT | `stt` | `stt` |
| Translation | `{model_slug}` | `{model_slug}` |
| Vision / pages | `{model_slug}` | `{model_slug}` |
| Generic | `{service_slug}` | `{service_slug}` |

`model_slug` = lowercase + underscored (e.g. `gpt_4o`, `claude_3_5_sonnet`).

---

## Step 4 — Write and run the setup script

Use a single Python script. Install `requests` if needed:
`pip install requests -q --break-system-packages`

### Feature creation payload

```python
payload = {
  "name": "<Display Name>",
  "type": "metered",
  "lookup_key": "<lookup_key>",
  "description": "<description with rate>",
  "unit_singular": "<unit>",
  "unit_plural": "<units>",
  "meter": {
    "name": "<Display Name> Meter",
    "event_name": "<event_name>",
    "reset_usage": "BILLING_PERIOD",
    "aggregation": {"type": "SUM", "field": "<aggregation_field>"}
  },
  # Include reporting_unit only when display unit differs from tracking unit:
  "reporting_unit": {
    "unit_singular": "hour",
    "unit_plural": "hours",
    "conversion_rate": 3600
  }
}
```

Extract `meter_id` from the response — required for price creation:
```python
meter_id = result.get("meter_id") or (result.get("meter") or {}).get("id")
```

### Plan creation payload

```python
{"name": "<Plan Name>", "lookup_key": "<plan_key>", "description": "<desc>"}
```

### Price creation payload

```python
{
  "billing_cadence": "RECURRING",
  "billing_model": "FLAT_FEE",
  "billing_period": "MONTHLY",
  "billing_period_count": 1,         # ← REQUIRED — must be ≥ 1 or API returns 400
  "currency": "<usd|inr|eur|...>",   # lowercase ISO
  "entity_id": "<plan_id>",
  "entity_type": "PLAN",
  "invoice_cadence": "ARREAR",
  "price_unit_type": "FIAT",
  "type": "USAGE",
  "amount": "<per_unit_amount>",     # string, exact decimal — e.g. "0.000004"
  "meter_id": "<meter_id>",
  "display_name": "<Display Name>",
  "lookup_key": "<plan_key>_<feature_key>",
  "description": "<rate label>"
}
```

### Cloning a plan (for Starter/Pro/Business tiers)

```python
r = requests.post(f"{BASE_URL}/plans/{source_plan_id}/clone", headers=H,
    json={"name": "Pro", "lookup_key": "pro", "description": "Pro tier"})
# Returns the new plan with all prices already copied
```

### Script skeleton

```python
import requests, time
from decimal import Decimal

API_KEY  = "<key>"
BASE_URL = "https://api.cloud.flexprice.io/v1"
H = {"Content-Type": "application/json", "x-api-key": API_KEY}

def post(path, body):
    r = requests.post(f"{BASE_URL}{path}", headers=H, json=body)
    if r.status_code not in (200, 201): print(f"ERR {r.status_code}: {r.text}"); return None
    return r.json()

# 1. Create features → collect meter_ids
# 2. Create base plan → get plan_id
# 3. Create prices (one per feature, pointing to plan_id + meter_id)
# 4. Clone plan for Pro / Business / etc.
# Add time.sleep(0.2) between calls
```

---

## Step 5 — Cleanup (when redoing from scratch)

If the user asks to delete and redo, order matters — prices first, then plans, then features.

**DELETE quirk: the `/prices` endpoint requires `Content-Type: application/json` with an empty `{}` body.**

```python
def delete(path):
    r = requests.delete(f"{BASE_URL}{path}", headers=H, json={})  # {} body required!
    return r.status_code in (200, 204)

# 1. GET /prices?limit=100 → delete each by ID
# 2. GET /plans?limit=100  → delete each by ID
# 3. GET /features?limit=100 → delete each by ID
```

**Price lookup_keys are globally unique** — always delete prices before plans when cleaning up.

---

## Step 6 — Verify and report

Summary table:

| Feature | Event | Agg field | Tracks | Rate |
|---|---|---|---|---|
| GPT-4o - Input Tokens | gpt_4o | input_tokens | tokens | $2.50/1M |
| Speech to Text | stt | seconds | seconds | $0.006/min |

---

## Common pitfalls

- **`billing_period_count` must be ≥ 1** — omitting it or passing 0 returns a 400.
- **`amount` is a string** — pass `"0.000004"` not `0.000004`.
- **`currency` is lowercase** — `"usd"` not `"USD"`.
- **LLM models → 3 features each** — input, cached input, output. Same `event_name`, different `field`.
- **`meter_id` ≠ `feature_id`** — prices link to the meter. Extract `meter_id` from the feature response.
- **DELETE prices needs `{}`** — `requests.delete(url, headers=H, json={})` — the empty body is required.
- **Price lookup_keys survive plan deletion** — always delete prices before plans when cleaning up.
- **Client-rendered pages** — if `web_fetch` returns a shell, use Chrome tools to get real content.
