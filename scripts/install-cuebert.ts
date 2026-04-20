#!/usr/bin/env npx tsx

/**
 * Hub project scaffold (install-cuebert)
 *
 * **Deprecated:** Cuebert does not install files into application repositories.
 * Application repos should remain at **zero Cuebert footprint**; add them to the
 * Cursor multi-root workspace alongside this hub.
 *
 * Forked from the Cue hub baseline; paths and product naming are Cuebert-specific.
 *
 * This entrypoint only performs **hub-side** setup:
 * - `docs/projects/{project}/` (plans, knowledge, rules)
 * - `.cuebert/vault/{project}/` placeholder on the hub
 * - Optional: register an app repo path in `.cuebert/workspace-manifest.json` for
 *   tools that discover workspace roots (e.g. hydrate-vault --all)
 *
 * Usage (from hub root):
 *   npx tsx scripts/install-cuebert.ts --project-key <name> [--language react|python|go] [<app-repo-path>]
 *
 * - `--project-key` — key under `docs/projects/{key}/` (required)
 * - `<app-repo-path>` — optional absolute path to an app repo; if set, adds/updates
 *   the manifest entry pointing at that directory (relative to the hub)
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { ensureCursorMcpConfig } from './lib/ensure-cursor-mcp.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CUEBERT_ROOT = path.resolve(__dirname, '..');

function readHubVersionFromDisk(): string {
  const hubVersionPath = path.join(CUEBERT_ROOT, '.cuebert', 'version.json');
  if (fs.existsSync(hubVersionPath)) {
    try {
      return JSON.parse(fs.readFileSync(hubVersionPath, 'utf-8')).version ?? '0.1.0';
    } catch {
      /* keep default */
    }
  }
  return '0.1.0';
}

function ensureDir(dir: string): void {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
    console.log(`  📁 ${path.relative(process.cwd(), dir)}`);
  }
}

function scaffoldHubVaultDir(projectName: string): void {
  const hubVaultDir = path.join(CUEBERT_ROOT, '.cuebert', 'vault', projectName);
  ensureDir(hubVaultDir);
  const gk = path.join(hubVaultDir, '.gitkeep');
  if (!fs.existsSync(gk)) fs.writeFileSync(gk, '');
  console.log(`  ✓ Hub vault directory: .cuebert/vault/${projectName}/`);
}

function scaffoldHubProjectStateDirs(projectName: string): void {
  const sub = ['plans/active', 'plans/archive', 'knowledge', 'rules'] as const;
  for (const s of sub) {
    const dir = path.join(CUEBERT_ROOT, 'docs', 'projects', projectName, s);
    ensureDir(dir);
    const gk = path.join(dir, '.gitkeep');
    if (!fs.existsSync(gk)) fs.writeFileSync(gk, '');
  }
  console.log(`  ✓ Hub project state: docs/projects/${projectName}/ (plans, knowledge, rules)`);
}

function bootstrapGlobalVault(): void {
  const homeDir = process.env.HOME || process.env.USERPROFILE || '';
  if (!homeDir) {
    console.log('  ⚠ Could not determine home directory — skipping vault bootstrap');
    return;
  }

  const cuebertGlobal = path.join(homeDir, '.cuebert');
  if (fs.existsSync(path.join(cuebertGlobal, 'vault', 'credentials.yaml'))) {
    console.log('  ✓ Global vault exists at ~/.cuebert/');
    return;
  }

  console.log('Bootstrapping global vault at ~/.cuebert/ ...');
  for (const dir of ['vault', 'registry']) {
    ensureDir(path.join(cuebertGlobal, dir));
  }

  const credsPath = path.join(cuebertGlobal, 'vault', 'credentials.yaml');
  if (!fs.existsSync(credsPath)) {
    fs.writeFileSync(
      credsPath,
      `# ~/.cuebert/vault/credentials.yaml
# All secrets — NEVER commit. File permissions: 600 (owner-only read/write).
# Populate interactively with: python scripts/init-vault.py

sfdc:
  api_token: ""
  proxy_url: ""

jira:
  url: ""
  email: ""
  api_token: ""
  project_key: ""
`,
    );
    fs.chmodSync(credsPath, 0o600);
    console.log(`  ✓ Created credentials.yaml (permissions: 600)`);
  }

  const configPath = path.join(cuebertGlobal, 'config.yaml');
  if (!fs.existsSync(configPath)) {
    fs.writeFileSync(
      configPath,
      `# ~/.cuebert/config.yaml
cuebert_source: "${CUEBERT_ROOT}"
default_language: python
vault_version: 1
`,
    );
    console.log('  ✓ Created config.yaml');
  }

  console.log('  ✅ Global vault bootstrap complete.\n');
}

function registerInManifest(appRepoPath: string, language: string, projectName: string): void {
  const manifestPath = path.join(CUEBERT_ROOT, '.cuebert', 'workspace-manifest.json');
  let manifest: Record<string, unknown> = {};

  if (fs.existsSync(manifestPath)) {
    try {
      manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
    } catch {
      console.log('  ⚠ Could not parse workspace-manifest.json — will create fresh');
    }
  }

  const hubVer = readHubVersionFromDisk();

  if (!manifest.projects || typeof manifest.projects !== 'object') {
    manifest = {
      $schema: 'cuebert-workspace-manifest',
      manifestVersion: '1.0',
      hub: { name: 'cuebert', cuebertVersion: hubVer, updated: new Date().toISOString().split('T')[0] },
      projects: {},
      vaultResolution: {
        order: [
          'project .cuebert/vault/',
          'hub .cuebert/vault/{project}/',
          'hub .cuebert/vault/shared/',
        ],
        description: 'Credentials are resolved in this priority order. Deep-merged per FileVaultResolver semantics (see docs/_ai_system/standards/vault.md).',
      },
    };
  }

  const relPath = path.relative(CUEBERT_ROOT, appRepoPath);
  const projects = manifest.projects as Record<string, Record<string, string>>;

  projects[projectName] = {
    path: relPath.startsWith('.') ? relPath : `../${path.basename(appRepoPath)}`,
    language,
    description: `[TODO: describe ${projectName}]`,
    installed: new Date().toISOString().split('T')[0],
  };

  (manifest as Record<string, unknown>).hub = {
    ...((manifest.hub as Record<string, unknown>) || {}),
    name: 'cuebert',
    cuebertVersion: hubVer,
    updated: new Date().toISOString().split('T')[0],
  };

  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  console.log(`  ✓ Registered ${projectName} in workspace-manifest.json`);
}

function run(projectName: string, language: string, appRepoPath: string | undefined): void {
  if (!/^[-a-z0-9_]+$/i.test(projectName)) {
    console.error(`❌ Invalid --project-key "${projectName}" (use letters, numbers, hyphen, underscore only).`);
    process.exit(1);
  }

  console.log('\n⚠️  install-cuebert is deprecated for app-repo file installation.');
  console.log('    Cuebert is hub-only; use a multi-root workspace. Hub scaffold only.\n');
  console.log(`🚀 Hub scaffold for project key: ${projectName}`);
  console.log(`   Language (manifest): ${language}`);
  console.log(`   Hub: ${CUEBERT_ROOT}\n`);

  bootstrapGlobalVault();
  console.log('Configuring Cursor MCP servers...');
  ensureCursorMcpConfig({ logWhenUnchanged: true });

  if (appRepoPath) {
    if (!fs.existsSync(appRepoPath)) {
      console.error(`❌ App repo path does not exist: ${appRepoPath}`);
      process.exit(1);
    }
    console.log('\nRegistering app repo in workspace manifest...');
    registerInManifest(path.resolve(appRepoPath), language, projectName);
  } else {
    console.log('\n(No app-repo path — skipping workspace-manifest.json update.)');
  }

  console.log('\nScaffolding hub project directories...');
  scaffoldHubVaultDir(projectName);
  scaffoldHubProjectStateDirs(projectName);

  console.log('\n✅ Hub scaffold complete.');
  console.log(`   - docs/projects/${projectName}/`);
  console.log(`   - .cuebert/vault/${projectName}/`);
  console.log(`\nNext: add docs/projects/${projectName}/profile.md on the hub, add app repos to the Cursor workspace,`);
  console.log('and read control-plane-paths.md for discovery rules.\n');
}

const args = process.argv.slice(2);
if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
  console.log('Hub project scaffold (install-cuebert — deprecated for app installs)\n');
  console.log('Usage: npx tsx scripts/install-cuebert.ts --project-key <name> [--language react|python|go] [<app-repo-path>]\n');
  console.log('  --project-key <name>   Hub key under docs/projects/{name}/ (required)');
  console.log('  --language <lang>      Stored in manifest when app path given (default: react)');
  console.log('  <app-repo-path>        Optional path to register in workspace-manifest.json\n');
  process.exit(args.length === 0 ? 1 : 0);
}

let projectKey = '';
let language = 'react';
let appPath: string | undefined;
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === '--language') {
    language = args[++i] ?? language;
    continue;
  }
  if (a === '--project-key') {
    projectKey = args[++i] ?? '';
    continue;
  }
  if (a.startsWith('-')) {
    console.error(`❌ Unknown option: ${a}`);
    process.exit(1);
  }
  if (!appPath) appPath = path.resolve(a);
  else {
    console.error('❌ Unexpected extra argument.');
    process.exit(1);
  }
}

if (!projectKey) {
  console.error('❌ --project-key is required.');
  process.exit(1);
}

if (!['react', 'python', 'go'].includes(language)) {
  console.error(`❌ Unknown language: ${language}. Use react, python, or go.`);
  process.exit(1);
}

run(projectKey, language, appPath);
