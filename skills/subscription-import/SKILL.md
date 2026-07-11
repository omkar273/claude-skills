---
name: subscription-import
description: >
  Bulk-import subscriptions into FlexPrice from a CSV file. Use this skill whenever
  the user wants to: create subscriptions from a spreadsheet or CSV, bulk-onboard
  customers into FlexPrice, import contract data as subscriptions, or run a
  subscription import/migration. Trigger on: 'import subscriptions', 'create
  subscriptions from CSV', 'bulk subscription', 'onboard customers',
  'subscription import', or any time the user uploads a CSV with customer IDs,
  plan IDs, and pricing data and wants them turned into active FlexPrice
  subscriptions. Also trigger when the user wants to re-import or re-run a
  previous import, fix duplicate subscriptions, or cancel-and-recreate existing ones.
---

# FlexPrice Subscription Import

Bulk-create FlexPrice customers and subscriptions from a CSV file.
The script is idempotent — it always does a **live subscription check** before
creating, so it is safe to re-run. Supports FLAT_FEE and TIERED billing models,
credit grants, and commitment blocks.

---

## 0 — Before You Start

Always clarify these before writing any code:

1. **Region / base URL** — Which FlexPrice environment? Ask for the base URL and API key.
   - Cloud (default): `https://api.cloud.flexprice.io/v1`
   - US region: `https://us.api.flexprice.io/v1`
   - Self-hosted: user will provide their own URL
2. **Billing model** — `FLAT_FEE` (single `amount` per customer row) or `TIERED`
   (multiple rows per customer, one per tier)?
3. **Optional columns** — Confirm which fields are present:
   `end_date`, `credit_grants.*`, `commitment_amount`, `commitment_duration`, `overage_factor`.
4. **End-date skip logic** — Should rows where `end_date` is before today be skipped entirely?
   (Default: yes.)
5. **Dry run first** — Always run in dry-run mode and show the user all payloads
   before touching the API. Get explicit approval before the live run.

---

## 1 — Expected CSV Format

### FLAT_FEE (one row per customer)

| Column | Example | Notes |
|--------|---------|-------|
| `external_customer_id` | `cust_abc123` | Unique per customer |
| `customer_name` | `Acme Corp` | Used as FlexPrice customer name |
| `plan_id` | `plan_01KG4E...` | Target plan ID |
| `currency` | `usd` | Lowercase ISO code |
| `billing_period` | `MONTHLY` | `MONTHLY`, `ANNUAL`, etc. |
| `billing_cycle` | `calendar` | `calendar` or `anniversary` |
| `start_date` | `2025-09-25T00:00:00.000Z` | ISO 8601 UTC |
| `end_date` | `2026-09-25T00:00:00.000Z` | ISO 8601 UTC — skip row if before today |
| `override_line_items.price_id` | `price_01KG4J...` | Price to override |
| `override_line_items.billing_model` | `FLAT_FEE` | |
| `override_line_items.amount` | `0.00000075` | Float |
| `credit_grants.credits` | `5000.00` | Omit credit_grants block entirely if 0 or empty |
| `credit_grants.cadence` | `ONETIME` | Required when credits > 0 |
| `credit_grants.expiration_type` | `NEVER` | Required when credits > 0 |
| `commitment_amount` | `60000.00` | Include only when all 3 commitment fields set AND overage_factor > 1 |
| `commitment_duration` | `ANNUAL` | Part of commitment block |
| `overage_factor` | `1.5` | Must be > 1 for commitment block to be included |

### TIERED (multi-row per customer)

Each tier is its own row. Rows sharing the same `external_customer_id` are
grouped into one subscription.

| Column | Example | Notes |
|--------|---------|-------|
| `override_line_items.billing_model` | `TIERED` | |
| `override_line_items.tier_mode` | `SLAB` | `SLAB` or `VOLUME` |
| `override_line_items.tiers.upto` | `1000000` or `null` | String `"null"` becomes JSON null for last tier |
| `override_line_items.tiers.unit_amount` | `0` | Sent as **string** in payload |
| `override_line_items.tiers.flat_amount` | `20000` | Sent as **string** in payload |

---

## 2 — Subscription Payload Structure

### FLAT_FEE payload

```json
{
  "external_customer_id": "<from CSV>",
  "plan_id":              "<from CSV>",
  "currency":             "<from CSV>",
  "billing_period":       "<from CSV>",
  "billing_period_count": 1,
  "billing_cycle":        "<from CSV>",
  "start_date":           "<from CSV>",
  "end_date":             "<from CSV>",
  "override_line_items": [
    {
      "price_id": "<from CSV>",
      "amount":   0.00000075
    }
  ],
  "credit_grants": [
    {
      "scope":           "SUBSCRIPTION",
      "name":            "Usage Bank",
      "cadence":         "ONETIME",
      "credits":         5000.00,
      "expiration_type": "NEVER"
    }
  ],
  "commitment_amount":   60000.0,
  "commitment_duration": "ANNUAL",
  "overage_factor":      1.5
}
```

### TIERED payload

```json
{
  "external_customer_id": "<from CSV>",
  "plan_id":              "<from CSV>",
  "currency":             "<from CSV>",
  "billing_period":       "<from CSV>",
  "billing_period_count": 1,
  "billing_cycle":        "<from CSV>",
  "start_date":           "<from CSV>",
  "override_line_items": [
    {
      "price_id":      "<from CSV>",
      "billing_model": "TIERED",
      "tier_mode":     "SLAB",
      "tiers": [
        { "unit_amount": "0", "flat_amount": "20000", "up_to": 1000000 },
        { "unit_amount": "0", "flat_amount": "40000", "up_to": 3000000 },
        { "unit_amount": "0", "flat_amount": "0",     "up_to": null }
      ]
    }
  ]
}
```

**Always hardcode `billing_period_count: 1`.
Do NOT pass `enable_true_up` or `proration_behavior` — the API applies its own defaults.**

---

## 3 — Field Rules and Transformations

### Credit grants
- Include `credit_grants` **only if** `credits > 0` AND `cadence` is non-empty.
- `scope` is always `"SUBSCRIPTION"` and `name` is always `"Usage Bank"`.

### Commitment block
Include `commitment_amount`, `commitment_duration`, and `overage_factor` together
**only when all three conditions hold simultaneously**:
1. `commitment_amount` is non-empty and > 0
2. `commitment_duration` is non-empty
3. `overage_factor` is non-empty and **strictly > 1**

Strip commas when parsing: `"60,000.00"` → `60000.0`.

### end_date
Skip the entire customer row if `end_date < today`.

---

## 4 — Execution Sequence

### Phase 1 — Dry run (mandatory)

```python
DRY_RUN = True  # flip to False only after user confirms payloads

if DRY_RUN:
    for c in customers:
        print(json.dumps(build_payload(c), indent=2))
    print(f"\nDRY RUN complete — {len(customers)} payloads shown above.")
    return
```

### Phase 2 — Live import (sequential)

```
For each customer in the CSV (after end-date filter):

  Step 1 — Live subscription check (never skip)
    GET /subscriptions?external_customer_id=...&plan_id=...&subscription_status=active
    → items found  → log skipped_active_sub, move to next customer
    → no items     → continue to Step 2

  Step 2 — Create / upsert customer
    POST /customers { external_id, name }
    → 409 / "already exists" → non-fatal, continue

  Step 3 — Create subscription
    POST /subscriptions (full payload)
    → save result to file immediately after each customer
```

---

## 5 — Implementation

Use `urllib.request` directly. Always include `/v1` in the base URL.

```python
import urllib.request, urllib.error, urllib.parse, json

API_KEY  = "<API_KEY>"
BASE_URL = "https://api.cloud.flexprice.io/v1"

HEADERS = {"Content-Type": "application/json", "x-api-key": API_KEY}

def api_get(path, params=None):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def api_post(path, payload):
    url  = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()}") from e
```

Extract subscription ID defensively:
```python
sub_id = (sub_resp.get("data") or {}).get("id") or sub_resp.get("id", "?")
```

### Batch execution (for large imports)

The bash sandbox times out at ~45 seconds. For large lists, run in batches of 7–8:

```bash
python3 import.py 1 8    # batch 1
python3 import.py 9 16   # batch 2
```

### Save results incrementally

Write the results file after **every** customer — not at the end of the loop.

---

## 6 — Critical Learnings

1. **The inline subscription check is non-negotiable.** Always check before creating.
2. **Credit grants and commitment blocks are independent** — never condition one on the other.
3. **Commitment requires overage_factor strictly > 1.** Missing or ≤ 1 → omit entire block.
4. **Results file can lag behind reality.** A timed-out bash call may not have committed the subscription server-side. Always verify with a live GET.
