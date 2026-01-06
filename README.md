## Apple Maps Experience Intelligence (Reddit → NLP → Dashboard)

## 🔗 Live Dashboard
 https://apple-maps-experience-intelligence-d8rr4gmsgb23bzzdfpuds9.streamlit.app/


## What this project does
This project turns **public Reddit discussions about Apple Maps** into structured, decision-ready insights.

Instead of manually reading posts, the notebook:
1) Collects Apple Maps–related threads from Reddit (posts + comments)  
2) Cleans and standardizes text  
3) Runs sentiment + “pain intensity” scoring  
4) Categorizes each thread into product themes (routing, POI/search, UI/CarPlay, etc.)  
5) Exports clean CSVs and generates a **Streamlit dashboard** to explore results

The end result is a lightweight “experience intelligence” workflow: **What are users complaining about, how severe is it, and what themes show up most often?**

---

## Data used (from the notebook)
- **Raw dataset loaded:** `273` Reddit posts (RangeIndex: 273 entries)
- **Threads analyzed in the final metrics table:** `228` threads (`[228 rows x 16 columns]`)
- Subreddits used (configured in the notebook): `apple`, `applemaps`
- Time window (configured in the notebook): last `8` months

---

## Key outputs / metrics (verified from notebook)
### Confidence signal (based on scraped comment volume)
- **Low confidence:** `176` threads  
- **Medium confidence:** `39` threads  
- **High confidence:** `13` threads  

### Pain severity buckets (weighted pain score)
- **Low:** `106`
- **Medium:** `53`
- **High:** `42`
- **Critical:** `27`

### Theme coverage (threads per theme)
The analysis assigns each thread into one of these themes (threads count):
- `navigation_routing_traffic`: **55**
- `ui_ux_carplay`: **37**
- `search_poi_data`: **13**
- `policy_strategy`: **11**
- `transit_walk_bike`: **7**
- `performance_reliability`: **1**
- `other`: **104**

> Note: The notebook keeps an “other” bucket for threads that don’t strongly match a specific theme.

---

## What’s inside the analysis table (what the dashboard uses)
Each thread includes structured fields such as:
- Post sentiment score + class (e.g., positive/neutral/negative)
- Comment sentiment distribution (neg/neu/pos rates)
- Scraped comment count
- Weighted pain score + pain bucket
- Theme label
- Cleaned text fields for evidence and review

---

## How to run
### Option A — Run the notebook end-to-end
Open and run:
- `apple_maps_experience_intel_clean_v6_exports_dashboard_fixed.ipynb`

This notebook also writes an export bundle:
- `outputs/` (analysis-ready CSV exports)
- `app.py` (Streamlit dashboard)
- `requirements_dashboard.txt`

### Option B — Run the Streamlit dashboard
After running the notebook (so outputs exist):

```bash
pip install -r requirements_dashboard.txt
streamlit run app.py
