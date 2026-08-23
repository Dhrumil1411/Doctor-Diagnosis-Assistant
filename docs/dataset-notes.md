# Dataset Notes — disease-prediction-42

Findings from the Step-1 audit of the raw CSVs, and what cleaning did about each.
Regenerate everything via `.venv\Scripts\python.exe ml\data_prep.py`; full machine-readable detail in `ml/artifacts/prep_report.json`.

## Reality vs. advertised numbers

| Claimed | Actual (this file set) | Explanation |
|---|---|---|
| 132 symptoms | **131 unique symptoms** | Header contains a duplicated column name (`fluid_overload` ×2); upstream "132" counted it twice |
| 42 diseases | **41 diseases** | Both files contain exactly 41 distinct prognoses |

## Quirks found and resolutions

1. **Duplicate column `fluid_overload`** — pandas reads the second occurrence as `fluid_overload.1`. Audit showed twin #1 is an all-zero dead column; all 114 positive signals live in twin #2. Resolution: OR-merge variants under the canonical name (equivalent here to keeping the informative one). A naive "keep first" dedupe would have silently destroyed data.
2. **Phantom trailing column (`Unnamed: 133`, Training only)** — artifact of a trailing comma in the header row; 0 non-null cells. Dropped after asserting emptiness.
3. **Space-broken column names (×3)** — `spotting_ urination`, `foul_smell_of urine`, `dischromic _patches` → spaces removed.
4. **Whitespace-padded labels (×2)** — `'Diabetes '` and `'Hypertension '` carry trailing spaces. Labels stripped; per-class counts unchanged.
5. **Cosmetic, left as-is:** label `(vertigo) Paroymsal  Positional Vertigo` contains an internal double space. Kept verbatim so mappings against external notebooks/docs stay trivial.

## Integrity guarantees enforced by `ml/data_prep.py`

- Row counts preserved: Train 4,920 · Test 42 — split used AS-IS, never merged or re-split
- Per-class label distributions identical pre/post cleaning (both sides normalized identically)
- Post-clean schemas identical and same-ordered across train/test (131 symptoms + `prognosis`)
- All symptom values strictly ∈ {0, 1}; zero NaN cells anywhere after cleaning
- No test label unseen in training

## Modeling caveats carried forward

- Classes perfectly balanced (120 rows each in training) — class-weighting largely moot, but harmless to keep
- `Testing.csv` holds just 42 rows across 41 classes (several classes have a single test case): per-class metrics there are noise. Strategy: model selection via stratified CV inside `cleaned_train.csv`; touch the test set once, at the end of Step 2
- Symptoms are binary presence flags — severity/duration fields from the intake form cannot feed this classifier; they go to the LLM layer instead
