#%%
import re
from tqdm import tqdm
import pandas as pd
from bs4 import BeautifulSoup

from functions import table_merged_df, get_columns, extract_relative_effects_numbers_quality

#%%
cochrane_info = pd.read_csv("data/25-04-01-citation-export-interventions-no-abstract.csv")
cochrane_info.index = cochrane_info["Cochrane Review ID"]

sof_tables = pd.read_csv('data/25-04-01-sof-tables-interventions.csv', index_col=0)
sof_tables = sof_tables[~sof_tables["sof"].isna()]
sof_tables = sof_tables[sof_tables.index.isin(cochrane_info.index)]

data = []

for id in tqdm(sof_tables.index):
    html_content = sof_tables.loc[id, 'sof']
    # Replace non-breaking spaces for consistency (used inconsistently)
    html_content = html_content.replace('\xa0', ' ')
    # Replace all th with td for consistency (used inconsistently)
    html_content = html_content.replace('<th', '<td')
    html_content = html_content.replace('</th', '</td')
    # Convert superscript digits
    html_content = re.sub(r'(?<=<sup>)([\d,]+)(?=</sup>)', lambda m: ''.join(['⁰¹²³⁴⁵⁶⁷⁸⁹'[int(d)] if d.isdigit() else ' ' for d in m.group(0)]), html_content)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Loop over SOF-Tables to extract information
    tables = soup.find_all('table', class_='summary-of-findings')
    for table_nr in range(len(tables)):
        table = tables[table_nr]

        result_tuple = table_merged_df(table)
        if not result_tuple:
            continue
        table_title, header_rows, footer_rows, table_df, merged_df = result_tuple

        # Get columns
        rownames_col, relative_effects_col, nr_participants_studies_col, certainty_col = get_columns(merged_df)

        merged_df['NA'] = 'NA'
        
        # Only look at important columns
        sof_df = merged_df[[rownames_col, relative_effects_col, nr_participants_studies_col, certainty_col]]
        sof_df.columns = ['rowname', 'relative_effects', 'nr_participants_studies', 'certainty']
        sof_df = sof_df.drop_duplicates() # Some rows are now duplicated, mostly because they used to have multiple sub-rows in "Illustrative comparative rates"

        sof_df['cochrane_id'] = id
        sof_df['table_nr'] = table_nr + 1
        sof_df['table_title'] = table_title
        sof_df['rownames_col'] = rownames_col
        sof_df['relative_effects_col'] = relative_effects_col
        sof_df['nr_participants_studies_col'] = nr_participants_studies_col
        sof_df['certainty_col'] = certainty_col

        sof_df['row_nr'] = list(range(1, sof_df.shape[0]+1))
        
        data = data + sof_df[['cochrane_id', 'table_nr', 'table_title', 'rownames_col', 'relative_effects_col', 'nr_participants_studies_col', 'certainty_col', 'row_nr', 'rowname', 'relative_effects', 'nr_participants_studies', 'certainty']].reset_index(drop=True).values.tolist()
    
combined_sof_df = pd.DataFrame(data, columns=['cochrane_id', 'table_nr', 'table_title', 'rownames_col', 'relative_effects_col', 'nr_participants_studies_col', 'certainty_col', 'row_nr', 'rowname', 'relative_effects', 'nr_participants_studies', 'certainty'])

# Remove obvious footer cell that accidentally got included in the table (probably bad colspan)
combined_sof_df = combined_sof_df[~combined_sof_df["rowname"].str.lower().str.startswith("*the basis for the assumed risk", na=False)]
combined_sof_df = combined_sof_df[~combined_sof_df["rowname"].str.lower().str.startswith("*the risk in the intervention group", na=False)]
combined_sof_df = combined_sof_df[~combined_sof_df["rowname"].str.lower().str.startswith("grade working group", na=False)]
combined_sof_df = combined_sof_df[~combined_sof_df["rowname"].str.lower().str.startswith("ci: confidence interval", na=False)]

combined_sof_df.to_csv('results/25-04-01-combined_sof_df.csv', index=False)
# %%
combined_sof_df = pd.read_csv("results/25-04-01-combined_sof_df.csv")

parsed_sof_df = extract_relative_effects_numbers_quality(combined_sof_df)

# Remove ratio effects that are inconsistent (13 outcomes in 13 reviews)
# list(zip(
#     parsed_sof_df.loc[(parsed_sof_df["point_estimate"] < parsed_sof_df["lower_ci"]) | (parsed_sof_df["point_estimate"] > parsed_sof_df["upper_ci"]) | (parsed_sof_df["lower_ci"] > parsed_sof_df["upper_ci"]), "cochrane_id"],
#     parsed_sof_df.loc[(parsed_sof_df["point_estimate"] < parsed_sof_df["lower_ci"]) | (parsed_sof_df["point_estimate"] > parsed_sof_df["upper_ci"]) | (parsed_sof_df["lower_ci"] > parsed_sof_df["upper_ci"]), "relative_effects"]
# ))
# [('CD000544.PUB5', 'RR 1.25 (0.0.56 to 2.78)'),
#  ('CD001537.PUB5', 'RR 0.13 (0.40 to 0.15)'),
#  ('CD004185.PUB3', 'OR 1.04 (0.65 to 1. 68)'),
#  ('CD005506.PUB5', 'RR 0.52 (0.38 to 0.1)'),
#  ('CD006096.PUB4', 'RR 5.25 (0.94 to 1.90)'),
#  ('CD006196.PUB2', 'RR 1.16 (1.33 to 2.08)'),
#  ('CD006258.PUB2', 'RR 0.75 (0.81 to 0.92)'),
#  ('CD006531.PUB2', 'OR 1.98 (0.79 to 1.23)'),
#  ('CD010480.PUB2', 'RR 1.13 (1.47 to 2.68)'),
#  ('CD011559.PUB2',  "This comparison was only made in 1 study, which showed a significantly lower incidence of ORN in the HBO group (2/37 patients) when compared to the antibiotic group (11/37 patients) (6‐month follow‐up) (RR 0.18, 95% CI 0.43 to 0.76, P = 0.01 using Fisher's exact test)"),
#  ('CD012529.PUB2', 'RR 1.02 (1.22 to 1.45)'),
#  ('CD013344.PUB2', 'RR 0.07 (0.16 to 3.02)'),
#  ('CD013579.PUB2', 'RR 0.52 (0.69 to 3.34)')]
parsed_sof_df.loc[\
    (parsed_sof_df["point_estimate"] < parsed_sof_df["lower_ci"]) | (parsed_sof_df["point_estimate"] > parsed_sof_df["upper_ci"]) | (parsed_sof_df["lower_ci"] > parsed_sof_df["upper_ci"]),\
    ["effect_type", "point_estimate", "lower_ci", "upper_ci"]] = None

# When nr_studies_cleaned > 0 but nr_participants_cleaned == 0, set nr_participants_cleaned to None (46 outcomes in 30 reviews)
# list(zip(
#     parsed_sof_df.loc[(parsed_sof_df["nr_participants_cleaned"] == 0) & (parsed_sof_df["nr_studies_cleaned"] > 0), "cochrane_id"],
#     parsed_sof_df.loc[(parsed_sof_df["nr_participants_cleaned"] == 0) & (parsed_sof_df["nr_studies_cleaned"] > 0), "nr_participants_studies"]
# ))
# [('CD001088.PUB4', '0  (3 studies)'),
#  ('CD001470.PUB2', '0  (1 study)'),
#  ('CD001711.PUB2', '0  (3 studies)'),
#  ('CD001711.PUB2', '0  (3 studies)'),
#  ('CD002219.PUB2', '0 (2 studies)'),
#  ('CD002219.PUB2', '0 (2 studies)'),
#  ('CD003546.PUB3', '0 (1 study)'),
#  ('CD004269.PUB3', '0 (2 studies)'),
#  ('CD004269.PUB3', '0 (1 study)'),
#  ('CD004366.PUB6', '0  (6 studies)'),
#  ('CD004366.PUB6', '0  (4 studies)'),
#  ('CD004366.PUB6', '0  (1 study)'),
#  ('CD004366.PUB6', '0  (1 study)'),
#  ('CD004366.PUB6', '0  (3 studies)'),
#  ('CD004577.PUB3', '0 (1 study)'),
#  ('CD005135.PUB3', '0 (3)'),
#  ('CD005437.PUB4', '0  (1 study)⁸'),
#  ('CD006362.PUB4', '0  (2 studies)'),
#  ('CD006413.PUB2', '0  (1 study⁸ ⁹)'),
#  ('CD006413.PUB2', '0  (1 study⁸)'),
#  ('CD006459.PUB3', '0  (7 studies)'),
#  ('CD006459.PUB3', '0  (7 studies)'),
#  ('CD006716.PUB3', '0  (1 study)'),
#  ('CD006716.PUB3', '0  (1 study)'),
#  ('CD006853.PUB2', '0 (3 studies)'),
#  ('CD007160.PUB4', '0  (2 studies)'),
#  ('CD007160.PUB4', '0  (2 studies)'),
#  ('CD007177.PUB2', '0 (2 studies²)'),
#  ('CD007177.PUB2', '0 (2 studies²)'),
#  ('CD008739.PUB2', '0 (1 study)'),
#  ('CD008788.PUB3', '0  (4 studies)'),
#  ('CD008872.PUB2', '0 (1 study)'),
#  ('CD009101.PUB3', '0  (3 studies)'),
#  ('CD009101.PUB3', '0  (1 study)'),
#  ('CD009111.PUB3', '0  (1 study)'),
#  ('CD009111.PUB3', '0  (1)'),
#  ('CD009237.PUB2', '0 (34 studies)'),
#  ('CD009929.PUB2', '0 (1 study)'),
#  ('CD009992.PUB2', '0  (1 study)'),
#  ('CD011226.PUB2', '0  (3 studies)'),
#  ('CD011354.PUB2', '0  (1 study)'),
#  ('CD011565.PUB2', '0  (13)'),
#  ('CD011565.PUB2', '0  (2 studies)'),
#  ('CD011565.PUB2', '0  (2)'),
#  ('CD011856.PUB2', '0  (2 studies)'),
#  ('CD013305.PUB2', '0 (1 RCT)')]
parsed_sof_df.loc[\
    (parsed_sof_df["nr_participants_cleaned"] == 0) & (parsed_sof_df["nr_studies_cleaned"] > 0),\
    ["nr_participants_cleaned"]] = None

# Outcomes with nr_studies_cleaned > nr_participants_cleaned (32 outcomes in 11 reviews)
# list(zip(
#     parsed_sof_df.loc[parsed_sof_df["nr_studies_cleaned"] > parsed_sof_df["nr_participants_cleaned"], "cochrane_id"],
#     parsed_sof_df.loc[parsed_sof_df["nr_studies_cleaned"] > parsed_sof_df["nr_participants_cleaned"], "nr_participants_studies"]
# ))
# [('CD001935.PUB3', '5 (409)'),
#  ('CD001935.PUB3', '2 (231)'),
#  ('CD002207.PUB4', '8 (1027)'),
#  ('CD002207.PUB4', '4 (501)'),
#  ('CD002207.PUB4', '6 (919)'),
#  ('CD002207.PUB4', '6 (859)'),
#  ('CD004203.PUB3', '143  (1610 studies)'),
#  ('CD006258.PUB2', '11 (3396)'),
#  ('CD006258.PUB2', '6 (2889)'),
#  ('CD006258.PUB2', '2 (1688)'),
#  ('CD006258.PUB2', '8 (988)'),
#  ('CD006961.PUB5', '1 (82)'),
#  ('CD008227.PUB4', '1 (83)'),
#  ('CD009453.PUB2', '2 (455)'),
#  ('CD011457.PUB2', '4 (383)'),
#  ('CD011457.PUB2', '3 (333)'),
#  ('CD011457.PUB2', '2 (263)'),
#  ('CD011457.PUB2', '2 (120)'),
#  ('CD011457.PUB2', '3 (313)'),
#  ('CD011457.PUB2', '2 (170)'),
#  ('CD011457.PUB2', '2 (263)'),
#  ('CD012177.PUB2', '30 participants 98 events (cardiac arrests) observed'),
#  ('CD012177.PUB2', '1778 participants 57,193 in the population studied²'),
#  ('CD012177.PUB2', '156 participants 558 in the population studied'),
#  ('CD012177.PUB2', '951 participants 314,055 in the patient population'),
#  ('CD012177.PUB2', '1417 participants 28,676 in the population (patients and staff)²'),
#  ('CD012177.PUB2', '634 participants 179,400 in the patient population'),
#  ('CD013614.PUB2', '1 (20)'),
#  ('CD015790.PUB2', '3 (568)'),
#  ('CD015790.PUB2', '3 (459)'),
#  ('CD015790.PUB2', '4 (733)'),
#  ('CD015790.PUB2', '6 (864)')]
#  Unclear for two reviews, remove: 
parsed_sof_df.loc[\
    (parsed_sof_df["cochrane_id"].isin(["CD004203.PUB3", "CD012177.PUB2"])) & (parsed_sof_df["nr_studies_cleaned"] > parsed_sof_df["nr_participants_cleaned"]),\
    ["nr_participants_cleaned", "nr_studies_cleaned"]] = None
# In the other 9 reviews clearly swapped accidentally by authors => swap to fix
mask = parsed_sof_df["nr_studies_cleaned"] > parsed_sof_df["nr_participants_cleaned"]
temp = parsed_sof_df.loc[mask, "nr_participants_cleaned"].copy()
parsed_sof_df.loc[mask, "nr_participants_cleaned"] = parsed_sof_df.loc[mask, "nr_studies_cleaned"]
parsed_sof_df.loc[mask, "nr_studies_cleaned"] = temp

parsed_sof_df = parsed_sof_df[['cochrane_id', 'table_nr', 'table_title', 'row_nr', 'rowname', 'effect_type', 'point_estimate', 'lower_ci', 'upper_ci', 'nr_participants_cleaned', 'nr_studies_cleaned', 'certainty_cleaned']]
parsed_sof_df.to_csv("results/25-04-01-parsed_sof_df.csv", index=False)

# %%
