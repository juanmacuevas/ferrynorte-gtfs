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
