#!/usr/bin/env bash
# gate_contrast.sh — Gate 3: contraste WCAG AA (axe color-contrast).
# Wrapper fino sobre gate_axe.mjs filtrando a regra color-contrast (< 4.5:1).
# Uso idêntico ao gate_axe.mjs:
#   capturar champion:  bash gates/gate_contrast.sh --url <champion> --out champ_contrast.json
#   julgar challenger:  bash gates/gate_contrast.sh --url <challenger> --out res.json --baseline champ_contrast.json
# Contrato: 1 linha — "PASS" | "FAIL:axe:color-contrast+N" | "FAIL:axe:infra:<motivo>".
set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec node "$DIR/gate_axe.mjs" --rules color-contrast "$@"
