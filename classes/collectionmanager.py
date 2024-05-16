from geopandas import GeoDataFrame
import pandas as pd
import shapely
from . import osmapi
from . import gdfbuilder

builder = gdfbuilder.GdfBuilder()
api = osmapi.OSM_API()

categorisation = pd.read_excel("Book3.xlsx")
primary_tags = categorisation["primary tag"].unique()


def _find_primary_tag(x):
    for tag in primary_tags:
        if tag in x:
            return tag


def _categorise_from_tags(x):
    try:
        return categorisation[categorisation["secondary tag"] == x][
            "L0 category"
        ].values[0]
    except:
        return "Uncategorised"


def clean_amenities(gdf, area):

    # Centralise the geometry
    gdf.loc[:, "geometry"] = gdf.loc[:, "geometry"].apply(shapely.centroid)

    # filter out the amenities that are not within the area
    gdf = gdf[gdf.geometry.within(area)]

    gdf.reset_index(drop=True, inplace=True)
    # Extract the primary and secondary tags
    gdf.loc[:, "primary_tag"] = gdf.loc[:, "tags"].apply(lambda x: _find_primary_tag(x))
    print("Primary tags extracted")
    gdf.loc[:, "secondary_tag"] = gdf.loc[:, :].apply(
        lambda x: x.tags.get(x.primary_tag, None), axis=1
    )

    # Categorise the amenities
    gdf.loc[:, "L0_category"] = gdf.loc[:, "secondary_tag"].apply(_categorise_from_tags)
    return gdf


class AmenityManager(GeoDataFrame):

    @property
    def _constructor(self):
        self.to_crs(epsg=4326, inplace=True)
        return AmenityManager

    def _centroid(self):
        self["geometry"] = self.geometry.centroid
        return self

    def _find_primary_tag(self, x):
        for tag in primary_tags:
            if tag in x:
                return tag

    def _extract_tags(self):
        self.loc[:, "primary_tag"] = self["tags"].apply(
            lambda x: self._find_primary_tag(x)
        )
        self.loc[:, "secondary_tag"] = self.apply(
            lambda x: x.tags.get(x.primary_tag, None), axis=1
        )

    def _categorise_L0_from_tags(self, x):
        try:
            return categorisation[categorisation["secondary tag"] == x][
                "L0 category"
            ].values[0]
        except ValueError:
            return "Other"

    def make_L0_categorisation(self):
        self._centroid()
        self._extract_tags()
        return self


class CollectionManager(GeoDataFrame):

    @property
    def _constructor(self):

        self._selected_area = None
        return CollectionManager

    def select_area(self, colname, value):
        self._selected_area = self[self[colname] == value]

    def get_amenities(self):
        if self._selected_area is None:
            return "No area selected"
        data = api.query_amenities(self._selected_area.total_bounds)
        gdf = builder.json_to_gdf(data)
        return clean_amenities(gdf, self._selected_area.geometry.iloc[0])
