/**
 * Shared module: project-profile.mdc generation (hub-centric)
 *
 * If you maintain a project rule on the **hub**, point it at the canonical
 * profile under `docs/projects/{project}/profile.md` (see control-plane-paths.md).
 * Cuebert does not generate `.mdc` files inside application repositories.
 */

import * as fs from 'fs';

export function extractFromProfile(profilePath: string): {
  language: string;
  framework: string;
  styling: string;
} {
  const defaults = { language: 'TypeScript', framework: 'React 18', styling: '' };
  if (!fs.existsSync(profilePath)) return defaults;

  const content = fs.readFileSync(profilePath, 'utf-8');

  const langMatch = content.match(/\*\s*\*\*Language:\*\*\s*(.+)/);
  const fwMatch = content.match(/\*\s*\*\*Framework:\*\*\s*(.+)/);
  const styleMatch = content.match(/\*\s*\*\*Styling:\*\*\s*(.+)/);

  return {
    language: langMatch?.[1]?.trim() ?? defaults.language,
    framework: fwMatch?.[1]?.trim() ?? defaults.framework,
    styling: styleMatch?.[1]?.trim() ?? defaults.styling,
  };
}

export function detectPrimaryLanguage(language: string, framework: string): string {
  const lower = `${language} ${framework}`.toLowerCase();
  if (lower.includes('python') || lower.includes('fastapi') || lower.includes('django') || lower.includes('flask')) return 'python';
  if (lower.includes('go') || lower.includes('golang')) return 'go';
  return 'react';
}

/**
 * @param profilePath — Hub path to `docs/projects/{project}/profile.md` (or compatible markdown) for extraction
 * @param hubRelPath — Relative path from the workspace folder where this rule applies to the hub root (often `.` for hub-only)
 */
export function generateProjectProfileMdc(
  projectName: string,
  profilePath: string,
  hubRelPath: string,
): string {
  const info = extractFromProfile(profilePath);
  const primary = detectPrimaryLanguage(info.language, info.framework);
  const hubProfileRef = `${hubRelPath}/docs/projects/${projectName}/profile.md`;

  return `---
description: "Cuebert project profile for ${projectName} — loaded on every request"
alwaysApply: true
---

# ${projectName} — Project Profile

| Key | Value |
|-----|-------|
| **Language** | ${info.language} |
| **Framework** | ${info.framework} |
| **Styling** | ${info.styling || 'N/A'} |
| **Primary Language** | ${primary} |
| **Hub** | ${hubRelPath} |

## Hub workspace resolution

Agents, standards, and shared rules load from the Cuebert hub at \`${hubRelPath}\` when this repo is opened in a **multi-root workspace** with the hub.

**Project plans, knowledge, and project rules** on the hub:

- \`${hubRelPath}/docs/projects/${projectName}/plans/\`
- \`${hubRelPath}/docs/projects/${projectName}/knowledge/\`
- \`${hubRelPath}/docs/projects/${projectName}/rules/\` (if present)

Canonical per-project profile (hub):

- \`${hubProfileRef}\`

See \`${hubRelPath}/docs/_ai_system/standards/control-plane-paths.md\`.
`;
}
