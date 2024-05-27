"""
When rendering Plotly graphs as the children of tabs, sometimes the graph will
not be sized correctly if it wasn't initially visible. The solution to this
problem is to render the tab content dynamically using a callback.

This example shows how to do that, and also shows how to use a dcc.Store
component to cache the graph data so that if the generating process is slow,
the graph still renders quickly when the user switches tabs.
"""

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import geopandas as gpd
import pandas as pd
import numpy as np
import os
from shapely import centroid
import plotly_express as px
from dash import Input, Output, dcc, html, State, dash_table
from classes.areaplotter import plot_area
from pysal.explore import esda  # Exploratory Spatial analytics
from pysal.lib import weights  # Spatial weights
from splot import esda as esdaplot

import classes.entropycalculator as ec


# EXPLAINER = """This example shows how to use callbacks to render graphs inside
# tab content to ensure that they are sized correctly when switching tabs. It
# also demonstrates use of a `dcc.Store` component to cache graph data so that
# if the data generating process is expensive, switching tabs is still quick."""
EXPLAINER = """"""

app = dash.Dash(external_stylesheets=[dbc.themes.LUX])

app.layout = dbc.Container(
    [
        html.H1("Entropy dashboard", id="title", style={"textAlign": "center"}),
        dcc.Markdown(EXPLAINER),
        dbc.Button(
            "Regenerate graphs",
            color="primary",
            id="button",
            className="mb-3",
        ),
        dbc.RadioItems(
            options=[
                {"label": "Entropy", "value": "entropy"},
                {"label": "Autocorrelation", "value": "autocorrelation"},
            ],
            value="autocorrelation",
            id="mode_selector",
            inline=True,
        ),
        dbc.RadioItems(
            options=[
                {"label": "Shannon", "value": "shannon"},
                {"label": "Leibovici", "value": "leibovici"},
                {"label": "Altieri", "value": "altieri"},
            ],
            value="shannon",
            id="entropy_selector",
            inline=True,
        ),
        dbc.RadioItems(
            options=[
                {"label": "Not normalised", "value": ""},
                {"label": "Normalised", "value": "_n"},
            ],
            value="",
            id="normalisation_selector",
            inline=True,
        ),
        dbc.RadioItems(
            options=[
                {"label": "Filter 0", "value": "0"},
                {"label": "Filter 1", "value": "1"},
                {"label": "Filter 2", "value": "2"},
            ],
            value="0",
            id="filter_selector",
            inline=True,
        ),
        dbc.RadioItems(
            options=[
                {"label": "L0", "value": "L0"},
                {"label": "L1", "value": "L1"},
            ],
            value="L0",
            id="category_selector",
            inline=True,
        ),
        dbc.RadioItems(
            options=[
                {"label": "Wijken", "value": "wijken"},
                {"label": "Buurten", "value": "buurten"},
            ],
            value="wijken",
            id="scale_selector",
            inline=True,
        ),
        dbc.Offcanvas(
            children=[],
            id="offcanvas-placement",
            title="Placement",
            is_open=False,
            placement="end",
            style={"width": "70%"},
        ),
        dbc.Tabs(
            [
                dbc.Tab(label="Amsterdam", tab_id="Amsterdam"),
                dbc.Tab(label="Eindhoven", tab_id="Eindhoven"),
                dbc.Tab(label="Rotterdam", tab_id="Rotterdam"),
                dbc.Tab(label="Maastricht", tab_id="Maastricht"),
                dbc.Tab(label="Utrecht", tab_id="Utrecht"),
                dbc.Tab(label="Groningen", tab_id="Groningen"),
                dbc.Tab(label="Leeuwarden", tab_id="Leeuwarden"),
                dbc.Tab(label="Zwolle", tab_id="Zwolle"),
                dbc.Tab(label="Arnhem", tab_id="Arnhem"),
                dbc.Tab(label="Den Haag", tab_id="Den Haag"),
            ],
            id="tabs",
            active_tab="Eindhoven",
        ),
        # include an empty div where the graph will be rendered
        # html.Div(id="graph-container", children=[]),
        # we wrap the store and tab content with a spinner so that when the
        # data is being regenerated the spinner shows. delay_show means we
        # don't see the spinner flicker when switching tabs
        dbc.Spinner(
            [
                dcc.Store(id="store"),
                html.Div(id="tab-content", className="p-4"),
            ],
            delay_show=100,
        ),
        dbc.Spinner(
            [
                dcc.Store(id="store_correlations"),
                html.Div(id="correlation-content", className="p-4"),
            ],
            delay_show=100,
        ),
    ]
)


def get_similar_areas(gdf, area, n=5):
    agecols = list(gdf.filter(regex="P_.*_JR$").columns)
    features = ["BEV_DICHTH", "L0_altieri", "L1_altieri"]
    gdf = gdf[gdf["BEV_DICHTH"] > 0]  # remove rows with 0 population density
    # normalize features
    gdf[features] = gdf[features].apply(lambda x: (x - x.min()) / (x.max() - x.min()))
    gdf[agecols] = gdf[agecols].apply(lambda x: x / 100)

    area = gdf[gdf.index == area.index[0]]

    features = features + agecols

    # calculate the distance between the sample and all other wijken, don't use the index
    gdf["distance"] = np.linalg.norm(gdf[features] - area[features].values[0], axis=1)

    # sort by distance ascending
    similarities = gdf.sort_values("distance").reset_index(drop=True)
    # similarities = similarities[~similarities['gemeentenaam'].isin(area['gemeentenaam'])]

    return similarities[1 : n + 1][["gemeentenaam", "wijknaam"]]


def get_choro(
    gdf, ent_value="shannon", scale_value="wijken", category_value="L0", norm=""
):
    labelnames = {"wijken": "wijknaam", "buurten": "buurtnaam"}
    codenames = {"wijken": "wijkcode", "buurten": "buurtcode"}
    fig = px.choropleth(
        gdf,
        geojson=gdf.geometry,
        locations=gdf.index,
        color_continuous_scale="thermal",
        # set scale range from 0 to 6
        range_color=(0, 8) if "_n" not in norm else (0, 1),
        color=f"{category_value}_{ent_value}{norm}",
        hover_data={labelnames[scale_value]: True, codenames[scale_value]: True},
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, autosize=True)
    return fig


def get_choro_autocor(
    gdf, ent_value="shannon", scale_value="wijken", category_value="L0", norm=""
):
    labelnames = {"wijken": "wijknaam", "buurten": "buurtnaam"}
    codenames = {"wijken": "wijkcode", "buurten": "buurtcode"}
    col = f"{category_value}_{ent_value}{norm}"

    gdf = gdf.dropna(subset=[col])
    gdf = gdf.reset_index(drop=True)
    w = weights.contiguity.Queen.from_dataframe(gdf, use_index=False)
    w.transform = "R"

    lisa = esda.Moran_Local(gdf[col], w)

    gdf.loc[:, "lisa"] = lisa.q

    lisadict = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    gdf.loc[:, "lisa"] = gdf.loc[:, "lisa"].map(lisadict)

    fig = px.choropleth(
        gdf,
        geojson=gdf.geometry,
        locations=gdf.index,
        color="lisa",
        color_discrete_map={
            "HH": "#E45756",
            "LH": "#72B7B2",
            "LL": "#4C78A8",
            "HL": "#F58518",
        },
        color_discrete_sequence=["#E45756", "#72B7B2", "#4C78A8", "#F58518"],
        # color_continuous_scale=["#E45756", "#72B7B2", "#4C78A8", "#F58518"],
        hover_data={labelnames[scale_value]: True, codenames[scale_value]: True},
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, autosize=True)
    return fig


@app.callback(
    [
        Output("offcanvas-placement", "is_open"),
        Output("offcanvas-placement", "children"),
        Output("offcanvas-placement", "title"),
    ],
    [
        Input("choro", "clickData"),
        Input("tabs", "active_tab"),
        Input("scale_selector", "value"),
        Input("filter_selector", "value"),
    ],
    [State("offcanvas-placement", "is_open")],
)
def toggle_offcanvas(clickData, gm_name, scale, filterlevel, is_open):
    if clickData:
        # print(clickData)

        area_code = clickData["points"][0]["customdata"][1]
        area_name = clickData["points"][0]["customdata"][0].replace("/", "_")
        areadict = {"wijken": "wijknaam", "buurten": "buurtnaam"}
        codedict = {"wijken": "wijkcode", "buurten": "buurtcode"}

        # load all cbs data
        # cbs = gpd.read_parquet("data/wijkenbuurten_2023_clean.parquet")
        # cbs = cbs[cbs[codedict[scale]] == area_code]
        gdf = gpd.read_parquet(
            f"results/filter{filterlevel}/{scale}/{gm_name}_{scale}_{filterlevel}.parquet"
        )
        area = gdf[gdf[areadict[scale]] == area_name]
        # collect statistics
        aantal_inwoners = area["AANT_INW"]
        agecols = area.filter(regex="P_.*_JR$").columns
        area.loc[:, agecols] = area.loc[:, agecols].apply(
            lambda x: np.ceil(aantal_inwoners * x / 100)
        )

        cols_gebnl = area.filter(regex="P_GEBNL.*").columns
        cols_gebbl = area.filter(regex="P_GEBBL.*").columns
        # cols_geb = cols_gebnl + cols_gebbl
        area.loc[:, cols_gebnl] = area.loc[:, cols_gebnl].apply(
            lambda x: np.ceil(aantal_inwoners * x / 100)
        )
        area.loc[:, cols_gebbl] = area.loc[:, cols_gebbl].apply(
            lambda x: np.ceil(aantal_inwoners * x / 100)
        )

        # make relative bar plot of the amount of mannen en vrouwen
        mv_bar = go.Figure()
        mv_bar.add_trace(
            go.Bar(
                y=["Mannen / Vrouwen"],
                x=area["AANT_MAN"],
                name="Mannen",
                orientation="h",
                marker=dict(
                    color="rgba(36, 111, 219, 0.4)",
                    line=dict(color="rgba(36, 111, 219, 0.4)"),
                ),
            )
        )
        mv_bar.add_trace(
            go.Bar(
                y=["Mannen / Vrouwen"],
                x=area["AANT_VROUW"],
                name="Vrouwen",
                orientation="h",
                marker=dict(
                    color="rgba(245, 40, 145, 0.4)",
                    line=dict(color="rgba(245, 40, 145, 0.4)"),
                ),
            )
        )
        for col in agecols:
            mv_bar.add_trace(
                go.Bar(
                    y=["leeftijd"],
                    x=area[col],
                    name=col,
                    orientation="h",
                )
            )
        for col in cols_gebnl:
            mv_bar.add_trace(
                go.Bar(
                    y=["geboren"],
                    x=area[col],
                    name=col,
                    orientation="h",
                )
            )
        for col in cols_gebbl:
            mv_bar.add_trace(
                go.Bar(
                    y=["geboren"],
                    x=area[col],
                    name=col,
                    orientation="h",
                )
            )

        mv_bar.update_layout(
            barmode="relative",
            # height=250,
            xaxis_autorange=True,
        )

        area = gpd.read_parquet(
            f"results/filter{filterlevel}/{scale}/{gm_name}_{scale}_{filterlevel}.parquet"
        )
        area = area[area[areadict[scale]] == area_name]

        counts = area.filter(regex="L0_c_.*").sum()
        counts = counts.reset_index()
        counts.columns = ["category", "count"]
        counts.category = counts.category.str.replace("L0_c_", "")
        amenity_bar = px.bar(counts, x="count", y="category", orientation="h")

        gdf_tot = None
        for file in os.listdir(f"results/filter{filterlevel}/{scale}"):
            if file.endswith(".parquet"):
                if gdf_tot is not None:
                    gdf_tot = pd.concat(
                        [
                            gdf_tot,
                            gpd.read_parquet(
                                f"results/filter{filterlevel}/{scale}/{file}"
                            ),
                        ]
                    )
                else:
                    gdf_tot = gpd.read_parquet(
                        f"results/filter{filterlevel}/{scale}/{file}"
                    )
        area = gdf_tot[gdf_tot[codedict[scale]] == area_code]
        similarities = get_similar_areas(gdf_tot, area, 5)

        return (
            not is_open,
            # html.Img(src=app.get_asset_url("area_plot.png"), style={"width": "100%"}),
            [
                html.H4(f"Amenity distribution"),
                dcc.Graph(figure=amenity_bar),
                html.H4(f"Population distribution"),
                dcc.Graph(figure=mv_bar),
                html.H4(f"Most similar areas"),
                dash_table.DataTable(similarities.to_dict("records")),
            ],
            f"{gm_name} - {clickData['points'][0]['customdata'][0]}",
        )

    return is_open, None, "Placement"


@app.callback(
    Output("tab-content", "children"),
    [
        Input("tabs", "active_tab"),
        Input("store", "data"),
    ],
)
def render_tab_content(active_tab, data):
    """
    This callback takes the 'active_tab' property as input, as well as the
    stored graphs, and renders the tab content depending on what the value of
    'active_tab' is.
    """
    if active_tab and data is not None:
        if active_tab == "Amsterdam":
            return dcc.Graph(figure=data["Amsterdam"], id="choro")
        elif active_tab == "Eindhoven":
            return dcc.Graph(figure=data["Eindhoven"], id="choro")
        elif active_tab == "Rotterdam":
            return dcc.Graph(figure=data["Rotterdam"], id="choro")
        elif active_tab == "Maastricht":
            return dcc.Graph(figure=data["Maastricht"], id="choro")
        elif active_tab == "Utrecht":
            return dcc.Graph(figure=data["Utrecht"], id="choro")
        elif active_tab == "Groningen":
            return dcc.Graph(figure=data["Groningen"], id="choro")
        elif active_tab == "Leeuwarden":
            return dcc.Graph(figure=data["Leeuwarden"], id="choro")
        elif active_tab == "Zwolle":
            return dcc.Graph(figure=data["Zwolle"], id="choro")
        elif active_tab == "Arnhem":
            return dcc.Graph(figure=data["Arnhem"], id="choro")
        elif active_tab == "Den Haag":
            return dcc.Graph(figure=data["Den Haag"], id="choro")
    return "No tab selected"


@app.callback(
    Output("store", "data"),
    [
        Input("button", "n_clicks"),
        Input("entropy_selector", "value"),
        Input("filter_selector", "value"),
        Input("scale_selector", "value"),
        Input("category_selector", "value"),
        Input("normalisation_selector", "value"),
        Input("mode_selector", "value"),
    ],
)
def generate_graphs(
    n, ent_value, filter_value, scale_value, category_value, norm, mode
):
    """
    This callback generates three simple graphs from random data.
    """

    if mode == "autocorrelation":
        ams = get_choro_autocor(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Amsterdam_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        ehv = get_choro_autocor(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Eindhoven_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        rot = get_choro_autocor(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Rotterdam_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        maa = get_choro_autocor(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Maastricht_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        dhg = get_choro_autocor(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/'s-Gravenhage_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        arn = get_choro_autocor(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Arnhem_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        zwl = get_choro_autocor(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Zwolle_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        lwd = get_choro_autocor(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Leeuwarden_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        grn = get_choro_autocor(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Groningen_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        utr = get_choro_autocor(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Utrecht_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )

    else:
        ams = get_choro(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Amsterdam_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        ehv = get_choro(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Eindhoven_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        rot = get_choro(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Rotterdam_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        maa = get_choro(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Maastricht_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        dhg = get_choro(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/'s-Gravenhage_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        arn = get_choro(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Arnhem_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        zwl = get_choro(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Zwolle_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        lwd = get_choro(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Leeuwarden_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        grn = get_choro(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Groningen_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )
        utr = get_choro(
            gpd.read_parquet(
                f"results/filter{filter_value}/{scale_value}/Utrecht_{scale_value}_{filter_value}.parquet"
            ),
            ent_value,
            scale_value,
            category_value,
            norm,
        )

    # save figures in a dictionary for sending to the dcc.Store
    return {
        "Amsterdam": ams,
        "Eindhoven": ehv,
        "Rotterdam": rot,
        "Maastricht": maa,
        "Den Haag": dhg,
        "Arnhem": arn,
        "Zwolle": zwl,
        "Leeuwarden": lwd,
        "Groningen": grn,
        "Utrecht": utr,
    }


@app.callback(
    Output("store_correlations", "data"),
    [
        Input("button", "n_clicks"),
        Input("filter_selector", "value"),
        Input("scale_selector", "value"),
        Input("category_selector", "value"),
        Input("normalisation_selector", "value"),
    ],
)
def generate_corr_matrices(n, filter_value, scale_value, category_value, norm):
    """
    This callback computes the correlation matrices for the different cities.
    """

    ams = gpd.read_parquet(
        f"results/filter{filter_value}/{scale_value}/Amsterdam_{scale_value}_{filter_value}.parquet"
    )
    ehv = gpd.read_parquet(
        f"results/filter{filter_value}/{scale_value}/Eindhoven_{scale_value}_{filter_value}.parquet"
    )
    rot = gpd.read_parquet(
        f"results/filter{filter_value}/{scale_value}/Rotterdam_{scale_value}_{filter_value}.parquet"
    )
    maa = gpd.read_parquet(
        f"results/filter{filter_value}/{scale_value}/Maastricht_{scale_value}_{filter_value}.parquet"
    )
    dhg = gpd.read_parquet(
        f"results/filter{filter_value}/{scale_value}/'s-Gravenhage_{scale_value}_{filter_value}.parquet"
    )
    arn = gpd.read_parquet(
        f"results/filter{filter_value}/{scale_value}/Arnhem_{scale_value}_{filter_value}.parquet"
    )
    zwl = gpd.read_parquet(
        f"results/filter{filter_value}/{scale_value}/Zwolle_{scale_value}_{filter_value}.parquet"
    )
    lwd = gpd.read_parquet(
        f"results/filter{filter_value}/{scale_value}/Leeuwarden_{scale_value}_{filter_value}.parquet"
    )
    grn = gpd.read_parquet(
        f"results/filter{filter_value}/{scale_value}/Groningen_{scale_value}_{filter_value}.parquet"
    )
    utr = gpd.read_parquet(
        f"results/filter{filter_value}/{scale_value}/Utrecht_{scale_value}_{filter_value}.parquet"
    )

    ams_corr = ams.filter(regex=f"{category_value}_.*_n$").corr()
    ehv_corr = ehv.filter(regex=f"{category_value}_.*_n$").corr()
    rot_corr = rot.filter(regex=f"{category_value}_.*_n$").corr()
    maa_corr = maa.filter(regex=f"{category_value}_.*_n$").corr()
    dhg_corr = dhg.filter(regex=f"{category_value}_.*_n$").corr()
    arn_corr = arn.filter(regex=f"{category_value}_.*_n$").corr()
    zwl_corr = zwl.filter(regex=f"{category_value}_.*_n$").corr()
    lwd_corr = lwd.filter(regex=f"{category_value}_.*_n$").corr()
    grn_corr = grn.filter(regex=f"{category_value}_.*_n$").corr()
    utr_corr = utr.filter(regex=f"{category_value}_.*_n$").corr()

    # set the diagonal to NaN
    np.fill_diagonal(ams_corr.values, np.nan)
    np.fill_diagonal(ehv_corr.values, np.nan)
    np.fill_diagonal(rot_corr.values, np.nan)
    np.fill_diagonal(maa_corr.values, np.nan)
    np.fill_diagonal(dhg_corr.values, np.nan)
    np.fill_diagonal(arn_corr.values, np.nan)
    np.fill_diagonal(zwl_corr.values, np.nan)
    np.fill_diagonal(lwd_corr.values, np.nan)
    np.fill_diagonal(grn_corr.values, np.nan)
    np.fill_diagonal(utr_corr.values, np.nan)

    # make a px graph of the correlation matrix
    ams_corr = px.imshow(ams_corr, range_color=(0, 1))
    ehv_corr = px.imshow(ehv_corr, range_color=(0, 1))
    rot_corr = px.imshow(rot_corr, range_color=(0, 1))
    maa_corr = px.imshow(maa_corr, range_color=(0, 1))
    dhg_corr = px.imshow(dhg_corr, range_color=(0, 1))
    arn_corr = px.imshow(arn_corr, range_color=(0, 1))
    zwl_corr = px.imshow(zwl_corr, range_color=(0, 1))
    lwd_corr = px.imshow(lwd_corr, range_color=(0, 1))
    grn_corr = px.imshow(grn_corr, range_color=(0, 1))
    utr_corr = px.imshow(utr_corr, range_color=(0, 1))

    # save figures in a dictionary for sending to the dcc.Store
    return {
        "Amsterdam": ams_corr,
        "Eindhoven": ehv_corr,
        "Rotterdam": rot_corr,
        "Maastricht": maa_corr,
        "Den Haag": dhg_corr,
        "Arnhem": arn_corr,
        "Zwolle": zwl_corr,
        "Leeuwarden": lwd_corr,
        "Groningen": grn_corr,
        "Utrecht": utr_corr,
    }


@app.callback(
    Output("correlation-content", "children"),
    [
        Input("tabs", "active_tab"),
        Input("store_correlations", "data"),
    ],
)
def render_correlation_matrices(active_tab, data):
    """
    This callback takes the 'active_tab' property as input, as well as the
    stored graphs, and renders the tab content depending on what the value of
    'active_tab' is.
    """

    if active_tab and data is not None:
        if active_tab == "Amsterdam":
            return dcc.Graph(figure=data["Amsterdam"])
        elif active_tab == "Eindhoven":
            return dcc.Graph(figure=data["Eindhoven"])
        elif active_tab == "Rotterdam":
            return dcc.Graph(figure=data["Rotterdam"])
        elif active_tab == "Maastricht":
            return dcc.Graph(figure=data["Maastricht"])
        elif active_tab == "Utrecht":
            return dcc.Graph(figure=data["Utrecht"])
        elif active_tab == "Groningen":
            return dcc.Graph(figure=data["Groningen"])
        elif active_tab == "Leeuwarden":
            return dcc.Graph(figure=data["Leeuwarden"])
        elif active_tab == "Zwolle":
            return dcc.Graph(figure=data["Zwolle"])
        elif active_tab == "Arnhem":
            return dcc.Graph(figure=data["Arnhem"])
        elif active_tab == "Den Haag":
            return dcc.Graph(figure=data["Den Haag"])

    return "No tab selected"


if __name__ == "__main__":
    app.run(debug=True)
