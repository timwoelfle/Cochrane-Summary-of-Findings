#%%
#import random
import os
import re
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
import numpy as np
import graphviz

manual_extraction_path = "data/manual_extraction/"

st.set_page_config(page_title="Cochrane Summary of Findings (SOF) Tables", layout="wide")

cochrane_ids_reviewed_included = np.array([re.sub(r"\.csv.*", "", x) for x in os.listdir(manual_extraction_path) if x.endswith(".csv")])
cochrane_ids_reviewed_excluded = np.array([re.sub(r"\.csv.*", "", x) for x in os.listdir(f"{manual_extraction_path}excluded/")])
cochrane_ids_reviewed_test = np.array([re.sub(r"\.csv.*", "", x) for x in os.listdir(f"{manual_extraction_path}test/")])

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
    # Remove outcomes without GRADE
    parsed_sof_df = parsed_sof_df[parsed_sof_df["certainty_cleaned"].notna()]

    # Load manual_extraction
    manual_extraction_per_table = []

    manual_sof_df_dict = {}

    for cochrane_id in np.concatenate((cochrane_ids_reviewed_included, cochrane_ids_reviewed_test)):
        if os.path.exists(f"{manual_extraction_path}{cochrane_id}.csv"):
            manual_sof_df = pd.read_csv(f"{manual_extraction_path}{cochrane_id}.csv").reset_index(drop=True)
        else:
            manual_sof_df = pd.read_csv(f"{manual_extraction_path}test/{cochrane_id}.csv").reset_index(drop=True)
        
        manual_sof_df["cochrane_id"] = cochrane_id

        # row_nr missing in older manual_extraction files (not in test files though)
        if not "row_nr" in manual_sof_df.columns:
           manual_sof_df["row_nr"] = manual_sof_df.groupby("table_nr").cumcount() + 1

        # Remove outcomes without GRADE 
        manual_sof_df = manual_sof_df[manual_sof_df["certainty_cleaned"].notna()]
        
        manual_sof_df_dict[cochrane_id] = manual_sof_df.copy()

        manual_sof_df = manual_sof_df[["table_nr", "row_nr", "rowname", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned"]]
        manual_sof_df["rowname"] = manual_sof_df["rowname"].replace(r"\s+", " ", regex=True)
        manual_sof_df = manual_sof_df.astype(str)

        automatic_sof_df = parsed_sof_df[parsed_sof_df["cochrane_id"] == cochrane_id].reset_index(drop=True)
        automatic_sof_df = automatic_sof_df[["table_nr", "row_nr", "rowname", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned"]]
        automatic_sof_df["rowname"] = automatic_sof_df["rowname"].replace(r"\s+", " ", regex=True)
        automatic_sof_df = automatic_sof_df.astype(str)

        for table_nr in manual_sof_df["table_nr"].unique():
            manual_sof_df_sub = manual_sof_df[manual_sof_df["table_nr"] == str(table_nr)].reset_index(drop=True)
            automatic_sof_df_sub = automatic_sof_df[automatic_sof_df["table_nr"] == str(table_nr)].reset_index(drop=True)
            # Shorten longer dataframe
            len_manual_sof_df_sub = len(manual_sof_df_sub)
            len_automatic_sof_df_sub = len(automatic_sof_df_sub)
            rows_min = min(len_manual_sof_df_sub, len_automatic_sof_df_sub)
            rows_max = max(len_manual_sof_df_sub, len_automatic_sof_df_sub)
            if rows_min != rows_max:
                if manual_sof_df_sub["row_nr"].isin(automatic_sof_df_sub["row_nr"]).all():
                    manual_sof_df_sub.index = manual_sof_df_sub["row_nr"]
                    automatic_sof_df_sub.index = automatic_sof_df_sub["row_nr"]
                    automatic_sof_df_sub = automatic_sof_df_sub.loc[manual_sof_df_sub.index]
                else:
                    automatic_sof_df_sub = automatic_sof_df_sub[0:rows_min]
                    manual_sof_df_sub = manual_sof_df_sub[0:rows_min]
            fraction_length = len_automatic_sof_df_sub/len_manual_sof_df_sub
            fraction_equal = (automatic_sof_df_sub==manual_sof_df_sub).mean().mean() * (rows_min/rows_max)

            manual_extraction_per_table.append([cochrane_id, int(table_nr), fraction_length, fraction_equal, manual_sof_df_sub.compare(automatic_sof_df_sub)])

    manual_extraction_per_table = pd.DataFrame(manual_extraction_per_table, columns=["cochrane_id", "table_nr", "fraction_length", "fraction_equal", "compare"])
    manual_extraction = manual_extraction_per_table.groupby("cochrane_id").agg({"fraction_length": "mean", "fraction_equal": "mean"})

    return cochrane_info, sof_original, parsed_sof_df, manual_sof_df_dict, manual_extraction_per_table, manual_extraction

cochrane_info, sof_original, parsed_sof_df, manual_sof_df_dict, manual_extraction_per_table, manual_extraction = load_data()

#%%
# Outcomes with certainty_cleaned non-nan must pass these unflagged_criteria:
# - certainty_cleaned is in ["very low", "low", "moderate", "high"]
# - nr_participants_cleaned > 0 or nr_studies_cleaned > 0
parsed_sof_df["participants_or_studies_set"] = (parsed_sof_df["nr_participants_cleaned"] > 0) | (parsed_sof_df["nr_studies_cleaned"] > 0)

unflagged_criteria = parsed_sof_df[parsed_sof_df["certainty_cleaned"].notna()].groupby("cochrane_id").agg({
    "certainty_cleaned": lambda x: x.isin(["very low", "low", "moderate", "high"]).all(),
    "participants_or_studies_set": lambda x: x.any(),
})

# Unflagged reviews have at least one outcome passing unflagged_criteria
cochrane_ids_unflagged = unflagged_criteria.index[
    unflagged_criteria["certainty_cleaned"] & \
    unflagged_criteria["participants_or_studies_set"]
]
cochrane_ids_reviewed_tuning = cochrane_ids_reviewed_included[np.isin(cochrane_ids_reviewed_included, cochrane_ids_unflagged)]
cochrane_ids_reviewed_tuning_differs = cochrane_ids_reviewed_included[np.isin(cochrane_ids_reviewed_included, cochrane_ids_unflagged) & (manual_extraction.loc[cochrane_ids_reviewed_included, "fraction_equal"] < 1)]
cochrane_ids_reviewed_test_differs = cochrane_ids_reviewed_test[manual_extraction.loc[cochrane_ids_reviewed_test, "fraction_equal"] < 1]

cochrane_ids_flagged = unflagged_criteria.index[~np.isin(unflagged_criteria.index, cochrane_ids_unflagged)]
cochrane_ids_flagged_excluded = cochrane_ids_reviewed_excluded[np.isin(cochrane_ids_reviewed_excluded, cochrane_ids_flagged)]
cochrane_ids_flagged_included = cochrane_ids_reviewed_included[np.isin(cochrane_ids_reviewed_included, cochrane_ids_flagged)]
cochrane_ids_flagged_undecided = cochrane_ids_flagged[~np.isin(cochrane_ids_flagged, np.concatenate((cochrane_ids_flagged_excluded, cochrane_ids_flagged_included)))]

#random.seed(7)
#cochrane_id_unflagged_random_set = np.array(random.sample(list(cochrane_ids_unflagged), 100))
#cochrane_id_unflagged_random_set_reviewed = cochrane_id_unflagged_random_set[np.isin(cochrane_id_unflagged_random_set, cochrane_ids_reviewed_test)]
#cochrane_id_unflagged_random_set_unreviewed = cochrane_id_unflagged_random_set[~np.isin(cochrane_id_unflagged_random_set, cochrane_ids_reviewed_test)]

# Combine parsed_sof_df and manual_sof_df_dict to final_sof_df
final_sof_df = pd.concat([
    parsed_sof_df.loc[
        ~parsed_sof_df["cochrane_id"].isin(np.concatenate((cochrane_ids_flagged, cochrane_ids_reviewed_tuning, cochrane_ids_reviewed_test))),
        ["cochrane_id", "table_nr", "row_nr", "rowname", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned"]
    ],
    pd.concat(manual_sof_df_dict.values())[
        ["cochrane_id", "table_nr", "row_nr", "rowname", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned"]
    ]
]).reset_index(drop=True)
final_sof_df = final_sof_df[(final_sof_df["nr_participants_cleaned"] > 0) | (final_sof_df["nr_studies_cleaned"] > 0)]

assert (final_sof_df["effect_type"].isna() == final_sof_df["point_estimate"].isna()).all()
assert (final_sof_df["effect_type"].isna() == final_sof_df["lower_ci"].isna()).all()
assert (final_sof_df["effect_type"].isna() == final_sof_df["upper_ci"].isna()).all()

final_sof_df["primary_outcome"] = False
final_sof_df.loc[(final_sof_df["table_nr"] == 1) & (final_sof_df["row_nr"] == 1), "primary_outcome"] = True
final_sof_df["mortality_outcome"] = final_sof_df["rowname"].astype(str).str.contains("mortality|death")

final_sof_df[["cochrane_id", "table_nr", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned", "primary_outcome", "mortality_outcome"]].\
    to_csv("final/25-04-01-final_sof_df.csv", index=False)

cochrane_ids_total_included = cochrane_info.index[cochrane_info.index.isin(final_sof_df["cochrane_id"].unique())]
cochrane_info.loc[cochrane_ids_total_included, ["Cochrane Review ID", "Title", "Year", "Issue", "Keywords", "Cochrane Review Group Code"]].\
    to_csv("final/25-04-01-final_cochrane_info.csv", index=False)

#%%
st.html("""
<style>
td, th { border: 1px solid #ccc }
</style>
""")#MainMenu, header, footer {visibility: hidden;}

# Flowchart
def get_n_reviews_rows_outcomes_w_grade(sof_df):
    #return f"{len(sof_df["cochrane_id"].unique())} reviews with {int((sof_df["certainty_cleaned"].notna() & ((sof_df["nr_participants_cleaned"] > 0) | (sof_df["nr_studies_cleaned"] > 0))).sum())} outcomes*",\
    return len(sof_df["cochrane_id"].unique()),\
        len(sof_df),\
        int(sof_df["certainty_cleaned"].notna().sum())

def get_n_from_cochrane_ids(selected_cochrane_ids):
    return get_n_reviews_rows_outcomes_w_grade(parsed_sof_df[parsed_sof_df["cochrane_id"].isin(selected_cochrane_ids)])

assert (~np.isin(cochrane_ids_reviewed_test, cochrane_ids_flagged)).all()

# Create flow chart DOT
flowchart = f"""
digraph {{
    rankdir=TB;
    node [shape=box];
    
    A [label="Total number of Cochrane reviews \non interventions as of 2025-04-01 \n(n={len(cochrane_info)})"];
    B [label="Reviews with \nSummary of Findings (SoF) Table(s) \n(n={len(sof_original)})"];
    C [label="Reviews with \nat least one outcome with GRADE \n(n={get_n_from_cochrane_ids(unflagged_criteria.index)[0]})"];
    D1 [label="Unflagged reviews \n(n={get_n_from_cochrane_ids(cochrane_ids_unflagged)[0]})"];
    D4 [label="Flagged reviews \nn={(~unflagged_criteria["participants_or_studies_set"]).sum()} without Nr. of participants or studies \nn={(~unflagged_criteria["certainty_cleaned"]).sum()} with multiple GRADE levels in one outcome \n(n={get_n_from_cochrane_ids(cochrane_ids_flagged)[0]} in total)"];
    E1 [label="Random set manually reviewed \nfor automatic extraction tuning \n(n={get_n_from_cochrane_ids(cochrane_ids_reviewed_tuning)[0]}) \nwith {manual_extraction.loc[cochrane_ids_reviewed_tuning, "fraction_equal"].mean()*100:.1f}% accuracy of automatic vs manual extraction"];
    E2 [label="Random set manually reviewed \nafter automatic extraction tuning ('test set') \n(n={get_n_from_cochrane_ids(cochrane_ids_reviewed_test)[0]}) \nwith {manual_extraction.loc[cochrane_ids_reviewed_test, "fraction_equal"].mean()*100:.1f}% accuracy of automatic vs manual extraction"];
    E3 [label="\nNot manually reviewed \n(n={get_n_from_cochrane_ids(cochrane_ids_unflagged[~np.isin(cochrane_ids_unflagged, np.concatenate((cochrane_ids_reviewed_tuning, cochrane_ids_reviewed_test)))])[0]})\n\n"];
    E4 [label="Flagged reviews \nkept after manual review \n(n={get_n_from_cochrane_ids(cochrane_ids_flagged_included)[0]}) \nwith {manual_extraction.loc[cochrane_ids_flagged_included, "fraction_equal"].mean()*100:.1f}% accuracy of automatic vs manual extraction"];
    F1 [label="Total included reviews \n(n={get_n_reviews_rows_outcomes_w_grade(final_sof_df)[0]} with {get_n_reviews_rows_outcomes_w_grade(final_sof_df)[1]} outcomes)"];
    
    A -> B [label=" removed n={len(cochrane_info) - get_n_reviews_rows_outcomes_w_grade(parsed_sof_df)[0]}"];
    B -> C [label=" removed n={len(sof_original) - get_n_from_cochrane_ids(unflagged_criteria.index)[0]}"];
    C -> D1 -> E1;
    C -> D4;
    D1 -> E2;
    D1 -> E3;
    D4 -> E4 [label=" removed n={get_n_from_cochrane_ids(unflagged_criteria.index[~unflagged_criteria["participants_or_studies_set"]][unflagged_criteria.index[~unflagged_criteria["participants_or_studies_set"]].isin(cochrane_ids_reviewed_excluded)])[0]} after manual review \nwithout Nr. of participants or studies"];
    E1 -> F1;
    E2 -> F1;
    E3 -> F1;
    E4 -> F1;
}}
"""

# Create flowchart 
dot = graphviz.Source(flowchart)
dot.render("final/25-04-01-flowchart", format="svg", cleanup=True)
#dot.render("final/flowchart", format="pdf", cleanup=True)

st.image("final/25-04-01-flowchart.svg", caption="Flowchart of the Cochrane reviews included in the analysis", width=900)

#%%
# Selectboxed

cochrane_id = st.selectbox(f"Unflagged reviews ({len(cochrane_ids_unflagged)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_unflagged).sum()} outcomes)", cochrane_ids_unflagged, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Thereof reviewed for tweaking ({len(cochrane_ids_reviewed_tuning)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_reviewed_tuning).sum()} outcomes; mean fraction_length: {manual_extraction.loc[cochrane_ids_reviewed_tuning, "fraction_length"].mean():0.3f}, mean fraction_equal: {manual_extraction.loc[cochrane_ids_reviewed_tuning, "fraction_equal"].mean():0.3f})", cochrane_ids_reviewed_tuning, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}, (fraction_equal: {manual_extraction.loc[x, "fraction_equal"]:0.3f})")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Thereof fraction_equal < 1 ({len(cochrane_ids_reviewed_tuning_differs)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_reviewed_tuning_differs).sum()} outcomes; mean fraction_equal: {manual_extraction.loc[cochrane_ids_reviewed_tuning_differs, "fraction_equal"].mean():0.3f})", cochrane_ids_reviewed_tuning_differs, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}, (fraction_equal: {manual_extraction.loc[x, "fraction_equal"]:0.3f})")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Test set 100 ({len(cochrane_ids_reviewed_test)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_reviewed_test).sum()} outcomes; mean fraction_length: {manual_extraction.loc[cochrane_ids_reviewed_test, "fraction_length"].mean():0.3f}, mean fraction_equal: {manual_extraction.loc[cochrane_ids_reviewed_test, "fraction_equal"].mean():0.3f})", cochrane_ids_reviewed_test, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}, (fraction_equal: {manual_extraction.loc[x, "fraction_equal"]:0.3f})")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Thereof fraction_equal < 1 ({len(cochrane_ids_reviewed_test_differs)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_reviewed_test_differs).sum()} outcomes; mean fraction_equal: {manual_extraction.loc[cochrane_ids_reviewed_test_differs, "fraction_equal"].mean():0.3f})", cochrane_ids_reviewed_test_differs, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}, (fraction_equal: {manual_extraction.loc[x, "fraction_equal"]:0.3f})")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Flagged reviews unreviewed ({len(cochrane_ids_flagged_undecided)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_flagged_undecided).sum()} outcomes)", cochrane_ids_flagged_undecided, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Flagged reviews included ({len(cochrane_ids_flagged_included)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_flagged_included).sum()} outcomes; mean fraction_length: {manual_extraction.loc[cochrane_ids_flagged_included, "fraction_length"].mean():0.3f}, mean fraction_equal: {manual_extraction.loc[cochrane_ids_flagged_included, "fraction_equal"].mean():0.3f})", cochrane_ids_flagged_included, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}, (fraction_length: {manual_extraction.loc[x, "fraction_length"]:0.3f}, fraction_equal: {manual_extraction.loc[x, "fraction_equal"]:0.3f})")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Flagged reviews excluded ({len(cochrane_ids_flagged_excluded)} with {parsed_sof_df["cochrane_id"].isin(cochrane_ids_flagged_excluded).sum()} outcomes)", cochrane_ids_flagged_excluded, index=None, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}")

if not cochrane_id:
    cochrane_id = st.selectbox(f"Total included reviews ({len(cochrane_ids_total_included)} with {len(final_sof_df)} outcomes)", cochrane_ids_total_included, index=0, format_func=lambda x: f"{x}: {cochrane_info.loc[x, 'Title']}")

st.link_button("Open in Cochrane", f"https://doi.org/10.1002/14651858.{cochrane_id}")

#%%
sof_df = parsed_sof_df[parsed_sof_df["cochrane_id"] == cochrane_id]

if cochrane_id in manual_sof_df_dict.keys():
    manual_sof_df = manual_sof_df_dict[cochrane_id]
else:
    manual_sof_df = None

st.markdown(f"{sof_df['table_nr'].max()} SOF table(s), {sof_df.shape[0]} outcome(s)")

# SOF tables

st.header("Original SOF tables")

html_content = sof_original[cochrane_id]
soup = BeautifulSoup(html_content, "html.parser")
tables = soup.find_all("table", class_="summary-of-findings")

for table_nr in range(1, len(tables)+1):
    st.subheader(f"SOF table {table_nr}")
    
    manual_extraction_table = manual_extraction_per_table[(manual_extraction_per_table["cochrane_id"] == cochrane_id) & (manual_extraction_per_table["table_nr"] == table_nr)]
    assert len(manual_extraction_table) <= 1
    if len(manual_extraction_table):
        manual_extraction_table = manual_extraction_table.iloc[0]
        if manual_extraction_table["fraction_equal"] < 1:
            st.subheader(f"Difference between manual and automatic extraction (fraction_length: {manual_extraction_table["fraction_length"]:0.3f}, fraction_equal: {manual_extraction_table["fraction_equal"]:0.3f})")
            manual_extraction_table["compare"]

    col1, col2 = st.columns(2)

    with col2:
        if (sof_df["table_nr"] == table_nr).sum():
            tab1 = st.tabs(["Automatic Extraction"])[0]
            with tab1:
                edited = st.data_editor(
                    sof_df.loc[sof_df["table_nr"] == table_nr, ["rowname", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned"]],
                    column_config={
                        "effect_type": "t", "point_estimate": "e", "lower_ci": "lo", "upper_ci": "up", "nr_participants_cleaned": "n_p", "nr_studies_cleaned": "n_s", "certainty_cleaned": "grade"
                    },
                    hide_index=True
                )

                sof_df.loc[sof_df["table_nr"] == table_nr, ["rowname", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned"]] = edited
    
    with col1:
        #with st.expander(f"SOF table {i}", True):
        tab1, tab2 = st.tabs(["Original Table", "Manual Extraction"])

        # Raw table
        table = tables[table_nr-1]
        with tab1:
            st.html(str(table))
        with tab2:
            if type(manual_sof_df) == pd.DataFrame:
                st.dataframe(
                    manual_sof_df.loc[manual_sof_df["table_nr"] == table_nr, ["rowname", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned"]],
                    hide_index=True
                )

st.download_button("Download SOF tables as CSV", sof_df[["cochrane_id", "table_nr", "row_nr", "rowname", "effect_type", "point_estimate", "lower_ci", "upper_ci", "nr_participants_cleaned", "nr_studies_cleaned", "certainty_cleaned"]].to_csv(index=False), file_name=f"{cochrane_id}.csv")
