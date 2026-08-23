# ml/

Classifier pipeline for the Kaggle disease-prediction dataset (fixed train/test split):
`data_prep.py` → cleaning + `artifacts/symptom_vocabulary.json` · `train.py` / `evaluate.py` → LR vs RF comparison, champion model artifact.
Artifacts are regenerable; never re-split the source data.
