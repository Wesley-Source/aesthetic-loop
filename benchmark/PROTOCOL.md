# WiserUI-Bench — Protocolo PRÉ-REGISTRADO (patch B3)

**Status: PRÉ-REGISTRO. Nenhum dado de resultado existe neste repo ainda.**
Este arquivo foi commitado ANTES do primeiro run exatamente para que a
iteração não vire curve-fitting. Alterações neste arquivo após o primeiro run
só são legítimas em um novo bloco "Amendment N" datado, com o motivo declarado
— editar o protocolo silenciosamente é o overfit que este registro existe
para impedir.

Data do registro: 2026-10-05 · Autor: Wesley Carlos Nascimento

## Por que este protocolo existe

O design v0.1 definiu "painel ≥65% no WiserUI-Bench" como critério de vida do
projeto — e, na mesma seção, citou a evidência de que MLLMs são fracos em
prever preferência humana. Os dois só coexistem se o número for medido sob um
protocolo que não pode ser ajustado até passar. Este é esse protocolo.

## 1. Fonte de dados

- Bench: **WiserUI-Bench** ([arXiv:2505.05026]) — pares de UI com preferência
  humana coletada. UI-Bench ([arXiv:2508.20410]) como segunda referência,
  sem entrada no critério.
- **n declarado obrigatório.** "≥65% com margem" exige IC95 distinguível de
  acaso: com n=200, 65% → IC95 [58%, 72%]; **mínimo absoluto de 43 pares
  julgáveis**; abaixo disso o critério inteiro é ruído e o run NÃO é
  publicado como evidência (nem favorável).

## 2. Configuração exata do juiz (fixada antes do run)

- **Modelos (pin exato, I5):** os `judges` de `judge/panel.yaml` com `mode:
  multi-family` — mín. 2 famílias distintas. Single-family NÃO valida este
  benchmark (B1: "GLM julga GLM" é o problema, não a resposta).
- **Temperatura:** 0.2 (a de `panel.yaml` — nunca 0; ver SKILL.md).
- **Prompt:** `judge/prompt_pairwise.md` exatamente como commitado, sem
  edição entre iterações.
- **Personas:** as 3 de `panel.yaml` (designer, apressado, dev-legado),
  mesmo peso.
- **Ordem:** AB+BA obrigatório (GenArena); seed por par logada.

## 3. Split held-out

- Divisão **70/30** por pares, sorteio com seed fixa registrada no run
  (`python3 -c "import random; random.Random(<SEED>).shuffle(pairs)"`).
- **Desenvolvimento de protocolo (se houver) olha só os 70%.** Os 30%
  held-out são julgados UMA vez, no final, com o protocolo congelado.
- O número público é o do **held-out**. Sempre.

## 4. Orçamento de iterações de protocolo (anti-overfit)

- **Máximo 2 iterações** de ajuste de protocolo (prompt/personas/pesos).
  Cada iteração re-julga só o split de 70%.
- **Terceira tentativa = publicar o resultado negativo.** Não há exceção.
- Métricas reportadas em TODA iteração: acurácia **com** e **sem**
  swap-filtering (descartar inconsistentes é survivorship — a acurácia do
  subconjunto consistente não é a acurácia do painel em produção), com **IC
  de Wilson 95%**, e o n efetivo de cada uma.

## 5. Critério de vida e regra de pivô (fixados agora)

- **Critério de sucesso:** acurácia held-out multi-família **≥65% com IC95
  inteiro acima de 55%**.
- **< 65% → PIVÔ ASSISTIDO, não morte:** v0.1 reposiciona como
  "aesthetic-loop assistido" — o loop propõe + filtra (gates + pairwise como
  ranking de confiança), o humano ratifica em lote (UI de swipe, batches de
  10 pares — N1). O pivô reusa ~90% do código existente (gates, censo,
  worktree, log, calibração) e é um produto honesto a 55–60%: reverte o pior,
  sugere o melhor, o dono decide.
- O README só cita números do bench DEPOIS do run; até lá, placeholders
  `<N iterações, N mantidas, X% no bench — números reais do run de validação>`
  (I6 — nada de número inventado por soar bem).

## 6. Fórmula do intervalo de confiança (Wilson, 95%)

```
n = acertos + erros; p̂ = acertos/n; z = 1.96
centro = (p̂ + z²/2n) / (1 + z²/n)
meia-largura = z·sqrt(p̂(1−p̂)/n + z²/4n²) / (1 + z²/n)
IC95 = [centro − meia-largura, centro + meia-largura]
```

Ferramenta: `python3 benchmark/wilson.py <acertos> <n>` (implementada neste repo).

## 7. Re-bench em mudança de pin (I5)

Qualquer alteração de `model:` em `judge/panel.yaml` → smoke re-run de 30
pares antes de confiar em comparações entre épocas. O log de cada rodada
registra o pin usado; o meta-juiz compara swap-rate contra a janela homóloga
do MESMO pin, não só contra as últimas rodadas.

## Resultados

(vazio por pré-registro — será preenchido como `RESULTS.md` separado,
apontando para o commit exato do protocolo usado, com os dados brutos de
votos por par.)
