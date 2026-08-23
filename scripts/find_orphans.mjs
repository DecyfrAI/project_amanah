// Walks the import graph from the real entry points and reports source files
// that nothing reaches. Run: node scripts/find_orphans.mjs
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { dirname, resolve, relative, extname, join } from 'node:path';

const SRC = resolve('apps/web/src');
const ENTRIES = ['apps/web/src/main.tsx'];
const EXTS = ['.ts', '.tsx', '.js', '.jsx'];

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) out.push(...walk(full));
    else if (EXTS.includes(extname(name))) out.push(full);
  }
  return out;
}

function resolveSpec(spec, fromFile) {
  let base;
  if (spec.startsWith('@/')) {
    base = join(SRC, spec.slice(2));
  } else if (spec.startsWith('.')) {
    base = resolve(dirname(fromFile), spec);
  } else {
    return null;
  }
  const candidates = [
    base,
    ...EXTS.map((e) => base + e),
    ...EXTS.map((e) => join(base, 'index' + e)),
  ];
  for (const c of candidates) {
    if (existsSync(c) && statSync(c).isFile()) return c;
  }
  return null;
}

// Three shapes: `from '...'`, bare `import '...'`, and dynamic `import('...')`.
const SPEC_RES = [
  /\bfrom\s*['"]([^'"]+)['"]/g,
  /\bimport\s+['"]([^'"]+)['"]/g,
  /\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
];

function importsOf(file) {
  const text = readFileSync(file, 'utf8');
  const specs = [];
  for (const re of SPEC_RES) {
    for (const m of text.matchAll(re)) {
      if (m[1]) specs.push(m[1]);
    }
  }
  return specs;
}

const all = walk(SRC);
const tests = all.filter((f) => /\.test\.[tj]sx?$/.test(f));
const sources = all.filter((f) => !/\.test\.[tj]sx?$/.test(f));

// Reachable from the application entry point only.
const reachable = new Set();
const queue = ENTRIES.map((e) => resolve(e));
while (queue.length) {
  const file = queue.pop();
  if (!file || reachable.has(file)) continue;
  reachable.add(file);
  for (const spec of importsOf(file)) {
    const target = resolveSpec(spec, file);
    if (target && !reachable.has(target)) queue.push(target);
  }
}

// Files referenced by test files (directly or transitively).
const testReached = new Set();
const tqueue = [...tests];
while (tqueue.length) {
  const file = tqueue.pop();
  if (!file) continue;
  for (const spec of importsOf(file)) {
    const target = resolveSpec(spec, file);
    if (target && !testReached.has(target)) {
      testReached.add(target);
      tqueue.push(target);
    }
  }
}

const r = (f) => relative(resolve('.'), f);
const deadEverywhere = sources.filter((f) => !reachable.has(f) && !testReached.has(f));
const testOnly = sources.filter((f) => !reachable.has(f) && testReached.has(f));
const untested = sources.filter((f) => reachable.has(f) && !testReached.has(f));

console.log(`source files: ${sources.length}, test files: ${tests.length}`);
console.log(`reachable from main.tsx: ${reachable.size}\n`);

console.log(`== DEAD: unreachable from app AND from tests (${deadEverywhere.length}) ==`);
deadEverywhere.map(r).sort().forEach((f) => console.log('  ' + f));

console.log(`\n== TEST-ONLY: only reachable from a test (${testOnly.length}) ==`);
testOnly.map(r).sort().forEach((f) => console.log('  ' + f));

console.log(`\n== IN APP BUT NO TEST TOUCHES IT (${untested.length}) ==`);
untested.map(r).sort().forEach((f) => console.log('  ' + f));
