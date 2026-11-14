from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    make_scorer,
    precision_score,
    recall_score,
    top_k_accuracy_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate

CV_FOLDS = 5
RANDOM_STATE = 42
SCORING = {
    "f1_macro": make_scorer(f1_score, average="macro", zero_division=0),
    "accuracy": make_scorer(accuracy_score),
    "precision_macro": make_scorer(precision_score, average="macro", zero_division=0),
    "recall_macro": make_scorer(recall_score, average="macro", zero_division=0),
}


def cross_evaluate(model, X, y) -> dict:
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_validate(model, X, y, cv=cv, scoring=SCORING, n_jobs=-1)
    summary: dict = {}
    for metric in SCORING:
        vals = scores[f"test_{metric}"]
        summary[metric] = {"mean": round(float(np.mean(vals)), 4), "std": round(float(np.std(vals)), 4)}
    summary["per_fold"] = {m: [round(float(v), 4) for v in scores[f"test_{m}"]] for m in SCORING}
    return summary


def evaluate_on_test(model, X_test, y_test) -> dict:
    pred = model.predict(X_test)
    results = {
        "accuracy": float(accuracy_score(y_test, pred)),
        "precision_macro": float(precision_score(y_test, pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_test, pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_test, pred, average="macro", zero_division=0)),
        "per_class": classification_report(y_test, pred, output_dict=True, zero_division=0),
    }
    if hasattr(model, "predict_proba"):
        try:
            proba = model.predict_proba(X_test)
            results["top_5_accuracy"] = float(
                top_k_accuracy_score(y_test, proba, k=min(5, len(model.classes_)), labels=model.classes_)
            )
            results["top_10_accuracy"] = float(
                top_k_accuracy_score(y_test, proba, k=min(10, len(model.classes_)), labels=model.classes_)
            )
        except Exception:
            pass
    return results


def update_metrics_file(eval_results: dict, metrics_path: Path | str) -> dict:
    """Update an existing metrics.json file with precision, recall, and macro F1 scores."""
    p = Path(metrics_path)
    if not p.exists():
        raise FileNotFoundError(f"Metrics file not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    final_eval = data.setdefault("final_test_eval", {})
    final_eval["precision_macro"] = round(eval_results.get("precision_macro", 0.0), 4)
    final_eval["recall_macro"] = round(eval_results.get("recall_macro", 0.0), 4)
    final_eval["f1_macro"] = round(eval_results.get("f1_macro", 0.0), 4)

    champion_name = data.get("champion", {}).get("name")
    if champion_name and champion_name in data.get("models", {}):
        data["models"][champion_name]["precision_macro"] = round(eval_results.get("precision_macro", 0.0), 4)
        data["models"][champion_name]["recall_macro"] = round(eval_results.get("recall_macro", 0.0), 4)
        data["models"][champion_name]["f1_macro"] = round(eval_results.get("f1_macro", 0.0), 4)

    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data
