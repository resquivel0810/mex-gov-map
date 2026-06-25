"""Utilidades para parsear periodos de mandato."""

from __future__ import annotations

import re
from datetime import date

import pandas as pd

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

# Nombre en CSV → nomgeo INEGI
CSV_A_INEGI: dict[str, str] = {
    "Aguascalientes": "Aguascalientes",
    "Baja California": "Baja California",
    "Baja California Sur": "Baja California Sur",
    "Campeche": "Campeche",
    "Chiapas": "Chiapas",
    "Chihuahua": "Chihuahua",
    "Coahuila": "Coahuila de Zaragoza",
    "Colima": "Colima",
    "Ciudad de México": "Ciudad de México",
    "Distrito Federal": "Ciudad de México",
    "Durango": "Durango",
    "Guanajuato": "Guanajuato",
    "Guerrero": "Guerrero",
    "Hidalgo": "Hidalgo",
    "Jalisco": "Jalisco",
    "Estado de México": "México",
    "Michoacán": "Michoacán de Ocampo",
    "Morelos": "Morelos",
    "Nayarit": "Nayarit",
    "Nuevo León": "Nuevo León",
    "Oaxaca": "Oaxaca",
    "Puebla": "Puebla",
    "Querétaro": "Querétaro",
    "Quintana Roo": "Quintana Roo",
    "San Luis Potosí": "San Luis Potosí",
    "Sinaloa": "Sinaloa",
    "Sonora": "Sonora",
    "Tabasco": "Tabasco",
    "Tamaulipas": "Tamaulipas",
    "Tlaxcala": "Tlaxcala",
    "Veracruz": "Veracruz de Ignacio de la Llave",
    "Yucatán": "Yucatán",
    "Zacatecas": "Zacatecas",
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


def fin_mandato(periodo: str) -> date | None:
    if pd.isna(periodo):
        return None

    s = str(periodo).strip()
    if s.lower().startswith("desde"):
        return None

    if " - " not in s:
        return None

    parte = s.split(" - ", 1)[1].strip()
    return parse_fecha(parte)
