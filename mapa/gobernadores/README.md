# Gobernadores en el tiempo (D3 + INEGI)

Mapa de México con **357 fechas clave** desde 1989: cada estado se colorea según el partido del gobernador en funciones. Incluye slider, reproducción automática y panel de cambios.

## Ver el mapa

```bash
cd mapa/gobernadores
python3 -m http.server 8080
```

Abre **http://localhost:8080**

## Regenerar datos

Tras actualizar el CSV o para refrescar geometrías INEGI:

```bash
cd ../..   # raíz del repo
PYTHONPATH=. .venv/bin/python mapa/gobernadores/scripts/prepare_data.py
```

Descarga estados desde [INEGI wscatgeo](https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgee/) y genera:

- `data/estados_inegi.geojson` — geometrías simplificadas (32 entidades)
- `data/mandatos.json` — mandatos parseados desde `gobernadores_mexico_desde_1989.csv`

## Controles

- **Slider**: navega entre fechas de cambio de gobernador
- **▶ Reproducir**: animación cronológica
- **Siguiente cambio**: salta al próximo evento
- **Hover** sobre un estado: nombre, partido y periodo

Estados sin filas en el CSV (p. ej. Baja California Sur, Quintana Roo) aparecen en gris. Ciudad de México se extrae de [Wikipedia](https://es.wikipedia.org/wiki/Anexo:Gobernantes_de_Ciudad_de_México) (jefes de gobierno y regentes).
