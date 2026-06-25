from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import create_engine

from gobernadores.extract import extract_all
from gobernadores.states import ESTADOS_WIKI


def main() -> int:
    p = argparse.ArgumentParser(
        description="Extrae gobernadores (nombre, periodo, partido) desde Wikipedia."
    )
    p.add_argument(
        "-o",
        "--output",
        default="gobernadores_mexico.csv",
        help="Ruta del CSV de salida",
    )
    p.add_argument(
        "--estado",
        action="append",
        metavar="NOMBRE",
        help="Filtrar por nombre de estado (puede repetirse). Ej: --estado Jalisco",
    )
    p.add_argument(
        "--postgres",
        metavar="URL",
        help="SQLAlchemy URL, ej: postgresql+psycopg2://user:pass@host:5432/db",
    )
    p.add_argument(
        "--table",
        default="gobernadores",
        help="Nombre de tabla para --postgres",
    )
    args = p.parse_args()

    pairs = ESTADOS_WIKI
    if args.estado:
        wanted = {e.strip().casefold() for e in args.estado}
        pairs = [(s, t) for s, t in ESTADOS_WIKI if s.casefold() in wanted]
        missing = wanted - {s.casefold() for s, _ in pairs}
        if missing:
            print("Estados no reconocidos:", ", ".join(sorted(missing)), file=sys.stderr)
            return 2

    df, errors = extract_all(pairs)
    df.to_csv(args.output, index=False)
    print(f"CSV escrito: {args.output} ({len(df)} filas)")

    if errors:
        print("Advertencias / errores por estado:", file=sys.stderr)
        for estado, msg in errors:
            print(f"  - {estado}: {msg}", file=sys.stderr)

    pg_url = args.postgres or os.environ.get("DATABASE_URL")
    if pg_url:
        engine = create_engine(pg_url)
        df.to_sql(args.table, engine, if_exists="append", index=False)
        print(f"Filas añadidas a PostgreSQL tabla {args.table!r}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
