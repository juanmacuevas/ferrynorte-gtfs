# ferrynorte-gtfs

[![Publish GTFS feeds](https://github.com/juanmacuevas/ferrynorte-gtfs/actions/workflows/build.yml/badge.svg)](https://github.com/juanmacuevas/ferrynorte-gtfs/actions/workflows/build.yml)
[![License: CC BY 4.0](https://img.shields.io/badge/license-CC%20BY%204.0-lightgrey.svg)](LICENSE.md)

Feeds GTFS para operadores de ferry del norte de España, generados de forma
determinista a partir de los horarios publicados por cada operador y con
historial completo en git.

## Operadores

| Operador | Líneas | Temporada | Feed |
|---|---|---|---|
| [Los Reginas](operators/los-reginas/) | Santander–El Puntal · Santander–Pedreña–Somo | Jun–Oct 2026 | [descargar](https://github.com/juanmacuevas/ferrynorte-gtfs/releases/download/los-reginas/los-reginas_gtfs.zip) |

## Estructura

```
operators/<op>/gtfs/      feed GTFS (.txt) — la verdad, editable a mano, con historial git
operators/<op>/sources/   documentación de origen (horario en PDF/web, capturas, confirmaciones)
operators/<op>/src/        utilidad opcional para redactar el feed desde la fuente (si aplica)
builds/<op>/              ZIP local para pruebas (no versionado: ver Distribución)
```

Los `.txt` de `operators/<op>/gtfs/` son la **fuente autoritativa**, mantenida a
mano y validada (`make validate`). El ZIP publicable no se versiona en git: lo
genera y publica CI como GitHub Release (ver [Distribución](#distribución)).

Cuando el horario de un operador es legible por máquina (Los Reginas: PDF export
de Excel), `operators/<op>/src/` aporta una utilidad **opcional** para redactar el
feed, siempre revisada a mano y nunca ejecutada por CI. Cuando la fuente no es
estructurada, el feed se mantiene directamente a mano y `sources/` conserva la
documentación que respalda cada dato.

## Uso

Herramientas: [uv](https://docs.astral.sh/uv/) + `make`.

```bash
make validate       # valida el feed (estructura + referencias) — gate de CI
make zip            # valida y empaqueta builds/<op>/<op>_gtfs.zip
make setup          # instala dependencias (uv sync) — sólo si usas el tooling de src/
make build          # (opcional) redacta los .txt desde la fuente del operador
make check          # (opcional) compara el feed con lo que produciría src/
make help           # lista los targets   (otro operador: make … OPERATOR=<nombre>)
```

`make validate` es la red de seguridad de un repo editado a mano: corre en local
y como **gate bloqueante en CI** (no se publica un feed inválido). `build`/`check`
son utilidades opcionales del operador con fuente automatizable.

## Añadir un operador

1. Crea `operators/<op>/gtfs/` con los ficheros GTFS `.txt`.
2. Coloca en `operators/<op>/src/` lo que convierta las fuentes del operador en
   esos `.txt` (la conversión es, por naturaleza, específica de cada operador).
3. `make zip OPERATOR=<op>` para probar en local; al hacer push a `main`, CI
   publica el feed como Release con tag `<op>` (URL de descarga constante).

## Distribución

Cada feed se publica como **GitHub Release** con tag fijo = nombre del operador.
El nombre del asset es constante, así que la URL de descarga no cambia nunca:

```
https://github.com/juanmacuevas/ferrynorte-gtfs/releases/download/<operador>/<operador>_gtfs.zip
```

Esa URL es la que se registra en [Mobility Database](https://mobilitydatabase.org/)
y Google Transit, y no cambia entre publicaciones.

### Automatización

La publicación es **automática**. En cada `push` a `main` que modifique
`operators/**`, el workflow [`build.yml`](.github/workflows/build.yml):

1. valida cada feed con `scripts/validate.py` — si falla, **no publica nada**;
2. empaqueta el ZIP de forma determinista (bytes idénticos si el contenido no
   cambia, para no generar actualizaciones falsas aguas abajo);
3. crea o actualiza la Release de cada operador (tag fijo `<op>`, asset
   reemplazado con `--clobber`), con fecha/hora y `feed_version` en el título.

No hay paso manual: basta con hacer push. El badge de estado del README refleja
el último run del workflow y se actualiza solo.

## Licencia

[CC BY 4.0](LICENSE.md) — uso libre con atribución.
