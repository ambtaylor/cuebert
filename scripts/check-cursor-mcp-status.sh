#!/usr/bin/env bash
# Read-only diagnostic for Cursor MCP auto-run / sequential-thinking readiness.
# Safe to run while Cursor is open (no writes).
# Platform: macOS + Cursor.app (see Issue I-4 in cuebert-gaming-system plan).
#
# Usage: bash cuebert/scripts/check-cursor-mcp-status.sh
# Exit: 0 = all checks pass, 1 = one or more failures
set -euo pipefail

PRODUCT_JSON="/Applications/Cursor.app/Contents/Resources/app/product.json"
ROOT="$HOME/Library/Application Support/Cursor"
KEY='src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser'
DB="$ROOT/User/globalStorage/state.vscdb"
MCP_JSON="${HOME}/.cursor/mcp.json"

FAILS=0

fail() {
  echo "[FAIL] $*"
  FAILS=$((FAILS + 1))
}

pass() {
  echo "[PASS] $*"
}

summary() {
  if [[ "$FAILS" -eq 0 ]]; then
    echo "SUMMARY: all checks passed (0 failures)."
    exit 0
  else
    echo "SUMMARY: $FAILS check(s) failed."
    exit 1
  fi
}

# --- 1) Cursor version ---
if [[ -f "$PRODUCT_JSON" ]]; then
  ver=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" "$PRODUCT_JSON" 2>/dev/null || echo "unknown")
  pass "Cursor version (product.json): $ver"
else
  fail "Cursor product.json missing at $PRODUCT_JSON (cannot read version)."
fi

# --- 2) state.vscdb top-level flags (Cuebert expects auto-run friendly values) ---
if [[ ! -f "$DB" ]]; then
  fail "state.vscdb not found: $DB (cannot read IDE flags)."
else
  if ! /usr/bin/sqlite3 -readonly "$DB" "SELECT 1 FROM ItemTable WHERE key='$KEY' LIMIT 1;" | grep -q 1; then
    fail "ItemTable missing expected key (cannot read shouldAutoContinueToolCall / yoloMcpToolsDisabled / isAutoApplyEnabled)."
  else
    sac=$(/usr/bin/sqlite3 -readonly "$DB" "SELECT json_extract(value,'\$.shouldAutoContinueToolCall') FROM ItemTable WHERE key='$KEY';")
    yolo=$(/usr/bin/sqlite3 -readonly "$DB" "SELECT json_extract(value,'\$.yoloMcpToolsDisabled') FROM ItemTable WHERE key='$KEY';")
    auto=$(/usr/bin/sqlite3 -readonly "$DB" "SELECT json_extract(value,'\$.isAutoApplyEnabled') FROM ItemTable WHERE key='$KEY';")
    if [[ "$sac" == "1" ]]; then pass "state.vscdb: shouldAutoContinueToolCall=$sac"; else fail "state.vscdb: shouldAutoContinueToolCall expected 1, got ${sac:-<empty>}"; fi
    if [[ "$yolo" == "0" ]]; then pass "state.vscdb: yoloMcpToolsDisabled=$yolo"; else fail "state.vscdb: yoloMcpToolsDisabled expected 0, got ${yolo:-<empty>}"; fi
    if [[ "$auto" == "1" ]]; then pass "state.vscdb: isAutoApplyEnabled=$auto"; else fail "state.vscdb: isAutoApplyEnabled expected 1, got ${auto:-<empty>}"; fi
  fi
fi

# --- 3) modes4 by id: agent + triage autoRun / fullAutoRun ---
if [[ -f "$DB" ]] && /usr/bin/sqlite3 -readonly "$DB" "SELECT 1 FROM ItemTable WHERE key='$KEY' LIMIT 1;" | grep -q 1; then
  M4_TYPE=$(/usr/bin/sqlite3 -readonly "$DB" "SELECT json_type(value, '\$.composerState.modes4') FROM ItemTable WHERE key='$KEY';" || echo "")
  if [[ "$M4_TYPE" != "array" ]]; then
    fail "composerState.modes4 is not an array (json_type=${M4_TYPE:-<empty>})."
  else
    pass "composerState.modes4 present (json_type=array)"
    while IFS= read -r line; do
      idx="${line%%|*}"
      rest="${line#*|}"
      mid="${rest%%|*}"
      ar="${rest#*|}"
      far="${ar#*|}"
      ar="${ar%%|*}"
      case "$mid" in
        agent|triage)
          if [[ "$ar" == "1" ]] && [[ "$far" == "1" ]]; then
            pass "modes4[$idx] id=$mid autoRun=$ar fullAutoRun=$far"
          else
            fail "modes4[$idx] id=$mid expected autoRun=1 and fullAutoRun=1 (got autoRun=${ar:-?} fullAutoRun=${far:-?})."
          fi
          ;;
      esac
    done < <(/usr/bin/sqlite3 -readonly "$DB" "
      SELECT key || '|' || json_extract(value, '\$.id') || '|' ||
             json_extract(value, '\$.autoRun') || '|' ||
             json_extract(value, '\$.fullAutoRun')
      FROM json_each((
        SELECT json_extract(value, '\$.composerState.modes4') FROM ItemTable WHERE key='$KEY' LIMIT 1
      ));
    ")
    for id in agent triage; do
      c=$(/usr/bin/sqlite3 -readonly "$DB" "
        SELECT COUNT(*) FROM json_each((
          SELECT json_extract(value, '\$.composerState.modes4') FROM ItemTable WHERE key='$KEY' LIMIT 1
        )) WHERE json_extract(value, '\$.id') = '$id';
      ")
      if [[ "$c" -ge 1 ]]; then
        pass "modes4: found id=$id"
      else
        fail "modes4: missing entry with id=$id"
      fi
    done
  fi
fi

# --- 4) ~/.cursor/mcp.json: sequential-thinking + alwaysAllow ---
if [[ ! -f "$MCP_JSON" ]]; then
  fail "mcp.json missing: $MCP_JSON"
else
  if python3 -c 'import json,sys
path=sys.argv[1]
with open(path,encoding="utf-8") as f:data=json.load(f)
servers=data.get("mcpServers")or{}
st=servers.get("sequential-thinking")
if not isinstance(st,dict):sys.exit(1)
allow=st.get("alwaysAllow")
if not isinstance(allow,list)or"sequentialthinking"not in allow:sys.exit(1)
sys.exit(0)' "$MCP_JSON" 2>/dev/null; then
    pass "mcp.json: sequential-thinking present; alwaysAllow includes sequentialthinking"
  else
    fail "mcp.json: sequential-thinking missing or alwaysAllow does not include sequentialthinking"
  fi
fi

summary
