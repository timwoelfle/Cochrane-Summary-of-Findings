#%%
import os
import re
import streamlit as st
import numpy as np
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
#alt.data_transformers.enable("vegafusion")

from functions import create_box_pie_plot

st.set_page_config(page_title="Cochrane Reviews", layout="wide")

@st.cache_data
def get_cochrane_info_incl_topics():
    cochrane_info = pd.read_csv("data/25-04-01-citation-export-interventions-no-abstract.csv", index_col=0)
    
    review_groups = cochrane_info["Cochrane Review Group Code"].str.split('; ').to_list()
    review_groups = [review_group for sublist in review_groups for review_group in sublist]
    review_groups = pd.Series(review_groups).value_counts().to_dict()

    keywords = cochrane_info["Keywords"].str.split('; ').to_list()
    keywords = [keyword for sublist in keywords if isinstance(sublist, list) for keyword in sublist]
    # Remove squared brackets and contents from keywords
    keywords = [keyword.split('[')[0].strip() for keyword in keywords if isinstance(keyword, str)]
    # Remove asterisks from keywords
    keywords = [keyword.strip('*').strip() for keyword in keywords]

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

    # topics = cochrane_info["Cochrane Topic"].str.split('; ').to_list()
    # topics = [group for sublist in topics for group in sublist]
    # topics = pd.Series(topics).value_counts().to_dict()
    topics = {}

    parsed_sof_df = pd.read_csv("results/25-04-01-parsed_sof_df.csv")
    
    cochrane_info["Has SOF-Table"] = cochrane_info.index.isin(parsed_sof_df["cochrane_id"].unique())

    return cochrane_info, review_groups, topics, keywords, parsed_sof_df

cochrane_info, review_groups, topics, keywords, parsed_sof_df = get_cochrane_info_incl_topics()

# cochrane_info.index[(~cochrane_info["Has SOF-Table"]) & (cochrane_info["Year"] > 2020)]
# Index(['CD007968.PUB3', 'CD015424.PUB2', 'CD013255.PUB2', 'CD012361.PUB2',
#        'CD014616', 'CD013637.PUB2', 'CD001322.PUB2', 'CD015582.PUB2',
#        'CD015511.PUB2', 'CD015236.PUB2', 'CD013730.PUB2', 'CD004030.PUB4',
#        'CD015775', 'CD011535.PUB6', 'CD014553.PUB2', 'CD012458.PUB2',
#        'CD013780.PUB2', 'CD012218.PUB2', 'CD013182.PUB2', 'CD015769',
#        'CD007593.PUB2', 'CD013201.PUB3', 'CD013813.PUB2', 'CD003733.PUB5',
#        'CD013634.PUB2', 'CD011335.PUB3', 'CD015023.PUB2', 'CD012246.PUB2',
#        'CD014703.PUB2', 'CD002204.PUB5', 'CD015077', 'CD012979.PUB3',
#        'CD012926.PUB2', 'CD008461.PUB4', 'CD013644.PUB2', 'CD013345.PUB2',
#        'CD012992.PUB2', 'CD013839.PUB2', 'CD011059.PUB4', 'CD013242.PUB2',
#        'CD009046.PUB3', 'CD011823.PUB3', 'CD009325.PUB3', 'CD004986.PUB4',
#        'CD013755.PUB2', 'CD008583.PUB3', 'CD010849.PUB4', 'CD012985.PUB2',
#        'CD010288.PUB5', 'CD011406.PUB2', 'CD011907.PUB3', 'CD013664.PUB2',
#        'CD009719.PUB3', 'CD012924.PUB2', 'CD013488.PUB2', 'CD012920.PUB2',
#        'CD012923.PUB2', 'CD013702.PUB2', 'CD003424.PUB5', 'CD008708.PUB5',
#        'CD012866.PUB2', 'CD004060.PUB3', 'CD013118.PUB2', 'CD011973.PUB2',
#        'CD001507.PUB4'],
#       dtype='object', name='Cochrane Review ID')
# All of these were checked manually and lacked a SOF table (mostly "empty reviews" with 0 included studies or withdrawn reviews) except:
# - CD011406.PUB2 has empty SOF table
# - CD012924.PUB2 has empty SOF table
# - CD013255.PUB2: SOF tables as Figures...
# - CD004030.PUB4: SOF table without proper class and section to be correctly identified, also completely non-standard format

#%%
col1, col2, col3, col4 = st.columns(4)

with col1:
    topics_sel = st.multiselect(
        "Select Topics", topics.keys(),
        placeholder=f"Default: All {len(topics)} Topics",
        format_func=lambda x: f"{x} ({topics[x]})"
    )

with col2:
    review_groups_sel = st.multiselect(
        "Select Review Groups", review_groups.keys(),
        placeholder=f"Default: All {len(review_groups)} Review Groups",
        format_func=lambda x: f"{x} ({review_groups[x]})"
    )

with col3:
    keywords_sel = st.multiselect(
        "Select Keywords", keywords.keys(),
        placeholder=f"Default: All {len(keywords)} Keywords",
        format_func=lambda x: f"{x} ({keywords[x]})"
    )

with col4:
    min_year = int(cochrane_info["Year"].min())
    max_year = int(cochrane_info["Year"].max())
    year_range = st.slider(
        "Select Year Range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1
    )

# Filter sof_dfs to match filtered reviews
def get_filtered_data():
    cochrane_info_sub = cochrane_info[(cochrane_info["Year"] >= year_range[0]) & (cochrane_info["Year"] <= year_range[1])]

    if len(topics_sel):
        cochrane_info_sub = cochrane_info_sub[
            cochrane_info_sub["Cochrane Topic"].apply(lambda x: any(topic in x for topic in topics_sel))
        ]

    if len(review_groups_sel):
        cochrane_info_sub = cochrane_info_sub[
            cochrane_info_sub["Cochrane Review Group Code"].apply(lambda x: any(review_group in x for review_group in review_groups_sel))
        ]

    if len(keywords_sel):
        cochrane_info_sub = cochrane_info_sub[
            cochrane_info_sub["Keywords"].apply(lambda x: isinstance(x, str) and any(keyword in x for keyword in keywords_sel))
        ]

    parsed_sof_df_sub = parsed_sof_df[parsed_sof_df["cochrane_id"].isin(cochrane_info_sub.index)]

    return cochrane_info_sub, parsed_sof_df_sub

cochrane_info_sub, parsed_sof_df_sub = get_filtered_data()

#%%
st.header(f"All Cochrane Reviews ({cochrane_info_sub.shape[0]} / {cochrane_info.shape[0]})")

columns_to_show = st.multiselect(
    "Show columns",
    cochrane_info_sub.columns,
    default=["Title", "Year", "Issue", "URL", "Cochrane Review Group Code", "Cochrane Topic"]
)

st.dataframe(cochrane_info_sub[columns_to_show], use_container_width=True)

#%%
st.header(f"Reviews with SOF-Table ({cochrane_info_sub['Has SOF-Table'].sum()} / {cochrane_info['Has SOF-Table'].sum()})")

st.altair_chart(
    alt.Chart(cochrane_info_sub).mark_bar().encode(
        x='Year:O',
        y='count()',
        color='Has SOF-Table:N'
    ).properties(
        title='Proportion of Cochrane Reviews with SOF-Tables'
    ).interactive()
)

#%%

# Only use unflagged reviews for now
parsed_sof_df_sub = parsed_sof_df_sub[parsed_sof_df_sub["certainty_cleaned"].notna() & ((parsed_sof_df_sub["nr_studies_cleaned"] > 0) | (parsed_sof_df_sub["nr_participants_cleaned"] > 0))]

st.subheader(f"Outcomes ({parsed_sof_df_sub.shape[0]} / {parsed_sof_df.shape[0]})")

col1, col2, col3 = st.columns(3)

with col1:
    plot_df = parsed_sof_df_sub
    fig_axes = create_box_pie_plot(plot_df)
    fig_axes[0].suptitle("All Outcomes")
    fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
    st.pyplot(fig_axes[0], use_container_width=True)

with col2:
    plot_df = parsed_sof_df_sub[parsed_sof_df_sub["primary_outcome"]]
    fig_axes = create_box_pie_plot(plot_df)
    fig_axes[0].suptitle("Primary Outcomes")
    fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
    st.pyplot(fig_axes[0], use_container_width=True)

with col3:
    plot_df = parsed_sof_df_sub[parsed_sof_df_sub["mortality_outcome"]]
    fig_axes = create_box_pie_plot(plot_df)
    fig_axes[0].suptitle("Mortality Outcomes")
    fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
    st.pyplot(fig_axes[0], use_container_width=True)

with col1:
    plot_df = parsed_sof_df_sub[parsed_sof_df_sub["significant"]]
    fig_axes = create_box_pie_plot(plot_df)
    fig_axes[0].suptitle("All Significant Outcomes")
    fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
    st.pyplot(fig_axes[0], use_container_width=True)

with col2:
    plot_df = parsed_sof_df_sub[parsed_sof_df_sub["significant"] & parsed_sof_df_sub["primary_outcome"]]
    fig_axes = create_box_pie_plot(plot_df)
    fig_axes[0].suptitle("Significant Primary Outcomes")
    fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
    st.pyplot(fig_axes[0], use_container_width=True)

with col3:
    plot_df = parsed_sof_df_sub[parsed_sof_df_sub["significant"] & parsed_sof_df_sub["mortality_outcome"]]
    fig_axes = create_box_pie_plot(plot_df)
    fig_axes[0].suptitle("Significant Mortality Outcomes")
    fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
    st.pyplot(fig_axes[0], use_container_width=True)

with col1:
    plot_df = parsed_sof_df_sub[parsed_sof_df_sub["has_relative_effect"] & (~parsed_sof_df_sub["significant"])]
    fig_axes = create_box_pie_plot(plot_df)
    fig_axes[0].suptitle("All Insignificant Outcomes")
    fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
    st.pyplot(fig_axes[0], use_container_width=True)

with col2:
    plot_df = parsed_sof_df_sub[parsed_sof_df_sub["has_relative_effect"] & (~parsed_sof_df_sub["significant"]) & parsed_sof_df_sub["primary_outcome"]]
    fig_axes = create_box_pie_plot(plot_df)
    fig_axes[0].suptitle("Insignificant Primary Outcomes")
    fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
    st.pyplot(fig_axes[0], use_container_width=True)

with col3:
    plot_df = parsed_sof_df_sub[parsed_sof_df_sub["has_relative_effect"] & (~parsed_sof_df_sub["significant"]) & parsed_sof_df_sub["mortality_outcome"]]
    fig_axes = create_box_pie_plot(plot_df)
    fig_axes[0].suptitle("Insignificant Mortality Outcomes")
    fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
    st.pyplot(fig_axes[0], use_container_width=True)

with col1:
    plot_df = parsed_sof_df_sub[parsed_sof_df_sub["very_large_effect"]]
    fig_axes = create_box_pie_plot(plot_df)
    fig_axes[0].suptitle("All Outcomes with very large Effects")
    fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
    st.pyplot(fig_axes[0], use_container_width=True)

with col2:
    plot_df = parsed_sof_df_sub[parsed_sof_df_sub["very_large_effect"] & parsed_sof_df_sub["primary_outcome"]]
    fig_axes = create_box_pie_plot(plot_df)
    fig_axes[0].suptitle("Primary Outcomes with very large Effects")
    fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
    st.pyplot(fig_axes[0], use_container_width=True)

with col3:
    plot_df = parsed_sof_df_sub[parsed_sof_df_sub["very_large_effect"] & parsed_sof_df_sub["mortality_outcome"]]
    fig_axes = create_box_pie_plot(plot_df)
    fig_axes[0].suptitle("Mortality Outcomes with very large Effects")
    fig_axes[1].set_title(f"({plot_df.shape[0]} in {len(plot_df["cochrane_id"].unique())} Cochrane Reviews)")
    st.pyplot(fig_axes[0], use_container_width=True)

#%%

# outcome_selection_criteria = st.pills("Outcome selection criteria", ["primary_outcome", "mortality_outcome", "has_relative_effect", "significant", "very_large_effect"], selection_mode="multi")

# #@st.cache_data # not sure why it doesn't work - shouldn't cache be deleted when outcome_selection_criteria changes?
# def select_outcomes():
#     selected_outcomes = parsed_sof_df_sub
#     for selection_criterion in outcome_selection_criteria:
#         selected_outcomes = selected_outcomes[selected_outcomes[selection_criterion]]
#     return selected_outcomes

# selected_outcomes = select_outcomes()

# st.text(selected_outcomes.shape[0])

# col1, col2, col3 = st.columns(3)

# with col1:
#     # fig, ax = plt.subplots(figsize=(10, 6))
#     # counts = parsed_sof_df_sub['certainty_cleaned'].value_counts().sort_index()
#     # counts.plot(kind='bar', ax=ax)
#     # st.pyplot(fig)

#     # fig, ax = plt.subplots(figsize=(10, 6))
#     # parsed_sof_df_sub.boxplot(column="row_nr", by="certainty_cleaned", ax=ax, showfliers=False, meanline=True, showmeans=True)
#     # st.pyplot(fig)

#     df = selected_outcomes.groupby("cochrane_id")["certainty_cleaned"].value_counts(dropna=False).reset_index()

#     fig, ax = plt.subplots(figsize=(10, 6))
#     df.boxplot(column="count", by="certainty_cleaned", ax=ax, showfliers=False, meanline=True, showmeans=True)
#     st.pyplot(fig)

# with col2:
#     fig, ax = plt.subplots(figsize=(10, 6))
#     selected_outcomes.boxplot(column="nr_participants_cleaned", by="certainty_cleaned", ax=ax, showfliers=False, meanline=True, showmeans=True)
#     st.pyplot(fig)

# with col3:
#     fig, ax = plt.subplots(figsize=(10, 6))
#     selected_outcomes.boxplot(column="nr_studies_cleaned", by="certainty_cleaned", ax=ax, showfliers=False, meanline=True, showmeans=True)
#     ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
#     st.pyplot(fig)

# # Experimental treemap for selection
# import plotly.express as px
# event_dict = st.plotly_chart(
#     px.treemap(
#         names=parsed_sof_df_sub["header_control"].str.lower().value_counts()[1:50].index.to_list(),
#         parents=[""]*49,
#         values=parsed_sof_df_sub["header_control"].str.lower().value_counts()[1:50].to_list()
#     ),
#     on_select="rerun"
# )
# st.write(event_dict["selection"]["points"][0]["label"] if len(event_dict["selection"]["points"]) and "label" in event_dict["selection"]["points"][0] else None)

# # Doesn't work because this is added in an iframe, have to manually evaluate code in console at the moment
# st.components.v1.html("""<script>
# element = document.querySelector('.stPlotlyChart .js-plotly-plot')
# element.on('plotly_click', function(e) {
#     console.log('click', e)
#     element.emit('plotly_selected', { points: e.points })
# })
# </script>""")

# %%
