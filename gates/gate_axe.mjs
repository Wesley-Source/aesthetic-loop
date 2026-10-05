#!/usr/bin/env node
// gate_axe.mjs — Gate 2: axe-core via Playwright.
// Roda axe na página e compara violações serious/critical contra o champion.
// Uso:
//   capturar champion:  node gates/gate_axe.mjs --url <champion_url> --out champ_axe.json
//   julgar challenger:  node gates/gate_axe.mjs --url <challenger_url> --out res.json --baseline champ_axe.json
//   só regras exatas:   --rules color-contrast (usado por gate_contrast.sh)
// Contrato: exatamente 1 linha — "PASS" | "FAIL:axe:<regra>+N" | "FAIL:axe:infra:<motivo>".
// Exit: 0 = PASS, 1 = FAIL (produto), 2 = infra (retryável, não conta p/ FALHAS).
import { createRequire } from 'module';
import { readFileSync, writeFileSync } from 'fs';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const args = process.argv.slice(2);
const arg = (name, def = null) => {
  const i = args.indexOf(name);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : def;
};
const url = arg('--url');
const out = arg('--out', 'axe_result.json');
const rulesFilter = arg('--rules'); // CSV de rule ids, ex.: "color-contrast"
const baselinePath = arg('--baseline');
if (!url) { console.error('usage: gate_axe.mjs --url URL [--out f.json] [--baseline b.json] [--rules r1,r2]'); process.exit(2); }

let axeSource;
try {
  axeSource = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
} catch (e) {
  console.log('FAIL:axe:infra:axe-core not installed (npm install in repo root)');
  process.exit(2);
}

let browser;
try {
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 800 },
    reducedMotion: 'reduce',
    deviceScaleFactor: 1,
  });
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  await page.addScriptTag({ content: axeSource });
  const axeOptions = rulesFilter ? { runOnly: { type: 'rule', values: rulesFilter.split(',').map(s => s.trim()) } } : {};
  const results = await page.evaluate(async (opts) => await window.axe.run(document, opts), axeOptions);
  await browser.close();

  // Mantém apenas serious/critical — barulho "moderate/minor" não bloqueia (design §2.2).
  let violations = results.violations
    .filter(v => !rulesFilter && v.impact !== 'serious' && v.impact !== 'critical' ? false : true)
    .map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.length }));

  let verdict = 'PASS', detail = '';
  if (baselinePath) {
    let baseline = [];
    try {
      baseline = JSON.parse(readFileSync(baselinePath, 'utf8')).violations || [];
    } catch (e) {
      console.log('FAIL:axe:infra:baseline unreadable: ' + baselinePath);
      process.exit(2);
    }
    const baseCount = Object.fromEntries(baseline.map(v => [v.id, v.nodes]));
    const regressions = violations.filter(v => v.nodes > (baseCount[v.id] || 0));
    if (regressions.length > 0) {
      detail = regressions.map(v => `${v.id}+${v.nodes - (baseCount[v.id] || 0)}`).join(',');
      verdict = `FAIL:axe:${detail}`;
    }
  } else if (violations.length > 0 && rulesFilter) {
    // Modo regra única sem baseline = CAPTURA (medição do champion): violações
    // pré-existentes do champion NÃO falham a captura — o gate julga REGRESSÃO
    // do challenger contra esse baseline (design §2.2: "novo par < 4.5:1").
    // Página cujo champion já viola AA: registre no log; o ratchet melhora a
    // partir do estado atual em vez de bloquear o loop inteiro.
    console.error(`capture: ${violations.reduce((a, v) => a + v.nodes, 0)} nodes em violação no baseline (não-bloqueante)`);
  }

  writeFileSync(out, JSON.stringify({ url, rules: rulesFilter, violations }, null, 2));
  console.log(verdict);
  process.exit(verdict === 'PASS' ? 0 : 1);
} catch (e) {
  if (browser) { try { await browser.close(); } catch {} }
  console.log('FAIL:axe:infra:' + String(e.message || e).slice(0, 140));
  process.exit(2);
}
