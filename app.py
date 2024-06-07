import dash_leaflet as dl
import dash_leaflet.express as dlx
from dash import Dash, html, Output, Input
from dash_extensions.javascript import arrow_function, assign
import dash_bootstrap_components as dbc

import geopandas as gpd
import random
import json

gemeenten = gpd.read_parquet("data/gemeenten_RE.parquet")
# cut off part of the gemeenten
# gemeenten = gemeenten.sample(frac=0.4)
gemeenten["geometry"] = (
    gemeenten.to_crs(gemeenten.estimate_utm_crs()).simplify(100).to_crs(gemeenten.crs)
)
gemeenten_json = json.loads(gemeenten.to_json())

wijken = gpd.read_parquet("data/wijken_stedent.parquet")
# cut off wijken not in gemeenten
wijken = wijken[wijken["gemeentenaam"].isin(gemeenten["gemeentenaam"])]
wijken["geometry"] = (
    wijken.to_crs(wijken.estimate_utm_crs()).simplify(10).to_crs(wijken.crs)
)
wijken_json = json.loads(wijken.to_json())

ent_max = gemeenten["L0_shannon_1"].max()
ent_min = gemeenten["L0_shannon_1"].min()


def get_info(feature=None):
    header = [html.H4("Shannon entropy of municipalities")]
    if not feature:
        return header + [html.P("Hover over a municipality")]
    return header + [
        html.B(feature["properties"]["gemeentenaam"]),
        html.Br(),
        "Shannon = {:.3f}".format(feature["properties"]["L0_shannon_1"]),
    ]


# make classes ranging from 0 to ent_max with 8 steps
classes = [ent_min + (ent_max - ent_min) / 8 * i for i in range(9)]

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

# Geojson rendering logic, must be JavaScript as it is executed in clientside.
style_handle = assign(
    """function(feature, context){
    const {classes, colorscale, style, colorProp, testprop, municipality} = context.hideout;  // get props from hideout
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
    const {classes, colorscale, style, colorProp, testprop, municipality} = context.hideout;  // get props from hideout
    const value = feature.properties[testprop];  // get value the determines the color
    // console.log('value: ', value)
    // console.log('municipality: ', municipality)
    for (let i = 0; i < classes.length; ++i) {
        if (value == municipality) {
            style.fillColor = 'rgba( 255, 255, 255, 0.0 )';  // set the fill color according to the class
        } else {
            style.fillColor = 'rgba( 0, 0, 0, 1)';  // set the fill color according to the class
        }
    }
    return style;
}"""
)
style_spotlight_wijk = assign(
    """function(feature, context){
    const {classes, colorscale, style, colorProp, testprop, municipality} = context.hideout;  // get props from hideout
    const value = feature.properties[testprop];  // get value the determines the color
    // console.log('value: ', value)
    // console.log('municipality: ', municipality)
    for (let i = 0; i < classes.length; ++i) {
        if (value == municipality) {
            style.color = 'darkgray';  // set the fill color according to the class
        } else {
            style.color = 'rgba( 255, 255, 255, 0)';  // set the fill color according to the class
        }
    }
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
        colorProp="L0_shannon_1",
        testprop="gemeentenaam",
        municipality="",
    ),
    # clickData="Hello!",
    id="geojson",
)

# wijken
geojson_wijken = dl.GeoJSON(
    data=wijken_json,  # geojson data
    style=style_handle,  # how to style each polygon
    # zoomToBounds=True,  # when true, zooms to bounds when data changes (e.g. on load)
    # zoomToBoundsOnClick=True,  # when true, zooms to bounds of feature (e.g. polygon) on click
    # hoverStyle=arrow_function(
    #     dict(weight=5, color="#666", dashArray="")
    # ),  # style applied on hover
    hideout=dict(
        colorscale=colorscale,
        classes=classes,
        style=style_wijk,
        colorProp="sted/entropy",
        testprop="gemeentenaam",
        municipality="",
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
app = Dash(prevent_initial_callbacks=True)
app.layout = dbc.Container(
    children=[
        dl.Map(
            children=[
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
                        dl.Overlay(
                            geojson_wijken, name="wijken", checked=False, id="wk_layer"
                        ),
                    ],
                    id="lc",
                ),
                # dl.TileLayer(
                #     url="https://api.maptiler.com/maps/dataviz/{z}/{x}/{y}.png?key=xpqbUuTHIbezz932Aghp"
                # ),
                # geojson
                colorbar,
                info,
            ],
            center=[52.2129919, 5.2793703],
            zoom=7,
            style={
                "height": "80vh",
            },
        ),
        dbc.Button("Reset", color="primary", className="me-1", id="btn", value=0),
    ]
)


@app.callback(Output("info", "children"), Input("geojson", "hoverData"))
def info_hover(feature):
    return get_info(feature)


# @app.callback(
#     Output("geojson_wijken", "hideout"),
#     Output("geojson_wijken", "style"),
#     Input("wk_layer", "checked"),
#     Input("geojson_wijken", "hideout"),
#     Input("geojson", "hideout"),
# )
# def wijken_focus(checked, hideout_wk, hideout_gm):
#     if checked:
#         print("focussing wijken")
#         print("municipality == '': ", hideout_gm["municipality"] == "")
#         hideout_wk["municipality"] = hideout_gm["municipality"]
#         return hideout_wk, style_spotlight_wijk
#     else:
#         print("not focussing wijken")
#         return hideout_wk, style_wijk


@app.callback(
    Output("geojson", "hideout", allow_duplicate=True),
    Output("geojson", "style", allow_duplicate=True),
    Output("geojson_wijken", "hideout", allow_duplicate=True),
    Output("geojson_wijken", "style", allow_duplicate=True),
    # Input("geojson", "hideout"),
    # Input("btn", "value"),
    Input("btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset(n_clicks):
    if n_clicks:
        hideout = geojson.__getattribute__("hideout")
        hideout_wk = geojson_wijken.__getattribute__("hideout")
        hideout_wk["municipality"] = ""
        hideout["municipality"] = ""
        return hideout, style_handle, hideout_wk, style_wijk


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


if __name__ == "__main__":
    app.run_server(debug=True)
