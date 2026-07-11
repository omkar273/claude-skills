---
name: invoice-validation
description: >
  Validate FlexPrice invoice subtotals by cross-checking them against three sources: the
  finalized invoice (search API), a fresh preview recalculation, and usage analytics.
  Produces two CSVs: an invoice-level sheet with all three totals and diffs, and a
  line-item sheet to pinpoint discrepancies. Use whenever the user wants to validate,
  audit, or reconcile invoice amounts — phrases like "validate invoices", "invoice sanity
  check", "check invoice totals", "billing discrepancies", "invoice vs analytics",
  "invoice vs preview", "reconcile invoices", or any request to cross-check what was
  charged against usage data or a fresh recalculation.
---

# Invoice Validation

Validates FlexPrice invoice subtotals by calling three APIs for each invoice and comparing the results.

## What you need from the user

Before starting, confirm you have:

1. **Input CSV** — a file with at minimum these columns:
   - `id` — invoice ID (format: `inv_*`)
   - `subscription_id` — subscription ID (format: `subs_*`)
   - `external_id` — the customer's external ID
   - `period_start` — billing period start (ISO 8601 or `YYYY-MM-DD HH:MM:SS+00`)
   - `period_end` — billing period end
   - `subtotal` — the recorded invoice amount

2. **API key** — the `x-api-key` value

3. **Base URL** — Which FlexPrice environment?
   - Cloud (default): `https://api.cloud.flexprice.io/v1`
   - US: `https://us.api.flexprice.io/v1`
   - Self-hosted: user will provide

## The three sources compared

| Source | API | What it represents |
|---|---|---|
| **Actual** | `POST /v1/invoices/search` | The finalized invoice as stored in FlexPrice |
| **Preview** | `POST /v1/invoices/internal/preview` | A fresh recalculation from the subscription + pricing rules |
| **Analytics** | `POST /v1/events/analytics` | Raw usage events aggregated into cost — usage charges only |

> **Important:** Analytics only covers usage-based charges. It will legitimately be lower than
> the invoice subtotal for customers with flat fees, minimum commitments, or prepaid credits.
> The most meaningful comparison for catching billing bugs is **subtotal vs preview**.

## Output files

### 1. `invoices_validated.csv`
One row per invoice. Same columns as input, plus:

| Column | Description |
|---|---|
| `analytics_total` | Total cost from analytics API |
| `preview_invoice_total` | Subtotal from preview API |
| `diff_subtotal_vs_analytics` | `subtotal - analytics_total` |
| `diff_subtotal_vs_preview` | `subtotal - preview_invoice_total` |
| `diff_analytics_vs_preview` | `analytics_total - preview_invoice_total` |
| `analytics_error` | API error message if analytics call failed |
| `preview_error` | API error message if preview call failed |
| `actual_search_error` | API error message if invoice search failed |

### 2. `invoice_line_items.csv`
One row per line item across all three sources. Key for diagnosing which line item causes a discrepancy.

Columns: `invoice_id`, `subscription_id`, `external_id`, `period_start`, `period_end`,
`source` (actual / preview / analytics), `display_name`, `price_type`, `meter_id`,
`amount`, `quantity`, `price_unit_amount`, `currency`

## How to run

Write a Python script that:
1. Reads the input CSV
2. For each invoice, calls all three APIs
3. Writes `invoices_validated.csv` and `invoice_line_items.csv` incrementally

Install dependency: `pip install requests --break-system-packages -q`

For large files, support `--start` and `--end` flags to process in chunks:
```bash
python3 validate_invoices.py invoices.csv <api_key> ./output --sources all --start 0 --end 100
python3 validate_invoices.py invoices.csv <api_key> ./output --sources all --start 100 --end 200
```

Support a `--sources` flag: `all` (default), `preview`, or `analytics` — to selectively refresh one source without re-running everything.

## API reference

### Invoice Search
```
POST /v1/invoices/search
Body: { "invoice_ids": ["inv_..."] }
Key response fields: items[0].subtotal, items[0].line_items[]
```

### Invoice Preview
```
POST /v1/invoices/internal/preview
Body: {
  "subscription_id": "subs_...",
  "hide_zero_charges_line_items": true,
  "period_start": "2026-03-01T00:00:00Z",
  "period_end": "2026-04-01T00:00:00Z"
}
Key response fields: subtotal, line_items[]
```

### Analytics
```
POST /v1/events/analytics
Body: {
  "external_customer_id": "...",
  "start_time": "2026-03-01T00:00:00.000Z",   ← NOTE: start_time, NOT period_start
  "end_time":   "2026-04-01T00:00:00.000Z"    ← NOTE: end_time, NOT period_end
}
Key response fields: total_cost, items[].{name, meter_id, total_cost, total_usage}
```

## Interpreting results

After running, summarize:

1. **Error count** — rows with `analytics_error` or `preview_error`
2. **CSV vs Preview mismatches** — rows where `abs(diff_subtotal_vs_preview) > 0.01` (most actionable)
3. **Diff distribution**:
   - Exact match (diff < 0.01) — no issue
   - Rounding (0.01–1.00) — likely float/currency rounding
   - Small diff (1.00–10.00) — worth investigating
   - Large diff (≥ 10.00) — likely a real billing discrepancy
4. **Drill into line items** for top mismatches — filter `invoice_line_items.csv` by `invoice_id` and compare `source = actual` vs `source = preview`
