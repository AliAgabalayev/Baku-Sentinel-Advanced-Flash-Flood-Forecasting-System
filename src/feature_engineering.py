"""
pipeline/feature_engineering.py
================================
DEPRECATED — kept only for backward import compatibility.

In the medallion architecture, ALL feature engineering is done in SQL
inside pipeline.py (get_sentinel_feature_sql). This produces the Gold
layer (gold.flood_features) which is the direct input to model.py.

If you import build_features / compute_feature_correlations / etc. from
here, they now delegate to the Gold layer via DuckDB rather than
re-computing on raw Pandas DataFrames — so column names always match.

Do NOT call build_features() on raw Bronze data.  Use pipeline.load_gold().
"""

import logging
from typing import Optional

import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


def build_features(*args, **kwargs):
    raise NotImplementedError(
        "build_features() is not used in the medallion pipeline.\n"
        "Run  pipeline.run_pipeline()  to create the Gold layer, then\n"
        "load it with  pipeline.load_gold()."
    )


def compute_feature_correlations(df: pd.DataFrame,
                                 target: str = "is_flood",
                                 method: str = "spearman") -> pd.DataFrame:
    """Spearman correlation of every numeric feature against `target`."""
    num_df = df.select_dtypes(include="number")
    if target not in num_df.columns:
        logger.warning(f"Target '{target}' not found.")
        return pd.DataFrame()

    y = num_df[target].dropna()
    rows = []
    for col in num_df.columns:
        if col == target:
            continue
        x = num_df[col].dropna()
        common = x.index.intersection(y.index)
        if len(common) < 30:
            continue
        if method == "spearman":
            corr, pval = stats.spearmanr(x.loc[common], y.loc[common])
        else:
            corr, pval = stats.pearsonr(x.loc[common], y.loc[common])
        rows.append({"feature": col, "correlation": corr, "p_value": pval})

    out = (pd.DataFrame(rows)
           .sort_values("correlation", key=abs, ascending=False)
           .assign(significant=lambda d: d["p_value"] < 0.05))
    logger.info(f"Correlations computed: {len(out)} features.")
    return out


def run_hypothesis_tests(df: pd.DataFrame,
                         target: str = "is_flood",
                         features: Optional[list] = None) -> pd.DataFrame:
    """Mann-Whitney U test: flood vs non-flood group for each feature."""
    if target not in df.columns:
        logger.warning(f"Target '{target}' not found.")
        return pd.DataFrame()

    flood    = df[df[target] == 1]
    no_flood = df[df[target] == 0]
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if features:
        num_cols = [c for c in num_cols if c in features]

    rows = []
    for col in num_cols:
        if col == target:
            continue
        f, nf = flood[col].dropna(), no_flood[col].dropna()
        if len(f) < 10 or len(nf) < 10:
            continue
        stat, pval = stats.mannwhitneyu(f, nf, alternative="two-sided")
        rows.append({
            "feature":          col,
            "flood_median":     f.median(),
            "no_flood_median":  nf.median(),
            "delta_median":     f.median() - nf.median(),
            "mw_statistic":     stat,
            "p_value":          pval,
            "significant":      pval < 0.05,
            "effect_direction": "higher_on_flood" if f.mean() > nf.mean() else "lower_on_flood",
        })

    out = pd.DataFrame(rows).sort_values("p_value")
    logger.info(f"Hypothesis tests: {out['significant'].sum()}/{len(out)} significant.")
    return out


def summarize_feature_importance(corr_df: pd.DataFrame,
                                 hypo_df: pd.DataFrame,
                                 top_n: int = 20) -> pd.DataFrame:
    """Merge correlation + Mann-Whitney results into one ranked table."""
    if corr_df.empty or hypo_df.empty:
        return pd.DataFrame()
    merged = corr_df.merge(
        hypo_df[["feature", "flood_median", "no_flood_median",
                 "delta_median", "p_value", "significant", "effect_direction"]],
        on="feature", how="inner", suffixes=("_corr", "_mw"),
    )
    return (merged
            .assign(abs_corr=lambda d: d["correlation"].abs())
            .sort_values("abs_corr", ascending=False)
            .head(top_n))
