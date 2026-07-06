# Los Reginas S.L.
 
Naviera de la Bahía de Santander.
 
- **Web**: https://www.losreginas.com
- **Teléfono**: 942 216 753
- **Email**: info@losreginas.es
 
## Líneas
 
| Línea | Tipo | Temporada |
|---|---|---|
| Santander – El Puntal | Playa, frecuencia 30 min | Jun–Oct |
| Santander – Pedreña – Somo | Regular | Jun–Oct |
 
## Calendarios
 
| service_id | Días | Periodo |
|---|---|---|
| `puntal_2026` | Diario | 01/06–04/10/2026 |
| `ped_comun` | L–D | 22/06–31/10/2026 |
| `ped_lab` | L–V | 22/06–31/10/2026 |
| `ped_fds` | S–D + festivos | 22/06–31/10/2026 |
 
## Festivos Cantabria 2026 incluidos
 
- 28 jul — Día de las Instituciones de Cantabria
- 15 sep — Festividad de la Bien Aparecida
- 12 oct — Fiesta Nacional de España
 
## Fuentes y mantenimiento

La verdad es `gtfs/*.txt`, editable a mano y revisable en cada `git diff`.

| Qué | Dónde | Fuente |
|---|---|---|
| Feed (verdad) | [`gtfs/`](gtfs/) | mantenido a mano |
| Origen | [`src/config.json`](src/config.json) → `source.pdfs` | URLs de los PDF publicados en losreginas.com |
| Tarifas | [`src/config.json`](src/config.json) → `fares` | hoja TARIFAS impresa — **no vigilada**, actualizar a mano |
| Vigilancia | [`src/check_source.py`](src/check_source.py) (`make watch`) | avisa cuando cambian los enlaces a PDF de la web |
| Utilidad opcional | [`src/`](src/) | redacta el horario de temporada desde los PDF (los descarga de las URLs) |

- **Línea Pedreña–Somo**: PDF *laborable* vigente desde **22/06/2026**, PDF
  *fin de semana* desde **04/07/2026** (URLs en `src/config.json`). Verificado por última vez:
  **2026-07-03**.
- **Línea El Puntal**: estática (`frequencies.txt`); no procede de PDF.
- El tooling de [`src/`](src/) es **opcional y no autoritativo** (no lo ejecuta
  CI): redacta un borrador del horario regular que se revisa a mano. Cambios
  ad-hoc (eventos, salidas puntuales) se editan directamente en `gtfs/`.
  Detalle en [`src/README.md`](src/README.md).

## Notas
 
- Tiempos de trayecto deducidos matemáticamente del horario publicado.
- Línea Puntal modelada con `frequencies.txt` (`exact_times=0`) — un solo barco,
  sujeto a acumulación de retrasos a lo largo del día.
- Restricciones por mareas bajas no incluidas (fuera de alcance GTFS estático).
- Tarifas en GTFS Fares v1 (`fare_attributes.txt` + `fare_rules.txt`, generadas
  desde `config.fares`). Billetes vendidos a bordo / en taquilla, así que son
  informativas. El ida+vuelta usa `transfers=1`; Google Maps planifica trayectos
  de ida, por lo que mostrará la tarifa de ida, no la de vuelta.
 
## Versiones
 
| Versión | Fecha | Cambios |
|---|---|---|
| 2026.1 | 2026-06-08 | Release inicial |
| 2026.2 | 2026-06-25 | Línea Pedreña–Somo actualizada al horario vigente desde 22/06/2026 (laborables y fines de semana). Eliminada regata (12/06, pasada). |
| 2026.3 | 2026-07-03 | Horario de fin de semana/festivos actualizado al vigente desde 04/07/2026: cadencia nocturna ampliada (Santander +20:40/21:10/21:40, Somo +20:35/21:05, Pedreña +20:45/21:15). Las salidas de Santander 20:30 y 21:00 pasan a ser solo laborables. |
| 2026.4 | 2026-07-06 | Editor del feed (`feed_publisher_name`/`url`) fijado a «Los Reginas» / losreginas.com. Añadidas tarifas (GTFS Fares v1): billete de ida y de ida+vuelta para ambas líneas. `route_short_name` de El Puntal vaciado (evita el aviso «headsign contiene route short name» en Google). |
