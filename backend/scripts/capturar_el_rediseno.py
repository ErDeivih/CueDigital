"""Las capturas del rediseno, pantalla por pantalla y a los dos tamanos que importan.

POR QUE EXISTE
El contrato del rediseno (`cuedigital:redesign-20261101-v1`) pide, por cada pantalla, una
captura de antes y otra de despues, en movil y en escritorio, con su huella. Habia
capturas sueltas (`docs/capturas/`) y un guion para cinco anchuras
(`capturar_las_anchuras.py`), pero ninguno dejaba **el nombre y la huella que pide el
contrato**. Esto las deja en `docs/diseno/capturas/`, con un `manifest.json` que dice el
sha256 de cada una, para que el informe las pueda citar sin inventarse nada.

QUE NO HACE
- No inventa datos: usa una cuenta y unas parcelas de mentira, creadas al vuelo, y el
  servidor temporal que ya usan los demas guiones (`el_servidor_temporal`).
- No es una prueba de que la pantalla este bien: es el material para mirarla. La revision
  es la que decide.
- No rellena `REDISENO.json`: eso lo escribe quien revisa, con lo que vea aqui.

USO
    python scripts/capturar_el_rediseno.py [fase]

`fase` es `before` (por defecto) o `after`, y solo cambia el nombre de la carpeta y de
los ficheros, para no pisar la captura de antes con la de despues.
"""

from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

# Los dos tamanos del contrato: un movil de una mano y una pantalla de despacho.
LAS_ANCHURAS = {"mobile": (390, 844), "desktop": (1366, 900)}

# Las pantallas que se capturan, con el papel que cumplen. La clave es la de `rutas.js`.
# No estan las 58: estan las que este rediseno toca y las que ensenan los dos modos.
LAS_PANTALLAS = (
    ("inicio", "#/", "campo", "El primer boton que ve el agricultor."),
    ("tierras", "#/tierras", "campo", "La lista de sus tierras."),
    ("tierras_mapa", "#/tierras/mapa", "campo", "Las tierras en el mapa y en la tabla."),
    ("tierra", "#/tierras/1", "campo", "La ficha de una tierra."),
    ("cuaderno", "#/cuaderno", "campo", "El cuaderno: lo apuntado y lo que hay que apuntar."),
    ("trabajos", "#/trabajos", "campo", "La agenda de los trabajos."),
    ("tareas", "#/tareas", "campo", "Lo que hay que hacer."),
    ("almacen", "#/almacen", "campo", "Lo que hay en el almacen."),
    ("dictado", "#/dictado", "campo", "Decir un apunte en voz alta."),
    ("buscar", "#/buscar", "campo", "Buscar algo entre todo."),
    ("plan", "#/plan", "despacho", "El plan de abono."),
    ("analisis", "#/analisis", "despacho", "Los analisis de laboratorio."),
    ("facturas", "#/facturas", "despacho", "Las facturas de lo comprado."),
    ("ventas", "#/ventas", "despacho", "Lo que se vende."),
    ("maquinaria", "#/maquinaria", "despacho", "Las maquinas."),
    ("papeles", "#/papeles", "despacho", "Los papeles y la bandeja."),
    ("junta", "#/junta", "despacho", "Lo que falta para la Junta."),
    ("ayuda", "#/ayuda", "campo", "La ayuda."),
)

LA_CARPETA = pathlib.Path("..") / "docs" / "diseno" / "capturas"


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def abrir(nav, direccion: str, camino: str) -> None:
    """Abre una direccion y espera a que el texto de la pantalla deje de cambiar."""
    for _ in range(3):
        nav.abrir(f"{direccion}/{camino}", esperar=3.0)
        anterior = ""
        for _ in range(40):
            el_actual = el_texto(nav)
            if el_actual and el_actual == anterior:
                return
            anterior = el_actual
            time.sleep(0.5)


def main() -> int:
    fase = sys.argv[1] if len(sys.argv) > 1 else "before"
    if fase not in ("before", "after"):
        print(f"  fase desconocida: {fase} (vale `before` o `after`)")
        return 2
    la_carpeta = LA_CARPETA / fase
    la_carpeta.mkdir(parents=True, exist_ok=True)
    hechas: list[dict] = []

    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(
            direccion, "rediseno@prueba.local", "una-clave-larga-y-facil", "Ca"
        )
        # Unos datos, para que las pantallas no salgan vacias. Son de mentira y no salen de aqui.
        for i, alias in enumerate(("LA VEGA", "EL PRADO", "LAS ERAS"), start=1):
            _llamar(
                direccion,
                "/api/parcelas",
                token=cuenta["token"],
                metodo="POST",
                cuerpo={
                    "alias": alias,
                    "ref_sigpac": f"47-100-0-0-{i}",
                    "municipio": "Medina del Campo",
                    "superficie_ha": 2.0 + i,
                    "geometria": (
                        f"POLYGON(({-4.72 - i / 100} 41.65, {-4.71 - i / 100} 41.65, "
                        f"{-4.71 - i / 100} 41.66, {-4.72 - i / 100} 41.66, {-4.72 - i / 100} 41.65))"
                    ),
                },
            )

        for vista, (ancho, alto) in LAS_ANCHURAS.items():
            with NavegadorDeVerdad(ancho=ancho, alto=alto) as nav:
                nav.medir(ancho, alto)
                _poner_la_sesion(nav, direccion, cuenta["token"])
                for clave, camino, modo, papel in LAS_PANTALLAS:
                    abrir(nav, direccion, camino)
                    for _ in range(60):
                        if el_texto(nav).strip():
                            break
                        time.sleep(0.5)
                    else:
                        raise RuntimeError(f"No se ha abierto {clave} ({camino}): la pantalla esta en blanco")
                    medida = nav.evaluar("({ancho: innerWidth, alto: innerHeight})")
                    if medida != {"ancho": ancho, "alto": alto}:
                        raise RuntimeError(f"Viewport distinto del solicitado en {clave}: {medida}")
                    crudo = base64.b64decode(
                        nav.orden("Page.captureScreenshot", {"format": "png"})["data"]
                    )
                    nombre = f"{clave}-{vista}.png"
                    (la_carpeta / nombre).write_bytes(crudo)
                    hechas.append(
                        {
                            "page": clave,
                            "route": camino,
                            "mode": modo,
                            "role": papel,
                            "phase": fase,
                            "viewport": vista,
                            "path": f"docs/diseno/capturas/{fase}/{nombre}",
                            "sha256": hashlib.sha256(crudo).hexdigest(),
                            "bytes": len(crudo),
                        }
                    )
                    print(f"  {fase}/{nombre}  ({len(crudo) // 1024} KB)")

    manifiesto = la_carpeta / "manifest.json"
    anterior = {}
    if manifiesto.exists():
        try:
            anterior = {f["path"]: f for f in json.loads(manifiesto.read_text("utf-8"))}
        except (ValueError, KeyError, TypeError):
            anterior = {}
    for ficha in hechas:
        anterior[ficha["path"]] = ficha
    manifiesto.write_text(
        json.dumps(sorted(anterior.values(), key=lambda f: f["path"]), ensure_ascii=False, indent=2),
        "utf-8",
    )
    print(f"\n  {len(hechas)} capturas, en {la_carpeta.resolve()}")
    print(f"  el manifiesto: {manifiesto.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
