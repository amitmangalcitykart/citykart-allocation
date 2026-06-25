import streamlit as st
import pandas as pd
import numpy as np
import io

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ALLOCATION LOGIC  —  Part-1 MC Fixture
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _standard_round(mc, conts):
    n          = len(conts)
    raw        = [c * mc for c in conts]
    floored    = [int(x) for x in raw]
    remainders = [raw[i] - floored[i] for i in range(n)]
    extra      = int(round(mc - sum(floored)))
    top_rem    = sorted(range(n), key=lambda i: (-remainders[i], i))[:extra]
    for i in top_rem:
        floored[i] += 1
    return [float(x) for x in floored]


def _min1_then_remainder(mc, conts):
    n         = len(conts)
    base      = [1.0] * n
    remaining = mc - n
    if remaining == 0:
        return base
    extra = _standard_round(remaining, conts)
    return [base[i] + extra[i] for i in range(n)]


def compute_allocations(mc_fix, conts_with_idx):
    """
    RULES  (n = active depts with CONT% > 0)
    ─────────────────────────────────────────
    R0   MC=0 or n=0       →  0 for all
    R7   n=1               →  full MC FIX to that dept
    R0.5 MC=0.5            →  top CONT% gets 0.5, rest 0
    R1   MC=1              →  top 2 by CONT% get 0.5, rest 0
    R2   MC=2, n=2         →  1 each
    R3   MC=2, n=3         →  top gets 1, rest get 0.5
    R4   MC≥3, n=2         →  std rounding; if any=0 → min-1 fallback
    R5   MC≥3, n≥3, MC≥n  →  min 1 each + remainder by std rounding
    R6   MC≥3, n≥3, MC<n  →  std rounding only
    """
    n     = len(conts_with_idx)
    idxs  = [i for i, _ in conts_with_idx]
    conts = [c for _, c in conts_with_idx]

    if mc_fix == 0 or n == 0:
        return {i: 0.0 for i in idxs}

    if n == 1:
        return {idxs[0]: float(mc_fix)}

    if mc_fix == 0.5:
        top    = max(range(n), key=lambda i: conts[i])
        allocs = [0.0] * n
        allocs[top] = 0.5
        return {idxs[i]: allocs[i] for i in range(n)}

    if mc_fix == 1:
        order  = sorted(range(n), key=lambda i: -conts[i])
        allocs = [0.0] * n
        for rank, li in enumerate(order):
            if rank < 2:
                allocs[li] = 0.5
        return {idxs[i]: allocs[i] for i in range(n)}

    if mc_fix == 2 and n == 2:
        return {idxs[0]: 1.0, idxs[1]: 1.0}

    if mc_fix == 2 and n == 3:
        top    = max(range(3), key=lambda i: conts[i])
        allocs = [0.5, 0.5, 0.5]
        allocs[top] = 1.0
        return {idxs[i]: allocs[i] for i in range(3)}

    if n == 2:
        std = _standard_round(mc_fix, conts)
        if min(std) == 0:
            std = _min1_then_remainder(mc_fix, conts)
        return {idxs[i]: std[i] for i in range(2)}

    if mc_fix >= n:
        allocs = _min1_then_remainder(mc_fix, conts)
    else:
        allocs = _standard_round(mc_fix, conts)
    return {idxs[i]: allocs[i] for i in range(n)}


def run_part1(df):
    """Run Part-1 MC Fixture allocation. Returns (result_df, n_groups, n_match, n_mismatch)."""

    # Auto-detect group column
    group_col = None
    for col in ['GROUP', 'Group', 'DEPARTMENT Group']:
        if col in df.columns:
            group_col = col
            break
    if group_col is None:
        raise ValueError(
            "Group column not found in file. "
            "Expected one of: GROUP / Group / DEPARTMENT Group"
        )

    df = df.copy()
    df['Auto Allocation'] = 0.0

    for (store, grp, udf), group in df.groupby(['STORE', group_col, 'UDF-06']):
        mc_fix = float(group['MC FIX'].iloc[0])
        if mc_fix == 0:
            continue
        active = group[group['CONT%'] > 0]
        if len(active) == 0:
            continue
        allocs = compute_allocations(
            mc_fix, list(zip(active.index, active['CONT%']))
        )
        for idx, val in allocs.items():
            df.loc[idx, 'Auto Allocation'] = val

    # ── Validation ──────────────────────────────────────────
    check = (
        df[df['MC FIX'] > 0]
        .groupby(['STORE', group_col, 'UDF-06'])
        .agg(mc_fix=('MC FIX', 'first'), total=('Auto Allocation', 'sum'))
        .reset_index()
    )
    check['match'] = (check['mc_fix'] - check['total']).abs() < 0.01
    n_groups   = len(check)
    n_match    = int(check['match'].sum())
    n_mismatch = n_groups - n_match

    return df, n_groups, n_match, n_mismatch


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STREAMLIT UI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

st.set_page_config(
    page_title = "Part-1 MC Fixture",
    page_icon  = "📦",
    layout     = "centered",
)

st.title("📦 Part-1 : MC Fixture Allocation")
st.markdown(
    "Upload your input CSV file. "
    "Allocation runs automatically and the output is ready to download."
)
st.divider()

uploaded_file = st.file_uploader("📂 Upload Input CSV", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)

        # ── Input summary ────────────────────────────────────
        st.subheader("📊 Input Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Rows",    f"{len(df):,}")
        c2.metric("Total Stores",  f"{df['STORE'].nunique():,}")
        c3.metric("MC FIX Range",  f"{int(df['MC FIX'].min())} – {int(df['MC FIX'].max())}")

        # ── Run allocation ───────────────────────────────────
        with st.spinner("⚙️ Running Part-1 MC Fixture allocation..."):
            result_df, n_groups, n_match, n_mismatch = run_part1(df)

        # ── Validation results ───────────────────────────────
        st.subheader("✅ Validation Results")
        c4, c5, c6 = st.columns(3)
        c4.metric("Total Groups",  f"{n_groups:,}")
        c5.metric("Matching",      f"{n_match:,}")
        c6.metric("Mismatches",    f"{n_mismatch:,}")

        if n_mismatch == 0:
            st.success("All groups validated — totals match MC FIX perfectly.")
        else:
            st.warning(f"{n_mismatch} group(s) have mismatches. Please review.")

        # ── Preview ──────────────────────────────────────────
        st.subheader("👁️ Output Preview (first 20 rows)")
        st.dataframe(result_df.head(20), use_container_width=True)

        # ── Download ─────────────────────────────────────────
        st.divider()
        buf = io.BytesIO()
        result_df.to_csv(buf, index=False)
        buf.seek(0)

        st.download_button(
            label            = "⬇️  Download Output CSV",
            data             = buf,
            file_name        = "Part1_MC_Fixture_Output.csv",
            mime             = "text/csv",
            use_container_width = True,
        )

    except Exception as e:
        st.error(f"❌ Error: {e}")

else:
    st.info("👆 Please upload a CSV file to get started.")
