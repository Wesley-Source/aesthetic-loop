#!/usr/bin/env python3
"""fixture_hash.py — hash do champion por rodada (patch I2).

Pré-flight captura o hash do HTML renderizado do champion; toda rodada
re-checa. Mudou → a RUN É INVÁLIDA (conteúdo dinâmico — data relativa, avatar,
contagem — invalida o pairwise silenciosamente). Nada de "continua e torce".

Também serve de canário de comparabilidade (N3): `--canary` renderiza o MESMO
estado 2× e exige hashes iguais — diferente → a página não é elegível para
modo automático.

Uso:
  capturar:   python3 tools/fixture_hash.py --url http://localhost:3000 --write .aesthetic_fixture_hash
  verificar:  python3 tools/fixture_hash.py --url http://localhost:3000 --check .aesthetic_fixture_hash
  canário:    python3 tools/fixture_hash.py --url http://localhost:3000 --canary
Saída (--check/--canary): 1 linha "PASS" | "FAIL:fixture:<motivo>" | "FAIL:fixture:infra:<motivo>".
Exit: 0 PASS; 1 FAIL (produto/página não elegível); 2 infra.
"""
import argparse
import hashlib
import sys
from pathlib import Path

FREEZE_JS = """() => {
  // Congela tudo que muda sozinho, para o HTML ser determinístico:
  document.querySelectorAll('time, [datetime]').forEach(e => { e.textContent = 'FROZEN_TIME'; });
  document.querySelectorAll('img').forEach(i => { i.src = 'FROZEN_IMG'; i.removeAttribute('srcset'); });
  document.querySelectorAll('[data-timestamp], [data-relative-time]').forEach(e => { e.textContent = 'FROZEN_TS'; });
  return document.documentElement.outerHTML;
}"""


def rendered_html(url: str) -> str:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800},
                                reduced_motion="reduce")
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(300)
        html = page.evaluate(FREEZE_JS)
        browser.close()
    return html


def h(url: str) -> str:
    return hashlib.sha256(rendered_html(url).encode()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--write")
    ap.add_argument("--check")
    ap.add_argument("--canary", action="store_true")
    args = ap.parse_args()

    try:
        if args.canary:
            h1, h2 = h(args.url), h(args.url)
            if h1 != h2:
                print("FAIL:fixture:canary: 2 renders do mesmo estado produziram "
                      "hashes diferentes — página não elegível para modo automático")
                sys.exit(1)
            print("PASS")
            sys.exit(0)
        if args.write:
            digest = h(args.url)
            Path(args.write).write_text(digest + "\n")
            print(digest)
            sys.exit(0)
        if args.check:
            stored = Path(args.check).read_text().strip()
            current = h(args.url)
            if current != stored:
                print("FAIL:fixture:hash mudou desde a captura — run INVÁLIDA "
                      "(conteúdo dinâmico na página-alvo); re-congele fixtures e recomece")
                sys.exit(1)
            print("PASS")
            sys.exit(0)
        print(h(args.url))
    except Exception as e:
        print(f"FAIL:fixture:infra:{str(e)[:120]}")
        sys.exit(2)


if __name__ == "__main__":
    main()
