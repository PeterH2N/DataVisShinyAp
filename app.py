from estate_data import pie_chart
import plotly.express as px
import plotly.graph_objects as go
import requests
import pandas as pd
from shiny import App, ui, reactive, render
from shinywidgets import output_widget, render_plotly
from estate_data import average_price_by_town_by_year, assessed_vs_sale

# Download official GeoJSON
geojson_url = "https://geodata.ct.gov/api/download/v1/items/654fdaadd0dd4b53babb0fa37f4c0b75/geojson?layers=0"
geojson = requests.get(geojson_url).json()

# Extract municipality names
municipalities = [feature["properties"]["Municipality"] for feature in geojson["features"]]

# Create DataFrame with random values
df = average_price_by_town_by_year()

report_url = "https://docs.google.com/document/d/1DDc3AaebMGMwsLZFZ00CDSKElZVNbGRQ2rUThI_wy1I/edit?usp=sharing"

# Assessed value vs sale amount
def make_assessed(y_axis) -> go.Figure:
    filtered_df = (df.query("`Sale Year` >= 2009")).copy()
    filtered_df["Percentage Of Income Sale"] = filtered_df["Sale Amount"] / filtered_df["Median Household Income"] * 100
    filtered_df["Percentage Of Income Assessment"] = filtered_df["Assessed Value"] / filtered_df["Median Household Income"] * 100
    year_df = filtered_df.groupby(["Sale Year"], as_index=False)[["Sale Amount", "Assessed Value", "Median Household Income", "Percentage Of Income Sale", "Percentage Of Income Assessment"]].mean()


    if (y_axis == "Sale Amount"):
        fig = px.line(
            year_df,
            y=["Sale Amount","Assessed Value"],
            x="Sale Year",
            markers=True
        )
        return fig
    else:
        fig = px.line(
            year_df,
            y=["Percentage Of Income Sale", "Percentage Of Income Assessment"],
            x="Sale Year",
            markers=True
        )
        return fig


# Create Plotly choropleth map
def make_fig(year, residential_type) -> go.Figure: 

    filtered_df = df.query(f"`Sale Year` == {year} and `Residential Type` == '{residential_type}'")
    filtered_df["clipped_price"] = df["Sale Amount"].clip(lower=df["Sale Amount"].quantile(.1), upper=df["Sale Amount"].quantile(.95))

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
        hover_data={"Size_Scatter": False},
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

# scatterplot for change over time
def make_scatter() -> go.Figure:
    df_filtered = df.query("`Residential Type` == 'All' and `Sale Year` >= 2005").copy()
    df_filtered = df_filtered.groupby(["Town", "Sale Year"], as_index=False)["Sale Amount"].mean().copy()
    price_2009 = df_filtered.query("`Sale Year` == 2011").drop(columns=["Sale Year"])
    price_2009["Sale Amount 2011"] = price_2009["Sale Amount"]
    price_2009 = price_2009.drop(columns=["Sale Amount"]).copy()
    df_filtered = df_filtered.query("`Sale Year`== 2021").copy()
    df_filtered = df_filtered.groupby(["Town"])[["Sale Amount"]].mean()


    df_filtered = df_filtered.merge(
        price_2009[["Town", "Sale Amount 2011"]],
        on=["Town"],
        how="left",
    )

    df_filtered["Change Percentage"] = (df_filtered["Sale Amount"] - df_filtered["Sale Amount 2011"]) / df_filtered["Sale Amount 2011"] * 100

    fig = px.scatter(
        df_filtered,
        y="Change Percentage",
        x="Sale Amount",
        color="Town",
        hover_data={"Sale Amount": True, "Town": True, "Sale Amount 2011": True},
        labels={"Change Percentage": "Change since 2011"}
    )

    return fig

# bar chart for residential types
def make_bar_chart() -> go.Figure:
    df_filtered = df.query("`Sale Year` >= 2005").copy()
    df_filtered = df_filtered.groupby(["Residential Type", "Sale Year"], as_index=False)["Sale Amount"].mean().copy()
    price_2009 = df_filtered.query("`Sale Year` == 2011").drop(columns=["Sale Year"])
    print(price_2009)
    price_2009["Sale Amount 2011"] = price_2009["Sale Amount"]
    price_2009 = price_2009.drop(columns=["Sale Amount"]).copy()
    df_filtered = df_filtered.query("`Sale Year`== 2021").copy()
    df_filtered = df_filtered.groupby(["Residential Type"])[["Sale Amount"]].mean()


    df_filtered = df_filtered.merge(
        price_2009[["Residential Type", "Sale Amount 2011"]],
        on=["Residential Type"],
        how="left",
    )

    df_filtered["Change Percentage"] = (df_filtered["Sale Amount"] - df_filtered["Sale Amount 2011"]) / df_filtered["Sale Amount 2011"] * 100

    print(df_filtered)

    fig = px.bar(
        df_filtered,
        x="Residential Type",
        y="Change Percentage",
    )

    return fig


# Line plot for percentage of household income, or just sale amount
def make_line_grap(residential_type: str, y_axis: str) -> go.Figure:
    filtered_df = (df.query("`Sale Year` >= 2009")).copy()
    filtered_df["Percentage Of Income"] = filtered_df["Sale Amount"] / filtered_df["Median Household Income"] * 100
    year_df = filtered_df.groupby(["Sale Year"], as_index=False)[["Sale Amount", "Median Household Income", "Percentage Of Income"]].mean()

    fig = px.line(
        year_df,
        y=y_axis,
        x="Sale Year",
        markers=True
    )

    return fig


app_tab_general = ui.page_fluid(
    ui.column(
        12,
        ui.card(
            ui.card_header("1: Residential types by percentage of sales"),
            ui.HTML(pie_chart())
        )
    )
)

app_tab_by_year = ui.page_fluid(
    ui.column(
            12,
            ui.card(
                ui.row(
                    ui.column(
                        6,
                        ui.card(
                        ui.card_header("5 & 6: Prices through the years"),
                        output_widget("connecticut_percentage_line"),
                        ),
                    ),
                    ui.column(
                        6,
                        ui.card(
                        ui.card_header("7 & 8: Assessed price and sales price"),
                        output_widget("connecticut_assessment")
                        ),
                    )
                ),
                ui.card_footer(
                    ui.input_select(
                            "line_plot_type",
                            "Y-Axis",
                            choices = ["Sale Amount", "Percentage Of Income"],
                            selected="Sale Amount"
                        )
                )
            ),
            
            ui.card(
                ui.card_header("9: Change since 2011 by residential type"),
                output_widget("connecticut_change_by_residential")
            )
        )
)

app_tab_by_town = ui.page_fluid(
    ui.column(
            12,
            ui.card(
                ui.card_header("2: Connecticut Municipalities Map"),
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
                ),
                ui.card_footer("This graph was in part AI generated by Microsoft Copilot. The following prompt was used, and then iterated on:\n 'Using shiny python, can you give me an example of a map of Connecticut, with all the municipalities rendered in different color values?'")
                
            ),
            ui.card(
                ui.card_header("3: Bubble Plot"),
                ui.output_ui("connecticut_bubble")
            ),
            ui.card(
                ui.card_header("4: Change since 2011"),
                output_widget("connecticut_change_by_town"),
            ),
        ),    
    
)

# Shiny UI using shinywidgets
app_ui = ui.page_navbar(
        ui.nav_panel(
        "General",
        ui.output_ui("page_general"),
        value="general_tab"
    ),
    ui.nav_panel(
        "Prices by Town",
        ui.output_ui("page_1"),
        value="by_town_tab"
    ),
    ui.nav_panel(
        "Prices through the years",
        ui.output_ui("page_2"),
        value="by_year_tab"
    ),
    # Push following controls to the right
    ui.nav_spacer(),

    # Add a button that opens a URL in a new tab
    ui.nav_control(
        ui.a(
            "Open Docs",
            href=report_url,
            target="_blank",
            rel="noopener",
            class_="btn btn-primary"
         )
    ),
    selected="general_tab",
    title="Connecticut Home Prices",
)

# Shiny server using render_plotly
def server(input, output, session):
    fig_reactive = reactive.Calc(lambda: make_fig(input.year_slider(), input.residential_type()))

    @reactive.Calc    
    def bubble_fig():        
        return make_bubble()
    
    @reactive.Calc
    def percentage_line_fig():
        return make_line_grap("All", input.line_plot_type())
    
    @reactive.Calc
    def reactive_assessment():
        return make_assessed(input.line_plot_type())

    @output
    @render_plotly
    def connecticut_map():
        return fig_reactive()
    
    @output
    @render.ui
    def connecticut_bubble():
        return ui.HTML(make_bubble().to_html())

    @output
    @render_plotly
    def connecticut_percentage_line():
        return percentage_line_fig()

    @output
    @render_plotly
    def connecticut_change_by_town():
        return make_scatter() 

    @output
    @render_plotly
    def connecticut_change_by_residential():
        return make_bar_chart() 

    @output
    @render_plotly
    def connecticut_assessment():
        return reactive_assessment()

    @output
    @render.ui
    def page_1():
        return app_tab_by_town

    @output
    @render.ui
    def page_2():
        return app_tab_by_year

    @output
    @render.ui
    def page_general():
        return app_tab_general



app = App(app_ui, server)
