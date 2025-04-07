#%%
import re
import numpy as np
import pandas as pd
from io import StringIO
import matplotlib.pyplot as plt

flags = re.IGNORECASE | re.MULTILINE

number = r"(?:no.?|number|№) *(?:of)? *"
participants = r"(?:participants|patients|persons|people|women|men|children|infants|babies|eyes|couples|limbs|teeth|procedures|episodes|intubations|paa|restorations|ulcers)"
studies = r"(?:randomised|randomized|observational|cross-over)?\s*(?:stud|trial|rct):?\s*"

def table_merged_df(table):
    full_table_df = pd.read_html(StringIO(str(table)))[0].fillna('')
    full_table_df = full_table_df.loc[:, ~(full_table_df == '').all()]
    max_columns = full_table_df.shape[1]
    # Old approach: First cell often indicates table width through its colspan attribute (but not always, compare e.g. CD008624.PUB2)
    #int(table.find('td').get('colspan'))
    
    # If table is actually empty, skip (e.g. CD011189.PUB2 SOF3: just one field saying "No included studies")
    if max_columns == 1:
        return False

    table_title = table.find('td').text.strip()
    if table_title and (table_title.startswith("Patient or population") or table_title.startswith("Outcome")):
        table_title = table.find('span', class_='table-title').text.strip()

    # Separate rows in header_rows, main_rows, footer_rows
    rows = table.find_all('tr')
    few_td_rows = [len(row.find_all('td')) <= 2 for row in rows] # some reviews have 2 columns for header (on purpose, e.g. CD000329; not on purpose, e.g. CD002745.PUB3, CD001191.PUB4)len(row.find_all('td'))
    max_colspan_rows = [int(row.find('td').get('colspan')) >= max_columns for row in rows]
    first_main_row = next((i for i, x in enumerate(few_td_rows) if not x), len(few_td_rows)) # next(...) gives index of first falsy value or len
    header_rows = rows[0:first_main_row]
    last_main_row = len(rows) - next((i for i, x in enumerate(max_colspan_rows[::-1]) if not x), len(few_td_rows)) # next(...[::-1]...) gives index of first falsy from the bottom value or len
    main_rows = rows[first_main_row:last_main_row]
    footer_rows = rows[last_main_row:]

    # Select outcome rows and their headers
    #rows = list(filter(lambda row: len(row.find_all('td')) == max_columns, rows))
    #n_cells = [len(row.find_all('td')) for row in rows]
    # colspan >= 5 is usually a missing / header row
    #main_rows = list(filter(lambda row: int(row.find('td').get('colspan')) < 5, main_rows)) # only considers first td
    #main_rows = list(filter(lambda row: max([int(x.get("colspan")) for x in row.find_all('td')]) < 5, main_rows))
    main_rows = list(filter(lambda row: int(row.find('td').get('colspan')) < max_columns, main_rows)) # Removes intermediate header-rows with colspan == max_columns

    if not len(main_rows):
        return False
    
    table_df = pd.read_html(StringIO(f'<table>{main_rows}</table>'))[0].fillna('')

    # Remove completely empty columns (incl. empty column name, e.g. CD006208.PUB3)
    table_df = table_df.loc[:, ~(table_df == '').all()]
    table_df.columns = range(table_df.shape[1]) # CD004250.PUB5: 1st column completely empty
    
    # If "Outcomes" is stretched over 2 columns: merge them with \n (e.g. CD003316.PUB7)
    # If 1st column is "Outcomes" and 2nd column is "Comparison": merge them with \n (e.g. CD000528.PUB2)
    if  (str(table_df.loc[0,0]).startswith('Outcome') and str(table_df.loc[0,1]).startswith('Outcome')): #or\
        #((table_df.loc[0,0].startswith('Outcome')) and (('Comparison' in table_df.loc[0,1]) or 'comparison' in table_df.loc[0,1])):
        rows_diff = table_df.loc[:,0] != table_df.loc[:,1]
        table_df.loc[rows_diff, 0] = table_df.loc[rows_diff, 0] + '\n' + table_df.loc[rows_diff, 1]
        # Remove second outcome column
        table_df = table_df.drop(table_df.columns[1], axis=1)
    
    if  (re.search(r'^Outcome|Intervention|Treatment', str(table_df.iloc[0,0]), re.IGNORECASE) and re.search(r"Comparison|Primary outcome measure", str(table_df.iloc[0,1]), re.IGNORECASE)):
        rows_diff = table_df.loc[:,0] != table_df.loc[:,1]
        table_df.loc[rows_diff, 0] = table_df.loc[rows_diff, 0] + '\n' + table_df.loc[rows_diff, 1]
        # Remove second outcome column
        table_df = table_df.drop(table_df.columns[1], axis=1)
        # IDs with "Comparison" / "comparison" in 2nd column: ['CD000425.PUB4' 'CD000528.PUB2' 'CD001168.PUB3' 'CD004063.PUB4', 'CD005468.PUB2' 'CD006208.PUB3' 'CD006745.PUB3' 'CD007039.PUB3', 'CD007825.PUB6' 'CD008117.PUB2' 'CD008326.PUB2' 'CD008797.PUB2', 'CD010036.PUB2' 'CD010293.PUB2' 'CD010393.PUB2' 'CD011034.PUB2', 'CD011376.PUB3' 'CD012421']
        # print(f"Merged 1st and 2nd columns: {id}")

    # Merge header rows with \n (if row is empty [e.g. CD001800.PUB3 and CD006353.PUB4] or the same as upper_left_cell, the last row is empty [e.g. CD010483.PUB4])
    rows = table_df.values.tolist()
    new_rows = [rows[0]]
    upper_left_cell = new_rows[0][0]
    for i in range(1, len(rows)):
        current_row = pd.Series(rows[i])
        prev_row = pd.Series(new_rows[-1])
        cols_diff = current_row != prev_row
        #if current_row[0] == '' or not cols_diff[0]:
        if current_row[0] == '' or current_row[0] == upper_left_cell or prev_row[0] == '':
            prev_row[cols_diff] = prev_row[cols_diff].astype(str) + '\n' + current_row[cols_diff].astype(str)
            new_rows[-1] = prev_row.to_list()
        else:
            new_rows += rows[i:]
            break

    merged_df = pd.DataFrame(new_rows[1:], columns=new_rows[0])

    # Must have at least one row (i.e. outcome)
    if not merged_df.shape[0]:
        return False

    # Drop completely duplicated columns (i.e. both content and column-names) columns (pretty hardcoded for CD006185.PUB5: control column duplicated)
    merged_df = merged_df.loc[:, ~(merged_df.T.duplicated() & merged_df.columns.duplicated())]

    # Add '2' to duplicated column names (important for e.g. CD009081.PUB2)
    while merged_df.columns.duplicated().any():
        merged_df.columns = merged_df.columns.where(~merged_df.columns.duplicated(), merged_df.columns + ' 2')

    return (table_title, header_rows, footer_rows, table_df, merged_df)

def get_columns(merged_df):
    columns = merged_df.columns
    get_column = lambda contains, flags=flags: columns[columns.astype(str).str.contains(contains, flags=flags)][0] if columns.astype(str).str.contains(contains, flags=flags).any() else 'NA'

    rownames_col = columns[0]
    relative_effects_col = get_column(r'^Relative +|^Risk +ratio|^Odds +ratio|^Hazard +ratio|^RR +\(95%|^OR +\(95%| RR +\(95%| OR +\(95%')
    if relative_effects_col == 'NA':
        relative_effects_col = get_column(r'^RR\b.*\(95%|^OR\b.*\(95%', re.MULTILINE)
    
    #nr_participants_studies_col = get_column('No.? +of +participants|Number +of +participants|№ +of +participants|No.? +of +patients|Number +of +patients|№ +of +patients|Participants.*\s*stud')
    nr_participants_studies_col_str = rf'{number}{participants}'
    nr_participants_studies_col = get_column(nr_participants_studies_col_str)
    if nr_participants_studies_col == 'NA':
        nr_participants_studies_col_str += rf'|{participants}.*\s*{studies}|{number}{studies}'
        nr_participants_studies_col = get_column(nr_participants_studies_col_str)
    # In >40 reviews (e.g. CD003376.PUB4), "No of participants (studies)" is in Outcomes column without the header acknowledging it (less often it's acknowledged: ['CD009596.PUB4', 'CD011991.PUB2', 'CD011992.PUB2', 'CD011993.PUB2','CD011994.PUB2', 'CD011995.PUB2', 'CD011996.PUB2', 'CD012023.PUB2','CD013307.PUB3', 'CD013799.PUB2', 'CD015087.PUB2'])
    if nr_participants_studies_col == 'NA':
        nr_participants_studies_col_str += rf"|\d+ +{participants}"
        if merged_df[rownames_col].astype(str).str.contains(nr_participants_studies_col_str, flags=flags).any():
            nr_participants_studies_col = rownames_col
    
    certainty_col = get_column(r'^Certainty.*\s*GRADE|^Quality.*\s*GRADE') # Should contain both "Certainty|Quality" AND "GRADE", otherwise less specific (compare e.g. CD009273.PUB2)
    if certainty_col == 'NA':
        certainty_col = get_column(r'^Certainty|^Quality|^Overall certainty|^Overall quality|GRADE')
    
    return rownames_col, relative_effects_col, nr_participants_studies_col, certainty_col

def extract_relative_effects_numbers_quality(combined_sof_df):
    # Extract certainty_cleaned
    grade = ["verylw", "low", "moderate", "high"]
    def match_grade(x):
        x= str(x).lower().replace("verylow", "very low") # CD008649.PUB4
        x= str(x).lower().replace("m oderate", "moderate") # CD007880.PUB3
        x= str(x).lower().replace("l ow", "low") # CD004711.PUB3
        x= str(x).lower().replace("very low", "verylw") # to differentiate very low and low
        matches = [g for g in grade if g in x]
        if len(matches) >= 1:
            if matches[0] == "verylw":
                matches[0] = "very low"
            return ",".join(matches)
        else:
            return "NA"
    combined_sof_df["certainty_cleaned"] = combined_sof_df["certainty"].apply(match_grade)

    combined_sof_df["certainty_cleaned"] = pd.Categorical(
        combined_sof_df["certainty_cleaned"], 
        categories=["very low", "low", "moderate", "high"],
        ordered=True
    )

    # Remove thousands separators , and ' (don't remove thousands searator space " ", because otherwise e.g. in CD008649.PUB4, "22 1 study" will be converted to "221 study")
    # and convert written numbers 1-9 to digits
    # and remove superscript numbers (e.g. CD008649.PUB4)
    nr_participants_studies_processed = combined_sof_df["nr_participants_studies"].\
        str.replace(r"\b(\d+),(\d+)\b", r'\1\2', regex=True, flags=flags).str.replace(r"\b(\d+)'(\d+)\b", r'\1\2', regex=True, flags=flags).\
        str.replace(r'\bone\b', '1', regex=True, flags=flags).str.replace(r'\btwo\b', '2', regex=True, flags=flags).str.replace(r'\bthree\b', '3', regex=True, flags=flags).str.replace(r'\bfour\b', '4', regex=True, flags=flags).str.replace(r'\bfive\b', '5', regex=True, flags=flags).str.replace(r'\bsix\b', '6', regex=True, flags=flags).str.replace(r'\bseven\b', '7', regex=True, flags=flags).str.replace(r'\beight\b', '8', regex=True, flags=flags).str.replace(r'\bnine\b', '9', regex=True, flags=flags).\
        str.replace(r'[⁰¹²³⁴⁵⁶⁷⁸⁹]*', '', regex=True, flags=flags).\
        str.replace(r'N\s*=\s*', '', regex=True, flags=flags)
    nr_participants_studies_all_numbers = nr_participants_studies_processed.str.extractall(r'(\d+)', re.MULTILINE)
    combined_sof_df["nr_participants_studies_col_nr_of_nr"] = nr_participants_studies_all_numbers.groupby(level=0).size().reindex(combined_sof_df.index, fill_value=0)
    
    # Most specific extraction
    combined_sof_df.loc[\
        (combined_sof_df["nr_participants_studies_col_nr_of_nr"] >= 2) & \
        combined_sof_df["nr_participants_studies_col"].str.contains(rf"{participants}.+\s*.*{studies}", flags=flags), \
        ["nr_participants_cleaned", "nr_studies_cleaned"]] = \
        nr_participants_studies_processed.str.extract(r'^(\d+)\b[\s([,:]+\b(\d+)', flags=flags).astype(float).rename({0: "nr_participants_cleaned", 1: "nr_studies_cleaned"}, axis=1)
    combined_sof_df.loc[\
        (combined_sof_df["nr_participants_studies_col_nr_of_nr"] >= 2) & \
        combined_sof_df["nr_participants_studies_col"].str.contains(rf"{studies}.+\s*.*{participants}", flags=flags), \
        ["nr_studies_cleaned", "nr_participants_cleaned"]] = \
        nr_participants_studies_processed.str.extract(r'^(\d+)\b[\s([,:]+\b(\d+)', flags=flags).astype(float).rename({0: "nr_studies_cleaned", 1: "nr_participants_cleaned"}, axis=1)

    # combined_sof_df.loc[\
    #     #combined_sof_df["nr_participants_cleaned"].isna() & \
    #     (combined_sof_df["nr_participants_studies_col_nr_of_nr"] >= 2) & \
    #     combined_sof_df["nr_participants_studies_col"].str.contains(rf"{participants}.+\s*.*{studies}", flags=flags), \
    #     ["nr_participants_cleaned", "nr_studies_cleaned"]] = \
    #     nr_participants_studies_processed.str.extract(r'(\d+)\b.*\b(\d+)', flags=flags).astype(float).rename({0: "nr_participants_cleaned", 1: "nr_studies_cleaned"}, axis=1)
    # combined_sof_df.loc[\
    #     #combined_sof_df["nr_participants_cleaned"].isna() & \
    #     (combined_sof_df["nr_participants_studies_col_nr_of_nr"] >= 2) & \
    #     combined_sof_df["nr_participants_studies_col"].str.contains(rf"{studies}.+\s*.*{participants}", flags=flags), \
    #     ["nr_studies_cleaned", "nr_participants_cleaned"]] = \
    #     nr_participants_studies_processed.str.extract(r'(\d+)\b.*\b(\d+)', flags=flags).astype(float).rename({0: "nr_studies_cleaned", 1: "nr_participants_cleaned"}, axis=1)
    
    combined_sof_df.loc[\
        combined_sof_df["nr_participants_cleaned"].isna() & \
        combined_sof_df["nr_participants_studies_col"].str.contains(rf"^(?:{number})?{participants}", flags=flags), \
        "nr_participants_cleaned"] = \
        nr_participants_studies_processed.str.extract(r'^(\d+)', flags=flags, expand=False).astype(float)
    combined_sof_df.loc[\
        combined_sof_df["nr_studies_cleaned"].isna() & \
        combined_sof_df["nr_participants_studies_col"].str.contains(rf"^(?:{number})?{studies}", flags=flags), \
        "nr_studies_cleaned"] = \
        nr_participants_studies_processed.str.extract(r'^(\d+)', flags=flags, expand=False).astype(float)
    
    combined_sof_df.loc[\
        combined_sof_df["nr_participants_cleaned"].isna() & \
        combined_sof_df["nr_participants_studies"].str.contains(rf"{number}{participants}(\d+)", flags=flags), \
        "nr_participants_cleaned"] = \
        nr_participants_studies_processed.str.extract(rf'{number}{participants}(\d+)', flags=flags, expand=False).astype(float)
    # Still specific extraction
    # extraction = nr_participants_studies_processed[\
    #     combined_sof_df[["nr_participants_cleaned", "nr_studies_cleaned"]].isna().all(axis=1)].\
    #     str.extract(rf'(\d+)\s*{participants}[\s,(\[]+(\d+)\s*{studies}', flags=flags)
    
    # combined_sof_df.loc[\
    #     combined_sof_df["nr_participants_studies_col"].str.contains(rf"^{participants}") & \
    #     extraction.notna().all(axis=1), \
    #     ['nr_participants_cleaned', 'nr_studies_cleaned']] = \
    #     extraction[extraction.notna().all(axis=1)].astype(float).to_numpy()
    # #combined_sof_df.loc[extraction.notna().all(axis=1), "nr_participants_studies_col_nr_found"] = 2
    # Less specific extraction
    combined_sof_df["nr_participants_cleaned"] = combined_sof_df["nr_participants_cleaned"].fillna(nr_participants_studies_processed.str.extract(rf'(\d+)\s?{participants}', flags=flags).astype(float).squeeze())
    combined_sof_df["nr_studies_cleaned"] = combined_sof_df["nr_studies_cleaned"].fillna(nr_participants_studies_processed.str.extract(rf'(\d+)\s?{studies}', flags=flags).astype(float).squeeze())

    #combined_sof_df.loc[combined_sof_df["nr_participants_studies_col_nr_found"].isna(), "nr_participants_studies_col_nr_found"] = combined_sof_df[["nr_participants_cleaned", "nr_studies_cleaned"]].notna().sum(axis=1)
    # If one is 0, so is the other
    combined_sof_df.loc[(combined_sof_df["nr_studies_cleaned"] == 0) & combined_sof_df["nr_participants_cleaned"].isna(), "nr_participants_cleaned"] = 0
    combined_sof_df.loc[(combined_sof_df["nr_participants_cleaned"] == 0) & combined_sof_df["nr_studies_cleaned"].isna(), "nr_studies_cleaned"] = 0
    
    #combined_sof_df[["nr_participants_cleaned", "nr_studies_cleaned"]]=np.nan
    #combined_sof_df[["nr_participants_cleaned", "nr_studies_cleaned"]].sum()
    #combined_sof_df[["nr_participants_studies_col", "nr_participants_studies", "nr_participants_studies_col_nr_of_nr", "nr_participants_cleaned", "nr_studies_cleaned"]]
    #combined_sof_df.loc[combined_sof_df[["nr_participants_cleaned", "nr_studies_cleaned"]].isna().any(axis=1) & (combined_sof_df["nr_participants_studies_col_nr_of_nr"]>0), ["cochrane_id", "nr_participants_studies_col", "nr_participants_studies", "nr_participants_studies_col_nr_of_nr", "nr_participants_cleaned", "nr_studies_cleaned"]]
    #combined_sof_df.loc[(combined_sof_df["nr_participants_studies_col_nr_of_nr"]>0), ["cochrane_id", "nr_participants_studies_col", "nr_participants_studies", "nr_participants_studies_col_nr_of_nr", "nr_participants_cleaned", "nr_studies_cleaned"]]
    

    # Relative effects
    effect_type_cleaned = {
        #"incidence rate ratio": "IRR", # subsumed under RR
        "hazard ratio": "HR",
        "odds ratio": "OR",
        "relative risk": "RR", # doesn't seem to occur
        "risk ratio": "RR",
        "rate ratio": "RR",
    }
    #effect_type = r"Rate ratio|Risk ratio|RR|Adjusted RR|Reported adjusted RR|aRR|Odds Ratio|OR|Adjusted OR|Reported adjusted OR|aOR|Peto OR|POR|Hazard ratio|HR|Adjusted HR|aHR|Incidence rate ratio|IRR|Adjusted IRR|aIRR"
    #re_str = rf"({effect_type}):?\s*\[?(\d+\.?\d*)\]?\s*\((?:95% ?CI )?\[?(\d+\.?\d*)\]?(?:\s*to\s*)?(?:,\s*)?\[?(\d+\.?\d*)\]?\)"
    effect_type_full_re_str = rf"{'|'.join(effect_type_cleaned.keys())}"
    effect_type_acronym_re_str = rf"{'|'.join(effect_type_cleaned.values())}" # acronyms should be case sensitive because of lower case "or" in many columns
    effect_type_re_str = rf"({effect_type_full_re_str}|{effect_type_acronym_re_str})"
    point_estimate_and_ci_re_str = r"\[?(\d+\.?\d*)\]?\s*\((?:95% ?CI )?\[?(\d+\.?\d*)\]?(?:\s*to\s*)?(?:,\s*)?\[?(\d+\.?\d*)\]?"
    
    # effect_type is in each cell
    re_str = rf"{effect_type_re_str}:?\s*{point_estimate_and_ci_re_str}"

    combined_sof_df.loc[ \
        combined_sof_df["relative_effects"].astype(str).str.contains(re_str, flags=flags), \
        ["effect_type", "point_estimate", "lower_ci", "upper_ci"]] = \
        combined_sof_df["relative_effects"].astype(str).str.extract(re_str, flags=flags).rename({0: "effect_type", 1: "point_estimate", 2: "lower_ci", 3: "upper_ci"}, axis=1)
    
    # effect_type is in header only
    combined_sof_df.loc[ \
        ~combined_sof_df["relative_effects"].astype(str).str.contains(re_str, flags=flags) & \
        combined_sof_df["relative_effects"].astype(str).str.contains(point_estimate_and_ci_re_str, flags=flags) & \
        (combined_sof_df["relative_effects_col"].astype(str).str.contains(rf"{effect_type_full_re_str}", flags=flags) | \
        combined_sof_df["relative_effects_col"].astype(str).str.contains(rf"{effect_type_acronym_re_str}", flags=re.MULTILINE)), \
        ["point_estimate", "lower_ci", "upper_ci"]] = \
        combined_sof_df["relative_effects"].str.extract(point_estimate_and_ci_re_str, flags=flags).rename({0: "point_estimate", 1: "lower_ci", 2: "upper_ci"}, axis=1)
    combined_sof_df.loc[ \
        ~combined_sof_df["relative_effects"].astype(str).str.contains(re_str, flags=flags) & \
        combined_sof_df["relative_effects"].astype(str).str.contains(point_estimate_and_ci_re_str, flags=flags) & \
        combined_sof_df["relative_effects_col"].astype(str).str.contains(rf"{effect_type_full_re_str}", flags=flags), \
        "effect_type"] = \
        combined_sof_df["relative_effects_col"].astype(str).str.extract(f"({effect_type_full_re_str})", flags=flags).rename({0: "effect_type"}, axis=1)
    combined_sof_df.loc[ \
        ~combined_sof_df["relative_effects"].astype(str).str.contains(re_str, flags=flags) & \
        combined_sof_df["relative_effects"].astype(str).str.contains(point_estimate_and_ci_re_str, flags=flags) & \
        ~combined_sof_df["relative_effects_col"].astype(str).str.contains(rf"{effect_type_full_re_str}", flags=flags) & \
        combined_sof_df["relative_effects_col"].astype(str).str.contains(rf"{effect_type_acronym_re_str}", flags=re.MULTILINE), \
        "effect_type"] = \
        combined_sof_df["relative_effects_col"].astype(str).str.extract(rf"({effect_type_acronym_re_str})", flags=re.MULTILINE).rename({0: "effect_type"}, axis=1)

    # Convert to float
    combined_sof_df[["point_estimate", "lower_ci", "upper_ci"]] = combined_sof_df[["point_estimate", "lower_ci", "upper_ci"]].astype(float)

    # Use only acronyms for effect_type
    combined_sof_df["effect_type"] = combined_sof_df["effect_type"].str.lower()
    combined_sof_df.loc[combined_sof_df["effect_type"].isin(effect_type_cleaned.keys()), "effect_type"] = \
        combined_sof_df.loc[combined_sof_df["effect_type"].isin(effect_type_cleaned.keys()), "effect_type"].map(effect_type_cleaned)
    combined_sof_df["effect_type"] = combined_sof_df["effect_type"].str.upper()


    combined_sof_df["has_relative_effect"] = combined_sof_df["effect_type"].notna()
    # Consistency check
    #(combined_sof_df.loc[~combined_sof_df["effect_type"].isna(), "lower_ci"] <= combined_sof_df.loc[~combined_sof_df["effect_type"].isna(), "upper_ci"]).value_counts(dropna=False)
    combined_sof_df["mortality_outcome"] = combined_sof_df["rowname"].astype(str).str.contains("mortality|death")
    combined_sof_df["significant"] = (combined_sof_df[["point_estimate", "lower_ci"]]>1).all(axis=1) | (combined_sof_df[["point_estimate", "lower_ci"]]<1).all(axis=1)
    combined_sof_df["very_large_effect"] = (combined_sof_df["point_estimate"] >= 5) | (combined_sof_df["point_estimate"] <= 0.2)

    combined_sof_df["primary_outcome"] = False
    combined_sof_df.loc[(combined_sof_df["table_nr"] == 1) & (combined_sof_df["row_nr"] == 1), "primary_outcome"] = True

    return combined_sof_df
# %%
def create_box_pie_plot(combined_sof_df):
    # Create box-plot
    fig, ax = plt.subplots(figsize=(5, 5))
    certainty_levels = ["very low", "low", "moderate", "high"]
    data = [combined_sof_df.loc[combined_sof_df["certainty_cleaned"] == level, "nr_participants_cleaned"].dropna() for level in certainty_levels]
    data_studies = [combined_sof_df.loc[combined_sof_df["certainty_cleaned"] == level, "nr_studies_cleaned"].dropna() for level in certainty_levels]

    ax.set_ylabel('Number of participants', color='black')
    #ax.set_yscale('symlog')
    #ax.set_ylim(10, 100000)
    ax.set_ylim(0, 10000)

    boxplot = ax.boxplot(
        data,
        positions=np.arange(len(certainty_levels)) * 2.0,  # Shift positions for the first set of boxplots
        labels=certainty_levels,
        showfliers=False,
        meanline=True,
        showmeans=True,
        patch_artist=True,
        boxprops=dict(facecolor="white", color="black"),
        medianprops=dict(color="black"),
        meanprops=dict(color="black", linestyle="--")
    )

    # Create a second y-axis for the studies boxplot
    ax2 = ax.twinx()
    ax2.set_ylabel('Number of studies', color='#206fb2', rotation=270, labelpad=10)
    ax2.set_ylim(0, 20)  # Set the range for the second y-axis
    #ax2.set_yscale('symlog')
    #ax2.set_ylim(1, 50)
    ax2.yaxis.set_major_locator(plt.MaxNLocator(integer=True))  # Ensure only whole ticks
    ax2.tick_params(axis='y', colors='#206fb2')  # Set tick color to #206fb2
    ax2.spines['right'].set_color('#206fb2')  # Set the right spine color to #206fb2

    boxplot_studies = ax2.boxplot(
        data_studies,
        positions=np.arange(len(certainty_levels)) * 2.0 + 0.8,  # Shift positions for the second set of boxplots
        showfliers=False,
        meanline=True,
        showmeans=True,
        patch_artist=True,
        boxprops=dict(facecolor="white", color="#206fb2"),
        medianprops=dict(color="#206fb2"),
        whiskerprops=dict(color="#206fb2"),
        capprops=dict(color="#206fb2"),
        meanprops=dict(color="#206fb2", linestyle="--")
    )

    ax.text(
        -0.5,  # x-coordinate (boxplot positions are 1-indexed)
        -700,  # y-coordinate (below the x-axis)
        'P75:\nMedian:\nP25:',
        ha='right', va='top', fontsize=10, color='black'
    )

    # Add median values below x-labels for participants
    for i, line in enumerate(boxplot['medians']):
        median_value = line.get_ydata()[0]
        p25 = boxplot['whiskers'][i*2].get_ydata()[0]
        p75 = boxplot['whiskers'][i*2+1].get_ydata()[0]
        ax.text(
            i * 2.0 + 0.5,  # x-coordinate (boxplot positions are 1-indexed)
            -700,  # y-coordinate (below the x-axis)
            f'{p75:.0f}\n{median_value:.0f}\n{p25:.0f}',
            ha='right', va='top', fontsize=10, color='black'
        )

    # # Add median values below x-labels for studies
    for i, line in enumerate(boxplot_studies['medians']):
        median_value = line.get_ydata()[0]
        p25 = boxplot_studies['whiskers'][i*2].get_ydata()[0]
        p75 = boxplot_studies['whiskers'][i*2+1].get_ydata()[0]
        ax.text(
            i * 2.0 + 0.7,  # x-coordinate (boxplot positions are 1-indexed)
            -700,  # y-coordinate (below the x-axis)
            f'{p75:.0f}\n{median_value:.0f}\n{p25:.0f}',
            ha='left', va='top', fontsize=10, color='#206fb2'
        )


    ax.set_xticks(np.arange(len(certainty_levels)) * 2.0 + 0.4)
    ax.set_xticklabels(certainty_levels)
    ax.set_xlabel('')
    ax.set_title('')
    fig.suptitle('')

    # Add pie chart as inset
    plot_df = pd.DataFrame(combined_sof_df["certainty_cleaned"].value_counts(sort=False)).reset_index()

    pie_ax_pos = [0.27, 0.53, 0.3, 0.3]  # [left, bottom, width, height]
    inset_ax = fig.add_axes(pie_ax_pos)
    # Copy pie chart data to inset
    colors = ['#a8cee5', '#74b2d7', '#4592c6', '#206fb2']  # Light to dark blue gradient
    wedges, texts, autotexts = inset_ax.pie(plot_df['count'][::-1], labels=plot_df['certainty_cleaned'][::-1], 
                                           colors=colors[::-1], autopct='%.0f%%', startangle=90, pctdistance=0.75)
    inset_ax.axis('equal')
    return fig, ax, ax2, inset_ax
# %%
