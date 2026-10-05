# aesthetic-loop

**The Karpathy loop for UI taste.** Keep-or-revert loop for aesthetics/UX: the
agent proposes one small UI change, deterministic gates run first (free), and a
**blind pairwise judge — screenshots only, run in both orders (AB+BA)** —
decides keep or revert. Regressions get reverted; improvements compound as
commits on a dedicated branch.

> Karpathy said the autoresearch loop "only works where evaluation is
> quantitative" and listed aesthetics as the counterexample. This repo is the
> direct answer: a trustworthy *scalar* for taste, built from blind pairwise
> comparison with position-swap filtering (GenArena), standing on
> deterministic floor gates.

```text
for each round (cap 20):
  builder (disposable subagent) → ONE small change in a git branch
  deterministic GATES: build · axe serious/critical · WCAG AA contrast · DOM invariance
     └ fail → instant revert, costs ~0 judge tokens
  blind PAIRWISE judge: champion vs challenger, screenshots only, AB+BA
     └ verdict counts only if it survives the position swap
  keep (commit) or revert — APPEND-only log with screenshots + verdicts
  meta-judge every N rounds: swap-rate + κ out of healthy range → pause + human vote
```

## Install

```bash
npx skills add Wesley-Source/aesthetic-loop
```

Works in any of the 79+ harnesses that skills.sh indexes. Requirements checked
by the doctor (below): git, Playwright/Chromium, fonts, and an API key for each
judge family in `judge/panel.yaml`.

## Single-family mode — the default (any family)

The loop works with **one single model family** — Z.ai/GLM, Claude, Gemini,
whatever provider you have. This is not a degraded mode: it is the product's
primary mode, with reinforced safeguards, because judge and builder share the
same RLHF aesthetic prior (Panickssery et al. 2024 — blindness to code does
not remove stylistic-fingerprint bias).

### Safeguards single-family requires (all automatic)

1. **Deterministic gates rule.** Build, axe, WCAG contrast and the meta-judge
   decide almost everything; the intra-family pairwise only breaks ties between
   gate-passing candidates — never the source of truth.
2. **Accelerated meta-judge**: every 3 rounds (not 5). Family-bias accumulates
   faster without cross-family counterweight.
3. **Mandatory human vote at END** before any merge — and every vote feeds the
   calibration layer, which is the real counterweight: with 10–20 of your
   pairs, the judge follows YOUR taste, not the family default.
4. **Anti-slop signal in the judge's rubric** (not a gate): the slop detector
   never blocks, but the prompt penalizes generic composition — the
   counterweight that a family firewall would provide in multi-family mode.

### What single-family does NOT allow

- **Publishing results as evidence of the anti-Karpathy thesis**: the honest
  critique is "GLM judging GLM". Multi-family WiserUI-Bench validation
  (benchmark/PROTOCOL.md) is the license for public claims.
- **Autonomous merges without your END-human vote.** Multi-family: the
  meta-judge may approve alone with healthy swap-rate/κ. Single-family: your
  end-of-run vote is part of the protocol, not optional.

### Upgrading to multi-family

`judge/panel.yaml` accepts N families with exact model pins. Add a second
family and the per-round firewall turns on by itself (the builder's family
leaves the panel), the meta-judge relaxes to every 5 rounds, and the
END-human-vote requirement drops to optional.

**Multi-family validation** (WiserUI-Bench with 2+ families) strengthens
public claims; the protocol is pre-registered and ready to run whenever
validation and produce the launch evidence. `panel.yaml` already accepts the
multi-family format — flip `mode` and un-comment the judges.

## Honest costs (computed, not vibes)

Per run, 20-round cap, judge calls only pass when gates pass (~50% of rounds):

| Scenario | Judge calls | US$/run | Wall-clock |
|---|---|---|---|
| v0.1 (1 frontier judge × 3 personas × AB+BA) | 60 | **$1.53** | + gates |
| v0.5 panel (2 frontier judges × 3 personas × AB+BA) | 120 | **$2.52** | + gates |
| Single-family GLM (1 judge × 3 personas × AB+BA) | 60 | **$0.72** | + gates |

The dollar sign is not the problem — caps make cost verifiable, as promised.
The honest wall is:

- **Gates × states × rounds**: full Lighthouse/axe suites cost 15–30 s each;
  120 gate executions ≈ 30–60 min of wall time per run, plus ~240 screenshots
  in a 6-state matrix (≈16 min of Playwright). Mitigation: Lighthouse only
  post-keep (validation after the decision), axe+contrast per round.
- **Infra ≠ product failures**: Playwright/Chromium on a headless VPS with
  missing fonts or sporadic OOM must NOT burn the FALHAS→FIM counter — infra
  failures retry with backoff (3×) and don't count. Missing fonts literally
  change the typography the judge sees → the doctor checks `fc-list`.
- **Subscription ≠ unlimited API**: your Z.ai plan's rate limit can strangle
  60+ judge calls per run. The doctor measures real throughput before run 1.

## --doctor (run before the first round)

```bash
bash tools/doctor.sh http://localhost:8123/demo_target.html
```

Validates, in order: git available · Playwright/Chromium launches headless ·
fonts via `fc-list` (project fonts via `AESTHETIC_REQUIRED_FONTS`) ·
deterministic render (same state rendered 2× = same hash; a page that fails
this is **not eligible for automatic mode**, I2/N3) · real API throughput of
each configured judge family.

## How much setup does YOUR project need?

The one-command install installs the *loop*, not your project's *eligibility*.
Honest per-project costs:

| Your project is… | Setup you need | Why |
|---|---|---|
| Static page / no backend | ~zero. Serve it, run the doctor | fixtures are already frozen |
| Live page, own backend | **Fixture snapshots from the real backend** (never synthetic strings — truncation/wrap/overflow are aesthetic decisions; synthetic data optimizes for a world that doesn't exist). The fixture hash must be stable or the run is invalid | I2 |
| Any page | **State census** (`tools/state_census.py`): directed crawl discovers states — don't hand-list them, the builder breaks exactly the state nobody screenshotted | I1 |
| Any page with a build | One env var: `AESTHETIC_BUILD_CMD` (or a standard `npm run build`) | gate 1 |
| Headless VPS | Install project fonts + `fontconfig`; Chromium RAM headroom | I3 |
| Multi-page app | v0.1 is **one page** (static, CSS/layout changes only). Multi-page is v1.0 | design §6 |

If step 3 of 6 of the doctor failing sounds like your week, this section just
saved you the churn — that's its job.

## Assisted pivot (if the judge doesn't clear the bar)

The benchmark protocol (`benchmark/PROTOCOL.md`, **pre-registered**) defines
the kill/pivot rule before the first run: if the panel scores **<65%** on
held-out WiserUI-Bench pairs (Wilson 95% CI fully above 55%), v0.1 repositions
as **aesthetic-loop assisted** — the loop proposes and filters, the human
ratifies in batches of 10 swipes. The pivot reuses ~90% of this codebase and
is an honest product at 55–60%: it reverts the worst, surfaces the best, the
owner decides.

## Benchmark status

A **single-family validation run** was executed under the frozen protocol
(2026-10-05): held-out accuracy **87.2%** with swap-filtering (41/47,
Wilson 95% CI [74.8%, 94.0%]), zero prompt iterations. Full numbers,
methodology and caveats in
[`benchmark/RESULTS_singlefamily_2026-10-05.md`](benchmark/RESULTS_singlefamily_2026-10-05.md).

**What this does and does not mean:** it clears the pre-registered bar for
**personal/production use** of the loop by the repo owner (GLM judge). It is
**not** evidence of the anti-Karpathy thesis — the honest critique remains
"GLM judging GLM", and the multi-family run (a second, non-Z.ai judge family)
is the license for public performance claims. Until that run exists, this
README deliberately quotes no benchmark number as a selling point.

## The slop signal is a signal, not a gate

AI-slop detection (`tools/slop_signal.py`, 0–100) is **logged and fed to the
judge's rubric** — it never blocks a keep by itself. A hardcoded list of
"AI tells" (ban `#F4F1EA`!) is trivially gameable by the builder, punishes
legitimate human choices (cream + serif is also a human taste), and turns the
system into "select for not triggering the detector" — Goodhart embedded in
the floor. The anti-slop lives in the judge's negative rubric instead
(`judge/prompt_pairwise.md`): cost zero, not gameable by a gate. If you ever
promote it to a gate: first measure the noise (same champion rendered 5×), set
δ = 2–3× observed noise — never a round number someone chose.

## Repository map

```
SKILL.md                      the skill (karpathy-loop format, B1 labels, judge temp 0.2)
gates/                        deterministic floor: build · axe · WCAG contrast (+ orchestrator)
judge/panel.yaml              judge panel — multi-family format, single-family = degraded case
judge/prompt_pairwise.md      blind pairwise prompt + anti-slop negative rubric
judge/run_pair.py             1 judge × 1 pair × 2 orders, swap validation, temp 0.2
judge/meta_judge.py           windowed swap-rate + κ → CONTINUE | PAUSE_HUMAN | DEMOTE:<id>
demo/demo_target.html         static demo target, frozen states (zero dynamic content)
demo/checks/metric.sh         prints exactly 1 number (karpathy-loop contract)
benchmark/PROTOCOL.md         PRE-REGISTERED WiserUI-Bench protocol
benchmark/RESULTS_singlefamily_2026-10-05.md  single-family run: 87.2% held-out (personal-use bar cleared)
benchmark/wilson.py           the CI formula the protocol commits to
tools/slop_signal.py          slop score — signal + rubric input, never a gate (B2)
tools/state_census.py         state census by directed crawl, frozen per run (I1)
tools/dom_invariance.py       DOM invariance gate — catches broken modals w/o LLM (I1)
tools/fixture_hash.py         champion fixture hash per round + render canary (I2/N3)
tools/doctor.sh               pre-flight environment validation (I3)
directions/deck.yaml          pre-enumerated aesthetic directions; one per round (I4)
aesthetic-results.md.example  APPEND-only log structure (placeholders only — no invented numbers)
.claude-plugin/plugin.json    manifest for skills.sh indexing
```

## What's real in v0.1 vs. what's pending

**Implemented and runnable today**: all deterministic gates, the state census,
the DOM invariance gate, the fixture hash/canary, the doctor, the demo target
with its metric, the blind pairwise prompt, the AB+BA runner (against any
OpenAI-compatible multimodal API, temp 0.2), the meta-judge, the deck of
directions, the pre-registered benchmark protocol.

**Pending (and labeled as such everywhere)**: the multi-family validation runs
(owner is buying frontier credits — B1) and therefore any benchmark number,
keep-rate, or "N iterations kept M" claim. This README contains **no such
numbers** on purpose. The demo GIF for launch comes after that validation, not
before.

## License

MIT © Wesley Carlos Nascimento
