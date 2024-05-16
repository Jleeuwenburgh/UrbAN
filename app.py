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
import numpy as np
from shapely import centroid
import plotly_express as px
from dash import Input, Output, dcc, html, State
from classes.areaplotter import plot_area

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
                dbc.Tab(label="Nijmegen", tab_id="Nijmegen"),
                dbc.Tab(label="Maastricht", tab_id="Maastricht"),
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


def area_plot(scale, gm_name, area_name):
    gdf = gpd.read_parquet(
        f"results_normalised/filter0/{scale}/{gm_name}_{scale}.parquet"
    )
    labelnames = {"wijken": "wijknaam", "buurten": "buurtnaam"}
    gdf = gdf[gdf[labelnames[scale]] == area_name]
    inner_b, outer_b = ec.return_buildings(gdf.geometry.values[0])
    amenities = ec.return_categorised_amenities(gdf.geometry.values[0])

    figure = go.Figure()

    figure.add_trace(outer_b.plot(color="silver", alpha=0.3))
    figure.add_trace(inner_b.plot(color="silver", edgecolor="dimgrey", alpha=0.5))
    figure.add_trace(gdf.boundary.plot(color="black"))
    figure.add_trace(
        amenities.plot(
            column="L0_category",
            markersize=10,
            cmap="jet",
            legend=True,
            legend_kwds={"loc": "center left", "bbox_to_anchor": (1, 0.5)},
        )
    )

    # fig, ax = plt.subplots()
    # fig, ax = plt.subplots(figsize=(15, 15))
    # outer_b.plot(ax=ax, color="silver", alpha=0.3)
    # inner_b.plot(ax=ax, color="silver", edgecolor="dimgrey", alpha=0.5)
    # gdf.boundary.plot(ax=ax, color="black")
    # amenities.plot(
    #     ax=ax,
    #     column="L0_category",
    #     markersize=10,
    #     cmap="jet",
    #     legend=True,
    #     legend_kwds={"loc": "center left", "bbox_to_anchor": (1, 0.5)},
    # )
    # ax.set_axis_off()

    return figure


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
        # color_continuous_midpoint=0.5 if "_n" in value else 0.5,
        color=f"{category_value}_{ent_value}{norm}",
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
        print(clickData)

        area_code = clickData["points"][0]["customdata"][1]
        area_name = clickData["points"][0]["customdata"][0].replace("/", "_")
        areadict = {"wijken": "wijknaam", "buurten": "buurtnaam"}
        codedict = {"wijken": "wijkcode", "buurten": "buurtcode"}

        # load all cbs data
        cbs = gpd.read_parquet("wijkenbuurten_2023_clean.parquet")
        cbs = cbs[cbs[codedict[scale]] == area_code]

        # collect statistics
        aantal_inwoners = int(cbs["aantal_inwoners"].sum())
        aantal_mannen = int(cbs["mannen"].sum())
        aantal_vrouwen = int(cbs["vrouwen"].sum())

        # make relative bar plot of the amount of mannen en vrouwen
        mv_bar = go.Figure()
        mv_bar.add_trace(
            go.Bar(
                y=["Mannen / Vrouwen"],
                x=[aantal_mannen],
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
                x=[aantal_vrouwen],
                name="Vrouwen",
                orientation="h",
                marker=dict(
                    color="rgba(245, 40, 145, 0.4)",
                    line=dict(color="rgba(245, 40, 145, 0.4)"),
                ),
            )
        )

        mv_bar.update_layout(
            barmode="relative",
            height=250,
            xaxis_autorange=True,
        )

        area = gpd.read_parquet(
            f"results/filter{filterlevel}/{scale}/{gm_name}_{scale}.parquet"
        )
        area = area[area[areadict[scale]] == area_name]

        counts = area.filter(regex="L0_c_.*").sum()
        counts = counts.reset_index()
        counts.columns = ["category", "count"]
        counts.category = counts.category.str.replace("L0_c_", "")
        amenity_bar = px.bar(counts, x="count", y="category", orientation="h")

        return (
            not is_open,
            # html.Img(src=app.get_asset_url("area_plot.png"), style={"width": "100%"}),
            [
                dcc.Graph(figure=amenity_bar),
                dcc.Graph(figure=mv_bar),
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
        elif active_tab == "Nijmegen":
            return dcc.Graph(figure=data["Nijmegen"], id="choro")
        elif active_tab == "Maastricht":
            return dcc.Graph(figure=data["Maastricht"], id="choro")
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
    ],
)
def generate_graphs(n, ent_value, filter_value, scale_value, category_value, norm):
    """
    This callback generates three simple graphs from random data.
    """

    ams = get_choro(
        gpd.read_parquet(
            f"results_normalised/filter{filter_value}/{scale_value}/amsterdam_{scale_value}.parquet"
        ),
        ent_value,
        scale_value,
        category_value,
        norm,
    )
    ehv = get_choro(
        gpd.read_parquet(
            f"results_normalised/filter{filter_value}/{scale_value}/eindhoven_{scale_value}.parquet"
        ),
        ent_value,
        scale_value,
        category_value,
        norm,
    )
    rot = get_choro(
        gpd.read_parquet(
            f"results_normalised/filter{filter_value}/{scale_value}/rotterdam_{scale_value}.parquet"
        ),
        ent_value,
        scale_value,
        category_value,
        norm,
    )
    nij = get_choro(
        gpd.read_parquet(
            f"results_normalised/filter{filter_value}/{scale_value}/nijmegen_{scale_value}.parquet"
        ),
        ent_value,
        scale_value,
        category_value,
        norm,
    )
    maa = get_choro(
        gpd.read_parquet(
            f"results_normalised/filter{filter_value}/{scale_value}/maastricht_{scale_value}.parquet"
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
        "Nijmegen": nij,
        "Maastricht": maa,
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
        f"results_normalised/filter{filter_value}/{scale_value}/amsterdam_{scale_value}.parquet"
    )
    ehv = gpd.read_parquet(
        f"results_normalised/filter{filter_value}/{scale_value}/eindhoven_{scale_value}.parquet"
    )
    rot = gpd.read_parquet(
        f"results_normalised/filter{filter_value}/{scale_value}/rotterdam_{scale_value}.parquet"
    )
    nij = gpd.read_parquet(
        f"results_normalised/filter{filter_value}/{scale_value}/nijmegen_{scale_value}.parquet"
    )
    maa = gpd.read_parquet(
        f"results_normalised/filter{filter_value}/{scale_value}/maastricht_{scale_value}.parquet"
    )

    ams_corr = ams.filter(regex=f"{category_value}_.*_n$").corr()
    ehv_corr = ehv.filter(regex=f"{category_value}_.*_n$").corr()
    rot_corr = rot.filter(regex=f"{category_value}_.*_n$").corr()
    nij_corr = nij.filter(regex=f"{category_value}_.*_n$").corr()
    maa_corr = maa.filter(regex=f"{category_value}_.*_n$").corr()

    # set the diagonal to NaN
    np.fill_diagonal(ams_corr.values, np.nan)
    np.fill_diagonal(ehv_corr.values, np.nan)
    np.fill_diagonal(rot_corr.values, np.nan)
    np.fill_diagonal(nij_corr.values, np.nan)
    np.fill_diagonal(maa_corr.values, np.nan)

    # make a px graph of the correlation matrix
    ams_corr = px.imshow(ams_corr)
    ehv_corr = px.imshow(ehv_corr)
    rot_corr = px.imshow(rot_corr)
    nij_corr = px.imshow(nij_corr)
    maa_corr = px.imshow(maa_corr)

    # save figures in a dictionary for sending to the dcc.Store
    return {
        "Amsterdam": ams_corr,
        "Eindhoven": ehv_corr,
        "Rotterdam": rot_corr,
        "Nijmegen": nij_corr,
        "Maastricht": maa_corr,
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
        elif active_tab == "Nijmegen":
            return dcc.Graph(figure=data["Nijmegen"])
        elif active_tab == "Maastricht":
            return dcc.Graph(figure=data["Maastricht"])
    return "No tab selected"


if __name__ == "__main__":
    app.run(debug=True)
