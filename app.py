import streamlit as st
import pandas as pd
import math
import io
from PIL import Image

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
    logo = Image.open("logo.png.webp")
    st.image(logo, width=120)
with col2:
    st.markdown("<h1 style='color:#c62828;'>Citykart Fixture Allocation Tool</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#2e7d32;'>Upload → Allocate → Download</p>", unsafe_allow_html=True)

st.divider()

uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

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
        art = st.selectbox("ART (for count)", cols)
        udf06 = st.selectbox("UDF-06", cols)
        floor = st.selectbox("Floor", cols)
    with c3:
        cont_col = st.selectbox("Cont %", cols)
        mc_col = st.selectbox("MC Fix", cols)

    if st.button("Run Allocation"):
        df[cont_col] = pd.to_numeric(df[cont_col], errors="coerce").fillna(0)
        df[mc_col] = pd.to_numeric(df[mc_col], errors="coerce").fillna(0)

        group_cols = [store, division, section, groupc, department, udf06, floor]

        def balanced_round(values, mc_fix):
            rounded = []
            frac_list = []
            for v in values:
                base = math.floor(v)
                frac = v - base
                r = base + 1 if frac >= 0.4 else base
                rounded.append(r)
                frac_list.append(frac)

            diff = mc_fix - sum(rounded)

            if diff > 0:
                order = sorted(range(len(frac_list)), key=lambda i: frac_list[i], reverse=True)
                for i in order:
                    if diff == 0: break
                    rounded[i] += 1
                    diff -= 1

            elif diff < 0:
                diff = abs(diff)
                order = sorted(range(len(frac_list)), key=lambda i: frac_list[i])
                for i in order:
                    if diff == 0: break
                    if rounded[i] > 0:
                        rounded[i] -= 1
                        diff -= 1
            return rounded

        df["ALLOC"] = 0.0

        for keys, grp in df.groupby(group_cols):
            mc_fix = grp.iloc[0][mc_col]
            art_count = grp[art].nunique()

            if mc_fix == 1:

                # rows jahan cont% > 0
                valid = grp[grp[cont_col] > 0]

                if len(valid) == 1:
                    df.loc[valid.index, "ALLOC"] = 1

                elif len(valid) >= 2:
                    top2 = valid.sort_values(cont_col, ascending=False).head(2)
                    df.loc[top2.index, "ALLOC"] = 0.5
                    
            elif mc_fix > 1:
                raw_vals = [df.loc[i, cont_col] * mc_fix for i in grp.index]
                final_vals = balanced_round(raw_vals, int(mc_fix))
                for i, val in zip(grp.index, final_vals):
                    df.loc[i, "ALLOC"] = val

        st.success("Allocation Completed!")

        buffer = io.BytesIO()
        df.to_csv(buffer, index=False)
        st.download_button("Download Output CSV", buffer.getvalue(),
                           file_name="Citykart_Output.csv",
                           mime="text/csv")