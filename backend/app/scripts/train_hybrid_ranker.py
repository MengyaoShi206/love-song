# -*- coding: utf-8 -*-
import argparse
import json
import os

import numpy as np
import joblib

from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score, log_loss

from app.services.ml_ranker import (
    HybridXgbDnnRanker, ml_ranker, META_PATH, ISO_PATH
)


def load_pairs(jsonl_path: str):
    samples = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            samples.append((row["me"], row["other"], int(row["label"])))
    return samples


def get_me_ids(samples):
    return np.array([s[0].get("id") for s in samples], dtype=np.int64)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/training_pairs.jsonl")
    ap.add_argument("--xgb_top_k", type=int, default=16)
    ap.add_argument("--hidden", type=str, default="64,32")
    ap.add_argument("--split", choices=["by_me", "user_disjoint"], default="by_me")
    ap.add_argument("--cv", type=int, default=0, help="K-fold GroupKFold(by_me)。0/1 表示不用 CV")
    args = ap.parse_args()

    hidden = tuple(int(x) for x in args.hidden.split(",") if x)
    samples = load_pairs(args.data)
    N = len(samples)

    # --------- 路径保障 ---------
    os.makedirs(os.path.dirname(META_PATH), exist_ok=True)

    # ===== 情况 A：使用 K 折分组交叉验证（按 me.id 分组） =====
    if args.cv and args.cv >= 2:
        k = int(args.cv)
        groups = get_me_ids(samples)
        y_all = np.array([int(s[2]) for s in samples], dtype=np.int32)

        oof_pred = np.full(N, np.nan, dtype=np.float64)
        aucs = []

        gkf = GroupKFold(n_splits=k)
        for fold_idx, (tr_idx, va_idx) in enumerate(gkf.split(np.zeros(N), y_all, groups=groups), start=1):
            tr_s = [samples[i] for i in tr_idx]
            va_s = [samples[i] for i in va_idx]

            # 折内：不加载旧模型、不持久化、不做标定
            rk = HybridXgbDnnRanker(load_existing=False)
            rk.fit(
                tr_s,
                xgb_top_k=args.xgb_top_k,
                dnn_hidden=hidden,
                split_mode="by_me",
                save_model=False,
                calibrate=False
            )

            # ===== 训练集预测 =====
            train_p = [rk.predict_pair(me, other) for (me, other, _) in tr_s]
            train_p = np.array(train_p, dtype=np.float64)
            y_train = y_all[tr_idx]

            # ===== 验证集预测 =====
            val_p = [rk.predict_pair(me, other) for (me, other, _) in va_s]
            val_p = np.array(val_p, dtype=np.float64)
            y_val = y_all[va_idx]
            oof_pred[va_idx] = val_p  # 保存 OOF 预测

            # ===== AUC 计算 =====
            auc_tr = auc_val = None
            if len(np.unique(y_train)) >= 2:
                auc_tr = roc_auc_score(y_train, train_p)
            if len(np.unique(y_val)) >= 2:
                auc_val = roc_auc_score(y_val, val_p)
                aucs.append(auc_val)

            # ===== 输出 =====
            if auc_tr is not None and auc_val is not None:
                print(f"[CV] fold {fold_idx}/{k}: train AUC={auc_tr:.4f} | val AUC={auc_val:.4f} (n_val={len(va_idx)})")
            elif auc_val is not None:
                print(f"[CV] fold {fold_idx}/{k}: val AUC={auc_val:.4f} (n_val={len(va_idx)})")
            else:
                print(f"[CV] fold {fold_idx}/{k}: 单类验证集，跳过 AUC (n_val={len(va_idx)})")

        # ------- 基于 OOF 的全局标定（先试 platt，失败再试 iso，否则 pct） -------
        mask = np.isfinite(oof_pred)
        p = oof_pred[mask]
        y = y_all[mask]

        used = "none"
        calib = None
        iso_model = None
        ll_before = log_loss(y, p, labels=[0, 1])

        # try platt
        try:
            lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, class_weight="balanced")
            lr.fit(p.reshape(-1, 1), y)
            a = float(lr.coef_[0, 0])
            b = float(lr.intercept_[0])
            p_after = 1.0 / (1.0 + np.exp(-(a * p + b)))
            ll_after = log_loss(y, p_after, labels=[0, 1])
            if ll_after + 1e-4 < ll_before and abs(a) >= 0.5:
                used = "platt"
                calib = ("platt", a, b)
        except Exception as e:
            print("[CV] platt 失败：", repr(e))

        # try iso
        if used == "none":
            try:
                iso = IsotonicRegression(out_of_bounds="clip")
                iso.fit(p, y)
                p_iso = iso.predict(p)
                ll_after = log_loss(y, p_iso, labels=[0, 1])
                if ll_after + 1e-4 < ll_before:
                    used = "iso"
                    iso_model = iso
            except Exception as e:
                print("[CV] iso 失败：", repr(e))

        # fallback pct
        if used == "none":
            p5, p95 = float(np.percentile(p, 5)), float(np.percentile(p, 95))
            used = "pct"
            calib = ("pct", p5, p95)

        # ------- 全量再训最终模型（不在 fit 内做标定），再挂上 OOF 标定器 -------
        stat = ml_ranker.fit(
            samples,
            xgb_top_k=args.xgb_top_k,
            dnn_hidden=hidden,
            split_mode=args.split,
            save_model=True,
            calibrate=False
        )

        if used == "platt":
            ml_ranker.calib = ("platt", calib[1], calib[2])
            ml_ranker.iso = None
        elif used == "iso":
            ml_ranker.calib = ("iso", float("nan"), float("nan"))
            ml_ranker.iso = iso_model
            try:
                joblib.dump(iso_model, ISO_PATH)
            except Exception:
                pass
        else:  # pct
            ml_ranker.calib = calib
            ml_ranker.iso = None

        # 写 meta（附带 CV 信息）
        meta = {
            "features_used": ml_ranker.selected_feats,
            "expected_dim": ml_ranker.expected_dim,
            "calib": (list(ml_ranker.calib) if ml_ranker.calib else None),
            "calib_mode": used,
            "cv_folds": k,
            "cv_auc_mean": float(np.mean(aucs)) if aucs else None,
            "cv_auc_std": float(np.std(aucs)) if aucs else None,
            "n_samples": int(N),
        }
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        print("CV done:", meta)

    # ===== 情况 B：不使用 CV，走单次 by_me/user_disjoint 切分 =====
    else:
        stat = ml_ranker.fit(
            samples,
            xgb_top_k=args.xgb_top_k,
            dnn_hidden=hidden,
            split_mode=args.split
        )
        print("Train done:", stat)
