# -*- coding: utf-8 -*-
import argparse, json
from app.services.ml_ranker import ml_ranker

def load_pairs(jsonl_path: str):
    samples = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            samples.append((row["me"], row["other"], int(row["label"])))
    return samples

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/training_pairs.jsonl")
    ap.add_argument("--xgb_top_k", type=int, default=16)
    ap.add_argument("--hidden", type=str, default="64,32")
    ap.add_argument("--split", choices=["by_me", "user_disjoint"], default="by_me")
    args = ap.parse_args()

    hidden = tuple(int(x) for x in args.hidden.split(",") if x)
    samples = load_pairs(args.data)
    stat = ml_ranker.fit(samples,
                     xgb_top_k=args.xgb_top_k,
                     dnn_hidden=hidden,
                     split_mode=args.split)
    print("Train done:", stat)
