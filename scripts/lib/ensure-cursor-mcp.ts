/**
 * Cursor ~/.cursor/mcp.json merge for Cuebert-required MCP servers.
 * Keeps sequential-thinking on auto-allow even when Cursor resets `alwaysAllow` to [].
 */

import * as fs from 'fs';
import * as path from 'path';

export interface McpServerConfig {
  command?: string;
  args?: string[];
  url?: string;
  headers?: Record<string, string>;
  env?: Record<string, string>;
  alwaysAllow?: string[];
}

// Use a login shell (`bash -lc`) so nvm/Homebrew PATH is sourced at MCP-server
// spawn time. Cursor launches MCP servers from its own (non-login) process, which
// on macOS does NOT include `~/.nvm` or `/opt/homebrew/bin` unless Cursor was
// started from a Terminal that already had them on PATH. The login-shell form
// avoids hardcoded absolute paths (which break on Node version upgrades) and
// the parallel `env.PATH` block (which Cursor's "Repair server" UI tends to
// inject and which then drifts). `exec` replaces the bash process so SIGTERM
// from Cursor reaches the MCP server cleanly on shutdown.
export const CUEBERT_REQUIRED_MCP_SERVERS: Record<string, McpServerConfig> = {
  'sequential-thinking': {
    command: '/bin/bash',
    args: ['-lc', 'exec npx -y @modelcontextprotocol/server-sequential-thinking'],
    alwaysAllow: ['sequentialthinking'],
  },
};

export type McpJsonRoot = { mcpServers?: Record<string, McpServerConfig> };

function mergeAlwaysAllow(
  existingEntry: McpServerConfig,
  required: McpServerConfig,
): boolean {
  const req = required.alwaysAllow;
  if (!req || req.length === 0) return false;

  const have = Array.isArray(existingEntry.alwaysAllow) ? existingEntry.alwaysAllow : [];
  const needs = have.length === 0 || req.some((t) => !have.includes(t));
  if (!needs) return false;

  existingEntry.alwaysAllow = [...new Set([...have, ...req])];
  return true;
}

/** Pure merge — does not read/write disk. Used by install/update and by verify script. */
export function applyCuebertRequiredMcpServers(root: McpJsonRoot): {
  merged: McpJsonRoot;
  changedCount: number;
  actions: string[];
} {
  const merged: McpJsonRoot = JSON.parse(JSON.stringify(root || {}));
  if (!merged.mcpServers) merged.mcpServers = {};

  const actions: string[] = [];
  let changedCount = 0;

  for (const [name, config] of Object.entries(CUEBERT_REQUIRED_MCP_SERVERS)) {
    if (!merged.mcpServers[name]) {
      merged.mcpServers[name] = { ...config };
      actions.push(`Added MCP server: ${name}`);
      changedCount++;
    } else if (mergeAlwaysAllow(merged.mcpServers[name], config)) {
      actions.push(`Merged alwaysAllow for: ${name}`);
      changedCount++;
    }
  }

  return { merged, changedCount, actions };
}

function ensureDir(dir: string): void {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

/**
 * Patches ~/.cursor/mcp.json so sequential-thinking includes alwaysAllow for `sequentialthinking`.
 * Fixes post-Cursor-update shapes like `alwaysAllow: []` or missing tool entries.
 *
 * @returns true if the file on disk was written
 */
export function ensureCursorMcpConfig(opts?: { logWhenUnchanged?: boolean }): boolean {
  const logWhenUnchanged = opts?.logWhenUnchanged !== false;
  const homeDir = process.env.HOME || process.env.USERPROFILE || '';
  if (!homeDir) return false;

  const mcpJsonPath = path.join(homeDir, '.cursor', 'mcp.json');
  let existing: McpJsonRoot = {};

  if (fs.existsSync(mcpJsonPath)) {
    try {
      existing = JSON.parse(fs.readFileSync(mcpJsonPath, 'utf-8'));
    } catch {
      existing = {};
    }
  } else {
    ensureDir(path.join(homeDir, '.cursor'));
  }

  const { merged, changedCount, actions } = applyCuebertRequiredMcpServers(existing);
  const diskChanged = changedCount > 0 && JSON.stringify(merged) !== JSON.stringify(existing);

  if (diskChanged) {
    fs.writeFileSync(mcpJsonPath, JSON.stringify(merged, null, 2) + '\n');
    for (const a of actions) console.log(`  ✓ ${a}`);
    console.log(`  ✅ Cursor MCP config updated (${changedCount} change(s))`);
  } else if (logWhenUnchanged) {
    console.log('  ✅ MCP servers already satisfy Cuebert requirements (sequential-thinking auto-allow)');
  }

  return diskChanged;
}
