---
name: batch-subscription-draft-compute
description: >
  Batch draft-and-compute FlexPrice subscriptions from a CSV file of subscription IDs. Use this skill
  whenever the user wants to trigger subscription draft and compute, process subscription drafts, or run
  the draft-and-compute endpoint on a list/batch of subscription IDs. Triggers on: 'draft and compute',
  'draft-and-compute', 'subscription draft', 'batch subscription', 'subscription compute', 'drafts prepare',
  or any mention of running the /subscriptions/temporal/draft-and-compute API on multiple subscription IDs.
  Also trigger when the user uploads a CSV containing subscription IDs (subs_*) and wants them processed.
---

# Batch Subscription Draft-and-Compute

Process a CSV of FlexPrice subscription IDs by calling the draft-and-compute endpoint for each one, in configurable batches.

## Required inputs

1. **CSV file** — A file with a header row containing an `id` column with subscription IDs (e.g., `subs_01KKYH6K...`)
2. **API key** — The `x-api-key` header value
3. **Base URL** — Ask for region if not already known:
   - Cloud (default): `https://api.cloud.flexprice.io/v1`
   - US: `https://us.api.flexprice.io/v1`
   - Self-hosted: user will provide

## Default configuration

- **Batch size**: 200
- **Sleep between batches**: 2 seconds

Adjust based on user preference: "go easy" → batch 50, sleep 3s. "aggressive" → batch 500, sleep 1s.

## How to run

```bash
#!/bin/bash
API_KEY="<provided-api-key>"
BASE_URL="<base-url>"
CSV_FILE="<path-to-csv>"

mapfile -t IDS < <(tail -n +2 "$CSV_FILE" | tr -d '\r')
TOTAL=${#IDS[@]}
BATCH_SIZE=200
SLEEP_SECONDS=2
SUCCESS=0
FAIL=0
BATCH_NUM=0

echo "Starting batch draft-and-compute for $TOTAL subscriptions (batches of $BATCH_SIZE, ${SLEEP_SECONDS}s sleep)"
for ((i=0; i<TOTAL; i++)); do
  ID="${IDS[$i]}"
  [ -z "$ID" ] && continue

  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    "${BASE_URL}/subscriptions/temporal/${ID}/draft-and-compute" \
    -H "x-api-key: ${API_KEY}" \
    -H "Content-Type: application/json")

  if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
    SUCCESS=$((SUCCESS + 1))
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $ID -> HTTP $HTTP_CODE"
  fi

  BATCH_POS=$(( (i % BATCH_SIZE) + 1 ))
  PROCESSED=$((i + 1))

  if [ "$BATCH_POS" -eq "$BATCH_SIZE" ] && [ "$PROCESSED" -lt "$TOTAL" ]; then
    BATCH_NUM=$((BATCH_NUM + 1))
    echo "Batch $BATCH_NUM done ($PROCESSED/$TOTAL) | Success: $SUCCESS, Fail: $FAIL"
    sleep $SLEEP_SECONDS
  fi
done

echo "---"
echo "COMPLETE: $PROCESSED/$TOTAL processed | Success: $SUCCESS | Fail: $FAIL"
```

## Handling large files

If the CSV has more than ~2,000 IDs, the execution may time out. Use a `START` variable to resume from where it left off.

## After completion

Report total processed, successful, and failed counts (with IDs if any failed).
