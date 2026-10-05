#!/usr/bin/env bash
# run_gates.sh — Orquestra os gates determinísticos em ordem de custo,
# short-circuit na primeira falha. SLOP NÃO É GATE (patch B2): o slop-score
# é sinal logado + rubrica do juiz (tools/slop_signal.py), nunca bloqueia.
#
# Uso: bash gates/run_gates.sh <champion_url> <challenger_url> [workdir_tmp]
# Contrato: exatamente 1 linha final — "PASS" | "FAIL:<gate>:<detalhe>".
#           Linhas "gate <nome>: ..." acima são log de progresso (stderr não).
# Exit: 0 = todos passaram; 1 = falha de produto; 2 = falha de infra (retry com backoff — NÃO conta p/ FALHAS→FIM).
set -u

CHAMP="${1:-}"; CHALL="${2:-}"; TMP="${3:-$(mktemp -d)}"
if [ -z "$CHALL" ]; then echo "usage: run_gates.sh <champion_url> <challenger_url> [tmpdir]" >&2; echo "FAIL:gates:usage"; exit 1; fi
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$TMP"

run_gate() { # <nome> <cmd...> — propaga exit 0/1/2; imprime log de progresso
  local name="$1"; shift
  echo "gate $name: running..." >&2
  local out rc
  out=$("$@" 2>/tmp/aesthetic_gate_err.log); rc=$?
  echo "$out"
  [ -s /tmp/aesthetic_gate_err.log ] && head -2 /tmp/aesthetic_gate_err.log >&2
  return $rc
}

# 1. BUILD (mais barato)
OUT=$(run_gate build bash "$DIR/gate_build.sh"); RC=$?
echo "gate build: $OUT" >&2
if [ $RC -eq 2 ]; then echo "FAIL:build:infra:${OUT#FAIL:build:}"; exit 2; fi
if [ $RC -ne 0 ]; then echo "$OUT"; exit 1; fi

# 2. AXE — baseline do champion, depois challenger comparado ao baseline
OUT=$(run_gate axe-capture node "$DIR/gate_axe.mjs" --url "$CHAMP" --out "$TMP/champ_axe.json"); RC=$?
echo "gate axe-capture(champion): $OUT" >&2
if [ $RC -ne 0 ]; then echo "$OUT"; exit $RC; fi
OUT=$(run_gate axe node "$DIR/gate_axe.mjs" --url "$CHALL" --out "$TMP/chall_axe.json" --baseline "$TMP/champ_axe.json"); RC=$?
echo "gate axe(challenger): $OUT" >&2
if [ $RC -eq 2 ]; then echo "FAIL:axe:infra:${OUT#FAIL:axe:}"; exit 2; fi
if [ $RC -ne 0 ]; then echo "$OUT"; exit 1; fi

# 3. CONTRASTE WCAG AA (color-contrast do axe)
OUT=$(run_gate contrast-capture bash "$DIR/gate_contrast.sh" --url "$CHAMP" --out "$TMP/champ_contrast.json"); RC=$?
echo "gate contrast-capture(champion): $OUT" >&2
if [ $RC -ne 0 ]; then echo "$OUT"; exit $RC; fi
OUT=$(run_gate contrast bash "$DIR/gate_contrast.sh" --url "$CHALL" --out "$TMP/chall_contrast.json" --baseline "$TMP/champ_contrast.json"); RC=$?
echo "gate contrast(challenger): $OUT" >&2
if [ $RC -eq 2 ]; then echo "FAIL:contrast:infra:${OUT#FAIL:axe:}"; exit 2; fi
if [ $RC -ne 0 ]; then echo "FAIL:contrast:${OUT#FAIL:axe:}"; exit 1; fi

echo "PASS"
exit 0
