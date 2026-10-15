from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "Data" / "Kaggle" / "diseases-symptoms-773" / "diseases-symptoms-773.csv"
OUT_DIR = ROOT / "ml" / "artifacts"
LABEL = "diseases"
RANDOM_STATE = 42
TEST_SIZE = 0.20


def clean_symptom_name(col: str) -> str:
    cleaned = col.strip().lower()
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned


def to_display_name(col_raw: str) -> str:
    cleaned = col_raw.strip()
    return " ".join(word.capitalize() for word in cleaned.split())


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading raw dataset from {RAW_PATH}...")
    df = pd.read_csv(RAW_PATH)
    raw_shape = list(df.shape)
    print(f"Raw shape: {raw_shape}")

    if LABEL not in df.columns:
        raise ValueError(f"Label column {LABEL!r} not found in {df.columns}")

    df[LABEL] = df[LABEL].astype(str).str.strip()

    raw_symptom_cols = [c for c in df.columns if c != LABEL]
    symptom_mapping = {c: clean_symptom_name(c) for c in raw_symptom_cols}

    # Verify no duplicate IDs after normalization
    if len(set(symptom_mapping.values())) != len(raw_symptom_cols):
        raise ValueError("Collision detected in normalized symptom column names")

    df = df.rename(columns=symptom_mapping)
    symptom_ids = [symptom_mapping[c] for c in raw_symptom_cols]

    # Check for NaN or non-binary values
    if df.isna().any().any():
        raise ValueError("NaN cells found in dataset")

    for col in symptom_ids:
        bad = set(pd.unique(df[col])) - {0, 1}
        if bad:
            raise ValueError(f"Column {col!r} contains non-binary values: {bad}")

    diseases = sorted(df[LABEL].unique())
    n_diseases = len(diseases)
    n_symptoms = len(symptom_ids)

    print(f"Cleaned dataset: {len(df)} rows, {n_symptoms} symptoms, {n_diseases} diseases")

    # Split into train and test preserving singleton classes in train
    class_counts = df[LABEL].value_counts()
    singletons = class_counts[class_counts < 2].index
    df_singletons = df[df[LABEL].isin(singletons)]
    df_multi = df[~df[LABEL].isin(singletons)]

    train_multi, test_multi = train_test_split(
        df_multi,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=df_multi[LABEL],
    )

    train_df = pd.concat([train_multi, df_singletons], ignore_index=True)
    test_df = test_multi.reset_index(drop=True)

    print(f"Split complete: train={len(train_df)}, test={len(test_df)}")

    # Build symptom vocabulary
    vocabulary = {
        "dataset": "Diseases and Symptoms Dataset (Kaggle)",
        "label_field": LABEL,
        "n_symptoms": n_symptoms,
        "n_diseases": n_diseases,
        "symptoms": [
            {
                "id": symptom_mapping[raw_col],
                "display_name": to_display_name(raw_col),
                "column": symptom_mapping[raw_col],
                "raw_name": raw_col,
            }
            for raw_col in raw_symptom_cols
        ],
        "diseases": diseases,
    }

    vocab_path = OUT_DIR / "symptom_vocabulary.json"
    vocab_path.write_text(json.dumps(vocabulary, indent=2), encoding="utf-8")
    train_df.to_csv(OUT_DIR / "cleaned_train.csv", index=False)
    test_df.to_csv(OUT_DIR / "cleaned_test.csv", index=False)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(RAW_PATH),
        "raw_shape": raw_shape,
        "outputs": {
            "train": str(OUT_DIR / "cleaned_train.csv"),
            "test": str(OUT_DIR / "cleaned_test.csv"),
            "vocabulary": str(vocab_path),
        },
        "integrity": {
            "train_rows": len(train_df),
            "test_rows": len(test_df),
            "symptom_count": n_symptoms,
            "disease_count": n_diseases,
            "singleton_classes_preserved": len(singletons),
        },
    }
    (OUT_DIR / "prep_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\nVocabulary and cleaned CSVs written to {OUT_DIR}")


if __name__ == "__main__":
    main()

