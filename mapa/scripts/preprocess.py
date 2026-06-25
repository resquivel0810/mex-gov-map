#!/usr/bin/env python3
"""Genera GeoJSON liviano: estados (dissolve) y municipios por estado."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import geopandas as gpd

SOURCE = Path("/Users/montserratcolinaspicazo/Downloads/MunicipiosMexico.json")
OUT_DIR = Path(__file__).resolve().parent.parent / "data"
SIMPLIFY_TOLERANCE = 0.005  # grados (~500 m)


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFD", name)
    ascii_name = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    ascii_name = ascii_name.lower().strip()
    ascii_name = re.sub(r"[^a-z0-9]+", "-", ascii_name)
    return ascii_name.strip("-")


def simplify(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
    return gdf


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"No se encontró el archivo fuente: {SOURCE}")

    print(f"Leyendo {SOURCE} …")
    mun = gpd.read_file(SOURCE)
    mun = mun[["NAME_1", "NAME_2", "geometry"]].copy()

    estados = mun.dissolve(by="NAME_1", as_index=False)[["NAME_1", "geometry"]]
    estados = simplify(estados)

    municipios_dir = OUT_DIR / "municipios"
    municipios_dir.mkdir(parents=True, exist_ok=True)

    index: list[dict[str, str]] = []

    print("Exportando estados …")
    estados_path = OUT_DIR / "estados.geojson"
    estados.to_file(estados_path, driver="GeoJSON")

    print("Exportando municipios por estado …")
    for nombre, grupo in mun.groupby("NAME_1"):
        slug = slugify(nombre)
        grupo = simplify(grupo[["NAME_1", "NAME_2", "geometry"]])
        out_path = municipios_dir / f"{slug}.geojson"
        grupo.to_file(out_path, driver="GeoJSON")
        index.append({"name": nombre, "slug": slug, "file": f"municipios/{slug}.geojson"})
        print(f"  {nombre} ({len(grupo)} municipios) → {out_path.name}")

    index_path = OUT_DIR / "index.json"
    index_path.write_text(json.dumps(sorted(index, key=lambda x: x["name"]), ensure_ascii=False, indent=2), encoding="utf-8")

    total_mb = sum(f.stat().st_size for f in OUT_DIR.rglob("*") if f.is_file()) / (1024 * 1024)
    print(f"\nListo en {OUT_DIR} (~{total_mb:.1f} MB total)")


if __name__ == "__main__":
    main()
