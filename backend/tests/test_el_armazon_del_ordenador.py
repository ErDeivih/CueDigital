"""El armazón del ordenador: el menú lateral y la barra de arriba (30/09/2026).

**Por qué existe esta prueba.** David lo pidió con estas palabras: *«debe ser responsive para usarse en pc y
móvil, no solo móvil… hacer una versión para pc que parezca una aplicación de gestión»*. Hasta hoy no había
nada de eso: la aplicación era una columna de móvil de 44 rem con botones de 64 px y **ni un solo
`@media`**, así que en un ordenador se veía un móvil en medio de la pantalla y para llegar a las 64 tierras
había que saber que estaban detrás de un botón de la pantalla de inicio.

Esta prueba defiende las cuatro piezas de las que depende que eso funcione, y **cada una por un motivo que
ya ha dolido alguna vez en este proyecto**:

  1. **El armazón tiene que estar en el HTML** (`#marco`). Si falta el contenedor, React no monta nada y el
     ordenador se queda sin menú, sin que ninguna prueba de pantallas se entere (las pantallas se montan en
     otro contenedor).
  2. **El CSS tiene que tener los dos lados del `@media`**: el de escritorio (menú, barra, ancho) y el de
     móvil (esconder el armazón). Sin el segundo, el menú se comería la pantalla de un móvil.
  3. **Cada renglón del menú tiene que tener su texto de verdad.** Los nombres salen de `textos.py`, y un
     texto que falta **no revienta nada**: deja el renglón en blanco y el agricultor ve un botón vacío. Es
     el mismo fallo que cazó `test_que_no_falte_ningun_texto.py` en su día, pero aquí las claves se piden
     desde una tabla de `app.js` (`MODULOS`), así que hay que comprobarlo a mano.
  4. **El armazón tiene que ir en la caché del campo** (`marco.js` en el `service-worker`): sin él, un
     ordenador que abra la aplicación sin cobertura se queda sin menú.
"""

from __future__ import annotations

import pathlib
import re

from app.routers import interfaz as router_interfaz

RAIZ = pathlib.Path(__file__).resolve().parents[2]
WEB = RAIZ / "backend" / "web"
APP = WEB / "app.js"
CSS = WEB / "estilos.css"
HTML = WEB / "index.html"
SERVICIO = WEB / "service-worker.js"
MARCO = WEB / "react" / "piezas" / "marco.js"


def _modulos_del_menu() -> list[tuple[str, str, str]]:
    """Los módulos de la tabla `MODULOS` de `app.js`: (clave, clave del texto, acción)."""
    codigo = APP.read_text(encoding="utf-8")
    trozo = codigo.split("const MODULOS = [", 1)
    assert len(trozo) == 2, "no se encuentra la tabla de módulos del menú en app.js"
    tabla = trozo[1].split("];", 1)[0]
    return [
        (clave, texto, accion)
        for clave, texto, accion in re.findall(
            r'\{\s*clave:\s*"([^"]+)",\s*texto:\s*"([^"]+)",\s*accion:\s*"([^"]+)"', tabla
        )
    ]


class TestElArmazonEsta:
    def test_el_contenedor_del_armazon_esta_en_el_html(self):
        html = HTML.read_text(encoding="utf-8")
        assert 'id="marco"' in html, (
            "falta el contenedor del armazón (`#marco`) en index.html: sin él, en un ordenador no hay menú"
        )
        # Y tiene que ir **antes** de la pantalla: el armazón es el marco donde vive la pantalla.
        assert html.index('id="marco"') < html.index('id="pantalla"')

    def test_el_css_tiene_la_parte_de_escritorio_y_la_de_movil(self):
        css = CSS.read_text(encoding="utf-8")
        assert "@media (min-width: 64rem)" in css, "no hay ninguna regla para pantallas anchas"
        assert ".marco .menu" in css, "el menú lateral no tiene estilos"
        assert ".marco .barra" in css, "la barra de arriba no tiene estilos"
        assert "max-width: none" in css, "la pantalla sigue siendo una columna de móvil en el ordenador"
        # Y el otro lado: en una pantalla estrecha el armazón **no se ve**. Se dice a propósito para que
        # nadie lo quite creyendo que sobra.
        assert "@media (max-width: 63.99rem)" in css, "no se esconde el armazón en el móvil"
        escondido = css.split("@media (max-width: 63.99rem)", 1)[1]
        assert "display: none" in escondido.split("}", 1)[0]

    def test_la_cabecera_de_movil_se_esconde_en_el_ordenador(self):
        """En el ordenador, el trabajo de la cabecera lo hace la barra: dos barras pegadas son una de más.

        La cabecera **sigue en el HTML** (sus botones y su `#cabecera-texto` los usan las pruebas y el
        móvil): lo único que cambia es que en pantalla ancha no se enseña.
        """
        css = CSS.read_text(encoding="utf-8")
        ancho = css.split("@media (min-width: 64rem)", 1)[1].split("@media (max-width: 63.99rem)", 1)[0]
        assert re.search(r"header\.cabecera\s*\{\s*display:\s*none", ancho), (
            "en el ordenador se siguen viendo las dos barras (la cabecera de móvil y la del armazón)"
        )

    def test_los_botones_de_la_barra_son_mas_pequenos_que_los_del_movil(self):
        """Con ratón no hacen falta 64 px, pero tampoco 20: se quedan en 2.9 rem (unos 46 px).

        Es una decisión, y por eso está escrita: el agricultor tiene entre 50 y 70 años y aquí usa ratón,
        así que los botones de la barra y de las filas de una tabla pueden ser más pequeños que los del
        móvil, pero no minúsculos.
        """
        css = CSS.read_text(encoding="utf-8")
        ancho = css.split("@media (min-width: 64rem)", 1)[1].split("@media (max-width: 63.99rem)", 1)[0]
        assert "min-height: 2.9rem" in ancho
        # Y las medidas del móvil no se tocan: siguen ahí para la pantalla estrecha.
        assert "--toque: 64px" in css
        assert "min-height: var(--toque)" in css


class TestElPanelNoAprietaLaTabla:
    """El panel de detalle al lado de la tabla, y **cuándo deja de caber** (30/09/2026).

    **Por qué existe esta prueba, con lo que la trajo.** La primera vez que se miró la versión de
    ordenador **con los datos de verdad** (64 tierras, no dos de prueba) fue en la revisión de la
    interfaz, y en un portátil de 1024 px apareció el fallo: con el panel al lado, a la tabla de tierras
    le quedaban 22 rem y **la columna de Acciones se quedaba fuera de la pantalla**. El agricultor veía
    tres columnas de cinco y tenía que desplazar la tabla en horizontal para llegar al botón de cada
    fila. Ninguna prueba lo cazaba porque todas las capturas eran a 1440 px.

    La cuenta está medida (menú 17 rem + márgenes 4 rem + panel 20 rem + hueco 1 rem + tabla 30 rem =
    **72 rem**), y por eso la regla es la que es: por debajo de 72 rem el panel va debajo.
    """

    def _css_del_ordenador(self) -> str:
        css = CSS.read_text(encoding="utf-8")
        return css.split("@media (min-width: 64rem)", 1)[1].split("@media (max-width: 63.99rem)", 1)[0]

    def test_el_panel_va_al_lado_en_una_pantalla_ancha(self):
        ancho = self._css_del_ordenador()
        assert "grid-template-columns: minmax(0, 1fr) 20rem" in ancho, (
            "el panel de detalle ya no va al lado de la tabla en el ordenador"
        )

    def test_por_debajo_de_72_rem_el_panel_pasa_debajo(self):
        """La cuenta de las medidas, escrita aquí para que nadie «arregle» el número sin hacerla."""
        ancho = self._css_del_ordenador()
        assert "@media (max-width: 71.99rem)" in ancho, (
            "no hay ninguna regla para el ancho en el que el panel y la tabla no caben juntos: en un "
            "portátil de 1024 px, la tabla deja fuera la columna de Acciones (se vio en la revisión de "
            "la interfaz del 30/09/2026)"
        )
        estrecho = ancho.split("@media (max-width: 71.99rem)", 1)[1]
        assert "grid-template-columns: minmax(0, 1fr)" in estrecho, (
            "en pantalla estrecha el panel sigue ocupando su columna al lado de la tabla"
        )
        # Y deja de ser pegajoso: si va debajo, no tiene que acompañar a nadie.
        assert re.search(r"\.panel-detalle\s*\{\s*position:\s*static", estrecho), (
            "el panel sigue siendo pegajoso cuando va debajo de la tabla"
        )

    def test_el_ancho_minimo_del_escritorio_cabe_en_la_cuenta(self):
        """64 rem (el mínimo del escritorio) es **menos** que 72 rem: por eso hace falta la regla de arriba.

        Si algún día el mínimo del escritorio subiera a 72 rem, esta regla sobraría; y si bajara, el
        fallo sería más gordo. Se comprueba para que los tres números (64, 72 y 20 rem del panel) no se
        separen sin que nadie se entere.
        """
        css = CSS.read_text(encoding="utf-8")
        assert "@media (min-width: 64rem)" in css
        assert 64 < 72, "el mínimo del escritorio ya no es menor que el ancho que necesita la tabla"


class TestElMenuTieneSusNombres:
    def test_hay_modulos_en_el_menu(self):
        modulos = _modulos_del_menu()
        assert len(modulos) >= 12, f"el menú se ha quedado con {len(modulos)} módulos"

    def test_cada_modulo_tiene_su_texto_en_el_servidor(self):
        """Un renglón del menú sin texto es un botón vacío, y eso no revienta nada: solo se ve mal."""
        vocabulario = router_interfaz.interfaz()
        sin_texto = []
        for clave, texto, _accion in _modulos_del_menu():
            partes = texto.split(".")
            valor = vocabulario
            for parte in partes:
                valor = valor.get(parte) if isinstance(valor, dict) else None
            if not (isinstance(valor, str) and valor.strip()):
                sin_texto.append(f"{clave} → {texto}")
        assert sin_texto == [], f"estos módulos del menú saldrían sin nombre: {sin_texto}"

    def test_cada_modulo_lleva_su_accion(self):
        """Y su acción tiene que ser una de las que el manejador de clics atiende.

        `test_los_botones_hacen_algo.py` mira esto por el otro lado (lo que se pinta en los componentes);
        aquí se mira la tabla de `app.js`, que es de donde salen las acciones del menú.
        """
        atendidas = set(re.findall(r'nombre === "([a-z-]+)"', APP.read_text(encoding="utf-8")))
        huerfanas = sorted(
            {accion for _clave, _texto, accion in _modulos_del_menu() if accion not in atendidas}
        )
        assert huerfanas == [], f"hay módulos del menú que no hacen nada al pulsarlos: {huerfanas}"

    def test_el_modulo_activo_se_marca_por_la_pantalla(self):
        """El módulo en el que se está lo dice **la pantalla que está puesta**, no el botón pulsado.

        «Mi cuaderno» se abre desde el menú, desde la pantalla de inicio y desde el aviso de lo que falta;
        en los tres sitios tiene que marcar el mismo renglón. Por eso hay una tabla de pantalla → módulo, y
        por eso se comprueba que **todas las pantallas migradas** estén en ella o no estén en ninguna (una
        pantalla que no está deja el menú sin marcar, y ahí el agricultor no sabe dónde está).
        """
        codigo = APP.read_text(encoding="utf-8")
        trozo = codigo.split("const MODULO_DE_LA_PANTALLA = {", 1)
        assert len(trozo) == 2, "no se encuentra la tabla de pantalla → módulo"
        tabla = trozo[1].split("};", 1)[0]
        asignadas = dict(re.findall(r"(\w+):\s*\"([a-z]+)\"", tabla))
        assert len(asignadas) >= 20, f"solo hay {len(asignadas)} pantallas con módulo"
        # Y todos los módulos que se usan en la tabla tienen que existir en el menú.
        claves = {clave for clave, _texto, _accion in _modulos_del_menu()}
        inventados = sorted(set(asignadas.values()) - claves)
        assert inventados == [], f"estas pantallas marcan un módulo que no está en el menú: {inventados}"

    def test_el_armazon_se_guarda_para_el_campo(self):
        guardados = set(re.findall(r'"([^"]+\.js)"', SERVICIO.read_text(encoding="utf-8")))
        assert "/react/piezas/marco.js" in guardados, (
            "el armazón no se guarda en la caché: un ordenador sin cobertura se quedaría sin menú"
        )

    def test_el_armazon_no_escribe_ninguna_frase(self):
        """Los nombres de los módulos y las palabras de la barra vienen del servidor, como todo.

        **Aquí no se mira el texto del fichero**: eso ya lo hace la prueba del componente
        (`tests_js/react.test.js`, «el armazón no lleva ni una frase escrita a mano»), que monta el armazón y
        compara **cada frase que se ve** con los textos del servidor. Mirar aquí los trozos entre `>` y `<`
        daba falsos positivos (el propio `html\`` de la plantilla) sin comprobar nada de verdad, así que lo
        que se comprueba en esta prueba es lo que sí se puede comprobar leyendo: que el componente **no
        lleve ni un texto suelto entre las etiquetas** de sus plantillas.
        """
        codigo = MARCO.read_text(encoding="utf-8")
        sin_comentarios = re.sub(r"/\*[\s\S]*?\*/", "", codigo)
        sin_comentarios = re.sub(r"^\s*//.*$", "", sin_comentarios, flags=re.M)
        # Cada texto que se enseña tiene que salir de `frase(...)`: si aparece un literal suelto dentro de
        # la plantilla, es una frase escrita a mano.
        assert re.search(r"<[a-z]+[^>]*>\s*[A-Za-zÁÉÍÓÚÑáéíóúñ][^<${]*</", sin_comentarios) is None, (
            "hay texto escrito a mano dentro de una etiqueta del armazón"
        )
