import pandas as pd

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


def average_price_by_town_by_year():
    return df.groupby(["Town", "Sale Year"], as_index=False)["Sale Amount"].mean().sort_values(by=['Town', 'Sale Year'], ascending=[True, True])

print(average_price_by_town_by_year())