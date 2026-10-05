#!/usr/bin/env bash
# gate_build.sh — Gate 1 (mais barato): build/compile do projeto-alvo.
# Contrato: imprime exatamente 1 linha — "PASS" ou "FAIL:build:<motivo>".
# Exit: 0 = PASS, 1 = FAIL (produto), 2 = erro de infra (retryável, não conta p/ FALHAS).
set -u

fail() { echo "FAIL:build:$1"; exit 1; }
infra() { echo "FAIL:build:infra:$1"; exit 2; }

# Comando de build explícito vence (defina AESTHETIC_BUILD_CMD no projeto-alvo).
if [ -n "${AESTHETIC_BUILD_CMD:-}" ]; then
  if ! command -v bash >/dev/null 2>&1; then infra "no shell"; fi
  if ! eval "$AESTHETIC_BUILD_CMD" >/tmp/aesthetic_build.log 2>&1; then
    tail -5 /tmp/aesthetic_build.log | tr '\n' ' ' | cut -c1-160 | fail "$(cat -)"
  fi
  echo "PASS"
  exit 0
fi

# Projeto Node com script "build".
if [ -f package.json ] && node -e "const p=require('./package.json'); process.exit((p.scripts&&p.scripts.build)?0:1)" 2>/dev/null; then
  if ! npm run build --silent >/tmp/aesthetic_build.log 2>&1; then
    tail -5 /tmp/aesthetic_build.log | tr '\n' ' ' | cut -c1-160 | fail "$(cat -)"
  fi
  echo "PASS"
  exit 0
fi

# Projeto Python com pyproject/setuptools: compile-check dos .py como build mínimo.
if [ -f pyproject.toml ] || [ -f setup.py ]; then
  PY_ERR=$(python3 -m compileall -q . 2>&1 | head -3)
  if [ -n "$PY_ERR" ]; then fail "$(echo "$PY_ERR" | tr '\n' ' ' | cut -c1-160)"; fi
  echo "PASS"
  exit 0
fi

# Página estática (sem toolchain): nada a compilar — gate trivialmente passa.
echo "PASS"
exit 0
