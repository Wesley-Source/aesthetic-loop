#!/usr/bin/env python3
"""dom_invariance.py — gate de invariância DOM entre screenshots (patch I1).

Barato e sem LLM: para um mesmo estado, compara challenger vs champion o
CONJUNTO de elementos interativos visíveis/clicáveis e o overflow do body.
Pega modal quebrado, overlay morto, botão que sumiu, scroll horizontal
acidental — exatamente as regressões que o screenshot do estado errado
esconderia. Custo: 1 script Playwright, segundos.

Uso: python3 tools/dom_invariance.py --champion URL --challenger URL [--state-dir states/]
Saída: 1 linha "PASS" | "FAIL:dom:<detalhe>" | "FAIL:dom:infra:<motivo>" (mesmo contrato dos gates).
Exit: 0 PASS; 1 FAIL (produto); 2 infra.
"""
import argparse
import json
import sys
from pathlib import Path

SNAPSHOT_JS = """() => {
  const cs = el => getComputedStyle(el);
  const visible = [...document.querySelectorAll('body *')].filter(e => {
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && cs(e).visibility !== 'hidden' && cs(e).display !== 'none';
  });
  const interactive = visible.filter(e => {
    const tag = e.tagName.toLowerCase();
    return tag === 'a' || tag === 'button' || tag === 'input' || tag === 'select'
      || tag === 'textarea' || tag === 'summary' || e.getAttribute('role') === 'button'
      || e.getAttribute('role') === 'tab' || e.getAttribute('tabindex') !== null;
  });
  const sig = interactive.map(e => {
    const r = e.getBoundingClientRect();
    const label = (e.getAttribute('aria-label') || e.textContent || e.getAttribute('placeholder') || '')
      .trim().slice(0, 40).replace(/\\s+/g, ' ');
    return `${e.tagName}:${label}:${Math.round(r.width)}x${Math.round(r.height)}`;
  }).sort();
  // overlays/modais presentes (dialog aberto, aria-modal, position fixed cobrindo tela)
  const overlays = visible.filter(e => {
    const s = cs(e);
    const r = e.getBoundingClientRect();
    return (e.tagName === 'DIALOG' && e.open) || s.position === 'fixed'
      && r.width > window.innerWidth * 0.5 && r.height > window.innerHeight * 0.5;
  }).map(e => e.tagName + ':' + (e.id || e.className || '').toString().slice(0, 30)).sort();
  return {
    interactive_sig: sig,
    n_interactive: sig.length,
    overlays: overlays,
    body_overflow_x: document.documentElement.scrollWidth > window.innerWidth + 1,
    scroll_height: document.documentElement.scrollHeight,
  };
}"""


def snapshot(url: str) -> dict:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        page.goto(url, wait_until="networkidle", timeout=30000)
        snap = page.evaluate(SNAPSHOT_JS)
        browser.close()
    return snap


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--champion", required=True)
    ap.add_argument("--challenger", required=True)
    ap.add_argument("--tolerance", type=int, default=2,
                    help="nº de elementos interativos que podem diferecer sem falhar")
    args = ap.parse_args()
    try:
        champ = snapshot(args.champion)
        chall = snapshot(args.challenger)
    except Exception as e:
        print(f"FAIL:dom:infra:{str(e)[:120]}")
        sys.exit(2)

    problems = []
    if chall["body_overflow_x"] and not champ["body_overflow_x"]:
        problems.append("novo overflow horizontal")
    set_c, set_l = set(champ["interactive_sig"]), set(chall["interactive_sig"])
    removed, added = set_c - set_l, set_l - set_c
    if len(removed) > args.tolerance:
        problems.append(f"{len(removed)} elementos interativos sumiram: {sorted(removed)[:3]}")
    if len(added) > args.tolerance:
        problems.append(f"{len(added)} elementos interativos novos: {sorted(added)[:3]}")
    if len(chall["overlays"]) > len(champ["overlays"]) + 1:
        problems.append(f"overlays novos inesperados: {chall['overlays'][:3]}")
    if abs(chall["scroll_height"] - champ["scroll_height"]) > max(400, 0.5 * champ["scroll_height"]):
        problems.append(f"altura da página mudou >50%: {champ['scroll_height']}→{chall['scroll_height']}")

    if problems:
        print("FAIL:dom:" + "; ".join(problems)[:200])
        sys.exit(1)
    print("PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
