from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "Data" / "Kaggle" / "disease-prediction-42"
OUT_DIR = ROOT / "ml" / "artifacts"
DOCS_DIR = ROOT / "docs"
LABEL = "prognosis"

EXPECTED_ROWS = {"Training.csv": 4920, "Testing.csv": 42}
MIN_SYMPTOMS = 100


def read_and_clean(path: Path) -> tuple[pd.DataFrame, dict]:
    actions: dict = {"file": path.name, "dropped_unnamed": [], "merged_duplicates": {}, "renamed_spaces": {}}
    df = pd.read_csv(path)
    actions["raw_shape"] = list(df.shape)

    unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
    for col in unnamed:
        if df[col].notna().any():
            raise ValueError(f"{path.name}: unnamed column {col!r} unexpectedly contains data")
    if unnamed:
        df = df.drop(columns=unnamed)
        actions["dropped_unnamed"] = unnamed

    variant_re = re.compile(r"^(?P<base>.+)\.(?P<idx>\d+)$")
    groups: dict[str, list[str]] = {}
    for col in df.columns:
        m = variant_re.match(str(col))
        if m:
            base = m.group("base")
            if base in df.columns:
                groups.setdefault(base, []).append(str(col))
    for base, variants in groups.items():
        series = [df[base]] + [df[v] for v in variants]
        merged = series[0].copy()
        for s in series[1:]:
            merged = ((merged == 1) | (s == 1)).astype(int)
        ones_before = [int(s.sum()) for s in series]
        df[base] = merged
        df = df.drop(columns=variants)
        actions["merged_duplicates"][base] = {"variants": [base] + variants, "ones_per_variant": ones_before}

    rename_map = {c: str(c).replace(" ", "") for c in df.columns if " " in str(c)}
    if rename_map:
        df = df.rename(columns=rename_map)
        actions["renamed_spaces"] = rename_map

    df[LABEL] = df[LABEL].astype(str).str.strip()

    symptom_cols = [c for c in df.columns if c != LABEL]
    if df.isna().any().any():
        raise ValueError(f"{path.name}: NaN cells remain after cleaning")
    for col in symptom_cols:
        bad = set(pd.unique(df[col])) - {0, 1}
        if bad:
            raise ValueError(f"{path.name}: column {col!r} has non-binary values: {bad}")

    actions["clean_shape"] = list(df.shape)
    return df, actions


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frames: dict[str, pd.DataFrame] = {}
    reports: dict[str, object] = {}
    raw_label_counts: dict[str, pd.Series] = {}

    for name, expected_rows in EXPECTED_ROWS.items():
        path = RAW_DIR / name
        raw = pd.read_csv(path)
        raw_label_counts[name] = raw[LABEL].astype(str).str.strip().value_counts().sort_index()
        df, actions = read_and_clean(path)

        if len(df) != expected_rows:
            raise AssertionError(f"{name}: row count changed {len(df)} != {expected_rows}")
        expected_cols = (actions["raw_shape"][1]
                         - len(actions["dropped_unnamed"])
                         - sum(len(v["variants"]) - 1 for v in actions["merged_duplicates"].values()))
        if df.shape[1] != expected_cols:
            raise AssertionError(f"{name}: expected {expected_cols} columns after cleaning, got {df.shape[1]}")

        cleaned_counts = df[LABEL].value_counts().sort_index()
        if not cleaned_counts.equals(raw_label_counts[name]):
            raise AssertionError(f"{name}: label distribution changed during cleaning")
        if int(cleaned_counts.sum()) != len(df):
            raise AssertionError(f"{name}: label count mismatch")

        frames[name] = df
        reports[name] = actions
        print(f"{name}: {actions['raw_shape']} -> {actions['clean_shape']} | "
              f"unnamed dropped: {len(actions['dropped_unnamed'])} | "
              f"duplicates merged: {list(actions['merged_duplicates'])} | "
              f"space-renames: {len(actions['renamed_spaces'])}")

    train_df = frames["Training.csv"]
    test_df = frames["Testing.csv"]

    if list(train_df.columns) != list(test_df.columns):
        raise AssertionError("train/test column schemas differ after cleaning")

    symptoms = list(train_df.columns)
    symptoms.remove(LABEL)
    if len(symptoms) < MIN_SYMPTOMS:
        raise AssertionError(f"implausibly few symptoms remaining: {len(symptoms)}")
    diseases = sorted(train_df[LABEL].unique())
    unseen = sorted(set(test_df[LABEL]) - set(train_df[LABEL]))
    if unseen:
        raise AssertionError(f"test contains labels absent from training: {unseen}")

    vocabulary = {
        "dataset": "Disease Prediction Using Machine Learning (Kaggle)",
        "label_field": LABEL,
        "n_symptoms": len(symptoms),
        "n_diseases": len(diseases),
        "symptoms": [
            {
                "id": col,
                "display_name": col.replace("_", " ").capitalize(),
                "column": col,
            }
            for col in symptoms
        ],
        "diseases": diseases,
    }

    vocab_path = OUT_DIR / "symptom_vocabulary.json"
    vocab_path.write_text(json.dumps(vocabulary, indent=2), encoding="utf-8")
    train_df.to_csv(OUT_DIR / "cleaned_train.csv", index=False)
    test_df.to_csv(OUT_DIR / "cleaned_test.csv", index=False)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {k: str(RAW_DIR / k) for k in EXPECTED_ROWS},
        "outputs": {
            "train": str(OUT_DIR / "cleaned_train.csv"),
            "test": str(OUT_DIR / "cleaned_test.csv"),
            "vocabulary": str(vocab_path),
        },
        "integrity": {
            "rows_unchanged": True,
            "split_preserved": True,
            "symptom_count": len(symptoms),
            "disease_count": len(diseases),
            "train_class_balance": {k: int(v) for k, v in train_df[LABEL].value_counts().sort_index().items()},
            "test_rows_per_class": {k: int(v) for k, v in test_df[LABEL].value_counts().sort_index().items()},
        },
        "cleaning_actions": reports,
    }
    (OUT_DIR / "prep_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\nsymptoms: {len(symptoms)} | diseases: {len(diseases)}")
    print(f"train class balance: min={min(report['integrity']['train_class_balance'].values())}, "
          f"max={max(report['integrity']['train_class_balance'].values())}")
    print(f"artifacts written to {OUT_DIR}")


if __name__ == "__main__":
    main()
