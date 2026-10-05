"""La lista de lo que pide la Junta no puede mentir.

Este test existe por un fallo real: el resumen de `docs/LO_QUE_PIDE_LA_JUNTA.md` decía
«13 secciones hechas, 4 a medias, 0 sin empezar», y **no sumaba 21**: eran 17. Además decía
que no faltaba ninguna sección cuando la cosecha comercializada llevaba desde el principio
marcada como inexistente.

La tabla estaba bien; el total estaba mal contado a mano. Ese es justo el tipo de dato que
este proyecto no puede permitirse: la lista existe para decir la verdad sobre lo que falta,
y un total que no cuadra la convierte en una lista en la que no se puede confiar.

**Y en la ronda 13 pasó lo contrario, que es peor y enseña más.** El total sumaba 21 y la fila 21
era «Utilidades: Ver listados». Pero «Utilidades» **no es un apartado del cuaderno**: es el menú
donde están los informes. El apartado que faltaba de verdad era **Documentación** —el repositorio
de papeles que la app oficial tiene y aquí no existía—. Es decir: **un total correcto con un
elemento equivocado dentro pasa cualquier suma**. Este test contaba filas; no miraba qué había en
ellas. Por eso ahora hay además una comprobación de que la última fila es la de documentación, y
de que la corrección está escrita en el documento con su motivo.

Lo que se comprueba aquí:

1. Que el resumen suma 21 y que cada número coincide con lo que dice la tabla.
2. Que los 21 son los que dice el documento oficial: veinte apartados más el repositorio de
   documentación.
3. Que ningún número de test escrito a mano en la documentación se queda viejo.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
LISTA = RAIZ / "docs" / "LO_QUE_PIDE_LA_JUNTA.md"

ESTADOS = {"✅": "hechas", "⚠️": "a medias", "❌": "sin empezar"}


def cuantos(ruta: Path, patron: str) -> int | None:
    """El número de pruebas que la documentación dice, leído con su patrón.

    Devuelve `None` si el patrón no aparece: así una frase reescrita se nota en vez de
    compararse contra un cero que no significa nada.
    """
    encontrado = re.search(patron, ruta.read_text(encoding="utf-8"))
    return int(encontrado.group(1)) if encontrado else None


def _apartado(numero: int) -> str:
    """El texto de un apartado del documento, sin los demás.

    Hace falta separarlos porque la tabla del apartado 1 y la del 2 empiezan las dos por un
    número, y contar las dos juntas daría 23 «secciones» en vez de 21. Ese fue el primer
    fallo de este mismo test, y por eso se deja escrito.
    """
    texto = LISTA.read_text(encoding="utf-8")
    trozo = texto.split(f"## {numero}.", 1)[1]
    return trozo.split(f"## {numero + 1}.", 1)[0]


def _filas_de_la_tabla_de_secciones() -> dict[str, list[int]]:
    """Saca de la tabla del apartado 1 qué secciones hay en cada estado."""
    numeros: dict[str, list[int]] = {estado: [] for estado in ESTADOS}
    for linea in _apartado(1).splitlines():
        if not linea.startswith("| "):
            continue
        celdas = [celda.strip() for celda in linea.strip("|").split("|")]
        if len(celdas) < 3 or not celdas[0].isdigit():
            continue
        for estado in ESTADOS:
            if celdas[2] == estado:
                numeros[estado].append(int(celdas[0]))
    return numeros


def _resumen_del_apartado_uno() -> dict[str, int]:
    """Los tres números del resumen: hechas, a medias y sin empezar.

    Se admiten las dos palabras, «secciones» y «apartados», a propósito: el documento oficial
    dice «seis secciones con veinte apartados…, además de un repositorio de documentación», así
    que las 21 filas son apartados, no secciones. Confundir las dos palabras fue parte del motivo
    de que «Utilidades» estuviera en la tabla como si fuera uno de ellos. La primera versión de
    este test exigía «secciones hechas», y por eso no lo cazó.
    """
    trozo = _apartado(1)
    encontrado = re.search(
        r"\*\*Resumen: (\d+) (?:secciones|apartados) hech[oa]s, (\d+) a medias, "
        r"(\d+) sin empezar\*\*",
        trozo,
    )
    assert encontrado, "no encuentro la línea del resumen en el apartado 1"
    return {
        "hechas": int(encontrado.group(1)),
        "a medias": int(encontrado.group(2)),
        "sin empezar": int(encontrado.group(3)),
    }


class TestElResumenCuadraConLaTabla:
    def test_hay_veintiuna_secciones(self):
        """La app oficial CUECyL tiene 21 secciones. Ni una más, ni una menos."""
        numeros = _filas_de_la_tabla_de_secciones()
        todos = sorted(n for lista in numeros.values() for n in lista)
        assert todos == list(range(1, 22)), f"las secciones numeradas son: {todos}"

    def test_el_resumen_dice_la_verdad(self):
        numeros = _filas_de_la_tabla_de_secciones()
        resumen = _resumen_del_apartado_uno()
        for estado, nombre in ESTADOS.items():
            cuantos = len(numeros[estado])
            assert resumen[nombre] == cuantos, (
                f"la tabla dice {cuantos} {nombre} y el resumen dice {resumen[nombre]}. "
                f"Secciones {nombre}: {numeros[estado]}"
            )
        assert sum(resumen.values()) == 21, f"el resumen no suma 21: {resumen}"

    def test_ninguna_seccion_esta_sin_clasificar(self):
        numeros = _filas_de_la_tabla_de_secciones()
        clasificadas = sum(len(lista) for lista in numeros.values())
        assert clasificadas == 21, f"solo {clasificadas} secciones tienen estado"

    def test_la_ultima_fila_es_el_repositorio_de_documentacion(self):
        """**Este test existe por un fallo real, y de los que más cuesta ver.**

        Hasta la ronda 13 la fila 21 era «Utilidades: Ver listados». El total sumaba 21 y este
        fichero lo daba por bueno, porque solo contaba filas. Pero «Utilidades» es el menú donde
        están los informes, no un apartado que se cumplimente, y el apartado que faltaba de
        verdad era **Documentación**, que no estaba en ninguna parte.

        De dónde sale el 21, con las palabras del documento oficial
        (`03_CastillaYLeon_CUECyL_instrucciones.pdf`): *«El Cuecyl se estructura en seis secciones
        con veinte apartados organizados por su temática…, además de un repositorio de
        documentación.»* O sea: veinte apartados más el repositorio. Las filas 1 a 20 son los
        veinte apartados uno por uno; la 21 tiene que ser el repositorio.
        """
        texto = LISTA.read_text(encoding="utf-8")
        assert "**Documentación anexa**" in texto, (
            "la fila 21 tiene que ser el repositorio de documentación, que es lo que dice el "
            "documento oficial («además de un repositorio de documentación»)"
        )
        # Y no puede volver a colarse un menú como si fuera un apartado.
        filas = [
            linea
            for linea in _apartado(1).splitlines()
            if linea.startswith("| ") and linea.strip("|").split("|")[0].strip().isdigit()
        ]
        assert not any("Utilidades" in fila for fila in filas), (
            "«Utilidades» es el menú de los informes, no un apartado del cuaderno: no puede "
            "ocupar una fila de la tabla"
        )

    def test_la_correccion_esta_escrita_con_su_motivo(self):
        """Un número que cambia sin decir por qué es un número en el que no se puede confiar."""
        texto = LISTA.read_text(encoding="utf-8")
        # Se juntan los saltos de línea y se quitan los «>» de las citas antes de buscar: si no,
        # una frase que el documento parte en dos líneas —o que cae dentro de un bloque de cita—
        # no se encuentra, y el test fallaría por cómo está maquetado el texto en vez de por lo
        # que dice. Fue el primer fallo de este mismo test, y el segundo fue el «>».
        plano = " ".join(texto.replace(">", " ").split())
        assert "Corrección de la ronda 13" in plano
        assert "no es un apartado del cuaderno" in plano
        # Y la frase del documento oficial, para que la razón quede en el repositorio.
        assert "seis secciones con veinte apartados" in plano

    def test_lo_que_pide_la_junta_tambien_cuadra(self):
        """El apartado 2 son 10 cosas, y su resumen tiene que sumar 10.

        Es exactamente el fallo de antes: un total escrito a mano que no cuadra con nada.
        El resumen de esas diez cosas está al final del apartado 1, justo debajo de su
        tabla; se comprueba ahí y no en el apartado 2.
        """
        trozo = _apartado(1)
        assert "diez cosas" in trozo or "10 cosas" in trozo, "no encuentro el resumen"
        encontrado = re.search(
            r"(?:diez|10)\s+cosas\):\s*\*\*(.+?)\*\*",
            trozo,
            flags=re.DOTALL,
        )
        assert encontrado, "no encuentro el resumen de las diez cosas de la Junta"
        # Se suman TODOS los números del resumen, sin exigir cómo están redactados: así el
        # test sigue valiendo si un día la frase cambia de forma, y lo que sigue comprobando
        # es lo que importa, que el total cuadre.
        numeros = [int(n) for n in re.findall(r"\d+", encontrado.group(1))]
        assert numeros, f"el resumen no tiene números: {encontrado.group(1)!r}"
        assert sum(numeros) == 10, f"el resumen de esas diez cosas suma {sum(numeros)}: {numeros}"

    def test_las_filas_del_apartado_dos_son_diez(self):
        filas = [
            linea
            for linea in _apartado(2).splitlines()
            if linea.startswith("| ") and linea.strip("|").split("|")[0].strip().isdigit()
        ]
        assert len(filas) == 10, f"el apartado 2 tiene {len(filas)} filas"

    def test_el_resumen_del_apartado_dos_cuenta_lo_que_dice_la_tabla(self):
        """Cada número del resumen tiene que salir de contar los iconos de la tabla.

        **Esto se añadió en la ronda 35 y hacía falta.** El resumen decía «1 hecha, 3 a medias, 6 que
        dependen de David» y la tabla tenía **1, 4 y 5**: sumaba 10 igual, así que el test que solo
        miraba el total lo daba por bueno. Es la misma lección de la ronda 13 —«un total correcto con
        un elemento equivocado dentro pasa cualquier suma»— un escalón más abajo: aquí lo que estaba
        mal no era el total, sino **cómo se repartía**. Ahora se cuentan los iconos, uno por uno.
        """
        filas = [
            linea
            for linea in _apartado(2).splitlines()
            if linea.startswith("| ") and linea.strip("|").split("|")[0].strip().isdigit()
        ]
        iconos = [linea.split("|")[3].strip() for linea in filas]
        hechas = sum(1 for icono in iconos if "✅" in icono)
        a_medias = sum(1 for icono in iconos if "⚠️" in icono)
        dependen = sum(1 for icono in iconos if "🔒" in icono)
        assert hechas + a_medias + dependen == len(filas), (
            f"hay filas sin estado claro: {iconos}"
        )

        resumen = re.search(r"cosas\):\s*\*\*(.+?)\*\*", _apartado(1), flags=re.DOTALL)
        assert resumen, "no encuentro el resumen de las diez cosas"
        numeros = [int(n) for n in re.findall(r"\d+", resumen.group(1))]
        assert numeros == [hechas, a_medias, dependen], (
            f"el resumen dice {numeros} y la tabla tiene "
            f"{hechas} hechas, {a_medias} a medias y {dependen} que dependen de David"
        )

    def test_los_numeros_de_test_de_la_documentacion_no_se_quedan_viejos(self):
        """README y AGENTS dicen cuántos tests hay, y los dos tienen que decir lo mismo.

        El número exacto lo comprueba `pytest` solo (los cuenta él). Lo que aquí se
        comprueba es que las dos documentaciones no se contradigan: cuando una se
        actualiza y la otra no, alguien lee la vieja y deja de fiarse de las dos.
        """
        en_readme = cuantos(RAIZ / "README.md", r"m pytest\s+# (\d+) tests")
        en_agents = cuantos(RAIZ / "AGENTS.md", r"# Python \((\d+) tests\)")
        en_lista = cuantos(LISTA, r"tenía (\d+) tests de Python")
        assert en_readme == en_agents == en_lista, (
            f"los tests de Python se cuentan distinto: README {en_readme}, "
            f"AGENTS {en_agents}, lista de la Junta {en_lista}"
        )

        # **Y el número tiene que ser el de verdad, no solo coincidir entre los tres documentos.**
        # La documentación decía 279 cuando había 278: los tres decían lo mismo y los tres estaban
        # mal, que es justo el fallo que este test existe para cazar. Se cuentan los ficheros, uno por
        # uno, con los mismos números que da `node --test`.
        js_de_verdad = 0
        for fichero in sorted((RAIZ / "backend" / "tests_js").glob("*.test.js")):
            texto = fichero.read_text(encoding="utf-8")
            js_de_verdad += len(re.findall(r"^test\(", texto, re.M))
        assert js_de_verdad > 0, "no se ha contado ninguna prueba de JavaScript"

        js_readme = cuantos(RAIZ / "README.md", r"tests_js/\*\.test\.js\"\s+# (\d+) tests")
        js_agents = cuantos(RAIZ / "AGENTS.md", r"# JavaScript \((\d+) tests\)")
        js_lista = cuantos(LISTA, r"y (\d+) de JavaScript")
        assert js_readme == js_agents == js_lista, (
            f"los tests de JavaScript se cuentan distinto: README {js_readme}, "
            f"AGENTS {js_agents}, lista de la Junta {js_lista}"
        )
        assert js_readme == js_de_verdad, (
            f"la documentación dice {js_readme} pruebas de JavaScript y hay {js_de_verdad} "
            "(contadas en los ficheros de `tests_js/`)"
        )

    def test_el_numero_de_pruebas_de_python_es_el_de_verdad(self, request):
        """El número de pruebas de Python no solo tiene que cuadrar: tiene que ser el de verdad.

        **Esto faltaba, y por eso el número se quedó viejo dos veces en el mismo día** (02/10/2026).
        De JavaScript sí se comprueba contra la realidad —se cuentan los `test(` de los ficheros de
        `tests_js/`—, pero de Python solo se comparaba **entre los tres documentos**: los tres decían
        3663 y había 3677, así que el guardián estaba verde y la documentación mentía. Es el mismo
        fallo que este fichero existe para cazar —«los tres decían lo mismo y los tres estaban mal»—
        un escalón más arriba. Aquí al que se le pregunta es a **`pytest`**, que es quien los cuenta.

        **La limitación, dicha y no escondida:** si se corre solo una parte de la suite, lo recogido
        es menos que el total y de ahí no se puede concluir nada; en ese caso la prueba **se salta
        diciéndolo**, en vez de dar un «todo bien» falso o un rojo falso. Lo que sí caza es lo que ha
        pasado hoy dos veces: se añaden pruebas, la documentación se queda atrás, y nadie se entera.
        """
        documentado = cuantos(RAIZ / "README.md", r"m pytest\s+# (\d+) tests")
        assert documentado, "no encuentro el número de pruebas de Python en el README"
        recogidas = request.session.testscollected
        if recogidas < documentado:
            pytest.skip(
                f"se ha recogido solo una parte de la suite ({recogidas} de {documentado}): "
                "así no se puede comprobar el total"
            )
        assert recogidas == documentado, (
            f"la documentación dice {documentado} pruebas de Python y hay {recogidas}. "
            "Actualiza el recuento en README.md, AGENTS.md y docs/LO_QUE_PIDE_LA_JUNTA.md "
            "(los tres, y con el número medido, no con el que había antes)"
        )
