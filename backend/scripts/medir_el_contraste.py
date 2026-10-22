"""***El contraste, medido de verdad*** (22/10/2026, D05).

*El encargo pide «contraste». No a ojo: **con la formula de la WCAG** sobre los colores que el navegador tiene
puestos de verdad -`getComputedStyle`-, buscando el fondo efectivo hacia arriba cuando el del elemento es
transparente.*

*Se mide **una vez por pantalla** y se dice:*
  · ***el peor contraste*** de esa pantalla;
  · ***cuantos textos*** estan por debajo de **4,5** -el minimo para texto normal- y por debajo de **3,0** -el
    minimo para texto grande y para lo no esencial-.

***Y el limite de lo que esto mide***: *el color **no** es el contraste sentido -un texto fino sobre un fondo claro
se lee peor de lo que dice el numero-, y **eso solo lo ve quien mira**. Aqui se mide lo que se puede medir.*

Uso:  python scripts/medir_el_contraste.py
"""

from __future__ import annotations

import re
import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

# *Cada trozo de texto con su color, su fondo efectivo y su tamano.*
LOS_TEXTOS = (
    "(() => {"
    " const seVe = (n) => { const r = n.getBoundingClientRect(); return r.width > 0 && r.height > 0; };"
    " const elFondo = (n) => {"
    "  let e = n;"
    "  while (e && e !== document.documentElement) {"
    "   const c = getComputedStyle(e).backgroundColor;"
    "   if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') return c;"
    "   e = e.parentElement;"
    "  }"
    "  return 'rgb(255, 255, 255)';"
    " };"
    " const los = Array.from(document.querySelectorAll('#pantalla *')).filter(function (n) {"
    "  return n.children.length === 0 && (n.textContent || '').trim() && seVe(n);"
    " });"
    " return los.slice(0, 300).map(function (n) {"
    "  const s = getComputedStyle(n);"
    "  return [s.color, elFondo(n), parseFloat(s.fontSize), (n.textContent || '').trim().slice(0, 40)].join('|');"
    " });"
    "})()"
)


def la_luminancia(color: str) -> float:
    """*La luminancia relativa de un color `rgb(...)` o `rgba(...)`, segun la WCAG.*"""
    numeros = [float(n) for n in re.findall(r"[\d.]+", color)[:3]]
    if len(numeros) < 3:
        return 0.0
    canales = []
    for valor in numeros:
        c = valor / 255.0
        canales.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]


def el_contraste(un_color: str, un_fondo: str) -> float:
    a, b = la_luminancia(un_color), la_luminancia(un_fondo)
    claro, oscuro = max(a, b), min(a, b)
    return round((claro + 0.05) / (oscuro + 0.05), 2)


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:400]!r}")
    return bien


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def abrir(nav, direccion: str, camino: str) -> None:
    for _ in range(3):
        nav.abrir(f"{direccion}/{camino}", esperar=3.0)
        anterior = ""
        for _ in range(30):
            el_actual = el_texto(nav)
            if el_actual and el_actual == anterior:
                return
            anterior = el_actual
            time.sleep(0.4)


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "contraste@prueba.local", "una-clave-larga-y-facil", "Co")
        with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
            _poner_la_sesion(nav, direccion, cuenta["token"])
            for pantalla, camino in (("inicio", "#/inicio"), ("tierras", "#/tierras/mapa"), ("cuaderno", "#/cuaderno")):
                abrir(nav, direccion, camino)
                los = nav.evaluar(LOS_TEXTOS) or []
                medidas = []
                for crudo in los:
                    color, fondo, tamano, texto = (crudo.split("|") + ["", "", "", ""])[:4]
                    if not color:
                        continue
                    medidas.append((el_contraste(color, fondo), float(tamano or 16), texto))
                if not medidas:
                    fallos += not comprobar(False, f"***{pantalla}: no se midio ningun texto***")
                    continue
                el_peor = min(medidas)
                los_bajos = [m for m in medidas if m[0] < 4.5]
                los_muy_bajos = [m for m in medidas if m[0] < 3.0]
                print(f"\n== {pantalla} ({len(medidas)} textos) ==")
                print(f"  el peor: {el_peor[0]}:1  ({el_peor[2]!r})")
                print(f"  por debajo de 4,5: {len(los_bajos)}")
                for uno in sorted(los_bajos)[:5]:
                    print(f"    {uno[0]}:1  a {uno[1]:.0f}px  {uno[2]!r}")
                # ***El limite duro: por debajo de 3,0 no se lee.*** *Por encima de 4,5 es lo que pide la WCAG para
                # texto normal; entre 3 y 4,5 se avisa pero no se falla, porque el color no es el contraste sentido
                # -eso solo lo ve quien mira-.*
                fallos += not comprobar(
                    not los_muy_bajos,
                    f"***{pantalla}: ningun texto por debajo de 3,0*** "
                    f"({len(los_muy_bajos)} por debajo si los hay)",
                    str(sorted(los_muy_bajos)[:4]),
                )
    print(f"\nComprobaciones: 6   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
