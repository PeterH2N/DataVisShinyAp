import pandas as pd
from census import Census
import os
c = Census("a54a198ac29e952c264e29856c0ae19bbc3b44aa")

df_cd = {}

def get_census_data():
    path = "res/census_data.csv"
    if os.path.exists(path):
        df_cd = pd.read_csv(path)
    else:
        frames = []
        for yr in range(2009, 2022):
            #url = f"https://api.census.gov/data/{yr}/acs/acs5"
            data = c.acs5.get(('NAME','B19013_001E','B01003_001E'),
                              {'for':'county subdivision:*','in':'state:09'},
                              year=yr)
            df = pd.DataFrame(data)
            df['Year'] = yr
            frames.append(df)
        df_cd = pd.concat(frames, ignore_index=True)
        df_cd["Town"] = df_cd["NAME"].str.replace(r"\s+town.*$", "", regex=True)
        df_cd["Median Household Income"] = df_cd["B19013_001E"]
        df_cd["Population"] = df_cd["B01003_001E"]
        
        df_cd.to_csv("res/census_data.csv", index=False)

get_census_data()


local_file = "res/estate_data.csv"

df = pd.read_csv(local_file, dtype={
    'Residential Type': 'string',
    'Property Type': 'string',
    'Non Use Code': 'string',
    'Assessor Remarks': 'string',
    'OPM remarks': 'string',
    'Location': 'string'
}, parse_dates=["Date Recorded"])

df["Sale Year"] = df["Date Recorded"].dt.year
df = df.query("`Residential Type`.notna()")

def change_in_price_by_town_by_year():
    filtered = df.query("Town.notna()")
    average_by_year = (filtered.groupby(["Town", "Sale Year"], as_index=False)["Sale Amount"].mean()).copy()
    average_by_year["Percentage Change"] = average_by_year.groupby("Town")["Sale Amount"].pct_change() * 100
    return average_by_year.query("`Town`.notna() and `Percentage Change`.notna()").copy()



def average_price_by_town_by_year():
    filtered = df.query("Town.notna()")

    
    average_by_year = filtered.groupby(["Town", "Sale Year"], as_index=False)["Sale Amount"].mean()
    average_by_year["Residential Type"] = "All"
    average_by_year_and_town = (
        filtered
        .groupby(["Town", "Residential Type", "Sale Year"], as_index=False)["Sale Amount"]
        .mean()
        .sort_values(by=['Town', 'Sale Year'], ascending=[True, True]))
    
    # Add census data
    average_by_year = average_by_year.merge(
        df_cd[["Town", "Year", "Population", "Median Household Income"]],    
        left_on=["Town", "Sale Year"],    
        right_on=["Town", "Year"],
        how="left"
    )
    return pd.concat([average_by_year_and_town, average_by_year], ignore_index=True)