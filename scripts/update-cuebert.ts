#!/usr/bin/env npx tsx

/**
 * Cuebert hub self-update (update-cuebert)
 *
 * **Deprecated:** syncing files into application repositories is removed.
 * Run this from the **hub** repo to refresh Cursor MCP config and bump hub
 * metadata in `.cuebert/workspace-manifest.json` when present.
 *
 * Application repos are discovered via the Cursor multi-root workspace; they
 * must not receive Cuebert-installed trees (zero-footprint model).
 *
 * Usage (from hub root):
 *   npx tsx scripts/update-cuebert.ts
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { ensureCursorMcpConfig } from './lib/ensure-cursor-mcp.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CUEBERT_ROOT = path.resolve(__dirname, '..');

function main(): void {
  const manifestPath = path.join(CUEBERT_ROOT, '.cuebert', 'workspace-manifest.json');

  const hubVersionPath = path.join(CUEBERT_ROOT, '.cuebert', 'version.json');
  let hubVersion = '0.1.0';
  if (fs.existsSync(hubVersionPath)) {
    try {
      hubVersion = JSON.parse(fs.readFileSync(hubVersionPath, 'utf-8')).version ?? '0.1.0';
    } catch {
      /* keep default */
    }
  }

  console.log(`\n🔄 Cuebert hub self-update — hub v${hubVersion}\n`);
  console.log('(App-repo hub file sync has been removed; use a multi-root workspace.)\n');

  console.log('Syncing Cursor MCP servers...');
  ensureCursorMcpConfig({ logWhenUnchanged: false });

  if (!fs.existsSync(manifestPath)) {
    console.log('\nℹ️  No .cuebert/workspace-manifest.json — optional; create via install-cuebert.ts --project-key if needed.');
    console.log(`\n${'═'.repeat(50)}`);
    console.log(`✅ MCP config refreshed — Cuebert v${hubVersion}`);
    console.log(`${'═'.repeat(50)}\n`);
    return;
  }

  let raw: string;
  try {
    raw = fs.readFileSync(manifestPath, 'utf-8');
  } catch {
    console.error('❌ Could not read workspace-manifest.json');
    process.exit(1);
  }

  let manifest: { hub?: { updated?: string; cuebertVersion?: string; name?: string } };
  try {
    manifest = JSON.parse(raw);
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
  console.log(`  ✓ Updated hub metadata in workspace-manifest.json`);

  console.log(`\n${'═'.repeat(50)}`);
  console.log(`✅ Hub metadata + MCP — Cuebert v${hubVersion}`);
  console.log(`${'═'.repeat(50)}\n`);
}

main();
