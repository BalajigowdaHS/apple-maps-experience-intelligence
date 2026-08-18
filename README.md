# Apple Maps Experience Intelligence

[Live Streamlit dashboard](https://apple-maps-experience-intelligence-d8rr4gmsgb23bzzdfpuds9.streamlit.app/)

This project turns public Reddit conversations about Apple Maps into an auditable product-feedback dashboard. The pipeline collects posts and comments, cleans and classifies them, scores sentiment and pain, and exports thread-level evidence for product triage.

## Current dataset

- 228 analyzed Reddit threads from `r/apple` and `r/applemaps`
- 1,002 scraped comments
- 148 threads with at least one scraped comment
- 7 theme buckets and 6 post-type buckets
- Coverage: May 14, 2025 through December 31, 2025

The dataset is a directional public-discourse sample. It is not representative of the full Apple Maps user population.

## Dashboard metrics

- **Comment sentiment share** is weighted by actual comment counts. Threads without comments do not dilute the rate.
- **Pain intensity (0–1)** combines post negativity, negative-comment share, and directional negative consensus. Positive consensus cannot increase pain.
- **Confidence-adjusted pain** discounts threads with limited comment evidence using weights of 0.60, 0.85, and 1.00 for low, medium, and high confidence.
- **Theme priority score** is the sum of confidence-adjusted pain across a theme, combining frequency, severity, and evidence strength.
- **Triage** sends well-supported high/critical signals to `action_now`, thin severe signals to `investigate`, and low-pain signals to `monitor`.

Original notebook-exported pain fields are retained in memory as `legacy_pain_intensity` and `legacy_weighted_pain` for auditability. The dashboard uses the corrected definitions above.

## Project structure

```text
app.py                                  Streamlit dashboard
src/metrics.py                          Tested metric definitions
tests/test_metrics.py                   Metric regression tests
notebooks/Data_Collection.ipynb         Reddit collection workflow
notebooks/Data_Cleaning&Modling.ipynb   Cleaning, NLP, and export workflow
notebooks/outputs/                       Dashboard-ready CSV exports
data/raw/ and data/processed/            Source and normalized datasets
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The dashboard requirements are intentionally small for fast deployment. To rerun the NLP notebooks, install `requirements-notebook.txt` as well.

Run the lightweight metric tests with:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The app reads `notebooks/outputs/thread_metrics.csv` as its required source. Other output files provide optional evidence and precomputed exports.
