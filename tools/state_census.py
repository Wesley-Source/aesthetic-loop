#!/usr/bin/env python3
"""state_census.py — censo de estados por crawl dirigido (patch I1).

NÃO confie em lista manual de estados: o builder que muda um token
compartilhado quebra exatamente o estado que ninguém fotografou (modal aberto,
toast, estado vazio, overflow). Este script descobre e fotografa o conjunto:

  1. página inicial desktop (1280×800);
  2. viewport mobile (390×844) — quebras de layout;
  3. todos os links internos encontrados na página inicial (dirigido, 1 nível);
  4. todos os <button>/<details>/[role=tab] clicáveis — captura ANTES/DEPOIS
     do clique (modal, accordion, dropdown);
  5. estado "vazio": intercepta requisições de dados com resposta vazia
     (route abort em XHR/fetch de API) e fotografa;
  6. conteúdo longo: injeta texto em inputs/parágrafos para forçar wrap
     (overflow com conteúdo longo).

O conjunto é congelado por run em <outdir>/manifest.json — o pairwise usa
exatamente esse conjunto; novos estados NO MEIO do run invalidam a run
(I2: fixture/champion congelado).

Uso: python3 tools/state_census.py --url http://localhost:3000 --out states/
Exit: 0 ok; 2 infra.
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", default="states")
    ap.add_argument("--max-links", type=int, default=10)
    args = ap.parse_args()
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    states = []  # {id, file, how, viewport, selector_or_url}
    base = args.url

    def shot(page, sid, how, extra=None):
        fname = f"{sid}.png"
        page.screenshot(path=str(outdir / fname), full_page=False)
        states.append({"id": sid, "file": fname, "how": how, **(extra or {})})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # --- desktop base ---
        page = browser.new_page(viewport={"width": 1280, "height": 800},
                                reduced_motion="reduce")
        try:
            page.goto(base, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"INFRA: falha ao abrir {base}: {e}", file=sys.stderr)
            sys.exit(2)
        shot(page, "desktop-home", "initial desktop viewport")

        # --- links internos (1 nível, dirigido) ---
        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.href).filter(h => h.startsWith(location.origin))")
        seen = set()
        for h in list(dict.fromkeys(links))[: args.max_links]:
            if h == base or h in seen or urlparse(h).fragment:
                continue
            seen.add(h)
            sid = "page-" + (urlparse(h).path.strip("/").replace("/", "-") or "root")[:40]
            try:
                page.goto(h, wait_until="networkidle", timeout=20000)
                shot(page, sid, f"internal link {h}")
            except Exception:
                continue  # link morto não é estado

        # --- viewport mobile ---
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(base, wait_until="networkidle", timeout=20000)
        shot(page, "mobile-home", "mobile viewport 390x844",
             {"viewport": "390x844"})
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(base, wait_until="networkidle", timeout=20000)

        # --- toggles: modal/accordion/dropdown (antes/depois do clique) ---
        clickables = page.query_selector_all("button, details summary, [role=tab]")
        for i, el in enumerate(clickables[:20]):
            try:
                if not el.is_visible():
                    continue
                label = ((el.get_attribute("aria-expanded") is not None) or
                         (el.evaluate("e => e.tagName") == "SUMMARY"))
                before_open = el.get_attribute("aria-expanded")
                el.click(timeout=3000)
                page.wait_for_timeout(250)
                sid = f"toggle-{i}"
                shot(page, sid, f"after click on button#{i} "
                     f"('{(el.inner_text() or '')[:30].strip()}')")
                # volta ao estado fechado se conseguimos detectar expansão
                if before_open is not None or label:
                    try:
                        el.click(timeout=2000)
                        page.wait_for_timeout(150)
                    except Exception:
                        page.goto(base, wait_until="networkidle", timeout=20000)
            except Exception:
                continue

        # --- estado vazio: aborta XHR/fetch de dados ---
        def route_abort(route):
            if any(k in route.request.url for k in ("/api/", "/graphql", "json")):
                route.fulfill(status=200, content_type="application/json", body="[]")
            else:
                route.continue_()
        page.route("**/*", route_abort)
        page.goto(base, wait_until="networkidle", timeout=20000)
        shot(page, "empty-data", "API responses forced to empty []")
        page.unroute("**/*")

        # --- conteúdo longo (overflow/wrap) ---
        page.goto(base, wait_until="networkidle", timeout=20000)
        page.evaluate("""() => {
          const filler = 'palavramuitolonga '.repeat(40);
          document.querySelectorAll('p, h1, h2, h3, td, th').forEach(e => {
            e.dataset.aestheticOrig = e.textContent;
            e.textContent = (e.textContent.slice(0, 20) + ' ' + filler).slice(0, 400);
          });
          document.querySelectorAll('input[type=text], input:not([type])').forEach(e => { e.value = filler; });
        }""")
        page.wait_for_timeout(200)
        shot(page, "long-content", "forced long text (wrap/overflow probe)")

        browser.close()

    manifest = {"base_url": base, "frozen_for_run": True, "states": states}
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(json.dumps({"states_found": len(states), "manifest": str(outdir / 'manifest.json')}))


if __name__ == "__main__":
    main()
