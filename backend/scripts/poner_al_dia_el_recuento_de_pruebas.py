"""La suite entera, el recuento real y los documentos al día (08/10/2026).

**Por qué un guion.** El recuento de pruebas de Python aparece en varios documentos, y cada vez que se añade una
prueba o un guion hay que moverlo. Hacerlo a mano ha fallado ya dos veces (una por no encontrarlo y otra por
dejarlo a medias). Esto lo hace entero: corre la suite **completa**, lee el número **real** del informe, pone ese
número en **todos** los `.md` del repositorio (fuera del entorno virtual) y vuelve a pasar la suite para
comprobar que el guardián del recuento queda en verde.

Uso:  python scripts/poner_al_dia_el_recuento_de_pruebas.py
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

RAIZ = pathlib.Path(__file__).resolve().parents[1]  # backend/
REPO = RAIZ.parent
# Los números que han estado puestos en los documentos. Se sustituyen **todos** por el real.
LOS_VIEJOS = ("4665", "4666", "4670", "4672", "4673", "4674", "4675")
# **Sólo los documentos que llevan el recuento** (08/10/2026). Antes esto barría **todos** los `.md` del
# repositorio, y eso **destrozó una huella SHA-256** en `data/fega/LEEME.md` -el hash llevaba la cifra `4672`
# dentro-, que un guardián caza. Un reemplazo a lo bruto por todo el repositorio **no es un atajo, es un riesgo**:
# aquí va la lista, y si algún día hay otro documento con el recuento, se añade a mano.
LOS_DOCUMENTOS = ("README.md", "AGENTS.md", "docs/LO_QUE_PIDE_LA_JUNTA.md")


def correr_la_suite() -> tuple[int, int, int, list[str]]:
    """Devuelve (recogidas, fallos, errores, **los nombres de los que fallan**).

    POR QUÉ DEVUELVE LOS NOMBRES (11/10/2026). El informe XML que se escribía ya los traía, pero **no se
    imprimían**, y me costó una ronda: el recuento dijo «4792 recogidas, 1 fallos» **dos veces seguidas**, y
    como no decía cuáles hubo que correr la suite entera otra vez para averiguarlo —y en esa corrida salió
    verde, así que el fallo era **intermitente y se quedó sin nombre**—. Un recuento que dice que algo falla y
    no dice **qué** es un instrumento a medias: la próxima vez el nombre queda escrito.
    """
    informe = pathlib.Path(tempfile.gettempdir()) / "el-recuerdo.xml"
    suyo = subprocess.run(  # noqa: S603 — es el propio proyecto
        [sys.executable, "-m", "pytest", "tests", "-q", f"--junit-xml={informe}"],
        cwd=str(RAIZ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if not informe.exists():
        print(suyo.stdout[-1500:] if suyo.stdout else "(sin salida)")
        return (0, 1, 0, [])
    arbol = ET.parse(informe).getroot()
    suite = arbol if arbol.tag == "testsuite" else arbol.find("testsuite")
    fallando = [
        f"{caso.get('classname', '')}::{caso.get('name', '')}"
        for caso in suite.iter("testcase")
        if list(caso.iter("failure")) or list(caso.iter("error"))
    ]
    return (
        int(suite.get("tests", 0)),
        int(suite.get("failures", 0)),
        int(suite.get("errors", 0)),
        fallando,
    )


def _decir_lo_que_falla(fallando: list[str]) -> None:
    """Los nombres, uno por línea y con su archivo: sin esto, «1 fallos» no dice nada que se pueda buscar."""
    for nombre in fallando:
        print(f"   FALLA: {nombre}")


def poner_el_recuento(real: str) -> list[str]:
    """Pone el recuento **sólo** en los documentos que lo llevan, y **descubre** el número viejo leyéndolo.

    El guardián de la casa -el del recuento- cazó que mi **lista de números viejos** se quedaba corta: decía 4679
    y no estaba en la lista, así que el guion **no escribía nada** y la suite seguía en rojo. Ahora el número
    viejo **se lee del README** en vez de llevarse en una lista que hay que acordarse de ampliar.
    """
    los_viejos = set(LOS_VIEJOS)
    try:
        # **Sólo la línea de Python** (08/10/2026). Mirando cualquier «NNNN tests» del README, este guion
        # sustituyó también el recuento de **JavaScript** -1077- por el de Python, y el guardián de los números
        # de la documentación **lo cazó**. Aquí se lee **sólo la línea del pytest**, que es la que lleva el
        # recuento de Python; el de JavaScript tiene su propia línea y no se toca.
        las_del_readme = (REPO / "README.md").read_text(encoding="utf-8").splitlines()
        las_del_pytest = " ".join(uno for uno in las_del_readme if "pytest" in uno)
        los_viejos.update(re.findall(r"(\d{4})\s+tests", las_del_pytest))
    except OSError:
        print("   (no he podido leer el README para descubrir el número viejo)")
    tocados = []
    for nombre in LOS_DOCUMENTOS:
        fichero = REPO / nombre
        if not fichero.exists():
            print(f"   (no está: {nombre})")
            continue
        texto = fichero.read_text(encoding="utf-8")
        nuevo = texto
        for viejo in los_viejos:
            if viejo != real:
                nuevo = nuevo.replace(viejo, real)
        if nuevo != texto:
            fichero.write_text(nuevo, encoding="utf-8")
            tocados.append(nombre)
    return tocados


def main() -> int:
    print("1) la suite entera, tal como está:")
    recogidas, fallos, errores, fallando = correr_la_suite()
    print(f"   {recogidas} recogidas, {fallos} fallos, {errores} errores")
    _decir_lo_que_falla(fallando)
    if not recogidas:
        print("=> no he podido leer el recuento del informe: mira la salida de arriba")
        return 1

    real = str(recogidas)
    print(f"2) el recuento real es **{real}**: se pone en todos los documentos")
    tocados = poner_el_recuento(real)
    for fichero in tocados:
        print(f"   · {fichero}")

    print("3) y la suite entera otra vez, para ver el guardián del recuento en verde:")
    recogidas2, fallos2, errores2, fallando2 = correr_la_suite()
    print(f"   {recogidas2} recogidas, {fallos2} fallos, {errores2} errores")
    _decir_lo_que_falla(fallando2)

    if recogidas2 == recogidas and fallos2 == 0 and errores2 == 0:
        print(f"\n=> EN VERDE: {real} pruebas de Python, 0 fallos, y los documentos al día")
        return 0
    print("\n=> sigue habiendo algo: mira los fallos de arriba")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
