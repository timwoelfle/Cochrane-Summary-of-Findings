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

combined_sof_df.to_csv('results/25-04-01-combined_sof_df.csv', index=False)
# %%
combined_sof_df = pd.read_csv("results/25-04-01-combined_sof_df.csv")

parsed_sof_df = extract_relative_effects_numbers_quality(combined_sof_df)
parsed_sof_df = parsed_sof_df[['cochrane_id', 'table_nr', 'table_title', 'row_nr', 'rowname', 'certainty_cleaned', 'nr_participants_studies_col_nr_of_nr', 'nr_participants_cleaned', 'nr_studies_cleaned', 'effect_type', 'point_estimate', 'lower_ci', 'upper_ci', 'has_relative_effect', 'mortality_outcome', 'significant', 'very_large_effect', 'primary_outcome']]
parsed_sof_df.to_csv("results/25-04-01-parsed_sof_df.csv", index=False)

# %%
