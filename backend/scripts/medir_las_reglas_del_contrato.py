"""Medir EN EL NAVEGADOR las reglas de `Components` del contrato (14/10/2026).

**POR QUE EXISTE.** `test_design_md.py` comprueba que el **fichero** del CSS diga lo que el contrato
manda. Eso no basta para las reglas que son de lo que **se ve**: si un boton principal se duplica, si un
boton grande se queda sin icono o si aparece una sombra, el fichero puede estar impecable y la pantalla
no. Este guion abre el navegador de verdad y **mide**.

**Y POR QUE ES UN GUION Y NO UNA PRUEBA.** De las reglas que mide, una **depende de una decision del
dueño** que esta pendiente -si los botones grandes de las pantallas que no son el inicio llevan icono-.
Una prueba que falla por algo que no esta decidido no vale: **se para el trabajo por una pregunta, no por
un fallo**. Asi que aqui se **informa** de esa, y se **falla** solo por las que ya son decision tomada.

Uso:  python scripts/medir_las_reglas_del_contrato.py <direccion> [base-de-la-auditoria]
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"

# Lo que se mide en cada pantalla. **Solo lo que SE VE**: el mismo HTML trae la forma de movil y la de
# escritorio y las separa el CSS (`.solo-escritorio` / `.solo-movil`), asi que contar sin filtrar por
# visibilidad da el doble y **no es un hallazgo del producto** (costo dos mediciones aprenderlo).
MEDIR = """(() => {
  const p = document.querySelector('#pantalla') || document;
  const seVe = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const todos = Array.from(p.querySelectorAll('.boton')).filter(seVe);
  const principales = todos.filter((b) => b.classList.contains('boton-principal'));
  const grandes = todos.filter((b) => b.getBoundingClientRect().height >= 64);
  const tieneIcono = (b) => Boolean(b.querySelector('svg, img, .icono'));
  const conSombra = Array.from(p.querySelectorAll('*'))
    .filter(seVe)
    .filter((e) => { const s = getComputedStyle(e).boxShadow; return s && s !== 'none'; }).length;
  const raiz = getComputedStyle(document.documentElement);
  return {
    principales: principales.length,
    textos_principales: principales.map((b) => (b.innerText || '').trim().slice(0, 30)),
    grandes: grandes.length,
    grandes_con_icono: grandes.filter(tieneIcono).length,
    grandes_sin_icono: grandes.filter((b) => !tieneIcono(b)).map((b) => (b.innerText || '').trim().slice(0, 26)),
    con_sombra: conSombra,
    radio: raiz.getPropertyValue('--radio').trim(),
    letra: raiz.getPropertyValue('--letra').trim(),
  };
})()"""

# Las pantallas que se miden: la de inicio y tres de las que tienen botones grandes.
PANTALLAS = (
    ("#/", "El inicio", 390, 844, True),
    ("#/semillas", "Mis semillas", 390, 844, True),
    ("#/", "El inicio (escritorio)", 1440, 1000, False),
    ("#/almacen", "El almacen (escritorio)", 1440, 1000, False),
)

FALLOS: list[str] = []
PENDIENTE: list[str] = []


def main() -> int:
    print(f"== Las reglas de `Components`, MEDIDAS en el navegador  ({DIRECCION}) ==")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    for ruta, nombre, ancho, alto, movil in PANTALLAS:
        with NavegadorDeVerdad(ancho=ancho, alto=alto) as nav:
            nav.medir(ancho, alto, movil=movil)
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
            )
            nav.abrir(f"{DIRECCION}/{ruta}", esperar=3.0)
            if not nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25):
                FALLOS.append(f"{nombre}: la pantalla no ha montado")
                continue
            m = nav.evaluar(MEDIR)
        print(f"\n  --- {nombre} ({ruta}, {ancho}px) ---")
        print(f"    {json.dumps(m, ensure_ascii=False)}")

        # 1 · «Solo hay uno [boton principal] en la pantalla, y si hay dos, uno de los dos sobra».
        if m["principales"] > 1:
            FALLOS.append(f"{nombre}: {m['principales']} botones principales -> {m['textos_principales']}")
        print(f"    ['{'OK   ' if m['principales'] <= 1 else 'FALLO'}] "
              f"botones principales: {m['principales']}")

        # 2 · «Nada de sombras, degradados ni animaciones» -y al sol una sombra es un borde sucio-.
        if m["con_sombra"]:
            FALLOS.append(f"{nombre}: {m['con_sombra']} elementos con sombra calculada")
        print(f"    ['{'OK   ' if not m['con_sombra'] else 'FALLO'}] elementos con sombra: {m['con_sombra']}")

        # 3 · «El icono y la palabra van siempre juntos» -en el boton de 64 px, el del campo-.
        if m["grandes"]:
            if m["grandes_sin_icono"]:
                PENDIENTE.append(f"{nombre}: {m['grandes_sin_icono']}")
            print(f"    ['{'OK   ' if not m['grandes_sin_icono'] else 'OJO  '}] "
                  f"botones de 64 px: {m['grandes']}, con icono: {m['grandes_con_icono']}"
                  f"{'' if not m['grandes_sin_icono'] else '  sin icono: ' + str(m['grandes_sin_icono'])}")
        else:
            print("    ['--   '] no hay botones de 64 px en esta pantalla (el suelo es 40 en el escritorio)")

    print("\n== LO QUE FALLA, y es decision tomada ==" if FALLOS else "\n== Nada falla de lo ya decidido ==")
    for f in FALLOS:
        print(f"    - {f}")
    if PENDIENTE:
        print("\n== PENDIENTE DE UNA DECISION DEL DUEÑO (no falla, informa) ==")
        print("   «El icono y la palabra van siempre juntos»: estos botones grandes no llevan icono.")
        print("   El contrato dice que si -«quien no lee bien reconoce el dibujo»-, pero **que dibujo**")
        print("   para cada uno es contenido que decide el dueño, no el agente:")
        for p in PENDIENTE:
            print(f"    · {p}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
