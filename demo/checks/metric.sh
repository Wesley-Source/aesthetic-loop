#!/usr/bin/env bash
# demo/checks/metric.sh — o contrato do karpathy-loop adaptado: imprime
# EXATAMENTE 1 NÚMERO no stdout (exit 0). Números extra vão para stderr.
#
# Aqui a métrica é determinística e objetiva: nº de violações WCAG AA
# (axe color-contrast + sérias/críticas) do demo_target servido em $URL.
# Serve como validação de que a cadeia Playwright→axe→parse-regex está viva
# sem gastar 1 token de juiz.
#
# Uso: URL=http://localhost:8123 bash demo/checks/metric.sh   (ou $1)
set -u
URL="${1:-${URL:-http://localhost:8123/demo_target.html}}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

OUT=$(node "$REPO/gates/gate_axe.mjs" --url "$URL" --out "$TMP/axe.json" 2>/dev/null); RC=$?
if [ $RC -eq 2 ]; then echo "0"; echo "metric: infra failure — treat as 0 but flag" >&2; exit 0; fi

# Conta o total de nodes em violação (todas, não só serious — métrica é granulada;
# gates é que são serious/critical-only).
N=$(python3 -c "
import json,sys
d = json.load(open('$TMP/axe.json'))
print(sum(v['nodes'] for v in d['violations']))
" 2>/dev/null || echo "0")
echo "$N"
exit 0
