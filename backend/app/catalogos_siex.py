"""Los catálogos que publica SIEX, para saber a qué tabla corresponde cada uno del descriptor.

## El problema que resuelve

El descriptor del cuaderno dice, campo por campo, contra qué catálogo valida: «Catálogo de
Eficacia del tratamiento». Eso dice **cómo se llama** el catálogo, no **qué tabla** hay que mirar
para sacar los códigos. Y sin saber qué tabla es, no se puede ni pedir los valores.

## Lo que sí se puede afirmar, y lo que no

SIEX publica, sin certificado, la lista de sus 287 catálogos con su nombre. Cruzando los dos
nombres sale esto:

- **15 de los 40** catálogos que pide el descriptor tienen una tabla de SIEX **con el nombre
  exactamente igual** (comparando sin mayúsculas ni acentos). Esas correspondencias son un dato,
  no una suposición, y las 15 son tablas públicas.
- **Los otros 25 no coinciden.** Y aquí está lo importante: **no se emparejan «por parecido»**.
  El descriptor pide «tipos de producto» y en SIEX hay una tabla que se llama «tipo de producto
  fitosanitario» (`TIPO_PRODFITO`): se parecen mucho, y no se puede afirmar que sean la misma.
  Afirmarlo sería inventar, y esto es un volcado oficial: un catálogo equivocado guarda el
  producto equivocado.

## Lo que este módulo NO hace

**No baja los valores.** El portal publica la estructura de las tablas (sus columnas), y los
datos de cada tabla están detrás de un captcha. Aquí solo se dice a qué tabla habría que pedirlos.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from . import iuws_descriptor

RAIZ = Path(__file__).resolve().parents[2]
RUTA = RAIZ / "data" / "siex_catalogos.json"

_inventario: dict | None = None
_leido = False


def normaliza(texto: str) -> str:
    """Sin mayúsculas, sin acentos y con los espacios de dentro colapsados.

    Es lo mínimo para comparar dos nombres escritos por dos organismos distintos: «Catálogo de
    Eficacia del tratamiento» y «Eficacia del tratamiento». Más allá de esto ya sería interpretar.
    """
    sin_acentos = unicodedata.normalize("NFKD", texto or "")
    limpio = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return " ".join(limpio.lower().split())


def cargar(ruta: Path | str | None = None) -> dict | None:
    """Lee el inventario. Devuelve `None` si no está, y entonces todo se dice vacío.

    Mismo criterio que el resto de listas oficiales: si el fichero no está, el programa sigue
    funcionando y dice que no lo tiene, en vez de suponer.
    """
    global _inventario, _leido
    destino = Path(ruta) if ruta else RUTA
    _leido = True
    if not destino.exists():
        _inventario = None
        return None
    try:
        datos = json.loads(destino.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        _inventario = None
        return None
    if not isinstance(datos, dict) or not datos.get("catalogos"):
        _inventario = None
        return None
    _inventario = datos
    return _inventario


def olvidar() -> None:
    """Vacía el inventario leído. Existe para los tests: uno que carga el suyo no puede dejarlo
    puesto para el siguiente, o el orden de ejecución cambiaría los resultados."""
    global _inventario, _leido
    _inventario = None
    _leido = False


def inventario() -> dict | None:
    if not _leido:
        cargar()
    return _inventario


def cargada() -> bool:
    return bool(inventario())


def catalogo_de_siex(nombre: str) -> dict | None:
    """La tabla de SIEX cuyo nombre coincide **exactamente** con ese, o `None`.

    `None` significa «no se puede afirmar», no «no existe». Ver el aviso del principio del
    módulo: parecerse no es ser.
    """
    buscado = normaliza(nombre)
    if not buscado:
        return None
    for catalogo in (inventario() or {}).get("catalogos", ()):
        if normaliza(catalogo.get("nombre", "")) == buscado:
            return catalogo
    return None


def catalogos_publicos() -> tuple[dict, ...]:
    return tuple(c for c in (inventario() or {}).get("catalogos", ()) if c.get("publico"))


def el_cruce() -> tuple[dict, ...]:
    """El cruce entero: un renglón por cada catálogo que pide el descriptor.

    Cada renglón dice el nombre que usa el descriptor, la tabla de SIEX si coincide
    exactamente (con su identificador y si es pública) y, si no coincide, que no coincide.
    """
    salida = []
    for nombre, cuantos in iuws_descriptor.catalogos_que_pide():
        tabla = catalogo_de_siex(nombre)
        salida.append(
            {
                "descriptor": nombre,
                "campos": cuantos,
                "tabla_de_siex": tabla["id"] if tabla else None,
                "publica": bool(tabla.get("publico")) if tabla else None,
            }
        )
    return tuple(salida)


def resumen() -> dict:
    """Lo que se puede decir del cruce, contado, para la pantalla de estado y para la ayuda."""
    if not cargada():
        return {
            "cargado": False,
            "por_que_no": (
                "No está el inventario de catálogos de SIEX. Se rehace con "
                "scripts/bajar_catalogos_siex.py."
            ),
            "catalogos_de_siex": 0,
            "coinciden_exactamente": 0,
            "sin_coincidencia": 0,
            "el_cruce": [],
        }
    cruce = el_cruce()
    coinciden = [r for r in cruce if r["tabla_de_siex"]]
    return {
        "cargado": True,
        "catalogos_de_siex": len(inventario().get("catalogos", ())),
        "publicos_de_siex": len(catalogos_publicos()),
        "coinciden_exactamente": len(coinciden),
        "sin_coincidencia": len(cruce) - len(coinciden),
        # El detalle de las que sí coinciden, que es lo que sirve para pedir los valores.
        "el_cruce": [r for r in cruce if r["tabla_de_siex"]],
        "los_que_no_coinciden": [r["descriptor"] for r in cruce if not r["tabla_de_siex"]],
    }
