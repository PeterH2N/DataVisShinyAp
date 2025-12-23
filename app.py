
import plotly.express as px
import plotly.graph_objects as go
import requests
import pandas as pd
from shiny import App, ui, reactive, render
from shinywidgets import output_widget, render_plotly
from estate_data import average_price_by_town_by_year

# Download official GeoJSON
geojson_url = "https://geodata.ct.gov/api/download/v1/items/654fdaadd0dd4b53babb0fa37f4c0b75/geojson?layers=0"
geojson = requests.get(geojson_url).json()

# Extract municipality names
municipalities = [feature["properties"]["Municipality"] for feature in geojson["features"]]

# Create DataFrame with random values
df = average_price_by_town_by_year()


# Create Plotly choropleth map
def make_fig(year, residential_type): 

    filtered_df = df.query(f"`Sale Year` == {year} and `Residential Type` == '{residential_type}'")
    #filtered_df["clipped_price"] = df["Sale Amount"].clip(lower=df["Sale Amount"].quantile(.1), upper=df["Sale Amount"].quantile(.95))

    return px.choropleth_mapbox(
    filtered_df,
    geojson=geojson,
    locations="Town",
    featureidkey="properties.Municipality",
    color="Sale Amount",
    color_continuous_scale=px.colors.sequential.Oranges,
    mapbox_style="carto-positron",  # No token needed
    center={"lat": 41.6, "lon": -72.7},
    zoom=7,
    title="Connecticut Municipalities",
    labels={"Sale Amount": "Average price"},
    hover_name="Town", 
    hover_data={"Sale Amount": True, "Town": False},
    range_color=(100000, 1500000),
    custom_data=["Town", "Sale Amount"]
    ).update_traces(hovertemplate="<b>%{customdata[0]}</b><br>Price: %{customdata[1]}<extra></extra>")

# Create bubble plot
def make_bubble() -> go.Figure:
    # Filter data for the animation
    df_anim = df.query("`Residential Type` == 'All' and `Sale Year` >= 2005").copy()

    # Guard: empty dataset
    if df_anim.empty:
        fig = go.Figure()
        fig.update_layout(
            title="No data for Residential Type = 'All' and Year ≥ 2005",
            xaxis_title="Median Household Income",
            yaxis_title="Sale Amount (USD)",
            height=500,
        )
        return fig

    # Drop NaNs in critical fields
    df_anim = df_anim.dropna(subset=["Median Household Income", "Sale Amount", "Sale Year"])

    # Ensure year → INT → clean STRING (strip any embedded quotes or whitespace)
    df_anim["Sale Year"] = (
        pd.to_numeric(df_anim["Sale Year"], errors="coerce")
        .astype("Int64")
        .dropna()
    )
    df_anim["Sale Year"] = df_anim["Sale Year"].astype(int).astype(str)
    df_anim["Sale Year"] = df_anim["Sale Year"].str.strip().str.strip("'\"")

    years_str = sorted(df_anim["Sale Year"].unique())
    if len(years_str) < 2:
        # Only one frame → static plot
        fig = px.scatter(
            df_anim,
            x="Median Household Income",
            y="Sale Amount",
            color="Town",
            hover_name="Town",
            labels={
                "Median Household Income": "Median Household Income",
                "Sale Amount": "Sale Amount (USD)",
            },
        )
        fig.update_layout(title=f"Bubble plot (static) — Year {years_str[0]}")
        return fig

    # Size handling
    if "Population" not in df_anim.columns:
        df_anim["Population"] = 1
    global_max = df_anim["Population"].max()
    if pd.isna(global_max) or global_max == 0:
        global_max = 1

    df_anim["Size_Scatter"] = (df_anim["Population"] / global_max).clip(lower=0.02) * 40
    df_anim["Size_Scatter"] = df_anim["Size_Scatter"].fillna(0.02 * 40)

    # Fixed ranges so you can see motion
    x_min = float(df_anim["Median Household Income"].min())
    x_max = float(df_anim["Median Household Income"].max())
    y_min = float(df_anim["Sale Amount"].min())
    y_max = float(df_anim["Sale Amount"].max())

    fig = px.scatter(
        df_anim,
        x="Median Household Income",
        y="Sale Amount",
        color="Town",
        size="Size_Scatter",
        hover_name="Town",
        labels={
            "Median Household Income": "Median Household Income",
            "Sale Amount": "Sale Amount (USD)",
            "Sale Year": "Year",
        },
        animation_frame="Sale Year",                   # now clean strings like "2010"
        # animation_group="Town",                      # optional
        category_orders={"Sale Year": years_str},      # exact same clean strings
        range_x=[x_min, x_max],
        range_y=[y_min, y_max],
    )

    # Area sizing
    size_max_px = 40
    max_size_val = float(df_anim["Size_Scatter"].max()) if df_anim["Size_Scatter"].max() is not None else 1.0
    sizeref = 2.0 * max_size_val / (size_max_px ** 2) if max_size_val > 0 else 1.0
    fig.update_traces(marker=dict(sizemode="area", sizeref=sizeref, sizemin=6, opacity=0.8))

    # Explicit animation controls using the same clean year strings
    fig.update_layout(
        #height=600,
        legend_title_text="Town",
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[
                            None,
                            {
                                "frame": {"duration": 600, "redraw": True},
                                "fromcurrent": True,
                                "transition": {"duration": 300, "easing": "linear"},
                            },
                        ],
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[
                            [None],
                            {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"},
                        ],
                    ),
                ],
            )
        ],
        sliders=[
            dict(
                active=0,
                currentvalue={"prefix": "Year: "},
                steps=[
                    dict(
                        label=y,
                        method="animate",
                        args=[[y], {"mode": "immediate", "frame": {"duration": 0, "redraw": True}}],
                    )
                    for y in years_str
                ],
            )
        ],
    )
    return fig




# Shiny UI using shinywidgets
app_ui = ui.page_fluid(
    ui.card(
        ui.card_header("Connecticut Municipalities Map"),
        output_widget("connecticut_map"),
        ui.row(
            ui.input_slider(
        "year_slider",
        "Choose a year",
        min = 2001,
        max = 2021,
        value = 2011,
        step = 1,
        ),
        ui.input_select(
        "residential_type",
        "Residential Type",
        choices = list(df["Residential Type"].unique()),
        selected="All"
        )
        )
    ),
    ui.card(
        ui.card_header("Bubble Plot"),
        ui.output_ui("connecticut_bubble")
    )
)

# Shiny server using render_plotly
def server(input, output, session):
    fig_reactive = reactive.Calc(lambda: make_fig(input.year_slider(), input.residential_type()))

    @reactive.Calc    
    def bubble_fig():        
        return make_bubble()

    @output
    @render_plotly
    def connecticut_map():
        return fig_reactive()
    
    @output
    @render.ui
    def connecticut_bubble():
        return ui.HTML(make_bubble().to_html())



app = App(app_ui, server)
