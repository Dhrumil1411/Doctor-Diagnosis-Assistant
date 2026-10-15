from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.naive_bayes import BernoulliNB, MultinomialNB

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "ml" / "artifacts"
LABEL = "diseases"
RANDOM_STATE = 42
CHAMPION_CANDIDATES = ["bernoulli_nb", "multinomial_nb"]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_models() -> dict:
    return {
        "dummy_most_frequent": DummyClassifier(strategy="most_frequent", random_state=RANDOM_STATE),
        "multinomial_nb": MultinomialNB(alpha=0.1),
        "bernoulli_nb": BernoulliNB(alpha=0.1),
    }


def compute_top_k_acc(classes: np.ndarray, proba: np.ndarray, y_true: np.ndarray, k: int = 5) -> float:
    top_indices = np.argsort(proba, axis=1)[:, -k:]
    top_classes = classes[top_indices]
    hits = np.any(top_classes == y_true[:, None], axis=1)
    return float(np.mean(hits))


def load_clean() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    train = pd.read_csv(ART / "cleaned_train.csv")
    test = pd.read_csv(ART / "cleaned_test.csv")
    features = [c for c in train.columns if c != LABEL]
    if features != [c for c in test.columns if c != LABEL]:
        raise AssertionError("train/test feature schemas differ")
    return train, test, features


def main() -> None:
    print("Loading cleaned train and test datasets...", flush=True)
    train_df, test_df, features = load_clean()

    X_train = sparse.csr_matrix(train_df[features].values, dtype=np.float32)
    y_train = np.asarray(train_df[LABEL], dtype=str)

    X_test = sparse.csr_matrix(test_df[features].values, dtype=np.float32)
    y_test = np.asarray(test_df[LABEL], dtype=str)

    print(f"Train set: {X_train.shape[0]} samples, {len(features)} features, {len(np.unique(y_train))} classes", flush=True)
    print(f"Test set: {X_test.shape[0]} samples, {len(features)} features, {len(np.unique(y_test))} classes", flush=True)

    model_results: dict[str, dict] = {}
    fitted_models: dict[str, object] = {}

    print(f"\n{'model':<24} {'top1_acc':<12} {'top5_acc':<12} {'top10_acc':<12} {'train_time'}", flush=True)

    models = build_models()
    for name, model in models.items():
        t0 = time.time()
        model.fit(X_train, y_train)
        elapsed = time.time() - t0

        fitted_models[name] = model

        # Evaluate on test set
        pred = model.predict(X_test)
        top1_acc = float(accuracy_score(y_test, pred))

        top5_acc = None
        top10_acc = None
        if hasattr(model, "predict_proba"):
            try:
                proba = model.predict_proba(X_test)
                classes = np.asarray(model.classes_, dtype=str)
                top5_acc = compute_top_k_acc(classes, proba, y_test, k=5)
                top10_acc = compute_top_k_acc(classes, proba, y_test, k=10)
            except Exception as e:
                print(f"Warning: top-k calculation error for {name}: {e}")

        top5_str = f"{top5_acc:.4f}" if top5_acc is not None else "N/A"
        top10_str = f"{top10_acc:.4f}" if top10_acc is not None else "N/A"
        print(f"{name:<24} {top1_acc:<12.4f} {top5_str:<12} {top10_str:<12} {elapsed:.2f}s", flush=True)

        model_results[name] = {
            "params": str(model.get_params(deep=False)),
            "train_time_sec": round(elapsed, 2),
            "top1_accuracy": round(top1_acc, 4),
            "top5_accuracy": round(top5_acc, 4) if top5_acc is not None else None,
            "top10_accuracy": round(top10_acc, 4) if top10_acc is not None else None,
        }

    # Select champion model based on highest top-5 accuracy (or top-1 if tied)
    champion_name = max(
        CHAMPION_CANDIDATES,
        key=lambda n: (
            model_results[n].get("top5_accuracy") or 0.0,
            model_results[n].get("top1_accuracy") or 0.0,
            -CHAMPION_CANDIDATES.index(n),
        ),
    )
    champion_model = fitted_models[champion_name]
    print(f"\nChampion model selected: {champion_name}", flush=True)

    bundle_path = ART / "model.joblib"
    joblib.dump(
        {
            "model": champion_model,
            "model_name": champion_name,
            "feature_names": features,
            "diseases": sorted(np.unique(y_train).tolist()),
            "metadata": {
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "champion_type": champion_name,
                "train_rows": int(X_train.shape[0]),
                "test_rows": int(X_test.shape[0]),
                "n_features": len(features),
                "n_classes": int(len(np.unique(y_train))),
                "top1_accuracy": model_results[champion_name]["top1_accuracy"],
                "top5_accuracy": model_results[champion_name]["top5_accuracy"],
                "top10_accuracy": model_results[champion_name]["top10_accuracy"],
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
            "n_train": int(X_train.shape[0]),
            "n_test": int(X_test.shape[0]),
            "n_features": len(features),
            "n_classes": int(len(np.unique(y_train))),
            "sha256": {
                "cleaned_train.csv": sha256_of(ART / "cleaned_train.csv"),
                "cleaned_test.csv": sha256_of(ART / "cleaned_test.csv"),
            },
        },
        "models": model_results,
        "champion": {
            "name": champion_name,
            "reported_model_name": champion_name,
            "candidates_considered": CHAMPION_CANDIDATES,
            "baseline_floor_included": "dummy_most_frequent",
        },
        "final_test_eval": {
            "top1_accuracy": model_results[champion_name]["top1_accuracy"],
            "top5_accuracy": model_results[champion_name]["top5_accuracy"],
            "top10_accuracy": model_results[champion_name]["top10_accuracy"],
        },
        "artifact": {"path": str(bundle_path), "sha256": sha256_of(bundle_path)},
    }
    (ART / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Saved champion bundle to {bundle_path.name} and metrics to metrics.json", flush=True)


if __name__ == "__main__":
    main()

