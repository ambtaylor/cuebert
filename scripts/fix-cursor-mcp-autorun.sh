#!/usr/bin/env bash
# Patches Cursor's state.vscdb to enable MCP auto-run (sequential-thinking)
# after a Cursor IDE update resets fullAutoRun or reorders modes4.
# Platform: macOS + Cursor.app (see Issue I-4 in cuebert-gaming-system plan).
#
# Usage: quit Cursor, then run:  bash cuebert/scripts/fix-cursor-mcp-autorun.sh
set -euo pipefail

PRODUCT_JSON="/Applications/Cursor.app/Contents/Resources/app/product.json"
ROOT="$HOME/Library/Application Support/Cursor"
STAMP=$(date +%Y%m%d-%H%M%S)
KEY='src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser'
DB="$ROOT/User/globalStorage/state.vscdb"

log_cursor_version() {
  if [[ ! -f "$PRODUCT_JSON" ]]; then
    echo "WARN: Cursor product.json not found at $PRODUCT_JSON (version unknown; macOS path)." >&2
    return
  fi
  local ver
  ver=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" "$PRODUCT_JSON" 2>/dev/null || echo "unknown")
  echo "Cursor version (from product.json): $ver"
}

abort_schema() {
  echo "ABORT: Schema validation failed — $*" >&2
  echo "  Expected ItemTable JSON with composerState.modes4 as a JSON array containing modes with id 'agent' and 'triage'." >&2
  echo "  Close Cursor, ensure this machine uses the expected Cursor profile, or inspect: $DB" >&2
  exit 1
}

if [[ ! -f "$DB" ]]; then
  echo "ABORT: state.vscdb not found: $DB" >&2
  exit 1
fi

log_cursor_version

# --- Schema: composerState.modes4 exists, is array, has agent + triage (by id) ---
ROW_EXISTS=$(/usr/bin/sqlite3 -readonly "$DB" "SELECT COUNT(*) FROM ItemTable WHERE key='$KEY';")
if [[ "$ROW_EXISTS" != "1" ]]; then
  abort_schema "ItemTable row for expected key missing (count=$ROW_EXISTS)."
fi

JSON_OK=$(/usr/bin/sqlite3 -readonly "$DB" "SELECT json_valid(value) FROM ItemTable WHERE key='$KEY';")
if [[ "$JSON_OK" != "1" ]]; then
  abort_schema "stored JSON is not valid for key."
fi

M4_TYPE=$(/usr/bin/sqlite3 -readonly "$DB" "SELECT json_type(value, '\$.composerState.modes4') FROM ItemTable WHERE key='$KEY';")
if [[ "$M4_TYPE" != "array" ]]; then
  abort_schema "composerState.modes4 is not an array (json_type='$M4_TYPE')."
fi

AGENT_COUNT=$(/usr/bin/sqlite3 -readonly "$DB" "
  SELECT COUNT(*) FROM json_each((
    SELECT json_extract(value, '\$.composerState.modes4') FROM ItemTable WHERE key='$KEY' LIMIT 1
  )) WHERE json_extract(value, '\$.id') = 'agent';
")
TRIAGE_COUNT=$(/usr/bin/sqlite3 -readonly "$DB" "
  SELECT COUNT(*) FROM json_each((
    SELECT json_extract(value, '\$.composerState.modes4') FROM ItemTable WHERE key='$KEY' LIMIT 1
  )) WHERE json_extract(value, '\$.id') = 'triage';
")

if [[ "$AGENT_COUNT" -lt 1 ]] || [[ "$TRIAGE_COUNT" -lt 1 ]]; then
  abort_schema "modes4 must include at least one 'agent' and one 'triage' entry (agent=$AGENT_COUNT, triage=$TRIAGE_COUNT)."
fi

AGENT_IDX=$(/usr/bin/sqlite3 -readonly "$DB" "
  SELECT key FROM json_each((
    SELECT json_extract(value, '\$.composerState.modes4') FROM ItemTable WHERE key='$KEY' LIMIT 1
  )) WHERE json_extract(value, '\$.id') = 'agent' LIMIT 1;
")
TRIAGE_IDX=$(/usr/bin/sqlite3 -readonly "$DB" "
  SELECT key FROM json_each((
    SELECT json_extract(value, '\$.composerState.modes4') FROM ItemTable WHERE key='$KEY' LIMIT 1
  )) WHERE json_extract(value, '\$.id') = 'triage' LIMIT 1;
")

if [[ -z "$AGENT_IDX" ]] || [[ -z "$TRIAGE_IDX" ]]; then
  abort_schema "could not resolve modes4 indices for agent/triage."
fi

echo "=== Patching: $DB ==="
echo "Resolved modes4 indices: agent=[$AGENT_IDX] triage=[$TRIAGE_IDX]"

cp "$DB" "$DB.bak.$STAMP" || true
echo "Backup: $DB.bak.$STAMP"

echo "--- BEFORE (selected fields) ---"
/usr/bin/sqlite3 -readonly "$DB" "
  SELECT
    'shouldAutoContinueToolCall=' || COALESCE(json_extract(value,'\$.shouldAutoContinueToolCall'),'NULL'),
    'yoloMcpToolsDisabled=' || COALESCE(json_extract(value,'\$.yoloMcpToolsDisabled'),'NULL'),
    'isAutoApplyEnabled=' || COALESCE(json_extract(value,'\$.isAutoApplyEnabled'),'NULL'),
    'modes4[' || '$AGENT_IDX' || '].id=' || COALESCE(json_extract(value,'\$.composerState.modes4[' || '$AGENT_IDX' || '].id'),'NULL'),
    'modes4[' || '$AGENT_IDX' || '].autoRun=' || COALESCE(json_extract(value,'\$.composerState.modes4[' || '$AGENT_IDX' || '].autoRun'),'NULL'),
    'modes4[' || '$AGENT_IDX' || '].fullAutoRun=' || COALESCE(json_extract(value,'\$.composerState.modes4[' || '$AGENT_IDX' || '].fullAutoRun'),'NULL'),
    'modes4[' || '$TRIAGE_IDX' || '].id=' || COALESCE(json_extract(value,'\$.composerState.modes4[' || '$TRIAGE_IDX' || '].id'),'NULL'),
    'modes4[' || '$TRIAGE_IDX' || '].autoRun=' || COALESCE(json_extract(value,'\$.composerState.modes4[' || '$TRIAGE_IDX' || '].autoRun'),'NULL'),
    'modes4[' || '$TRIAGE_IDX' || '].fullAutoRun=' || COALESCE(json_extract(value,'\$.composerState.modes4[' || '$TRIAGE_IDX' || '].fullAutoRun'),'NULL')
  FROM ItemTable WHERE key='$KEY';
"

# Build json_set paths for modes4 slots (indices from json_each are numeric strings)
/usr/bin/sqlite3 "$DB" "PRAGMA busy_timeout=5000; BEGIN;

  UPDATE ItemTable SET value=json_set(value,
    '\$.shouldAutoContinueToolCall', 1,
    '\$.yoloMcpToolsDisabled', 0,
    '\$.isAutoApplyEnabled', 1
  ) WHERE key='$KEY' AND json_valid(value);

  UPDATE ItemTable SET value=json_set(value,
    '\$.composerState.useYoloMode', 0,
    '\$.composerState.shouldAutoContinueToolCall', 1,
    '\$.composerState.yoloMcpToolsDisabled', 0,
    '\$.composerState.isAutoApplyEnabled', 1,
    '\$.composerState.modes4[' || '$AGENT_IDX' || '].autoRun', 1,
    '\$.composerState.modes4[' || '$AGENT_IDX' || '].fullAutoRun', 1,
    '\$.composerState.modes4[' || '$TRIAGE_IDX' || '].autoRun', 1,
    '\$.composerState.modes4[' || '$TRIAGE_IDX' || '].fullAutoRun', 1
  ) WHERE key='$KEY' AND json_valid(value);

  UPDATE ItemTable SET value=REPLACE(value,'\"mcpEnabled\": false','\"mcpEnabled\": true')
    WHERE key='$KEY' AND value LIKE '%\"mcpEnabled\": false%';

  COMMIT;"

echo "--- AFTER (same fields) ---"
/usr/bin/sqlite3 -readonly "$DB" "
  SELECT
    'shouldAutoContinueToolCall=' || COALESCE(json_extract(value,'\$.shouldAutoContinueToolCall'),'NULL'),
    'yoloMcpToolsDisabled=' || COALESCE(json_extract(value,'\$.yoloMcpToolsDisabled'),'NULL'),
    'isAutoApplyEnabled=' || COALESCE(json_extract(value,'\$.isAutoApplyEnabled'),'NULL'),
    'modes4[' || '$AGENT_IDX' || '].id=' || COALESCE(json_extract(value,'\$.composerState.modes4[' || '$AGENT_IDX' || '].id'),'NULL'),
    'modes4[' || '$AGENT_IDX' || '].autoRun=' || COALESCE(json_extract(value,'\$.composerState.modes4[' || '$AGENT_IDX' || '].autoRun'),'NULL'),
    'modes4[' || '$AGENT_IDX' || '].fullAutoRun=' || COALESCE(json_extract(value,'\$.composerState.modes4[' || '$AGENT_IDX' || '].fullAutoRun'),'NULL'),
    'modes4[' || '$TRIAGE_IDX' || '].id=' || COALESCE(json_extract(value,'\$.composerState.modes4[' || '$TRIAGE_IDX' || '].id'),'NULL'),
    'modes4[' || '$TRIAGE_IDX' || '].autoRun=' || COALESCE(json_extract(value,'\$.composerState.modes4[' || '$TRIAGE_IDX' || '].autoRun'),'NULL'),
    'modes4[' || '$TRIAGE_IDX' || '].fullAutoRun=' || COALESCE(json_extract(value,'\$.composerState.modes4[' || '$TRIAGE_IDX' || '].fullAutoRun'),'NULL')
  FROM ItemTable WHERE key='$KEY';
"

echo ""
echo "Done. Restart Cursor and verify sequential-thinking runs without approval prompts."
