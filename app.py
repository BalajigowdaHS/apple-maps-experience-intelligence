# app.py — Apple Maps Experience Intel (Storyboard)
# 6 views: KPIs → theme priority → theme/type → drilldown → insights → methodology

from __future__ import annotations
from html import escape
from pathlib import Path
import pandas as pd
import streamlit as st

from src.metrics import enrich_metrics, theme_summary, weighted_rate

try:
    import altair as alt
except Exception:
    alt = None


# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Apple Maps Experience Review", page_icon="🗺️", layout="wide")


# -----------------------------
# CLEAN UI (Apple keynote minimal)
# -----------------------------
st.markdown(
    """
<style>
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1220px; }
header {visibility: hidden;}
h1,h2,h3 { letter-spacing: -0.02em; }
.small-muted { color: rgba(250,250,250,0.65); font-size: 0.95rem; }
.card {
  background: linear-gradient(145deg, rgba(39,110,241,0.09), rgba(255,255,255,0.025));
  border: 1px solid rgba(120,170,255,0.16);
  border-radius: 18px;
  padding: 18px 20px;
  min-height: 100%;
}
.quote {
  background: rgba(90,170,255,0.10);
  border: 1px solid rgba(90,170,255,0.22);
  border-radius: 12px;
  padding: 12px 14px;
}
hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 1.2rem 0; }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
[data-testid="stMetric"] {
  background: rgba(255,255,255,0.035);
  border: 1px solid rgba(255,255,255,0.09);
  padding: 14px 16px;
  border-radius: 16px;
}
[data-testid="stMetricLabel"] { min-height: 2.4rem; }
[data-baseweb="tab-list"] { gap: 0.4rem; }
[data-baseweb="tab"] { border-radius: 999px; padding: 0.55rem 0.9rem; }
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# PATHS (no hardcoding)
# -----------------------------
def project_root() -> Path:
    here = Path(__file__).resolve()
    # if app.py is inside src/, root is parent of src
    if here.parent.name.lower() == "src":
        return here.parent.parent
    return here.parent


ROOT = project_root()
OUTPUTS = ROOT / "notebooks" / "outputs"

THREAD_METRICS = OUTPUTS / "thread_metrics.csv"
THEME_RANK = OUTPUTS / "theme_rank.csv"
TOP_PAIN = OUTPUTS / "top_pain_threads.csv"
EVIDENCE = OUTPUTS / "evidence_comments.csv"


def require(path: Path) -> None:
    if not path.exists():
        st.error(
            f"Missing file:\n\n`{path}`\n\n"
            f"Expected exports in:\n\n`{OUTPUTS}`\n\n"
            "Fix:\n"
            "1) Run notebook export cells\n"
            "2) Confirm CSVs saved to notebooks/outputs/\n"
            "3) Re-run:  streamlit run app.py"
        )
        st.stop()


@st.cache_data(show_spinner=False)
def load_data():
    require(THREAD_METRICS)
    df_threads = pd.read_csv(THREAD_METRICS)

    df_theme = pd.read_csv(THEME_RANK) if THEME_RANK.exists() else pd.DataFrame()
    df_top = pd.read_csv(TOP_PAIN) if TOP_PAIN.exists() else pd.DataFrame()
    df_ev = pd.read_csv(EVIDENCE) if EVIDENCE.exists() else pd.DataFrame()

    # normalize dates
    for d in ["created_date"]:
        if d in df_threads.columns:
            df_threads[d] = pd.to_datetime(df_threads[d], errors="coerce")
        if d in df_top.columns:
            df_top[d] = pd.to_datetime(df_top[d], errors="coerce")

    # ensure thread_id exists if exported differently
    if "thread_id" not in df_threads.columns:
        if "index" in df_threads.columns:
            df_threads = df_threads.rename(columns={"index": "thread_id"})
        else:
            # sometimes it becomes "Unnamed: 0"
            for c in df_threads.columns:
                if "unnamed" in c.lower():
                    df_threads = df_threads.rename(columns={c: "thread_id"})
                    break

    df_threads = enrich_metrics(df_threads)
    return df_threads, df_theme, df_top, df_ev


df_threads, df_theme, df_top, df_ev = load_data()


# -----------------------------
# FORMATTERS
# -----------------------------
def fmt_num(x) -> str:
    if x is None or pd.isna(x):
        return "—"
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return str(x)

def fmt_score(x) -> str:
    if x is None or pd.isna(x):
        return "—"
    try:
        return f"{float(x):.3f}"
    except Exception:
        return str(x)

def fmt_pct(x) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x*100:.1f}%"

def clamp(text: str, n: int = 150) -> str:
    if not isinstance(text, str):
        return ""
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"
def shorten_url(u: str, n: int = 55) -> str:
    """
    Shorten long URLs for clean table display.
    Keeps UI readable while full URL is still available on click.
    """
    if not isinstance(u, str):
        return ""
    return u if len(u) <= n else u[: n - 3] + "..."


# -----------------------------
# NORTH STAR METRIC (simple, interpretable)
# -----------------------------
# Overall comment sentiment is weighted by the number of comments in each thread.
NEG_XP = weighted_rate(df_threads, "comment_neg_rate")
POS_XP = weighted_rate(df_threads, "comment_pos_rate")
NEU_XP = weighted_rate(df_threads, "comment_neu_rate")


# -----------------------------
# COVER
# -----------------------------
st.markdown("## Apple Maps Experience Intel")
st.markdown("<div class='small-muted'>Public feedback → themes → sentiment → pain → decision-ready triage</div>", unsafe_allow_html=True)

with st.expander("Data quality & definitions", expanded=False):
    threads_with_comments = int(df_threads["n_comments_scraped"].gt(0).sum())
    st.write(
        f"{len(df_threads):,} threads; {threads_with_comments:,} include scraped comments; "
        f"{int(df_threads['n_comments_scraped'].sum()):,} comments analyzed."
    )
    st.caption(
        "Comment sentiment is weighted by actual comment count. Pain uses directional negative "
        "consensus, and priority adjusts pain for evidence confidence."
    )


# -----------------------------
# TABS (6 views)
# -----------------------------
tabs = st.tabs([
    "1) Problem & KPIs",
    "2) Theme-level pain",
    "3) Theme × Post type",
    "4) Critical drilldown",
    "5) Key Insights & Recommendations",
    "6) Methodology"
])

# ============================================================
# PAGE 1 — Problem & KPIs
# ============================================================
with tabs[0]:
    # ============================================================
    # PAGE 1 — Problem & KPIs (no image, keynote minimal)
    # ============================================================

    st.markdown("## Apple Maps Experience Intel (Reddit)")
    st.markdown("<div class='small-muted'>Public feedback → structured themes → quantified pain → decision-ready priorities</div>", unsafe_allow_html=True)
    st.divider()

    # -----------------------------
    # 1) Business problem + why
    # -----------------------------
    a, b = st.columns([1.25, 1])

    with a:
        st.markdown("### The business problem")
        st.markdown(
            """
<div class="card">
<b>Goal:</b> Identify where Apple Maps <b>frustrates</b> or <b>delights</b> users using organic Reddit conversations,
then convert that noise into <b>actionable product priorities</b>.<br><br>
<b>Challenge:</b> Feedback is high-volume and unstructured — PMs can’t read every thread.<br>
<b>Solution:</b> A repeatable pipeline that <b>classifies</b> feedback into themes, <b>scores pain</b>, and provides <b>evidence</b> (quotes + links).
</div>
""",
            unsafe_allow_html=True,
        )

    with b:
        st.markdown("### What this delivers")
        st.markdown(
            """
<div class="card">
1) <b>Theme clarity</b> (routing, POI/search, UI, reliability, policy, …)<br>
2) <b>Prioritization</b> using confidence-adjusted theme burden + triage labels<br>
3) <b>Evidence pack</b> with representative comments + thread links
</div>
""",
            unsafe_allow_html=True,
        )

    st.divider()

    # -----------------------------
    # 2) Data sources + coverage
    # -----------------------------
    st.markdown("### Data sources (public signal)")
    left, right = st.columns([1, 1])

    sources = sorted(df_threads["subreddit"].dropna().unique().tolist()) if "subreddit" in df_threads.columns else []
    date_min = df_threads["created_date"].min() if "created_date" in df_threads.columns else None
    date_max = df_threads["created_date"].max() if "created_date" in df_threads.columns else None

    total_threads = len(df_threads)
    total_comments = df_threads["n_comments_scraped"].sum() if "n_comments_scraped" in df_threads.columns else None

    with left:
        st.markdown(
            """
<div class="card">
<b>Sources:</b> Reddit threads (posts + comments) mentioning Apple Maps<br><br>
<b>Unit of analysis:</b> <b>Thread</b> (one thread = one user story)<br>
<b>Why thread-level:</b> Lets us combine post intent + community reaction into one decision object.
</div>
""",
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            f"""
<div class="card">
<b>Coverage snapshot</b><br><br>
<b>Subreddits:</b> {", ".join(sources) if sources else "—"}<br>
<b>Time window:</b> {(date_min.date() if pd.notna(date_min) else "—")} → {(date_max.date() if pd.notna(date_max) else "—")}<br>
<b>Threads analyzed:</b> {fmt_num(total_threads)}<br>
<b>Comments scraped:</b> {fmt_num(total_comments)}
</div>
""",
            unsafe_allow_html=True,
        )

    st.divider()

    # -----------------------------
    # 3) North Star + KPI cards
    # -----------------------------
    st.markdown("### North Star & key KPIs")

    # Overall comment sentiment, weighted by the number of comments in each thread.
    neg_rate, pos_rate, neu_rate = NEG_XP, POS_XP, NEU_XP

    critical_threads = (df_threads["pain_bucket"] == "critical").sum() if "pain_bucket" in df_threads.columns else None
    high_threads = (df_threads["pain_bucket"].isin(["high", "critical"])).sum() if "pain_bucket" in df_threads.columns else None

    action_now_threads = (df_threads["triage_label"] == "action_now").sum()

    # Portfolio priority: additive confidence-adjusted pain; exclude catch-all "other".
    top_theme = None
    if "theme" in df_threads.columns:
        tmp = theme_summary(df_threads)
        tmp = tmp[tmp["theme"].ne("other")]
        if not tmp.empty:
            top_theme = str(tmp.iloc[0]["theme"]).replace("_", " ").title()

    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric("Negative comment share", fmt_pct(neg_rate))
    k2.metric("Positive comment share", fmt_pct(pos_rate))
    k3.metric("High / critical threads", fmt_num(high_threads), help="Severity only; evidence confidence is shown separately.")
    k4.metric("Action now", fmt_num(action_now_threads), help="High/critical pain with medium or high comment confidence.")
    k5.metric("Top named priority", top_theme if top_theme else "—")

    st.markdown(
        """
<div class="small-muted">
Comment shares represent comments, not an average of threads. “Action now” requires both elevated pain and enough
community evidence; low-confidence severe threads remain in “investigate.”
</div>
""",
        unsafe_allow_html=True,
    )

    st.divider()

    # -----------------------------
    # 4) User voice preview
    # -----------------------------
    st.markdown("### The user voice (evidence preview)")

    quotes = []
    if not df_ev.empty:
        if "representative_comments" in df_ev.columns:
            quotes = df_ev["representative_comments"].dropna().astype(str).head(3).tolist()
        else:
            for col in ["text_clean", "comment", "text"]:
                if col in df_ev.columns:
                    quotes = df_ev[col].dropna().astype(str).head(3).tolist()
                    break

    if not quotes and "post_text_clean" in df_threads.columns:
        quotes = df_threads["post_text_clean"].dropna().astype(str).head(3).tolist()

    if quotes:
        q1, q2, q3 = st.columns(3)
        cols = [q1, q2, q3]
        for i, q in enumerate(quotes[:3]):
            with cols[i]:
                st.markdown(f"<div class='quote'>“{escape(clamp(q, 170))}”</div>", unsafe_allow_html=True)
    else:
        st.info("No evidence text found yet. Re-run notebook export for evidence_comments.csv")

    st.divider()

    # -----------------------------
    # 5) Storyboard roadmap (sets up Page 2+)
    # -----------------------------
    st.markdown("### What happens next (the storyboard)")
    st.markdown(
        """
<div class="card">
<b>Page 2:</b> Theme priority ranking (severity + evidence + frequency)<br>
<b>Page 3:</b> Theme × Post Type (complaints vs bugs vs praise)<br>
<b>Page 4:</b> Critical threads drill-down (full context + most negative comments)<br>
<b>Page 5:</b> Live insights & recommendations<br>
<b>Page 6:</b> Methodology & metric definitions (trust layer)
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# PAGE 2 — Theme-level pain
# ============================================================
with tabs[1]:
    st.markdown("## Theme priorities")
    st.markdown(
        "<div class='small-muted'>Separate severity, reach, and evidence strength before deciding what to act on.</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    # -----------------------------
    # Build theme table (robust to missing cols)
    # -----------------------------
    needed = ["theme"]
    if "theme" not in df_threads.columns:
        st.warning("`theme` column not found in thread_metrics.csv. Re-run the notebook export.")
        st.stop()

    df_t = df_threads.copy()

    theme_tbl = theme_summary(df_t)

    # -----------------------------
    # Controls (clean + minimal)
    # -----------------------------
    c1, c2, c3 = st.columns([1.2, 1, 1])

    with c1:
        sort_mode = st.selectbox(
            "Sort themes by",
            options=[
                "Priority score (recommended)",
                "Avg pain intensity",
                "Avg confidence-adjusted pain",
                "Volume (threads)",
            ],
            index=0
        )

    with c2:
        top_n = st.slider("Show top N themes", 5, 20, 10)

    with c3:
        show_details = st.toggle("Show details table", value=True)

    # Sorting logic
    if sort_mode.startswith("Priority"):
        theme_tbl = theme_tbl.sort_values("priority_score", ascending=False)
    elif sort_mode.startswith("Avg pain"):
        theme_tbl = theme_tbl.sort_values("avg_pain_intensity", ascending=False) if "avg_pain_intensity" in theme_tbl.columns else theme_tbl
    elif sort_mode.startswith("Avg confidence"):
        theme_tbl = theme_tbl.sort_values("avg_weighted_pain", ascending=False) if "avg_weighted_pain" in theme_tbl.columns else theme_tbl
    else:
        theme_tbl = theme_tbl.sort_values("threads", ascending=False)

    view = theme_tbl.head(top_n).copy()

    # -----------------------------
    # Layout: two visuals (or compact tables)
    # -----------------------------
    left, right = st.columns([1.1, 0.9])

    # === Chart 1: confidence-adjusted priority burden
    with left:
        st.markdown("<div class='card'><b>Priority ranking</b></div>", unsafe_allow_html=True)

        if alt is not None and "priority_score" in view.columns:
            bar = (
                alt.Chart(view)
                .mark_bar(cornerRadiusEnd=5, color="#4F8DF7")
                .encode(
                    y=alt.Y("theme:N", sort="-x", title=None),
                    x=alt.X("priority_score:Q", title="Priority score"),
                    tooltip=[
                        "theme",
                        alt.Tooltip("threads:Q"),
                        alt.Tooltip("total_comments:Q"),
                        alt.Tooltip("avg_pain_intensity:Q", format=".3f"),
                        alt.Tooltip("priority_score:Q", format=".3f"),
                        alt.Tooltip("action_now:Q"),
                    ],
                )
                .properties(height=320)
            )
            st.altair_chart(bar, width="stretch")
        else:
            st.info("Chart unavailable. Showing the compact ranking instead.")
            st.dataframe(view[["theme", "threads", "total_comments", "priority_score"]], width="stretch", height=320)

        st.markdown(
            "<div class='small-muted'>Priority score = sum of confidence-adjusted pain across threads. It captures severity, evidence, and frequency without allowing a single thread to lead the portfolio.</div>",
            unsafe_allow_html=True,
        )

    # === Chart 2: Sentiment mix by theme
    with right:
        st.markdown("<div class='card'><b>Theme sentiment mix (comment-weighted)</b></div>", unsafe_allow_html=True)

        mix_cols = ["comment_neg_rate", "comment_neu_rate", "comment_pos_rate"]
        if all(c in view.columns for c in mix_cols):
            mix = view[["theme"] + mix_cols].copy()

            # long format for stacked bar
            mix_long = mix.melt("theme", var_name="sentiment", value_name="rate")
            mix_long["sentiment"] = mix_long["sentiment"].map({
                "comment_neg_rate": "Negative",
                "comment_neu_rate": "Neutral",
                "comment_pos_rate": "Positive",
            })

            if alt is not None:
                stacked = (
                    alt.Chart(mix_long)
                    .mark_bar()
                    .encode(
                        x=alt.X("theme:N", sort="-y", title=None),
                        y=alt.Y("rate:Q", stack="normalize", title="Share of comments"),
                        color=alt.Color("sentiment:N", title=None),
                        tooltip=[
                            "theme",
                            "sentiment",
                            alt.Tooltip("rate:Q", format=".2f"),
                        ],
                    )
                    .properties(height=320)
                )
                st.altair_chart(stacked, width="stretch")
            else:
                st.dataframe(mix, width="stretch", height=320)

            st.markdown(
                "<div class='small-muted'>Interpretation: Negative share shows where frustration dominates; Positive share shows where users feel value.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Comment sentiment rate columns not found (comment_neg_rate/neu/pos). Re-run the notebook thread-metrics section.")

    st.divider()

    # -----------------------------
    # Details table (not wide / not cluttered)
    # -----------------------------
    if show_details:
        st.markdown("### Theme KPI table (compact)")

        cols = ["theme", "threads", "total_comments", "priority_score", "high_critical_rate", "action_now"]
        for c in ["avg_pain_intensity", "avg_weighted_pain"]:
            if c in theme_tbl.columns:
                cols.append(c)

        for c in ["comment_neg_rate", "comment_neu_rate", "comment_pos_rate"]:
            if c in theme_tbl.columns:
                cols.append(c)

        show_tbl = theme_tbl[cols].copy()

        # friendly formatting
        for c in ["avg_pain_intensity", "avg_weighted_pain", "priority_score", "high_critical_rate"]:
            if c in show_tbl.columns:
                show_tbl[c] = show_tbl[c].map(lambda x: float(x) if pd.notna(x) else x)

        for c in ["comment_neg_rate", "comment_neu_rate", "comment_pos_rate"]:
            if c in show_tbl.columns:
                show_tbl[c] = show_tbl[c].map(lambda x: float(x) if pd.notna(x) else x)

        # show fewer rows + readable height
        st.dataframe(show_tbl.head(top_n), width="stretch", height=360)

        with st.expander("How to read this table", expanded=False):
            st.markdown(
                """
- **threads**: number of unique user stories (threads) in this theme  
- **total_comments**: engagement depth (how much community reaction exists)  
- **priority_score**: total confidence-adjusted pain across a theme
- **avg_pain_intensity**: mean severity; **avg_weighted_pain** discounts thin evidence
- **action_now**: high/critical threads with medium/high evidence confidence
- **comment_neg/neu/pos_rate**: share of comments by sentiment (weighted by comment count where possible)  
                """
            )

# ============================================================
# PAGE 3 — Theme × Post type
# ============================================================
with tabs[2]:
    st.markdown("## Theme × post type (what kind of feedback is each theme getting?)")
    st.markdown(
        "<div class='small-muted'>This view tells a PM: “Is Navigation pain mostly complaints? Are POI issues mostly bug reports? Is UI mixed praise + complaints?”</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    if "theme" not in df_threads.columns or "post_type" not in df_threads.columns:
        st.warning("Missing `theme` or `post_type` in thread_metrics.csv. Re-run notebook export.")
        st.stop()

    df_t = df_threads.copy()

    # -----------------------------
    # Controls (simple)
    # -----------------------------
    c1, c2, c3 = st.columns([1.1, 1, 1])

    with c1:
        metric_mode = st.selectbox(
            "Metric for heatmap",
            ["Avg pain intensity", "Avg confidence-adjusted pain", "Count of threads"],
            index=0,
        )

    with c2:
        min_threads = st.slider("Hide rare combinations (min threads)", 1, 10, 2)

    with c3:
        show_table = st.toggle("Show compact table", value=True)

    # choose metric column
    if metric_mode == "Avg pain intensity":
        if "pain_intensity" not in df_t.columns:
            st.warning("pain_intensity not found. Switching to Count of threads.")
            metric_mode = "Count of threads"
        metric_col = "pain_intensity"
        agg_func = "mean"
        value_label = "avg_pain_intensity"
    elif metric_mode == "Avg confidence-adjusted pain":
        if "weighted_pain" not in df_t.columns:
            st.warning("weighted_pain not found. Switching to Avg pain intensity.")
            metric_mode = "Avg pain intensity"
            metric_col = "pain_intensity"
            agg_func = "mean"
            value_label = "avg_pain_intensity"
        else:
            metric_col = "weighted_pain"
            agg_func = "mean"
            value_label = "avg_weighted_pain"
    else:
        metric_col = None
        agg_func = None
        value_label = "threads"

    # -----------------------------
    # Build pivot table
    # -----------------------------
    if metric_mode == "Count of threads":
        pivot = (
            df_t.groupby(["theme", "post_type"])
            .size()
            .reset_index(name="threads")
        )
    else:
        pivot = (
            df_t.groupby(["theme", "post_type"], as_index=False)
            .agg(
                threads=("theme", "count"),
                value=(metric_col, agg_func),
            )
            .rename(columns={"value": value_label})
        )

    # filter rare combos
    pivot = pivot[pivot["threads"] >= min_threads].copy()

    # wide table for heatmap
    if metric_mode == "Count of threads":
        wide = pivot.pivot(index="theme", columns="post_type", values="threads").fillna(0)
    else:
        wide = pivot.pivot(index="theme", columns="post_type", values=value_label)

    # Order themes by total threads (desc) for readability
    theme_order = (
        df_t.groupby("theme").size().sort_values(ascending=False).index.tolist()
    )
    wide = wide.reindex(index=[t for t in theme_order if t in wide.index])

    # Order post_types by total presence
    pt_order = (
        df_t.groupby("post_type").size().sort_values(ascending=False).index.tolist()
    )
    wide = wide.reindex(columns=[p for p in pt_order if p in wide.columns])

    # -----------------------------
    # Heatmap (clean, not cluttered)
    # -----------------------------
    st.markdown("<div class='card'><b>Heatmap view</b></div>", unsafe_allow_html=True)

    if alt is not None and wide.shape[0] > 0 and wide.shape[1] > 0:
        heat_df = wide.reset_index().melt("theme", var_name="post_type", value_name="value")
        heat_df["value"] = pd.to_numeric(heat_df["value"], errors="coerce")

        # For counts, show integers; for avg metrics, show 3 decimals
        fmt = ".0f" if metric_mode == "Count of threads" else ".3f"

        heat = (
            alt.Chart(heat_df)
            .mark_rect()
            .encode(
                x=alt.X("post_type:N", title=None),
                y=alt.Y("theme:N", title=None, sort=theme_order),
                color=alt.Color("value:Q", title=metric_mode),
                tooltip=[
                    "theme",
                    "post_type",
                    alt.Tooltip("value:Q", format=fmt, title=metric_mode),
                ],
            )
            .properties(height=min(420, 34 * max(6, len(wide.index))))
        )

        # Overlay numbers (optional but readable here)
        text = (
            alt.Chart(heat_df)
            .mark_text(baseline="middle")
            .encode(
                x="post_type:N",
                y=alt.Y("theme:N", sort=theme_order),
                text=alt.Text("value:Q", format=fmt),
            )
        )

        st.altair_chart(heat + text, width="stretch")
    else:
        st.info("Altair not installed or empty heatmap. Showing compact table instead.")
        st.dataframe(wide, width="stretch", height=420)

    st.divider()

    # -----------------------------
    # Drilldown: select a theme and see post_type distribution + KPIs
    # -----------------------------
    st.markdown("### Drilldown (pick a theme)")

    theme_choices = sorted(df_t["theme"].dropna().unique().tolist())
    chosen_theme = st.selectbox("Theme", theme_choices, index=0)

    sub = df_t[df_t["theme"] == chosen_theme].copy()

    # Distribution table
    dist = (
        sub.groupby("post_type")
        .agg(
            threads=("post_type", "count"),
            avg_pain=("pain_intensity", "mean") if "pain_intensity" in sub.columns else ("post_type", "count"),
            avg_weighted=("weighted_pain", "mean") if "weighted_pain" in sub.columns else ("post_type", "count"),
            avg_neg=("comment_neg_rate", "mean") if "comment_neg_rate" in sub.columns else ("post_type", "count"),
            avg_pos=("comment_pos_rate", "mean") if "comment_pos_rate" in sub.columns else ("post_type", "count"),
            total_comments=("n_comments_scraped", "sum") if "n_comments_scraped" in sub.columns else ("post_type", "count"),
        )
        .reset_index()
        .sort_values("threads", ascending=False)
    )

    # Rates must represent comments, not an unweighted average of threads.
    for source_col, output_col in [("comment_neg_rate", "avg_neg"), ("comment_pos_rate", "avg_pos")]:
        if source_col in sub.columns:
            weighted = {
                name: weighted_rate(group, source_col)
                for name, group in sub.groupby("post_type")
            }
            dist[output_col] = dist["post_type"].map(weighted)

    # Make it compact + readable
    show_cols = ["post_type", "threads"]
    for c in ["total_comments", "avg_pain", "avg_weighted", "avg_neg", "avg_pos"]:
        if c in dist.columns:
            show_cols.append(c)

    left, right = st.columns([1.1, 0.9])

    with left:
        st.markdown("<div class='card'><b>Post type distribution (this theme)</b></div>", unsafe_allow_html=True)
        st.dataframe(dist[show_cols], width="stretch", height=280)

    with right:
        st.markdown("<div class='card'><b>Quick read</b></div>", unsafe_allow_html=True)

        # identify dominant post type
        if len(dist) > 0:
            top_pt = dist.iloc[0]["post_type"]
            top_threads = dist.iloc[0]["threads"]
        else:
            top_pt, top_threads = "—", 0

        # theme-level KPI summary
        k_threads = len(sub)
        k_comments = sub["n_comments_scraped"].sum() if "n_comments_scraped" in sub.columns else float("nan")
        k_pain = sub["pain_intensity"].mean() if "pain_intensity" in sub.columns else float("nan")
        k_neg = weighted_rate(sub, "comment_neg_rate")

        st.markdown(
            f"""
- **Dominant feedback type:** `{top_pt}` ({top_threads} threads)
- **Threads in theme:** {fmt_num(k_threads)}
- **Total comments:** {fmt_num(k_comments)}
- **Avg pain intensity:** {fmt_score(k_pain)}
- **Negative comment share:** {fmt_pct(k_neg)}
"""
        )

        st.markdown(
            "<div class='small-muted'>Next: go to the <b>Critical threads</b> page to view real examples + links.</div>",
            unsafe_allow_html=True,
        )

    if show_table:
        with st.expander("Full pivot table (compact)", expanded=False):
            st.dataframe(wide, width="stretch", height=360)



# ============================================================
# PAGE 4 — Critical drilldown
# ============================================================
with tabs[3]:
    st.markdown("## Critical threads (drill-down)")
    st.markdown(
        "<div class='small-muted'>Decision view: filter → shortlist → open a thread → read evidence → link out.</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    # -----------------------------
    # Guardrails
    # -----------------------------
    required_cols = {"thread_id", "theme", "post_type"}
    missing = [c for c in required_cols if c not in df_threads.columns]
    if missing:
        st.error(f"thread_metrics.csv is missing: {missing}. Re-run notebook export.")
        st.stop()

    df_t = df_threads.copy()

    # -----------------------------
    # Filters (clean + minimal)
    # -----------------------------
    f1, f2, f3, f4 = st.columns([1.1, 1.0, 1.0, 1.0])

    theme_opts = ["All"] + sorted(df_t["theme"].dropna().unique().tolist())
    post_type_opts = ["All"] + sorted(df_t["post_type"].dropna().unique().tolist())

    pain_bucket_opts = ["All"]
    if "pain_bucket" in df_t.columns:
        pain_bucket_opts += ["critical", "high", "medium", "low"]

    triage_opts = ["All"]
    if "triage_label" in df_t.columns:
        triage_opts += ["action_now", "investigate", "monitor"]

    with f1:
        sel_theme = st.selectbox("Theme", theme_opts, index=0)
    with f2:
        sel_post_type = st.selectbox("Post type", post_type_opts, index=0)
    with f3:
        sel_bucket = st.selectbox("Pain bucket", pain_bucket_opts, index=0)
    with f4:
        sel_triage = st.selectbox("Triage", triage_opts, index=0)

    # Optional time window if created_date exists
    if "created_date" in df_t.columns:
        dmin = pd.to_datetime(df_t["created_date"], errors="coerce").min()
        dmax = pd.to_datetime(df_t["created_date"], errors="coerce").max()
        if pd.notna(dmin) and pd.notna(dmax):
            d1, d2 = st.date_input(
                "Date range",
                value=(dmin.date(), dmax.date()),
                min_value=dmin.date(),
                max_value=dmax.date(),
            )
            df_t = df_t[
                (pd.to_datetime(df_t["created_date"], errors="coerce").dt.date >= d1)
                & (pd.to_datetime(df_t["created_date"], errors="coerce").dt.date <= d2)
            ]

    # Apply filters
    if sel_theme != "All":
        df_t = df_t[df_t["theme"] == sel_theme]
    if sel_post_type != "All":
        df_t = df_t[df_t["post_type"] == sel_post_type]
    if sel_bucket != "All" and "pain_bucket" in df_t.columns:
        df_t = df_t[df_t["pain_bucket"] == sel_bucket]
    if sel_triage != "All" and "triage_label" in df_t.columns:
        df_t = df_t[df_t["triage_label"] == sel_triage]

    st.divider()

    # -----------------------------
    # Ranking controls (what makes a thread “top”?)
    # -----------------------------
    sort_choices = []
    if "weighted_pain" in df_t.columns:
        sort_choices.append("weighted_pain")
    if "pain_intensity" in df_t.columns:
        sort_choices.append("pain_intensity")
    if "comment_neg_rate" in df_t.columns:
        sort_choices.append("comment_neg_rate")
    if "n_comments_scraped" in df_t.columns:
        sort_choices.append("n_comments_scraped")
    if "post_sentiment" in df_t.columns:
        sort_choices.append("post_sentiment")

    if not sort_choices:
        sort_choices = ["thread_id"]

    s1, s2 = st.columns([1, 1])
    with s1:
        sort_by = st.selectbox("Sort by", sort_choices, index=0)
    with s2:
        top_n = st.slider("Show top N", 10, 100, 30)

    # Sort (descending for “pain” metrics; sentiment might be inverse)
    ascending = False
    if sort_by == "post_sentiment":
        # lower sentiment (more negative) is more concerning → ascending True
        ascending = True

    df_ranked = df_t.sort_values(sort_by, ascending=ascending).head(top_n).copy()

    # Create clean previews
    if "post_text_clean" in df_ranked.columns:
        df_ranked["post_preview"] = df_ranked["post_text_clean"].astype(str).map(lambda x: clamp(x, 140))
    elif "post_text" in df_ranked.columns:
        df_ranked["post_preview"] = df_ranked["post_text"].astype(str).map(lambda x: clamp(x, 140))
    else:
        df_ranked["post_preview"] = ""

    if "url" in df_ranked.columns:
        df_ranked["url_short"] = df_ranked["url"].astype(str).map(lambda x: shorten_url(x, 55))
    else:
        df_ranked["url_short"] = ""

    # -----------------------------
    # Shortlist table (compact)
    # -----------------------------
    st.markdown("<div class='card'><b>Top threads (shortlist)</b></div>", unsafe_allow_html=True)

    show_cols = [
        "thread_id", "theme", "post_type",
    ]
    for c in ["pain_bucket", "triage_label", "pain_intensity", "weighted_pain", "post_sentiment",
              "comment_neg_rate", "n_comments_scraped", "created_date", "post_preview", "url_short"]:
        if c in df_ranked.columns and c not in show_cols:
            show_cols.append(c)

    # Streamlit nice columns (link in drilldown)
    st.dataframe(
        df_ranked[show_cols],
        width="stretch",
        height=360,
        hide_index=True,
    )

    st.divider()

    # -----------------------------
    # Drilldown selector
    # -----------------------------
    st.markdown("<div class='card'><b>Open a thread</b></div>", unsafe_allow_html=True)

    thread_choices = df_ranked["thread_id"].astype(str).dropna().unique().tolist()
    if not thread_choices:
        st.info("No threads match the filters.")
        st.stop()

    chosen_thread = st.selectbox("Select thread_id", thread_choices, index=0)

    row = df_threads[df_threads["thread_id"].astype(str) == str(chosen_thread)]
    if row.empty:
        st.warning("Thread not found in thread_metrics.csv")
        st.stop()

    r = row.iloc[0]

    # Snapshot KPIs (small + readable)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Theme", str(r.get("theme", "—")))
    k2.metric("Post type", str(r.get("post_type", "—")))
    k3.metric("Pain intensity", fmt_score(r.get("pain_intensity", None)) if "pain_intensity" in row.columns else "—")
    k4.metric("Negative comment share", fmt_pct(r.get("comment_neg_rate", None)) if "comment_neg_rate" in row.columns else "—")

    # Extra row (decision labels)
    c1, c2, c3 = st.columns(3)
    if "pain_bucket" in row.columns:
        c1.metric("Pain bucket", str(r.get("pain_bucket", "—")))
    if "triage_label" in row.columns:
        c2.metric("Triage", str(r.get("triage_label", "—")))
    if "n_comments_scraped" in row.columns:
        c3.metric("Comments scraped", fmt_num(r.get("n_comments_scraped", None)))

    st.divider()

    # Full post text (reader mode)
    st.markdown("### Post text")
    post_text = None
    for col in ["post_text_clean", "post_text", "text_clean", "text"]:
        if col in row.columns and isinstance(r.get(col, None), str):
            post_text = r.get(col)
            break

    if post_text:
        st.markdown(f"<div class='quote'>{escape(post_text)}</div>", unsafe_allow_html=True)
    else:
        st.info("Post text not found in exports for this thread.")

    # Link out
    if "url" in row.columns and isinstance(r.get("url", None), str):
        st.link_button("Open on Reddit", r["url"])

    st.divider()

    # Evidence: representative comments (best available export)
    st.markdown("### Representative comments (evidence)")
    if df_ev is not None and not df_ev.empty and "thread_id" in df_ev.columns:
        ev = df_ev[df_ev["thread_id"].astype(str) == str(chosen_thread)].copy()

        if ev.empty:
            st.info("No evidence rows for this thread in evidence_comments.csv")
        else:
            # Most common export is one row per thread with representative_comments
            if "representative_comments" in ev.columns:
                st.markdown("<div class='quote'><b>Most negative / most representative comments</b></div>", unsafe_allow_html=True)
                st.write(str(ev.iloc[0]["representative_comments"]))
            else:
                # fallback to typical fields
                cols = [c for c in ["sentiment_compound", "text_clean", "comment", "text"] if c in ev.columns]
                if cols:
                    if "sentiment_compound" in cols:
                        ev = ev.sort_values("sentiment_compound", ascending=True)
                    st.dataframe(ev[cols].head(20), width="stretch", height=320, hide_index=True)
                else:
                    st.info("evidence_comments.csv exists but does not include usable comment text fields.")
    else:
        st.info("evidence_comments.csv not found (optional export). Run the notebook evidence export cell.")

# ============================================================
# 6) KEY INSIGHTS & RECOMMENDATIONS
# ============================================================
with tabs[4]:
    st.markdown("## Key Insights & Recommendations")
    st.caption("A live readout calculated from the current export")

    st.divider()

    # -----------------------------
    # Executive insights
    # -----------------------------
    st.markdown("### Executive insights")

    live_summary = theme_summary(df_threads)
    named_summary = live_summary[live_summary["theme"].ne("other")].copy()
    top_priority = named_summary.iloc[0]
    enough_comments = named_summary[named_summary["total_comments"].ge(10)]
    most_negative = enough_comments.sort_values("comment_neg_rate", ascending=False).iloc[0]
    other_share = df_threads["theme"].eq("other").mean()
    low_conf_share = df_threads["comment_confidence"].eq("low").mean()

    st.markdown(
        f"""
**1. {str(top_priority['theme']).replace('_', ' ').title()} is the leading named priority.**

It contributes **{top_priority['priority_score']:.2f} priority points** across
**{int(top_priority['threads'])} threads**, after severity is adjusted for evidence confidence.

**2. {str(most_negative['theme']).replace('_', ' ').title()} has the highest negative comment share among themes with at least 10 comments.**

Its comment-weighted negative share is **{fmt_pct(most_negative['comment_neg_rate'])}**. This is a reaction signal, not a user-population estimate.

**3. Classification coverage is the largest analysis gap.**

The catch-all `other` bucket contains **{fmt_pct(other_share)} of threads**. Improve the taxonomy before treating theme comparisons as exhaustive.

**4. Most thread-level signals need corroboration.**

**{fmt_pct(low_conf_share)} of threads** have low comment confidence. Severe low-confidence items are routed to `investigate`, not directly to `action_now`.
"""
    )

    st.divider()

    # -----------------------------
    # Theme-level recommendations
    # -----------------------------
    st.markdown("### Theme-level recommendations")

    recs = pd.DataFrame(
        [
            ["navigation_routing_traffic",
             "Prioritize reliability over optimization. Focus on route consistency, rerouting logic, and traffic confidence."],

            ["search_poi_data",
             "Improve POI freshness and correction latency. Consider better user feedback loops for place accuracy."],

            ["ui_ux_carplay",
             "Validate UI changes with real driving contexts. Treat complaints as usability signals, not sentiment noise."],

            ["performance_reliability",
             "Monitor aggressively. Even small volumes here correlate strongly with high pain when they occur."],

            ["policy_strategy",
             "Separate product pain from policy frustration. Track sentiment, but avoid mixing with core UX priorities."]
        ],
        columns=["Theme", "Recommendation"]
    )

    st.dataframe(recs, width="stretch", height=260)

    st.divider()

    # -----------------------------
    # Action framework
    # -----------------------------
    st.markdown("### Action framework")

    st.markdown(
        """
**Act now**
- High/critical pain with medium or high evidence confidence
- Reproducible failures with clear user impact

**Investigate**
- Medium pain, or severe threads with thin evidence
- Mixed sentiment with rising complaint frequency

**Monitor**
- Low pain or opinionated discussions
- Policy or ecosystem topics without clear product levers
"""
    )


# ============================================================
# PAGE 5 — Methodology (Trust layer)
# ============================================================
with tabs[5]:

    st.markdown("## Methodology")
    st.caption("How raw public feedback becomes decision-ready product signals")

    st.divider()

    # -----------------------------
    # Data sourcing
    # -----------------------------
    st.markdown("### 1. Data sourcing")

    st.markdown(
        """
- **Source**: Public Reddit discussions  
- **Subreddits**: `r/apple`, `r/applemaps`
- **Granularity**:
  - One **thread** = one user story
  - Includes the **post** and all **scraped comments**
- **Time window**: Last ~8 months (rolling)

Why Reddit?
- Long-form, organic feedback
- Users describe *real navigation failures*, not survey answers
- Strong signal for frustration vs delight
"""
    )

    st.divider()

    # -----------------------------
    # Maps relevance filter
    # -----------------------------
    st.markdown("### 2. Apple Maps relevance filtering")

    st.markdown(
        """
Not every post in these subreddits is about Maps.

A thread is marked **Maps-relevant** if:
- Title or body explicitly mentions *Apple Maps*
- OR comments clearly discuss Maps navigation, POIs, routing, UI, or reliability

This step removes:
- General Apple news
- Hardware-only discussions
- Irrelevant app comparisons
"""
    )

    st.divider()

    # -----------------------------
    # Sentiment analysis
    # -----------------------------
    st.markdown("### 3. Sentiment analysis")

    st.markdown(
        """
- **Model**: VADER (rule-based, social-text optimized)
- Applied separately to:
  - Post text
  - Each individual comment
- Outputs:
  - `compound` score ∈ [-1, +1]
  - Labeled as **positive / neutral / negative**

Why VADER?
- Robust for short, opinionated text
- Handles emphasis, negation, punctuation
- Transparent and reproducible (no black-box fine-tuning)
"""
    )

    st.divider()

    # -----------------------------
    # Theme & post type classification
    # -----------------------------
    st.markdown("### 4. Theme & post-type classification")

    st.markdown(
        """
**Theme assignment** (rule-based keyword mapping):

Examples:
- `navigation_routing_traffic`
- `search_poi_data`
- `ui_ux_carplay`
- `performance_reliability`
- `policy_strategy`
- `transit_walk_bike`

**Post type assignment**:
- `experience_complaint`
- `experience_praise`
- `bug_report`
- `feature_request`
- `comparison_discussion`
- `policy_discussion`

Why rule-based?
- Fully interpretable
- Easy to audit and extend
- Matches how PMs already reason about feedback buckets
"""
    )

    st.divider()

    # -----------------------------
    # Pain intensity
    # -----------------------------
    st.markdown("### 5. Pain intensity & triage logic")

    st.markdown(
        """
Each thread is reduced to a **single severity score**:

**pain_intensity (0–1)** combines:
- Post negativity (author frustration)
- % of negative comments (community agreement)
- Directional negative consensus (`max(negative − positive, 0)`)

Intuition:
- A very negative post with many agreeing comments → **high pain**
- Unanimously positive comments do **not** add pain
- A mixed or debated thread → lower negative consensus

From this we derive:
- **pain_bucket**: low / medium / high / critical
- **confidence-adjusted pain**: severity × evidence weight (0.60 / 0.85 / 1.00)
- **theme priority score**: sum of confidence-adjusted pain across threads
- **triage_label**:
  - `action_now`: high/critical pain with medium/high comment confidence
  - `investigate`: medium pain, or high/critical pain with thin evidence
  - `monitor`: low pain
"""
    )

    st.divider()

    # -----------------------------
    # Reproducibility
    # -----------------------------
    st.markdown("### 6. Reproducibility & extensibility")

    st.markdown(
        """
- Entire pipeline runs in a notebook
- Outputs exported as CSVs:
  - `thread_metrics.csv`
  - `theme_rank.csv`
  - `top_pain_threads.csv`
  - `evidence_comments.csv`
- Streamlit app is **read-only**, purely for exploration
- Pipeline can be re-run monthly or extended to:
  - App Store reviews
  - Support tickets
  - Internal feedback tools
"""
    )

    st.markdown(
        "<div class='small-muted'>This page exists to build trust — not to overwhelm.</div>",
        unsafe_allow_html=True,
    )

