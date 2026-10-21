"""Tests de la interfaz del agricultor (el "Modo Sencillo").

Lo que se comprueba aquí es lo que los tests del backend no cubrían: que la interfaz
se sirve, que el vocabulario que usa está libre de jerga y que los ficheros de la
pantalla han quedado de verdad en su sitio.

Lo que NO se puede comprobar aquí, y conviene tenerlo claro: que la pantalla se vea
bien en un móvil de verdad y que un agricultor sepa usarla. Eso exige la prueba con
tres agricultores del apartado 5.18 del documento del MVP, y no la sustituye ningún
test automático.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app import catalogos, textos

WEB = Path(__file__).resolve().parents[1] / "web"
TESTS_JS = Path(__file__).resolve().parents[1] / "tests_js"

FICHEROS_WEB = [
    "index.html",
    "estilos.css",
    "app.js",
    "nucleo.js",
    "manifest.webmanifest",
    "service-worker.js",
]


# --------------------------------------------------------------------------
# Utilidades para revisar el texto que de verdad se ve
# --------------------------------------------------------------------------


def quita_comentarios_html(texto: str) -> str:
    return re.sub(r"<!--.*?-->", " ", texto, flags=re.DOTALL)


def quita_comentarios_js(texto: str) -> str:
    """Quita los comentarios de JavaScript, **respetando lo que va dentro de las comillas**.

    Hace falta quitar los comentarios porque las palabras prohibidas sí pueden aparecer en uno
    explicando por qué están prohibidas; lo que no puede aparecer es en pantalla.

    Y hace falta respetar las comillas por un fallo que se encontró de verdad: con
    `re.sub(r"/\\*.*?\\*/", ...)` (lo que había antes), un `accept=".pdf,image/*"` lleva un `/*`
    dentro de una comilla, y esa expresión lo tomaba por el principio de un comentario y **borraba
    todo** hasta el siguiente `*/` que hubiera en el fichero. El resultado no era solo un aviso
    falso: era que todo lo que caía en medio **se quedaba sin revisar** en silencio. Un test que se
    come el fichero es peor que no tenerlo, porque da la sensación de que revisa.

    Y las expresiones regulares también se respetan, porque aquí las hay con comillas dentro:
    `.replace(/"/g, "&quot;")` es un `"` que no abre ninguna cadena. Sin esto, esa comilla se comía
    el fichero hasta la siguiente comilla, comentarios incluidos (es el segundo fallo real de este
    mismo recorrido, y por eso hay tests de las dos cosas).

    Y hay un tercero, que es el peor de los tres **porque no se notaba**: una plantilla con otra
    plantilla dentro (`` `${a ? html`<b/>` : null}` ``) cerraba donde no era, y a partir de ahí el
    fichero entero iba descolocado. Los comentarios dejaban de quitarse y su texto se revisaba
    como si fuera de pantalla. Se destapó al añadir la pantalla del almacén: un comentario que
    decía «tal y como los sirve `/api/interfaz`» hizo saltar el aviso de jerga por una frase que
    el agricultor no ve. Lo que estaba roto no era el comentario, era el quitador.
    """
    limpio, _ = _limpia_un_trozo(texto, 0, None)
    return limpio


def _limpia_un_trozo(texto: str, indice: int, fin: str | None) -> tuple[str, int]:
    """Quita los comentarios de un trozo de JavaScript y dice por dónde sigue.

    `fin` es el carácter que cierra el trozo cuando se está **dentro del `${…}` de una
    plantilla** (`"}"`), y `None` cuando es el fichero entero. Se cuenta el anidamiento de
    llaves porque dentro de un `${…}` puede haber objetos (`${f(x, { a: 1 })}`), y sin contarlas
    la expresión se cerraría en la primera llave y volvería el descoloque.
    """
    salida: list[str] = []
    ultimo = ""
    llaves = 0
    largo = len(texto)
    while indice < largo:
        caracter = texto[indice]
        if caracter in "\"'":
            trozo, indice = _copia_una_cadena(texto, indice, caracter)
            salida.append(trozo)
            ultimo = caracter
            continue
        if caracter == "`":
            trozo, indice = _copia_una_plantilla(texto, indice)
            salida.append(trozo)
            ultimo = "`"
            continue
        if fin is not None and caracter == "{":
            llaves += 1
            salida.append(caracter)
            indice += 1
            continue
        if fin is not None and caracter == "}":
            if llaves == 0:
                return "".join(salida), indice
            llaves -= 1
            salida.append(caracter)
            indice += 1
            continue
        if caracter == "/" and indice + 1 < largo and texto[indice + 1] == "/":
            while indice < largo and texto[indice] not in "\r\n":
                indice += 1
            continue
        if caracter == "/" and indice + 1 < largo and texto[indice + 1] == "*":
            indice += 2
            while indice < largo and not (
                texto[indice] == "*" and indice + 1 < largo and texto[indice + 1] == "/"
            ):
                indice += 1
            indice += 2
            continue
        if caracter == "/" and _abre_una_expresion_regular(ultimo):
            salida.append(caracter)
            indice += 1
            dentro_de_corchetes = False
            while indice < largo:
                if texto[indice] == "\\":
                    salida.append(texto[indice : indice + 2])
                    indice += 2
                    continue
                if texto[indice] == "\n":
                    break
                if texto[indice] == "[":
                    dentro_de_corchetes = True
                elif texto[indice] == "]":
                    dentro_de_corchetes = False
                elif texto[indice] == "/" and not dentro_de_corchetes:
                    salida.append(texto[indice])
                    indice += 1
                    break
                salida.append(texto[indice])
                indice += 1
            ultimo = "/"
            continue
        if not caracter.isspace():
            ultimo = caracter
        salida.append(caracter)
        indice += 1
    return "".join(salida), indice


def _copia_una_cadena(texto: str, indice: int, comilla: str) -> tuple[str, int]:
    """Copia tal cual una cadena entre comillas simples o dobles.

    Dentro de una cadena no hay comentarios que quitar: lo que parezca uno es parte del texto.
    """
    salida = [comilla]
    indice += 1
    while indice < len(texto):
        if texto[indice] == "\\":
            salida.append(texto[indice : indice + 2])
            indice += 2
            continue
        salida.append(texto[indice])
        if texto[indice] == comilla:
            indice += 1
            break
        indice += 1
    return "".join(salida), indice


def _copia_una_plantilla(texto: str, indice: int) -> tuple[str, int]:
    """Copia una plantilla (`` `` `…` `` ``), quitando los comentarios de sus `${…}`.

    **Por qué no basta con buscar la siguiente comilla.** Una plantilla puede llevar dentro
    otras plantillas —`` `${a ? html`<b/>` : null}` ``—, y cada `${…}` puede llevar llaves,
    comillas y expresiones regulares. Buscando a ciegas la siguiente comilla, la plantilla de
    fuera se cerraba en la de dentro y **el programa entero se descolocaba**. Se encontró con un
    `<b … />` dentro de un `${…}`: la barra de `/>` va detrás de la llave de `${d}`, y la
    heurística de «una barra detrás de `}` abre una expresión regular» se la comía, con la
    comilla que cerraba la plantilla de dentro incluida.
    """
    salida = ["`"]
    indice += 1
    largo = len(texto)
    while indice < largo:
        caracter = texto[indice]
        if caracter == "\\":
            salida.append(texto[indice : indice + 2])
            indice += 2
            continue
        if caracter == "`":
            salida.append("`")
            indice += 1
            break
        if caracter == "$" and indice + 1 < largo and texto[indice + 1] == "{":
            salida.append("${")
            indice += 2
            trozo, indice = _limpia_un_trozo(texto, indice, "}")
            salida.append(trozo)
            if indice < largo:
                salida.append("}")
                indice += 1
            continue
        salida.append(caracter)
        indice += 1
    return "".join(salida), indice


def _abre_una_expresion_regular(ultimo: str) -> bool:
    """¿Esa barra abre una expresión regular o es una división?

    Es la heurística de siempre: después de un valor (un número, un paréntesis que se cierra, una
    palabra) una barra divide; después de un operador, de una apertura o del principio del fichero,
    abre una expresión regular. No es un analizador de JavaScript ni falta que hace: lo que hace
    falta es no confundir el `"` de `/"/g` con el principio de una cadena.

    **El `<` NO cuenta como apertura.** Lo estaba, y era un fallo de verdad: una etiqueta de
    cierre de las plantillas de la pantalla (`</span>`) empieza por `<` y seguía con `/`, así que
    el quitador la tomaba por una expresión regular y **se comía el resto de la línea**, con la
    comilla de la plantilla incluida. A partir de ahí el fichero entero iba descolocado: los
    comentarios dejaban de reconocerse y su texto se revisaba como si fuera de pantalla. Se
    encontró al pasar la pantalla de inicio a React, que usa plantillas dentro de plantillas.
    Una expresión regular de verdad detrás de un `<` no aparece en este proyecto (y si algún día
    aparece, el `<` no es lo que la distingue: lo que la distingue es que después viene un patrón
    y otra barra, no una etiqueta).
    """
    if not ultimo:
        return True
    return ultimo in "(,=:[!&|?{};+-*%~^>"


def cadenas_de_js(texto: str) -> list[str]:
    """Saca los textos que un agricultor podría llegar a leer de un JavaScript.

    Deliberadamente se queda solo con las cadenas que PARECEN prosa: las que llevan
    un espacio o una tilde. Las claves internas ("cuedigital.interfaz",
    "aviso-pendientes") son identificadores sin espacios, no textos de pantalla, y
    revisarlas daría falsos avisos que acabarían haciendo ignorar este test.

    Lo que NO caza, y hay que saberlo: una etiqueta suelta de una sola palabra escrita
    a mano. Por eso los rótulos viven en `textos.py` y se sirven por `/api/interfaz`,
    que es donde el test sí los cubre todos.
    """
    resultados: list[str] = []

    # 1. Cadenas entrecomilladas. Se descartan los identificadores y los nombres de
    #    clase ("aviso aviso-error", "cuedigital.interfaz"): son palabras en
    #    minúscula, sin tildes y sin puntuación, no textos de pantalla.
    patron = re.compile(r"""(['"])([^'"\n]*)\1""")
    for coincidencia in patron.finditer(texto):
        cadena = coincidencia.group(2)
        if cadena.strip() and not re.fullmatch(r"[a-z0-9 .\-_:/]+", cadena):
            resultados.append(cadena)

    # 2. Plantillas de varias líneas. Se les quitan las expresiones ${...} y las
    #    etiquetas HTML: lo que queda es exactamente el texto que vería el agricultor.
    for plantilla in plantillas_de_javascript(texto):
        sin_etiquetas = re.sub(r"<[^>]*>", " ", plantilla)
        if re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3}", sin_etiquetas):
            resultados.append(sin_etiquetas)

    return resultados


def plantillas_de_javascript(texto: str) -> list[str]:
    """Saca el texto visible de las plantillas (`` `…` ``) de un JavaScript.

    Se quitan las expresiones `${…}`, que son código y no se ven en pantalla. Eso se hace con un
    recorrido propio y **no con una expresión regular**, y la razón es un fallo real: con
    `\\$\\{[^{}]*\\}` (que es lo que había antes) una expresión que lleva **llaves dentro** —como
    `${rellena(f("x"), { producto: y })}`— se cortaba a la mitad, y el resto del código
    (`});\n  } catch (error) {`) acababa dentro del texto que se revisa. El resultado era un aviso de
    jerga por un trozo de programa: un falso positivo, que es la clase de ruido que hace que un test
    se acabe ignorando.

    Ahora se cuentan las llaves y se saltan las cadenas de dentro de la expresión (comillas simples,
    dobles y plantillas anidadas), así que lo que sale es lo que de verdad se lee en la pantalla.
    """
    trozos: list[str] = []
    indice = 0
    largo = len(texto)
    while indice < largo:
        if texto[indice] != "`":
            indice += 1
            continue
        indice += 1
        llaves = 0
        visible: list[str] = []
        while indice < largo:
            caracter = texto[indice]
            if caracter == "\\":
                indice += 2
                continue
            if llaves == 0 and caracter == "`":
                break
            if llaves == 0 and caracter == "$" and indice + 1 < largo and texto[indice + 1] == "{":
                llaves = 1
                indice += 2
                continue
            if llaves > 0:
                if caracter in "\"'`":
                    # Dentro de la expresión hay una cadena (o una plantilla anidada): se salta
                    # entera, porque las llaves que lleve dentro no son de la expresión.
                    comilla = caracter
                    indice += 1
                    while indice < largo:
                        if texto[indice] == "\\":
                            indice += 2
                            continue
                        if texto[indice] == comilla:
                            indice += 1
                            break
                        indice += 1
                    continue
                if caracter == "{":
                    llaves += 1
                elif caracter == "}":
                    llaves -= 1
                indice += 1
                continue
            visible.append(caracter)
            indice += 1
        trozos.append("".join(visible))
        indice += 1
    return trozos


def texto_visible_de_html(texto: str) -> str:
    sin_comentarios = quita_comentarios_html(texto)
    sin_scripts = re.sub(r"<(script|style)\b.*?</\1>", " ", sin_comentarios, flags=re.DOTALL | re.I)
    return re.sub(r"<[^>]+>", " ", sin_scripts)


# --------------------------------------------------------------------------
# La interfaz se sirve
# --------------------------------------------------------------------------


class TestSeSirve:
    def test_los_ficheros_de_la_pantalla_existen(self):
        for nombre in FICHEROS_WEB:
            assert (WEB / nombre).is_file(), f"Falta web/{nombre}"

    @pytest.mark.parametrize("nombre", FICHEROS_WEB)
    def test_cada_fichero_se_sirve(self, cliente, nombre):
        respuesta = cliente.get(f"/{nombre}")
        assert respuesta.status_code == 200, f"/{nombre} no se sirve"
        assert len(respuesta.content) > 0

    def test_la_portada_sirve_la_pagina(self, cliente):
        respuesta = cliente.get("/")
        assert respuesta.status_code == 200
        assert "text/html" in respuesta.headers["content-type"]
        # La marca identifica la aplicación; «Mi cuaderno» sigue siendo un módulo.
        assert f'<title>{textos.MARCA["nombre"]}</title>' in respuesta.text
    def test_la_api_sigue_respondiendo_con_la_pantalla_montada(self, cliente):
        """El montaje de ficheros en "/" se come cualquier ruta registrada después.

        Este test existe porque ese fallo es silencioso: la ruta desaparece y nadie
        se entera hasta que un agricultor no puede entrar.
        """
        assert cliente.get("/health").status_code == 200
        assert cliente.get("/api").status_code == 200
        assert cliente.get("/api/ayuda").status_code == 200

    @pytest.mark.parametrize(
        "nombre,tipo_esperado",
        [
            ("app.js", "javascript"),
            ("nucleo.js", "javascript"),
            ("estilos.css", "text/css"),
            ("manifest.webmanifest", "manifest+json"),
            ("index.html", "text/html"),
        ],
    )
    def test_cada_fichero_se_sirve_con_su_tipo(self, cliente, nombre, tipo_esperado):
        """Un .js servido como text/plain hace que el navegador rechace el módulo.

        Pasa en Windows, donde los tipos MIME salen del registro del sistema. El
        fallo no da ningún mensaje útil: la pantalla se queda en blanco.
        """
        respuesta = cliente.get(f"/{nombre}")
        tipo = respuesta.headers["content-type"]
        assert tipo_esperado in tipo, f"/{nombre} se sirve como {tipo}"

    @pytest.mark.parametrize(
        "nombre",
        [
            # Los ficheros de React (los oficiales de `vendor` y los nuestros).
            "vendor/react.production.min.js",
            "vendor/react-dom.production.min.js",
            "vendor/htm.umd.js",
            "react/montar.js",
            "react/pantallas/inicio.js",
        ],
    )
    def test_los_ficheros_de_react_se_sirven(self, cliente, nombre):
        """Si el servidor no los sirve, la pantalla de inicio no se puede dibujar.

        No basta con que estén en el disco: tienen que salir por HTTP **y** como JavaScript. Un
        `.js` servido como `text/plain` lo rechaza el navegador, y el fallo no dice nada útil:
        la pantalla se queda en blanco. Se comprueba lo mismo que para `app.js`.
        """
        respuesta = cliente.get(f"/{nombre}")
        assert respuesta.status_code == 200, f"/{nombre} no se sirve"
        assert len(respuesta.content) > 0, f"/{nombre} se sirve vacío"
        tipo = respuesta.headers["content-type"]
        assert "javascript" in tipo, f"/{nombre} se sirve como {tipo}"


# --------------------------------------------------------------------------
# El vocabulario de la interfaz
# --------------------------------------------------------------------------


class TestVocabulario:
    def test_la_interfaz_trae_la_pantalla_de_inicio(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        inicio = datos["pantalla_inicio"]
        assert inicio["pregunta"]
        assert len(inicio["botones"]) == 6

    def test_estan_los_seis_botones_del_modo_sencillo(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        identificadores = [b["id"] for b in datos["pantalla_inicio"]["botones"]]
        assert identificadores == [
            "echar_producto",
            "abonar",
            "trabajo",
            "mi_cuaderno",
            "papel",
            "ayuda",
        ]

    def test_el_boton_de_echar_producto_es_el_mas_grande(self, cliente):
        """Es el 90 % de los usos: tiene que ser el que primero ve y el que más se toca."""
        datos = cliente.get("/api/interfaz").json()
        botones = datos["pantalla_inicio"]["botones"]
        grandes = [b["id"] for b in botones if b.get("principal")]
        assert grandes == ["echar_producto"]

    def test_cada_boton_lleva_icono_y_pista(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        for boton in datos["pantalla_inicio"]["botones"]:
            assert boton["icono"], f"{boton['id']} no tiene icono"
            assert boton["texto"]
            assert boton["pista"], f"{boton['id']} no tiene pista"

    def test_toda_palabra_de_boton_que_usa_la_interfaz_existe(self):
        """Cada `accion("...")` que usa `app.js` tiene que estar en `ACCIONES`.

        **Esto faltaba y ya había pasado factura.** `accion("guardar")` devuelve su propio nombre
        cuando la clave no está en la tabla, así que el botón de guardar de «guardar un papel» salía
        escrito «guardar», en minúscula y distinto de todos los demás, desde el primer día. Un texto
        que falta no revienta nada: se ve raro y nadie sabe por qué.
        """
        codigo = (WEB / "app.js").read_text(encoding="utf-8")
        usadas = set(re.findall(r'accion\("([a-z_]+)"\)', codigo))
        assert usadas, "no se ha encontrado ningún `accion(...)` en app.js"
        faltan = sorted(usadas - set(textos.ACCIONES))
        assert faltan == [], f"estas palabras de botón no están en `ACCIONES`: {faltan}"

    def test_la_interfaz_trae_todo_lo_que_necesita_para_funcionar(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        for clave in (
            "acciones",
            "aviso",
            "rotulos",
            "mensajes",
            "etiquetas",
            "justificaciones",
            "unidades",
            "trabajos",
            "provincias",
            "plazos_legales",
            "react",
        ):
            assert clave in datos, f"a la interfaz le falta {clave}"

    def test_las_etiquetas_llevan_su_explicacion(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        for clave, etiqueta in datos["etiquetas"].items():
            assert etiqueta.get("pregunta"), f"{clave} no tiene pregunta"
            assert etiqueta.get("pista"), f"{clave} no tiene pista"

    def test_los_rotulos_que_usa_la_pantalla_estan(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        for clave in (
            "unidad_hectareas",
            "unidad_kilos",
            "producto",
            "abono",
            "hectareas",
            "por_que",
            "recogido",
            "apuntes_de_producto",
        ):
            assert datos["rotulos"].get(clave), f"falta el rótulo {clave}"

    def test_los_avisos_que_usa_la_pantalla_estan(self, cliente):
        """La pantalla coge el texto de estado de `aviso` o de `mensajes`.

        Se comprueba que exista en alguno de los dos: lo que no puede pasar es que la
        interfaz pida un texto que no está y salga un hueco en blanco delante del
        agricultor.
        """
        datos = cliente.get("/api/interfaz").json()
        disponibles = {**datos["aviso"], **datos["mensajes"]}
        for clave in (
            "apuntado_ok",
            "pendientes",
            "sin_cobertura",
            "no_hay_parcelas",
            "no_hay_productos",
            "no_hay_abonos",
            "no_se_pudo",
            "confirmar_salida",
            "pie",
            "cargando",
        ):
            assert disponibles.get(clave), f"falta el aviso {clave}"

    def test_las_preguntas_del_asistente_estan_todas(self, cliente):
        """Las claves que pide `app.js`. Si falta una, la pregunta sale en blanco."""
        datos = cliente.get("/api/interfaz").json()
        necesarias = (
            "comun.parcela_id",
            "comun.fecha",
            "comun.superficie_ha",
            "tratamiento.superficie",
            "tratamiento.justificacion",
            "tratamiento.producto_id",
            "tratamiento.dosis",
            "tratamiento.quien_maquina",
            "tratamiento.observaciones",
            "tratamiento.resumen",
            "tratamiento.aplicador_id",
            "tratamiento.equipo_id",
            "fertilizacion.fertilizante_id",
            "fertilizacion.kg_ha_producto",
            "fertilizacion.resumen",
            "labor.que_has_hecho",
            "labor.detalles",
        )
        for clave in necesarias:
            assert datos["etiquetas"].get(clave), f"falta la etiqueta {clave}"


class TestPantallasDeAlta:
    """Las pantallas que hacen que la aplicación se pueda usar de verdad.

    Antes de tenerlas, al agricultor nuevo se le decía "añade tu primera parcela" y no
    había ninguna forma de hacerlo: se quedaba mirando una pantalla que le pedía algo
    imposible. Estos tests comprueban que el vocabulario de esas pantallas se sirve y
    que a la interfaz no le falta nada para pintarlas.
    """

    def test_se_sirven_las_pantallas_de_alta(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        assert datos["maestros"]["titulo"]
        assert datos["maestros"]["intro"]
        assert datos["dictado"]["titulo"]

    def test_estan_las_cinco_secciones_con_su_boton_de_anadir(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        for tipo in ("parcela", "producto", "abono", "aplicador", "equipo"):
            for prefijo in ("seccion", "pista", "sin", "anadir"):
                assert datos["maestros"].get(f"{prefijo}_{tipo}"), (
                    f"falta maestros.{prefijo}_{tipo}"
                )

    def test_esta_el_aviso_que_desbloquea_al_agricultor_nuevo(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        assert datos["maestros"]["antes_de_empezar"]
        assert datos["maestros"]["falta_parcela"]
        assert datos["maestros"]["anadir_primera_parcela"]

    def test_cada_tipo_dice_donde_se_usa(self, cliente):
        """Cuando alguien da de alta una máquina tiene que saber para qué sirve."""
        datos = cliente.get("/api/interfaz").json()
        for tipo in ("parcela", "producto", "abono", "aplicador", "equipo"):
            assert datos["maestros"].get(f"{tipo}_se_usa"), f"falta maestros.{tipo}_se_usa"

    def test_las_preguntas_de_los_campos_estan_todas(self, cliente):
        """Las claves que pide `app.js` en las pantallas de alta."""
        datos = cliente.get("/api/interfaz").json()
        necesarias = (
            "parcela.alias",
            "parcela.superficie_ha",
            "parcela.sistema",
            "parcela.ref_sigpac",
            "parcela.municipio",
            "parcela.masa_agua_cerca",
            "parcela.captacion_consumo_humano",
            "parcela.zona_vulnerable_nitratos",
            "producto.nombre_comercial",
            "producto.numero_registro",
            "producto.dosis_maxima",
            "producto.unidad_dosis",
            "producto.plazo_seguridad_dias",
            "producto.lote",
            "producto.fecha_caducidad",
            "abono.nombre",
            "abono.riqueza_n",
            "abono.riqueza_p",
            "abono.riqueza_k",
            "abono.tipo",
            "aplicador.nombre",
            "aplicador.es_empresa",
            "aplicador.numero_carne",
            "aplicador.fecha_caducidad_carne",
            "equipo.nombre",
            "equipo.fecha_proxima_iteaf",
        )
        for clave in necesarias:
            etiqueta = datos["etiquetas"].get(clave)
            assert etiqueta, f"falta la etiqueta {clave}"
            assert etiqueta.get("pregunta"), f"{clave} no tiene pregunta"

    def test_los_sistemas_y_los_abonos_vienen_con_su_nombre(self, cliente):
        """La interfaz no traduce valores: se los dan traducidos."""
        datos = cliente.get("/api/interfaz").json()
        sistemas = {item["valor"]: item["texto"] for item in datos["sistemas"]}
        # **Tres, y la tercera es «no lo sé»** (A10, 05/10/2026). Antes eran dos —secano y regadío— y
        # el que no elegía nada se guardaba como secano, así que el programa declaraba de secano una
        # tierra de regadío y el cuaderno de la Junta escribía una «S». El sistema decide contra qué
        # columna del anexo III de la Orden MAV/398/2022 se compara el abonado: se ofrece la tercera
        # respuesta y el agricultor decide. El texto lo pone el servidor (`textos.ACCIONES`), que es
        # lo que esta prueba comprueba: la interfaz no traduce nada por su cuenta.
        assert sistemas == {"secano": "Secano", "regadio": "Regadío", "nulo": "No lo sé"}
        tipos = {item["valor"]: item["texto"] for item in datos["tipos_abono"]}
        assert "mineral" in tipos and tipos["mineral"]

    def test_las_unidades_de_dosis_estan(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        assert "L/ha" in datos["unidades_dosis"]
        assert "kg/ha" in datos["unidades_dosis"]

    def test_el_dictado_trae_su_texto_y_su_alternativa_sin_voz(self, cliente):
        """Donde no haya reconocimiento de voz, tiene que poder escribirse."""
        datos = cliente.get("/api/interfaz").json()
        for clave in (
            "titulo",
            "intro",
            "boton",
            "escribe",
            "ejemplo",
            "entender",
            "no_se_puede",
            "no_he_oido",
        ):
            assert datos["dictado"].get(clave), f"falta dictado.{clave}"

    def test_la_tarjeta_de_revision_tiene_sus_botones(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        assert datos["dictado"]["apuntarlo"]
        assert datos["dictado"]["corregir"]
        assert datos["maestros"]["sin_sitio_titulo"]


class TestCertificadoEnLaInterfaz:
    def test_la_interfaz_trae_los_textos_del_certificado(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        for clave in ("boton", "pista", "no_configurado", "no_dado_de_alta", "sin_nif"):
            assert datos["certificado"].get(clave), f"falta certificado.{clave}"

    def test_sin_configurar_el_estado_lo_dice(self, cliente, monkeypatch):
        """La pantalla necesita saberlo para no enseñar un botón que lleva a un error."""
        monkeypatch.delenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", raising=False)
        datos = cliente.get("/api/cuenta/certificado/estado").json()
        assert datos["configurado"] is False
        assert datos["si_no_se_puede"]


# --------------------------------------------------------------------------
# La jerga, también en la interfaz
# --------------------------------------------------------------------------


class TestSinJergaEnLaInterfaz:
    def test_lo_que_sirve_la_api_no_lleva_jerga(self, cliente):
        """El agricultor no puede leer jerga en lo que se le enseña.

        **Y esta prueba miraba también los códigos, hasta el 05/10/2026.** Recorría todas las cadenas
        de la respuesta, incluido el `valor` de un catálogo (`{"valor": "fitosanitario", "texto":
        "Producto para las plagas y las hierbas"}`), y ahí se puso roja al integrar las cuentas del
        T13: la palabra «fitosanitario» está prohibida en pantalla y es, a la vez, **el código con el
        que se guarda esa categoría en la base de datos**.

        Lo que decide es una regla que el proyecto ya tenía escrita en `contactos.py` («aquí la clave
        sí lo dice, porque **la clave no la lee nadie**»): **un catálogo trae su código y su texto, y
        el agricultor solo lee el texto**. Así que se salta el `valor` **solo cuando el diccionario es
        un catálogo** (tiene `valor` y también `texto` o `etiqueta`), y se sigue revisando todo lo
        demás: los textos, las listas, los mensajes y cualquier cadena suelta.

        Y no se pierde vigilancia: que esos códigos sean los que el servidor conoce lo comprueban las
        pruebas de cada catálogo (`test_gastos.py`, `test_t14_maquinaria.py`), y el valor sigue
        entrando en el recorrido.
        """
        datos = cliente.get("/api/interfaz").json()
        problemas: dict[str, list[str]] = {}

        def es_un_catalogo(valor: dict) -> bool:
            return "valor" in valor and ("texto" in valor or "etiqueta" in valor)

        def revisar(valor, camino):
            if isinstance(valor, str):
                encontradas = textos.palabras_prohibidas_encontradas(valor)
                if encontradas:
                    problemas[f"{camino}: {valor[:60]}"] = encontradas
            elif isinstance(valor, dict):
                for clave, contenido in valor.items():
                    # El código de un catálogo no lo lee nadie: ver el porqué en el docstring.
                    if clave == "valor" and es_un_catalogo(valor):
                        continue
                    revisar(contenido, f"{camino}.{clave}")
            elif isinstance(valor, list):
                for indice, contenido in enumerate(valor):
                    revisar(contenido, f"{camino}[{indice}]")

        revisar(datos, "interfaz")
        assert not problemas, f"La interfaz sirve textos con jerga: {problemas}"

    def test_el_guardian_de_la_jerga_sigue_mordiendo(self):
        """Y el guardián de arriba no se ha quedado tonto al saltarse los códigos.

        Se le da lo mismo que revisa él, con jerga en el sitio que **sí** se lee (el `texto` de un
        catálogo) y con jerga en el sitio que **no** (el `valor`), y tiene que quejarse **de una sola
        cosa**: de la primera.
        """
        revisados: dict[str, list[str]] = {}

        def revisar(valor, camino):
            if isinstance(valor, str):
                encontradas = textos.palabras_prohibidas_encontradas(valor)
                if encontradas:
                    revisados[camino] = encontradas
            elif isinstance(valor, dict):
                es_catalogo = "valor" in valor and ("texto" in valor or "etiqueta" in valor)
                for clave, contenido in valor.items():
                    if clave == "valor" and es_catalogo:
                        continue
                    revisar(contenido, f"{camino}.{clave}")
            elif isinstance(valor, list):
                for indice, contenido in enumerate(valor):
                    revisar(contenido, f"{camino}[{indice}]")

        revisar(
            {
                "catalogo_bueno": {"valor": "fitosanitario", "texto": "Producto para las plagas"},
                "catalogo_malo": {"valor": "otro", "texto": "Un producto fitosanitario"},
            },
            "interfaz",
        )
        assert "interfaz.catalogo_bueno.valor" not in revisados, (
            "el código de un catálogo no lo lee nadie: no puede hacer saltar el guardián"
        )
        assert "interfaz.catalogo_malo.texto" in revisados, (
            "y el texto sí se lee: si lleva jerga, el guardián tiene que cazarlo"
        )

    def test_el_html_no_lleva_jerga_en_lo_que_se_ve(self):
        visible = texto_visible_de_html((WEB / "index.html").read_text(encoding="utf-8"))
        encontradas = textos.palabras_prohibidas_encontradas(visible)
        assert not encontradas, f"index.html muestra jerga: {encontradas}"

    @pytest.mark.parametrize(
        "nombre",
        [
            "app.js",
            "nucleo.js",
            # Las pantallas que ya están en React también son interfaz, y también pueden
            # escribir un texto para el agricultor por error: entran aquí por el mismo motivo.
            "react/montar.js",
            "react/pantallas/inicio.js",
        ],
    )
    def test_el_javascript_no_lleva_jerga_en_sus_textos(self, nombre):
        """Caza cualquier rótulo escrito a mano en la interfaz.

        Es el test que impide que alguien escriba un texto para el agricultor
        directamente en el JavaScript, saltándose el fichero de textos y, con él,
        la garantía de que no hay jerga.
        """
        codigo = quita_comentarios_js((WEB / nombre).read_text(encoding="utf-8"))
        problemas: list[str] = []
        for cadena in cadenas_de_js(codigo):
            encontradas = textos.palabras_prohibidas_encontradas(cadena)
            if encontradas:
                problemas.append(f"{cadena[:70]} -> {encontradas}")
        assert not problemas, f"{nombre} escribe textos con jerga: {problemas}"


class TestElBuscadorDeTextosDeLaPantalla:
    """El que saca de `app.js` lo que ve el agricultor, que es lo que revisa el test de jerga.

    Se prueba aquí porque es un test **que se apoya en otro**, y cuando el de dentro se equivoca el
    de fuera deja de avisar (o avisa de cosas que no son). Las dos cosas pasaron de verdad: con la
    versión anterior, una expresión con llaves dentro se cortaba a la mitad y el código de al lado
    salía como si fuera un texto de pantalla.
    """

    def test_una_expresion_con_llaves_dentro_no_deja_ver_codigo(self):
        plantillas = plantillas_de_javascript(
            "pintar(`<p>Hola ${rellena(f(\"x\"), { producto: y })}</p>`);\n  } catch (error) {"
        )
        assert "<p>Hola" in plantillas[0]
        # Lo que importa: el código de después de la expresión **no** se cuela como texto.
        assert "error" not in plantillas[0]
        assert "catch" not in plantillas[0]

    def test_una_plantilla_dentro_de_otra(self):
        plantillas = plantillas_de_javascript(
            "`<ul>${lista.map((x) => `<li>${x}</li>`).join(\"\")}</ul>`"
        )
        assert plantillas[0] == "<ul></ul>"

    def test_las_cadenas_de_dentro_se_saltan(self):
        # La comilla con una llave dentro no puede descontar una llave de la expresión.
        plantillas = plantillas_de_javascript("`<p>${f(\"}\")}</p> te`")
        assert "te" in plantillas[0]

    def test_una_plantilla_sin_expresiones_se_devuelve_entera(self):
        assert plantillas_de_javascript("`<p>Sin nada</p>`") == ["<p>Sin nada</p>"]

    def test_una_etiqueta_de_cierre_no_se_toma_por_una_expresion_regular(self):
        """`</span>` no abre una expresión regular.

        **Este fallo se encontró de verdad**, al pasar la pantalla de inicio a React. Aquella
        pantalla usa plantillas dentro de plantillas (una etiqueta de htm dentro de otra), y el
        quitador tomaba el `/` de `</span>` por el principio de una expresión regular: se comía el
        resto de la línea, comilla de la plantilla incluida, y a partir de ahí el fichero entero
        iba descolocado. El resultado no era un aviso falso cualquiera: era que **los comentarios
        dejaban de revisarse como comentarios** y su texto salía como si fuera de pantalla.
        """
        codigo = (
            "const a = html`\n"
            "  <p>${c ? html`<span>${d}</span>` : null}</p>\n"
            "`;\n"
            "/*\n"
            " * Un comentario que no se debe revisar.\n"
            " */\n"
        )
        limpio = quita_comentarios_js(codigo)
        assert "Un comentario que no se debe revisar" not in limpio, (
            "el comentario ha sobrevivido: el quitador se ha descolocado con la etiqueta de cierre"
        )
        # Y lo que sí es código sigue entero.
        assert "<span>" in limpio

    def test_el_texto_de_verdad_se_sigue_viendo(self):
        """El buscador no puede quedarse tan fino que ya no vea el texto que revisa."""
        plantillas = plantillas_de_javascript("pintar(`<h1>${titulo}</h1><p>La validación falló</p>`)")
        assert any("validación" in plantilla for plantilla in plantillas)


class TestLaPantallaDeInicioEnReact:
    """La pantalla de inicio se pinta con React, sin compilar.

    Es el paso piloto de la migración (la guía está en `docs/REACT.md`). Aquí se comprueban
    las tres cosas que, si se hicieran mal, dejarían al agricultor **sin pantalla**, que es el
    único fallo que este proyecto no se puede permitir:

    1. `index.html` tiene que cargar los ficheros de React **antes** que `app.js`: el módulo
       los necesita nada más cargarse.
    2. El servicio que guarda la aplicación en el móvil tiene que guardarlos también, o en el
       campo no habría con qué dibujar la primera pantalla (eso se comprueba en
       `TestSinCobertura`, con la lista de ficheros).
    3. El aviso que se enseña cuando React no ha llegado tiene que estar en `textos.py` como
       todos los demás textos, y sin jerga.
    """

    def test_la_pagina_carga_react_antes_que_la_aplicacion(self):
        pagina = (WEB / "index.html").read_text(encoding="utf-8")
        posiciones = []
        for fichero in (
            "/vendor/react.production.min.js",
            "/vendor/react-dom.production.min.js",
            "/vendor/htm.umd.js",
        ):
            posicion = pagina.find(fichero)
            assert posicion >= 0, f"index.html no carga {fichero}"
            posiciones.append(posicion)
        aplicacion = pagina.find("/app.js")
        assert aplicacion >= 0, "index.html no carga la aplicación"
        assert max(posiciones) < aplicacion, (
            "los ficheros de React tienen que ir ANTES de app.js: si no, el módulo no "
            "encuentra React ni htm cuando el navegador lo carga y la pantalla se queda en blanco"
        )
        assert posiciones == sorted(posiciones), (
            "los tres ficheros de React no se cargan en el orden de la carpeta: primero React, "
            "después ReactDOM y por último htm, que es el que los necesita a los dos"
        )

    def test_el_aviso_de_emergencia_viene_del_servidor(self, cliente):
        """Si React no llega, el agricultor tiene que leer algo, no encontrarse un hueco."""
        datos = cliente.get("/api/interfaz").json()
        assert datos["react"] == textos.REACT
        assert datos["react"]["sin_react"].strip()
        assert datos["react"]["recargar"].strip()

    def test_ese_aviso_no_lleva_jerga(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        for clave, texto in datos["react"].items():
            encontradas = textos.palabras_prohibidas_encontradas(texto)
            assert not encontradas, f"react.{clave} lleva jerga: {encontradas}"

    def test_los_textos_de_react_los_revisa_el_test_de_jerga(self):
        """Si no entran en `textos_visibles()`, el test general deja de verlos."""
        visibles = textos.textos_visibles()
        for clave, texto in textos.REACT.items():
            assert texto in visibles, f"react.{clave} se queda fuera del test de jerga"

    def test_las_copias_de_los_tests_traen_el_aviso_de_emergencia(self):
        """Sin el texto en la copia, el test vería el aviso en blanco y lo daría por bueno."""
        for fichero in ("interfaz.test.js", "react.test.js"):
            copia = (TESTS_JS / fichero).read_text(encoding="utf-8")
            for clave, texto in textos.REACT.items():
                assert f'"{texto}"' in copia, f"react.{clave} no está en {fichero}"

    def test_la_copia_nueva_lleva_los_textos_de_la_pantalla_de_inicio(self):
        """La copia de `react.test.js` dice lo mismo que sirve el servidor.

        Es el mismo agujero que se cerró con las preguntas del asistente (ver
        `TestLasPreguntasDelAsistenteEstanYSeComprueban`): si la copia se queda atrás, el test
        que mira la pantalla comprueba una pantalla que el agricultor no tiene, y **pasa**.

        Esta copia lleva los textos **enteros**, no recortados como los de `interfaz.test.js`
        (que acorta algunos para no hacer líneas larguísimas). Por eso aquí se puede comparar
        letra a letra; las pistas de los botones se comparan por su principio, para que valga
        también si algún día se recortan.
        """
        copia = (TESTS_JS / "react.test.js").read_text(encoding="utf-8")
        inicio = textos.PANTALLA_INICIO
        usados = [
            inicio["saludo"],
            inicio["pregunta"],
            inicio["repetir"]["texto"],
            inicio["repetir"]["vacio"],
            # La frase que se dice cuando hay apuntes pero ninguno se puede repetir. Estaba de más
            # la otra («todavía no has apuntado nada») en ese caso, y encima se elegía mirando solo
            # lo que recordaba el móvil: la copia tiene que llevar las dos.
            inicio["repetir"]["sin_poder_repetir"],
            textos.MAESTROS["antes_de_empezar"],
            textos.MAESTROS["falta_parcela"],
            textos.MAESTROS["anadir_primera_parcela"],
            textos.MAESTROS["mis_cosas"],
            textos.DICTADO["titulo"],
            textos.DICTADO["pista_boton"],
        ]
        faltan = [texto for texto in usados if f'"{texto}"' not in copia]
        assert faltan == [], f"la copia de react.test.js no lleva estos textos: {faltan}"

        for boton in inicio["botones"]:
            for clave in ("id", "texto", "icono"):
                assert f'"{boton[clave]}"' in copia, (
                    f"el botón {boton['id']} no lleva su {clave} en la copia"
                )
            pista = re.search(
                r'id: "' + re.escape(boton["id"]) + r'".*?pista: "([^"]*)"', copia, re.S
            )
            assert pista, f"el botón {boton['id']} no lleva pista en la copia"
            assert pista.group(1).strip(), f"el botón {boton['id']} tiene la pista en blanco"
            assert boton["pista"].startswith(pista.group(1)), (
                f"la copia dice otra pista para {boton['id']}: "
                f"{pista.group(1)!r} en vez de {boton['pista']!r}"
            )

    def test_la_copia_lleva_los_textos_de_los_grupos(self):
        """Lo mismo para los grupos de parcelas (ronda 44)."""
        copia = (TESTS_JS / "react.test.js").read_text(encoding="utf-8")
        usados = [
            textos.GRUPOS["titulo"],
            textos.GRUPOS["explica"],
            textos.GRUPOS["faltan_cultivos"],
            textos.GRUPOS["sin_grupos"],
            textos.GRUPOS["para_que"],
            textos.GRUPOS["calcular"],
            textos.GRUPOS["automatico"],
            textos.CULTIVOS["titulo"],
            textos.MAESTROS["titulo"],
            textos.ACCIONES["volver"],
        ]
        faltan = [texto for texto in usados if f'"{texto}"' not in copia]
        assert faltan == [], f"la copia de react.test.js no lleva estos textos: {faltan}"

    def test_la_copia_lleva_los_textos_de_las_ventas(self):
        """Lo mismo para «lo que he vendido» (ronda 43)."""
        copia = (TESTS_JS / "react.test.js").read_text(encoding="utf-8")
        usados = [
            textos.VENTA["titulo"],
            textos.VENTA["explica"],
            textos.VENTA["sin_nada"],
            textos.VENTA["dinero_fuera"],
            textos.VENTA["anadir"],
            textos.VENTA["sin_comprador"],
            textos.VENTA["tabla_lote"],
            textos.VENTA["tabla_albaran"],
            textos.ACCIONES["volver"],
        ]
        faltan = [texto for texto in usados if f'"{texto}"' not in copia]
        assert faltan == [], f"la copia de react.test.js no lleva estos textos: {faltan}"

    def test_la_copia_lleva_los_textos_de_las_medidas(self):
        """Lo mismo para las medidas preventivas (ronda 41): las preguntas y las palabras de la nota."""
        copia = (TESTS_JS / "react.test.js").read_text(encoding="utf-8")
        usados = [
            textos.MEDIDAS["titulo"],
            textos.MEDIDAS["explica"],
            textos.MEDIDAS["marcar_titulo"],
            textos.MEDIDAS["marcar_pista"],
            textos.MEDIDAS["catalogo_aviso"],
            textos.MEDIDAS["guardar"],
            textos.MEDIDAS["no_hago_ninguna"],
            textos.MEDIDAS["observaciones"],
            textos.MEDIDAS["tus_palabras"],
            textos.ACCIONES["volver"],
        ]
        faltan = [texto for texto in usados if f'"{texto}"' not in copia]
        assert faltan == [], f"la copia de react.test.js no lleva estos textos: {faltan}"

    def test_la_copia_lleva_los_textos_de_mis_datos(self):
        """Lo mismo para «mis datos» (ronda 40): los once campos, con su nombre y su pista.

        Es la primera pantalla con campos que se rellenan, así que su copia es además el modelo de
        las que vengan: si un nombre de campo se queda atrás, el agricultor vería un campo sin
        rótulo.
        """
        copia = (TESTS_JS / "react.test.js").read_text(encoding="utf-8")
        usados = [textos.MIS_DATOS["titulo"], textos.MIS_DATOS["explica"],
                  textos.MIS_DATOS["guardado"], textos.MIS_DATOS["guardar"]]
        for campo, _tipo in (
            ("nombre", "texto"), ("nif", "texto"), ("registro_autonomico", "texto"),
            ("registro_nacional", "texto"), ("direccion", "texto"), ("localidad", "texto"),
            ("codigo_postal", "texto"), ("provincia", "texto"), ("municipio", "texto"),
            ("telefono", "texto"), ("correo", "texto"),
        ):
            usados.append(textos.MIS_DATOS[campo])
            if textos.MIS_DATOS.get(f"{campo}_pista"):
                usados.append(textos.MIS_DATOS[f"{campo}_pista"])
        usados.append(textos.ACCIONES["volver"])
        faltan = [texto for texto in usados if f'"{texto}"' not in copia]
        assert faltan == [], f"la copia de react.test.js no lleva estos textos: {faltan}"

    def test_la_copia_lleva_los_textos_de_las_fincas(self):
        """Lo mismo para «quién entra en mi finca» (ronda 89): las palabras de la pantalla y las de los
        cuatro papeles.

        Los cuatro papeles («Tú (titular)», «El titular de la finca», «Tu cuenta» y «Ayuda en la finca»)
        se copian porque son los que se leen **al lado de cada nombre**, y el que cambia según quién mire
        es justo el que se puede quedar mal: si la copia llevara solo dos, la prueba no vería la
        diferencia entre el titular y el ayudante.
        """
        copia = (TESTS_JS / "react.test.js").read_text(encoding="utf-8")
        usados = [
            textos.FINCAS["titulo"],
            textos.FINCAS["explica"],
            textos.FINCAS["estas_en"],
            textos.FINCAS["la_tuya"],
            textos.FINCAS["papel_ayudante"],
            textos.FINCAS["entrar_en"],
            textos.FINCAS["anadir"],
            textos.FINCAS["que_correo"],
            textos.FINCAS["que_correo_pista"],
            textos.FINCAS["anadir_pista"],
            textos.FINCAS["quitar"],
            textos.FINCAS["titular"],
            textos.FINCAS["papel_titular"],
            textos.FINCAS["ayudante"],
            textos.FINCAS["tu_cuenta"],
            textos.FINCAS["eres_el_titular"],
            textos.FINCAS["no_eres_el_titular"],
            textos.FINCAS["solo_una"],
            textos.FINCAS["anadida"],
            textos.FINCAS["quitada"],
            # Y uno de los avisos del servidor: son los que se leen tal cual cuando algo no se puede
            # hacer (el correo no es de ninguna cuenta, ya estaba, es el tuyo…).
            textos.FINCAS["cuenta_que_no_existe"],
            textos.ACCIONES["volver"],
        ]
        faltan = [texto for texto in usados if f'"{texto}"' not in copia]
        assert faltan == [], f"la copia de react.test.js no lleva estos textos: {faltan}"

    def test_la_interfaz_sirve_las_palabras_de_las_fincas(self, cliente):
        """Y que salgan por `/api/interfaz`, que es de donde las pide la aplicación.

        Sin esto, el servidor tendría los textos y la pantalla saldría con los botones en blanco: es el
        fallo que ya pasó con otros bloques (los textos existían y nadie los servía).
        """
        datos = cliente.get("/api/interfaz").json()
        fincas = datos["fincas"]
        for clave in ("titulo", "explica", "anadir", "quitar", "entrar_en", "papel_titular"):
            assert fincas.get(clave), f"falta el texto «{clave}» de las fincas"

    def test_la_copia_lleva_los_textos_de_lo_que_hay_sembrado(self):
        """Lo mismo para «qué hay sembrado» (ronda 38): la copia, palabra por palabra."""
        copia = (TESTS_JS / "react.test.js").read_text(encoding="utf-8")
        usados = [
            textos.CULTIVOS["titulo"],
            textos.CULTIVOS["explica"],
            textos.CULTIVOS["sin_parcelas"],
            textos.CULTIVOS["para_que"],
            textos.CULTIVOS["falta_decirlo"],
            textos.CULTIVOS["otros_anos"],
            textos.CULTIVOS["repite"],
            textos.CULTIVOS["decir"],
            textos.CULTIVOS["cambiar"],
            textos.CULTIVOS["tiene"],
            textos.CULTIVOS["cuando"],
            textos.CULTIVOS["hasta"],
            textos.MAESTROS["titulo"],
            textos.ACCIONES["volver"],
        ]
        faltan = [texto for texto in usados if f'"{texto}"' not in copia]
        assert faltan == [], f"la copia de react.test.js no lleva estos textos: {faltan}"

    def test_la_copia_lleva_los_textos_del_almacen(self):
        """Lo mismo para el almacén (ronda 34): las cuentas y sus etiquetas, tal y como se sirven.

        Estas etiquetas son las que el agricultor lee al lado de cada número —«Compraste», «Llevas
        echado», «Te queda»—, así que una copia que se quede atrás hace que el test compruebe una
        pantalla que él no tiene.
        """
        copia = (TESTS_JS / "react.test.js").read_text(encoding="utf-8")
        usados = [
            textos.CESTA["titulo"],
            textos.CESTA["explica"],
            textos.CESTA["vacia"],
            textos.CESTA["comprado"],
            textos.CESTA["gastado"],
            textos.CESTA["queda"],
            textos.CESTA["apuntes"],
            textos.CESTA["cuando"],
            textos.CESTA["donde_lo_compraste"],
            textos.CESTA["para_que_sirve"],
            textos.CESTA["como_apuntarlo"],
            textos.CESTA["ir_a_productos"],
            textos.FACTURAS["titulo"],
            textos.ACCIONES["volver"],
        ]
        faltan = [texto for texto in usados if f'"{texto}"' not in copia]
        assert faltan == [], f"la copia de react.test.js no lleva estos textos: {faltan}"

    def test_la_copia_lleva_los_textos_de_los_papeles(self):
        """Lo mismo para «los papeles» (ronda 33): la copia tiene que decir lo que sirve el servidor.

        Se comprueban las frases que deciden lo que ve el agricultor —el aviso de que un papel está
        apuntado sin fichero, la palabra de los dos botones y el aviso de que no hay ninguno—, que son
        las que se copiaron a mano en `react.test.js`.
        """
        copia = (TESTS_JS / "react.test.js").read_text(encoding="utf-8")
        usados = [
            textos.DOCUMENTOS["titulo"],
            textos.DOCUMENTOS["explica"],
            textos.DOCUMENTOS["sin_papeles"],
            textos.DOCUMENTOS["sin_carpeta"],
            textos.DOCUMENTOS["para_que"],
            textos.DOCUMENTOS["tiene_fichero"],
            textos.DOCUMENTOS["no_tiene_fichero"],
            textos.DOCUMENTOS["descargar"],
            textos.DOCUMENTOS["subir_fichero"],
            textos.DOCUMENTOS["sin_fichero"],
            textos.DOCUMENTOS["nuevo"],
            textos.DOCUMENTOS["listado"],
            textos.MAESTROS["titulo"],
            textos.ACCIONES["volver"],
        ]
        faltan = [texto for texto in usados if f'"{texto}"' not in copia]
        assert faltan == [], f"la copia de react.test.js no lleva estos textos: {faltan}"

    def test_la_copia_lleva_los_textos_de_la_pantalla_de_confirmacion(self):
        """Lo mismo para la segunda pantalla migrada, la de «Apuntado…» (ronda 31).

        Sin esto, la copia de `react.test.js` podría quedarse con una frase vieja y el test de la
        pantalla comprobaría una pantalla que el agricultor no tiene —y pasaría—, que es el agujero
        que ya se cerró dos veces en este proyecto.
        """
        copia = (TESTS_JS / "react.test.js").read_text(encoding="utf-8")
        usados = [
            textos.INTERFAZ["apuntado_ok"],
            textos.MENSAJES["sin_cobertura"],
            textos.MENSAJES["V8_dias_de_espera"],
            textos.ACCIONES["deshacer"],
            textos.ACCIONES["volver"],
        ]
        faltan = [texto for texto in usados if f'"{texto}"' not in copia]
        assert faltan == [], f"la copia de react.test.js no lleva estos textos: {faltan}"


class TestElQuitadorDeComentarios:
    """El que limpia los comentarios antes de buscar jerga. También se prueba.

    Y no por gusto: la versión anterior borraba medio fichero cuando encontraba un `/*` dentro de
    unas comillas, y lo que se borraba **no se revisaba**. Esto lo encontró el atributo
    `accept=".pdf,image/*"` de la pantalla de las facturas.
    """

    def test_un_comentario_de_bloque_se_quita(self):
        assert "no se ve" not in quita_comentarios_js("/* no se ve */ const x = 1;")

    def test_un_comentario_de_linea_se_quita(self):
        assert "no se ve" not in quita_comentarios_js("// no se ve\nconst x = 1;")

    def test_una_barra_dentro_de_comillas_no_se_come_el_fichero(self):
        """`accept=".pdf,image/*"` es el caso real que rompió esto."""
        codigo = 'const a = `accept=".pdf,image/*"`;\nconst b = "esto se tiene que seguir viendo";'
        limpio = quita_comentarios_js(codigo)
        assert "esto se tiene que seguir viendo" in limpio
        assert 'accept=".pdf,image/*"' in limpio

    def test_los_comentarios_de_verdad_siguen_quitandose(self):
        codigo = 'const a = "texto";\n/* un comentario con la palabra validación */\nconst b = 2;'
        assert "validación" not in quita_comentarios_js(codigo)
        assert "texto" in quita_comentarios_js(codigo)

    def test_una_expresion_regular_con_comilla_dentro(self):
        """`.replace(/"/g, "&quot;")` es una comilla que no abre ninguna cadena.

        Es el segundo fallo real de este recorrido: sin entender esa barra, la comilla de `/"/g` se
        comía el fichero hasta la siguiente comilla, comentarios incluidos.
        """
        codigo = (
            'const limpio = String(x).replace(/"/g, "&quot;");\n'
            "/* un comentario con la palabra validación */\n"
            "const b = 2;"
        )
        limpio = quita_comentarios_js(codigo)
        assert "validación" not in limpio
        assert "&quot;" in limpio

    def test_una_division_no_se_toma_por_una_expresion_regular(self):
        codigo = 'const mitad = total / 2;\nconst otro = "sigue aquí";'
        assert "sigue aquí" in quita_comentarios_js(codigo)

    def test_una_plantilla_dentro_de_otra_no_se_come_el_fichero(self):
        """El tercer fallo real, y el más callado de los tres.

        La pantalla del almacén trajo un comentario que decía «tal y como los sirve
        `/api/interfaz`», y el test de jerga se quejó de la palabra «interfaz» en un comentario
        que el agricultor no ve. Lo que estaba roto no era el comentario: era esto. El `/>` de un
        `<b … />` dentro de un `${…}` va detrás de una llave, y la heurística de la barra se lo
        comía junto con la comilla que cerraba la plantilla de dentro. A partir de ahí el fichero
        iba descolocado y **los comentarios dejaban de quitarse**.
        """
        codigo = (
            "const x = html`\n"
            "  ${a ? html`<b c=${d} />` : null}\n"
            "`;\n"
            "/* un comentario con la palabra validación */\n"
            "const y = 1;\n"
        )
        limpio = quita_comentarios_js(codigo)
        assert "validación" not in limpio, "el comentario de después de la plantilla no se quita"
        assert "<b c=${d} />" in limpio, "el trozo de plantilla de dentro se ha perdido"

    def test_lo_que_hay_dentro_de_un_dolar_llaves_tambien_se_limpia(self):
        """Un comentario dentro de `${…}` tampoco se ve en pantalla."""
        codigo = "const x = html`${a /* validación */ + b}`;"
        limpio = quita_comentarios_js(codigo)
        assert "validación" not in limpio
        assert "${a  + b}" in limpio, f"se ha roto la expresión: {limpio}"

    def test_las_llaves_de_dentro_del_dolar_llaves_no_cierran_la_expresion(self):
        """`${f(x, { a: 1 })}` lleva llaves dentro: sin contarlas, la expresión se cerraría antes."""
        codigo = "const x = html`${f(y, { a: 1 })}`;\n/* un comentario con la palabra validación */"
        limpio = quita_comentarios_js(codigo)
        assert "validación" not in limpio
        assert "{ a: 1 }" in limpio


# --------------------------------------------------------------------------
# Lo que tiene que cumplir para un agricultor que no sabe de informática
# --------------------------------------------------------------------------


class TestModoSencillo:
    def test_la_letra_base_no_baja_de_18_pixeles(self):
        css = (WEB / "estilos.css").read_text(encoding="utf-8")
        assert "--letra: 18px" in css
        assert "font-size: var(--letra)" in css

    def test_los_botones_no_bajan_de_64_pixeles_de_alto(self):
        css = (WEB / "estilos.css").read_text(encoding="utf-8")
        assert "--toque: 64px" in css
        assert "min-height: var(--toque)" in css

    def test_se_puede_agrandar_la_letra(self):
        css = (WEB / "estilos.css").read_text(encoding="utf-8")
        assert "letra-grande" in css
        codigo = (WEB / "app.js").read_text(encoding="utf-8")
        assert "letra-grande" in codigo

    def test_el_html_se_puede_ampliar_con_los_dedos(self):
        """Sin esto, quien ve poco no puede hacer zoom y la letra grande no basta."""
        html = quita_comentarios_html((WEB / "index.html").read_text(encoding="utf-8"))
        assert "user-scalable=no" not in html
        assert "width=device-width" in html

    def test_los_numeros_se_piden_con_teclado_numerico(self):
        """En el móvil, un número tiene que sacar el teclado de números y no el de letras.

        **Esto miraba `app.js` y ya no está ahí**: los campos de la interfaz se migraron a React y el que
        decide el teclado es la pieza del campo (`react/piezas/campo.js`). Se escribe `inputMode` (que es
        lo que entiende React) y el analizador del navegador lo deja en el atributo `inputmode`; por eso
        la comprobación de verdad es la de un navegador de verdad
        (`scripts/comprobar_en_un_navegador.py`, la ruta de las hectáreas, que busca
        `inputmode="decimal"` en el HTML que dibuja Chrome).
        """
        pieza = (WEB / "react" / "piezas" / "campo.js").read_text(encoding="utf-8")
        assert '"decimal"' in pieza, "el campo no pide el teclado de números con coma"
        assert '"numeric"' in pieza, "el campo no sabe pedir un número sin decimales (una hora)"
        codigo = (WEB / "app.js").read_text(encoding="utf-8")
        assert 'tipo: "numero"' in codigo, "el asistente no pide ningún número con su teclado"
        assert 'tipo: "entero"' in codigo, "el asistente no pide ninguna hora con su teclado"

    def test_hay_un_boton_que_dice_que_no_sabe_que_pulsar(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        botones = {b["id"]: b for b in datos["pantalla_inicio"]["botones"]}
        assert botones["ayuda"]["texto"] == "NO SÉ QUÉ PULSAR"

    def test_la_pantalla_avisa_de_lo_que_queda_pendiente_de_mandar(self):
        codigo = (WEB / "app.js").read_text(encoding="utf-8")
        assert "aviso-pendientes" in codigo
        assert "mandarPendientes" in codigo

    def test_se_puede_deshacer_lo_apuntado(self):
        codigo = (WEB / "app.js").read_text(encoding="utf-8")
        assert "deshacer" in codigo

    def test_hay_un_boton_para_repetir_lo_de_la_ultima_vez(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        assert datos["pantalla_inicio"]["repetir"]["texto"] == "LO MISMO QUE LA ÚLTIMA VEZ"

    def test_cada_campo_lleva_su_explicacion_al_lado(self):
        """Debajo de cada campo va su explicación: qué es, para qué sirve, un ejemplo y qué pasa si falta.

        **Esto miraba `app.js` y ya no está ahí**: el bloque lo pinta la pieza del campo
        (`react/piezas/ayuda_de_un_campo.js`) y los cuatro rótulos los sirve el servidor. Lo que queda en
        `app.js` es preparar los datos (`datosDeLaAyuda`), que es lo que se comprueba aquí.
        """
        pieza = (WEB / "react" / "piezas" / "ayuda_de_un_campo.js").read_text(encoding="utf-8")
        assert "ayuda-campo" in pieza
        for rotulo in ("que_es", "por_que", "ejemplo", "si_falta"):
            assert f"rotulos.{rotulo}" in pieza or f"r.{rotulo}" in pieza, (
                f"a la ayuda del campo le falta el rótulo «{rotulo}»"
            )
        codigo = (WEB / "app.js").read_text(encoding="utf-8")
        assert "datosDeLaAyuda" in codigo, "la aplicación ya no prepara los datos de la ayuda"
        assert "ayuda.rotulos_de_un_campo" in codigo, "los rótulos ya no se piden al servidor"

    def test_la_pantalla_de_ayuda_existe_y_tiene_los_porques(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        assert datos["ayuda"]["pantalla"]["titulo"] == "Ayuda"
        assert "para_que_sirve" in datos["ayuda"]["porques"]
        assert "papel_o_digital" in datos["ayuda"]["porques"]
        assert datos["ayuda"]["campos"]

    def test_las_medidas_preventivas_se_preguntan_en_cristiano(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        assert len(datos["medidas_preventivas"]) == len(catalogos.MEDIDAS_PREVENTIVAS)
        for medida in datos["medidas_preventivas"]:
            assert medida["pregunta"].startswith("¿"), (
                f"{medida['codigo']} no se pregunta como una pregunta"
            )

    def test_la_interfaz_dice_las_fechas_que_importan(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        plazos = datos["plazos_legales"]
        assert plazos["cuaderno_en_papel_hasta"] == "31/12/2026"
        assert plazos["productos_electronico_desde"] == "01/01/2027"


class TestSinCobertura:
    def test_la_aplicacion_se_guarda_en_el_movil_para_abrirla_sin_cobertura(self):
        codigo = (WEB / "service-worker.js").read_text(encoding="utf-8")
        for fichero in (
            "/index.html",
            "/estilos.css",
            "/app.js",
            "/nucleo.js",
            # La pantalla de inicio se pinta con React: si estos no se guardan, en el campo no
            # se puede dibujar la primera pantalla. Se añadieron al pasarla a React, y esta
            # prueba se amplió con ellos a propósito: quitar uno de esta lista es dejar al
            # agricultor sin pantalla justo donde no hay cobertura para volver a descargarlo.
            "/vendor/react.production.min.js",
            "/vendor/react-dom.production.min.js",
            "/vendor/htm.umd.js",
            "/react/montar.js",
            "/react/pantallas/inicio.js",
        ):
            assert fichero in codigo, f"el service worker no guarda {fichero}"

    def test_la_cache_lleva_fecha_y_numero(self):
        """Sin cambiar el nombre de la caché, el móvil sigue con los ficheros viejos.

        Pasó al meter React: un despliegue con el `app.js` nuevo (que pide React) y la caché
        sin los ficheros de React deja al agricultor sin pantalla, y sin cobertura no hay forma
        de arreglarlo desde el móvil. El nombre lleva la fecha y un número para poder subirlo.
        """
        codigo = (WEB / "service-worker.js").read_text(encoding="utf-8")
        cache = re.search(r'const CACHE = "([^"]+)"', codigo)
        assert cache, "el service worker no declara el nombre de su caché"
        assert re.fullmatch(r"cuedigital-\d{4}-\d{2}-\d{2}-\d+", cache.group(1)), (
            f"el nombre de la caché no lleva fecha y número: {cache.group(1)}"
        )

    def test_los_datos_del_agricultor_no_se_guardan_en_la_cache(self):
        """La caché del navegador es de ficheros, no de sus datos. Esto no se toca."""
        codigo = (WEB / "service-worker.js").read_text(encoding="utf-8")
        assert 'url.pathname.startsWith("/api/")' in codigo

    def test_la_cola_de_pendientes_usa_el_almacen_del_movil(self):
        codigo = (WEB / "app.js").read_text(encoding="utf-8")
        assert "localStorage" in codigo
        assert "crearCola" in codigo


class TestCadaPreguntaTieneSuTexto:
    """Un campo que se pinta en una pantalla tiene que tener su pregunta escrita.

    `pintaCamposMaestro` saca la pregunta de `textos.ETIQUETAS` por la clave del campo. Si la
    clave no está, el campo sale en pantalla **con la etiqueta vacía**: un hueco sin explicación
    al lado de una casilla, que para quien no sabe de informática es peor que no preguntar.

    **Pasó de verdad.** `labor.material_tratado`, `labor.material_adquirido` y
    `labor.fecha_adquisicion` salían sin pregunta en la pantalla de la siembra, y no se notó
    porque ningún test miraba esa pantalla entera. Esto recorre **todas** las claves del mapa de
    campos de `app.js`, así que la próxima vez salta solo.
    """

    def claves_del_mapa_de_campos(self) -> set[str]:
        fuente = (WEB / "app.js").read_text(encoding="utf-8")
        return set(re.findall(r'^\s*"([a-z_]+\.[a-z_0-9]+)":\s*\{\s*campo:', fuente, re.M))

    def etiquetas_que_ve_la_pantalla(self) -> dict:
        """Las mismas que sirve la aplicación, con la misma suma.

        El enrutador manda `{**textos.ETIQUETAS, **textos.ETIQUETAS_MAESTRO}` porque para la
        interfaz son lo mismo: las de las pantallas de alta y las del asistente. El test usa la
        misma expresión a propósito, para que no pueda comprobar una cosa distinta de la que se
        sirve.
        """
        return {**textos.ETIQUETAS, **textos.ETIQUETAS_MAESTRO}

    def test_hay_claves_que_comprobar(self):
        """Si el mapa cambiara de forma y el test no encontrara nada, no valdría para nada."""
        assert len(self.claves_del_mapa_de_campos()) > 30

    def test_todas_tienen_su_pregunta(self):
        etiquetas = self.etiquetas_que_ve_la_pantalla()
        faltan = [
            clave for clave in sorted(self.claves_del_mapa_de_campos()) if clave not in etiquetas
        ]
        assert faltan == [], f"campos que se pintan sin pregunta: {faltan}"

    def test_ninguna_pregunta_esta_vacia(self):
        etiquetas = self.etiquetas_que_ve_la_pantalla()
        for clave in sorted(self.claves_del_mapa_de_campos()):
            assert etiquetas[clave].get("pregunta", "").strip(), clave

    def test_y_ninguna_lleva_jerga(self):
        etiquetas = self.etiquetas_que_ve_la_pantalla()
        for clave in sorted(self.claves_del_mapa_de_campos()):
            for valor in etiquetas[clave].values():
                assert not textos.palabras_prohibidas_encontradas(valor), (clave, valor)


class TestLasPreguntasDelAsistenteEstanYSeComprueban:
    """Las preguntas del asistente son `et("clave")` y `pi("clave")`, no campos.

    El test de arriba recorre el mapa de campos de `pintaCamposMaestro`. Pero el asistente
    tiene además las preguntas de **cada pantalla**, y esas se piden con `et("plan.cultivo")`
    o `t("etiquetas.plan.cultivo.pregunta")`. Esa forma de pedirlas tenía dos agujeros, y los
    dos se han visto de verdad:

    1. Si la clave no está en `textos`, la pantalla sale **con la pregunta en blanco**: el
       agricultor ve una casilla sin saber qué le preguntan.
    2. Si la clave no está en la copia de los textos que usan los tests de JavaScript
       (`tests_js/interfaz.test.js`), el test pinta la pregunta en blanco y **da por bueno**
       cualquier cosa. Pasó con `plan.herramienta`: el test buscaba la pregunta, no la
       encontraba, y en vez de avisar se iba hasta el resumen.

    Este test saca las claves del propio `app.js`, así que no hay lista que mantener a mano:
    la próxima vez que se añada una pantalla, salta solo.
    """

    def claves_del_asistente(self) -> set[str]:
        fuente = (WEB / "app.js").read_text(encoding="utf-8")
        claves = set(re.findall(r'\bet\("([a-z0-9_.]+)"\)', fuente))
        claves |= set(re.findall(r'\bpi\("([a-z0-9_.]+)"\)', fuente))
        claves |= set(
            re.findall(r't\("etiquetas\.([a-z0-9_.]+)\.(?:pregunta|pista)"', fuente)
        )
        return claves

    def textos_del_test_de_javascript(self) -> str:
        return (
            Path(__file__).resolve().parents[1] / "tests_js" / "interfaz.test.js"
        ).read_text(encoding="utf-8")

    def test_hay_claves_que_comprobar(self):
        """Si `app.js` cambiara de forma y no se encontrara nada, el test no valdría."""
        assert len(self.claves_del_asistente()) > 40

    def test_todas_las_preguntas_del_asistente_se_sirven(self):
        """Sin la clave en `textos`, la pregunta sale en blanco delante del agricultor."""
        etiquetas = {**textos.ETIQUETAS, **textos.ETIQUETAS_MAESTRO}
        faltan = sorted(
            clave
            for clave in self.claves_del_asistente()
            if not (etiquetas.get(clave) or {}).get("pregunta", "").strip()
        )
        assert faltan == [], f"preguntas del asistente que saldrían en blanco: {faltan}"

    def test_la_copia_del_test_no_se_queda_sin_esas_preguntas(self):
        """Si falta en la copia, el test de JavaScript pasa con la pregunta en blanco."""
        copia = self.textos_del_test_de_javascript()
        faltan = sorted(
            clave for clave in self.claves_del_asistente() if f'"{clave}"' not in copia
        )
        assert faltan == [], (
            "estas preguntas no están en la copia de los textos de "
            f"tests_js/interfaz.test.js, así que ningún test las ve: {faltan}"
        )

    def test_los_campos_del_mapa_tambien_estan_en_la_copia(self):
        """El mismo agujero, pero con las preguntas de `pintaCamposMaestro`.

        Esas preguntas se piden con `t("etiquetas.<clave>.pregunta")` desde el mapa `CAMPOS` de
        `app.js`, y hasta ahora solo se comprobaba que estuvieran **en la aplicación**, no en la copia
        que usan los tests del móvil. Se encontró al añadir los campos de la máquina (marca, modelo,
        de quién es): la pregunta del nº de ROMA salía en blanco en el test y el test no la veía.
        """
        fuente = (WEB / "app.js").read_text(encoding="utf-8")
        claves = set(
            re.findall(r'^\s*"([a-z_]+\.[a-z_0-9]+)":\s*\{\s*campo:', fuente, re.M)
        )
        assert len(claves) > 30, "el mapa de campos de app.js no se ha podido leer"
        copia = self.textos_del_test_de_javascript()
        faltan = sorted(clave for clave in claves if f'"{clave}"' not in copia)
        assert faltan == [], (
            "estos campos se preguntan en pantalla y su pregunta no está en la copia de los textos "
            f"de tests_js/interfaz.test.js: {faltan}"
        )

    def test_la_copia_del_test_lleva_la_misma_pregunta_que_la_aplicacion(self):
        """La copia puede recortar la pista, pero no puede decir otra cosa.

        Si dijera otra cosa, los tests comprobarían una pantalla que el agricultor no tiene.
        """
        etiquetas = {**textos.ETIQUETAS, **textos.ETIQUETAS_MAESTRO}
        copia = self.textos_del_test_de_javascript()
        distintas = []
        for clave in sorted(self.claves_del_asistente()):
            servida = etiquetas[clave]["pregunta"]
            encontrada = re.search(
                r'"' + re.escape(clave) + r'":\s*\{\s*pregunta:\s*"([^"]*)"', copia
            )
            if encontrada and encontrada.group(1) != servida:
                distintas.append((clave, servida, encontrada.group(1)))
        assert distintas == [], f"la copia dice otra pregunta: {distintas}"


class TestLosEnlacesOficialesYElRegistroElectronico:
    """Cuando hay que traer un dato de fuera, la dirección tiene que estar en la aplicación.

    David lo pidió así: «si hay que traer datos de algún lado, poner el enlace para facilitar la
    tarea». Y preguntó también qué es eso del registro electrónico y dónde se apuntan los apuntes:
    las dos cosas se contestan en la pantalla de «mi cuaderno», con la ley detrás.
    """

    def test_se_sirve_la_explicacion_del_registro_electronico(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        registro = datos["registro_electronico"]
        assert registro["que_es"] and registro["donde"]
        # Las fechas que deciden si el agricultor puede seguir con el papel o no.
        assert "31 de diciembre de 2026" in registro["desde_cuando"]
        assert "1 de enero de 2027" in registro["desde_cuando"]
        assert "voluntario" in registro["es_voluntario"]

    def test_cada_sitio_oficial_lleva_su_direccion(self, cliente):
        registro = cliente.get("/api/interfaz").json()["registro_electronico"]
        enlaces = registro["enlaces"]
        assert len(enlaces) >= 6, f"solo hay {len(enlaces)} enlaces oficiales"
        for enlace in enlaces:
            assert enlace["texto"], "un enlace sin texto no se puede pulsar"
            assert enlace["url"].startswith("https://"), enlace
        direcciones = " ".join(enlace["url"] for enlace in enlaces)
        # Los cuatro sitios que de verdad hacen falta para rellenar el cuaderno.
        assert "particulares.ayg.jcyl.es" in direcciones
        assert "registro-explotaciones-agrarias-castilla.html" in direcciones
        assert "registro-productos" in direcciones
        assert "boe.es" in direcciones


class TestElTipoDeCarne:
    """El carné de quien echa el producto tiene cuatro tipos, y los dice el cuaderno de la Junta.

    Su hoja 1.2 tiene una columna para cada uno (básico, cualificado, fumigador y piloto) y se marca
    con una cruz. Con un texto libre la cruz no se puede poner, así que la lista es cerrada.
    """

    def test_los_cuatro_tipos_se_sirven_con_su_nombre(self, cliente):
        tipos = cliente.get("/api/interfaz").json()["tipos_carne"]
        valores = [tipo["valor"] for tipo in tipos]
        assert valores == ["basico", "cualificado", "fumigador", "piloto"]
        assert all(tipo["texto"] for tipo in tipos), "un tipo sin nombre no se puede elegir"

    def test_un_tipo_inventado_se_rechaza_con_la_lista(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/aplicadores",
            headers=cuenta["cabeceras"],
            json={"nombre": "Alguien", "tipo_carne": "nivel 2"},
        )
        assert respuesta.status_code == 422
        assert "no es un tipo de carné" in respuesta.json()["detail"]
        assert "Cualificado" in respuesta.json()["detail"]

    def test_se_guarda_en_minusculas_y_sin_espacios(self, cliente, cuenta):
        """Para que la cruz de la hoja 1.2 se ponga siempre en el mismo sitio."""
        respuesta = cliente.post(
            "/api/aplicadores",
            headers=cuenta["cabeceras"],
            json={"nombre": "Alguien", "tipo_carne": "  Cualificado "},
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["tipo_carne"] == "cualificado"
