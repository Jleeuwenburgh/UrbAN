from dash import Dash, html, Output, Input, dash_table, dcc
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import dash_leaflet.express as dlx
from dash_extensions.javascript import arrow_function, assign

import geopandas as gpd
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly_express as px

import json


# load datasets
gemeenten = gpd.read_parquet("data/gemeenten/gemeenten_stats.parquet")
wijken = gpd.read_parquet("data/wijken/wijken_stats_lisa.parquet")
buurten = gpd.read_parquet("data/buurten/buurten_stats.parquet")

gemeenten_counts = pd.read_parquet("data/gemeenten/gemeenten_counts.parquet")
wijken_counts = pd.read_parquet("data/wijken/wijken_counts.parquet")
buurten_counts = pd.read_parquet("data/buurten/buurten_counts.parquet")

# simplify geometry
gemeenten["geometry"] = (
    gemeenten.to_crs(gemeenten.estimate_utm_crs()).simplify(100).to_crs(gemeenten.crs)
)
wijken["geometry"] = (
    wijken.to_crs(wijken.estimate_utm_crs()).simplify(10).to_crs(wijken.crs)
)

# convert to json
gemeenten_json = json.loads(gemeenten.to_json())
wijken_json = json.loads(wijken.to_json())


ent_max = gemeenten["L0_shannon_1"].max()
ent_min = gemeenten["L0_shannon_1"].min()

stedent_max = wijken["sted/entropy"].max()
stedent_min = wijken["sted/entropy"].min()


def get_info(feature=None, hideout=None):
    if hideout:
        ent_measure = hideout["colorProp"].split("_")[1]

        if hideout["colorProp"].split("_")[-1] == "norm":
            infostr = f"Normalised {ent_measure}"
        else:
            infostr = f"Transformed {ent_measure}"
    else:
        ent_measure = ""
        infostr = ""

    header = [html.H4(f"{ent_measure} entropy of municipalities")]
    if not feature:
        return header + [html.P("Hover over a municipality")]
    return header + [
        html.B(feature["properties"]["gemeentenaam"]),
        html.Br(),
        f"{infostr} = {feature['properties'][hideout['colorProp']]:.2f}",
    ]


# ----------- wijken colorscale ------------
colorscale_wijken = "Virdis"
colorbar_wijken = dl.Colorbar(
    colorscale=colorscale_wijken, width=20, height=150, min=0, max=stedent_max
)


# make classes ranging from 0 to ent_max with 8 steps
classes = [0 + (4 - 0) / 8 * i for i in range(9)]

colorscale = [
    "#800026",
    "#BD0026",
    "#E31A1C",
    "#FC4E2A",
    "#FD8D3C",
    "#FEB24C",
    "#FED976",
    "#FFEDA0",
]


# style = dict(weight=2, opacity=1, color="white", dashArray="3", fillOpacity=0.7)
style = dict(weight=1, opacity=1, color="gray", fillOpacity=1)
style_wijk = dict(weight=2, opacity=1, color="darkgray", fillOpacity=0)
# Create colorbar.
ctg = ["{:.2f}+".format(cls, classes[i + 1]) for i, cls in enumerate(classes[:-1])] + [
    "{:.2f}+".format(classes[-1])
]
colorbar = dlx.categorical_colorbar(
    categories=ctg, colorscale=colorscale, width=600, height=30, position="bottomleft"
)
# colorbar = dl.Colorbar(position="bottomleft", width=300, height=30, min=0, max=ent_max)

# chromalib
chroma = "https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.4.2/chroma.min.js"  # js lib used for colors


# Geojson rendering logic, must be JavaScript as it is executed in clientside.
style_handle = assign(
    """function(feature, context){
    const {classes, colorscale, style, colorProp, testprop, municipality, vmax} = context.hideout;  // get props
    const csc = chroma.scale('YlGn').gamma(2).domain([0, vmax]);  // chroma lib to construct colorscale
    style.color = csc(feature.properties[colorProp]);  // set the fill color according to the class
    style.fillColor = csc(feature.properties[colorProp]);  // set the fill color according to the class
    style.color = 'black';
    style.fillOpacity = 1;
    style.weight = 0.5;
    //const value = feature.properties[colorProp];  // get value the determines the color
    //for (let i = 0; i < classes.length; ++i) {
    //    if (value > classes[i]) {
    //        style.fillColor = colorscale[i];  // set the fill color according to the class
    //    }
    //}
    return style;
}"""
)
style_wijk = assign(
    """function(feature, context){
    const {classes, colorscale, style, colorProp, testprop, municipality, vmin, vmax} = context.hideout;
    const value = feature.properties[colorProp];  // get value the determines the color
    for (let i = 0; i < classes.length; ++i) {
        if (value > classes[i]) {
            style.fillColor = colorscale[i];  // set the fill color according to the class
        }
    }
    return style;
}"""
)
style_spotlight = assign(
    """function(feature, context){
    const {classes, colorscale, style, colorProp, testprop, municipality} = context.hideout;
    const value = feature.properties[testprop];  // get value the determines the color
    // console.log('value: ', value)
    // console.log('municipality: ', municipality)
    for (let i = 0; i < classes.length; ++i) {
        if (value == municipality) {
            style.fillColor = 'rgba( 255, 255, 255, 0.0 )';  // set the fill color according to the class
        } else {
            style.fillColor = 'rgba( 0, 0, 0, 0.8)';  // set the fill color according to the class
        }
    }
    return style;
}"""
)
style_spotlight_wijk = assign(
    """function(feature, context){
    const {classes, colorscale, style, colorProp, testprop, municipality, vmin, vmax} = context.hideout;
    const value = feature.properties[testprop];  // get value the determines the color
    // console.log('value: ', value)
    // console.log('municipality: ', municipality)
    const csc = chroma.scale('YlGn').gamma(2).domain([0, vmax]);  // chroma lib to construct colorscale

    for (let i = 0; i < classes.length; ++i) {
        if (value == municipality) {
            style.color = 'darkgray';  // set the fill color according to the class
            style.fillColor = csc(feature.properties[colorProp]);
            style.fillOpacity = 0.7;
            style.weight = 1;
        } else {
            style.color = 'rgba( 255, 255, 255, 0)';  // set the fill color according to the class
            style.fillColor = 'white';  // set the fill color according to the class
            style.fillOpacity = 0;
            style.weight = 0;
        }
    }
    return style;
}"""
)

style_wijk_stedent = assign(
    """function(feature, context){
    const {colorscale, classes, style, colorProp, testprop, municipality, vmin, vmax} = context.hideout;
    const csc = chroma.scale('YlGn').gamma(2).domain([0, vmax]);  // chroma lib to construct colorscale
    style.color = csc(feature.properties[colorProp]);  // set the fill color according to the class
    style.fillColor = csc(feature.properties[colorProp]);  // set the fill color according to the class
    style.color = 'darkgrey';
    style.fillOpacity = 0.8;
    style.weight = 0.3;
    return style;
}"""
)


# Create geojson.
geojson = dl.GeoJSON(
    data=gemeenten_json,  # geojson data
    style=style_handle,  # how to style each polygon
    zoomToBounds=True,  # when true, zooms to bounds when data changes (e.g. on load)
    zoomToBoundsOnClick=True,  # when true, zooms to bounds of feature (e.g. polygon) on click
    hoverStyle=arrow_function(
        dict(weight=5, color="#666", dashArray="")
    ),  # style applied on hover
    hideout=dict(
        colorscale=colorscale,
        classes=classes,
        style=style,
        colorProp="L0_altieri_1_T",
        testprop="gemeentenaam",
        municipality="",
        vmax=10,
    ),
    # clickData="Hello!",
    id="geojson",
)

# wijken
geojson_wijken = dl.GeoJSON(
    data=wijken_json,  # geojson data
    style=style_wijk_stedent,  # how to style each polygon
    # zoomToBounds=True,  # when true, zooms to bounds when data changes (e.g. on load)
    # zoomToBoundsOnClick=True,  # when true, zooms to bounds of feature (e.g. polygon) on click
    hoverStyle=arrow_function(
        dict(weight=3, color="black", dashArray="")
    ),  # style applied on hover
    hideout=dict(
        colorscale=colorscale_wijken,
        classes=classes,
        style=style_wijk_stedent,
        colorProp="L0_altieri_1_T",
        testprop="gemeentenaam",
        municipality="",
        vmin=0,
        vmax=stedent_max,
    ),
    id="geojson_wijken",
)

# Create info control.
info = html.Div(
    children=get_info(),
    id="info",
    className="info",
    style={"position": "absolute", "bottom": "10px", "right": "10px", "zIndex": "1000"},
)
# Create app.
app = Dash(
    external_scripts=[chroma],
    prevent_initial_callbacks=True,
    external_stylesheets=[dbc.themes.LUX],
)
app.layout = dbc.Container(
    children=[
        html.H1(
            "Urban Amenities Navigator",
            className="text-center",
            style={"padding-top": "1rem"},
        ),
        dl.Map(
            children=[
                dl.Colorbar(
                    colorscale="YlGn",
                    width=30,
                    height=350,
                    min=0,
                    max=10,
                    id="cb",
                    position="bottomleft",
                ),
                dl.TileLayer(
                    url="https://api.maptiler.com/maps/dataviz/{z}/{x}/{y}.png?key=xpqbUuTHIbezz932Aghp"
                ),
                dl.LayersControl(
                    [
                        # dl.BaseLayer(
                        #     dl.TileLayer(
                        #         url="https://api.maptiler.com/maps/dataviz/{z}/{x}/{y}.png?key=xpqbUuTHIbezz932Aghp"
                        #     ),
                        #     name="Gemeenten",
                        #     checked=True,
                        # ),
                        dl.BaseLayer(
                            geojson, name="gemeenten", checked=True, id="gm_layer"
                        ),
                        dl.BaseLayer(
                            geojson_wijken, name="wijken", checked=False, id="wk_layer"
                        ),
                    ],
                    id="lc",
                ),
                # dl.TileLayer(
                #     url="https://api.maptiler.com/maps/dataviz/{z}/{x}/{y}.png?key=xpqbUuTHIbezz932Aghp"
                # ),
                # geojson
                # colorbar,
                info,
            ],
            center=[52.2129919, 5.2793703],
            zoom=7,
            style={
                "height": "70vh",
                "margin": "10px 0px",
                "border": "1px solid black",
            },
        ),
        dbc.Container(
            [
                html.H3("Controls"),
                dbc.Button(
                    "Reset", color="primary", className="me-1", id="btn", value=0
                ),
                dbc.RadioItems(
                    options=[
                        {"label": "Shannon", "value": "shannon"},
                        {"label": "Altieri", "value": "altieri"},
                        {"label": "Leibovici", "value": "leibovici"},
                    ],
                    value="altieri",
                    id="entropy_selector",
                    inline=True,
                    style={"padding": "10px 5px 10px 5px"},
                ),
                dbc.RadioItems(
                    options=[
                        {"label": "Level 0", "value": "0"},
                        {"label": "Level 1", "value": "1"},
                    ],
                    value="0",
                    id="category_selector",
                    inline=True,
                    style={"padding": "10px 5px 10px 5px"},
                ),
                dbc.RadioItems(
                    options=[
                        {"label": "Filter 0", "value": "0"},
                        {"label": "Filter 1", "value": "1"},
                        {"label": "Filter 2", "value": "2"},
                    ],
                    value="1",
                    id="filter_selector",
                    inline=True,
                    style={"padding": "10px 5px 10px 5px"},
                ),
                dbc.RadioItems(
                    options=[
                        {"label": "Transformed", "value": "_T"},
                        {"label": "Normalised", "value": "_norm"},
                    ],
                    value="_T",
                    id="norm_selector",
                    inline=True,
                    style={"padding": "10px 5px 10px 5px"},
                ),
                html.Div(id="wijk_insight", children="", style={"margin-top": "10px"}),
                dbc.Offcanvas(
                    children=[],
                    id="offcanvas-placement",
                    title="Insights",
                    is_open=False,
                    placement="end",
                    style={"width": "70%"},
                ),
            ]
        ),
    ]
)


@app.callback(
    Output("geojson", "hideout", allow_duplicate=True),
    Output("geojson", "style", allow_duplicate=True),
    Output("cb", "max"),
    Output("geojson_wijken", "hideout", allow_duplicate=True),
    Output("geojson_wijken", "style", allow_duplicate=True),
    Input("category_selector", "value"),
    Input("entropy_selector", "value"),
    Input("filter_selector", "value"),
    Input("norm_selector", "value"),
)
def update_filter(cat_value, entropy_value, filter_value, normalize):
    hideout = geojson.__getattribute__("hideout")
    hideout["colorProp"] = f"L{cat_value}_{entropy_value}_{filter_value}{normalize}"
    if normalize == "_norm":
        hideout["vmax"] = 1
        cbmax = 1
    else:
        hideout["vmax"] = 10
        cbmax = 10

    hideout_wk = geojson_wijken.__getattribute__("hideout")
    hideout_wk["colorProp"] = f"L{cat_value}_{entropy_value}_{filter_value}{normalize}"
    if normalize == "_norm":
        hideout_wk["vmax"] = 1
    else:
        hideout_wk["vmax"] = 10

    return hideout, style_handle, cbmax, hideout_wk, style_wijk_stedent


@app.callback(
    Output("info", "children"),
    Input("geojson", "hoverData"),
    Input("geojson_wijken", "hoverData"),
)
def info_hover(feature, feature_wijken):
    if feature_wijken:
        feature = feature_wijken
        hideout = geojson_wijken.__getattribute__("hideout")
    else:
        hideout = geojson.__getattribute__("hideout")
    return get_info(feature, hideout)


@app.callback(
    Output("geojson", "hideout", allow_duplicate=True),
    Output("geojson", "style", allow_duplicate=True),
    Output("geojson_wijken", "hideout", allow_duplicate=True),
    Output("geojson_wijken", "style", allow_duplicate=True),
    Input("btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset(n_clicks):
    if n_clicks:
        hideout = geojson.__getattribute__("hideout")
        hideout_wk = geojson_wijken.__getattribute__("hideout")
        hideout_wk["municipality"] = ""
        hideout["municipality"] = ""
        return hideout, style_handle, hideout_wk, style_wijk_stedent


@app.callback(
    Output("geojson", "hideout", allow_duplicate=True),
    Output("geojson", "style", allow_duplicate=True),
    Output("geojson_wijken", "hideout", allow_duplicate=True),
    Output("geojson_wijken", "style", allow_duplicate=True),
    Input("geojson", "clickData"),
    prevent_initial_call=True,
)
def municipality_click(clickData):
    gm_name = clickData["properties"]["gemeentenaam"]
    hideout = geojson.__getattribute__("hideout")
    hideout["municipality"] = gm_name
    hideout_wk = geojson_wijken.__getattribute__("hideout")
    hideout_wk["municipality"] = hideout["municipality"]

    return hideout, style_spotlight, hideout_wk, style_spotlight_wijk


@app.callback(
    Output("offcanvas-placement", "is_open"),
    Output("offcanvas-placement", "children"),
    # Output("wijk_insight", "children"),
    Input("geojson_wijken", "clickData"),
)
def wijk_click(clickData):
    if clickData:
        gm_naam = clickData["properties"]["gemeentenaam"]
        wijknaam = clickData["properties"]["wijknaam"]
        wijkcode = clickData["properties"]["wijkcode"]
        gdf = wijken[wijken["wijkcode"] == wijkcode]
        df_counts = wijken_counts[wijken_counts["wijkcode"] == wijkcode]

        ####################################################################
        # make horizontal bar plot of the amenities present in the wijk
        L0_counts = df_counts.filter(regex="L0_1.*").sum()

        counts = L0_counts.reset_index()
        counts.columns = ["category", "count"]
        counts.category = counts.category.str.replace("L0_1_count_", "")
        amenity_bar = px.bar(counts, x="count", y="category", orientation="h")

        ####################################################################
        agecols = gdf.filter(regex="P_.*_JR$").columns
        cols_gebnl = gdf.filter(regex="P_GEBNL.*").columns
        cols_gebbl = gdf.filter(regex="P_GEBBL.*").columns

        aantal_inwoners = wijken["AANT_INW"]

        gdf.loc[:, agecols] = gdf.loc[:, agecols].apply(
            lambda x: np.ceil(aantal_inwoners * x / 100)
        )
        gdf.loc[:, cols_gebnl] = gdf.loc[:, cols_gebnl].apply(
            lambda x: np.ceil(aantal_inwoners * x / 100)
        )
        gdf.loc[:, cols_gebbl] = gdf.loc[:, cols_gebbl].apply(
            lambda x: np.ceil(aantal_inwoners * x / 100)
        )

        # make relative bar plot of the amount of mannen en vrouwen
        mv_bar = go.Figure()
        mv_bar.add_trace(
            go.Bar(
                y=["Gender"],
                x=gdf["AANT_MAN"],
                name="Male",
                orientation="h",
                marker=dict(
                    color="rgba(36, 111, 219, 0.4)",
                    line=dict(color="rgba(36, 111, 219, 0.4)"),
                ),
            )
        )
        mv_bar.add_trace(
            go.Bar(
                y=["Gender"],
                x=gdf["AANT_VROUW"],
                name="Female",
                orientation="h",
                marker=dict(
                    color="rgba(245, 40, 145, 0.4)",
                    line=dict(color="rgba(245, 40, 145, 0.4)"),
                ),
            )
        )
        names = ["0-14", "15-24", "25-44", "45-64", "65+"]
        for col, name_ in zip(agecols, names):
            mv_bar.add_trace(
                go.Bar(
                    y=["Age"],
                    x=gdf[col],
                    name=name_ + " years",
                    orientation="h",
                )
            )
        names = [
            "NL born, NL heritage",
            "NL born, EU heritage",
            "NL born, non-EU heritage",
        ]
        for col, name_ in zip(cols_gebnl, names):
            mv_bar.add_trace(
                go.Bar(
                    y=["Birth and heritage"],
                    x=gdf[col],
                    name=name_,
                    orientation="h",
                )
            )
        names = ["Foreign born, EU heritage", "Foreign born, non-EU heritage"]
        for col, name_ in zip(cols_gebbl, names):
            mv_bar.add_trace(
                go.Bar(
                    y=["Birth and heritage"],
                    x=gdf[col],
                    name=name_,
                    orientation="h",
                )
            )
        mv_bar.update_layout(
            barmode="relative",
            # height=250,
            xaxis_autorange=True,
        )
        ####################################################################

        featurelist = [
            "L0_altieri_1_T_norm",
            "L0_altieri_1_T_Is_norm",
            "L1_altieri_1_T_norm",
            "L1_altieri_1_T_Is_norm",
        ]
        distcopy = wijken.copy()
        sample = distcopy[distcopy["wijkcode"] == wijkcode]

        # calculate the distance between the sample and all other wijken, don't use the index
        distcopy["distance"] = np.linalg.norm(
            distcopy[featurelist] - sample[featurelist].values[0], axis=1
        )

        # sort by distance ascending
        similarities = distcopy.sort_values("distance").reset_index(drop=True)

        similarities = similarities[["gemeentenaam", "wijknaam"]].head(6)
        # leave the sample out
        similarities = similarities[similarities["wijknaam"] != wijknaam]
        # rename gemeentenaam, wijknaam to municipality, district
        similarities = similarities.rename(
            columns={"gemeentenaam": "Municipality", "wijknaam": "District"}
        )

        ####################################################################

        return True, [
            html.H3(f"{gm_naam} - {wijknaam}"),
            html.Img(
                src=f"/assets/amenity_plots/wijken/WK077271.png", style={"width": "80%"}
            ),
            html.Hr(
                style={
                    "borderWidth": "0.3vh",
                    "width": "100%",
                    "borderColor": "#000000",
                    "borderStyle": "solid",
                }
            ),
            html.H4("Amenities"),
            dcc.Graph(figure=amenity_bar),
            html.Hr(
                style={
                    "borderWidth": "0.3vh",
                    "width": "100%",
                    "borderColor": "#000000",
                    "borderStyle": "solid",
                }
            ),
            html.H4("Demographics"),
            dcc.Graph(figure=mv_bar),
            html.Hr(
                style={
                    "borderWidth": "0.3vh",
                    "width": "100%",
                    "borderColor": "#000000",
                    "borderStyle": "solid",
                }
            ),
            html.H4("Similar neighbourhoods"),
            # table with similar neighbourhoods
            dash_table.DataTable(similarities.to_dict("records")),
        ]

    return ""


if __name__ == "__main__":
    app.run_server(debug=False)
