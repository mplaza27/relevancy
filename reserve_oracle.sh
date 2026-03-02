#!/usr/bin/env bash
set -euo pipefail

OCI="$HOME/bin/oci"
TENANCY_OCID="ocid1.tenancy.oc1..aaaaaaaakdjddgoscnnrshkaeh73jam6dyunozv54afynlyccvjigfsvwagq"
LOG="/tmp/oci-attempt.log"
RETRY_INTERVAL=60  # seconds between attempts

# --- Find the stack OCID ---
echo "Looking up stacks in your tenancy..."
STACK_ID=$("$OCI" resource-manager stack list \
  --compartment-id "$TENANCY_OCID" \
  --query 'data[0].id' \
  --raw-output)

if [[ -z "$STACK_ID" || "$STACK_ID" == "null" ]]; then
  echo "ERROR: No stacks found. Make sure you saved your instance config as a Stack in OCI Console."
  exit 1
fi

echo "Using stack: $STACK_ID"
echo "Will retry every ${RETRY_INTERVAL}s until capacity is available. Ctrl+C to stop."
echo ""

# --- Retry loop ---
ATTEMPT=0
while true; do
  ATTEMPT=$((ATTEMPT + 1))
  echo "Attempt #${ATTEMPT} — $(date)"

  "$OCI" resource-manager job create-apply-job \
    --stack-id "$STACK_ID" \
    --execution-plan-strategy AUTO_APPROVED \
    --wait-for-state SUCCEEDED \
    --wait-for-state FAILED 2>&1 | tee "$LOG"

  if grep -q '"lifecycle-state": "SUCCEEDED"' "$LOG"; then
    echo ""
    echo "Instance created successfully!"
    break
  fi

  echo "Not available yet. Retrying in ${RETRY_INTERVAL}s..."
  sleep "$RETRY_INTERVAL"
done
