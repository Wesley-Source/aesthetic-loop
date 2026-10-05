---
name: aesthetic-loop
description: Loop agênico keep-or-revert para estética/UX — melhora a aparência
  de uma página por tempo limitado com juiz pairwise cego (screenshots apenas,
  ordem AB+BA), painel de 2–3 modelos de famílias distintas, gates
  determinísticos antes do juiz caro e revert automático de regressões. Use
  quando o usuário pedir para "deixar a UI mais bonita", "rodar o aesthetic
  loop" ou iterar estética sem score absoluto.
---

# Aesthetic Loop

Melhora a estética/UX de uma página-alvo por tempo limitado. Dois papéis:

- **Juiz PERSISTENTE**: orquestra, roda os gates, comuta o painel de juízes,
  decide keep/revert, guarda estado (champion, swap-rate, κ, contadores).
  NUNCA edita código e NUNCA vê a tela "por conta própria" — julga só pelos
  protocolos abaixo.
- **Builder DESCARTÁVEL** (subagente novo a cada rodada): faz UMA mudança
  visual pequena. Não roda gates, não julga, não commita.

**REGRA DE OURO: o builder nunca vê o veredito — só o screenshot do champion.**
O veredito (racional do painel, scores, viés detectado) fica no log do juiz.
O builder recebe apenas o screenshot atual, o brief de melhora e a direção
estética ainda-não-tentada do deck (`directions/deck.yaml`); assim ele não
mimetiza o gosto do juiz nem racionaliza regressões.

## Single-family mode — o modo padrão (qualquer família)

O loop funciona **com uma única família de modelo** — Z.ai/GLM, Claude,
Gemini, qualquer provedor que o usuário tenha. Não é um modo degradado: é
o modo primário do produto, com salvaguardas reforçadas, porque juiz e
builder compartilham o mesmo prior estético de RLHF (Panickssery et al.
2024 — cegueira a código não remove o viés de impressão estilística).

### Salvaguardas que o single-family exige (todas automáticas)

1. **Gates determinísticos mandam.** Build, axe, contraste WCAG e o meta-juiz
   decidem quase tudo; o pairwise intra-família é DESEMPATE entre candidatos
   que já passaram no chão objetivo — nunca a fonte da verdade.
2. **Meta-juiz acelerado**: a cada 3 rodadas (não 5). Family-bias acumula
   mais rápido sem contrapeso entre famílias.
3. **Voto humano obrigatório no FIM** antes de qualquer merge — e cada voto
   entra na calibração, que é o contrapeso real: com 10-20 pares seus, o
   juiz segue o SEU gosto, não o default da família.
4. **Sinal anti-slop na rubrica do juiz** (não-gate): o detector de slop não
   bloqueia, mas o prompt penaliza composição genérica — o contrapeso contra
   o gosto-médio-de-IA que o firewall de família faria no modo multi.

### O que o single-family NÃO permite

- **Publicar resultados como evidência da tese** anti-Karpathy: a crítica
  honesta é "GLM julga GLM". A validação WiserUI-Bench multi-família
  (benchmark/PROTOCOL.md) é o que dá licença para afirmações públicas.
- **Merges autônomos sem seu FIM-humano.** Multi-família: o meta-juiz pode
  aprovar sozinho com swap-rate/κ saudáveis. Single-family: seu voto no fim
  é parte do protocolo, não opcional.

### Upgrade para multi-família

`judge/panel.yaml` aceita N famílias com pin de versão. Adicionou uma segunda
família? O firewall por rodada liga sozinho (família do builder sai do
painel), o meta-juiz volta a cada 5 rodadas e o requisito de voto humano
no FIM cai para opcional.

## Temperatura do juiz: 0.2

Fixa em `judge/panel.yaml` (`judge_temperature: 0.2`), não 0 nem 1.0:
- temp 0 remove apenas ruído de amostragem, não viés (viés está nos pesos);
- com temp 0, inconsistência entre ordens AB/BA vira sistemática (sempre a
  mesma), e o swap deixa de filtrar ruído para descartar direções inteiras;
- 0.2 mantém o swap como filtro de ruído. Os limiares do meta-juiz
  (`swap_rate_min`, em `meta_judge.py`) DEVEM ser recalibrados medindo o
  baseline real do painel antes de fixar qualquer número — não use o 50% do
  design original sem medir.

## Entrada

- `alvo` — URL ou rota da página.
- `direção` — critério estético livre ("mais premium", "menos cara de IA");
  OBRIGATÓRIO perguntar se faltar. Vira o brief do builder + as personas.
- `duração_do_loop`, `iterações máx.` (cap 20), `objetivo` (opcional).

## Pré-flight (ordem fixa)

1. `git rev-parse --show-toplevel`; branch dedicada `aesthetic/<slug>` +
   commit baseline (`BASELINE_SHA`). `ORIGINAL_BRANCH`/`ORIGINAL_SHA` gravados.
2. **Censo de estados (não lista manual)**: `python3 tools/state_census.py`
   faz crawl dirigido (clica tudo clicável, força estado vazio, viewport
   estreito) e fotografa o conjunto de estados → congela em `states/` por
   run. Acima de 6 estados, use os pesos por estado de `judge/panel.yaml`.
3. **Invariância de fixture**: hash do HTML renderizado do champion
   (`python3 tools/fixture_hash.py`) capturado no pré-flight e re-checado
   toda rodada; mudou → run inválida, não "continua e torce".
4. Servir o preview (dev server do projeto; senão `npx serve`).
5. Smoke test de screenshots **e de comparabilidade**: mesmo viewport,
   `prefers-reduced-motion: reduce`, `Date.now` congelado, scroll 0,
   animações desativadas. **Canário**: renderize o champion 2× sob essas
   condições — hash diferente → a página não é elegível para modo automático.
6. Verificar fontes do ambiente de render: `tools/doctor.sh` roda `fc-list`;
   fonte do projeto ausente → ABORTO (fonte faltando muda a tipografia que o
   juiz julga).
7. `aesthetic-results.md` (APPEND-only) + `aesthetic-calibration.md` criados.

### 7b. Target adaptation checklist (aprendido no 1º uso real — pokai, 2026-10-05)

Antes da rodada 1, PROVE que o pipeline vê as mudanças que o builder faz.
Três lições de um run real que quase produziu 5 rodadas de julgamento fantasma:

- **Onde o diff aparece**: páginas com abas/rotas renderizam só parte do DOM
  por vez. O target de captura deve ser O ESTADO ONDE O CSS PATCHEADO É
  VISÍVEL — no caso real, a tabela de turnos só existia na aba "Turns"; toda
  screenshot da aba default fotografava uma página onde o patch não existia.
  Documente no run: "diff de density aparece em: aba X, seletor Y".
- **Computed style é a prova; pixel/md5 é só indício**: recursos externos
  (sprites de CDN, ads, avatares) mudam entre capturas do MESMO estado — md5
  igual NÃO prova ausência de diff, md5 diferente NÃO prova presença. Prove
  aplicação lendo o computed style do elemento alvo ao vivo
  (`getComputedStyle(td).paddingBlock === "5px"`) — o gate de invariância
  DOM (`tools/dom_invariance.py`) cobre o caso geral.
- **Juiz com smoke real antes da rodada 1**: 1 chamada pairwise legítima
  (champion vs champion com diff sintético visível, ex.: padding 8→3px) —
  endpoint, saldo e visão validados em ~30s. Erros comuns que isso pega:
  endpoint da API errado (plano/conta divergentes dão 429 "no balance"
  ENQUANTO a key funciona no endpoint certo), contrato de parâmetros que
  mudou server-side (ex.: `thinking`), browser do Playwright ausente.
- **Revert cirúrgico**: `git checkout -- <arquivo>` (código), nunca
  `-- .` na raiz — estado de runtime do alvo (DBs, sessões, uploads) não é
  código e reverter pode derrubar o preview no meio do run.

## Gates determinísticos (o chão — imutáveis durante o loop)

`bash gates/run_gates.sh <champion_url> <challenger_url>` — ordem do mais
barato ao mais caro, short-circuit na primeira falha:

| Ordem | Gate | Ferramenta | Falha se |
|---|---|---|---|
| 1 | Build/compile | toolchain do projeto | exit ≠ 0 |
| 2 | Acessibilidade | axe-core via Playwright (`gates/gate_axe.mjs`) | violação serious/critical nova vs. champion |
| 3 | Contraste | WCAG AA via axe color-contrast (`gates/gate_contrast.sh`) | novo par texto/fundo < 4.5:1 |
| — | Invariância DOM | `tools/dom_invariance.py` | conjunto de elementos interativos/overflow mudou sem justificativa |

**O slop-score NÃO é gate.** É SINAL: `python3 tools/slop_signal.py` imprime
um número (0–100) que entra no log e na rubrica do prompt do juiz. Motivo
(patch B2): um detector de tells hardcodado é trivialmente gameable pelo
builder (aprende a evitar `#F4F1EA` mantendo a estética idêntica) e pune
escolhas humanas legítimas; promovê-lo a filtro principal é Goodhart
embutido — e "ninguém vigia os gates". Os tells anti-slop vivem como
**rubrica negativa** em `judge/prompt_pairwise.md` (custo zero, não-gameable
por gate). Se um dia o slop virar gate: meça antes o ruído (mesmo champion
renderizado 5×) e fixe δ = 2–3× o ruído observado — nunca um número escolhido.

Falhou qualquer gate → revert imediato (sem LLM), `PLATÔ++`, log.
Falha de INFRA (Chromium OOM, timeout de render, rate limit da API) → retry
com backoff, até 3×, e NÃO conta para `FALHAS→FIM`; só falha de produto conta.

## Rodada (repita)

1. `elapsed ≥ duração_do_loop` → FIM.
2. Integridade dos gates (dupla checagem): `git diff --quiet $BASELINE_SHA --
   gates/ tools/ judge/` E `git status --porcelain` desses dirs limpos.
   Violação → ABORTO.
3. **Direção ainda não tentada**: pegue do deck (`directions/deck.yaml`) a
   próxima direção estética não queimada; logue a queima. Dedup: hash
   normalizado do diff — variação repetida nem chega ao juiz (custa só
   builder). Deck esgotado → PLATÔ.
4. Builder novo (subagente descartável): screenshot do champion + brief de
   UMA mudança (1 arquivo / ~30 linhas) + a direção do deck. Ele NÃO vê
   vereditos anteriores.
5. Screenshot do challenger — mesmos breakpoints, viewport, seed e condições
   do champion (senão o pairwise é inválido).
6. Hash do fixture/champion re-checado (`tools/fixture_hash.py`); mudou →
   run inválida.
7. Gates determinísticos; falha → revert imediato, `PLATÔ++`, log.
8. **Painel pairwise cego AB+BA** (`judge/run_pair.py`): screenshots apenas,
   sem código, sem diff, sem nome de modelo, ordem aleatorizada por seed
   logada. Cada juiz × persona julga nas duas ordens; veredito só vale se
   sobreviver ao swap. Família do builder REMOVIDA do painel da rodada
   (firewall — impossível em single-family, ver modo degradado acima).
   Empate ("sem diferença perceptível" é opção explícita) → revert: o
   challenger precisa vencer, não empatar (maioria ≥ 2/3 do painel).
   Com painel mínimo de 2 famílias: 2 "indecisos" seguidos na mesma direção
   → pausa + voto humano (desempate N2, não espera o swap-rate janelado).
9. Keep: commit só dos paths tocados, champion avança (`aesthetic/<slug>`).
   Revert: fiel e auditado (`git restore --source=HEAD --staged --worktree`,
   `git status` limpo após cada revert).
10. Meta-juiz a cada 5 rodadas (3 em single-family) — `judge/meta_judge.py`:
    swap-rate da janela e κ do painel; fora da faixa calibrada → PAUSE_HUMAN
    (1 voto humano exigido) ou DEMOTE:<juiz> (peso zerado na maioria).
11. Contadores: PLATÔ (5 → FIM), FALHAS de produto (3 → FIM; falha de infra
    com retry NÃO conta).

## FIM

1. Checkout da branch original (fiel ao karpathy-loop; stash/backup
   reportados).
2. Relatório: rodadas executadas + motivo do FIM; keeps com hashes;
   **keeps/rodada** (métrica obrigatória — abaixo de 0.1 em validação interna,
   o posicionamento público muda); par de screenshots antes/depois do
   champion final; swap-rate/κ finais; custo em tokens e US$ da run.
3. Em single-family: recomendar explicitamente voto humano em lote sobre o
   diff acumulado antes de merge.
4. Opção: merge manual ou `git branch -D aesthetic/<slug>` — só com
   aprovação explícita do usuário.

## Validação (B3) — leia ANTES de confiar no painel

`benchmark/PROTOCOL.md` é PRÉ-REGISTRADO: prompt, modelos com pin exato,
temperatura, personas, split 70/30, orçamento de 2 iterações de protocolo,
regra de pivô e fórmula de IC foram fixados antes do primeiro run. Não há
dados de resultado neste repo ainda — o critério de vida do projeto (≥65%
multi-família no WiserUI-Bench, IC distinguishable de acaso) está definido
lá, junto com o pivô honesto ("aesthetic-loop assistido") caso fique abaixo.

## Doctor

`bash tools/doctor.sh` valida, nesta ordem: git disponível + repo limpo,
Playwright/Chromium instalado, fontes via `fc-list`, invariância de hash
(render 2× do mesmo estado), e throughput real da API do painel (1 chamada
por família configurada). Falhou um passo → o README documenta qual custo de
setup por projeto aquele passo representa (seção "quanto setup o SEU projeto
precisa").
