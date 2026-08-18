"""Transparent, testable metrics used by the Streamlit dashboard."""

from __future__ import annotations

import pandas as pd


CONFIDENCE_WEIGHTS = {"low": 0.60, "medium": 0.85, "high": 1.00}
PAIN_THRESHOLDS = {"critical": 0.35, "high": 0.20, "medium": 0.10}


def weighted_rate(
    frame: pd.DataFrame,
    rate_column: str,
    weight_column: str = "n_comments_scraped",
) -> float:
    """Return an event-weighted rate, excluding rows with no observations."""
    if rate_column not in frame or weight_column not in frame:
        return float("nan")
    rates = pd.to_numeric(frame[rate_column], errors="coerce")
    weights = pd.to_numeric(frame[weight_column], errors="coerce").fillna(0).clip(lower=0)
    valid = rates.notna() & weights.gt(0)
    if not valid.any() or weights[valid].sum() == 0:
        return float("nan")
    return float((rates[valid] * weights[valid]).sum() / weights[valid].sum())


def severity_bucket(score: float) -> str:
    if pd.isna(score):
        return "unknown"
    if score >= PAIN_THRESHOLDS["critical"]:
        return "critical"
    if score >= PAIN_THRESHOLDS["high"]:
        return "high"
    if score >= PAIN_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def enrich_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    """Add corrected pain, confidence, priority, and triage fields.

    The notebook's original absolute consensus term rewarded both unanimous
    negative and unanimous positive comments. Here only *negative* agreement
    can increase pain. Original exported fields are retained with a legacy_
    prefix for auditability.
    """
    df = frame.copy()
    numeric = [
        "post_sentiment",
        "comment_neg_rate",
        "comment_neu_rate",
        "comment_pos_rate",
        "n_comments_scraped",
        "pain_intensity",
        "weighted_pain",
    ]
    for column in numeric:
        if column in df:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "pain_intensity" in df:
        df["legacy_pain_intensity"] = df["pain_intensity"]
    if "weighted_pain" in df:
        df["legacy_weighted_pain"] = df["weighted_pain"]

    required = {"post_sentiment", "comment_neg_rate", "comment_pos_rate"}
    if required.issubset(df.columns):
        post_negativity = (-df["post_sentiment"].fillna(0)).clip(lower=0, upper=1)
        negative_rate = df["comment_neg_rate"].fillna(0).clip(lower=0, upper=1)
        negative_consensus = (
            df["comment_neg_rate"].fillna(0) - df["comment_pos_rate"].fillna(0)
        ).clip(lower=0, upper=1)
        df["negative_consensus"] = negative_consensus
        df["pain_intensity"] = (
            0.40 * post_negativity + 0.40 * negative_rate + 0.20 * negative_consensus
        ).clip(lower=0, upper=1)

    if "comment_confidence" not in df and "n_comments_scraped" in df:
        counts = df["n_comments_scraped"].fillna(0)
        df["comment_confidence"] = pd.cut(
            counts,
            bins=[-1, 4, 19, float("inf")],
            labels=["low", "medium", "high"],
        ).astype(str)

    confidence = df.get("comment_confidence", pd.Series("low", index=df.index))
    df["evidence_weight"] = confidence.map(CONFIDENCE_WEIGHTS).fillna(0.60)
    if "pain_intensity" in df:
        df["weighted_pain"] = df["pain_intensity"] * df["evidence_weight"]
        df["pain_bucket"] = df["pain_intensity"].map(severity_bucket)

        strong_signal = df["comment_confidence"].isin(["medium", "high"])
        high_pain = df["pain_bucket"].isin(["high", "critical"])
        df["triage_label"] = "monitor"
        df.loc[df["pain_bucket"].eq("medium") | (high_pain & ~strong_signal), "triage_label"] = "investigate"
        df.loc[high_pain & strong_signal, "triage_label"] = "action_now"

    return df


def theme_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Build theme metrics with correct comment weighting and additive priority."""
    if "theme" not in frame:
        return pd.DataFrame()

    summary = (
        frame.groupby("theme", dropna=False)
        .agg(
            threads=("theme", "size"),
            total_comments=("n_comments_scraped", "sum"),
            avg_pain_intensity=("pain_intensity", "mean"),
            avg_weighted_pain=("weighted_pain", "mean"),
            priority_score=("weighted_pain", "sum"),
            high_critical=("pain_bucket", lambda s: s.isin(["high", "critical"]).sum()),
            action_now=("triage_label", lambda s: s.eq("action_now").sum()),
        )
        .reset_index()
    )
    summary["high_critical_rate"] = summary["high_critical"] / summary["threads"]

    for column in ["comment_neg_rate", "comment_neu_rate", "comment_pos_rate"]:
        if column in frame:
            values = pd.Series(
                {
                    name: weighted_rate(group, column)
                    for name, group in frame.groupby("theme", dropna=False)
                },
                name=column,
            )
            summary = summary.merge(values.rename_axis("theme").reset_index(), on="theme", how="left")

    return summary.sort_values(["priority_score", "threads"], ascending=False)
