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
| `ped_comun` | L–D | 22/06/2026–30/09/2027 |
| `ped_lab` | L–V | 22/06/2026–30/09/2027 |
| `ped_fds` | S–D + festivos | 22/06/2026–30/09/2027 |
 
La línea Pedreña–Somo es regular (no estacional) y la empresa no publica
fecha final: su ventana se extiende un año por delante para que Google
Transit no marque el dataset como caducado, y se recorta o actualiza cuando
aparece un horario nuevo (`make watch`). El Puntal sí es estacional y
termina de verdad el 04/10/2026 («hasta el primer fin de semana de
octubre», web del operador).
 
## Festivos con horario de fin de semana
 
Festivos de Cantabria y nacionales que caen en día laborable dentro de la
ventana:
 
- 2026: 28 jul (Instituciones de Cantabria), 15 sep (Bien Aparecida),
  12 oct (Fiesta Nacional), 8 dic (Inmaculada), 25 dic (Navidad)
- 2027: 1 ene, 6 ene (Reyes), 25–26 mar (Jueves y Viernes Santo),
  28 jul (Instituciones de Cantabria), 15 sep (Bien Aparecida)
 
Los de 2027 son los fijos más la Semana Santa; el calendario laboral
autonómico de 2027 aún no está publicado, revisar cuando salga.
 
## Fuentes y mantenimiento

La verdad es `gtfs/*.txt`, editable a mano y revisable en cada `git diff`.

| Qué | Dónde | Fuente |
|---|---|---|
| Feed (verdad) | [`gtfs/`](gtfs/) | mantenido a mano |
| Origen | [`src/config.json`](src/config.json) → `source.pdfs` | URLs de los PDF publicados en losreginas.com |
| Tarifas | [`src/config.json`](src/config.json) → `fares` | hoja TARIFAS impresa — **no vigilada**, actualizar a mano |
| Vigilancia | [`src/check_source.py`](src/check_source.py) (`make watch`) | avisa cuando cambian los enlaces a PDF de la web |
| Utilidad opcional | [`src/`](src/) | redacta el horario de temporada desde los PDF (los descarga de las URLs) |

- **Línea Pedreña–Somo**: PDF *laborable* vigente desde **21/09/2026**, PDF
  *fin de semana* desde **26/09/2026** (URLs en `src/config.json`). Verificado por última vez:
  **2026-09-21**.
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
| 2026.8 | 2026-09-01 | Pedreña–Somo actualizada a los PDF vigentes: laborable desde 31/08/2026 y fin de semana desde 05/09/2026. Las salidas nocturnas (Santander 20:40/21:10/21:40, Somo 20:35/21:05) pasan a ser diarias; nueva rotación matinal diaria (Somo 10:30 / Santander 11:05); eliminadas las salidas de Santander 20:30/21:00 solo laborables. Retirados los servicios temporales ya vencidos de julio (pico vespertino) y agosto. |
| 2026.9 | 2026-09-21 | Pedreña–Somo actualizada a los PDF de otoño: laborable desde 21/09/2026 y fin de semana desde 26/09/2026. Se retiran las salidas nocturnas (Santander 20:40/21:10/21:40 → 20:30/21:00; Somo 20:35/21:05 → 20:25; Pedreña 20:45/21:15 → 20:35) y la salida de fin de semana de Santander 15:50 pasa a 15:40. Ventana de los calendarios `ped_*` y `feed_end_date` extendida hasta 30/09/2027 (línea regular sin fecha final publicada) para evitar los avisos de caducidad de Google Transit; añadidos los festivos con horario de fin de semana hasta sep/2027. El Puntal sin cambios (termina el 04/10/2026). |
