from dash import Dash
import geopandas as gpd
from dash import Input, Output, dcc, html, State, dash_table
import dash_leaflet as dl
import shapely
import json

import plotly.colors as pc
import numpy as np

app = Dash()
app.layout = html.Div(
    children=[
        dl.Map(
            children=[
                dl.TileLayer(
                    url="https://api.maptiler.com/maps/dataviz/{z}/{x}/{y}.png?key=xpqbUuTHIbezz932Aghp",
                ),
                dl.LayerGroup(id="polygons", n_clicks=0),
            ],
            center=[52.2129919, 5.2793703],
            zoom=7,
            style={"height": "80vh", "width": "70vw"},
            id="map",
        ),
        html.Button("Fly to Paris", id="btn"),
        html.Div(id="somebox"),
    ]
)


# @app.callback(
#     Output("map", "viewport"), Input("polygons", "n_clicks"), prevent_initial_call=True
# )
# def fly_to_paris(feature):
#     print(feature)
#     return dict(center=[52.2129919, 5.2793703], zoom=10, transition="flyTo")


@app.callback(
    Output("somebox", "children"),
    [Input("geojson", "clickData")],
    prevent_initial_call=True,
)
def capital_click(feature):
    if feature is not None:
        return html.H1(f"You clicked {feature['properties']['gemeentenaam']}")


def get_color_from_colorscale(value, colorscale, vmin=0, vmax=1):
    """
    Returns the color from a Plotly colorscale based on the input value.

    Parameters:
    - value: The input value for which the color needs to be found.
    - colorscale: A Plotly colorscale (list of [value, color] pairs).
    - vmin: Minimum value of the input range (default is 0).
    - vmax: Maximum value of the input range (default is 1).

    Returns:
    - color: The color corresponding to the input value in the colorscale.
    """

    # Normalize the value to be within [0, 1]
    norm_value = (value - vmin) / (vmax - vmin)
    norm_value = min(max(norm_value, 0), 1)  # Ensure the value is within [0, 1]

    len_colorscale = len(colorscale)
    cutoffs = np.linspace(0, 1, len_colorscale)

    lowcolor = None
    highcolor = None
    # find the two closest cutoffs
    for i in range(len_colorscale):
        if cutoffs[i] <= norm_value <= cutoffs[i + 1]:
            lowcolor = colorscale[i]
            highcolor = colorscale[i + 1]
            break

    # Use the get_continuous_color function to get the color
    color = pc.find_intermediate_color(
        lowcolor=lowcolor, highcolor=highcolor, intermed=norm_value, colortype="rgb"
    )

    return color


def stylef(feature):
    vmin = 0
    vmax = 8
    colorscale = pc.sequential.Oryel
    print(feature["features"].keys())
    fillcolor = get_color_from_colorscale(
        feature["features"]["RE_L0_1"], colorscale, vmin, vmax
    )
    weight = 2
    opacity = 1
    color = "white"
    dashArray = "3"
    fillOpacity = 0.7
    print(
        {
            "fillColor": fillcolor,
            "color": color,
            "weight": weight,
            "opacity": opacity,
            "fillOpacity": fillOpacity,
            "dashArray": dashArray,
        }
    )
    return {
        "fillColor": fillcolor,
        "color": color,
        "weight": weight,
        "opacity": opacity,
        "fillOpacity": fillOpacity,
        "dashArray": dashArray,
    }


@app.callback(
    Output("polygons", "children"),
    Input("map", "click_lat_lng"),
)
def update_map(click_lat_lng):
    gemeenten = gpd.read_parquet("data/gemeenten_RE_colors.parquet")
    # gemeenten.loc[:, "geometry"] = gemeenten.geometry.map(
    #     lambda polygon: shapely.ops.transform(lambda x, y: (y, x), polygon)
    # )

    # gemeenten.loc[:, "geopoints"] = gemeenten.loc[:, "geometry"].apply(
    #     lambda x: shapely.geometry.mapping(x)["coordinates"][0]
    # )

    map_geojson = dl.GeoJSON(
        data=json.loads(gemeenten.to_json()),
        zoomToBounds=True,
        zoomToBoundsOnClick=True,
        id="geojson",
    )

    return map_geojson

    # polygons = []
    # for _, row in gemeenten.iterrows():

    #     if type(row.geometry) is shapely.geometry.multipolygon.MultiPolygon:
    #         for polygon in row.geometry.geoms:
    #             polygons.append(
    #                 dl.Polygon(
    #                     positions=shapely.geometry.mapping(polygon)["coordinates"][0],
    #                     children=[dl.Tooltip(content=f"{row.gemeentenaam}")],
    #                     color=row.color,
    #                     opacity=1,
    #                     fillOpacity=0.9,
    #                     id=f"{row.gemeentenaam}_polygon",
    #                 )
    #             )
    #     else:
    #         polygons.append(
    #             dl.Polygon(
    #                 positions=shapely.geometry.mapping(row.geometry)["coordinates"][0],
    #                 children=[dl.Tooltip(content=f"{row.gemeentenaam}")],
    #                 color=row.color,
    #                 opacity=1,
    #                 fillOpacity=0.9,
    #             )
    #         )

    # return polygons


if __name__ == "__main__":
    app.run_server(debug=True)
    update_map()
