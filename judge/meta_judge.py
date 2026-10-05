#!/usr/bin/env python3
"""meta_judge.py — o juiz vigiado: autovalidação do painel sobre uma janela
de rodadas (Minimum Viable Validation Protocol).

Entrada: um JSONL com 1 registro por comparação já executada, cada linha:
  {"judge": <id>, "persona": <id>, "survived_swap": bool,
   "verdict": "A"|"B"|"TIE"|"UNDECIDED", "round": N}

Saída: UMA linha "CONTINUE" | "PAUSE_HUMAN" | "DEMOTE:<judge_id>" seguida de
um bloco JSON com swap_rate, kappa e os limiares usados (calibráveis em
judge/panel.yaml — B1: meça o baseline do seu painel antes de fixar).

Limiares default são chutes iniciais declarados, não números medidos.
Uso: python3 judge/meta_judge.py --log aesthetic-results.jsonl [--panel judge/panel.yaml] [--window 5]
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent


def fleiss_kappa(votes_by_item: list[list[str]]) -> float:
    """κ de Fleiss sobre categorias A/B/TIE (itens = comparações, raters = juízes)."""
    cats = ["A", "B", "TIE"]
    n_items = len(votes_by_item)
    if n_items == 0:
        return 0.0
    n_raters = len(votes_by_item[0])
    if n_raters < 2:
        return 0.0
    n = len(cats)
    p_sum = 0.0
    for votes in votes_by_item:
        c = Counter(votes)
        p_sum += sum((c.get(k, 0) / n_raters) ** 2 for k in cats)
    P_bar = p_sum / n_items
    p_j = [sum(1 for votes in votes_by_item for v in votes if v == k) / (n_items * n_raters) for k in cats]
    P_e = sum(p ** 2 for p in p_j)
    if P_e >= 0.9999:
        return 1.0
    return (P_bar - P_e) / (1 - P_e)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="JSONL de comparações (1 por linha)")
    ap.add_argument("--panel", default=str(HERE / "panel.yaml"))
    ap.add_argument("--window", type=int, default=None)
    args = ap.parse_args()

    # Limiares: defaults declarados ← panel.yaml (meta_judge.*)
    thresholds = {"swap_rate_min": 0.50, "kappa_min": 0.20, "window_rounds": 5}
    txt = Path(args.panel).read_text() if Path(args.panel).exists() else ""
    in_meta = False
    for line in txt.splitlines():
        bare = line.split("#")[0]
        if bare.startswith("meta_judge:"):
            in_meta = True
            continue
        if in_meta:
            if bare and not bare[0].isspace():
                in_meta = False
                continue
            parts = bare.strip().split(":")
            if len(parts) == 2 and parts[0] in thresholds:
                thresholds[parts[0]] = float(parts[1])
    window = args.window or int(thresholds["window_rounds"])

    rows = [json.loads(l) for l in Path(args.log).read_text().splitlines() if l.strip()]
    if not rows:
        print("PAUSE_HUMAN")
        print(json.dumps({"error": "log vazio — nada a validar"}))
        sys.exit(1)

    last_round = max(r.get("round", 0) for r in rows)
    recent = [r for r in rows if r.get("round", 0) > last_round - window] or rows

    swap_rate = sum(1 for r in recent if r.get("survived_swap")) / len(recent)

    # κ entre juízes por comparação (round, persona) — só onde ≥2 juízes votaram.
    by_item: dict[tuple, list[str]] = defaultdict(list)
    for r in recent:
        if r.get("verdict") in ("A", "B", "TIE"):
            by_item[(r.get("round"), r.get("persona"))].append(r["verdict"])
    items = [v for v in by_item.values() if len(v) >= 2]
    kappa = fleiss_kappa(items) if items else 0.0

    # Divergência por juiz (para DEMOTE): taxa de discordância com a maioria do item.
    discord = defaultdict(lambda: [0, 0])  # judge -> [discordou, votou]
    for votes in by_item.values():
        if len(votes) < 2:
            continue
        majority = Counter(votes).most_common(1)[0][0]
        # reprecisa associar juiz ao voto:
        pass
    by_judge_votes: dict[tuple, list[tuple]] = defaultdict(list)
    for r in recent:
        if r.get("verdict") in ("A", "B", "TIE"):
            by_judge_votes[(r.get("round"), r.get("persona"))].append((r["judge"], r["verdict"]))
    for votes in by_judge_votes.values():
        if len(votes) < 2:
            continue
        majority = Counter(v for _, v in votes).most_common(1)[0][0]
        for judge, v in votes:
            discord[judge][1] += 1
            if v != majority:
                discord[judge][0] += 1

    verdict = "CONTINUE"
    demoted = None
    if swap_rate < thresholds["swap_rate_min"]:
        verdict = "PAUSE_HUMAN"
    elif items and kappa < thresholds["kappa_min"]:
        ranked = sorted(discord.items(), key=lambda kv: -(kv[1][0] / kv[1][1] if kv[1][1] else 0))
        if ranked and ranked[0][1][1] >= 3 and (ranked[0][1][0] / ranked[0][1][1]) >= 0.6:
            demoted = ranked[0][0]
            verdict = f"DEMOTE:{demoted}"

    print(verdict)
    print(json.dumps({
        "swap_rate": round(swap_rate, 4),
        "kappa": round(kappa, 4),
        "n_comparisons": len(recent),
        "window_rounds": window,
        "thresholds": thresholds,
        "judge_discordance": {k: {"discord": v[0], "votes": v[1]} for k, v in discord.items()},
        "demoted": demoted,
        "note": "limiares são calibráveis — meça o baseline do seu painel antes de confiar (B1)",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
