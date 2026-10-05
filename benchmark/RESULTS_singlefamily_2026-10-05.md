# WiserUI-Bench — Run de Validação Single-Family (RESULTADOS)

**Data do run:** 2026-10-05/06 · **Executor:** Hermes (auditável em
`/opt/data/cache/scratch/wiserui_*.{json,jsonl,py}`)

**Classificação: USO PESSOAL.** Por definição do protocolo (§2), single-family
NÃO publica evidência da tese anti-Karpathy ("GLM julgando GLM"). Os números
abaixo são válidos para a decisão interna: **o juiz GLM serve para o loop do
dono?** Nada aqui pode virar claim público de marketing.

## Configuração (congelada, idêntica ao dev)

- Juiz: `glm-5.3-flash`, temp 0.2, thinking disabled, max_tokens 2000
- Prompt: `judge/prompt_pairwise.md` EXATAMENTE como commitado — **0 iterações
  de ajuste** (o orçamento do protocolo permitia 2; nenhuma foi usada)
- Personas: designer / apressado / dev-legado · AB+BA obrigatório
- Fonte: WiserUI-Bench (jeochris/wiserui-bench, 300 pares goodui.org)
- Split: seed 20261005, 70/30 → dev 208, held-out 90
- Exclusões declaradas ANTES do held-out: 92 imagens corrompidas (anti-bot
  HTML na origem), por par — dev efetivo 160, held-out efetivo 74
- Contagem: hit = veredito consistente nas 2 ordens escolhendo B (=win;
  codificação do runner: A=lose, B=win)

## Resultados

| Split | n julg. | Acurácia c/ swap-filter | IC95 Wilson |
|---|---|---|---|
| Dev | 158 consistentes | **82,9%** | [76,3%, 88,0%] |
| **Held-out** | 47 consistentes | **87,2%** | **[74,8%, 94,0%]** |

- Held-out por persona: dev-legado 94% · apressado 88% · designer 79%
- Sem swap-filter (só ordem AB): held-out 70,1% — a diferença de 17pp é a
  demonstração direta de por que o protocolo exige AB+BA
- Swap-inconsistência: dev 59%, held-out 45% dos pares decidíveis — o juiz
  fica genuinamente dividido nesses (distribuição de posição é simétrica;
  não é viés A/B de ordem)
- TIE: 140 (dev) / 73 (held-out) — tratado como não-aceite (revert), nunca
  como moeda forçada

## Veredito contra o critério pré-registrado (§5)

- ≥65% com IC inteiro acima de 55%: **PASSA** (87,2%, mínimo do IC 74,8%)
- Consequência: **loop autônomo liberado para uso pessoal do dono**, com as
  salvaguardas do modo single-family (meta-juiz a cada 3 rodadas, voto
  humano obrigatório no FIM antes de merge)
- Pivô assistido NÃO acionado

## Ressalvas registradas (honestidade plena)

1. **n do held-out caiu de 90 para 74 pares** (20 pares × 2 imagens perdidas
   para anti-bot). O IC ficou mais largo que o planejado (~±10pp vs ±6,5pp).
   Ainda assim o mínimo do IC (74,8%) fica 20pp acima da linha de 55%.
2. **Single-family**: viés de família entre juiz e builder não é medido por
   este run — é exatamente o que a validação multi-família medirá, quando
   houver 2ª família.
3. O dataset é web-first (252/300 web, 48 mobile) — generalização para
   mobile-first puro é extrapolada.
4. `glm-5.3-flash` é um snapshot; mudança de pin exige smoke re-run (I5).
