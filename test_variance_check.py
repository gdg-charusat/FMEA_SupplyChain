"""Quick smoke test: verify models produce different S/O/D/RPN scores."""
import sys, copy, yaml
sys.path.insert(0, "src")

with open("config/config.yaml") as f:
    config = yaml.safe_load(f)

from llm_extractor import LLMExtractor
from risk_scoring import RiskScoringEngine

texts = [
    "Brake pedal feels spongy and stopping distance increased",
    "Engine overheats after 30 minutes of driving",
    "Steering wheel vibrates at highway speeds",
    "Transmission slips between 2nd and 3rd gear",
]

models = [
    "mistralai/Mistral-7B-Instruct-v0.2",
    "meta-llama/Llama-2-7b-chat-hf",
    "gpt2",
    "Rule-based (No LLM)",
]

scorer = RiskScoringEngine(config)
all_rpns = {}

for model in models:
    cfg = copy.deepcopy(config)
    cfg["model"]["name"] = model
    ext = LLMExtractor(cfg)
    rpns = []
    print(f"\n=== {model} ===")
    for t in texts:
        info = ext.extract_failure_info(t)
        scored = scorer.score_fmea_row(info)
        s, o, d, rpn = scored["severity"], scored["occurrence"], scored["detection"], scored["rpn"]
        rpns.append(rpn)
        print(f"  S={s}  O={o}  D={d}  RPN={rpn:>4}  | {t[:50]}")
    all_rpns[model] = rpns

# Check variance
import numpy as np
print("\n--- Variance Check ---")
for i, t in enumerate(texts):
    vals = [all_rpns[m][i] for m in models]
    std = np.std(vals)
    print(f"Item {i+1} RPNs: {vals}  Std: {std:.2f}")

total_std = np.mean([np.std([all_rpns[m][i] for m in models]) for i in range(len(texts))])
print(f"\nAvg RPN Std across items: {total_std:.2f}")
if total_std > 0:
    print("SUCCESS: Non-zero variance across models")
else:
    print("FAIL: Zero variance - models produce identical scores")
