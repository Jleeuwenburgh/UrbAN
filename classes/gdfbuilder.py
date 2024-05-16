import geopandas as gpd
import pandas as pd
import shapely


class GdfBuilder:

    def __init__(self) -> None:
        pass

    def _build_geom_node(self, node):
        """
        This function is used to build the geometry column of a relation entity
        """

        return shapely.geometry.Point(node["lon"], node["lat"])

    def _build_geom_way(self, way):
        """
        This function is used to build the geometry column of a relation entity
        """

        # if way is closed, build polygon
        if way["nodes"][0] == way["nodes"][-1]:
            return shapely.geometry.Polygon(
                [(node["lon"], node["lat"]) for node in way["geometry"]]
            )
        # if way is open, build line
        if way["nodes"][0] != way["nodes"][-1]:
            return shapely.geometry.LineString(
                [(node["lon"], node["lat"]) for node in way["geometry"]]
            )

    def _build_geom_relation(self, relation):
        """
        This function is used to build the geometry column of a relation entity
        """

        # check if geometry is available
        try:
            relation["members"][0]["geometry"]
        except KeyError:
            return None

        # if relation is closed, build polygon
        if (
            relation["members"][0]["geometry"][0]
            == relation["members"][0]["geometry"][-1]
        ):
            return shapely.geometry.Polygon(
                [
                    (node["lon"], node["lat"])
                    for node in relation["members"][0]["geometry"]
                ]
            )
        # if relation is open, build line
        if (
            relation["members"][0]["geometry"][0]
            != relation["members"][0]["geometry"][-1]
        ):
            return shapely.geometry.LineString(
                [
                    (node["lon"], node["lat"])
                    for node in relation["members"][0]["geometry"]
                ]
            )

    def json_to_gdf(self, data):
        """This function is used to convert the query response of the API to a geodataframe

        Args:
            data (dict): the query response of the API
        """

        # check if there is data
        if not data["elements"]:
            return gpd.GeoDataFrame()

        df = pd.DataFrame(data["elements"])  # build df from data

        # get uniquee types and split df based on type
        available_types = df["type"].unique()
        dfs_by_type = {type: df[df["type"] == type] for type in available_types}

        # apply correct 'build geometry' function based on type
        for type, type_df in dfs_by_type.items():
            type_df.loc[:, "geometry"] = type_df.apply(
                eval(f"self._build_geom_{type}"), axis=1
            )

        # concat all dfs and convert to gdf
        df = pd.concat(dfs_by_type.values(), ignore_index=True)
        return gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
