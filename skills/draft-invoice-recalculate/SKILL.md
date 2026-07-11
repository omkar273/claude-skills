---
name: draft-invoice-recalculate
description: >
  Recalculate draft FlexPrice invoices in-place by calling the compute endpoint. Use this skill whenever
  the user wants to recalculate, recompute, or refresh draft invoices — whether they paste a list of
  invoice IDs, upload a CSV, or say things like 'run draft recalculations', 'recompute these invoices',
  'refresh invoice totals', 'recalculate draft invoices', or 'compute invoices'. Always trigger this skill
  when invoice IDs (inv_*) are provided alongside any intent to recompute or refresh.
---

# FlexPrice Draft Invoice Recalculate

Recalculates draft FlexPrice invoices in-place by calling the compute endpoint for each invoice ID.
Runs synchronously (`sync=true`) so results are immediate.

## Step 1 — Collect inputs

Ask the user for (if not already provided):

1. **Base URL** — Which FlexPrice environment?
   - Cloud (default): `https://api.cloud.flexprice.io/v1`
   - US: `https://us.api.flexprice.io/v1`
   - Self-hosted: user will provide

2. **API key** — the `x-api-key` value. Never store or log it.

If the user pastes invoice IDs directly in their message (newline or comma-separated), extract them
from the conversation. Otherwise ask them to paste a list or upload a CSV.

## Step 2 — Extract invoice IDs

Accept invoice IDs in any form:
- Pasted inline (newline or comma-separated)
- Uploaded CSV with an `id` column (or single column of IDs)

Strip whitespace and blank lines. IDs always match `inv_*`.

## Step 3 — Run recalculations

```bash
#!/bin/bash
API_KEY="<provided-api-key>"
BASE_URL="<base-url>"

INVOICE_IDS=(
  "inv_..."
  "inv_..."
)

SUCCESS=0
FAIL=0
FAILED_IDS=()

echo "Starting recalculation for ${#INVOICE_IDS[@]} invoices..."

for INV_ID in "${INVOICE_IDS[@]}"; do
  [ -z "$INV_ID" ] && continue

  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    "${BASE_URL}/invoices/${INV_ID}/compute?sync=true" \
    -H "x-api-key: ${API_KEY}" \
    -H "Content-Type: application/json")

  if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
    SUCCESS=$((SUCCESS + 1))
    echo "✓ $INV_ID (HTTP $HTTP_CODE)"
  else
    FAIL=$((FAIL + 1))
    FAILED_IDS+=("$INV_ID")
    echo "✗ $INV_ID (HTTP $HTTP_CODE)"
  fi
done

echo "---"
echo "Done: $SUCCESS succeeded, $FAIL failed"
if [ ${#FAILED_IDS[@]} -gt 0 ]; then
  echo "Failed IDs:"
  for ID in "${FAILED_IDS[@]}"; do echo "  $ID"; done
fi
```

> For large batches (100+ invoices) where you don't need to wait, switch to `sync=false`.

## Step 4 — Report results

After the script completes, tell the user: total processed, how many succeeded vs. failed, and list any failed IDs.

## Edge cases

- **404 Not Found**: Invoice ID doesn't exist, or the API key belongs to a different tenant.
- **403 Forbidden**: API key lacks permission for this operation.
- **422 Unprocessable**: Invoice isn't in `draft` status — only draft invoices can be recomputed.
- **Large batches (100+ IDs)**: Consider switching to `sync=false` and adding a 1–2s sleep between batches of 50.
