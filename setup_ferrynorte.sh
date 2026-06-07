#!/bin/bash
# Ejecutar desde dentro de ferrynorte-gtfs/
# bash setup_ferrynorte.sh

set -e

# ── Estructura de carpetas ────────────────────────────────────────────────────
mkdir -p operators/los-reginas
mkdir -p builds/los-reginas
mkdir -p .github/workflows

# ── README raíz ───────────────────────────────────────────────────────────────
cat > README.md << 'MD'
# ferrynorte-gtfs

GTFS feeds para operadores de ferry del norte de España.

## Estructura

```
operators/<operador>/   → ficheros fuente (.txt), editables, con historial git
builds/<operador>/      → ZIP distribuible generado a partir de los fuentes
```

## Operadores

| Operador | Líneas | Cobertura | Feed |
|---|---|---|---|
| [Los Reginas](operators/los-reginas/) | Santander–El Puntal, Santander–Pedreña–Somo | May–Oct 2026 | [ZIP](builds/los-reginas/los_reginas_gtfs_2026.zip) |

## Uso

Los feeds se sirven en:
```
https://ferrynorte.com/feeds/<operador>/feed.zip
```

Registrados en [Mobility Database](https://mobilitydatabase.org/).

## Licencia

[CC BY 4.0](LICENSE) — uso libre con atribución.
MD

# ── README operador ───────────────────────────────────────────────────────────
cat > operators/los-reginas/README.md << 'MD'
# Los Reginas S.L.

Naviera de la Bahía de Santander.

- **Web**: https://www.losreginas.com
- **Teléfono**: 942 216 753
- **Email**: info@losreginas.es

## Líneas

| Línea | Tipo | Temporada |
|---|---|---|
| Santander – El Puntal | Playa, frecuencia 30 min | Jun–Oct |
| Santander – Pedreña – Somo | Regular | Abr–Oct |

## Calendarios

| service_id | Días | Periodo |
|---|---|---|
| `puntal_2026` | Diario | 01/06–04/10/2026 |
| `ped_comun` | L–D | 23/05–31/10/2026 |
| `ped_lab` | L–V | 23/05–31/10/2026 |
| `ped_fds` | S–D + festivos | 23/05–31/10/2026 |
| `ped_regata` | Solo 12/06/2026 | Regata Bandera Bansander |

## Festivos Cantabria 2026 incluidos

- 28 jul — Día de las Instituciones de Cantabria
- 15 sep — Festividad de la Bien Aparecida
- 12 oct — Fiesta Nacional de España

## Notas

- Tiempos de trayecto deducidos matemáticamente del horario publicado.
- Línea Puntal modelada con `frequencies.txt` (`exact_times=0`) — un solo barco,
  sujeto a acumulación de retrasos a lo largo del día.
- Restricciones por mareas bajas no incluidas (fuera de alcance GTFS estático).

## Versiones

| Versión | Fecha | Cambios |
|---|---|---|
| 2026.1 | 2026-06-08 | Release inicial |
MD

# ── GitHub Actions: build automático del ZIP ─────────────────────────────────
cat > .github/workflows/build.yml << 'YML'
name: Build GTFS ZIP

on:
  push:
    paths:
      - 'operators/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build ZIPs
        run: |
          for op in operators/*/; do
            name=$(basename "$op")
            mkdir -p "builds/$name"
            zip -j "builds/$name/${name}_gtfs.zip" "$op"*.txt
            echo "Built builds/$name/${name}_gtfs.zip"
          done

      - name: Commit ZIPs
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add builds/
          git diff --staged --quiet || git commit -m "build: regenerate GTFS ZIPs [skip ci]"
          git push
YML

# ── .gitignore ────────────────────────────────────────────────────────────────
cat > .gitignore << 'GI'
.DS_Store
*.pyc
__pycache__/
GI

# ── Git init y primer commit ──────────────────────────────────────────────────
git init
git add .
git commit -m "chore: initial repo structure"

git branch -M main
git remote add origin https://github.com/juanmacuevas/ferrynorte-gtfs.git

echo ""
echo "✅ Repo inicializado. Pasos siguientes:"
echo ""
echo "  1. Copia los .txt a operators/los-reginas/"
echo "     (los tienes en el ZIP descargado)"
echo ""
echo "  2. Copia el ZIP a builds/los-reginas/los_reginas_gtfs_2026.zip"
echo ""
echo "  3. git add -A && git commit -m 'feat: add Los Reginas GTFS 2026'"
echo ""
echo "  4. Crea el repo en GitHub (vacío, sin README) y luego:"
echo "     git push -u origin main"
echo ""
echo "  5. Registra en Mobility Database:"
echo "     https://mobilitydatabase.org/"
echo "     URL del feed:"
echo "     https://raw.githubusercontent.com/juanmacuevas/ferrynorte-gtfs/main/builds/los-reginas/los_reginas_gtfs_2026.zip"
