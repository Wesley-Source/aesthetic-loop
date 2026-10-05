#!/usr/bin/env python3
"""slop_signal.py — slop-score da UI como SINAL, não gate (patch B2).

Imprime exatamente 1 número (0–100) no stdout: quanto maior, mais a página
carrega o pacote "default de IA" (tells do discourse 2026). O número:
  - entra no LOG da rodada (ex.: "slop 41→38");
  - vira insumo da rubrica do juiz (ver judge/prompt_pairwise.md, seção
    "rubrica negativa" — custo zero, não-gameable por gate);
  - NUNCA bloqueia um keep sozinho. Motivo: detector de tells hardcodado é
    trivialmente gameable pelo builder e pune escolhas humanas legítimas
    (cream + serif também é escolha real de gente). Se um dia virar gate,
    ANTES meça o ruído (mesmo champion 5×) e fixe δ = 2–3× o ruído observado.

Heurísticas aqui são estruturais (CSS computado via Playwright), não lista de
banned-hex. Uso:
  python3 tools/slop_signal.py --url http://localhost:3000 [--json]
"""
import argparse
import json
import sys
from pathlib import Path

def collect_stats() -> dict:
    from playwright.sync_api import sync_playwright  # noqa
    args = _parse()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        page.goto(args.url, wait_until="networkidle", timeout=30000)
        stats = page.evaluate("""() => {
          const els = [...document.querySelectorAll('body *')];
          const cs = el => getComputedStyle(el);
          const visible = els.filter(e => { const r = e.getBoundingClientRect(); const s = cs(e);
            return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; });
          const count = (pred) => visible.filter(pred).length;
          const roundedAll = (el) => { const s = cs(el);
            const tl = parseFloat(s.borderTopLeftRadius) || 0, tr = parseFloat(s.borderTopRightRadius) || 0,
                  bl = parseFloat(s.borderBottomLeftRadius) || 0, br = parseFloat(s.borderBottomRightRadius) || 0;
            return Math.min(tl,tr,bl,br) >= 16; };
          const sameShadow = {}; let shadowDominant = 0;
          const shadows = visible.map(e => cs(e).boxShadow).filter(s => s && s !== 'none');
          for (const s of shadows) { sameShadow[s] = (sameShadow[s]||0)+1; }
          const shadowMax = Math.max(0, ...Object.values(sameShadow));
          const fonts = {}; for (const e of visible) { const f = cs(e).fontFamily; fonts[f] = (fonts[f]||0)+1; }
          const fontMax = Math.max(0, ...Object.values(fonts));
          const fontMaxKey = Object.keys(fonts).find(k => fonts[k] === fontMax) || '';
          const weights = {}; for (const e of visible) { const w = cs(e).fontWeight; weights[w]=(weights[w]||0)+1; }
          const lightWeight = (parseFloat(Object.keys(weights).sort((a,b)=>weights[b]-weights[a])[0]||'400') <= 400);
          const r = document.body.getBoundingClientRect();
          const children = [...document.body.children].map(e=>e.getBoundingClientRect());
          const usedWidth = Math.max(0, ...children.map(c=>c.left+c.right)) - Math.min(0, ...children.map(c=>c.left));
          return {
            n_visible: visible.length,
            pct_rounded: count(roundedAll) / Math.max(1, visible.length),
            pct_grad_bg: count(e => cs(e).backgroundImage.includes('gradient')) / Math.max(1, visible.length),
            pct_low_contrast_accent: count(e => { const c = cs(e).color.match(/\\d+(\\.\\d+)?/g)||[0,0,0];
              const [rr,gg,bb] = c.map(Number); const lum = 0.2126*rr+0.7152*gg+0.0722*bb;
              return lum > 175 && lum < 235; }) / Math.max(1, visible.length),
            shadow_dominance: shadowMax / Math.max(1, shadows.length),
            system_font_dominance: fontMax / Math.max(1, visible.length),
            system_font_is_default: /(-apple-system|system-ui|Inter|Segoe UI|Roboto|Helvetica Neue)/i.test(fontMaxKey),
            light_weight_dominant: lightWeight,
            emoji_as_icon: count(e => /^\\p{Extended_Pictographic}{1,2}$/u.test(e.textContent.trim())) / Math.max(1, visible.length),
            body_overflow_x: document.documentElement.scrollWidth > window.innerWidth + 1,
            horizontal_dead_space_pct: Math.max(0, (r.width - usedWidth) / Math.max(1, r.width)),
          };
        }""")
        browser.close()
    return stats

def score(s: dict) -> float:
    """Ponderação declarada (somam 100). Cada tell vale o que vale — a rubrica
    do juiz continua sendo o árbitro final; este número é diagnóstico."""
    v = 0.0
    v += min(1, s["pct_rounded"] / 0.6) * 15          # cantos ≥16px em 60%+ dos elementos
    v += min(1, s["pct_grad_bg"] / 0.25) * 15         # gradientes decorativos espalhados
    v += min(1, s["pct_low_contrast_accent"] / 0.2) * 15  # pastel de baixo contraste como acento
    v += min(1, s["shadow_dominance"] / 0.8) * 10     # uma única sombra dominante (sem hierarquia)
    v += min(1, s["system_font_dominance"] / 0.9) * (15 if s["system_font_is_default"] else 5)
    if s["light_weight_dominant"]:
        v += 10
    v += min(1, s["emoji_as_icon"] / 0.05) * 10
    if s["body_overflow_x"]:
        v += 10
    return round(min(100, v), 1)

def _parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--json", action="store_true")
    return ap.parse_args()

if __name__ == "__main__":
    args = _parse()
    try:
        stats = collect_stats()
    except Exception as e:
        print(f"INFRA: {e}", file=sys.stderr)
        sys.exit(2)
    sc = score(stats)
    if args.json:
        print(json.dumps({"slop_score": sc, "stats": stats}, indent=2, ensure_ascii=False))
    else:
        print(sc)
