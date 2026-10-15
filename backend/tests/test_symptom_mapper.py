import pytest
from app.services.symptom_mapper import SymptomMapper, get_symptom_mapper
from app.services.classifier import get_classifier


@pytest.fixture
def mapper():
    return get_symptom_mapper()


def test_mapper_direct_feature_resolution(mapper):
    res = mapper.resolve_symptom("fever")
    assert res["feature_id"] == "fever"
    assert res["hpo_id"] == "HP:0001945"
    assert res["category"] == "Constitutional"


def test_mapper_direct_hpo_id_resolution(mapper):
    res = mapper.resolve_symptom("HP:0001945")
    assert res["feature_id"] == "fever"
    assert res["hpo_id"] == "HP:0001945"
    assert res["hpo_label"] == "Fever"

    res_lower = mapper.resolve_symptom("hp:0002094")
    assert res_lower["feature_id"] == "shortness_of_breath"
    assert res_lower["hpo_id"] == "HP:0002094"


def test_mapper_synonym_resolution(mapper):
    # breathlessness -> shortness_of_breath (HP:0002094)
    res1 = mapper.resolve_symptom("breathlessness")
    assert res1["feature_id"] == "shortness_of_breath"
    assert res1["hpo_id"] == "HP:0002094"

    # high_fever -> fever (HP:0001945)
    res2 = mapper.resolve_symptom("high_fever")
    assert res2["feature_id"] == "fever"
    assert res2["hpo_id"] == "HP:0001945"

    # chest pain -> sharp_chest_pain (HP:0001681)
    res3 = mapper.resolve_symptom("chest pain")
    assert res3["feature_id"] == "sharp_chest_pain"
    assert res3["hpo_id"] == "HP:0001681"

    # stomach pain -> sharp_abdominal_pain (HP:0002027)
    res4 = mapper.resolve_symptom("stomach pain")
    assert res4["feature_id"] == "sharp_abdominal_pain"
    assert res4["hpo_id"] == "HP:0002027"

    # itching -> itching_of_skin (HP:0000989)
    res5 = mapper.resolve_symptom("itching")
    assert res5["feature_id"] == "itching_of_skin"
    assert res5["hpo_id"] == "HP:0000989"


def test_mapper_unknown_term_fallback(mapper):
    res = mapper.resolve_symptom("completely_unregistered_symptom_xyz")
    assert res["feature_id"] == "completely_unregistered_symptom_xyz"
    assert res["hpo_id"] is None
    assert res["hpo_label"] == "Completely Unregistered Symptom Xyz"


def test_classifier_predict_with_hpo_and_synonyms():
    clf = get_classifier()
    # Query with a mix of HPO IDs, synonyms, and exact feature IDs
    res = clf.predict(["HP:0001945", "breathlessness", "cough", "sharp_chest_pain"])
    assert "fever" in res["recognized_symptoms"]
    assert "shortness_of_breath" in res["recognized_symptoms"]
    assert "cough" in res["recognized_symptoms"]
    assert "sharp_chest_pain" in res["recognized_symptoms"]
    assert len(res["predictions"]) > 0
    assert "hpo_mappings" in res
    assert res["hpo_mappings"].get("fever") == "HP:0001945"
    assert res["hpo_mappings"].get("shortness_of_breath") == "HP:0002094"


def test_classifier_vocabulary_contains_hpo_metadata():
    clf = get_classifier()
    vocab = clf.vocabulary()
    assert len(vocab) == 377
    fever_entry = next(v for v in vocab if v["id"] == "fever")
    assert fever_entry["hpo_id"] == "HP:0001945"
    assert fever_entry["display_name"] == "Fever"
