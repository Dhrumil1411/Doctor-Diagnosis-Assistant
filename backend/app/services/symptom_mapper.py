"""SymptomMapper Service - Standardized Human Phenotype Ontology (HPO) normalization layer.

Maps incoming doctor UI inputs, clinical notes, free-text terms, and DDXPlus evidence
concepts to standardized HPO identifiers (HP:XXXXXXX) and canonical 377-feature vector IDs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any


@dataclass(frozen=True)
class HpoConcept:
    hpo_id: str
    hpo_label: str
    category: str


# Core curated HPO ontology registry for primary clinical phenotype concepts
HPO_REGISTRY: dict[str, HpoConcept] = {
    # Constitutional / Systemic
    "fever": HpoConcept("HP:0001945", "Fever", "Constitutional"),
    "chills": HpoConcept("HP:0025143", "Chills", "Constitutional"),
    "fatigue": HpoConcept("HP:0012378", "Fatigue", "Constitutional"),
    "feeling_ill": HpoConcept("HP:0025255", "Malaise", "Constitutional"),
    "weight_loss": HpoConcept("HP:0001824", "Weight loss", "Constitutional"),
    "recent_weight_loss": HpoConcept("HP:0001824", "Weight loss", "Constitutional"),
    "weight_gain": HpoConcept("HP:0004324", "Weight gain", "Constitutional"),
    "sweating": HpoConcept("HP:0000975", "Hyperhidrosis", "Constitutional"),
    "thirst": HpoConcept("HP:0001959", "Polydipsia", "Constitutional"),
    "decreased_appetite": HpoConcept("HP:0004396", "Poor appetite", "Constitutional"),
    "excessive_appetite": HpoConcept("HP:0002591", "Polyphagia", "Constitutional"),
    "feeling_cold": HpoConcept("HP:0034336", "Cold intolerance", "Constitutional"),
    "feeling_hot_and_cold": HpoConcept("HP:0001945", "Temperature instability", "Constitutional"),

    # Respiratory
    "cough": HpoConcept("HP:0012735", "Cough", "Respiratory"),
    "coughing_up_sputum": HpoConcept("HP:0031956", "Productive cough", "Respiratory"),
    "coughing_up_blood": HpoConcept("HP:0002105", "Hemoptysis", "Respiratory"),
    "shortness_of_breath": HpoConcept("HP:0002094", "Dyspnea", "Respiratory"),
    "difficulty_breathing": HpoConcept("HP:0002094", "Dyspnea", "Respiratory"),
    "breathing_fast": HpoConcept("HP:0002789", "Tachypnea", "Respiratory"),
    "wheezing": HpoConcept("HP:0030828", "Wheezing", "Respiratory"),
    "nasal_congestion": HpoConcept("HP:0001742", "Nasal congestion", "Respiratory"),
    "sore_throat": HpoConcept("HP:0033050", "Pharyngitis / Sore throat", "Respiratory"),
    "hoarse_voice": HpoConcept("HP:0001609", "Hoarseness", "Respiratory"),
    "throat_swelling": HpoConcept("HP:0012028", "Laryngeal / Pharyngeal edema", "Respiratory"),
    "abnormal_breathing_sounds": HpoConcept("HP:0030828", "Abnormal respiratory sounds", "Respiratory"),
    "congestion_in_chest": HpoConcept("HP:0012735", "Chest congestion", "Respiratory"),
    "hurts_to_breath": HpoConcept("HP:0033668", "Pleuritic chest pain", "Respiratory"),

    # Cardiovascular
    "sharp_chest_pain": HpoConcept("HP:0001681", "Angina pectoris / Chest pain", "Cardiovascular"),
    "burning_chest_pain": HpoConcept("HP:0001681", "Retrosternal chest pain", "Cardiovascular"),
    "chest_tightness": HpoConcept("HP:0001681", "Chest pressure", "Cardiovascular"),
    "palpitations": HpoConcept("HP:0001962", "Palpitations", "Cardiovascular"),
    "irregular_heartbeat": HpoConcept("HP:0011675", "Arrhythmia", "Cardiovascular"),
    "fainting": HpoConcept("HP:0001279", "Syncope", "Cardiovascular"),
    "dizziness": HpoConcept("HP:0002321", "Vertigo / Dizziness", "Cardiovascular"),
    "leg_swelling": HpoConcept("HP:0010785", "Peripheral edema", "Cardiovascular"),
    "arm_swelling": HpoConcept("HP:0000969", "Upper extremity edema", "Cardiovascular"),

    # Gastrointestinal
    "nausea": HpoConcept("HP:0002018", "Nausea", "Gastrointestinal"),
    "vomiting": HpoConcept("HP:0002013", "Vomiting", "Gastrointestinal"),
    "vomiting_blood": HpoConcept("HP:0002248", "Hematemesis", "Gastrointestinal"),
    "sharp_abdominal_pain": HpoConcept("HP:0002027", "Abdominal pain", "Gastrointestinal"),
    "lower_abdominal_pain": HpoConcept("HP:0002027", "Lower abdominal pain", "Gastrointestinal"),
    "upper_abdominal_pain": HpoConcept("HP:0002027", "Epigastric pain", "Gastrointestinal"),
    "burning_abdominal_pain": HpoConcept("HP:0002027", "Burning abdominal pain", "Gastrointestinal"),
    "abdominal_distention": HpoConcept("HP:0003270", "Abdominal distention", "Gastrointestinal"),
    "swollen_abdomen": HpoConcept("HP:0003270", "Ascites / Abdominal distention", "Gastrointestinal"),
    "blood_in_stool": HpoConcept("HP:0002573", "Hematochezia", "Gastrointestinal"),
    "jaundice": HpoConcept("HP:0000952", "Jaundice", "Gastrointestinal"),
    "flatulence": HpoConcept("HP:0030084", "Flatulence", "Gastrointestinal"),
    "difficulty_in_swallowing": HpoConcept("HP:0002015", "Dysphagia", "Gastrointestinal"),
    "constipation": HpoConcept("HP:0002019", "Constipation", "Gastrointestinal"),
    "regurgitation": HpoConcept("HP:0002059", "Gastroesophageal reflux / Regurgitation", "Gastrointestinal"),
    "heartburn": HpoConcept("HP:0002020", "Heartburn", "Gastrointestinal"),

    # Neurological / Psychiatric
    "headache": HpoConcept("HP:0002315", "Headache", "Neurological"),
    "insomnia": HpoConcept("HP:0002360", "Sleep disturbance", "Neurological"),
    "anxiety_and_nervousness": HpoConcept("HP:0000739", "Anxiety", "Psychiatric"),
    "depression": HpoConcept("HP:0000716", "Depression", "Psychiatric"),
    "depressive_or_psychotic_symptoms": HpoConcept("HP:0000709", "Psychosis / Affective symptoms", "Psychiatric"),
    "abnormal_involuntary_movements": HpoConcept("HP:0001336", "Myoclonus / Involuntary movements", "Neurological"),
    "seizures": HpoConcept("HP:0001250", "Seizures", "Neurological"),
    "difficulty_speaking": HpoConcept("HP:0000750", "Dysarthria / Speech difficulty", "Neurological"),
    "diminished_hearing": HpoConcept("HP:0000365", "Hearing impairment", "Neurological"),
    "diminished_vision": HpoConcept("HP:0000505", "Visual impairment", "Neurological"),
    "double_vision": HpoConcept("HP:0000651", "Diplopia", "Neurological"),
    "blindness": HpoConcept("HP:0000618", "Blindness", "Neurological"),
    "numbness": HpoConcept("HP:0003474", "Hypoesthesia / Paresthesia", "Neurological"),

    # Dermatological
    "skin_rash": HpoConcept("HP:0009886", "Skin rash", "Dermatological"),
    "itching_of_skin": HpoConcept("HP:0000989", "Pruritus", "Dermatological"),
    "skin_irritation": HpoConcept("HP:0011123", "Inflammatory skin abnormality", "Dermatological"),
    "skin_growth": HpoConcept("HP:0001000", "Neoplasm of the skin", "Dermatological"),
    "skin_lesion": HpoConcept("HP:0000979", "Purpura / Skin lesion", "Dermatological"),
    "skin_swelling": HpoConcept("HP:0000969", "Edema of skin", "Dermatological"),
    "skin_dryness_peeling_scaliness_or_roughness": HpoConcept("HP:0000975", "Hyperkeratosis / Dry skin", "Dermatological"),
    "abnormal_appearing_skin": HpoConcept("HP:0000951", "Abnormality of the skin", "Dermatological"),

    # Genitourinary
    "frequent_urination": HpoConcept("HP:0000012", "Urinary urgency / Frequency", "Genitourinary"),
    "polyuria": HpoConcept("HP:0000103", "Polyuria", "Genitourinary"),
    "excessive_urination_at_night": HpoConcept("HP:0000017", "Nocturia", "Genitourinary"),
    "involuntary_urination": HpoConcept("HP:0000020", "Urinary incontinence", "Genitourinary"),
    "blood_in_urine": HpoConcept("HP:0000790", "Hematuria", "Genitourinary"),
    "painful_urination": HpoConcept("HP:0001947", "Dysuria", "Genitourinary"),
    "retention_of_urine": HpoConcept("HP:0000016", "Urinary retention", "Genitourinary"),
    "low_urine_output": HpoConcept("HP:0000079", "Oliguria", "Genitourinary"),

    # Musculoskeletal
    "leg_pain": HpoConcept("HP:0012514", "Lower limb pain", "Musculoskeletal"),
    "arm_pain": HpoConcept("HP:0034444", "Upper limb pain", "Musculoskeletal"),
    "back_pain": HpoConcept("HP:0003418", "Back pain", "Musculoskeletal"),
    "hip_pain": HpoConcept("HP:0030838", "Hip pain", "Musculoskeletal"),
    "joint_pain": HpoConcept("HP:0002829", "Arthralgia", "Musculoskeletal"),
    "elbow_weakness": HpoConcept("HP:0001324", "Muscle weakness", "Musculoskeletal"),
    "back_weakness": HpoConcept("HP:0001324", "Muscle weakness", "Musculoskeletal"),
    "bones_are_painful": HpoConcept("HP:0002653", "Bone pain", "Musculoskeletal"),
}

# Clinical synonyms, colloquial aliases, and legacy dataset variations mapping to 377 feature IDs
SYNONYM_MAP: dict[str, str] = {
    # Legacy / colloquial breathlessness aliases
    "breathlessness": "shortness_of_breath",
    "dyspnea": "shortness_of_breath",
    "difficulty_in_breathing": "difficulty_breathing",
    "sob": "shortness_of_breath",
    "short_of_breath": "shortness_of_breath",
    
    # Fever / Chills
    "high_fever": "fever",
    "pyrexia": "fever",
    "temperature": "fever",
    "rigors": "chills",
    "shaking_chills": "chills",

    # Chest & Cardiac
    "chest_pain": "sharp_chest_pain",
    "substernal_chest_pain": "sharp_chest_pain",
    "retrosternal_chest_pain": "burning_chest_pain",
    "crushing_chest_pain": "sharp_chest_pain",
    "angina": "sharp_chest_pain",
    "fast_heart_rate": "palpitations",
    "tachycardia": "palpitations",
    "racing_heart": "palpitations",
    "left_arm_pain": "arm_pain",

    # Abdominal / GI
    "abdominal_pain": "sharp_abdominal_pain",
    "stomach_pain": "sharp_abdominal_pain",
    "belly_ache": "sharp_abdominal_pain",
    "loss_of_appetite": "decreased_appetite",
    "anorexia": "decreased_appetite",
    "emesis": "vomiting",
    "throwing_up": "vomiting",
    "hematemesis": "vomiting_blood",
    "swollen_belly": "swollen_abdomen",
    "dysphagia": "difficulty_in_swallowing",
    "heart_burn": "heartburn",
    "acid_reflux": "regurgitation",

    # Skin / Dermatological
    "itching": "itching_of_skin",
    "pruritus": "itching_of_skin",
    "itchy_skin": "itching_of_skin",
    "rash": "skin_rash",
    "erythema": "skin_irritation",
    "skin_peeling": "skin_dryness_peeling_scaliness_or_roughness",
    "nodal_skin_eruptions": "skin_lesion",
    "dischromic_patches": "abnormal_appearing_skin",
    "skin_bumps": "skin_growth",

    # Urinary / Metabolic
    "frequent_micturition": "frequent_urination",
    "peeing_a_lot": "frequent_urination",
    "excessive_thirst": "thirst",
    "polydipsia": "thirst",
    "increased_hunger": "excessive_appetite",
    "excessive_hunger": "excessive_appetite",
    "polyphagia": "excessive_appetite",
    "hematuria": "blood_in_urine",
    "dysuria": "painful_urination",
    "pain_when_peeing": "painful_urination",

    # Neurological / Eyes
    "head_ache": "headache",
    "cephalea": "headache",
    "blurred_vision": "diminished_vision",
    "blurred_and_distorted_vision": "diminished_vision",
    "double_vision": "double_vision",
    "diplopia": "double_vision",
    "lightheadedness": "dizziness",
    "vertigo": "dizziness",
    "lethargy": "fatigue",
    "tiredness": "fatigue",
    "exhaustion": "fatigue",
    "phlegm": "coughing_up_sputum",
    "sputum": "coughing_up_sputum",
}

# Reverse HPO lookup table: HPO ID -> feature ID
HPO_TO_FEATURE: dict[str, str] = {}
for feat, concept in HPO_REGISTRY.items():
    if concept.hpo_id not in HPO_TO_FEATURE:
        HPO_TO_FEATURE[concept.hpo_id] = feat


def normalize_term(term: str) -> str:
    """Normalize any string to canonical lower_snake_case."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s_-]", "", term.strip().lower())
    return re.sub(r"[\s-]+", "_", cleaned)


class SymptomMapper:
    """Provides fast exact and synonym mapping to canonical feature IDs and HPO codes."""

    @staticmethod
    def resolve_symptom(input_str: str, known_features: set[str] | None = None) -> dict[str, Any]:
        """Resolve any raw symptom string or HPO code to canonical metadata."""
        raw = input_str.strip()
        upper_raw = raw.upper()

        # 1. Direct HPO ID lookup (e.g. 'HP:0001945')
        if upper_raw.startswith("HP:") and upper_raw in HPO_TO_FEATURE:
            feat = HPO_TO_FEATURE[upper_raw]
            concept = HPO_REGISTRY[feat]
            return {
                "feature_id": feat,
                "hpo_id": concept.hpo_id,
                "hpo_label": concept.hpo_label,
                "category": concept.category,
                "raw_input": raw,
            }

        normalized = normalize_term(raw)

        # 2. Check if normalized is already a normal feature ID
        canonical = normalized
        if known_features and canonical not in known_features:
            # 3. Check synonym mapping
            if normalized in SYNONYM_MAP:
                canonical = SYNONYM_MAP[normalized]
        elif normalized in SYNONYM_MAP:
            canonical = SYNONYM_MAP[normalized]

        # Check HPO registry for this canonical feature
        if canonical in HPO_REGISTRY:
            concept = HPO_REGISTRY[canonical]
            return {
                "feature_id": canonical,
                "hpo_id": concept.hpo_id,
                "hpo_label": concept.hpo_label,
                "category": concept.category,
                "raw_input": raw,
            }

        # Fallback: feature exists in classifier but not explicitly registered in HPO table
        is_known = (known_features is None) or (canonical in known_features)
        display = canonical.replace("_", " ").title()
        return {
            "feature_id": canonical if is_known else None,
            "hpo_id": None,
            "hpo_label": display,
            "category": "General Clinical Observation",
            "raw_input": raw,
        }

    @staticmethod
    def get_hpo_id(feature_id: str) -> str | None:
        """Return HPO ID for a given canonical feature ID."""
        concept = HPO_REGISTRY.get(feature_id)
        return concept.hpo_id if concept else None

    @staticmethod
    def get_hpo_label(feature_id: str) -> str | None:
        """Return HPO label for a given canonical feature ID."""
        concept = HPO_REGISTRY.get(feature_id)
        return concept.hpo_label if concept else None

    @staticmethod
    def get_category(feature_id: str) -> str:
        """Return clinical category for a given feature ID."""
        concept = HPO_REGISTRY.get(feature_id)
        return concept.category if concept else "General"

    @staticmethod
    def get_feature_id_from_hpo(hpo_id: str) -> str | None:
        """Return feature ID for a given HPO ID."""
        return HPO_TO_FEATURE.get(hpo_id.upper().strip())


@lru_cache
def get_symptom_mapper() -> SymptomMapper:
    return SymptomMapper()
