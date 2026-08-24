import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from app.core.config import get_settings


class ClassifierService:
    def __init__(self, artifacts_dir: Path):
        bundle = joblib.load(artifacts_dir / "model.joblib")
        self.model = bundle["model"]
        self.model_name: str = bundle["model_name"]
        self.feature_names: list[str] = list(bundle["feature_names"])
        self.diseases: list[str] = list(bundle["diseases"])
        self.metadata: dict = bundle.get("metadata", {})
        vocab_path = artifacts_dir / "symptom_vocabulary.json"
        if vocab_path.exists():
            vocab = json.loads(vocab_path.read_text(encoding="utf-8"))
            self.display_names: dict[str, str] = {
                s["id"]: s["display_name"] for s in vocab["symptoms"]
            }
        else:
            self.display_names = {}
        self._feature_index = {name: i for i, name in enumerate(self.feature_names)}

    def known_symptom_ids(self) -> list[str]:
        return list(self._feature_index)

    def vocabulary(self) -> list[dict]:
        return [
            {"id": sid, "display_name": self.display_names.get(sid, sid.replace("_", " ").title())}
            for sid in sorted(self._feature_index)
        ]

    def predict(self, symptom_ids: list[str], top_k: int = 5) -> dict:
        normalized = [s.strip().lower().replace(" ", "_") for s in symptom_ids]
        unknown = sorted({s for s in normalized if s not in self._feature_index})
        recognized = [s for s in normalized if s in self._feature_index]

        x = np.zeros((1, len(self.feature_names)), dtype=np.float64)
        for symptom in recognized:
            x[0, self._feature_index[symptom]] = 1.0

        proba = self.model.predict_proba(x)[0]
        classes = self.model.classes_
        order = np.argsort(proba)[::-1][:top_k]

        predictions = [
            {
                "rank": rank,
                "disease": str(classes[idx]),
                "confidence": round(float(proba[idx]), 4),
                "display_name": self.display_names.get(str(classes[idx])),
            }
            for rank, idx in enumerate(order, start=1)
        ]
        return {
            "predictions": predictions,
            "recognized_symptoms": recognized,
            "unknown_symptoms": unknown,
        }


@lru_cache
def get_classifier() -> ClassifierService:
    return ClassifierService(get_settings().model_artifacts_dir)
