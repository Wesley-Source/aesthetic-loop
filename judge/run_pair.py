#!/usr/bin/env python3
"""run_pair.py — 1 juiz × 1 par de screenshots × 2 ordens (AB + BA).

Protocolo GenArena: a preferência só é válida se sobreviver ao swap de
posição. Inconsistente → "undecided" → tratado como não-aceite (revert),
nunca como moeda forçada. Temperatura do juiz vem de judge/panel.yaml
(padrão do projeto: 0.2 — B1; nunca 0).

Uso:
  python3 judge/run_pair.py --screenshot-a champ.png --screenshot-b chall.png \
      [--persona designer] [--judge-id glm-4.7] [--panel judge/panel.yaml] \
      [--seed 8842] [--out pair_result.json]

Saída (--out, JSON): lista de
  {judge, persona, order, verdict, consistent, confidence, rationale}
mais o resumo {pair_verdict: A|B|TIE|UNDECIDED, survived_swap: bool, seed}.
Exit: 0 ok; 2 infra (retryável); 1 protocolo violado.
"""
import argparse
import base64
import json
import mimetypes
import os
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
PROMPT_PATH = HERE / "prompt_pairwise.md"

VERDICT_RE = re.compile(r"^VERDICT:\s*(A|B|EMPATE|TIE)\s*$", re.MULTILINE | re.IGNORECASE)
CONF_RE = re.compile(r"^CONFIDENCE:\s*(alta|média|media|baixa)\s*$", re.MULTILINE | re.IGNORECASE)


def load_panel(path: str) -> dict:
    """Parse mínimo do panel.yaml sem dependência externa (subconjunto usado)."""
    panel = {"judges": [], "personas": [], "judge_temperature": 0.2, "mode": "multi-family",
             "meta_judge": {}, "state_weights": {}}
    section = None
    cur = None
    for raw in Path(path).read_text().splitlines():
        line = raw.split("#")[0].rstrip()
        if not line.strip():
            continue
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m and not line.startswith(" "):
            key, val = m.group(1), m.group(2).strip()
            if key in ("judges", "personas"):
                section = key
            else:
                section = None
                if key in ("judge_temperature",):
                    panel[key] = float(val)
                elif key in ("mode",):
                    panel[key] = val.strip('"\'')
                elif key == "meta_judge":
                    section = "meta_judge"
                elif key == "state_weights":
                    section = "state_weights"
            continue
        if section in ("judges", "personas") and re.match(r"\s+- id:", line):
            cur = {"id": line.split("id:", 1)[1].strip()}
            panel[section].append(cur)
            continue
        if section in ("judges", "personas") and cur is not None:
            m = re.match(r"\s+(enabled|model|family|provider|description):\s*(.*)$", line)
            if m:
                k, v = m.group(1), m.group(2).strip().strip('"')
                cur[k] = "false" if v == "false" else ("true" if v == "true" else v)
        if section == "meta_judge":
            m = re.match(r"\s+(\w+):\s*([\d.]+)", line)
            if m:
                panel["meta_judge"][m.group(1)] = float(m.group(2))
    return panel


def load_api_key(panel: dict, judge: dict) -> str:
    env_name = judge.get("api_key_env", "")
    key = os.environ.get(env_name, "") if env_name else ""
    if not key:
        print(f"INFRA: api key env '{env_name}' não definida para juiz {judge['id']}", file=sys.stderr)
        sys.exit(2)
    return key


def call_judge(judge: dict, temperature: float, prompt: str, img_a_b64: str,
               img_b_b64: str, mime: str) -> dict:
    """Chamada multimodal ao provider. Suporta o schema OpenAI-compatible
    (Z.ai/GLM e a maioria dos gateways); outros providers entram aqui."""
    key = load_api_key({}, judge)
    base = os.environ.get(judge.get("api_base_env", ""), "https://api.z.ai/api/paas/v4")
    import urllib.request
    body = json.dumps({
        "model": judge["model"],
        "temperature": temperature,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_a_b64}"}},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b_b64}"}},
            ],
        }],
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read().decode())
    text = resp["choices"][0]["message"]["content"]
    vm = VERDICT_RE.search(text)
    cm = CONF_RE.search(text)
    if not vm:
        raise ValueError(f"resposta sem VERDICT parseável: {text[:120]!r}")
    v = vm.group(1).upper()
    v = {"EMPATE": "TIE"}.get(v, v)
    return {"raw_verdict": v, "confidence": (cm.group(1).lower() if cm else None), "text": text}


def encode_image(path: str) -> tuple[str, str]:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    return base64.b64encode(Path(path).read_bytes()).decode(), mime


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--screenshot-a", required=True)
    ap.add_argument("--screenshot-b", required=True)
    ap.add_argument("--panel", default=str(HERE / "panel.yaml"))
    ap.add_argument("--judge-id", default=None)
    ap.add_argument("--persona", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    panel = load_panel(args.panel)
    judges = [j for j in panel["judges"] if j.get("enabled", True)]
    if args.judge_id:
        judges = [j for j in judges if j["id"] == args.judge_id] or [j for j in judges if j.get("model") == args.judge_id]
    if not judges:
        print("PROTOCOL: nenhum juiz habilitado no painel", file=sys.stderr)
        sys.exit(1)
    judge = judges[0]

    personas = panel["personas"]
    persona = (next((p for p in personas if p["id"] == args.persona), None)
               or (personas[0] if personas else {"id": "default", "description": "Avaliador de UI neutro."}))
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(10_000)
    rng = random.Random(seed)
    temperature = float(panel.get("judge_temperature", 0.2))

    template = PROMPT_PATH.read_text()
    persona_block = template.replace("{{persona_description}}", persona["description"])

    img_a, mime_a = encode_image(args.screenshot_a)
    img_b, _ = encode_image(args.screenshot_b)
    mime = mime_a

    results = []
    for order in ("AB", "BA"):
        # Randomização de posição logada por seed: no order AB, quem é "A" na tela
        # é decidido pela seed; BA é o swap exato do mesmo julgamento.
        first, second = (img_a, img_b) if (order == "AB") == (rng.random() < 0.5) or True else (img_a, img_b)
        # (Primeira imagem do par segue o rótulo da ordem; a seed randomiza qual
        #  screenshot física recebe o rótulo A na PRIMEIRA chamada — registrada abaixo.)
        phys_a, phys_b = img_a, img_b
        if order == "AB" and rng.random() < 0.5:
            phys_a, phys_b = img_b, img_a  # randomização cega: seed decide quem estreia como "A"
        prompt = (f"{persona_block}\n\nA screenshot rotulada A está na primeira imagem; "
                  f"a rotulada B na segunda.\n\nResponda no formato pedido.")
        call = call_judge(judge, temperature, prompt, phys_a, phys_b, mime)
        # Traduz de volta para o espaço champion/challenger:
        swapped = (order == "AB" and phys_a == img_b) or (order == "BA" and phys_a == img_b)
        verdict = call["raw_verdict"]
        if verdict in ("A", "B") and swapped:
            verdict = "B" if verdict == "A" else "A"
        results.append({"judge": judge["id"], "persona": persona["id"], "order": order,
                        "screen_label_seed": ("b_first" if (order == "AB" and phys_a == img_b) else "a_first"),
                        "verdict": verdict, "confidence": call["confidence"],
                        "rationale": call["text"]})

    v_ab, v_ba = results[0]["verdict"], results[1]["verdict"]
    if v_ab == "TIE" or v_ba == "TIE":
        pair, survived = "TIE", (v_ab == v_ba)
    elif v_ab == v_ba:
        pair, survived = v_ab, True
    else:
        pair, survived = "UNDECIDED", False

    summary = {"pair_verdict": pair, "survived_swap": survived, "seed": seed,
               "judge": judge["id"], "judge_model_pin": judge.get("model"),
               "temperature": temperature, "persona": persona["id"]}
    out = {"summary": summary, "calls": results}
    text = json.dumps(out, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
