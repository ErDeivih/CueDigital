"""Enruta la pantalla de la fusión (14/10/2026).

Va **por línea** y con ancla, y **aborta sin tocar nada** si un ancla no aparece exactamente una vez. Todas las
formas están **leídas** de la pantalla de los terceros, que ya funciona: no se inventa ninguna.
"""

import ast
import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[1]
FUSION = "fusion"
PANTALLA = "pantallaDeLaFusion"


def por_linea(ruta, ancla, nuevas, *, donde="despues"):
    p = RAIZ / ruta
    lineas = p.read_bytes().decode("utf-8").split("\n")
    sitio = [k for k, l in enumerate(lineas) if l.strip() == ancla]
    if len(sitio) != 1:
        raise SystemExit(f"ABORTO en {ruta}: el ancla [{ancla[:50]}] aparece {len(sitio)} veces")
    k = sitio[0]
    s = "\r" if lineas[k].endswith("\r") else ""
    punto = k + 1 if donde == "despues" else k
    lineas[punto:punto] = [(x + s) if s else x for x in nuevas]
    p.write_bytes("\n".join(lineas).encode("utf-8"))
    return k + 1


# --- 1 · La ruta, después de la de los terceros (que es de la misma familia) ---
print("ruta ->", por_linea(
    "web/react/rutas.js",
    '{ clave: "trabajos_a_terceros", patron: ["trabajos-a-terceros"] },',
    [
        "  // **La fusión de dos fichas** (Entrega 5, 14/10/2026): juntar dos contactos que son el mismo. No es una",
        "  // pantalla de la ficha, así que tiene su propia dirección.",
        '  { clave: "fusion", patron: ["fusion"] },',
    ],
))

# --- 2 · El import ---
print("import ->", por_linea(
    "web/app.js",
    'import { pantallaDeLosTrabajosATerceros } from "./react/pantallas/trabajos_a_terceros.js";',
    ['import { pantallaDeLaFusion } from "./react/pantallas/fusion.js";'],
))

# --- 3 · El MAPA (componente -> clave de la pantalla) ---
print("MAPA ->", por_linea(
    "web/app.js",
    'PantallaDeLosTrabajosATerceros: "trabajos_a_terceros",',
    ['  PantallaDeLaFusion: "fusion",'],
))

# --- 4 · La rama del router: **contando**, no anclando ---
#
# Y esto me costó dos rondas, las dos midiendo:
#   · anclando en `return abrirLosTrabajosATerceros(parametros);` la rama se colaba **entre el return y su llave**
#     (ese return es la ÚLTIMA línea de la rama, y su `}` es la siguiente);
#   · anclando en la rama siguiente, `if (clave === "contacto") {` **aparece dos veces** en el fichero.
# Así que no se ancla: se cuenta. Se busca el return de los terceros, se comprueba que su llave es la de después, y la
# rama entra **detrás de esa llave**.
def la_rama_del_router():
    ruta = RAIZ / "web/app.js"
    lineas = ruta.read_bytes().decode("utf-8").split("\n")
    dentro = [k for k, l in enumerate(lineas) if l.strip() == "return abrirLosTrabajosATerceros(parametros);"]
    if len(dentro) != 1:
        raise SystemExit(f"ABORTO: el return de los terceros aparece {len(dentro)} veces")
    k = dentro[0]
    if lineas[k + 1].strip() != "}":
        raise SystemExit("ABORTO: detrás del return de los terceros no está su llave; no toco nada")
    if any('if (clave === "fusion")' in l for l in lineas):
        return "ya estaba"
    punto = k + 2
    s = "\r" if lineas[punto - 1].endswith("\r") else ""
    nuevas = [
        '  if (clave === "fusion") {',
        "    // **La fusión** (Entrega 5): la vista previa la hace el servidor, así que se pide a su puerta.",
        "    return abrirLaFusion(parametros);",
        "  }",
    ]
    lineas[punto:punto] = [(x + s) if s else x for x in nuevas]
    ruta.write_bytes("\n".join(lineas).encode("utf-8"))
    return punto


print("rama ->", la_rama_del_router())

# --- 5 · Los textos y el cargador, antes de la función del estado de los terceros ---
TEXTOS_FUSION = '''
# **La fusión de dos fichas** (Entrega 5, 14/10/2026). Se definen UNA vez y los sirve `interfaz.py`, como todo lo
# demás: dentro de la pantalla saldría MUDA, que es el fallo que ya ha aparecido tres veces en esta casa.
FUSION: dict[str, str] = {
    "titulo": "Juntar dos fichas que son la misma",
    "pista": (
        "Cuando el mismo cliente o el mismo proveedor está apuntado dos veces, se juntan en una. Primero se ve lo "
        "que va a pasar; no se junta nada hasta que tú lo digas."
    ),
    "cargando": "Mirando las dos fichas…",
    "la_que_desaparece": "La que desaparece (la que está de más)",
    "la_que_se_queda": "La que se queda (la buena)",
    "elije_una": "Elige una",
    "ver_lo_que_pasa": "Ver lo que va a pasar",
    "esto_es_lo_que_pasa": "Esto es lo que va a pasar",
    "que": "Qué",
    "de_la_que_desaparece": "De la que desaparece",
    "de_la_que_se_queda": "De la que se queda",
    "los_saldos_no_se_compensan": "Los saldos NO se compensan",
    "nos_debe": "nos debe",
    "le_debemos": "le debemos",
    "no_choca_nada": "No choca nada: se puede juntar tal cual.",
    "lo_que_choca": "Lo que choca, y qué hacer",
    "esto_no_lo_puede_decidir_la_pantalla": (
        "Esto NO lo puede decidir la pantalla: las dos fichas tienen notas escritas y la nota es un sitio único. "
        "Hay que decidir antes qué se hace con ellas."
    ),
    "fusionarlas": "Juntarlas",
    "el_origen_no_se_borra": (
        "La que desaparece NO se borra: se queda apuntando a la que se queda, para que sus enlaces de siempre sigan "
        "teniendo sentido. Y se puede deshacer."
    ),
    "hecho": "Hecho",
    "deshacer": "Deshacer la fusión",
    "deshacer_devuelve_solo_lo_que_trajo": (
        "Deshacer devuelve lo que trajo la fusión. Lo que se haya apuntado después a la ficha que se queda NO se toca."
    ),
}
'''

p = RAIZ / "app/textos.py"
crudo = p.read_bytes().decode("utf-8")
if "FUSION: dict[str, str]" in crudo:
    print("los textos ya estaban")
else:
    salto = "\r\n" if "\r\n" in crudo else "\n"
    p.write_bytes((crudo.rstrip("\r\n") + TEXTOS_FUSION.replace("\n", salto) + salto).encode("utf-8"))
    ast.parse(p.read_bytes().decode("utf-8"))
    print("textos -> escritos en app/textos.py")

# Y se sirven por la puerta de la interfaz, junto a los de los terceros, SIN list().
print("interfaz.py ->", por_linea(
    "app/routers/interfaz.py",
    '"trabajos_a_terceros": textos.TRABAJOS_A_TERCEROS,',
    ['        "fusion": textos.FUSION,'],
))

# --- 6 · La lista del guardián de rutas (compara EN ORDEN, así que va donde va en la tabla) ---
print("rutas.test.js ->", por_linea(
    "tests_js/rutas.test.js",
    '"trabajos_a_terceros",',
    ['  "fusion",'],
))

# --- 7 · El cargador, con la forma LEÍDA: `montar(() => pantalla(props))` y los textos ENVUELTOS ---
cargador = [
    "function estadoDeLaFusion() {",
    "  // **El estado de esta pantalla**, como el de las demás: lo cargado, si se está cargando, y el error.",
    "  estado.pantallas = estado.pantallas || {};",
    "  estado.pantallas.fusion = estado.pantallas.fusion || {",
    "    contactos: [],",
    "    origen_id: \"\",",
    "    destino_id: \"\",",
    "    previa: null,",
    "    resultado: null,",
    "    cargando: false,",
    "    error: \"\",",
    "    aviso: \"\",",
    "  };",
    "  return estado.pantallas.fusion;",
    "}",
    "",
    "function textosDeLaFusion() {",
    "  // **Envuelto, como TODAS las demás pantallas.** Pasarle a la pantalla YA el vocabulario la deja MUDA: es el",
    "  // fallo que ya ha aparecido tres veces aquí.",
    '  return { fusion: t("fusion", {}) };',
    "}",
    "",
    "/** Pinta la fusión tal y como está el estado ahora mismo. */",
    "function pantallaLaFusion() {",
    "  const suyo = estadoDeLaFusion();",
    "  return montar(() =>",
    "    pantallaDeLaFusion({",
    "      textos: textosDeLaFusion(),",
    "      contactos: suyo.contactos || [],",
    "      origen_id: suyo.origen_id,",
    "      destino_id: suyo.destino_id,",
    "      previa: suyo.previa,",
    "      resultado: suyo.resultado,",
    "      cargando: suyo.cargando,",
    "      error: suyo.error,",
    "      aviso: suyo.aviso,",
    "    }),",
    "  );",
    "}",
    "",
    "async function abrirLaFusion(parametros = {}) {",
    "  // **La fusión** (Entrega 5, 14/10/2026). Se piden los contactos, porque la pantalla necesita elegir dos.",
    "  const suyo = estadoDeLaFusion();",
    "  suyo.origen_id = parametros.origen || suyo.origen_id || \"\";",
    "  suyo.destino_id = parametros.destino || suyo.destino_id || \"\";",
    "  suyo.error = \"\";",
    "  suyo.aviso = \"\";",
    "  suyo.cargando = true;",
    "  pantallaLaFusion();",
    "  try {",
    "    const agenda = await apiJson(\"/api/contactos\");",
    "    suyo.contactos = agenda.contactos || [];",
    "  } catch (fallo) {",
    "    // **Si no se puede leer, se dice**: una lista vacía sin explicación parecería que no hay ninguno.",
    "    suyo.error = (fallo && fallo.message) || mensaje(\"no_se_pudo\");",
    "    suyo.contactos = [];",
    "  }",
    "  suyo.cargando = false;",
    "  return pantallaLaFusion();",
    "}",
    "",
]
lineas = (RAIZ / "web/app.js").read_bytes().decode("utf-8").split("\n")
k = next(k for k, l in enumerate(lineas) if l.startswith("function estadoDeLosTrabajosATerceros()"))
s = "\r" if lineas[k].endswith("\r") else ""
lineas[k:k] = [(x + s) if s else x for x in cargador]
(RAIZ / "web/app.js").write_bytes("\n".join(lineas).encode("utf-8"))
print("cargador -> antes de la línea", k + 1)

# --- 8 · Y la comprobación que faltaba las otras veces: que los textos que pide la pantalla EXISTAN ---
pantalla = (RAIZ / "web/react/pantallas/fusion.js").read_bytes().decode("utf-8")
usadas = sorted(set(re.findall(r"\bt\.([a-z_]+)", pantalla)))
trozo = (RAIZ / "app/textos.py").read_bytes().decode("utf-8").split("FUSION: dict[str, str]")[1].split("\n}")[0]
definidas = set(re.findall(r'"([a-z_]+)":', trozo))
faltan = [c for c in usadas if c not in definidas]
if faltan:
    raise SystemExit(f"ABORTO: la pantalla pide textos que no existen: {faltan}")
print(f"textos comprobados: la pantalla usa {len(usadas)} claves y están todas")
print("ENRUTADA: ruta, import, MAPA, rama, cargador, textos, interfaz y la lista del guardián")
