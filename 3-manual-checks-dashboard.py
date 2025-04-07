#%%
import random
import os
import re
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
import numpy as np

manual_extraction_path = "data/PICO-ground-truth-minimal/"

st.set_page_config(page_title="Cochrane Summary of Findings (SOF) Tables", layout="wide")

@st.cache_data
def load_data():
    cochrane_info = pd.read_csv("data/25-04-01-citation-export-interventions-no-abstract.csv")
    cochrane_info.index = cochrane_info["Cochrane Review ID"]

    sof_original = pd.read_csv("data/25-04-01-sof-tables-interventions.csv", index_col=0)
    sof_original = sof_original[~sof_original["sof"].isna()]
    # Only keep reviews that are in cochrane_info, which contains only the newest reviews on interventions
    sof_original = sof_original[sof_original.index.isin(cochrane_info.index)]
    sof_original = sof_original.to_dict()["sof"]

    parsed_sof_df = pd.read_csv("results/25-04-01-parsed_sof_df.csv")

    return cochrane_info, sof_original, parsed_sof_df
    
cochrane_info, sof_original, parsed_sof_df = load_data()

#%%
st.html("""
<style>
td, th { border: 1px solid #ccc }
</style>
""")#MainMenu, header, footer {visibility: hidden;}

cochrane_ids = parsed_sof_df["cochrane_id"].unique()

# Selectboxes
cochrane_ids_reviewed_included = np.array([re.sub(r"\.csv.*", "", x) for x in os.listdir(f"{manual_extraction_path}") if ".csv" in x])
cochrane_ids_reviewed_excluded = np.array([re.sub(r"\.csv.*", "", x) for x in os.listdir(f"{manual_extraction_path}excluded/")])

cochrane_ids_unflagged = parsed_sof_df.loc[parsed_sof_df["certainty_cleaned"].notna() & ((parsed_sof_df["nr_studies_cleaned"] > 0) | (parsed_sof_df["nr_participants_cleaned"] > 0)), "cochrane_id"].unique()
cochrane_ids_unflagged_reviewed = cochrane_ids_reviewed_included[np.isin(cochrane_ids_reviewed_included, cochrane_ids_unflagged)]

random.seed(7)
cochrane_id_unflagged_random_set = np.array(random.sample(list(cochrane_ids_unflagged), 100))
cochrane_id_unflagged_random_set_unreviewed = cochrane_id_unflagged_random_set[~np.isin(cochrane_id_unflagged_random_set, np.concatenate((cochrane_ids_reviewed_included, cochrane_ids_reviewed_excluded)))]

cochrane_ids_flagged = cochrane_ids[~np.isin(cochrane_ids, cochrane_ids_unflagged)]
cochrane_ids_flagged_excluded = cochrane_ids_reviewed_excluded[np.isin(cochrane_ids_reviewed_excluded, cochrane_ids_flagged)]
cochrane_ids_flagged_included = cochrane_ids_reviewed_included[np.isin(cochrane_ids_reviewed_included, cochrane_ids_flagged)]
cochrane_ids_flagged_undecided = cochrane_ids_flagged[~np.isin(cochrane_ids_flagged, np.concatenate((cochrane_ids_flagged_excluded, cochrane_ids_flagged_included)))]

cochrane_id = st.selectbox(f"Flagged reviews (no single valid certainty_cleaned or nr_studies_cleaned or nr_participants_cleaned) ({len(cochrane_ids_flagged)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_flagged).sum()} outcomes)", cochrane_ids_flagged, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Thereof reviewed and excluded reviews ({len(cochrane_ids_flagged_excluded)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_flagged_excluded).sum()} outcomes)", cochrane_ids_flagged_excluded, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Thereof reviewed and included reviews ({len(cochrane_ids_flagged_included)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_flagged_included).sum()} outcomes)", cochrane_ids_flagged_included, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Thereof unreviewed reviews ({len(cochrane_ids_flagged_undecided)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_flagged_undecided).sum()} outcomes)", cochrane_ids_flagged_undecided, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Unflagged reviews ({len(cochrane_ids_unflagged)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_unflagged).sum()} outcomes)", cochrane_ids_unflagged, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Thereof reviewed ({len(cochrane_ids_unflagged_reviewed)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_unflagged_reviewed).sum()} outcomes)", cochrane_ids_unflagged_reviewed, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Random subset (seed 7) ({len(cochrane_id_unflagged_random_set)})", cochrane_id_unflagged_random_set, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Thereof unreviewed ({len(cochrane_id_unflagged_random_set_unreviewed)})", cochrane_id_unflagged_random_set_unreviewed, index=0, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}")


st.link_button("Open in Cochrane", f"https://doi.org/10.1002/14651858.{cochrane_id}")

#%%
sof_df = parsed_sof_df[parsed_sof_df["cochrane_id"] == cochrane_id]

path = f"{manual_extraction_path}{cochrane_id}.csv"
if os.path.exists(path):
    manual_sof_df = pd.read_csv(path)
else:
    manual_sof_df = None

st.markdown(f"{sof_df['table_nr'].max()} SOF table(s), {sof_df.shape[0]} outcome(s)")

# SOF tables

st.header("Original SOF tables")

html_content = sof_original[cochrane_id]
soup = BeautifulSoup(html_content, "html.parser")
tables = soup.find_all("table", class_="summary-of-findings")

for i in range(1, len(tables)+1):
    st.subheader(f"SOF table {i}")
    
    col1, col2 = st.columns(2)

    with col2:
        if (sof_df["table_nr"] == i).sum():
            tab1 = st.tabs(["Automatic Extraction"])[0]
            with tab1:
                edited = st.data_editor(
                    sof_df.loc[sof_df["table_nr"] == i, ["rowname", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned"]],
                    column_config={
                        "effect_type": "t", "point_estimate": "e", "lower_ci": "lo", "upper_ci": "up", "nr_participants_cleaned": "n_p", "nr_studies_cleaned": "n_s", "certainty_cleaned": "grade"
                    },
                    hide_index=True
                )

                sof_df.loc[sof_df["table_nr"] == i, ["rowname", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned"]] = edited
    
    with col1:
        #with st.expander(f"SOF table {i}", True):
        tab1, tab2 = st.tabs(["Original Table", "Manual Extraction"])

        # Raw table
        table = tables[i-1]
        with tab1:
            st.html(str(table))
        with tab2:
            if type(manual_sof_df) == pd.DataFrame:
                st.dataframe(
                    manual_sof_df.loc[manual_sof_df["table_nr"] == i, ["rowname", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned"]],
                    hide_index=True
                )

st.download_button("Download SOF tables as CSV", sof_df[["table_nr", "rowname", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned"]].to_csv(index=False), file_name=f"{cochrane_id}.csv")
