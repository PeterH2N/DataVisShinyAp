
import plotly.express as px
import pandas as pd
import requests
import numpy as np
from shiny import App, ui
from shinywidgets import output_widget, render_plotly
from estate_data import average_price_by_town_by_year

# Download official GeoJSON
geojson_url = "https://geodata.ct.gov/api/download/v1/items/654fdaadd0dd4b53babb0fa37f4c0b75/geojson?layers=0"
geojson = requests.get(geojson_url).json()

# Extract municipality names
municipalities = [feature["properties"]["Municipality"] for feature in geojson["features"]]

# Create DataFrame with random values
df = average_price_by_town_by_year()
filtered_df = df.query("`Sale Year` == 2015")

# Create Plotly choropleth map
fig = px.choropleth_mapbox(
    filtered_df,
    geojson=geojson,
    locations="Town",
    featureidkey="properties.Municipality",
    color="Sale Amount",
    color_continuous_scale="Viridis",
    mapbox_style="carto-positron",  # No token needed
    center={"lat": 41.6, "lon": -72.7},
    zoom=7,
    title="Connecticut Municipalities",
    labels={"Sale Amount": "Average sale price"},
    hover_name="Town", 
    hover_data={"Sale Amount": True, "Town": False}
)

# Shiny UI using shinywidgets
app_ui = ui.page_fluid(
    ui.h2("Connecticut Municipalities Map"),
    output_widget("map")
)

# Shiny server using render_plotly
def server(input, output, session):
    @output
    @render_plotly
    def map():
        return fig

app = App(app_ui, server)
