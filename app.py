import dash_leaflet as dl
import dash_leaflet.express as dlx
from dash import Dash, html, Output, Input
from dash_extensions.javascript import arrow_function, assign
import dash_bootstrap_components as dbc

import geopandas as gpd
import json

# load datasets
gemeenten = gpd.read_parquet("data/gemeenten_RE.parquet")
wijken = gpd.read_parquet("data/wijken_stedent.parquet")

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


def get_info(feature=None):
    header = [html.H4("Shannon entropy of municipalities")]
    if not feature:
        return header + [html.P("Hover over a municipality")]
    return header + [
        html.B(feature["properties"]["gemeentenaam"]),
        html.Br(),
        "Shannon = {:.3f}".format(feature["properties"]["L0_shannon_1"]),
    ]


# ----------- wijken colorscale ------------
colorscale_wijken = "Virdis"
colorbar_wijken = dl.Colorbar(
    colorscale=colorscale_wijken, width=20, height=150, min=0, max=stedent_max
)


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

# chromalib
chroma = "https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.4.2/chroma.min.js"  # js lib used for colors


# Geojson rendering logic, must be JavaScript as it is executed in clientside.
style_handle = assign(
    """function(feature, context){
    const {classes, colorscale, style, colorProp, testprop, municipality} = context.hideout;  // get props
    const value = feature.properties[colorProp];  // get value the determines the color
    for (let i = 0; i < classes.length; ++i) {
        if (value > classes[i]) {
            style.fillColor = colorscale[i];  // set the fill color according to the class
        }
    }
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
        colorProp="sted/entropy",
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
app = Dash(external_scripts=[chroma], prevent_initial_callbacks=True)
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
                        dl.Overlay(
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
        html.Div(id="wijk_insight", children="", style={"margin-top": "10px"}),
    ]
)


@app.callback(Output("info", "children"), Input("geojson", "hoverData"))
def info_hover(feature):
    return get_info(feature)


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
    Output("wijk_insight", "children"),
    Input("geojson_wijken", "clickData"),
)
def wijk_click(clickData):
    if clickData:

        return clickData["properties"]["wijknaam"]
    return ""


if __name__ == "__main__":
    app.run_server(debug=True)
