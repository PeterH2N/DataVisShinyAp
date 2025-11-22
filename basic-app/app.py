from shiny import App, ui, reactive, render
from shinywidgets import render_widget, output_widget
import plotly.express as px
import pandas as pd
import requests

# Download Connecticut counties GeoJSON
geojson_url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
geojson_data = requests.get(geojson_url).json()

# Example dataset for CT counties
ct_data = pd.DataFrame({
    "county": [
        "Fairfield", "Hartford", "Litchfield", "Middlesex",
        "New Haven", "New London", "Tolland", "Windham"
    ],
    "value": [80, 65, 50, 55, 70, 60, 45, 40]
})

# Map county names to FIPS codes for CT
fips_map = {
    "Fairfield": "09001",
    "Hartford": "09003",
    "Litchfield": "09005",
    "Middlesex": "09007",
    "New Haven": "09009",
    "New London": "09011",
    "Tolland": "09013",
    "Windham": "09015"
}
ct_data["fips"] = ct_data["county"].map(fips_map)

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select(
            "palette",
            "Color scale",
            choices=["Viridis", "Plasma", "Cividis", "Turbo", "IceFire"],
            selected="Viridis",
        ),
        ui.input_slider("min", "Lower bound filter", min=0, max=100, value=0),
        ui.input_slider("max", "Upper bound filter", min=0, max=100, value=100),
    ),
    ui.h3("Connecticut Counties Choropleth"),
    output_widget("ct_map"),
    ui.hr(),
    ui.output_table("data_preview")
)

def server(input, output, session):
    @reactive.calc
    def filtered_df():
        lo, hi = input.min(), input.max()
        return ct_data[(ct_data["value"] >= lo) & (ct_data["value"] <= hi)]

    @output
    @render_widget
    def ct_map():
        df = filtered_df()
        fig = px.choropleth(
            df,
            geojson=geojson_data,
            locations="fips",
            color="value",
            color_continuous_scale=input.palette(),
            scope="usa",
            labels={"value": "Metric"},
        )
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        return fig

    @output
    @render.table
    def data_preview():
        return filtered_df()

app = App(app_ui, server)