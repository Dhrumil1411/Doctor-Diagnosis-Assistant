import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from app.core.config import get_settings
from app.services.symptom_mapper import SymptomMapper, get_symptom_mapper


class ClassifierService:
    def __init__(self, artifacts_dir: Path):
        bundle = joblib.load(artifacts_dir / "model.joblib")
        self.model = bundle["model"]
        self.model_name: str = bundle.get("model_name", "classifier")
        self.feature_names: list[str] = list(bundle["feature_names"])
        self.diseases: list[str] = list(bundle.get("diseases", []))
        self.metadata: dict = bundle.get("metadata", {})
        vocab_path = artifacts_dir / "symptom_vocabulary.json"
        if vocab_path.exists():
            vocab = json.loads(vocab_path.read_text(encoding="utf-8"))
            self.display_names: dict[str, str] = {
                s["id"]: s["display_name"] for s in vocab.get("symptoms", [])
            }
        else:
            self.display_names = {}
        self._feature_index = {name: i for i, name in enumerate(self.feature_names)}
        self._known_features = set(self._feature_index)
        self._mapper = get_symptom_mapper()

    def known_symptom_ids(self) -> list[str]:
        return list(self._feature_index)

    def vocabulary(self) -> list[dict]:
        return [
            {
                "id": sid,
                "display_name": self.display_names.get(sid, sid.replace("_", " ").title()),
                "hpo_id": self._mapper.get_hpo_id(sid),
                "category": self._mapper.get_category(sid),
            }
            for sid in sorted(self._feature_index)
        ]

    def predict(self, symptom_ids: list[str], top_k: int = 5) -> dict:
        recognized: list[str] = []
        unknown: list[str] = []
        hpo_mappings: dict[str, str | None] = {}

        for raw_symptom in symptom_ids:
            resolved = self._mapper.resolve_symptom(raw_symptom, self._known_features)
            feat = resolved.get("feature_id")
            if feat and feat in self._feature_index:
                if feat not in recognized:
                    recognized.append(feat)
                hpo_mappings[feat] = resolved.get("hpo_id")
            else:
                norm = raw_symptom.strip().lower().replace(" ", "_").replace("-", "_")
                if norm not in unknown:
                    unknown.append(norm)

        x = np.zeros((1, len(self.feature_names)), dtype=np.float32)
        for symptom in recognized:
            x[0, self._feature_index[symptom]] = 1.0

        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(x)[0]
        else:
            proba = np.ones(len(self.model.classes_)) / len(self.model.classes_)

        classes = self.model.classes_
        order = np.argsort(proba)[::-1][:top_k]

        predictions = [
            {
                "rank": rank,
                "disease": str(classes[idx]),
                "confidence": round(float(proba[idx]), 4),
                "display_name": str(classes[idx]).title(),
            }
            for rank, idx in enumerate(order, start=1)
        ]
        return {
            "predictions": predictions,
            "recognized_symptoms": recognized,
            "unknown_symptoms": unknown,
            "hpo_mappings": hpo_mappings,
        }


@lru_cache
def get_classifier() -> ClassifierService:
    return ClassifierService(get_settings().model_artifacts_dir)

