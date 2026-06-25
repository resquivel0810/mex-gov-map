from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

CUTOFF = date(1989, 7, 2)

MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def parse_fecha(texto: str) -> date | None:
    if not texto or pd.isna(texto):
        return None

    s = str(texto).strip()

    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", s, re.I)
    if m:
        dia, mes, anio = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        if mes in MESES:
            return date(anio, MESES[mes], dia)

    m = re.match(r"^(\w+)\s+de\s+(\d{4})$", s, re.I)
    if m:
        mes, anio = m.group(1).lower(), int(m.group(2))
        if mes in MESES:
            return date(anio, MESES[mes], 1)

    m = re.match(r"^(\d{4})$", s)
    if m:
        return date(int(m.group(1)), 1, 1)

    return None


def inicio_mandato(periodo: str) -> date | None:
    if pd.isna(periodo):
        return None

    s = str(periodo).strip()
    if s.lower().startswith("desde"):
        return parse_fecha(s)

    parte = s.split(" - ", 1)[0].strip()
    return parse_fecha(parte)


def filter_desde(df: pd.DataFrame, cutoff: date = CUTOFF) -> pd.DataFrame:
    inicios = df["periodo"].map(inicio_mandato)
    mask = inicios.notna() & (inicios >= cutoff)
    return df.loc[mask].copy()


def main() -> int:
    p = argparse.ArgumentParser(
        description="Filtra gobernadores con inicio de mandato a partir de una fecha."
    )
    p.add_argument(
        "-i",
        "--input",
        default="gobernadores_mexico.csv",
        help="CSV de entrada",
    )
    p.add_argument(
        "-o",
        "--output",
        default="gobernadores_mexico_desde_1989.csv",
        help="CSV de salida",
    )
    p.add_argument(
        "--desde",
        default="1989-07-02",
        help="Fecha mínima de inicio (YYYY-MM-DD)",
    )
    args = p.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"No se encontró: {input_path}", file=sys.stderr)
        return 1

    y, m, d = (int(x) for x in args.desde.split("-"))
    cutoff = date(y, m, d)

    df = pd.read_csv(input_path)
    filtrado = filter_desde(df, cutoff)
    filtrado.to_csv(args.output, index=False)

    sin_fecha = df["periodo"].map(inicio_mandato).isna().sum()
    print(f"Entrada:  {len(df)} filas")
    print(f"Salida:   {len(filtrado)} filas (inicio >= {cutoff.isoformat()})")
    print(f"Sin fecha parseable en entrada: {sin_fecha}")
    print(f"CSV escrito: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
