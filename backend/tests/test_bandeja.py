"""Las pruebas del T08: la bandeja documental (S10, 06/10/2026).

Están escritas al revés de lo habitual: **primero la regla del ticket, y la prueba lleva su nombre**. El
encargo lo pide así porque son las reglas que no se pueden saltar, y una prueba llamada
`test_lo_que_esta_bien` no protege nada:

| Regla que no se puede saltar | Prueba que falla si se rompe |
|---|---|
| El original no se toca nunca (ni su fichero ni su huella) | `TestElOriginalNoSeToca` |
| Lo leído es una propuesta, no un dato | `TestLoLeidoEsUnaPropuesta` |
| No se puede confirmar sin haber revisado | `TestNoSeConfirmaSinRevisar` |
| Subir dos veces el mismo papel no crea dos fichas | `TestElMismoPapelNoEntraDosVeces` |
| Un importe que no consta NO es cero | `TestUnImporteQueNoConstaNoEsCero` |
| Vincular no crea el gasto, ni la factura, ni la venta | `TestEnlazarNoCreaNada` |
| Una rectificativa no borra la anterior | `TestLasRectificativasDejanLasDos` |
| El tipo «inspección» entra sin romper los cuatro que ya había | `TestLosTiposDePapel` |
| No se dice que la lectura sea buena (ni porcentajes) | `TestNoSeMideLaCalidadDeLaLectura` |
| El papel de una finca no se ve desde otra | `TestAislamientoEntreFincas` |

## Lo que se puede probar hoy y lo que no

La lógica entera —los tipos, los estados, los duplicados, lo que se acepta, las clases de vínculo y las
rectificativas— es **`app/bandeja.py`**: funciones puras, sin base de datos y sin servidor. Eso se prueba
aquí y corre hoy.

La parte que guarda (`app/routers/bandeja_api.py`) necesita **las columnas nuevas de `documentos_anexos`,
la tabla `vinculos_de_documento` y los siete esquemas**, y esos ficheros son compartidos: los integra el
coordinador (`app/models.py`, `app/schemas.py`, `app/textos.py` y `app/catalogos.py`, con los bloques
literales de `docs/T08_BANDEJA.md`). Mientras no estén, esas pruebas **se saltan diciendo exactamente qué
falta** en vez de quedarse en verde sin comprobar nada —es la misma decisión del T13 y del T20—, y el día
que se integren corren solas, sin tocar este fichero.

Y hay un tercer grupo, que es el que impide que este ticket se entregue mintiendo: **las pruebas que leen
el informe** (`docs/T08_BANDEJA.md`) y comprueban que lo que falta está dicho, que los bloques que hay que
pegar se pueden ejecutar, y que **la pantalla no pinta ni una acción que no esté en la lista del informe**
(que es lo que el coordinador tiene que atar en `app.js`).
"""

from __future__ import annotations

import ast
import datetime as dt
import importlib
import pathlib
import re
import textwrap
from decimal import Decimal

import pytest

from app import bandeja, catalogos, dinero, facturas, ocr, textos

RAIZ = pathlib.Path(__file__).resolve().parents[2]
INFORME = RAIZ / "docs" / "T08_BANDEJA.md"
PANTALLA = RAIZ / "backend" / "web" / "react" / "pantallas" / "bandeja.js"
APP_JS = RAIZ / "backend" / "web" / "app.js"
ROUTER = RAIZ / "backend" / "app" / "routers" / "bandeja_api.py"


# ==========================================================================
# ¿Está ya integrado lo que este ticket necesita para probar el servidor?
# ==========================================================================
#
# Las columnas, la tabla, los esquemas, los textos y los tipos van en ficheros compartidos que **integra
# el coordinador**, así que puede ocurrir que este fichero de pruebas se ejecute antes de que estén. En ese
# caso las pruebas del recorrido **se saltan con el motivo escrito**, en vez de dar un rojo que no es de
# nadie o —peor— un verde que no comprueba nada.

COLUMNAS_QUE_FALTAN = {
    "tabla vinculos_de_documento": "VinculoDeDocumento",
}
COLUMNAS_DEL_PAPEL = (
    "huella",
    "estado_revision",
    "propuesta",
    "como_se_leyo",
    "propuesta_descartada",
    "datos_confirmados",
    "confirmado_en",
    "confirmado_por_usuario_id",
    "rectifica_a_id",
)


def _lo_que_falta_por_integrar() -> list[str]:
    """Lo que este ticket necesita y no puede escribir él, **leído de verdad**.

    Se mira con `hasattr` y no con una lista escrita a mano: el día que el coordinador integre las columnas
    y la tabla, esta función devuelve la lista vacía sola, sin que nadie se acuerde de tocar nada.
    """
    try:
        modelos = importlib.import_module("app.models")
    except Exception as fallo:  # noqa: BLE001 — cualquier fallo aquí es «no está integrado»
        return [f"no se puede importar `app.models`: {fallo}"]

    falta: list[str] = []
    documento = getattr(modelos, "DocumentoAnexo", None)
    for columna in COLUMNAS_DEL_PAPEL:
        if documento is None or not hasattr(documento, columna):
            falta.append(f"la columna documentos_anexos.{columna}")
    for nombre, atributo in COLUMNAS_QUE_FALTAN.items():
        if not hasattr(modelos, atributo):
            falta.append(nombre)
    try:
        esquemas = importlib.import_module("app.schemas")
    except Exception as fallo:  # noqa: BLE001
        falta.append(f"no se puede importar `app.schemas`: {fallo}")
    else:
        for nombre in (
            "PapelDeLaBandejaSalida",
            "LaBandejaSalida",
            "LaPropuestaSalida",
            "LoQueSeAceptoSalida",
            "VinculoDeUnPapelSalida",
            "ElFicheroComprobadoSalida",
            "LosCandidatosSalida",
            "LoQueHaPasadoSalida",
        ):
            if not hasattr(esquemas, nombre):
                falta.append(f"el esquema {nombre} de `app.schemas`")
    try:
        textos = importlib.import_module("app.textos")
    except Exception as fallo:  # noqa: BLE001
        falta.append(f"no se puede importar `app.textos`: {fallo}")
    else:
        if not hasattr(textos, "BANDEJA"):
            falta.append("los textos de la bandeja (`textos.BANDEJA`)")
        if "T08_papel_en_la_bandeja" not in textos.MENSAJES:
            falta.append("los mensajes `T08_*` de `textos.MENSAJES`")
    if "inspeccion" not in catalogos.TIPOS_DOCUMENTO:
        falta.append("el tipo de papel `inspeccion` en `catalogos.TIPOS_DOCUMENTO`")
    try:
        importlib.import_module("app.routers.bandeja_api")
    except Exception as fallo:  # noqa: BLE001
        falta.append(f"no se puede importar `app.routers.bandeja_api`: {fallo}")
    return falta


FALTA_POR_INTEGRAR = _lo_que_falta_por_integrar()

sin_integrar = pytest.mark.skipif(
    bool(FALTA_POR_INTEGRAR),
    reason=(
        "el recorrido de la bandeja necesita lo que integra el coordinador (las tablas, los esquemas, los "
        "textos y los tipos): el bloque literal está en `docs/T08_BANDEJA.md`"
    ),
)


# ==========================================================================
# Leer el informe: los bloques que hay que pegar y las acciones de la pantalla
# ==========================================================================


def _el_bloque(marcador: str) -> str:
    """El bloque literal del informe que va después de ese marcador.

    Los bloques se guardan así —con su marcador y su cerca— para que se puedan **pegar tal cual** y para
    que estas pruebas puedan leerlos: el bloque de las columnas va con su sangría (va dentro de una clase) y
    el de la tabla es una clase entera. Hay una prueba, más abajo, que comprueba que cada uno se puede
    ejecutar.
    """
    informe = INFORME.read_text(encoding="utf-8")
    patron = re.compile(
        rf"<!-- bloque: {re.escape(marcador)} -->\s*```[a-z]*\n(.*?)\n```", re.DOTALL
    )
    encontrado = patron.search(informe)
    assert encontrado, f"el informe no tiene el bloque «{marcador}», y hay que pegarlo"
    return encontrado.group(1)


def _las_acciones_de_la_pantalla() -> set[str]:
    """Las acciones que pinta `bandeja.js`, leídas del código (no de una lista escrita a mano).

    Es el mismo extractor que usa el guardián de los botones (`tests/test_los_botones_hacen_algo.py`), y por
    el mismo motivo: una lista a mano se queda vieja y deja de comprobar.
    """
    codigo = PANTALLA.read_text(encoding="utf-8")
    return set(re.findall(r"""\baccion=["']([a-z0-9_-]+)["']""", codigo))


def _las_acciones_que_atiende_app_js() -> set[str]:
    """Las acciones que el manejador de clics de `app.js` sabe atender."""
    codigo = APP_JS.read_text(encoding="utf-8")
    return set(re.findall(r"""nombre === ["']([a-z0-9_-]+)["']""", codigo))


def _las_acciones_que_el_informe_declara_pendientes() -> set[str]:
    """Las acciones que el informe dice que **todavía no** atiende `app.js`.

    Van escritas en una sola línea del informe (`pendientes en app.js: …`) para que esta prueba pueda
    compararlas con lo que de verdad falta: un informe que diga «falta atarlo» sin decir qué es un informe
    que nadie puede seguir.
    """
    informe = INFORME.read_text(encoding="utf-8")
    encontrado = re.search(r"^pendientes en app\.js: (.+)$", informe, re.MULTILINE)
    assert encontrado, "el informe no dice qué acciones están pendientes de atar en `app.js`"
    return {accion.strip() for accion in encontrado.group(1).split(",") if accion.strip()}


# ==========================================================================
# 1. Los tipos de papel
# ==========================================================================


class TestLosTiposDePapel:
    def test_los_cuatro_de_siempre_siguen_estando(self):
        """**Lo que el ticket prohíbe romper.** Los cuatro tipos que ya había son los que nombra el
        documento de la Junta: si el ticket los cambiara, los papeles que el agricultor ya tiene
        apuntados se quedarían con un tipo que no existe."""
        for tipo in ("contrato", "factura", "albaran_sigfito", "otros"):
            assert tipo in bandeja.TIPOS_DE_PAPEL, f"el tipo «{tipo}» se ha perdido"
            assert tipo in catalogos.TIPOS_DOCUMENTO

    def test_el_certificado_de_inspeccion_es_un_tipo(self):
        """Es el hueco que dejó escrito el T14: el papel de una inspección se apuntaba como «otros»."""
        assert "inspeccion" in bandeja.TIPOS_DE_PAPEL
        assert bandeja.etiqueta_de_papel("inspeccion") != catalogos.ETIQUETA_DOCUMENTO["otros"]

    def test_los_otros_tres_tipos_nuevos(self):
        for tipo in ("ticket", "albaran", "analitica"):
            assert tipo in bandeja.TIPOS_DE_PAPEL

    def test_el_albaran_de_entrega_no_es_el_de_los_envases(self):
        """Son dos papeles distintos y con el mismo nombre se confundirían."""
        assert "albaran" in bandeja.TIPOS_DE_PAPEL
        assert "albaran_sigfito" in bandeja.TIPOS_DE_PAPEL
        assert bandeja.etiqueta_de_papel("albaran") != bandeja.etiqueta_de_papel("albaran_sigfito")

    def test_ningun_tipo_se_repite(self):
        """La lista se arma con los del catálogo más los nuevos: el día que se integren, no pueden salir
        dos veces."""
        assert len(bandeja.TIPOS_DE_PAPEL) == len(set(bandeja.TIPOS_DE_PAPEL))

    def test_cada_tipo_tiene_su_nombre_en_palabras(self):
        for tipo in bandeja.TIPOS_DE_PAPEL:
            etiqueta = bandeja.etiqueta_de_papel(tipo)
            assert etiqueta
            if tipo != "otros":
                assert etiqueta != "Otro papel", f"«{tipo}» se queda sin nombre propio"

    def test_un_tipo_inventado_no_vale(self):
        assert not bandeja.es_un_tipo_de_papel("lo_que_sea")
        assert bandeja.etiqueta_de_papel("lo_que_sea") == catalogos.ETIQUETA_DOCUMENTO["otros"]

    def test_cada_tipo_dice_en_que_carpeta_cae(self):
        """Una sugerencia, no una obligación: lo que no se sabe cae a «Otros» y se puede cambiar."""
        assert bandeja.carpeta_sugerida_para("factura") == "Facturas"
        assert bandeja.carpeta_sugerida_para("contrato") == "Contratos"
        assert bandeja.carpeta_sugerida_para("inspeccion") == "Licencias y permisos"
        assert bandeja.carpeta_sugerida_para("otros") is None
        assert bandeja.carpeta_sugerida_para("inventado") is None
        for tipo in bandeja.TIPOS_DE_PAPEL:
            sugerida = bandeja.carpeta_sugerida_para(tipo)
            assert sugerida is None or sugerida in catalogos.CARPETAS_SUGERIDAS


# ==========================================================================
# 2. La revisión: los cuatro estados
# ==========================================================================


class TestLosEstadosDeLaRevision:
    def test_hay_cuatro_y_son_los_del_ticket(self):
        assert bandeja.ESTADOS == (
            bandeja.RECIEN_SUBIDO,
            bandeja.CLASIFICADO,
            bandeja.PROPUESTA_REVISADA,
            bandeja.CONFIRMADO,
        )

    def test_mientras_no_este_confirmado_esta_sin_revisar(self):
        """**La regla que hace que un papel que nadie ha mirado no parezca revisado.**"""
        for estado in bandeja.ESTADOS:
            assert bandeja.esta_sin_revisar(estado) is (estado != bandeja.CONFIRMADO)

    def test_un_papel_sin_decir_de_que_es_nace_recien_subido(self):
        assert bandeja.estado_al_subirlo(None) == bandeja.RECIEN_SUBIDO

    def test_un_papel_que_ya_sabe_de_que_es_nace_clasificado(self):
        assert bandeja.estado_al_subirlo("factura") == bandeja.CLASIFICADO

    def test_leer_no_cambia_de_estado(self):
        """**Leer no es revisar.** No hay ninguna función que confirme al leer, y tiene que seguir sin
        haberla: lo que se lee se guarda como propuesta y el papel sigue esperando a que alguien lo mire."""
        assert not hasattr(bandeja, "estado_al_leer")
        assert bandeja.estado_al_revisar() == bandeja.PROPUESTA_REVISADA
        assert bandeja.estado_al_revisar() != bandeja.CONFIRMADO
        assert bandeja.esta_sin_revisar(bandeja.estado_al_revisar())

    def test_clasificar_saca_de_recien_subido(self):
        assert bandeja.estado_al_clasificar() == bandeja.CLASIFICADO

    def test_un_estado_inventado_no_vale(self):
        assert not bandeja.es_un_estado("lo_que_sea")
        assert bandeja.esta_sin_revisar("lo_que_sea")
        assert bandeja.clave_del_estado("lo_que_sea") == "estado_desconocido"


# ==========================================================================
# 3. El original no se toca: la huella
# ==========================================================================


class TestElOriginalNoSeToca:
    def test_la_huella_es_la_misma_que_usa_el_resto_del_programa(self):
        """**No se escribe una tercera copia del SHA-256.** El programa ya tiene dos (`ocr.huella`, que usa
        el lector de facturas, y `extractos.huella_del_fichero`), y una tercera sería una tercera cosa que
        un día cambia sola. La de la bandeja es, literalmente, la misma función."""
        assert bandeja.huella_de is ocr.huella
        assert bandeja.huella_de(b"el contrato") == ocr.huella(b"el contrato")

    def test_la_huella_es_la_del_fichero_tal_y_como_llega(self):
        """El mismo contenido da la misma huella, y un byte de diferencia la cambia."""
        uno = bandeja.huella_de(b"factura de marzo")
        otro = bandeja.huella_de(b"factura de marzo ")
        assert uno == bandeja.huella_de(b"factura de marzo")
        assert uno != otro
        assert len(uno) == 64

    def test_dos_papeles_sin_fichero_no_son_el_mismo(self):
        """**Ni dos vacíos son iguales.** Un papel apuntado sin fichero no tiene huella, y decir que dos
        papeles sin fichero son el mismo sería inventarse un duplicado que impediría apuntar dos contratos
        distintos que no se han escaneado."""
        assert not bandeja.es_el_mismo_papel(None, None)
        assert not bandeja.es_el_mismo_papel("", "")
        assert not bandeja.es_el_mismo_papel("", None)
        assert not bandeja.es_el_mismo_papel(None, "a" * 64)

    def test_la_misma_huella_si_es_el_mismo_papel(self):
        assert bandeja.es_el_mismo_papel("a" * 64, "a" * 64)


# ==========================================================================
# 4. El mismo papel no entra dos veces
# ==========================================================================


class TestElMismoPapelNoEntraDosVeces:
    def _papel(self, huella="a" * 64, **cambios):
        return {
            "id": 1,
            "titulo": "La factura del abono",
            "huella": huella,
            "estado": bandeja.CLASIFICADO,
            "creado_en": dt.datetime(2026, 10, 3, 9, 0),
            **cambios,
        }

    def test_si_no_habia_ninguno_no_es_duplicado(self):
        decision = bandeja.decision_sobre_el_duplicado("b" * 64, papeles=[self._papel()])
        assert decision["duplicado"] is False
        assert decision["ya_estaba"] is None
        assert decision["donde"] is None

    def test_el_mismo_papel_se_detecta_y_se_dice_cual_era(self):
        """**La mitad del ticket:** el duplicado se dice **antes** de apuntarlo, y con el que ya estaba, que
        es lo que permite decidir sin buscar entre los papeles."""
        decision = bandeja.decision_sobre_el_duplicado("a" * 64, papeles=[self._papel()])
        assert decision["duplicado"] is True
        assert decision["donde"] == "la_bandeja"
        assert decision["ya_estaba"]["id"] == 1
        assert decision["ya_estaba"]["titulo"] == "La factura del abono"

    def test_un_papel_sin_huella_no_hace_que_todo_sea_duplicado(self):
        decision = bandeja.decision_sobre_el_duplicado("a" * 64, papeles=[self._papel(huella=None)])
        assert decision["duplicado"] is False

    def test_y_si_el_mismo_fichero_ya_esta_en_una_factura_de_compra(self):
        """El mismo papel puede haber entrado por la puerta de las facturas, que guarda su huella desde
        que se construyó el lector."""
        decision = bandeja.decision_sobre_el_duplicado(
            "c" * 64,
            papeles=[],
            facturas=[{"id": 7, "titulo": "Ferretería del Páramo", "huella": "c" * 64}],
        )
        assert decision["duplicado"] is True
        assert decision["donde"] == "una_factura_de_compra"
        assert decision["ya_estaba"]["id"] == 7

    def test_sin_huella_no_se_mira_nada(self):
        """Un fichero sin huella (que no puede pasar por la puerta de subida) no se compara con nadie."""
        assert bandeja.decision_sobre_el_duplicado(None, papeles=[self._papel()])["duplicado"] is False
        assert bandeja.decision_sobre_el_duplicado("", papeles=[self._papel()])["duplicado"] is False


# ==========================================================================
# 5. Lo leído es una propuesta, no un dato
# ==========================================================================


def _una_factura_leida(**cambios) -> facturas.FacturaLeida:
    """Lo que devuelve el lector de facturas, con números de verdad (los del caso A03 del contrato)."""
    leida = facturas.FacturaLeida(
        proveedor="Ferretería del Páramo",
        proveedor_nif="B12345678",
        numero_factura="2026/0042",
        fecha=dt.date(2026, 10, 1),
        base_imponible=810.0,
        cuota_iva=170.1,
        tipo_iva_pct=21.0,
        total=980.1,
        como_se_leyo="pdf",
        idioma_del_lector="spa",
    )
    leida.lineas = [
        facturas.LineaLeida(
            descripcion="Gasóleo agrícola",
            cantidad=300.0,
            unidad="L",
            precio_unitario=1.2,
            importe=360.0,
            cuadra=True,
        ),
        facturas.LineaLeida(
            descripcion="Abono NPK 15-15-15",
            cantidad=500.0,
            unidad="kg",
            precio_unitario=0.9,
            importe=450.0,
            cuadra=True,
        ),
    ]
    for clave, valor in cambios.items():
        setattr(leida, clave, valor)
    return leida


class TestLoLeidoEsUnaPropuesta:
    def test_los_importes_van_en_texto_decimal_y_no_en_coma_flotante(self):
        """El dinero viaja como texto en todo el programa, y una propuesta no es la excepción: si un
        importe acabara guardado como número de coma flotante, la cuenta del agricultor y la del programa
        dejarían de cuadrar por céntimos."""
        propuesta = bandeja.propuesta_de_factura(_una_factura_leida())
        assert propuesta["campos"]["total"] == "980.10"
        assert propuesta["campos"]["base_imponible"] == "810.00"
        assert propuesta["campos"]["fecha"] == "2026-10-01"
        assert propuesta["lineas"][0]["importe"] == "360.00"
        for valor in propuesta["campos"].values():
            assert not isinstance(valor, float), "un importe ha viajado como número de coma flotante"

    def test_un_importe_que_no_se_ha_leido_es_nulo_y_no_cero(self):
        """Un cero diría que la factura pone cero euros."""
        propuesta = bandeja.propuesta_de_factura(_una_factura_leida(cuota_iva=None, total=None))
        assert propuesta["campos"]["cuota_iva"] is None
        assert propuesta["campos"]["total"] is None
        assert propuesta["campos"]["base_imponible"] == "810.00"

    def test_de_cada_linea_se_dice_lo_unico_que_se_puede_comprobar(self):
        """**La cuenta cuadra** es aritmética, no una opinión: se puede decir sin corpus. Lo que no se dice
        es ninguna medida de la calidad de la lectura."""
        propuesta = bandeja.propuesta_de_factura(_una_factura_leida())
        assert propuesta["lineas"][0]["la_cuenta_cuadra"] is True
        assert propuesta["lineas"][1]["la_cuenta_cuadra"] is True
        # Y una línea cuya cuenta no cuadra lo dice, sin decir nada más de ella.
        torcida = bandeja.propuesta_de_factura(
            _una_factura_leida(
                lineas=[
                    facturas.LineaLeida(
                        descripcion="Algo que no cuadra",
                        cantidad=10.0,
                        unidad="kg",
                        precio_unitario=2.0,
                        importe=99.0,
                        cuadra=False,
                    )
                ]
            )
        )
        assert torcida["lineas"][0]["la_cuenta_cuadra"] is False
        assert propuesta["cuadra_el_total"] is True
        assert propuesta["suman_las_lineas"] is True

    def test_la_propuesta_dice_de_que_es_y_como_se_leyo(self):
        propuesta = bandeja.propuesta_de_factura(_una_factura_leida(), leido_en=dt.datetime(2026, 10, 6, 9))
        assert propuesta["clase"] == "factura"
        assert propuesta["como_se_leyo"] == "pdf"
        assert propuesta["leido_en"] == "2026-10-06T09:00:00"

    def test_los_avisos_del_lector_se_conservan(self):
        propuesta = bandeja.propuesta_de_factura(_una_factura_leida(avisos=["No he encontrado el NIF."]))
        assert propuesta["avisos"] == ["No he encontrado el NIF."]

    def test_una_propuesta_de_la_que_no_se_sabe_nada_lo_dice_con_su_motivo(self):
        propuesta = bandeja.propuesta_sin_leer("T08_este_papel_no_lo_se_leer")
        assert propuesta["clase"] == "ninguna"
        assert propuesta["avisos"] == ["T08_este_papel_no_lo_se_leer"]
        assert not bandeja.tiene_algo(propuesta)
        assert propuesta["lineas"] == []

    def test_solo_se_leen_los_papeles_que_tienen_lector(self):
        """Un contrato no se lee, y decir «no he podido» cuando no se intenta sería mentir por omisión."""
        assert bandeja.se_puede_leer("factura")
        assert bandeja.se_puede_leer("ticket")
        for tipo in ("contrato", "albaran", "inspeccion", "analitica", "otros", "albaran_sigfito"):
            assert not bandeja.se_puede_leer(tipo)

    def test_la_propuesta_va_y_vuelve_del_json(self):
        original = bandeja.propuesta_de_factura(_una_factura_leida())
        guardado = bandeja.a_json(original)
        assert isinstance(guardado, str)
        assert bandeja.de_json(guardado) == original

    def test_una_propuesta_que_no_se_puede_leer_es_no_lo_se_y_no_un_fallo(self):
        """La columna es texto: puede acabar con cualquier cosa dentro (una migración a medias, un fichero
        tocado a mano) y eso no puede tumbar la ficha del papel con un error del servidor."""
        assert bandeja.de_json("esto no es json") is None
        assert bandeja.de_json("[1, 2, 3]") is None
        assert bandeja.de_json(None) is None
        assert bandeja.de_json("") is None
        assert bandeja.a_json(None) is None

    def test_solo_se_enseñan_los_campos_de_la_cabecera(self):
        """Lo que se enseña y lo que se puede aceptar son **la misma lista**: si la lectura trajera un campo
        de más, no llegaría a la pantalla como si fuera aceptable."""
        propuesta = bandeja.propuesta_de_factura(_una_factura_leida())
        propuesta["campos"]["lo_que_sea"] = "algo"
        campos = bandeja.campos_de_la_propuesta(propuesta)
        assert "lo_que_sea" not in campos
        assert set(campos) <= set(bandeja.CAMPOS_DE_LA_CABECERA)

    def test_los_importes_de_una_propuesta_se_pueden_escribir(self):
        """El formateo del dinero es de `dinero.formatea`, y para eso hay que volver a `Decimal`."""
        importes = bandeja.importes_de_una_propuesta(bandeja.propuesta_de_factura(_una_factura_leida()))
        assert dinero.formatea(importes["total"]) == "980,10 €"
        assert importes["cuota_iva"] == Decimal("170.10")


class TestNoSeMideLaCalidadDeLaLectura:
    """**La regla que no se puede romper porque el T07 está bloqueado.**

    No hay corpus de facturas de verdad para medir la precisión del lector, así que el programa **no puede
    decir** que una lectura esté bien. Aquí se comprueba lo que no puede haber, y hay una prueba en la
    pantalla (`tests_js/bandeja.test.js`) que comprueba lo mismo por el otro lado: que no salga ni un
    porcentaje ni la palabra «confianza» en el HTML.
    """

    PROHIBIDAS = (
        "confianza",
        "porcentaje",
        "precision",
        "precisión",
        "acierto",
        "fiabilidad",
        "correctamente",
        "seguridad_de_la_lectura",
    )

    def _todas_las_claves(self, valor, encontradas: list[str]) -> list[str]:
        """Todas las claves de una estructura anidada, a cualquier profundidad."""
        if isinstance(valor, dict):
            for clave, dato in valor.items():
                encontradas.append(str(clave))
                self._todas_las_claves(dato, encontradas)
        elif isinstance(valor, list):
            for dato in valor:
                self._todas_las_claves(dato, encontradas)
        return encontradas

    def test_la_propuesta_no_lleva_ninguna_medida_de_la_calidad(self):
        propuesta = bandeja.propuesta_de_factura(_una_factura_leida())
        claves = self._todas_las_claves(propuesta, [])
        for prohibida in self.PROHIBIDAS:
            assert not any(prohibida in clave.lower() for clave in claves), (
                f"la propuesta lleva «{prohibida}»: sin corpus no se puede afirmar eso de una lectura"
            )

    def test_y_no_lleva_ningun_numero_entre_cero_y_cien(self):
        """Un porcentaje se cuela como un número suelto: se recorren los valores y se busca cualquier
        número que parezca una puntuación (entre 0 y 100 con decimales)."""
        propuesta = bandeja.propuesta_de_factura(_una_factura_leida())

        def numeros(valor, encontrados: list) -> list:
            if isinstance(valor, dict):
                for dato in valor.values():
                    numeros(dato, encontrados)
            elif isinstance(valor, list):
                for dato in valor:
                    numeros(dato, encontrados)
            elif isinstance(valor, (int, float)) and not isinstance(valor, bool):
                encontrados.append(valor)
            return encontrados

        # Lo único que hay son las dos cuentas (cuadra o no) y los conteos de líneas, y los conteos son
        # enteros pequeños que no dicen nada de la calidad (cuántas líneas hay, cuántas cuadran).
        assert numeros(propuesta, []) == []

    def test_la_pantalla_lleva_la_frase_que_dice_que_no_se_puede_medir(self):
        """Y no basta con no decir que está bien: hay que decir que no se sabe."""
        assert bandeja  # la bandeja no inventa nada…
        informe = INFORME.read_text(encoding="utf-8")
        assert '"no_se_mide_la_lectura"' in informe, (
            "el informe no lleva la frase que dice que la lectura no se puede medir"
        )
        assert "no dice si esta lectura está bien" in informe


# ==========================================================================
# 6. Lo que el agricultor acepta
# ==========================================================================


class TestLoQueAceptaElAgricultor:
    def test_los_importes_se_aceptan_como_se_escriben_aqui(self):
        aceptados = bandeja.campos_aceptados({"total": "980,10", "base_imponible": "980.10"})
        assert aceptados["total"] == "980.10"
        assert aceptados["base_imponible"] == "980.10"

    def test_un_campo_en_blanco_es_no_lo_se_y_no_dejalo_como_estaba(self):
        """**Es la mitad de la regla.** Si el agricultor borra un importe porque el papel no lo trae, el
        papel no puede quedarse con el que el programa había leído."""
        aceptados = bandeja.campos_aceptados({"total": "  ", "proveedor": ""})
        assert aceptados["total"] is None
        assert aceptados["proveedor"] is None
        assert "total" in aceptados

    def test_un_importe_que_no_se_entiende_se_dice(self):
        with pytest.raises(bandeja.DatoQueNoVale) as fallo:
            bandeja.campos_aceptados({"total": "como unos mil euros"})
        assert fallo.value.clave == "T08_ese_importe_no_se_entiende"

    def test_una_fecha_se_acepta_en_los_dos_formatos(self):
        assert bandeja.fecha_escrita("2026-10-01") == "2026-10-01"
        assert bandeja.fecha_escrita("01/10/2026") == "2026-10-01"
        assert bandeja.fecha_escrita("1-10-26") == "2026-10-01"
        assert bandeja.fecha_escrita("") is None
        assert bandeja.fecha_escrita(None) is None

    def test_una_fecha_que_no_existe_o_no_se_entiende_se_dice(self):
        with pytest.raises(bandeja.DatoQueNoVale) as inexistente:
            bandeja.fecha_escrita("31/02/2026")
        assert inexistente.value.clave == "T08_esa_fecha_no_existe"
        with pytest.raises(bandeja.DatoQueNoVale) as rara:
            bandeja.fecha_escrita("el martes")
        assert rara.value.clave == "T08_esa_fecha_no_se_entiende"

    def test_confirmar_sin_haber_aceptado_nada_no_es_una_decision(self):
        """Un conjunto con todo en blanco es alguien que ha abierto la pantalla y la ha dejado."""
        assert not bandeja.hay_algo_aceptado(bandeja.campos_aceptados({}))
        assert not bandeja.hay_algo_aceptado(bandeja.campos_aceptados({"total": ""}))
        assert bandeja.hay_algo_aceptado(bandeja.campos_aceptados({"total": "980,10"}))

    def test_de_lo_aceptado_solo_pasan_al_papel_su_quien_y_su_fecha(self):
        """El papel tiene cuatro campos propios y aquí se tocan dos. El título lo puso el agricultor y las
        notas son suyas: escribir ahí lo que el programa ha leído sería meter texto suyo sin que lo haya
        escrito."""
        for_el_papel = bandeja.para_el_papel(
            bandeja.campos_aceptados(
                {"proveedor": "Ferretería del Páramo", "fecha": "01/10/2026", "total": "980,10"}
            )
        )
        assert for_el_papel == {"quien": "Ferretería del Páramo", "fecha": dt.date(2026, 10, 1)}
        assert "titulo" not in for_el_papel
        assert "notas" not in for_el_papel
        assert "total" not in for_el_papel

    def test_sin_proveedor_ni_fecha_el_papel_se_queda_sin_ellos(self):
        assert bandeja.para_el_papel(bandeja.campos_aceptados({"total": "980,10"})) == {
            "quien": None,
            "fecha": None,
        }


class TestNoSeConfirmaSinRevisar:
    """**Las reglas del ticket, en las funciones que las deciden.**

    El servidor no deja confirmar sin haber revisado (contesta 409) y la pantalla no pinta el botón, porque
    el servidor le dice que no se puede. Aquí se comprueba la decisión pura, que es la que sostiene las dos.
    """

    def test_recien_subido_no_se_confirma(self):
        assert not bandeja.se_puede_confirmar(
            bandeja.RECIEN_SUBIDO, hay_algo_aceptado=True
        )

    def test_clasificado_no_se_confirma(self):
        """Un papel clasificado y leído pero **sin revisar** no se confirma: leer no es revisar."""
        assert not bandeja.se_puede_confirmar(bandeja.CLASIFICADO, hay_algo_aceptado=True)

    def test_revisado_pero_sin_nada_aceptado_tampoco(self):
        assert not bandeja.se_puede_confirmar(bandeja.PROPUESTA_REVISADA, hay_algo_aceptado=False)

    def test_revisado_y_con_algo_aceptado_si(self):
        assert bandeja.se_puede_confirmar(bandeja.PROPUESTA_REVISADA, hay_algo_aceptado=True)

    def test_lo_confirmado_no_se_vuelve_a_confirmar(self):
        assert not bandeja.se_puede_confirmar(bandeja.CONFIRMADO, hay_algo_aceptado=True)

    def test_la_lectura_se_descarta_solo_si_hay_lectura_y_nada_aceptado(self):
        assert bandeja.se_puede_descartar_la_propuesta(hay_propuesta=True, hay_algo_aceptado=False)
        assert not bandeja.se_puede_descartar_la_propuesta(hay_propuesta=False, hay_algo_aceptado=False)
        # Descartar algo que ya se aceptó sería borrar una decisión del agricultor sin decírselo.
        assert not bandeja.se_puede_descartar_la_propuesta(hay_propuesta=True, hay_algo_aceptado=True)

    def test_un_importe_que_no_consta_no_es_cero(self):
        """La regla del programa entera, aquí en su forma más pequeña: lo que no se sabe es nulo."""
        aceptados = bandeja.campos_aceptados({"total": ""})
        assert aceptados["total"] is None
        assert not dinero.es_cero(bandeja.importes_de_una_propuesta({"campos": aceptados})["total"])
        assert dinero.formatea(bandeja.importes_de_una_propuesta({"campos": aceptados})["total"]) == ""


# ==========================================================================
# 7. Enlazar: con lo que ya existe
# ==========================================================================


class TestEnlazarNoCreaNada:
    def test_las_clases_son_las_del_encargo_y_la_inspeccion(self):
        """Las cinco que pide el encargo (compra, gasto, venta, máquina y trabajo) más la inspección, que
        es el hueco que dejó el T14: `InspeccionDeMaquina.documento_id` ya apunta a un papel."""
        for clase in ("compra", "gasto", "venta", "maquina", "trabajo"):
            assert clase in bandeja.CLASES_DE_VINCULO
        assert bandeja.INSPECCION in bandeja.CLASES_DE_VINCULO
        assert len(bandeja.CLASES_DE_VINCULO) == len(set(bandeja.CLASES_DE_VINCULO))

    def test_una_clase_inventada_no_vale(self):
        assert not bandeja.es_una_clase_de_vinculo("lo_que_sea")
        assert bandeja.clave_de_la_clase("lo_que_sea") == "clase_desconocida"

    def test_a_un_certificado_de_inspeccion_se_le_sugiere_su_inspeccion(self):
        assert bandeja.clases_que_se_sugieren("inspeccion")[0] == bandeja.INSPECCION

    def test_a_una_factura_se_le_sugiere_la_compra(self):
        assert bandeja.clases_que_se_sugieren("factura")[0] == bandeja.COMPRA

    def test_un_papel_del_que_no_se_sabe_nada_no_sugiere_nada(self):
        """Es una sugerencia de pantalla, no una regla: lo que no se sabe, no se pone delante."""
        assert bandeja.clases_que_se_sugieren("otros") == ()
        assert bandeja.clases_que_se_sugieren("inventado") == ()

    def test_todas_las_clases_son_de_la_lista(self):
        for tipo in bandeja.TIPOS_DE_PAPEL:
            for clase in bandeja.clases_que_se_sugieren(tipo):
                assert bandeja.es_una_clase_de_vinculo(clase)

    def test_el_mismo_enlace_no_se_apunta_dos_veces(self):
        vinculos = [
            {"clase": "gasto", "entidad_id": 12},
            {"clase": "maquina", "entidad_id": 4},
        ]
        assert bandeja.ya_esta_vinculado(vinculos, "gasto", 12)
        assert bandeja.ya_esta_vinculado(vinculos, "gasto", "12")
        assert not bandeja.ya_esta_vinculado(vinculos, "gasto", 13)
        assert not bandeja.ya_esta_vinculado(vinculos, "venta", 12)

    def test_un_papel_puede_ir_con_varias_cosas_a_la_vez(self):
        """Un vínculo quitado no está en la lista (se borra su fila y queda el rastro): volver a enlazar
        algo que se quitó es un enlace nuevo y se admite."""
        vinculos = [
            {"clase": "gasto", "entidad_id": 12},
            {"clase": "maquina", "entidad_id": 4},
            {"clase": "trabajo", "entidad_id": 9},
        ]
        assert bandeja.ya_esta_vinculado(vinculos, "maquina", 4)
        assert not bandeja.ya_esta_vinculado([], "maquina", 4)


# ==========================================================================
# 8. Las rectificativas dejan las dos
# ==========================================================================


class TestLasRectificativasDejanLasDos:
    def test_un_papel_no_se_rectifica_a_si_mismo(self):
        se_puede, motivo = bandeja.puede_rectificar_a(7, 7)
        assert not se_puede
        assert motivo == "T08_un_papel_no_se_rectifica_a_si_mismo"

    def test_sin_decir_a_que_papel_no_hay_nada_que_hacer(self):
        se_puede, motivo = bandeja.puede_rectificar_a(7, None)
        assert not se_puede
        assert motivo == "T08_dime_a_que_papel_rectifica"

    def test_rectificar_a_otro_si_se_puede(self):
        se_puede, motivo = bandeja.puede_rectificar_a(7, 3)
        assert se_puede
        assert motivo == ""

    def test_una_cadena_de_rectificativas_no_es_un_circulo(self):
        cadena = {7: 3, 9: 7}
        assert not bandeja.hay_ciclo(cadena, 11, 9)
        assert not bandeja.hay_ciclo({}, 11, 9)

    def test_el_circulo_se_ve_y_no_se_deja_cerrar(self):
        """A rectifica a B y B rectifica a A: las dos quedarían diciendo que corrigen a la que las
        corrige, y la pantalla no podría contar la historia."""
        cadena = {7: 3}
        assert bandeja.hay_ciclo(cadena, 3, 7)
        assert not bandeja.hay_ciclo(cadena, 5, 7)
        # Y con un papel que ya se rectifica a sí mismo (un dato tocado a mano), no se entra en bucle.
        assert bandeja.hay_ciclo({5: 5}, 6, 5) is False

    def test_una_cadena_larga_rota_no_deja_el_programa_dando_vueltas(self):
        """Cien saltos y se corta: una cadena más larga que eso no es una cadena de facturas."""
        cadena = {numero: numero - 1 for numero in range(200, 1, -1)}
        assert not bandeja.hay_ciclo(cadena, 999, 200)


# ==========================================================================
# 9. Los nombres y el buscador
# ==========================================================================


class TestLosNombresYElBuscador:
    def test_el_tamano_de_un_fichero_se_escribe_para_leerlo(self):
        assert bandeja.describe_el_tamano(None) == ""
        assert bandeja.describe_el_tamano(512) == "512 bytes"
        assert bandeja.describe_el_tamano(20480) == "20,0 KB"
        assert bandeja.describe_el_tamano(3 * 1024 * 1024) == "3,0 MB"

    def test_un_papel_sin_nombre_se_llama_como_su_fichero(self):
        assert bandeja.titulo_por_defecto("factura-abril.pdf", "factura") == "factura-abril"
        assert bandeja.titulo_por_defecto(None, "factura") == "Una factura"
        assert bandeja.titulo_por_defecto("", "inspeccion") == "Un certificado de inspección"
        assert bandeja.titulo_por_defecto("sin-extension", "otros") == "sin-extension"

    def test_el_buscador_encuentra_sin_acentos_ni_mayusculas(self):
        """«albaran» tiene que encontrar «Albarán»: es como busca la gente, y si no, el buscador parecería
        roto justo con las palabras del campo."""
        assert bandeja.se_parece_a_lo_que_se_busca("albaran", "Albarán de entrega")
        assert bandeja.se_parece_a_lo_que_se_busca("FERRETERIA", "Ferretería del Páramo")
        assert not bandeja.se_parece_a_lo_que_se_busca("pepito", "Ferretería del Páramo")

    def test_sin_nada_que_buscar_sale_todo(self):
        assert bandeja.se_parece_a_lo_que_se_busca("", "lo que sea")
        assert bandeja.se_parece_a_lo_que_se_busca(None, "lo que sea")

    def test_las_claves_del_estado_y_de_la_clase(self):
        assert bandeja.clave_del_estado(bandeja.CONFIRMADO) == "estado_confirmado"
        assert bandeja.clave_de_la_clase(bandeja.INSPECCION) == "clase_inspeccion"


# ==========================================================================
# 10. Lo que falta por integrar, y cómo se comprueba cuando esté
# ==========================================================================


class TestLoQueFaltaEstaDicho:
    def test_el_mapa_de_lo_que_falta_se_mira_de_verdad(self):
        """Un guardián que no encuentra nada no está comprobando nada.

        Esta prueba comprueba el **extractor**: hoy faltan las columnas nuevas y la tabla (nadie las ha
        integrado todavía), y tiene que verlo. Cuando el coordinador las integre, esta prueba seguirá
        pasando (dirá que no falta nada, y entonces el recorrido corre entero).
        """
        falta = _lo_que_falta_por_integrar()
        if falta:
            assert any("documentos_anexos" in uno for uno in falta) or any(
                "vinculos_de_documento" in uno for uno in falta
            )

    def test_lo_que_falta_esta_escrito_en_el_informe(self):
        """Y lo que falta, con su nombre exacto, tiene que estar en `docs/T08_BANDEJA.md`.

        Es lo que impide que un ticket se entregue diciendo «falta integrar» sin decir **qué**, y que lo
        que falta se olvide en cuanto pasa la ronda.
        """
        assert INFORME.is_file(), "falta el informe del ticket: docs/T08_BANDEJA.md"
        informe = INFORME.read_text(encoding="utf-8")
        for pieza in (
            "DocumentoAnexo.huella",
            "estado_revision",
            "propuesta_descartada",
            "datos_confirmados",
            "confirmado_por_usuario_id",
            "rectifica_a_id",
            "VinculoDeDocumento",
            "bandeja_api",
            "include_router",
        ):
            assert pieza in informe, f"el informe no dice que haga falta «{pieza}»"

    def test_los_bloques_del_informe_se_pueden_ejecutar(self):
        """**Los bloques tienen que ser código de verdad.** Los del informe se copian a mano a los ficheros
        compartidos, así que un error de sintaxis ahí dentro se descubre al pegar, no aquí. Se comprueban
        con el analizador de Python: el de las columnas va con sangría (va dentro de una clase) y el de la
        tabla y el de los esquemas son código suelto.
        """
        for marcador in ("modelos-columnas", "modelos-tabla", "esquemas", "catalogos", "textos-bandeja", "textos-mensajes"):
            codigo = textwrap.dedent(_el_bloque(marcador))
            ast.parse(codigo, filename=f"informe:{marcador}")

    def test_el_bloque_de_las_columnas_trae_las_nueve(self):
        """Las nueve columnas, cada una con su nombre exacto: si falta una, la prueba del recorrido fallará
        al integrarse y el motivo no se vería."""
        bloque = _el_bloque("modelos-columnas")
        for columna in COLUMNAS_DEL_PAPEL:
            assert f"{columna}:" in bloque, f"el bloque de las columnas no trae `{columna}`"

    def test_el_bloque_de_los_esquemas_trae_los_que_importa_el_router(self):
        bloque = _el_bloque("esquemas")
        for nombre in (
            "VinculoDeUnPapelSalida",
            "LaPropuestaSalida",
            "LoQueSeAceptoSalida",
            "PapelDeLaBandejaSalida",
            "LaBandejaSalida",
            "ElFicheroComprobadoSalida",
            "LosCandidatosSalida",
            "LoQueHaPasadoSalida",
        ):
            assert f"class {nombre}(" in bloque, f"el bloque de los esquemas no trae `{nombre}`"

    def test_el_router_no_le_falta_ninguna_puerta(self):
        """Las trece puertas, leídas del fichero del router: son las que el informe lista y las que
        `app.js` tiene que llamar."""
        codigo = ROUTER.read_text(encoding="utf-8")
        for puerta in (
            'router.get("/bandeja"',
            'router.post("/bandeja/comprobar"',
            'router.post(\n    "/bandeja/subir"',
            'router.get("/bandeja/candidatos"',
            'router.get("/bandeja/{documento_id}"',
            '"/bandeja/{documento_id}/clasificar"',
            '"/bandeja/{documento_id}/leer"',
            '"/bandeja/{documento_id}/revisar"',
            '"/bandeja/{documento_id}/descartar"',
            '"/bandeja/{documento_id}/confirmar"',
            '"/bandeja/{documento_id}/vincular"',
            '"/bandeja/{documento_id}/desvincular"',
            '"/bandeja/{documento_id}/rectificar"',
        ):
            assert puerta in codigo, f"el router no tiene la puerta {puerta}"

    def test_la_puerta_de_confirmar_no_acepta_campos(self):
        """**La decisión más importante del ticket, comprobada en el código.** Si `confirmar` aceptara
        campos, «confirmar sin que nadie lo haya mirado» volvería a ser posible con una llamada bien hecha.
        """
        codigo = ROUTER.read_text(encoding="utf-8")
        empieza = codigo.index('"/bandeja/{documento_id}/confirmar"')
        termina = codigo.index("-> LoQueHaPasadoSalida", empieza)
        firma = codigo[empieza:termina]
        cuerpo = codigo[termina : codigo.index("@router.post", termina)]
        assert "datos: dict" not in firma and "campos" not in firma, (
            "la puerta de confirmar recibe campos: los campos se aceptan en `revisar`, no aquí"
        )
        assert "campos_aceptados(" not in cuerpo and "datos.get(" not in cuerpo, (
            "la puerta de confirmar está aceptando campos, y eso es lo que el ticket prohíbe"
        )


# ==========================================================================
# 11. La pantalla: sus acciones, y lo que el coordinador tiene que atar
# ==========================================================================


class TestLasAccionesDeLaPantalla:
    """Lo que impide que la pantalla pinte un botón que no hace nada.

    El manejador de clics de `app.js` es **uno solo**: una acción que se pinte y nadie atienda es un botón
    que se pulsa y no pasa nada, y no salta ningún error. Hay un guardián en el programa
    (`tests/test_los_botones_hacen_algo.py`) que lo comprueba; estas pruebas son su otra mitad: **la lista
    de lo que hay que atar**, escrita en el informe, para que la integración no se deje ninguna.
    """

    def test_la_pantalla_pinta_acciones_y_no_son_pocas(self):
        assert len(_las_acciones_de_la_pantalla()) >= 15, "el extractor de acciones se ha roto"

    def test_ninguna_accion_va_puesta_por_variable(self):
        """El guardián lee las acciones del código: una puesta por variable no se puede leer. Esta pantalla
        es nueva, así que no está en la lista de los ficheros que sí pueden hacerlo."""
        codigo = PANTALLA.read_text(encoding="utf-8").replace("*/", "").replace("/*", "")
        dinamicas = re.findall(r"""\baccion=\$\{""", codigo)
        assert not dinamicas, "hay acciones puestas por variable en la bandeja"

    def test_toda_accion_que_pinta_la_pantalla_esta_en_el_informe(self):
        """**La lista entera, una por una.** El coordinador tiene que atar estas acciones en `app.js`, y
        para eso el informe las dice todas: la que no esté, es un botón que no hará nada."""
        informe = INFORME.read_text(encoding="utf-8")
        sin_decir = sorted(
            accion for accion in _las_acciones_de_la_pantalla() if f"`{accion}`" not in informe
        )
        assert sin_decir == [], (
            "hay acciones que la pantalla pinta y el informe no dice quien las atiende: "
            + ", ".join(sin_decir)
        )

    def test_lo_que_todavia_no_atiende_app_js_esta_dicho(self):
        """Y lo que falta por atar, con su nombre. El día que el coordinador integre el bloque de `app.js`,
        esta prueba lo dirá sola (la lista de pendientes se queda vacía)."""
        pintadas = _las_acciones_de_la_pantalla()
        atendidas = _las_acciones_que_atiende_app_js()
        faltan = {accion for accion in pintadas if accion not in atendidas}
        declaradas = _las_acciones_que_el_informe_declara_pendientes()
        assert faltan <= declaradas, (
            "estas acciones no las atiende `app.js` y el informe no las declara pendientes: "
            + ", ".join(sorted(faltan - declaradas))
        )
        assert declaradas <= pintadas, (
            "el informe declara pendientes acciones que la pantalla ya no pinta: "
            + ", ".join(sorted(declaradas - pintadas))
        )

    def test_las_acciones_que_ya_existian_no_se_duplican(self):
        """«VER TODOS LOS PAPELES» y «VOLVER» ya existían y las atiende el manejador de siempre: si la
        pantalla las pintara con otro nombre, habría dos maneras de hacer lo mismo."""
        pintadas = _las_acciones_de_la_pantalla()
        assert "papel-ver-todos" in pintadas
        assert "ir-inicio" in pintadas
        assert "banco-ver" not in pintadas


# ==========================================================================
# 12. El recorrido por la API (se salta mientras falte la integración)
# ==========================================================================


@sin_integrar
class TestElRecorridoPorLaApi:
    """El recorrido entero: subir → comprobar el duplicado → clasificar → leer → revisar → confirmar →
    enlazar → desvincular → rectificar.

    Se salta mientras falten las columnas, la tabla, los esquemas, los textos y los tipos, y el día que
    estén se ejecuta entero: es lo que comprueba lo que **no se puede comprobar sin base de datos** (que el
    duplicado no cree una segunda ficha, que confirmar no deje confirmar sin revisar, que enlazar no cree un
    gasto, que la huella y el fichero no cambien al confirmar, y que el papel de una finca no se vea desde
    otra).

    Las mismas comprobaciones se han pasado contra las columnas y la tabla propuestas, en un SQLite
    temporal, antes de entregar el ticket (está contado en `docs/T08_BANDEJA.md`, apartado 2.3). Aquí quedan
    para que se sigan comprobando solas.
    """

    FICHERO = b"%PDF-1.4 una factura de mentira\n"
    NOMBRE = "factura-del-gasoleo.pdf"
    OTRO_ES = ("corregida.pdf", b"%PDF-1.4 la factura corregida\n", "application/pdf")

    # --- ayudantes ---

    def _comprobar(self, cliente, cuenta, contenido=None, nombre=None):
        return cliente.post(
            "/api/bandeja/comprobar",
            headers=cuenta["cabeceras"],
            files={"fichero": (nombre or self.NOMBRE, contenido or self.FICHERO, "application/pdf")},
        )

    def _subir(self, cliente, cuenta, *, tipo="factura", fichero=None, **campos):
        nombre, contenido, tipo_del_fichero = fichero or (self.NOMBRE, self.FICHERO, "application/pdf")
        datos = dict(campos)
        if tipo:
            datos["tipo"] = tipo
        return cliente.post(
            "/api/bandeja/subir",
            headers=cuenta["cabeceras"],
            files={"fichero": (nombre, contenido, tipo_del_fichero)},
            data=datos,
        )

    def _campos(self, **cambios):
        campos = {
            "proveedor": "Ferretería del Páramo",
            "numero_factura": "2026/0042",
            "fecha": "01/10/2026",
            "base_imponible": "810,00",
            "cuota_iva": "170,10",
            "total": "980,10",
        }
        campos.update(cambios)
        return campos

    def _un_gasto(self, cliente, cuenta, campana, concepto="Gasóleo del tractor"):
        respuesta = cliente.post(
            "/api/gastos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-10-01",
                "concepto": concepto,
                "categoria": "gasoleo",
                "importe": "360.00",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        # La puerta del gasto contesta `{gasto, ya_estaba, avisos}`, que es la forma que tiene para poder
        # decir «este ya estaba» sin duplicarlo.
        return respuesta.json()["gasto"]

    def _una_maquina(self, cliente, cuenta):
        # Las tres respuestas que no tienen valor por defecto son las que nadie ha afirmado todavía
        # («es tuya», «está disponible»): se contestan, y una de las respuestas posibles es «no lo sé».
        respuesta = cliente.post(
            "/api/maquinaria",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "El pulverizador",
                "clase": "equipo_de_aplicacion",
                "propiedad": "propia",
                "disponibilidad": "disponible",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def _una_inspeccion(self, cliente, cuenta, maquina_id):
        respuesta = cliente.post(
            f"/api/maquinaria/{maquina_id}/inspecciones",
            headers=cuenta["cabeceras"],
            json={"tipo": "iteaf", "fecha": "2026-03-01", "resultado": "favorable"},
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    # --- la subida y el duplicado ---

    def test_subir_guarda_el_original_y_lo_deja_sin_revisar(self, cliente, cuenta):
        respuesta = self._subir(cliente, cuenta)
        assert respuesta.status_code == 201, respuesta.text
        papel = respuesta.json()["papel"]
        assert papel["tiene_fichero"] is True
        assert papel["huella"] and len(papel["huella"]) == 64
        assert papel["sin_revisar"] is True
        assert papel["estado"] == bandeja.CLASIFICADO
        assert papel["la_propuesta"] is None
        assert cliente.get("/api/bandeja", headers=cuenta["cabeceras"]).json()["cuantos"] == 1

    def test_sin_decir_de_que_es_nace_recien_subido(self, cliente, cuenta):
        respuesta = self._subir(cliente, cuenta, tipo=None)
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["papel"]["estado"] == bandeja.RECIEN_SUBIDO
        listado = cliente.get("/api/bandeja", headers=cuenta["cabeceras"]).json()
        assert listado["sin_decir_de_que_es"] == 1
        assert listado["papeles"][0]["etiqueta_estado"]

    def test_un_tipo_que_no_existe_se_rechaza_con_la_lista(self, cliente, cuenta):
        respuesta = self._subir(cliente, cuenta, tipo="lo_que_sea")
        assert respuesta.status_code == 422
        assert "inspeccion" in respuesta.json()["detail"]

    def test_comprobar_no_escribe_nada(self, cliente, cuenta):
        """**La puerta del duplicado no guarda nada**: es lo que permite decir «ya lo tienes» antes de que
        nada haya cambiado."""
        respuesta = self._comprobar(cliente, cuenta)
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["ya_estaba"] is False
        assert respuesta.json()["huella"]
        assert cliente.get("/api/bandeja", headers=cuenta["cabeceras"]).json()["cuantos"] == 0

    def test_subir_dos_veces_el_mismo_papel_no_crea_dos_fichas(self, cliente, cuenta):
        """**La regla del ticket, de punta a punta.**"""
        self._subir(cliente, cuenta)
        antes = self._comprobar(cliente, cuenta)
        assert antes.json()["ya_estaba"] is True
        assert antes.json()["el_que_ya_estaba"]["id"]
        otra = self._subir(cliente, cuenta)
        assert otra.status_code == 409
        assert "ya lo tienes" in otra.json()["detail"]
        assert cliente.get("/api/bandeja", headers=cuenta["cabeceras"]).json()["cuantos"] == 1

    def test_el_original_se_puede_descargar_tal_cual(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta).json()["papel"]
        descargado = cliente.get(
            f"/api/documentos/{papel['id']}/fichero", headers=cuenta["cabeceras"]
        )
        assert descargado.status_code == 200
        assert descargado.content == self.FICHERO

    def test_el_papel_se_archiva_en_la_carpeta_de_su_tipo(self, cliente, cuenta):
        """Una sugerencia, no una obligación: la carpeta se puede cambiar en «los papeles»."""
        papel = self._subir(cliente, cuenta).json()["papel"]
        assert papel["carpeta"] == "Facturas"

    # --- clasificar ---

    def test_se_puede_decir_de_que_es_y_sale_de_recien_subido(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta, tipo=None).json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/clasificar",
            headers=cuenta["cabeceras"],
            json={"tipo": "inspeccion"},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["papel"]["tipo"] == "inspeccion"
        assert respuesta.json()["papel"]["estado"] == bandeja.CLASIFICADO

    def test_clasificar_conserva_lo_aceptado_pero_pide_revisarlo_otra_vez(self, cliente, cuenta):
        """Cambiar de opinión sobre qué es un papel no puede costarle al agricultor lo que ya tenía. Lo que
        sí hace es **volver a ponerlo sin revisar**: si el papel es otra cosa de lo que se creía, lo que se
        había aceptado hay que mirarlo otra vez."""
        papel = self._subir(cliente, cuenta).json()["papel"]
        cliente.post(
            f"/api/bandeja/{papel['id']}/revisar",
            headers=cuenta["cabeceras"],
            json={"campos": self._campos()},
        )
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/clasificar",
            headers=cuenta["cabeceras"],
            json={"tipo": "ticket"},
        )
        suyo = respuesta.json()["papel"]
        assert suyo["lo_aceptado"] is not None, "clasificar ha borrado lo que el agricultor había aceptado"
        assert suyo["estado"] == bandeja.CLASIFICADO
        assert suyo["se_puede_confirmar"] is False
        # Y con una revisión nueva vuelve a poder confirmarse.
        otra_vez = cliente.post(
            f"/api/bandeja/{papel['id']}/revisar",
            headers=cuenta["cabeceras"],
            json={"campos": self._campos()},
        )
        assert otra_vez.json()["papel"]["se_puede_confirmar"] is True

    # --- leer ---

    def test_leer_guarda_la_propuesta_y_no_cambia_el_estado(self, cliente, cuenta):
        """**Leer no es revisar.**"""
        papel = self._subir(cliente, cuenta).json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/leer", headers=cuenta["cabeceras"], json={}
        )
        assert respuesta.status_code == 200, respuesta.text
        suyo = respuesta.json()["papel"]
        assert suyo["estado"] == bandeja.CLASIFICADO
        assert suyo["se_puede_confirmar"] is False
        assert suyo["la_propuesta"] is not None
        # La propuesta no ha tocado los campos del papel.
        assert suyo["quien"] is None
        assert suyo["fecha"] is None
        # Y de la lectura no se dice en ningún sitio que sea buena.
        texto = str(suyo["la_propuesta"]).lower()
        for prohibida in ("confianza", "porcentaje", "precisión", "precision", "%"):
            assert prohibida not in texto

    def test_de_un_papel_que_no_se_sabe_leer_se_dice(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta, tipo="contrato").json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/leer", headers=cuenta["cabeceras"], json={}
        )
        assert respuesta.status_code == 200, respuesta.text
        suyo = respuesta.json()["papel"]
        # La propuesta se guarda **con su motivo** (no hay lectura, pero se sabe por qué), así que al
        # volver a abrir el papel no aparece un hueco sin explicación.
        assert suyo["la_propuesta"] is not None
        assert suyo["la_propuesta"]["lineas"] == []
        assert suyo["la_propuesta"]["campos"] == {}
        assert suyo["la_propuesta"]["avisos"], "no se dice por qué no hay lectura"
        assert suyo["se_puede_leer"] is False
        # Y se puede escribir a mano: revisar sin lectura vale.
        a_mano = cliente.post(
            f"/api/bandeja/{papel['id']}/revisar",
            headers=cuenta["cabeceras"],
            json={"campos": self._campos()},
        )
        assert a_mano.status_code == 200, a_mano.text
        assert a_mano.json()["papel"]["se_puede_confirmar"] is True

    # --- revisar ---

    def test_revisar_guarda_lo_aceptado_sin_confirmarlo(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta).json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/revisar",
            headers=cuenta["cabeceras"],
            json={"campos": self._campos()},
        )
        assert respuesta.status_code == 200, respuesta.text
        suyo = respuesta.json()["papel"]
        assert suyo["estado"] == bandeja.PROPUESTA_REVISADA
        assert suyo["lo_aceptado"]["campos"]["total"] == "980.10"
        assert suyo["lo_aceptado"]["textos"]["total"] == "980,10 €"
        assert suyo["se_puede_confirmar"] is True
        # Y el papel sigue como estaba: revisar no es confirmar.
        assert suyo["quien"] is None

    def test_revisar_sin_decir_nada_no_vale(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta).json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/revisar", headers=cuenta["cabeceras"], json={"campos": {}}
        )
        assert respuesta.status_code == 422

    def test_un_importe_que_no_se_entiende_se_dice(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta).json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/revisar",
            headers=cuenta["cabeceras"],
            json={"campos": self._campos(total="como mil euros")},
        )
        assert respuesta.status_code == 422
        assert "importe" in respuesta.json()["detail"]

    def test_dejar_un_campo_en_blanco_lo_deja_en_blanco(self, cliente, cuenta):
        """Un blanco es «no lo sé», no «déjalo como estaba»."""
        papel = self._subir(cliente, cuenta).json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/revisar",
            headers=cuenta["cabeceras"],
            json={"campos": self._campos(total="", cuota_iva="")},
        )
        suyo = respuesta.json()["papel"]
        assert suyo["lo_aceptado"]["campos"]["total"] is None
        assert suyo["lo_aceptado"]["textos"]["total"] == ""

    # --- descartar ---

    def test_descartar_la_lectura_no_la_borra(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta).json()["papel"]
        cliente.post(f"/api/bandeja/{papel['id']}/leer", headers=cuenta["cabeceras"], json={})
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/descartar",
            headers=cuenta["cabeceras"],
            json={"motivo": "no se lee nada"},
        )
        assert respuesta.status_code == 200, respuesta.text
        suyo = respuesta.json()["papel"]
        assert suyo["propuesta_descartada"] is True
        assert suyo["la_propuesta"] is not None, "descartar la lectura la ha borrado"
        assert suyo["se_puede_confirmar"] is False

    def test_descartar_sin_motivo_no_vale(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta).json()["papel"]
        cliente.post(f"/api/bandeja/{papel['id']}/leer", headers=cuenta["cabeceras"], json={})
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/descartar", headers=cuenta["cabeceras"], json={}
        )
        assert respuesta.status_code == 422

    # --- confirmar ---

    def test_no_se_puede_confirmar_sin_haber_revisado(self, cliente, cuenta):
        """**La regla, por la puerta del servidor.** Y la puerta no acepta campos: no hay forma de
        confirmar la propuesta sin que nadie la haya mirado."""
        papel = self._subir(cliente, cuenta).json()["papel"]
        cliente.post(f"/api/bandeja/{papel['id']}/leer", headers=cuenta["cabeceras"], json={})
        sin_revisar = cliente.post(
            f"/api/bandeja/{papel['id']}/confirmar",
            headers=cuenta["cabeceras"],
            json={"campos": self._campos()},
        )
        assert sin_revisar.status_code == 409
        assert "revisar" in sin_revisar.json()["detail"].lower()

    def test_confirmar_guarda_lo_aceptado_con_quien_y_cuando(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta).json()["papel"]
        cliente.post(
            f"/api/bandeja/{papel['id']}/revisar",
            headers=cuenta["cabeceras"],
            json={"campos": self._campos()},
        )
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/confirmar", headers=cuenta["cabeceras"], json={}
        )
        assert respuesta.status_code == 200, respuesta.text
        suyo = respuesta.json()["papel"]
        assert suyo["estado"] == bandeja.CONFIRMADO
        assert suyo["sin_revisar"] is False
        assert suyo["confirmado_en"]
        assert suyo["confirmado_por"] == "David"
        assert suyo["quien"] == "Ferretería del Páramo"
        assert suyo["fecha"] == "2026-10-01"

    def test_la_huella_y_el_fichero_no_cambian_al_confirmar(self, cliente, cuenta):
        """**La primera regla del ticket, comprobada.** El original es el original antes y después de
        confirmar: ni su huella, ni su nombre, ni su fichero."""
        papel = self._subir(cliente, cuenta).json()["papel"]
        huella = papel["huella"]
        cliente.post(
            f"/api/bandeja/{papel['id']}/revisar",
            headers=cuenta["cabeceras"],
            json={"campos": self._campos()},
        )
        confirmado = cliente.post(
            f"/api/bandeja/{papel['id']}/confirmar", headers=cuenta["cabeceras"], json={}
        ).json()["papel"]
        assert confirmado["huella"] == huella
        assert confirmado["nombre_del_fichero"] == papel["nombre_del_fichero"]
        assert confirmado["bytes"] == papel["bytes"]
        descargado = cliente.get(
            f"/api/documentos/{papel['id']}/fichero", headers=cuenta["cabeceras"]
        )
        assert descargado.content == self.FICHERO

    def test_un_papel_confirmado_sale_de_la_bandeja_y_se_ve_pidiendolo(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta).json()["papel"]
        cliente.post(
            f"/api/bandeja/{papel['id']}/revisar",
            headers=cuenta["cabeceras"],
            json={"campos": self._campos()},
        )
        cliente.post(f"/api/bandeja/{papel['id']}/confirmar", headers=cuenta["cabeceras"], json={})
        assert cliente.get("/api/bandeja", headers=cuenta["cabeceras"]).json()["cuantos"] == 0
        todos = cliente.get(
            "/api/bandeja", headers=cuenta["cabeceras"], params={"estado": "todos"}
        ).json()
        assert todos["cuantos"] == 1
        # Y sigue estando en «los papeles», que es donde vive un papel confirmado.
        assert cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()["cuantos"] == 1

    # --- la lista ---

    def test_la_lista_se_puede_filtrar_por_estado_y_por_texto(self, cliente, cuenta):
        self._subir(cliente, cuenta)
        self._subir(cliente, cuenta, fichero=self.OTRO_ES, titulo="La del taller")
        datos = cliente.get(
            "/api/bandeja", headers=cuenta["cabeceras"], params={"texto": "taller"}
        ).json()
        assert datos["cuantos"] == 1
        assert datos["papeles"][0]["titulo"] == "La del taller"
        # Y por estado: los que están sin revisar son los dos, y confirmados no hay ninguno.
        assert cliente.get("/api/bandeja", headers=cuenta["cabeceras"]).json()["cuantos"] == 2
        assert (
            cliente.get(
                "/api/bandeja", headers=cuenta["cabeceras"], params={"estado": "confirmado"}
            ).json()["cuantos"]
            == 0
        )
        assert (
            cliente.get(
                "/api/bandeja", headers=cuenta["cabeceras"], params={"estado": "lo_que_sea"}
            ).status_code
            == 422
        )

    def test_la_lista_lleva_las_palabras_y_los_tipos(self, cliente, cuenta):
        datos = cliente.get("/api/bandeja", headers=cuenta["cabeceras"]).json()
        assert datos["textos"]["titulo"]
        valores = {tipo["valor"] for tipo in datos["tipos"]}
        assert "inspeccion" in valores
        assert "contrato" in valores
        assert {clase["valor"] for clase in datos["clases"]} == set(bandeja.CLASES_DE_VINCULO)
        assert all(estado["etiqueta"] for estado in datos["estados"])

    # --- enlazar ---

    def test_enlazar_no_crea_el_gasto_ni_la_factura(self, cliente, cuenta, campana):
        """**La regla del ticket, por el lado del dinero:** enlazar une dos cosas que ya existen."""
        gasto = self._un_gasto(cliente, cuenta, campana)
        papel = self._subir(cliente, cuenta).json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/vincular",
            headers=cuenta["cabeceras"],
            json={"clase": "gasto", "entidad_id": gasto["id"]},
        )
        assert respuesta.status_code == 200, respuesta.text
        suyo = respuesta.json()["papel"]
        assert len(suyo["vinculos"]) == 1
        assert suyo["vinculos"][0]["clase"] == "gasto"
        assert "Gasóleo del tractor" in suyo["vinculos"][0]["que_es"]
        # Y sigue habiendo un gasto: el que había. Ni uno más.
        assert cliente.get("/api/gastos", headers=cuenta["cabeceras"]).json()["cuantos"] == 1

    def test_un_papel_puede_ir_con_varias_cosas_a_la_vez(self, cliente, cuenta, campana):
        gasto = self._un_gasto(cliente, cuenta, campana)
        maquina = self._una_maquina(cliente, cuenta)
        papel = self._subir(cliente, cuenta).json()["papel"]
        for clase, entidad in (("gasto", gasto["id"]), ("maquina", maquina["id"])):
            respuesta = cliente.post(
                f"/api/bandeja/{papel['id']}/vincular",
                headers=cuenta["cabeceras"],
                json={"clase": clase, "entidad_id": entidad},
            )
            assert respuesta.status_code == 200, respuesta.text
        assert len(respuesta.json()["papel"]["vinculos"]) == 2

    def test_el_mismo_enlace_dos_veces_se_dice(self, cliente, cuenta, campana):
        gasto = self._un_gasto(cliente, cuenta, campana)
        papel = self._subir(cliente, cuenta).json()["papel"]
        for _ in range(2):
            respuesta = cliente.post(
                f"/api/bandeja/{papel['id']}/vincular",
                headers=cuenta["cabeceras"],
                json={"clase": "gasto", "entidad_id": gasto["id"]},
            )
        assert respuesta.status_code == 409

    def test_enlazar_con_algo_que_no_existe_se_dice(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta).json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/vincular",
            headers=cuenta["cabeceras"],
            json={"clase": "gasto", "entidad_id": 9999},
        )
        assert respuesta.status_code == 404

    def test_una_clase_inventada_se_dice_con_la_lista(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta).json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/vincular",
            headers=cuenta["cabeceras"],
            json={"clase": "lo_que_sea", "entidad_id": 1},
        )
        assert respuesta.status_code == 422
        assert "gasto" in respuesta.json()["detail"]

    def test_desenlazar_quita_el_enlace_y_no_borra_lo_enlazado(self, cliente, cuenta, campana):
        gasto = self._un_gasto(cliente, cuenta, campana)
        papel = self._subir(cliente, cuenta).json()["papel"]
        cliente.post(
            f"/api/bandeja/{papel['id']}/vincular",
            headers=cuenta["cabeceras"],
            json={"clase": "gasto", "entidad_id": gasto["id"]},
        )
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/desvincular",
            headers=cuenta["cabeceras"],
            json={"clase": "gasto", "entidad_id": gasto["id"]},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["papel"]["vinculos"] == []
        assert cliente.get("/api/gastos", headers=cuenta["cabeceras"]).json()["cuantos"] == 1
        # Y quitar un enlace que no está se dice.
        assert (
            cliente.post(
                f"/api/bandeja/{papel['id']}/desvincular",
                headers=cuenta["cabeceras"],
                json={"clase": "gasto", "entidad_id": gasto["id"]},
            ).status_code
            == 404
        )

    def test_los_candidatos_son_cosas_que_ya_existen(self, cliente, cuenta, campana):
        self._un_gasto(cliente, cuenta, campana)
        respuesta = cliente.get(
            "/api/bandeja/candidatos", headers=cuenta["cabeceras"], params={"clase": "gasto"}
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["cuantos"] == 1
        assert "Gasóleo del tractor" in respuesta.json()["items"][0]["texto"]
        # Y el valor de la opción lleva **la clase y el identificador**, que es lo que hace que el
        # desplegable de la pantalla se baste solo para enlazar.
        assert respuesta.json()["items"][0]["valor"].startswith("gasto:")
        # Y se pueden buscar por texto.
        assert (
            cliente.get(
                "/api/bandeja/candidatos",
                headers=cuenta["cabeceras"],
                params={"clase": "gasto", "texto": "pepito"},
            ).json()["cuantos"]
            == 0
        )
        # Y una clase que no existe se dice con la lista.
        assert (
            cliente.get(
                "/api/bandeja/candidatos", headers=cuenta["cabeceras"], params={"clase": "x"}
            ).status_code
            == 422
        )

    # --- las inspecciones ---

    def test_un_certificado_de_inspeccion_se_enlaza_con_su_inspeccion(self, cliente, cuenta):
        """El hueco que dejó el T14: hasta hoy un certificado se apuntaba como «otros» porque el tipo no
        existía, y la inspección se quedaba sin su papel."""
        maquina = self._una_maquina(cliente, cuenta)
        inspeccion = self._una_inspeccion(cliente, cuenta, maquina["id"])
        papel = self._subir(cliente, cuenta, tipo="inspeccion").json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/vincular",
            headers=cuenta["cabeceras"],
            json={"clase": "inspeccion", "entidad_id": inspeccion["id"]},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["papel"]["vinculos"][0]["clase"] == "inspeccion"
        # Y la inspección se queda con su papel, que es el campo que enseña la ficha de la máquina.
        ficha = cliente.get(
            f"/api/maquinaria/{maquina['id']}", headers=cuenta["cabeceras"]
        ).json()
        suyas = [una for una in ficha["inspecciones"] if una["id"] == inspeccion["id"]]
        assert suyas and suyas[0]["documento_id"] == papel["id"]
        assert ficha["resumen"]["documentacion"]["con_papel"] == 1

    def test_una_inspeccion_que_ya_tiene_papel_no_se_pisa(self, cliente, cuenta):
        maquina = self._una_maquina(cliente, cuenta)
        inspeccion = self._una_inspeccion(cliente, cuenta, maquina["id"])
        primero = self._subir(cliente, cuenta, tipo="inspeccion").json()["papel"]
        segundo = self._subir(cliente, cuenta, tipo="inspeccion", fichero=self.OTRO_ES).json()["papel"]
        cliente.post(
            f"/api/bandeja/{primero['id']}/vincular",
            headers=cuenta["cabeceras"],
            json={"clase": "inspeccion", "entidad_id": inspeccion["id"]},
        )
        respuesta = cliente.post(
            f"/api/bandeja/{segundo['id']}/vincular",
            headers=cuenta["cabeceras"],
            json={"clase": "inspeccion", "entidad_id": inspeccion["id"]},
        )
        assert respuesta.status_code == 409
        # Y lo que sí se puede hacer: enlazarlo con la máquina, que es otra cosa.
        otra = cliente.post(
            f"/api/bandeja/{segundo['id']}/vincular",
            headers=cuenta["cabeceras"],
            json={"clase": "maquina", "entidad_id": maquina["id"]},
        )
        assert otra.status_code == 200

    # --- las rectificativas ---

    def test_una_rectificativa_deja_las_dos_y_se_dice_cual_corrige_a_cual(self, cliente, cuenta):
        primera = self._subir(cliente, cuenta).json()["papel"]
        segunda = self._subir(cliente, cuenta, fichero=self.OTRO_ES).json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{segunda['id']}/rectificar",
            headers=cuenta["cabeceras"],
            json={"rectifica_a_id": primera["id"]},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["papel"]["rectifica_a"]["id"] == primera["id"]
        # Y la primera sigue ahí, marcada y consultable.
        la_primera = cliente.get(
            f"/api/bandeja/{primera['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert la_primera["rectificada_por"][0]["id"] == segunda["id"]
        assert cliente.get("/api/bandeja", headers=cuenta["cabeceras"]).json()["cuantos"] == 2

    def test_un_papel_no_se_rectifica_a_si_mismo(self, cliente, cuenta):
        papel = self._subir(cliente, cuenta).json()["papel"]
        respuesta = cliente.post(
            f"/api/bandeja/{papel['id']}/rectificar",
            headers=cuenta["cabeceras"],
            json={"rectifica_a_id": papel["id"]},
        )
        assert respuesta.status_code == 422

    def test_una_cadena_de_rectificativas_se_puede_seguir(self, cliente, cuenta):
        primera = self._subir(cliente, cuenta).json()["papel"]
        segunda = self._subir(cliente, cuenta, fichero=self.OTRO_ES).json()["papel"]
        cliente.post(
            f"/api/bandeja/{segunda['id']}/rectificar",
            headers=cuenta["cabeceras"],
            json={"rectifica_a_id": primera["id"]},
        )
        # Y la segunda no puede rectificar a la primera «otra vez» cerrando el círculo.
        circulo = cliente.post(
            f"/api/bandeja/{primera['id']}/rectificar",
            headers=cuenta["cabeceras"],
            json={"rectifica_a_id": segunda["id"]},
        )
        assert circulo.status_code == 409

    # --- el aislamiento entre fincas y el borrado ---

    def test_un_papel_enlazado_no_se_puede_borrar_sin_mas(self, cliente, cuenta, campana):
        """**La consecuencia de que el vínculo sea una tabla con `documento_id`**: el borrado de papeles
        que ya existía (`documentos_api.borrar`, que cuenta las cosas que apuntan a un papel) lo mira solo,
        y contesta 409 en vez de dejar el vínculo apuntando a algo que ya no está. Lo que sí se puede
        siempre es **anular** el papel, que lo deja con su motivo y con su fichero."""
        gasto = self._un_gasto(cliente, cuenta, campana)
        papel = self._subir(cliente, cuenta).json()["papel"]
        cliente.post(
            f"/api/bandeja/{papel['id']}/vincular",
            headers=cuenta["cabeceras"],
            json={"clase": "gasto", "entidad_id": gasto["id"]},
        )
        respuesta = cliente.delete(
            f"/api/documentos/{papel['id']}", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 409, respuesta.text
        anulado = cliente.post(
            f"/api/documentos/{papel['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "era el papel de otro"},
        )
        assert anulado.status_code == 200, anulado.text
        # Y anulado no aparece en la bandeja, pero se puede pedir que salga.
        assert cliente.get("/api/bandeja", headers=cuenta["cabeceras"]).json()["cuantos"] == 0

    def test_el_papel_de_una_finca_no_se_ve_desde_otra(self, cliente, cuenta, crear_cuenta):
        papel = self._subir(cliente, cuenta).json()["papel"]
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")
        assert cliente.get("/api/bandeja", headers=otra["cabeceras"]).json()["cuantos"] == 0
        assert (
            cliente.get(f"/api/bandeja/{papel['id']}", headers=otra["cabeceras"]).status_code == 404
        )
        for puerta in ("confirmar", "leer", "vincular", "rectificar"):
            respuesta = cliente.post(
                f"/api/bandeja/{papel['id']}/{puerta}",
                headers=otra["cabeceras"],
                json={"clase": "gasto", "entidad_id": 1, "rectifica_a_id": 1},
            )
            assert respuesta.status_code == 404, f"la puerta {puerta} deja ver el papel de otra finca"
        assert (
            cliente.get(
                f"/api/documentos/{papel['id']}/fichero", headers=otra["cabeceras"]
            ).status_code
            == 404
        )

    def test_hace_falta_entrar(self, cliente):
        assert cliente.get("/api/bandeja").status_code == 401

# ==========================================================================
# De dónde sale el estado de revisión (05/10/2026, al integrar)
# ==========================================================================
#
# **Estas dos pruebas se añadieron al integrar el ticket, y por un defecto de verdad.** La columna
# `estado_revision` nacía con `default="recien_subido"`, y eso tenía dos consecuencias que no se ven en
# una prueba de la lógica pura:
#
#   1. **Los papeles que ya tenía el agricultor.** `asegurar_columnas` añade una columna nueva a una base
#      que ya existe **con el valor por defecto de Python** cuando lo hay: con ese `default`, los papeles
#      de antes de este ticket se quedarían «sin revisar» y la bandeja los enseñaría **todos de golpe** el
#      día de la actualización, pidiendo que se diga de qué son cuando el programa ya lo sabe.
#   2. **Un papel apuntado a mano en «los papeles»** no ha pasado por la bandeja: el agricultor ya dijo su
#      tipo y su carpeta al guardarlo, así que la bandeja le pediría otra vez lo que acaba de contestar.
#
# Se encontró en la comprobación del navegador: la ruta que guarda un papel en «los papeles» dejaba ese
# papel en la bandeja, y la bandeja decía de él «falta decir de qué es». Lo que se ata aquí es que el
# estado lo ponga **solo la puerta que sube a la bandeja**.
#
# Y lo que **no** se rompe por esto, que es la mitad que importa: la bandeja sigue diciendo de un papel
# sin estado lo que es —un papel ya clasificado— si alguien abre su ficha, porque
# `bandeja_api._como_sale_un_papel` lo trata como `CLASIFICADO`.


    def test_los_papeles_de_una_tierra_se_piden_por_la_tierra(self, cliente, cuenta, crear_parcela):
        """**CRM-06**: la ficha de una tierra tiene que poder enseñar SUS papeles.

        Y para eso hacia falta lo que se prueba aqui: que la bandeja se pueda pedir **por aquello con lo que
        un papel esta enlazado**. Antes solo filtraba por estado, tipo y texto, asi que para ver los papeles de
        una tierra habia que traerse la bandeja entera y cruzarla en la pantalla — lo contrario de lo que este
        proyecto hace.

        Y **de esta finca**: `clase`/`entidad_id` no son una clave ajena a proposito (apuntan a varias tablas),
        asi que quien comprueba que la entidad sea de la finca es esto. De ahi la segunda mitad de la prueba.
        """
        tierra = crear_parcela()
        subido = self._subir(cliente, cuenta, tipo="factura")
        assert subido.status_code in (200, 201), subido.text
        # **El papel va DENTRO de «papel»**, como en las demas pruebas de esta casa.
        papel = subido.json()["papel"]

        # Se enlaza el papel con la tierra — la clase nueva del CRM-06.
        enlace = cliente.post(
            f"/api/bandeja/{papel['id']}/vincular",
            headers=cuenta["cabeceras"],
            json={"clase": "tierra", "entidad_id": tierra["id"]},
        )
        assert enlace.status_code == 200, f"la tierra tiene que poder enlazarse: {enlace.text}"

        # Y pidiendo ESA tierra, sale.
        suyos = cliente.get(
            f"/api/bandeja?estado=todos&clase=tierra&entidad_id={tierra['id']}", headers=cuenta["cabeceras"]
        )
        assert suyos.status_code == 200, suyos.text
        ids = [cada_uno["id"] for cada_uno in suyos.json()["papeles"]]
        assert papel["id"] in ids, f"el papel de la tierra no sale al pedirla: {ids}"

        # **Y pidiendo OTRA tierra, no sale** — que es lo que hace util el filtro.
        otra = crear_parcela()
        ajenos = cliente.get(
            f"/api/bandeja?estado=todos&clase=tierra&entidad_id={otra['id']}", headers=cuenta["cabeceras"]
        )
        assert ajenos.status_code == 200, ajenos.text
        assert papel["id"] not in [cada_uno["id"] for cada_uno in ajenos.json()["papeles"]], (
            "el papel de una tierra no puede salir al pedir otra"
        )

        # Y **sin el filtro, sigue saliendo** — que es lo que el contrato prohibe romper.
        todos = cliente.get("/api/bandeja?estado=todos", headers=cuenta["cabeceras"])
        assert papel["id"] in [cada_uno["id"] for cada_uno in todos.json()["papeles"]]


class TestElEstadoDeRevisionLoPoneLaBandeja:
    def test_un_papel_guardado_a_mano_no_espera_en_la_bandeja(self, cliente, cuenta):
        """El que se apunta en «los papeles» **ya está clasificado**: no tiene nada que revisar."""
        creado = cliente.post(
            "/api/documentos",
            headers=cuenta["cabeceras"],
            json={"titulo": "Contrato de la finca del río", "tipo": "contrato"},
        )
        assert creado.status_code == 201, creado.text
        papel = creado.json()

        # Ni espera en la bandeja…
        bandeja_ahora = cliente.get("/api/bandeja", headers=cuenta["cabeceras"]).json()
        assert bandeja_ahora["cuantos"] == 0, (
            "un papel guardado a mano ha aparecido en la bandeja pidiendo que se diga de qué es: "
            f"{[uno['titulo'] for uno in bandeja_ahora['papeles']]}"
        )
        # …ni se queda sin estado: **sin estado**, que no es lo mismo que «recién subido».
        suyo = cliente.get(f"/api/bandeja/{papel['id']}", headers=cuenta["cabeceras"])
        assert suyo.status_code == 200, suyo.text
        assert suyo.json()["estado"] == bandeja.CLASIFICADO, (
            "un papel que no ha pasado por la bandeja sale como «recién subido»"
        )
        # Y se dice con la palabra del agricultor, no con la clave. **Lo que sí sale marcado como «sin
        # revisar» es el estado derivado** —de un papel que no ha pasado por la bandeja nadie ha dado el
        # visto bueno—, y eso es la verdad: lo que no se puede es confundirlo con «recién subido», que es
        # lo que pide que se diga de qué es.
        assert suyo.json()["etiqueta_estado"] == textos.BANDEJA["estado_clasificado"]

    def test_el_que_se_sube_a_la_bandeja_si_espera_y_dice_que_le_falta(self, cliente, cuenta):
        """Y el que llega a la bandeja, sí: eso es la bandeja. **El otro lado de lo mismo.**"""
        # **Sin decir de qué es**, que es como llega de verdad: una foto de un papel que el agricultor
        # acaba de hacer con el móvil. Un papel que se sube **con** su tipo ya viene clasificado (el
        # formulario de subida lo permite), así que el «recién subido» es este.
        subido = cliente.post(
            "/api/bandeja/subir",
            headers=cuenta["cabeceras"],
            files={"fichero": ("ticket.png", b"\x89PNG\r\n\x1a\n" + b"x" * 20, "image/png")},
        )
        assert subido.status_code == 201, subido.text

        bandeja_ahora = cliente.get("/api/bandeja", headers=cuenta["cabeceras"]).json()
        assert bandeja_ahora["cuantos"] == 1, "el papel subido no está en la bandeja"
        assert bandeja_ahora["papeles"][0]["estado"] == bandeja.RECIEN_SUBIDO
        assert bandeja_ahora["sin_decir_de_que_es"] == 1, (
            "la bandeja no dice que le falta saber de qué es el papel"
        )
        assert bandeja_ahora["papeles"][0]["sin_revisar"] is True
