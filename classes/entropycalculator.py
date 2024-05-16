import pandas as pd
import geopandas as gpd
import shapely
import shapely.geometry
from spatialentropy import altieri_entropy, leibovici_entropy
from scipy.stats import entropy
import numpy as np
import gc
from numpy import AxisError


# import shapely.geometry
from . import osmapi
from . import gdfbuilder

builder = gdfbuilder.GdfBuilder()
api = osmapi.OSM_API()

# ------- CONSTANTS -------#

# categorisation
CATEGORISATION = pd.read_excel("data/categorisation.xlsx")

# cleaning
COLS_TO_KEEP = ["type", "tags", "geometry"]

# ----------- FILTER 0 ------------#
L0_BLACKLIST = [
    "Uncategorised",
]
L1_BLACKLIST = {}
# ---------------------------------#

# ----------- FILTER 1 ------------#
# L0_BLACKLIST = [
#     "Uncategorised",
#     "Private transportation",
#     "Facilities",
#     "Waste management",
# ]
# L1_BLACKLIST = {
#     "Healthcare": ["Healthcare_Other"],
#     "Shopping": ["Shopping_Other"],
#     "Public service": ["PS_Other"],
# }
# ---------------------------------#

# ----------- FILTER 2 ------------#
# L0_BLACKLIST = [
#     "Uncategorised",
#     "Private transportation",
#     "Facilities",
#     "Waste management",
#     "Financial",
# ]
# L1_BLACKLIST = {
#     "Healthcare": ["Healthcare_Other"],
#     "Entertainment, arts and culture": ["EAC_Other"],
#     "Shopping": [
#         "Shopping_Other",
#         "Clothing and accessoires",
#         "Crafts",
#         "House and interior",
#         "Media, appliances and hardware",
#         "Mobility",
#     ],
#     "Public service": ["PS_Other"],
# }
# ---------------------------------#


def getfilter(filter_i):
    assert filter_i in [0, 1, 2], "Filter number must be 0, 1 or 2"
    # ----------- FILTER 0 ------------#
    if filter_i == 0:
        L0_BLACKLIST = [
            "Uncategorised",
        ]
        L1_BLACKLIST = {}
    # ---------------------------------#

    # ----------- FILTER 1 ------------#
    if filter_i == 1:
        L0_BLACKLIST = [
            "Uncategorised",
            "Private transportation",
            "Facilities",
            "Waste management",
        ]
        L1_BLACKLIST = {
            "Healthcare": ["Healthcare_Other"],
            "Shopping": ["Shopping_Other"],
            "Public service": ["PS_Other"],
        }
    # ---------------------------------#

    # ----------- FILTER 2 ------------#
    if filter_i == 2:
        L0_BLACKLIST = [
            "Uncategorised",
            "Private transportation",
            "Facilities",
            "Waste management",
            "Financial",
        ]
        L1_BLACKLIST = {
            "Healthcare": ["Healthcare_Other"],
            "Entertainment, arts and culture": ["EAC_Other"],
            "Shopping": [
                "Shopping_Other",
                "Clothing and accessoires",
                "Crafts",
                "House and interior",
                "Media, appliances and hardware",
                "Mobility",
            ],
            "Public service": ["PS_Other"],
        }
    # ---------------------------------#
    return (L0_BLACKLIST, L1_BLACKLIST)


def find_primary_tag(x):
    for tag in CATEGORISATION["primary tag"].unique():
        if tag in x:
            return tag


def _extract_tags(gdf):
    if gdf.empty:
        return gdf
    gdf.loc[:, "primary_tag"] = gdf.loc[:, "tags"].apply(lambda x: find_primary_tag(x))
    try:
        gdf.loc[:, "secondary_tag"] = gdf.apply(
            lambda x: x.tags.get(x.primary_tag, None),
            axis=1,
        )
    except ValueError:
        print("ValueError, Saving to file")
        gdf.to_parquet("errors/error.gdf")
        gdf.loc[:, "secondary_tag"] = "Uncategorised"
    return gdf


def _clean_amenities(gdf, area):
    # Centralise the geometry
    gdf.loc[:, "geometry"] = gdf.loc[:, "geometry"].apply(shapely.centroid)

    # filter out the amenities that are not within the area
    gdf = gdf[gdf.geometry.within(area)]

    # filter out the columns that are not needed
    gdf = gdf[COLS_TO_KEEP]

    gdf.reset_index(drop=True, inplace=True)

    return gdf


def _categorise_L0(x):
    primary = x.primary_tag
    secondary = x.secondary_tag
    try:
        return CATEGORISATION.loc[:, "L0 category"][
            (CATEGORISATION["primary tag"] == primary)
            & (CATEGORISATION["secondary tag"] == secondary)
        ].values[0]
    except IndexError:
        return "Uncategorised"


def _categorise_L1(x):
    secondary = x.secondary_tag
    l0 = x.L0_category
    try:
        return CATEGORISATION.loc[:, "L1 category"][
            (CATEGORISATION["secondary tag"] == secondary)
            & (CATEGORISATION["L0 category"] == l0)
        ].values[0]
    except IndexError:
        return "Uncategorised"


def _categorise_amenities(gdf):
    gdf.loc[:, "L0_category"] = gdf.loc[:, ["primary_tag", "secondary_tag"]].apply(
        _categorise_L0, axis=1
    )
    gdf.loc[:, "L1_category"] = gdf.loc[:, ["secondary_tag", "L0_category"]].apply(
        _categorise_L1, axis=1
    )
    return gdf


def _filter_uncategorised_L0(gdf):
    return gdf[gdf.L0_category != "Uncategorised"]


def _filter_uncategorised_L1(gdf):
    return gdf[gdf.L1_category != "Uncategorised"]


def _filter_uncategorised(gdf):
    gdf = _filter_uncategorised_L0(gdf)
    gdf = _filter_uncategorised_L1(gdf)
    return gdf


# def _points_to_tuples(gdf):
#     gdf.loc[:, "tupled_geom"] = gdf.loc[:, "geometry"].apply(lambda x: (x.x, x.y))
#     return gdf


def _points_to_2darray(gdf):
    return [[point.x, point.y] for point in gdf.geometry]


def _get_shannon_entropy(labels, base=2):
    # get the total count of the labels
    total_count = len(labels)
    # get the unique labels and their counts
    _, label_counts = np.unique(labels, return_counts=True)

    probs = label_counts / total_count
    # get the entropy
    return entropy(probs, base=base)


def calculate_entropies_fromapi(area):
    assert isinstance(
        area,
        (shapely.geometry.multipolygon.MultiPolygon, shapely.geometry.polygon.Polygon),
    ), "Area must be a shapely Polygon or MultiPolygon"

    # get the amenity data from the OSM API and convert it to a GeoDataFrame
    data = api.query_amenities(shapely.total_bounds(area))
    gdf = builder.json_to_gdf(data)

    if gdf.empty:
        return [0, 0, 0, 0, 0, 0]

    # clean the data
    gdf = _clean_amenities(gdf, area)

    if gdf.empty:
        return [0, 0, 0, 0, 0, 0]

    # Extract primary and secondary tags
    gdf = _extract_tags(gdf)

    # categorise the amenities
    gdf = _categorise_amenities(gdf)

    # filter out the uncategorised amenities
    gdf = _filter_uncategorised(gdf)

    # filter out prespecified categories
    gdf = gdf[~gdf.L0_category.isin(L0_BLACKLIST)]
    if L1_BLACKLIST:
        for key, value in L1_BLACKLIST.items():
            gdf = gdf[~((gdf.L0_category == key) & (gdf.L1_category.isin(value)))]

    points = _points_to_2darray(gdf)

    L0 = gdf.loc[:, "L0_category"].values
    L1 = gdf.loc[:, "L1_category"].values

    try:
        L0_entropy_shannon = _get_shannon_entropy(L0, base=2)
        L1_entropy_shannon = _get_shannon_entropy(L1, base=2)
        L0_entropy_altieri = altieri_entropy(points, L0, base=2).entropy
        L1_entropy_altieri = altieri_entropy(points, L1, base=2).entropy
        L0_entropy_leibovici = leibovici_entropy(points, L0, base=2).entropy
        L1_entropy_leibovici = leibovici_entropy(points, L1, base=2).entropy
    except AxisError:
        print("AxisError", gdf.head(10))
        return [0, 0, 0, 0, 0, 0]
    except ValueError:
        print("ValueError", gdf.head(10))
        return [0, 0, 0, 0, 0, 0]

    # collect the garbage to free up memory
    del data, gdf, points, L0, L1
    gc.collect()

    return [
        L0_entropy_shannon,
        L1_entropy_shannon,
        L0_entropy_altieri,
        L1_entropy_altieri,
        L0_entropy_leibovici,
        L1_entropy_leibovici,
    ]


def calculate_entropies(area, gm_name, entropy_types, filter_i):

    legal_entropy_types = [
        "L0_shannon",
        "L1_shannon",
        "L0_altieri",
        "L1_altieri",
        "L0_leibovici",
        "L1_leibovici",
    ]
    for et in entropy_types:
        assert (
            et in legal_entropy_types
        ), f"Entropy type {et} is not a legal entropy type"

    # get filters
    L0_BLACKLIST, L1_BLACKLIST = getfilter(filter_i)

    # gather amenities
    amenity_gdf = gpd.read_parquet(f"data/gm_amenities/amenities_{gm_name}.parquet")
    amenity_gdf = amenity_gdf[amenity_gdf.within(area)]

    if amenity_gdf.empty:
        return [0] * len(entropy_types)

    # apply filters
    amenity_gdf = amenity_gdf[~amenity_gdf.L0_category.isin(L0_BLACKLIST)]
    if L1_BLACKLIST:
        for key, value in L1_BLACKLIST.items():
            amenity_gdf = amenity_gdf[
                ~(
                    (amenity_gdf.L0_category == key)
                    & (amenity_gdf.L1_category.isin(value))
                )
            ]

    if amenity_gdf.empty:
        return [0] * len(entropy_types)

    L0 = amenity_gdf.loc[:, "L0_category"].values
    L1 = amenity_gdf.loc[:, "L1_category"].values

    # points = amenity_gdf.points_tup.values
    points = [[point.x, point.y] for point in amenity_gdf.geometry]
    calculated_entropies = []

    for entropy_type in entropy_types:
        cat, enttype = entropy_type.split("_")
        if enttype == "shannon":
            calculated_entropies.append(_get_shannon_entropy(eval(cat), base=2))
        elif enttype == "altieri":
            calculated_entropies.append(
                altieri_entropy(points, eval(cat), base=2).entropy
            )
        elif enttype == "leibovici":
            calculated_entropies.append(
                leibovici_entropy(points, eval(cat), base=2).entropy
            )

    return calculated_entropies


def calculate_entropies_fromapi_no_leibo(area):
    assert isinstance(
        area,
        (shapely.geometry.multipolygon.MultiPolygon, shapely.geometry.polygon.Polygon),
    ), "Area must be a shapely Polygon or MultiPolygon"

    # get the amenity data from the OSM API and convert it to a GeoDataFrame
    data = api.query_amenities(shapely.total_bounds(area))
    gdf = builder.json_to_gdf(data)

    if gdf.empty:
        return [0, 0, 0, 0]

    # clean the data
    gdf = _clean_amenities(gdf, area)

    if gdf.empty:
        return [0, 0, 0, 0]

    # Extract primary and secondary tags
    gdf = _extract_tags(gdf)

    # categorise the amenities
    gdf = _categorise_amenities(gdf)

    # filter out the uncategorised amenities
    gdf = _filter_uncategorised(gdf)

    # filter out prespecified categories
    gdf = gdf[~gdf.L0_category.isin(L0_BLACKLIST)]
    # for key, value in L1_BLACKLIST.items():
    #     gdf = gdf[~((gdf.L0_category == key) & (gdf.L1_category.isin(value)))]

    points = _points_to_2darray(gdf)

    L0 = gdf.loc[:, "L0_category"].values
    L1 = gdf.loc[:, "L1_category"].values

    try:
        L0_entropy_shannon = _get_shannon_entropy(L0, base=2)
        L1_entropy_shannon = _get_shannon_entropy(L1, base=2)
        L0_entropy_altieri = altieri_entropy(points, L0, base=2).entropy
        L1_entropy_altieri = altieri_entropy(points, L1, base=2).entropy
    except AxisError:
        print("AxisError", gdf.head(10))
        return [0, 0, 0, 0]
    except ValueError:
        print("ValueError", gdf.head(10))
        return [0, 0, 0, 0]

    # collect the garbage to free up memory
    del data, gdf, points, L0, L1
    gc.collect()

    return [
        L0_entropy_shannon,
        L1_entropy_shannon,
        L0_entropy_altieri,
        L1_entropy_altieri,
    ]


def return_categorised_amenities(area):
    assert isinstance(
        area,
        (shapely.geometry.multipolygon.MultiPolygon, shapely.geometry.polygon.Polygon),
    ), "Area must be a shapely Polygon or MultiPolygon"

    # get the amenity data from the OSM API and convert it to a GeoDataFrame
    data = api.query_amenities(shapely.total_bounds(area))
    gdf = builder.json_to_gdf(data)

    # clean the data
    gdf = _clean_amenities(gdf, area)

    if gdf.empty:
        return gdf

    # Extract primary and secondary tags
    gdf = _extract_tags(gdf)

    # categorise the amenities
    gdf = _categorise_amenities(gdf)

    # filter out the uncategorised amenities
    gdf = _filter_uncategorised(gdf)

    # filter out prespecified categories
    gdf = gdf[~gdf.L0_category.isin(L0_BLACKLIST)]
    if L1_BLACKLIST:
        for key, value in L1_BLACKLIST.items():
            gdf = gdf[~((gdf.L0_category == key) & (gdf.L1_category.isin(value)))]

    return gdf


def return_buildings(area):
    assert isinstance(
        area,
        (shapely.geometry.multipolygon.MultiPolygon, shapely.geometry.polygon.Polygon),
    ), "Area must be a shapely Polygon or MultiPolygon"

    # get the amenity data from the OSM API and convert it to a GeoDataFrame
    data = api.query_buildings(shapely.total_bounds(area))
    gdf = builder.json_to_gdf(data)

    outer = gdf[~gdf.geometry.within(area)]
    inner = gdf[gdf.geometry.within(area)]

    return outer, inner
