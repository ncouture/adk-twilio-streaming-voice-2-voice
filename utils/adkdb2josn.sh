#!/bin/bash
#

set -euo pipefail

DB="$1"
if [[ ! -f "${DB}" ]]; then
    echo "Usage: $(basename $0) <agents/.../.adk/session.db>"
    exit 1
fi

AGENT_PATH="$(basename \"${DB}\")"
JSON_FILE="${AGENT_PATH}/.adk/.json"

echo "{" > "$OUT"

# Get a list of tables
TABLES=$(sqlite3 "$DB" "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
TOTAL=$(echo "$TABLES" | wc -w)
COUNT=0

for TABLE in $TABLES; do
    COUNT=$((COUNT+1))
    echo "  \"$TABLE\":" >> "$OUT"

    # Dump table contents as JSON
    sqlite3 "$DB" -cmd ".mode json" "SELECT * FROM \"$TABLE\";" >> "$OUT"

    # Add comma unless it's the last table
    if [ "$COUNT" -lt "$TOTAL" ]; then
        echo "," >> "$OUT"
    fi
done

echo "}" >> "$OUT"
