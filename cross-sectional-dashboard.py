#%%
import streamlit as st
import numpy as np
import pandas as pd

from functions import create_box_pie_plot

effect_size_cutoffs = {
    "Very Large": 5,
    "Large": 2,
    "Medium": 1.5,
    "Small": 1.2,
    "Minimal": 1
}

st.set_page_config(page_title="Cochrane Reviews", layout="wide")
#st.set_page_config(page_title="Cochrane Reviews", layout="wide", initial_sidebar_state="auto", menu_items=None)

st.html("""
<style>
MainMenu, header, footer {visibility: hidden;}
        
.stMainBlockContainer {padding-top: 2rem; padding-bottom: 0rem;}
</style>
""")

st.header("Cochrane Reviews on Interventions with Summary of Findings (SoF) Table(s)")

@st.cache_data
def get_cochrane_info_incl_topics():
    cochrane_info = pd.read_csv("final/25-04-01-final_cochrane_info.csv", index_col=0)
    cochrane_info["URL"] = "http://dx.doi.org/10.1002/14651858." + cochrane_info.index
    
    review_groups = cochrane_info["Cochrane Review Group Code"].str.split("; ").to_list()
    review_groups = [review_group for sublist in review_groups for review_group in sublist]
    review_groups = pd.Series(review_groups).value_counts().to_dict()

    keywords = cochrane_info["Keywords"].str.split("; ").to_list()
    keywords = [keyword for sublist in keywords if isinstance(sublist, list) for keyword in sublist]
    # Remove squared brackets and contents from keywords
    keywords = [keyword.split("[")[0].strip() for keyword in keywords if isinstance(keyword, str)]
    # Remove asterisks from keywords
    keywords = [keyword.strip("*").strip() for keyword in keywords]

    keywords = pd.Series(keywords).value_counts().to_dict()

    # Add "Cochrane Topics" column to cochrane_info (Topics from https://www.cochranelibrary.com/cdsr/reviews)
    cochrane_info["Cochrane Topic"] = "no-topic"

    # TODO topics files have to be updated
    # topics = {k: pd.read_csv("data/24-07-cochrane-topics/" + k) for k in os.listdir("data/24-07-cochrane-topics/")}

    # #topics = {topic.replace("24-07-02-citation-export-interventions-", "").replace("24-07-04-citation-export-interventions-", "").replace(".csv", ""): index_review_id_wo_version(df) for topic, df in topics.items()}
    # topics = {topic.replace("24-07-02-citation-export-interventions-", "").replace("24-07-04-citation-export-interventions-", "").replace(".csv", ""): df.set_index("Cochrane Review ID") for topic, df in topics.items()}

    # for topic in topics.keys():
    #     for ind in topics[topic].index:
    #         if cochrane_info.loc[ind, "Cochrane Topic"] == "no-topic":
    #             cochrane_info.loc[ind, "Cochrane Topic"] = topic
    #         else:
    #             cochrane_info.loc[ind, "Cochrane Topic"] += "; " + topic

    # topics = cochrane_info["Cochrane Topic"].str.split("; ").to_list()
    # topics = [group for sublist in topics for group in sublist]
    # topics = pd.Series(topics).value_counts().to_dict()
    topics = {}

    final_sof_df = pd.read_csv("final/25-04-01-final_sof_df.csv")

    final_sof_df["has_relative_effect"] = final_sof_df["point_estimate"].notna()
    final_sof_df["significant"] = (final_sof_df[["point_estimate", "lower_ci"]]>1).all(axis=1) | (final_sof_df[["point_estimate", "upper_ci"]]<1).all(axis=1)

    # For dichotomous outcomes, in this case, one may consider rating down by two levels immediately if the ratio of the upper- to the lower-boundary of the CI is higher than 2.5 for odds ratios or 3.0 for relative risk ratios.
    # https://usblog.gradeworkinggroup.org/2022/09/when-is-imprecision-very-serious-for.html
    # Simulations conducted to inform GRADE guidance for addressing imprecision of dichotomous outcomes in the context of network meta-analysis provided insights into how many levels to rate down for imprecision in pairwise meta-analysis when considering the OIS [12]. These simulations suggested that when the ratio of the upper to the lower boundary of the CI is higher than 2.5 for odds ratios and three for RRs, the sample size is, for any reasonable combination of baseline risk and treatment effect, very far from meeting the OIS. Therefore, authors would not need to calculate the OIS and can rate down the certainty of evidence by two levels (Box 5, circumstance 1).
    # Using the OIS approach, for dichotomous outcomes, one should consider rating down two levels for imprecision, when the ratio of the upper to the lower boundary of the CI is more than 2.5 for odds ratio or three for risk ratio;
    # https://www.jclinepi.com/article/S0895-4356(22)00187-1/fulltext
    # Unclear how to handle HR - handle like OR at the moment (i.e., cutoff 2.5)
    final_sof_df["ci_very_wide"] = np.where(
        final_sof_df["effect_type"] == "RR",
        (final_sof_df["upper_ci"] / final_sof_df["lower_ci"]) > 3,
        (final_sof_df["upper_ci"] / final_sof_df["lower_ci"]) > 2.5
    )

    effect_sizes = list(effect_size_cutoffs.keys())
    for i in range(len(effect_sizes)):
        effect_size = effect_sizes[i]
        if i == 0:
            final_sof_df[effect_size] = (final_sof_df["point_estimate"] >= effect_size_cutoffs[effect_size]) | (final_sof_df["point_estimate"] <= (1/effect_size_cutoffs[effect_size]))
        else:
            final_sof_df[effect_size] = ((final_sof_df["point_estimate"] >= effect_size_cutoffs[effect_size]) & (final_sof_df["point_estimate"] < effect_size_cutoffs[effect_sizes[i-1]])) | \
                                            ((final_sof_df["point_estimate"] > (1/effect_size_cutoffs[effect_sizes[i-1]])) & (final_sof_df["point_estimate"] <= (1/effect_size_cutoffs[effect_size])))
    
    #cochrane_info = cochrane_info[cochrane_info.index.isin(final_sof_df["cochrane_id"].unique())]

    return cochrane_info, review_groups, topics, keywords, final_sof_df

cochrane_info, review_groups, topics, keywords, final_sof_df = get_cochrane_info_incl_topics()

cochrane_info["Year / Issue"] = cochrane_info["Year"].astype(str) + "/" + cochrane_info["Issue"].astype(str).str.zfill(2)

#%%
cols = st.columns(3)

# with cols[0]:
#     topics_sel = st.multiselect(
#         "Select Topics", topics.keys(),
#         placeholder=f"Default: All {len(topics)} Topics",
#         format_func=lambda x: f"{x} ({topics[x]})"
#     )

with cols[0]:
    review_groups_sel = st.multiselect(
        "Select Review Groups", review_groups.keys(),
        placeholder=f"Default: All {len(review_groups)} Review Groups",
        format_func=lambda x: f"{x} ({review_groups[x]})"
    )

with cols[1]:
    keywords_sel = st.multiselect(
        "Select Keywords", keywords.keys(),
        placeholder=f"Default: All {len(keywords)} Keywords",
        format_func=lambda x: f"{x} ({keywords[x]})"
    )

with cols[2]:
    min_year = int(cochrane_info["Year"].min())
    max_year = int(cochrane_info["Year"].max())
    year_range = st.slider(
        "Select Year Range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1
    )

cols = st.columns([16, 16, 20 + 1, 6, 6, 6, 6, 12, 11], vertical_alignment="bottom")

primary_outcomes_sel = cols[0].checkbox("Primary outcomes only", help="The first outcome in the first Summary of Findings Table if it has a GRADE rating.", value=False)
mortality_outcomes_sel = cols[1].checkbox("Mortality outcomes only", help="Outcomes with 'mortality' or 'death' in their name.", value=False)
outcomes_with_ratio_sel = cols[2].checkbox("Outcomes with Relative Effects only", help="Dichotomous (=binary) outcomes with Risk Ratios / Rate Ratios (RR), Odds Ratios (OR), Hazard Ratios (HR) in the 'Relative Effects' column.", value=False)

effect_type_sel = {}
effect_type_sel["RR"] = cols[3].checkbox("RR", help="Risk Ratio / Rate Ratio", value=True, disabled=not outcomes_with_ratio_sel)
effect_type_sel["OR"] = cols[4].checkbox("OR", help="Odds Ratio", value=True, disabled=not outcomes_with_ratio_sel)
effect_type_sel["HR"] = cols[5].checkbox("HR", help="Hazard Ratio", value=True, disabled=not outcomes_with_ratio_sel)

significant_sel = cols[7].checkbox("Significant", value=True, help="Only for Outcomes with ratios. Significant outcomes are those with RR/OR/HR confidence intervals (CIs) not including 1.", disabled=not outcomes_with_ratio_sel)
nonsignificant_sel = cols[8].checkbox("Nonsignificant", value=True, help="Only for Outcomes with ratios. Significant outcomes are those with RR/OR/HR confidence intervals (CIs) not including 1.", disabled=not outcomes_with_ratio_sel)

cols = st.columns([16, 16, 9, 8, 8, 8, 8 + 4, 12, 11], vertical_alignment="bottom")

effect_size_sel = {}
effect_size_sel["Very Large"] = cols[2].checkbox("Very Large", help=f"RR/OR/HR ≥ {effect_size_cutoffs['Very Large']:.2f} or ≤ {1/effect_size_cutoffs['Very Large']:.2f}", value=True, disabled=not outcomes_with_ratio_sel)
effect_size_sel["Large"] = cols[3].checkbox("Large", help=f"RR/OR/HR (≥ {effect_size_cutoffs['Large']:.2f} and < {effect_size_cutoffs['Very Large']:.2f}) or (> {1/effect_size_cutoffs['Very Large']:.2f} and ≤ {1/effect_size_cutoffs['Large']:.2f})", value=True, disabled=not outcomes_with_ratio_sel)
effect_size_sel["Medium"] = cols[4].checkbox("Medium", help=f"RR/OR/HR (≥ {effect_size_cutoffs['Medium']:.2f} and < {effect_size_cutoffs['Large']:.2f}) or (> {1/effect_size_cutoffs['Large']:.2f} and ≤ {1/effect_size_cutoffs['Medium']:.2f})", value=True, disabled=not outcomes_with_ratio_sel)
effect_size_sel["Small"] = cols[5].checkbox("Small", help=f"RR/OR/HR (≥ {effect_size_cutoffs['Small']:.2f} and < {effect_size_cutoffs['Medium']:.2f}) or (> {1/effect_size_cutoffs['Medium']:.2f} and ≤ {1/effect_size_cutoffs['Small']:.2f})", value=True, disabled=not outcomes_with_ratio_sel)
effect_size_sel["Minimal"] = cols[6].checkbox("Minimal", help=f"RR/OR/HR (≥ {effect_size_cutoffs['Minimal']:.2f} and < {effect_size_cutoffs['Small']:.2f}) or (> {1/effect_size_cutoffs['Small']:.2f} and ≤ {1/effect_size_cutoffs['Minimal']:.2f})", value=True, disabled=not outcomes_with_ratio_sel)

ci_not_very_wide_sel = cols[7].checkbox("CI not very wide", help="Confidence Interval (CI) ratio (upper/lower) ≤ 3 for RR or ≤ 2.5 for OR/HR (Compare: GRADE Guidance 34: update on rating imprecision using a minimally contextualized approach. Zeng, Linan et al. Journal of Clinical Epidemiology. 2022. Volume 150, 216 - 224.)", value=True, disabled=not outcomes_with_ratio_sel)
ci_very_wide_sel = cols[8].checkbox("CI very wide", help="Confidence Interval (CI) ratio (upper/lower) > 3 for RR or > 2.5 for OR/HR (Compare: GRADE Guidance 34: update on rating imprecision using a minimally contextualized approach. Zeng, Linan et al. Journal of Clinical Epidemiology. 2022. Volume 150, 216 - 224.)", value=True, disabled=not outcomes_with_ratio_sel)

# effect_size_range = st.select_slider(
#     "Select Effect Size Range",
#     options=[1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5, 4.75, 5.0, "infinity"],
#     value=(1.0, "infinity"),
# )
# effect_size_range = st.select_slider(
#     "Confidence Interval Ratio (Upper/Lower)",
#     options=[1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5, 4.75, 5.0, "infinity"],
#     value=1.0,
# )
#effect_size_sel = st.radio("Effect size", ["Very Large", "Large", "Medium", "Small", "Minimal", "Any"], index=5, help="Only for Outcomes with ratios. Outcomes with Very Large effects are those with RR/OR/HR ≥ 5 or ≤ 0.2.", horizontal=True, disabled=not outcomes_with_ratio_sel)
#if not outcomes_with_ratio_sel:
#    effect_size_sel = "Both"
#significance_sel = st.radio("Statistical significance", ["Significant", "Nonsignificant", "Any"], index=2, help="Only for Outcomes with ratios. Significant outcomes are those with RR/OR/HR confidence intervals (CIs) not including 1.", horizontal=True, disabled=not outcomes_with_ratio_sel)
#if not outcomes_with_ratio_sel:
#    significance_sel = "Both"

# Filter sof_dfs to match filtered reviews

def get_filtered_data():
    cochrane_info_sub = cochrane_info[(cochrane_info["Year"] >= year_range[0]) & (cochrane_info["Year"] <= year_range[1])]

    # if len(topics_sel):
    #     cochrane_info_sub = cochrane_info_sub[
    #         cochrane_info_sub["Cochrane Topic"].apply(lambda x: any(topic in x for topic in topics_sel))
    #     ]

    if len(review_groups_sel):
        cochrane_info_sub = cochrane_info_sub[
            cochrane_info_sub["Cochrane Review Group Code"].apply(lambda x: any(review_group in x for review_group in review_groups_sel))
        ]

    if len(keywords_sel):
        cochrane_info_sub = cochrane_info_sub[
            cochrane_info_sub["Keywords"].apply(lambda x: isinstance(x, str) and any(keyword in x for keyword in keywords_sel))
        ]

    final_sof_df_sub = final_sof_df[final_sof_df["cochrane_id"].isin(cochrane_info_sub.index)]

    # These are AND connected
    if primary_outcomes_sel:
        final_sof_df_sub = final_sof_df_sub[final_sof_df_sub["primary_outcome"]]
    if mortality_outcomes_sel:
        final_sof_df_sub = final_sof_df_sub[final_sof_df_sub["mortality_outcome"]]
    if outcomes_with_ratio_sel:
        final_sof_df_sub = final_sof_df_sub[final_sof_df_sub["has_relative_effect"]]
        # The following are OR connected
        final_sof_df_sub = final_sof_df_sub[final_sof_df_sub["effect_type"].isin(pd.Series(effect_type_sel.keys())[effect_type_sel.values()])]
        final_sof_df_sub = final_sof_df_sub[(significant_sel & final_sof_df_sub["significant"]) | (nonsignificant_sel & ~final_sof_df_sub["significant"])]
        final_sof_df_sub = final_sof_df_sub[final_sof_df_sub[pd.Series(effect_size_sel.keys())[effect_size_sel.values()]].any(axis=1)]
        final_sof_df_sub = final_sof_df_sub[(ci_very_wide_sel & final_sof_df_sub["ci_very_wide"]) | (ci_not_very_wide_sel & ~final_sof_df_sub["ci_very_wide"])]

    cochrane_info_sub = cochrane_info_sub[cochrane_info_sub.index.isin(final_sof_df_sub["cochrane_id"].unique())]

    cochrane_info_sub = pd.concat([
        cochrane_info_sub,
        final_sof_df_sub.groupby("cochrane_id").agg(
            nr_outcomes = pd.NamedAgg("certainty_cleaned", "size"),
            median_nr_participants = pd.NamedAgg("nr_participants_cleaned", "median"),
            median_nr_studies = pd.NamedAgg("nr_studies_cleaned", "median"),
        ),
        final_sof_df_sub[final_sof_df_sub["certainty_cleaned"] == "very low"].groupby("cochrane_id").agg(
            nr_outcomes_very_low = pd.NamedAgg("certainty_cleaned", "size"),
            very_low_median_nr_participants = pd.NamedAgg("nr_participants_cleaned", "median"),
            very_low_median_nr_studies = pd.NamedAgg("nr_studies_cleaned", "median"),
        ),
        final_sof_df_sub[final_sof_df_sub["certainty_cleaned"] == "low"].groupby("cochrane_id").agg(
            nr_outcomes_low = pd.NamedAgg("certainty_cleaned", "size"),
            low_median_nr_participants = pd.NamedAgg("nr_participants_cleaned", "median"),
            low_median_nr_studies = pd.NamedAgg("nr_studies_cleaned", "median"),
        ),
        final_sof_df_sub[final_sof_df_sub["certainty_cleaned"] == "moderate"].groupby("cochrane_id").agg(
            nr_outcomes_moderate = pd.NamedAgg("certainty_cleaned", "size"),
            moderate_median_nr_participants = pd.NamedAgg("nr_participants_cleaned", "median"),
            moderate_median_nr_studies = pd.NamedAgg("nr_studies_cleaned", "median"),
        ),
        final_sof_df_sub[final_sof_df_sub["certainty_cleaned"] == "high"].groupby("cochrane_id").agg(
            nr_outcomes_high = pd.NamedAgg("certainty_cleaned", "size"),
            high_median_nr_participants = pd.NamedAgg("nr_participants_cleaned", "median"),
            high_median_nr_studies = pd.NamedAgg("nr_studies_cleaned", "median"),
        )
    ], axis=1)
    cochrane_info_sub = cochrane_info_sub.rename(columns={
        "nr_outcomes": "# Outcomes",
        "nr_outcomes_very_low": "# Very Low Outcomes",
        "nr_outcomes_low": "# Low Outcomes",
        "nr_outcomes_moderate": "# Moderate Outcomes",
        "nr_outcomes_high": "# High Outcomes",
        "median_nr_participants": "Median # Participants",
        "very_low_median_nr_participants": "Median # Participants Very Low",
        "low_median_nr_participants": "Median # Participants Low",
        "moderate_median_nr_participant": "Median # Participants Moderate",
        "high_median_nr_participants": "Median # Participants High",
        "median_nr_studies": "Median # Studies",
        "very_low_median_nr_studies": "Median # Studies Very Low",
        "low_median_nr_studies": "Median # Studies Low",
        "moderate_median_nr_studies": "Median # Studies Moderate",
        "high_median_nr_studies": "Median # Studies High"
    })

    return cochrane_info_sub, final_sof_df_sub

cochrane_info_sub, final_sof_df_sub = get_filtered_data()

#%%
st.subheader(f"{len(cochrane_info_sub)} / {len(cochrane_info)} Reviews with {len(final_sof_df_sub)} / {len(final_sof_df)} Outcomes*")

"\*Only outcomes with a GRADE rating and with positive Number of Participants and/or Studies are considered."

cols = st.columns([1.5,1])

if len(cochrane_info_sub):
    with cols[0]:
        #cochrane_info_sub.index = "[" + cochrane_info_sub["Title"] + "](" + cochrane_info_sub["URL"] + ")"
        #st.table(cochrane_info_sub[columns_to_show])

        cochrane_info_sub_sel = st.dataframe(
            cochrane_info_sub,
            use_container_width=True,
            hide_index=True,
            selection_mode="multi-row",
            column_config={
                "Year": None,
                "Issue": None,
                "Cochrane Review Group Code": None,
                "Cochrane Topic": None,
                "Keywords": None,
                "Year / Issue": st.column_config.Column(width="small"),
                "URL": st.column_config.LinkColumn(
                    "URL", display_text="Open"
                ),
            },
            on_select="rerun"
        )

        selected_cochrane_ids = cochrane_info_sub.index[cochrane_info_sub_sel["selection"]["rows"]]

        if len(selected_cochrane_ids):
            final_sof_df_sub = final_sof_df_sub[final_sof_df_sub["cochrane_id"].isin(selected_cochrane_ids)]
            st.subheader(f"{len(selected_cochrane_ids)} Review(s) with {len(final_sof_df_sub)} Outcome(s) Selected")
            st.dataframe(final_sof_df_sub, hide_index=True, use_container_width=True)

    with cols[1]:
        plot_df = final_sof_df_sub
        fig_axes = create_box_pie_plot(plot_df)
        #fig_axes[0].suptitle("All Outcomes")
        #fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
        st.pyplot(fig_axes[0], use_container_width=True)