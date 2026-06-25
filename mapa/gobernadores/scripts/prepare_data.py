#!/usr/bin/env python3
"""Descarga geometrías INEGI y genera mandatos.json para el mapa temporal."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from gobernadores.dates import CSV_A_INEGI, fin_mandato, inicio_mandato

INEGI_URL = "https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgee/"
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CSV_DEFAULT = Path(__file__).resolve().parents[3] / "gobernadores_mexico_desde_1989.csv"
SIMPLIFY = 0.01


def fetch_inegi_estados() -> gpd.GeoDataFrame:
    print(f"Descargando {INEGI_URL} …")
    resp = requests.get(INEGI_URL, timeout=300)
    resp.raise_for_status()
    data = resp.json()

    gdf = gpd.GeoDataFrame.from_features(data["features"], crs="EPSG:4326")
    gdf = gdf.rename(columns={"nomgeo": "nomgeo_inegi"})
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY, preserve_topology=True)

    inegi_a_csv = {v: k for k, v in CSV_A_INEGI.items() if k not in ("Distrito Federal",)}
    gdf["estado_csv"] = gdf["nomgeo_inegi"].map(inegi_a_csv)
    return gdf


def build_mandatos(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    rows: list[dict] = []
    fechas: set[str] = set()

    for _, row in df.iterrows():
        estado = str(row["estado"]).strip()
        inicio = inicio_mandato(row["periodo"])
        if not inicio:
            continue
        fin = fin_mandato(row["periodo"])
        partido = str(row["partido"]).strip() if pd.notna(row["partido"]) else "Desconocido"

        rows.append(
            {
                "estado": estado,
                "nomgeo_inegi": CSV_A_INEGI.get(estado, estado),
                "nombre": str(row["nombre"]).strip(),
                "partido": partido,
                "periodo": str(row["periodo"]).strip(),
                "inicio": inicio.isoformat(),
                "fin": fin.isoformat() if fin else None,
            }
        )
        fechas.add(inicio.isoformat())
        if fin:
            fechas.add(fin.isoformat())

    partidos = sorted({r["partido"] for r in rows})
    fechas_ordenadas = sorted(fechas)

    return {
        "fuente": str(csv_path.name),
        "mandatos": rows,
        "partidos": partidos,
        "fechas_clave": fechas_ordenadas,
        "rango": {
            "min": fechas_ordenadas[0] if fechas_ordenadas else "1989-07-02",
            "max": date.today().isoformat(),
        },
    }


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("csv", nargs="?", default=str(CSV_DEFAULT))
    p.add_argument("--solo-mandatos", action="store_true", help="No volver a descargar INEGI")
    args = p.parse_args()

    csv_path = Path(args.csv)
    skip_geo = args.solo_mandatos

    if not csv_path.exists():
        print(f"No se encontró CSV: {csv_path}", file=sys.stderr)
        return 1

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    geo_path = DATA_DIR / "estados_inegi.geojson"
    if skip_geo and geo_path.exists():
        print(f"GeoJSON INEGI existente: {geo_path}")
    else:
        gdf = fetch_inegi_estados()
        gdf.to_file(geo_path, driver="GeoJSON")
        print(f"GeoJSON INEGI: {geo_path} ({len(gdf)} estados, {geo_path.stat().st_size // 1024} KB)")

    mandatos = build_mandatos(csv_path)
    json_path = DATA_DIR / "mandatos.json"
    json_path.write_text(json.dumps(mandatos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Mandatos: {json_path} ({len(mandatos['mandatos'])} registros)")
    print(f"Fechas clave: {len(mandatos['fechas_clave'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
