import matplotlib.pyplot as plt
import geopandas as gpd


def plot_area(gdf_area, gdf_pts, gdf_blds_i, gdf_blds_o):

    fig, ax = plt.subplots(figsize=(24, 10))

    # plot the boundaries of the wijk
    gdf_area.boundary.plot(ax=ax, color="black")

    # plot the buildings
    # gdf_blds_i.plot(ax=ax, color="black", alpha=0.5)
    # gdf_blds_o.plot(ax=ax, color="gray", alpha=0.5)

    # plot the points
    # gdf_pts.plot(
    #     ax=ax, column="L0_category", legend=True, legend_kwds={"loc": "upper left"}
    # )

    # no axis
    ax.axis("off")

    # set tight layout
    plt.tight_layout()

    # save the figure as a png
    plt.savefig("assets/area_plot.png", dpi=300)
