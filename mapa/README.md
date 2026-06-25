# Mapa interactivo de México (D3.js)

Vista nacional con **32 estados**; al hacer clic en un estado se cargan sus **municipios** y el mapa hace zoom a ese territorio.

## Ver el mapa

Desde esta carpeta (`mapa/`), levanta un servidor estático (necesario para `fetch`):

```bash
cd mapa
python3 -m http.server 8080
```

Abre [http://localhost:8080](http://localhost:8080).

## Regenerar datos

Si cambias el GeoJSON fuente (`~/Downloads/MunicipiosMexico.json`), ejecuta:

```bash
cd ..   # raíz del repo gobernadores
.venv/bin/python mapa/scripts/preprocess.py
```

Eso genera en `mapa/data/`:

- `estados.geojson` — límites estatales (dissolve de municipios)
- `municipios/*.geojson` — un archivo por estado (~3.8 MB en total)
- `index.json` — índice nombre → archivo

## Estructura

```
mapa/
├── index.html
├── mapa.js
├── styles.css
├── data/
└── scripts/preprocess.py
```
