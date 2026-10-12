"""Build a tiny spine lake (Silver plots/zoning + one published Gold table) for testing the spine-serve service."""
import sys
import textwrap
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box
from spine.lake import Lake
from spine.transform import execute, load_descriptor

DESCRIPTOR = """\
id: demo.plot_capacity
version: 0.1.0
kind: transform
title: Demo - allowable GFA = plot area x gross plot ratio (spine toy example)
upstream: {repo: tetratorus/saas-middleware (branch sg-urban-spine), license: MIT}
runtime: {type: python, entrypoint: "adapter:run"}
inputs:
  - {name: plots, source: "silver:plots", columns: [plot_id, area_m2]}
  - {name: zoning, source: "silver:zoning", columns: [plot_id, gross_plot_ratio]}
outputs:
  - name: plot_capacity
    key: [plot_id]
    columns:
      - {name: plot_id, type: string}
      - {name: gfa_m2, type: float, unit: m2}
"""
ADAPTER = """\
import pandas as pd

def run(inputs, params):
    df = pd.DataFrame(inputs["plots"][["plot_id", "area_m2"]]).merge(
        inputs["zoning"][["plot_id", "gross_plot_ratio"]], on="plot_id")
    df["gfa_m2"] = df.area_m2 * df.gross_plot_ratio.fillna(0)
    return {"plot_capacity": df[["plot_id", "gfa_m2"]]}
"""


def build(root: Path) -> Lake:
    lake = Lake(root / "lake")
    geoms = [box(29400, 28700, 29460, 28760), box(29470, 28700, 29530, 28740)]
    lake.silver_write("plots", gpd.GeoDataFrame({"plot_id": ["P1", "P2"], "area_m2": [g.area for g in geoms],
                                                 "source_version": "demo"}, geometry=geoms, crs="EPSG:3414"))
    lake.silver_write("zoning", pd.DataFrame({"plot_id": ["P1", "P2"], "zone_type": ["RESIDENTIAL", "COMMERCIAL"],
                                              "gross_plot_ratio": [2.8, 4.2], "source_version": "demo"}))
    t = root / "demo_transform"
    t.mkdir(parents=True, exist_ok=True)
    (t / "transform.yaml").write_text(DESCRIPTOR)
    (t / "adapter.py").write_text(textwrap.dedent(ADAPTER))
    execute(lake, load_descriptor(t / "transform.yaml"))
    return lake


if __name__ == "__main__":
    print(build(Path(sys.argv[1])).root)
