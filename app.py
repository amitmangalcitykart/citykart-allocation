import streamlit as st
import pandas as pd
import io
from PIL import Image
import os

st.set_page_config(page_title="Citykart Fixture Allocation", layout="wide")

# ---------- THEME ----------
st.markdown("""
<style>
body { background-color: #f7f7f7; }
.main { background-color: #ffffff; }
.stButton>button {
    background-color: #c62828;
    color: white;
    border-radius: 8px;
}
.stDownloadButton>button {
    background-color: #2e7d32;
    color: white;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
col1, col2 = st.columns([1,5])
with col1:
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png.webp")
    st.image(logo_path, width=120)

with col2:
    st.markdown("<h1 style='color:#c62828;'>Citykart Fixture Allocation Tool</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#2e7d32;'>Upload → Allocate → Download</p>", unsafe_allow_html=True)

st.divider()

uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

# ===============================
# ROUND ROBIN FUNCTION
# ===============================
def round_robin_allocate(cont_list, mc_fix):

    n = len(cont_list)

    targets = [round(c * mc_fix) for c in cont_list]

    alloc = [0] * n

    remaining = mc_fix

    order = sorted(range(n), key=lambda i: cont_list[i], reverse=True)

    while remaining > 0:

        allocated_in_pass = False

        for i in order:

            if alloc[i] < targets[i]:

                alloc[i] += 1
                remaining -= 1
                allocated_in_pass = True

                if remaining == 0:
                    break

        if not allocated_in_pass:
            break

    return alloc


if uploaded_file:

    df = pd.read_csv(uploaded_file)

    cols = df.columns.tolist()

    st.subheader("Select Columns")

    c1, c2, c3 = st.columns(3)

    with c1:
        store = st.selectbox("Store", cols)
        division = st.selectbox("Division", cols)
        section = st.selectbox("Section", cols)
        groupc = st.selectbox("Group", cols)

    with c2:
        department = st.selectbox("Department", cols)
        art = st.selectbox("ART", cols)
        udf06 = st.selectbox("UDF-06", cols)
        floor = st.selectbox("Floor", cols)

    with c3:
        cont_col = st.selectbox("Cont %", cols)
        mc_col = st.selectbox("MC Fix", cols)

    if st.button("Run Allocation"):

        df[cont_col] = pd.to_numeric(df[cont_col], errors="coerce").fillna(0)
        df[mc_col] = pd.to_numeric(df[mc_col], errors="coerce").fillna(0)

        group_cols = [store, division, section, groupc, department, udf06, floor]

        df["ALLOC"] = 0.0

        # ===============================
        # MAIN DISTRIBUTION LOGIC
        # ===============================
        for keys, grp in df.groupby(group_cols):

            mc_fix = grp.iloc[0][mc_col]

            idx_list = grp.index.tolist()

            valid_idx = [i for i in idx_list if df.loc[i, cont_col] > 0]

            valid_count = len(valid_idx)

            # ==========================
            # RULE 0: MC_FIX == 0.5
            # ==========================
            if mc_fix == 0.5:

                if valid_count > 0:

                    highest_idx = max(valid_idx,
                                      key=lambda i: df.loc[i, cont_col])

                    df.loc[highest_idx, "ALLOC"] = 0.5

                continue

            # ==========================
            # RULE 1: MC_FIX == 1
            # ==========================
            if mc_fix == 1:

                if valid_count > 0:

                    highest_idx = max(valid_idx,
                                      key=lambda i: df.loc[i, cont_col])

                    df.loc[highest_idx, "ALLOC"] = 1

            # ==========================
            # RULE 2: MC_FIX > 1
            # ==========================
            elif mc_fix > 1:

                if valid_count >= mc_fix:

                    sorted_valid = sorted(valid_idx,
                                          key=lambda i: df.loc[i, cont_col],
                                          reverse=True)

                    for i in sorted_valid[:int(mc_fix)]:
                        df.loc[i, "ALLOC"] = 1

                elif valid_count > 0:

                    cont_list = [df.loc[i, cont_col] for i in valid_idx]

                    final_vals = round_robin_allocate(cont_list, int(mc_fix))

                    for i, val in zip(valid_idx, final_vals):
                        df.loc[i, "ALLOC"] = val

            # ==========================
            # FINAL BALANCE FIX
            # ==========================
            allocated_sum = df.loc[idx_list, "ALLOC"].sum()

            balance = mc_fix - allocated_sum

            if balance == 1 and valid_count > 0:

                highest_idx = max(valid_idx,
                                  key=lambda i: df.loc[i, cont_col])

                df.loc[highest_idx, "ALLOC"] += 1

        st.success("Allocation Completed Successfully!")

        buffer = io.BytesIO()

        df.to_csv(buffer, index=False)

        st.download_button(
            "Download Output CSV",
            buffer.getvalue(),
            file_name="Citykart_Output.csv",
            mime="text/csv"
        )
