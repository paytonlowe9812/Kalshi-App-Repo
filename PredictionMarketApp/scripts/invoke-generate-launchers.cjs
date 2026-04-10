'use strict';
/**
 * Called from frontend/package.json "postinstall" on Windows, macOS, and Linux.
 * Runs generate_launchers.py using the first Python executable that works.
 */
const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const root = path.resolve(__dirname, '..');
const gen = path.join(root, 'scripts', 'generate_launchers.py');

if (!fs.existsSync(gen)) {
  console.warn('[postinstall] generate_launchers.py not found; skipping launch script generation.');
  process.exit(0);
}

const win = process.platform === 'win32';

/** @type {Array<[string, string[]]>} */
const attempts = win
  ? [
      ['py', ['-3', gen]],
      ['python', [gen]],
      ['python3', [gen]],
    ]
  : [
      ['python3', [gen]],
      ['python', [gen]],
    ];

for (const [cmd, args] of attempts) {
  const r = spawnSync(cmd, args, {
    cwd: root,
    stdio: 'inherit',
    shell: win,
    env: process.env,
  });
  if (r.status === 0) {
    process.exit(0);
  }
}

console.warn('[postinstall] Could not run generate_launchers.py (is Python 3.10+ on PATH?).');
console.warn('[postinstall] Launch scripts were not created. After fixing Python, run:');
console.warn(`[postinstall]   cd "${root}"`);
console.warn('[postinstall]   python scripts/generate_launchers.py');
process.exit(0);
