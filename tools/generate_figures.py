"""v2 Bermuda figures — real maps via geopandas + publication-quality matplotlib charts."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams

import geopandas as gpd
import numpy as np

OUT = Path("C:/bermuda-manual/chapters/assets/shared")
OUT.mkdir(parents=True, exist_ok=True)

# Publication theme (Russell-clean, serif)
rcParams.update({
    "font.family": "serif",
    "font.serif": ["Georgia", "Times New Roman", "DejaVu Serif"],
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.labelcolor": "#333",
    "axes.edgecolor": "#444",
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": "#cccccc",
    "grid.linestyle": ":",
    "grid.linewidth": 0.5,
    "grid.alpha": 0.7,
    "xtick.color": "#444",
    "ytick.color": "#444",
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.frameon": False,
    "legend.fontsize": 10,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "figure.dpi": 144,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})

ACCENT = "#5B7C99"
ACCENT2 = "#A8B5C1"
ACCENT3 = "#7E96AE"
ACCENT4 = "#3E5970"
ACCENT5 = "#C9A875"
PALETTE = [ACCENT, ACCENT4, ACCENT5, ACCENT3, ACCENT2]


def save(fig, name):
    fig.savefig(OUT / name, facecolor="white")
    plt.close(fig)
    print(f"wrote {OUT / name}")


# --- Map: parishes ---
def parish_map():
    gdf = gpd.read_file(OUT / "bermuda-parishes.geojson").to_crs(epsg=4326)
    name_field = next((c for c in ("name", "NAME", "Name") if c in gdf.columns), "name")
    palette = ["#D9C9A6", "#C6E0D5", "#E1CDD0", "#CFD8E3", "#E5DABA",
               "#D3C7E6", "#C5D9BD", "#E0CFCF", "#B4C7D6"]
    gdf = gdf.sort_values(name_field).reset_index(drop=True)
    gdf["color"] = [palette[i % len(palette)] for i in range(len(gdf))]
    fig, ax = plt.subplots(figsize=(9, 5), dpi=144)
    gdf.plot(ax=ax, color=gdf["color"], edgecolor="#444", linewidth=0.6)
    for _, row in gdf.iterrows():
        # Use representative point — works for both Polygon and MultiPolygon
        cx, cy = row.geometry.representative_point().x, row.geometry.representative_point().y
        ax.annotate(row[name_field], xy=(cx, cy),
                    ha="center", va="center", fontsize=9,
                    color="#222", fontweight="bold")
    ax.set_axis_off()
    ax.set_aspect("equal")
    # Title and source line
    fig.suptitle("Bermuda's nine traditional parishes", y=0.97,
                 fontsize=13, fontweight="bold", color="#222")
    ax.text(0.5, -0.02,
            "Boundaries from OpenStreetMap (© OSM contributors, ODbL).",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=8, color="#666", fontstyle="italic")
    save(fig, "parish-map.png")  # Replace SVG with PNG (real geometry)


# --- Map: ferry routes (parish polygons faded + Hamilton hub + 4 routes) ---
def ferry_routes():
    gdf = gpd.read_file(OUT / "bermuda-parishes.geojson").to_crs(epsg=4326)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=144)
    gdf.plot(ax=ax, color="#EFE6D2", edgecolor="#999", linewidth=0.4,
             alpha=0.85)
    # Hamilton hub coords (City of Hamilton on harbour edge of Pembroke)
    hamilton = (-64.7790, 32.2949)
    # Endpoint approximations (lon, lat)
    endpoints = [
        ("Dockyard (West End)",     -64.8395, 32.3261, ACCENT, "Blue"),
        ("Rockaway",                -64.7050, 32.2530, ACCENT3, "Pink"),
        ("Salt Kettle / Hinson's", -64.7950, 32.2890, ACCENT5, "Green"),
        ("St George's (East End)", -64.6790, 32.3835, ACCENT4, "Orange"),
    ]
    for name, lon, lat, col, route in endpoints:
        ax.plot([hamilton[0], lon], [hamilton[1], lat],
                color=col, linewidth=2.0, linestyle=(0, (4, 2)))
        ax.scatter([lon], [lat], color=col, s=42, zorder=4,
                   edgecolor="white", linewidth=1)
        ax.annotate(name, xy=(lon, lat),
                    xytext=(lon + 0.005, lat + 0.005),
                    fontsize=9, color="#222", fontweight="bold")
        # Route label at midpoint
        mx, my = (hamilton[0] + lon) / 2, (hamilton[1] + lat) / 2
        ax.annotate(route, xy=(mx, my), fontsize=8,
                    color=col, fontstyle="italic")
    ax.scatter([hamilton[0]], [hamilton[1]], color="#222", s=80, zorder=5,
               edgecolor="white", linewidth=1.5)
    ax.annotate("Hamilton", xy=hamilton,
                xytext=(hamilton[0], hamilton[1] - 0.012),
                fontsize=11, ha="center", color="#222", fontweight="bold")
    ax.set_axis_off()
    ax.set_aspect("equal")
    fig.suptitle("Bermuda ferry routes from Hamilton",
                 y=0.96, fontsize=13, fontweight="bold", color="#222")
    ax.text(0.5, -0.02,
            "Schematic; endpoints approximate. Boundaries © OSM contributors, ODbL.",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=8, color="#666", fontstyle="italic")
    save(fig, "ferry-routes.png")


# --- Climate ---
def climate_chart():
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
              "Aug", "Sep", "Oct", "Nov", "Dec"]
    temp_high = [20, 20, 21, 22, 24, 27, 29, 30, 29, 27, 24, 21]
    temp_low =  [16, 15, 16, 17, 19, 22, 24, 25, 25, 23, 20, 17]
    rain_mm =   [115, 114, 121, 112, 106, 117, 113, 144, 132, 147, 108, 102]
    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax1.fill_between(months, temp_low, temp_high, color=ACCENT, alpha=0.18,
                     label="Temperature range")
    ax1.plot(months, temp_high, color=ACCENT, linewidth=2, marker="o",
             markersize=4, label="High")
    ax1.plot(months, temp_low, color=ACCENT4, linewidth=2, marker="s",
             markersize=4, label="Low")
    ax1.set_ylabel("Temperature (°C)")
    ax1.set_ylim(0, 35)
    ax1.legend(loc="upper left", ncol=3)
    ax2 = ax1.twinx()
    ax2.bar(months, rain_mm, color=ACCENT5, alpha=0.40, width=0.65,
            edgecolor="white", linewidth=0.5)
    ax2.set_ylabel("Rainfall (mm)")
    ax2.set_ylim(0, 250)
    ax2.spines["top"].set_visible(False)
    ax2.grid(False)
    fig.suptitle("Monthly temperature and rainfall in Bermuda",
                 fontsize=13, fontweight="bold", color="#222")
    save(fig, "climate-chart.png")


def gdp_pie():
    labels = ["International business", "Government & utilities",
              "Retail & services", "Tourism", "Other"]
    sizes = [37, 14, 22, 6, 21]
    fig, ax = plt.subplots(figsize=(7, 5))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.0f%%", startangle=90,
        colors=PALETTE, wedgeprops={"edgecolor": "white", "linewidth": 2},
        textprops={"color": "#222", "fontsize": 11},
        pctdistance=0.78,
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontweight("bold")
    ax.set_aspect("equal")
    fig.suptitle("Bermuda GDP composition by sector",
                 fontsize=13, fontweight="bold", color="#222")
    save(fig, "gdp-pie.png")


def population_line():
    years = [1950, 1960, 1970, 1980, 1990, 2000, 2010, 2016, 2020, 2024]
    pop = [38000, 44000, 54000, 56000, 59000, 62000, 64000, 65000, 64054, 63000]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(years, pop, color=ACCENT, linewidth=2.4, marker="o", markersize=5,
            markerfacecolor="white", markeredgewidth=1.5, markeredgecolor=ACCENT)
    ax.fill_between(years, pop, alpha=0.12, color=ACCENT)
    ax.set_ylabel("Population")
    ax.set_xlabel("Year")
    ax.set_ylim(30000, 70000)
    ax.yaxis.set_major_formatter(lambda x, _: f"{int(x/1000):,}k")
    # Annotate peak
    peak_i = pop.index(max(pop))
    ax.annotate(f"peak: {max(pop):,} ({years[peak_i]})",
                xy=(years[peak_i], max(pop)),
                xytext=(years[peak_i] - 25, max(pop) + 4000),
                fontsize=10, color="#444",
                arrowprops=dict(arrowstyle="->", color="#888", lw=0.8))
    fig.suptitle("Bermuda population, 1950 to 2024",
                 fontsize=13, fontweight="bold", color="#222")
    save(fig, "population-line.png")


def cost_comparison():
    cats = ["Rent\n(1-bed centre)", "Groceries\n(monthly)",
            "Utilities\n(monthly)", "Transport\n(monthly)",
            "Restaurant\n(2 meals)"]
    bermuda = [4200, 1100, 550, 200, 140]
    oecd = [1600, 450, 230, 110, 60]
    x = np.arange(len(cats))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 4.5))
    b1 = ax.bar(x - w/2, bermuda, w, label="Bermuda", color=ACCENT,
                edgecolor="white", linewidth=0.5)
    b2 = ax.bar(x + w/2, oecd, w, label="OECD median", color=ACCENT2,
                edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    ax.set_ylabel("USD (monthly)")
    ax.legend(loc="upper right")
    ax.yaxis.set_major_formatter(lambda x, _: f"${int(x):,}")
    # Value labels on Bermuda bars
    for rect in b1:
        h = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2, h + 60, f"${h:,}",
                ha="center", va="bottom", fontsize=9, color="#222",
                fontweight="bold")
    fig.suptitle("Bermuda monthly cost vs. OECD median",
                 fontsize=13, fontweight="bold", color="#222")
    save(fig, "cost-comparison.png")


def rent_bars():
    parishes = ["Sandys", "Southampton", "Warwick", "Paget", "Pembroke",
                "Devonshire", "Smith's", "Hamilton", "St George's"]
    one_bed = [2400, 2700, 3100, 3400, 3800, 3300, 3100, 2900, 2400]
    three_bed = [4500, 5200, 5800, 6500, 7200, 6300, 5900, 5400, 4600]
    x = np.arange(len(parishes))
    w = 0.38
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(x - w/2, one_bed, w, label="1-bedroom", color=ACCENT,
           edgecolor="white", linewidth=0.5)
    ax.bar(x + w/2, three_bed, w, label="3-bedroom", color=ACCENT4,
           edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(parishes, rotation=20, ha="right")
    ax.set_ylabel("USD / month")
    ax.yaxis.set_major_formatter(lambda x, _: f"${int(x):,}")
    ax.legend(loc="upper right")
    fig.suptitle("Median monthly rent by parish",
                 fontsize=13, fontweight="bold", color="#222")
    save(fig, "rent-bars.png")


def tourism_line():
    years = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
    cruise = [381000, 391000, 484000, 524000, 535000, 64000, 51000,
              295000, 470000, 535000]
    air = [220000, 244000, 270000, 281000, 270000, 86000, 114000,
           168000, 199000, 235000]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(years, cruise, color=ACCENT, linewidth=2.4, marker="o",
            markersize=5, markerfacecolor="white", markeredgewidth=1.5,
            markeredgecolor=ACCENT, label="Cruise")
    ax.plot(years, air, color=ACCENT4, linewidth=2.4, marker="s",
            markersize=5, markerfacecolor="white", markeredgewidth=1.5,
            markeredgecolor=ACCENT4, label="Air")
    ax.set_ylabel("Arrivals")
    ax.set_xlabel("Year")
    ax.yaxis.set_major_formatter(lambda x, _: f"{int(x/1000)}k")
    ax.legend(loc="upper left", ncol=2)
    # Annotate the 2020 collapse
    ax.annotate("pandemic", xy=(2020, 64000), xytext=(2020.4, 200000),
                fontsize=10, color="#444", fontstyle="italic",
                arrowprops=dict(arrowstyle="->", color="#888", lw=0.8))
    fig.suptitle("Cruise and air arrivals, 2015 to 2024",
                 fontsize=13, fontweight="bold", color="#222")
    save(fig, "tourism-line.png")


if __name__ == "__main__":
    parish_map()
    ferry_routes()
    climate_chart()
    gdp_pie()
    population_line()
    cost_comparison()
    rent_bars()
    tourism_line()
    print("\nAll figures rewritten.")
