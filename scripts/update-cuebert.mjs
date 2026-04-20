#!/usr/bin/env node

/**
 * Cuebert hub self-update (update-cuebert — plain JS)
 *
 * **Deprecated:** syncing files into application repositories is removed.
 * Refreshes Cursor MCP config and updates hub metadata in
 * `.cuebert/workspace-manifest.json` when present.
 *
 * Usage (from hub root):
 *   node scripts/update-cuebert.mjs
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CUEBERT_ROOT = path.resolve(__dirname, '..');

// Use `bash -lc` so MCP servers spawn under a login shell that sources nvm and
// Homebrew PATH. Avoids hardcoded absolute Node paths (which break on Node
// upgrades) and the parallel `env.PATH` block that Cursor's "Repair server" UI
// tends to inject and then drift. `exec` ensures Cursor's SIGTERM reaches the
// MCP server directly. Keep this template in sync with
// scripts/lib/ensure-cursor-mcp.ts.
const CUEBERT_REQUIRED_MCP_SERVERS = {
  'sequential-thinking': {
    command: '/bin/bash',
    args: ['-lc', 'exec npx -y @modelcontextprotocol/server-sequential-thinking'],
    alwaysAllow: ['sequentialthinking'],
  },
};

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function ensureCursorMcpConfig() {
  const homeDir = process.env.HOME || process.env.USERPROFILE || '';
  if (!homeDir) return;

  const mcpJsonPath = path.join(homeDir, '.cursor', 'mcp.json');
  let existing = {};

  if (fs.existsSync(mcpJsonPath)) {
    try {
      existing = JSON.parse(fs.readFileSync(mcpJsonPath, 'utf-8'));
    } catch {
      existing = {};
    }
  } else {
    ensureDir(path.join(homeDir, '.cursor'));
  }

  if (!existing.mcpServers) existing.mcpServers = {};

  let changed = 0;
  for (const [name, config] of Object.entries(CUEBERT_REQUIRED_MCP_SERVERS)) {
    if (!existing.mcpServers[name]) {
      existing.mcpServers[name] = config;
      changed++;
    } else if (config.alwaysAllow) {
      const have = Array.isArray(existing.mcpServers[name].alwaysAllow)
        ? existing.mcpServers[name].alwaysAllow
        : [];
      const missing = config.alwaysAllow.some((t) => !have.includes(t));
      if (have.length === 0 || missing) {
        existing.mcpServers[name].alwaysAllow = [...new Set([...have, ...config.alwaysAllow])];
        changed++;
      }
    }
  }

  if (changed > 0) {
    fs.writeFileSync(mcpJsonPath, JSON.stringify(existing, null, 2) + '\n');
    console.log(`  ✅ Cursor MCP config updated (${changed} server(s))`);
  }
}

function main() {
  const manifestPath = path.join(CUEBERT_ROOT, '.cuebert', 'workspace-manifest.json');

  const hubVersionPath = path.join(CUEBERT_ROOT, '.cuebert', 'version.json');
  let hubVersion = '0.1.0';
  if (fs.existsSync(hubVersionPath)) {
    try {
      hubVersion = JSON.parse(fs.readFileSync(hubVersionPath, 'utf-8')).version ?? '0.1.0';
    } catch {
      /* default */
    }
  }

  console.log(`\n🔄 Cuebert hub self-update — hub v${hubVersion}\n`);
  console.log('(App-repo hub file sync has been removed; use a multi-root workspace.)\n');

  console.log('Syncing Cursor MCP servers...');
  ensureCursorMcpConfig();

  if (!fs.existsSync(manifestPath)) {
    console.log('\nℹ️  No .cuebert/workspace-manifest.json — optional.');
    console.log(`\n${'═'.repeat(50)}`);
    console.log(`✅ MCP config refreshed — Cuebert v${hubVersion}`);
    console.log(`${'═'.repeat(50)}\n`);
    return;
  }

  let manifest;
  try {
    manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
  } catch {
    console.error('❌ Invalid workspace-manifest.json');
    process.exit(1);
  }

  if (!manifest.hub || typeof manifest.hub !== 'object') {
    manifest.hub = { name: 'cuebert', cuebertVersion: hubVersion, updated: new Date().toISOString().split('T')[0] };
  } else {
    manifest.hub.updated = new Date().toISOString().split('T')[0];
    manifest.hub.cuebertVersion = hubVersion;
    manifest.hub.name = 'cuebert';
  }

  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  console.log('  ✓ Updated hub metadata in workspace-manifest.json');

  console.log(`\n${'═'.repeat(50)}`);
  console.log(`✅ Hub metadata + MCP — Cuebert v${hubVersion}`);
  console.log(`${'═'.repeat(50)}\n`);
}

main();
