# -*- coding: utf-8 -*-
import json, numpy as np, os
from app.services.ml_ranker import ml_ranker

def iter_pairs(path, n=200):
    k = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            yield row["me"], row["other"], row["label"]
            k += 1
            if k >= n: break

if __name__ == "__main__":
    data = "data/training_pairs.jsonl"
    raws, cals, labs = [], [], []
    for me, other, y in iter_pairs(data, n=500):
        x = ml_ranker._extract_features(me, other, return_names=False)
        p_raw = float(ml_ranker.dnn.predict_proba(x.reshape(1,-1))[0,1])
        p_cal = float(ml_ranker._apply_calib(p_raw))
        raws.append(p_raw); cals.append(p_cal); labs.append(y)
    def qq(v): 
        q = np.quantile(v, [0, .1, .5, .9, 1])
        return "min={:.3f} q10={:.3f} med={:.3f} q90={:.3f} max={:.3f}".format(*q)
    print("[probe] raw :", qq(np.array(raws)))
    print("[probe] cal :", qq(np.array(cals)))
    print("[probe] frac(cal==1.0) =", float((np.abs(np.array(cals)-1.0) < 1e-9).mean()))
