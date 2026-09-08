#!/usr/bin/env bash
set -euo pipefail

# Trigger a workflow by filename and watch its run using gh CLI.
# Usage: scripts/trigger_and_watch_workflow.sh [workflow_filename] [ref]
# Example: scripts/trigger_and_watch_workflow.sh fetch_and_commit_fixtures.yaml main

WORKFLOW=${1:-fetch_and_commit_fixtures.yaml}
REF=${2:-main}

echo "Triggering workflow $WORKFLOW on ref $REF"
gh workflow run "$WORKFLOW" --ref "$REF"

echo "Waiting briefly for run to register..."
sleep 5

echo "Finding latest run id for workflow $WORKFLOW"
RUN_JSON=$(gh run list --workflow "$WORKFLOW" --limit 1 --json id,status,conclusion,event,headBranch)
RUN_ID=$(python - <<PY
import sys, json
data = json.load(sys.stdin)
if len(data) == 0:
    print("")
else:
    print(data[0].get('id',''))
PY
<<<"$RUN_JSON")

if [ -z "$RUN_ID" ]; then
    echo "Could not find run id for workflow $WORKFLOW"
    exit 1
fi

echo "Watching run $RUN_ID"
gh run watch "$RUN_ID"

echo "Fetching logs for run $RUN_ID"
gh run view "$RUN_ID" --log

echo "Done"
