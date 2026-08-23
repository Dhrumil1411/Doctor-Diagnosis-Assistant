from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from ml.evaluate import CV_FOLDS, RANDOM_STATE, cross_evaluate, evaluate_on_test

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "ml" / "artifacts"
LABEL = "prognosis"
CHAMPION_CANDIDATES = ["logistic_regression", "random_forest"]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_models() -> dict:
    return {
        "dummy_most_frequent": DummyClassifier(strategy="most_frequent", random_state=RANDOM_STATE),
        "logistic_regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=400, n_jobs=-1, class_weight="balanced", random_state=RANDOM_STATE
        ),
    }


def load_clean() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    train = pd.read_csv(ART / "cleaned_train.csv")
    test = pd.read_csv(ART / "cleaned_test.csv")
    features = [c for c in train.columns if c != LABEL]
    if features != [c for c in test.columns if c != LABEL]:
        raise AssertionError("train/test feature schemas differ")
    return train, test, features


def main() -> None:
    train_df, test_df, features = load_clean()
    X_train, y_train = train_df[features], train_df[LABEL]
    X_test, y_test = test_df[features], test_df[LABEL]

    cv_results: dict[str, dict] = {}
    print(f"{'model':<22} {'f1_macro':<18} {'accuracy':<16} {'precision_macro':<16} recall_macro")
    for name, model in build_models().items():
        summary = cross_evaluate(model, X_train, y_train)
        cv_results[name] = {"params": model.get_params(deep=False).__str__(), "cv": summary}
        row = lambda m: f"{summary[m]['mean']:.4f}+/-{summary[m]['std']:.4f}"
        print(f"{name:<22} {row('f1_macro'):<18} {row('accuracy'):<16} {row('precision_macro'):<16} {row('recall_macro')}")

    champion_name = max(
        CHAMPION_CANDIDATES,
        key=lambda n: (cv_results[n]["cv"]["f1_macro"]["mean"], -CHAMPION_CANDIDATES.index(n)),
    )
    champion_model = build_models()[champion_name]
    print(f"\nchampion (max CV macro-F1): {champion_name}")

    champion_model.fit(X_train, y_train)
    test_eval = evaluate_on_test(champion_model, X_test, y_test)
    print(f"held-out test: accuracy={test_eval['accuracy']:.4f} f1_macro={test_eval['f1_macro']:.4f} "
          f"(per-class numbers unreliable: 42 rows / 41 classes -- see docs/dataset-notes.md)")

    bundle_path = ART / "model.joblib"
    joblib.dump(
        {
            "model": champion_model,
            "model_name": champion_name,
            "feature_names": features,
            "diseases": sorted(y_train.unique().tolist()),
            "metadata": {
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "selection_rule": f"max mean macro-F1 over {CV_FOLDS}-fold stratified CV on cleaned_train.csv",
                "train_rows": len(X_train),
                "n_features": len(features),
                "n_classes": int(y_train.nunique()),
                "dataset_sha256": {
                    "cleaned_train.csv": sha256_of(ART / "cleaned_train.csv"),
                    "cleaned_test.csv": sha256_of(ART / "cleaned_test.csv"),
                },
            },
        },
        bundle_path,
    )

    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_features": len(features),
            "n_classes": int(y_train.nunique()),
            "sha256": {
                "cleaned_train.csv": sha256_of(ART / "cleaned_train.csv"),
                "cleaned_test.csv": sha256_of(ART / "cleaned_test.csv"),
            },
        },
        "models": cv_results,
        "champion": {
            "name": champion_name,
            "candidates_considered": CHAMPION_CANDIDATES,
            "baseline_floor_included": "dummy_most_frequent",
        },
        "final_test_eval": {
            **{k: v for k, v in test_eval.items() if k != "per_class"},
            "per_class": test_eval["per_class"],
            "caveat": "42 test rows across 41 classes; several classes have a single case",
        },
        "artifact": {"path": str(bundle_path), "sha256": sha256_of(bundle_path)},
    }
    (ART / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\nsaved: {bundle_path.name}, metrics.json")


if __name__ == "__main__":
    main()
