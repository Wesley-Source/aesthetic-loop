#!/usr/bin/env bash
# doctor.sh — valida o ambiente ANTES da 1ª rodada (o setup quebrado é onde
# skills morrem). Falhou um passo → a mensagem diz qual custo de setup daquele
# passo (ver README, seção "quanto setup o SEU projeto precisa").
#
# Uso: bash tools/doctor.sh <url_do_alvo>
# Exit: 0 = tudo ok; 1 = algum passo falhou.
set -u
URL="${1:-}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAILED=0

say()  { echo "doctor: $*"; }
fail() { echo "doctor: FAIL — $*"; FAILED=1; }

# 1. Git disponível + repo
if ! command -v git >/dev/null 2>&1; then
  fail "git não encontrado. Custo: sem git não há ratchet — instale git (apt install git)."
elif ! git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  say "ok: git presente (fora de repo — o loop faz git init no alvo, isso é normal)"
else
  say "ok: repo git em $REPO"
  if [ -n "$(git -C "$REPO" status --porcelain 2>/dev/null | head -5)" ]; then
    say "aviso: repo sujo — o loop faz stash do WIP no pré-flight (karpathy-loop herdado)"
  fi
fi

# 2. Playwright/Chromium
cd "$REPO"
if node -e "const {chromium}=require('playwright'); chromium.launch({headless:true}).then(b=>b.close()).then(()=>process.exit(0)).catch(()=>process.exit(1))" 2>/dev/null; then
  say "ok: Playwright + Chromium lançam headless"
else
  fail "Playwright/Chromium não funciona. Custo: npm install && npx playwright install chromium (~150 MB download, 1×)."
fi

# 3. Fontes via fc-list (I3: fonte ausente MUDA a tipografia que o juiz julga)
if command -v fc-list >/dev/null 2>&1; then
  NFONTS=$(fc-list | wc -l)
  if [ "$NFONTS" -lt 5 ]; then
    fail "só $NFONTS fontes no sistema — render vai cair em fallback. Custo: apt install fonts-dejavu fonts-liberation (+ as fontes do SEU projeto)."
  else
    say "ok: fontconfig com $NFONTS fontes"
    if [ -n "${AESTHETIC_REQUIRED_FONTS:-}" ]; then
      for f in ${AESTHETIC_REQUIRED_FONTS//,/ }; do
        if ! fc-list | grep -qi "$f"; then
          fail "fonte requerida do projeto ausente: '$f' — screenshot sem ela invalida o pairwise (I3)."
        else
          say "ok: fonte do projeto presente: $f"
        fi
      done
    fi
  fi
else
  fail "fc-list indisponível — não dá para verificar fontes. Custo: apt install fontconfig."
fi

# 4. Invariância de fixture/canário (I2/N3) — só se passaram URL
# Python com playwright: prefere o venv do repo, senão o python3 do sistema.
PY="python3"
if ! python3 -c "import playwright" >/dev/null 2>&1; then
  if [ -x "$REPO/.venv/bin/python" ] && "$REPO/.venv/bin/python" -c "import playwright" >/dev/null 2>&1; then
    PY="$REPO/.venv/bin/python"
    say "ok: usando $PY (playwright disponível no venv do repo)"
  else
    fail "python3 sem playwright. Custo: pip install playwright && playwright install chromium (ou crie .venv no repo)."
  fi
fi
if [ -n "$URL" ] && "$PY" -c "import playwright" >/dev/null 2>&1; then
  if OUT=$("$PY" "$REPO/tools/fixture_hash.py" --url "$URL" --canary 2>&1) && [ "$OUT" = "PASS" ]; then
    say "ok: render determinístico (canário 2× = mesmo hash)"
  else
    fail "página não determinística: $OUT — conteúdo dinâmico invalida o pairwise. Custo: congele fixtures (snapshot real do backend, nunca sintético) e rode atrás de server estático."
  fi

  # 5. Throughput real da API do painel (I3: assinatura ≠ ilimitado)
  if [ -n "${ZAI_API_KEY:-}" ]; then
    T0=$(date +%s%N)
    if HTTP=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 \
        "${ZAI_API_BASE:-https://api.z.ai/api/paas/v4}/chat/completions" \
        -H "Authorization: Bearer $ZAI_API_KEY" -H "Content-Type: application/json" \
        -d '{"model":"glm-4.7","messages":[{"role":"user","content":"reply with the single word: ok"}],"max_tokens":5}'); then
      T1=$(date +%s%N)
      MS=$(( (T1 - T0) / 1000000 ))
      if [ "$HTTP" = "200" ]; then
        say "ok: API do painel respondeu 200 em ${MS}ms — meça throughput do SEU plano antes de runs longos (rate limit estrangula 60+ chamadas/run)"
      else
        fail "API do painel respondeu HTTP $HTTP — verifique chave/créditos antes de gastar."
      fi
    else
      fail "API do painel inacessível (timeout/rede)."
    fi
  else
    say "aviso: ZAI_API_KEY não definida — o pairwise não rodará (gates funcionam)."
  fi
else
  say "pule: passe <url_do_alvo> para validar canário de render e throughput da API"
fi

if [ "$FAILED" -ne 0 ]; then
  echo "doctor: FALHOU — resolva os itens acima (o README diz quanto setup o SEU projeto precisa)."
  exit 1
fi
echo "doctor: PASS"
