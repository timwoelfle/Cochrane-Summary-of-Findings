#%%
import requests
import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup
import pickle

# Read all Cochrane review ids
id_version_list = pd.read_csv("data/25-04-01-citation-export-interventions-no-abstract.csv")["Cochrane Review ID"]
#id_version_list = id_version_list.str.replace('PUB', 'pub')

def retrieve_summary_of_findings_table(id, print_version_warning=False):
    # URL of the Cochrane review
    url = "https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858." + id + "/full"

    # Set headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    # Fetch the page content
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        page_content = response.content

        # Parse the page content using BeautifulSoup
        soup = BeautifulSoup(page_content, 'html.parser')

        # Check whether the page was locked
        unlock_full_review = soup.find('a', {'text': 'Unlock the full review'})
        if unlock_full_review:
            print(f"Lock Warning: This review is locked. ID: {id}")

        if print_version_warning:
            version_warning = soup.find('p', {'class': 'version-warning'})
            if version_warning:
                print(f"Verion Warning: This review was retracted or is not the most recent version. ID: {id}")

        # Find the "Summary of findings" table(s) (without the section-parent, tables would be duplicated because of "Figures and Tables" section at the bottom of the page)
        summary_table = soup.select('section.summaryOfFindings table.summary-of-findings')

        if summary_table:
            # Convert to string to reduce memory
            return str(summary_table)
        else:
            #print(f"Summary of findings table not found. ID: {id}")
            return None
    else:
        print(f"Failed to retrieve the page. ID: {id}. Status code: {response.status_code}")
        return None

with open("data/25-01-19-sof-tables-all.pickle", "rb") as file:
    sof_tables = pickle.load(file)

missing_id_version = id_version_list[~id_version_list.isin(list(sof_tables.keys()))].to_list()


#%%
for id_version in tqdm(missing_id_version):
    id = id_version.split(".")[0]
    if len(id_version.split(".")) > 1:
        last_version = int(id_version[-1])
    else:
        last_version = 1
    for version in range(last_version, 0, -1):
        id_version = id
        if version > 1:
            id_version += f".PUB{version}"
        if not id_version in sof_tables.keys():
            sof_tables[id_version] = retrieve_summary_of_findings_table(id_version, print_version_warning=version==last_version)

with open('data/25-04-01-sof-tables-interventions.pickle', 'wb') as file:
    pickle.dump(sof_tables, file)

# Convert sof_tables to a pandas DataFrame and save as CSV
sof_tables_df = pd.DataFrame.from_dict(sof_tables, orient='index', columns=['sof'])
sof_tables_df = sof_tables_df.sort_index()
sof_tables_df.to_csv('data/25-04-01-sof-tables-interventions.csv', index=True)
