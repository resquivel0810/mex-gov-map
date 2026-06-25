from __future__ import annotations

import io
import re
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests
from bs4 import BeautifulSoup

from gobernadores.states import ESTADOS_WIKI

WIKI_BASE = "https://es.wikipedia.org/wiki/"
USER_AGENT = (
    "GobernadoresMXExtractor/0.1 (educational; https://github.com/local; "
    "contact: local)"
)

NOMBRE_KEYS = (
    "gobernador",
    "gobernadora",
    "titular",
    "nombre",
    "gobernante",
    "gobernantes",
    "persona",
    "mandatario",
    "regente",
    "jefe de gobierno",
    "jefe (a) de gobierno",
)
PERIODO_KEYS = (
    "mandato",
    "período",
    "periodo",
    "gestión",
    "gestion",
    "inicio",
    "fin",
    "duración",
    "duracion",
    "tiempo",
    "toma de posesión",
    "fin del mandato",
)
INICIO_KEYS = ("inicio de mandato", "inicio", "toma de posesión", "fecha de toma")
FIN_KEYS = ("fin de mandato", "fin del mandato", "fin ")
PARTIDO_KEYS = (
    "partido",
    "afiliación",
    "afiliacion",
    "afiliacion política",
    "partido político",
)

NEGATIVE_HINTS = (
    "población",
    "poblacion",
    "superficie",
    "capital",
    "municipio",
    "referencia",
)


def wiki_url(title: str) -> str:
    safe = title.replace(" ", "_")
    return WIKI_BASE + quote(safe, safe="/:")


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = df.columns
    if isinstance(cols, pd.MultiIndex):
        new_cols: list[str] = []
        for tup in cols:
            parts = [str(p).strip() for p in tup if str(p).strip().lower() != "nan"]
            new_cols.append(" ".join(parts).strip() or "columna")
        out = df.copy()
        out.columns = new_cols
        return out
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip().lower())


def column_score(names: list[str]) -> tuple[int, bool]:
    joined = " ".join(_norm(n) for n in names)
    if any(h in joined for h in NEGATIVE_HINTS) and "gobernador" not in joined:
        return -100, False
    score = 0
    has_person = False
    for n in names:
        low = _norm(n)
        if any(k in low for k in NOMBRE_KEYS):
            score += 4
            has_person = True
        if any(k in low for k in PERIODO_KEYS):
            score += 3
        if any(k in low for k in PARTIDO_KEYS):
            score += 2
    return score, has_person


def pick_best_table(tables: list[pd.DataFrame]) -> pd.DataFrame | None:
    best: tuple[float, pd.DataFrame] | None = None
    for t in tables:
        if t.shape[0] < 2 or t.shape[1] < 2:
            continue
        t2 = flatten_columns(t)
        names = [str(c) for c in t2.columns]
        score, has_person = column_score(names)
        if not has_person:
            continue
        rows = t2.shape[0]
        weighted = score * 10 + min(rows, 500)
        if best is None or weighted > best[0]:
            best = (weighted, t2)
    return None if best is None else best[1]


PARTIDO_ALIASES = {
    "morena": "Movimiento de Regeneración Nacional",
    "morena (partido político)": "Movimiento de Regeneración Nacional",
}


def clean_cell(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value)
    text = re.sub(r"\[[^\]]*]", "", text)
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    alias = PARTIDO_ALIASES.get(text.lower())
    if alias:
        return alias
    return text


def _first_matching_column(columns: list[str], keys: tuple[str, ...]) -> str | None:
    for c in columns:
        low = _norm(c)
        if any(k in low for k in keys):
            return c
    return None


def _best_column_by_fill(df: pd.DataFrame, keys: tuple[str, ...]) -> str | None:
    """Elige la columna cuyo nombre coincide con keys y tiene más valores no vacíos."""
    best_col: str | None = None
    best_n = -1
    for c in df.columns:
        low = _norm(str(c))
        if not any(k in low for k in keys):
            continue
        n = sum(1 for v in df[c] if clean_cell(v))
        if n > best_n:
            best_n = n
            best_col = str(c)
    return best_col


def _matching_columns(df: pd.DataFrame, keys: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for c in df.columns:
        low = _norm(str(c))
        if any(k in low for k in keys):
            out.append(str(c))
    return out


def map_columns(df: pd.DataFrame) -> dict[str, str | None]:
    cols = [str(c) for c in df.columns]
    nombre_cols = _matching_columns(df, NOMBRE_KEYS)
    nombre = _best_column_by_fill(df, NOMBRE_KEYS) or (
        nombre_cols[0] if nombre_cols else _first_matching_column(cols, NOMBRE_KEYS)
    )
    periodo = _best_column_by_fill(df, PERIODO_KEYS) or _first_matching_column(cols, PERIODO_KEYS)
    partido = _best_column_by_fill(df, PARTIDO_KEYS) or _first_matching_column(cols, PARTIDO_KEYS)
    inicio = _best_column_by_fill(df, INICIO_KEYS) or _first_matching_column(cols, INICIO_KEYS)
    fin = _best_column_by_fill(df, FIN_KEYS) or _first_matching_column(cols, FIN_KEYS)
    return {
        "nombre": nombre,
        "nombre_cols": nombre_cols,
        "periodo": periodo,
        "partido": partido,
        "inicio": inicio,
        "fin": fin,
    }


def _looks_like_date(text: str) -> bool:
    low = text.lower()
    if re.search(r"\d{1,2}\s+de\s+\w+", low):
        return True
    return bool(re.search(r"\d{4}", text)) and any(m in low for m in MESES_ES)


MESES_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _is_plausible_nombre(text: str) -> bool:
    if not text or len(text) < 3:
        return False
    low = text.lower()
    if low.startswith("http") or "archivo:" in low:
        return False
    if _looks_like_date(text):
        return False
    if any(k in low for k in ("partido", "presidente de la república", "logo")):
        return False
    return True


def row_nombre(row: pd.Series, mapping: dict[str, Any]) -> str:
    cols = mapping.get("nombre_cols") or []
    if mapping.get("nombre"):
        cols = list(dict.fromkeys([mapping["nombre"], *cols]))
    for c in cols:
        val = clean_cell(row.get(c, ""))
        if _is_plausible_nombre(val):
            return val
    return ""


def normalize_periodo_text(p: str) -> str:
    """Arregla rangos pegados tipo '1997-29 de septiembre' o '2000-29 de julio'."""
    p = re.sub(r"de\s+(\d{4})-(\d{1,2}\s+de\s+)", r"de \1 - \2", p)
    p = re.sub(r"(\d{4})-(\d{1,2}\s+de\s+)", r"\1 - \2", p)
    if " - " not in p and re.search(r"\d{4}-\d{1,2}\s+de", p):
        p = re.sub(r"(\d{4})-(\d{1,2}\s+de\s+)", r"\1 - \2", p)
    return p


def row_periodo(row: pd.Series, mapping: dict[str, Any]) -> str:
    if mapping.get("periodo"):
        p = clean_cell(row.get(mapping["periodo"], ""))
        if p:
            return normalize_periodo_text(p)
    inicio = clean_cell(row.get(mapping.get("inicio"), "")) if mapping.get("inicio") else ""
    fin = clean_cell(row.get(mapping.get("fin"), "")) if mapping.get("fin") else ""
    if inicio and fin:
        return f"{inicio} - {fin}"
    return inicio or fin


def fetch_html(url: str, timeout: int = 45) -> str:
    r = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "es"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.text


def extract_state_tables(html: str) -> list[pd.DataFrame]:
    """Parsea solo tablas `wikitable` cuando existan (mucho más rápido que todo el HTML)."""
    soup = BeautifulSoup(html, "lxml")
    results: list[pd.DataFrame] = []
    for table in soup.find_all("table"):
        classes = table.get("class") or []
        if "wikitable" not in classes:
            continue
        chunk = str(table)
        try:
            results.extend(pd.read_html(io.StringIO(chunk), flavor="lxml"))
        except ValueError:
            continue
    if results:
        return results
    return pd.read_html(io.StringIO(html), flavor="lxml")


def process_table(df: pd.DataFrame, estado: str) -> pd.DataFrame:
    df = flatten_columns(df)
    mapping = map_columns(df)
    if not mapping.get("nombre") and not mapping.get("nombre_cols"):
        raise ValueError("No se encontró columna de nombre/gobernador")

    partido_col = mapping["partido"]

    rows: list[dict[str, str]] = []
    for _, row in df.iterrows():
        nombre = row_nombre(row, mapping)
        if not nombre:
            continue
        periodo = row_periodo(row, mapping)
        partido = clean_cell(row.get(partido_col, "")) if partido_col else ""
        rows.append(
            {
                "estado": estado,
                "nombre": nombre,
                "periodo": periodo,
                "partido": partido,
            }
        )
    return pd.DataFrame(rows)


def tables_with_governors(tables: list[pd.DataFrame]) -> list[pd.DataFrame]:
    picked: list[pd.DataFrame] = []
    for t in tables:
        if t.shape[0] < 2 or t.shape[1] < 2:
            continue
        t2 = flatten_columns(t)
        score, has_person = column_score([str(c) for c in t2.columns])
        if has_person and score > 0:
            picked.append(t2)
    return picked


def extract_estado(estado: str, wiki_title: str) -> pd.DataFrame:
    url = wiki_url(wiki_title)
    html = fetch_html(url)
    tables = extract_state_tables(html)
    candidates = tables_with_governors(tables)
    if not candidates:
        raise ValueError(f"No se encontró tabla candidata para {estado}")

    frames: list[pd.DataFrame] = []
    for table in candidates:
        try:
            part = process_table(table, estado)
            if not part.empty:
                frames.append(part)
        except ValueError:
            continue

    if not frames:
        raise ValueError(f"No se pudieron procesar tablas para {estado}")

    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["nombre", "periodo"], keep="first")
    return out


def extract_all(
    estados: list[tuple[str, str]] | None = None,
) -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    estados = estados or ESTADOS_WIKI
    frames: list[pd.DataFrame] = []
    errors: list[tuple[str, str]] = []
    for estado, title in estados:
        try:
            frames.append(extract_estado(estado, title))
        except Exception as e:  # noqa: BLE001 — agregamos contexto por estado
            errors.append((estado, f"{type(e).__name__}: {e}"))
    if not frames:
        empty = pd.DataFrame(columns=["estado", "nombre", "periodo", "partido"])
        return empty, errors
    out = pd.concat(frames, ignore_index=True)
    return out, errors
