"""Las pruebas del T20: los extractos de banco y la conciliación reversible.

Están escritas al revés de lo habitual: **primero la regla de negocio, y la prueba lleva su nombre**.
El ticket lo pide así porque son las reglas que no se pueden saltar, y una prueba llamada
`test_lo_que_esta_bien` no protege nada:

| Regla que no se puede saltar | Prueba que falla si se rompe |
|---|---|
| Nada de conexión bancaria, ni real ni simulada | `TestNoHayNingunaConexionBancaria` |
| Importar dos veces el mismo extracto no duplica | `TestImportarDosVecesNoDuplica` |
| Conciliar no crea un segundo gasto | `TestConciliarNoCreaNada` |
| Un traspaso entre cuentas propias no crea ingresos | `TestUnTraspasoPropioNoEsIngresoNiGasto` |
| Pagos parciales y agrupados, y deshacerlos deja todo como estaba | `TestPagosParcialesYAgrupados`, `TestDeshacerDejaTodoComoEstaba` |
| Un importe que no consta NO es cero, de punta a punta | `TestUnImporteQueNoConstaNoEsCero` |
| Toda conciliación es reversible y deja rastro | `TestElRastroDeUnaConciliacion` |
| Un extracto de una finca no se ve desde otra | `TestAislamientoEntreFincas` |

## Lo que se puede probar hoy y lo que no

La lectura del fichero, los duplicados, los traspasos y toda la cuenta de la conciliación son
**funciones puras**: se prueban aquí, con ficheros de ejemplo inventados, sin base de datos y sin
servidor. La parte que guarda (`app/routers/extractos_api.py`) necesita las tablas que el ticket
propone, y esas tablas las escribe el coordinador en `models.py`: mientras no estén, esas pruebas se
**saltan diciendo qué falta** en vez de quedarse en verde sin comprobar nada. Es la misma decisión
del resto del programa: se dice lo que no se ha podido comprobar.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
from decimal import Decimal

import pytest

from app import extractos, models, textos

DATOS = pathlib.Path(__file__).resolve().parent / "datos"

PRINCIPAL = DATOS / "extracto_de_ejemplo_cuenta_principal.csv"
AHORRO = DATOS / "extracto_de_ejemplo_cuenta_de_ahorro.csv"
DUDOSAS = DATOS / "extracto_de_ejemplo_fechas_dudosas.csv"
RARAS = DATOS / "extracto_de_ejemplo_con_filas_raras.csv"

CUENTA = "Cuenta principal"
OTRA_CUENTA = "Cuenta de ahorro"
LAS_DOS_PROPIAS = {CUENTA: True, OTRA_CUENTA: True}

FECHA_DE_LA_FACTURA = dt.date(2026, 6, 1)
FECHA_DEL_PAGO = dt.date(2026, 6, 15)


def _lee(ruta: pathlib.Path, *, cuenta: str = CUENTA, perfil=None, explotacion_id: int = 1):
    """Lee un fichero de ejemplo tal y como lo lee el servidor: de bytes a lectura previa."""
    return extractos.lee_extracto(
        extractos.lee_el_texto(ruta.read_bytes()),
        perfil,
        cuenta=cuenta,
        explotacion_id=explotacion_id,
    )


def _una_fila(
    *,
    fecha: dt.date | None = dt.date(2026, 6, 15),
    importe: str | None = "500.00",
    signo: str | None = extractos.ENTRA,
    concepto: str | None = "TRANSFERENCIA RECIBIDA EJEMPLO",
    referencia: str | None = None,
    saldo: str | None = None,
    cuenta: str = CUENTA,
    explotacion_id: int | None = 1,
) -> extractos.FilaDeExtracto:
    """Un movimiento suelto, para las pruebas que no necesitan un fichero entero.

    La clave de duplicado se calcula con la función del módulo, igual que al leer un fichero, para que
    una prueba no esté comprobando un objeto que el programa nunca fabricaría.
    """
    return extractos.FilaDeExtracto(
        numero_de_linea=1,
        fecha=fecha,
        concepto=concepto,
        importe=Decimal(importe) if importe is not None else None,
        signo=signo,
        saldo=Decimal(saldo) if saldo is not None else None,
        referencia=referencia,
        cuenta=cuenta,
        clave_de_duplicado=extractos._parte_de_la_clave(
            cuenta=cuenta,
            fecha=fecha,
            importe=Decimal(importe) if importe is not None else None,
            signo=signo,
            concepto=concepto,
            saldo=Decimal(saldo) if saldo is not None else None,
            referencia=referencia,
        )
        + "#1",
        explotacion_id=explotacion_id,
    )


def _una_factura(
    *,
    documento_id: int = 1,
    clase: str = extractos.FACTURA_EMITIDA,
    contraparte: str | None = "Cooperativa Agricola Ejemplo",
    referencia: str | None = None,
    fecha: dt.date | None = FECHA_DE_LA_FACTURA,
    importe: str | None = "1205.40",
    pendiente: str | None = "1205.40",
    explotacion_id: int | None = 1,
) -> extractos.DocumentoPorConciliar:
    return extractos.DocumentoPorConciliar(
        clase=clase,
        documento_id=documento_id,
        contraparte=contraparte,
        referencia=referencia,
        fecha=fecha,
        importe=Decimal(importe) if importe is not None else None,
        pendiente=Decimal(pendiente) if pendiente is not None else None,
        explotacion_id=explotacion_id,
    )


# ==========================================================================
# No hay ninguna conexión bancaria (la protección del encargo)
# ==========================================================================


class TestNoHayNingunaConexionBancaria:
    """El encargo lo prohíbe expresamente: nada de conexión bancaria, ni real ni simulada.

    Esta prueba lee **el código escrito para este ticket** y comprueba que no hay ni una llamada a
    internet, ni un cliente de HTTP, ni un sitio donde quepa una clave de banca. No es una prueba
    sobre el comportamiento: es una prueba sobre la promesa, y por eso mira el texto del programa.
    Una promesa que no se comprueba es una promesa que se rompe el día que alguien añade «una
    conexión de solo lectura, que no hace daño».
    """

    FICHEROS = ("app/extractos.py", "app/routers/extractos_api.py")

    # Todo lo que haría falta para hablar con un banco.
    #
    # **Son identificadores de código y direcciones, no palabras del texto.** «Contraseña» aparece en
    # los comentarios de este ticket, y aparece justo para decir que **no** se pide: lo que se busca
    # aquí es un `import` de red, una dirección, o un sitio donde quepa una credencial
    # (`api_key`, `client_secret`), no la palabra que explica la prohibición.
    PROHIBIDO = (
        "import requests",
        "import httpx",
        "import urllib",
        "from urllib",
        "import socket",
        "import aiohttp",
        "urlopen(",
        "psd2",
        "openbanking",
        "open_banking",
        "http://",
        "https://",
        "api_key",
        "client_secret",
        "access_token",
        "password",
    )

    def test_los_ficheros_existen_y_se_leen(self):
        raiz = pathlib.Path(__file__).resolve().parents[1]
        for nombre in self.FICHEROS:
            assert (raiz / nombre).is_file(), f"no encuentro {nombre}: ¿se ha movido?"

    def test_no_hay_ni_una_llamada_a_internet(self):
        raiz = pathlib.Path(__file__).resolve().parents[1]
        encontrado: dict[str, list[str]] = {}
        for nombre in self.FICHEROS:
            texto = (raiz / nombre).read_text(encoding="utf-8")
            for prohibido in self.PROHIBIDO:
                if prohibido in texto:
                    encontrado.setdefault(nombre, []).append(prohibido)
        assert not encontrado, (
            "en el código de los extractos hay algo que huele a conexión bancaria: "
            f"{encontrado}. El encargo lo prohíbe: **solo se lee un fichero que sube el agricultor**."
        )

    def test_la_promesa_esta_escrita_en_el_propio_modulo(self):
        """Y si alguien borra el porqué, esta prueba lo dice: el motivo tiene que estar en el código."""
        raiz = pathlib.Path(__file__).resolve().parents[1]
        texto = (raiz / "app" / "extractos.py").read_text(encoding="utf-8")
        assert "No hay ninguna conexión con ningún banco" in texto


# ==========================================================================
# Leer el fichero: por la etiqueta, y sin adivinar
# ==========================================================================


class TestLeerElExtracto:
    def test_lee_todas_las_lineas_del_extracto_de_ejemplo(self):
        lectura = _lee(PRINCIPAL)
        # Siete líneas de datos: seis movimientos con importe y una sin él.
        assert len(lectura.movimientos) == 7
        assert lectura.rechazadas == ()
        assert lectura.saldo_final == Decimal("3879.45")

    def test_la_primera_fila_de_datos_no_es_la_primera_del_fichero(self):
        """Un extracto empieza por el banco y la cuenta, no por la tabla."""
        lectura = _lee(PRINCIPAL)
        assert lectura.cuenta.banco == "Banco del Paramo, S.A."
        assert lectura.cuenta.ultimos_digitos == "5555"
        assert lectura.movimientos[0].numero_de_linea == 4

    def test_las_columnas_se_buscan_por_su_etiqueta_y_no_por_su_sitio(self):
        """Si el banco cambia dos columnas de sitio, la lectura tiene que ser la misma.

        Es la receta que este programa ya aplicó al cuaderno de la Junta: leer por la etiqueta de la
        cabecera y **nunca** por «la columna L», porque una plantilla cambia y la lectura por
        posición se rompe en silencio devolviendo el dato de al lado.
        """
        al_reves = (
            "Banco del Paramo, S.A.;Cuenta: ES00 9999 8888 7777 6666 5555\n"
            "Saldo;Importe;Referencia;Concepto;Fecha\n"
            "3.480,20;-320,00;R-1;ADEUDO SEGURO EJEMPLO;14/06/2026\n"
        )
        lectura = extractos.lee_extracto(al_reves, cuenta=CUENTA, explotacion_id=1)
        assert len(lectura.movimientos) == 1
        fila = lectura.movimientos[0]
        assert fila.fecha == dt.date(2026, 6, 14)
        assert fila.importe == Decimal("320.00")
        assert fila.signo == extractos.SALE
        assert fila.saldo == Decimal("3480.20")
        assert fila.concepto == "ADEUDO SEGURO EJEMPLO"

    def test_no_se_guarda_el_numero_de_cuenta_entero(self):
        """Lo que hace falta es reconocer la cuenta, no el número entero.

        Un extracto lleva el IBAN completo, y ese número no hace falta para cuadrar nada. Aquí se
        comprueba **en el resultado**, no en el código: si alguien lo metiera en un campo, esta prueba
        se pone roja.
        """
        lectura = _lee(PRINCIPAL)
        todo = json.dumps(
            {
                "cuenta": lectura.cuenta.__dict__,
                "movimientos": [f.__dict__ for f in lectura.movimientos],
                "columnas": dict(lectura.columnas),
                "csv": extractos.a_csv(lectura.movimientos),
            },
            default=str,
        )
        assert "ES00" not in todo
        assert "66665555" not in todo.replace(" ", "")
        assert "5555" in todo

    def test_una_linea_sin_cabeceras_no_se_lee_por_posicion(self):
        """Sin cabeceras no se sabe qué columna es cada cosa, y esto lo dice en vez de adivinar."""
        texto = "01/06/2026;ALGO;-320,00\n02/06/2026;OTRA COSA;1.205,40\n"
        lectura = extractos.lee_extracto(texto, cuenta=CUENTA)
        assert lectura.movimientos == ()
        assert [r.motivo for r in lectura.rechazadas] == [
            extractos.SIN_CABECERAS,
            extractos.SIN_CABECERAS,
        ]
        assert extractos.AVISO_SIN_CABECERAS in [a.codigo for a in lectura.avisos]

    def test_un_concepto_con_un_punto_y_coma_suelto_no_desplaza_el_importe(self):
        """Una casilla de más desplaza todo lo que va detrás: esa línea se rechaza, no se lee torcida."""
        texto = (
            "Fecha;Concepto;Importe;Saldo\n"
            "14/06/2026;PAGO DE EJEMPLO;CON;PUNTO Y COMA;-320,00;100,00\n"
        )
        lectura = extractos.lee_extracto(texto, cuenta=CUENTA)
        assert lectura.movimientos == ()
        assert [r.motivo for r in lectura.rechazadas] == [extractos.COLUMNAS_DE_MAS]

    def test_el_saldo_que_no_cuadra_se_dice(self):
        """La aritmética es la prueba de que la lectura está bien: `saldo de antes + importe = saldo`.

        La tercera línea trae un saldo que no encaja con las dos anteriores (900 − 50 son 850, no
        1.500), y eso es lo que destapa una lectura torcida: un concepto que se ha comido una casilla,
        un importe de la columna de al lado.
        """
        texto = (
            "Fecha;Concepto;Importe;Saldo\n"
            "14/06/2026;PAGO DE EJEMPLO;-320,00;1.000,00\n"
            "15/06/2026;OTRO PAGO DE EJEMPLO;-100,00;900,00\n"
            "16/06/2026;UN TERCER PAGO;-50,00;1.500,00\n"
        )
        lectura = extractos.lee_extracto(texto, cuenta=CUENTA)
        avisos = {a.codigo: a for a in lectura.avisos}
        assert extractos.AVISO_SALDO_NO_CUADRA in avisos
        # La cabecera es la línea 1, así que la tercera fila de datos es la línea 4.
        assert avisos[extractos.AVISO_SALDO_NO_CUADRA].lineas == (4,)

    def test_los_saldos_que_cuadran_no_dan_ningun_aviso(self):
        """Y la prueba de arriba no puede ser una que salte siempre."""
        texto = (
            "Fecha;Concepto;Importe;Saldo\n"
            "14/06/2026;PAGO DE EJEMPLO;-320,00;1.000,00\n"
            "15/06/2026;OTRO PAGO DE EJEMPLO;-100,00;900,00\n"
            "16/06/2026;UN TERCER PAGO;-50,00;850,00\n"
        )
        lectura = extractos.lee_extracto(texto, cuenta=CUENTA)
        assert extractos.AVISO_SALDO_NO_CUADRA not in [a.codigo for a in lectura.avisos]
        assert len(lectura.movimientos) == 3

    def test_un_movimiento_que_sale_tiene_su_importe_y_su_signo_o_ninguno_de_los_dos(self):
        """La invariante de una fila guardada, comprobada sobre todo lo que se ha leído aquí.

        Si el importe no consta no hay signo posible (no hay dinero), y si consta es porque el signo
        está decidido: una fila con importe y sin signo sería un movimiento del que no se sabe si
        suma o resta, y ese movimiento no se puede sumar ni conciliar.
        """
        for ruta in (PRINCIPAL, AHORRO, DUDOSAS, RARAS):
            for fila in _lee(ruta).movimientos:
                assert (fila.importe is None) == (fila.signo is None), fila
                if fila.signo is not None:
                    assert fila.signo in extractos.SIGNOS


class TestNoSeAdivina:
    """Los tres casos donde un programa «listo» se inventaría un dato. Aquí se rechaza la fila."""

    def test_una_fecha_que_se_puede_leer_de_dos_maneras_se_rechaza(self):
        """`03/04/2026` es el 3 de abril o el 4 de marzo, y elegir mueve un apunte de mes."""
        lectura = _lee(DUDOSAS)
        ambiguas = [r for r in lectura.rechazadas if r.motivo == extractos.FECHA_AMBIGUA]
        assert len(ambiguas) == 2
        assert "03/04/2026" in ambiguas[0].texto
        # Y la que no se puede leer mal (03/03/2026: da igual el orden) sí se lee.
        assert [f.fecha for f in lectura.movimientos] == [dt.date(2026, 3, 3)]

    def test_el_propio_fichero_demuestra_el_formato_de_la_fecha(self):
        """Un extracto trae un mes entero: en cuanto hay un día del 13 en adelante, no hay duda."""
        lectura = _lee(PRINCIPAL)
        assert lectura.perfil.formato_de_fecha == "d/m/Y"
        avisos = {a.codigo: a for a in lectura.avisos}
        assert extractos.AVISO_FORMATO_DE_FECHA_DEDUCIDO in avisos
        assert avisos[extractos.AVISO_FORMATO_DE_FECHA_DEDUCIDO].datos["formato"] == "d/m/Y"
        assert 6 in avisos[extractos.AVISO_FORMATO_DE_FECHA_DEDUCIDO].lineas

    def test_con_el_formato_dicho_por_el_agricultor_el_dia_3_de_abril_es_el_3_de_abril(self):
        perfil = extractos.PerfilDeFormato(
            formato_de_fecha="d/m/Y",
            columnas={"fecha": "Fecha", "concepto": "Concepto", "importe": "Importe"},
        )
        texto = "Fecha;Concepto;Importe\n03/04/2026;PAGO DE EJEMPLO;-320,00\n"
        lectura = extractos.lee_extracto(texto, perfil, cuenta=CUENTA)
        assert [f.fecha for f in lectura.movimientos] == [dt.date(2026, 4, 3)]

    def test_un_importe_sin_signo_y_sin_prueba_en_el_fichero_se_rechaza(self):
        """Sin saldo que lo demuestre, un `40,00` sin signo puede ser un cobro o un pago."""
        texto = "Fecha;Concepto;Importe\n14/06/2026;PAGO DE EJEMPLO;40,00\n"
        lectura = extractos.lee_extracto(texto, cuenta=CUENTA)
        assert lectura.movimientos == ()
        assert [r.motivo for r in lectura.rechazadas] == [extractos.SIN_SIGNO]
        assert lectura.rechazadas[0].lo_que_dice == "40,00"

    def test_el_saldo_del_fichero_demuestra_si_un_importe_sin_signo_entra(self):
        """Y cuando el fichero lo demuestra, se lee: 1.000,00 + 25,00 = 1.025,00, no 975,00."""
        texto = (
            "Fecha;Concepto;Importe;Saldo\n"
            "14/06/2026;COBRO DE EJEMPLO SIN SIGNO;25,00;1.025,00\n"
        )
        # La primera línea no tiene saldo anterior, así que aquí no hay prueba ninguna.
        assert extractos.lee_extracto(texto, cuenta=CUENTA).movimientos == ()

        texto_con_dos = (
            "Fecha;Concepto;Importe;Saldo\n"
            "13/06/2026;PAGO DE EJEMPLO CON SIGNO;-25,00;1.000,00\n"
            "14/06/2026;COBRO DE EJEMPLO SIN SIGNO;25,00;1.025,00\n"
        )
        lectura = extractos.lee_extracto(texto_con_dos, cuenta=CUENTA)
        assert [f.signo for f in lectura.movimientos] == [extractos.SALE, extractos.ENTRA]
        assert extractos.AVISO_SIGNO_DEDUCIDO in [a.codigo for a in lectura.avisos]

    def test_con_la_convencion_dicha_por_el_agricultor_se_lee(self):
        perfil = extractos.PerfilDeFormato(
            decimal=",",
            sin_signo_quiere_decir=extractos.ENTRA,
            estilo_del_signo=extractos.SIGNO_EN_EL_IMPORTE,
            columnas={"fecha": "Fecha", "concepto": "Concepto", "importe": "Importe"},
        )
        texto = "Fecha;Concepto;Importe\n14/06/2026;COBRO DE EJEMPLO;40,00\n"
        lectura = extractos.lee_extracto(texto, perfil, cuenta=CUENTA)
        assert [(f.signo, f.importe) for f in lectura.movimientos] == [
            (extractos.ENTRA, Decimal("40.00"))
        ]

    def test_una_fila_con_debe_y_haber_no_se_elige(self):
        texto = (
            "Fecha;Concepto;Debe;Haber;Saldo\n"
            "14/06/2026;MOVIMIENTO RARO DE EJEMPLO;100,00;200,00;1.000,00\n"
        )
        lectura = extractos.lee_extracto(texto, cuenta=CUENTA)
        assert lectura.movimientos == ()
        assert [r.motivo for r in lectura.rechazadas] == [extractos.DEBE_Y_HABER]

    def test_las_columnas_de_debe_y_haber_se_leen_cuando_solo_hay_una(self):
        texto = (
            "Fecha;Concepto;Debe;Haber;Saldo\n"
            "14/06/2026;PAGO DE EJEMPLO;320,00;;320,00\n"
            "15/06/2026;COBRO DE EJEMPLO;;1.205,40;1.525,40\n"
        )
        lectura = extractos.lee_extracto(texto, cuenta=CUENTA)
        assert [(f.signo, f.importe) for f in lectura.movimientos] == [
            (extractos.SALE, Decimal("320.00")),
            (extractos.ENTRA, Decimal("1205.40")),
        ]

    def test_una_letra_de_signo_que_puede_querer_decir_dos_cosas_no_se_lee(self):
        """«C» es crédito en un banco y cargo en otro: no se puede leer sin saber cuál."""
        texto = (
            "Fecha;Concepto;Signo;Importe\n"
            "14/06/2026;PAGO DE EJEMPLO;CARGO;320,00\n"
            "15/06/2026;MOVIMIENTO CON LETRA;C;10,00\n"
        )
        lectura = extractos.lee_extracto(texto, cuenta=CUENTA)
        assert [(f.signo, f.importe) for f in lectura.movimientos] == [
            (extractos.SALE, Decimal("320.00"))
        ]
        assert [r.motivo for r in lectura.rechazadas] == [extractos.SIGNO_DESCONOCIDO]

    def test_un_movimiento_de_cero_euros_no_es_un_movimiento(self):
        """Y no es lo mismo que un importe que no consta: el cero **es** un dato."""
        lectura = _lee(RARAS)
        motivos = [r.motivo for r in lectura.rechazadas]
        assert extractos.IMPORTE_CERO in motivos
        ceros = [r for r in lectura.rechazadas if r.motivo == extractos.IMPORTE_CERO]
        assert ceros[0].lo_que_dice == "0,00"

    def test_un_importe_que_no_es_un_numero_se_dice_que_no_se_ha_podido_leer(self):
        lectura = _lee(RARAS)
        ilegibles = [r for r in lectura.rechazadas if r.motivo == extractos.IMPORTE_ILEGIBLE]
        assert [r.lo_que_dice for r in ilegibles] == ["S/N"]

    def test_lo_que_no_se_entiende_se_dice_con_su_numero_de_linea(self):
        """Un rechazo sin número de línea obliga al agricultor a buscar la fila a mano."""
        lectura = _lee(RARAS)
        assert [r.numero_de_linea for r in lectura.rechazadas] == [8, 6, 7]
        for rechazada in lectura.rechazadas:
            assert rechazada.texto.startswith("1")
            assert rechazada.motivo in extractos.MOTIVOS_DE_RECHAZO

    def test_el_fichero_con_filas_raras_se_lee_a_medias_y_lo_dice(self):
        lectura = _lee(RARAS)
        assert [f.numero_de_linea for f in lectura.movimientos] == [4, 5, 9]
        assert extractos.AVISO_FILAS_RECHAZADAS in [a.codigo for a in lectura.avisos]


# ==========================================================================
# Importar dos veces el mismo extracto no duplica nada
# ==========================================================================


class TestImportarDosVecesNoDuplica:
    def test_el_mismo_fichero_leido_dos_veces_da_las_mismas_claves(self):
        """La clave no puede depender de cuándo se lee ni de en qué orden: es la misma línea."""
        primera = _lee(PRINCIPAL)
        segunda = _lee(PRINCIPAL)
        assert [f.clave_de_duplicado for f in primera.movimientos] == [
            f.clave_de_duplicado for f in segunda.movimientos
        ]

    def test_importar_dos_veces_no_duplica_ningun_movimiento(self):
        primera = _lee(PRINCIPAL)
        guardadas = {f.clave_de_duplicado for f in primera.movimientos}
        segunda = _lee(PRINCIPAL)
        nuevas, repetidas = extractos.separa_lo_que_ya_estaba(segunda.movimientos, guardadas)
        assert nuevas == ()
        # Y se dice: las siete líneas se reconocen como lo que ya estaba.
        assert len(repetidas) == len(primera.movimientos) == 7

    def test_un_fichero_que_trae_movimientos_nuevos_solo_añade_los_nuevos(self):
        """El caso de verdad: el agricultor vuelve a descargar el extracto y trae más líneas."""
        primero = _lee(PRINCIPAL)
        guardadas = {f.clave_de_duplicado for f in primero.movimientos}
        con_una_mas = PRINCIPAL.read_text(encoding="utf-8") + (
            "29/06/2026;29/06/2026;COMPRA DE EJEMPLO NUEVA;REF-2026-0010;-18,50;3.860,95\n"
        )
        lectura = extractos.lee_extracto(con_una_mas, cuenta=CUENTA, explotacion_id=1)
        nuevas, repetidas = extractos.separa_lo_que_ya_estaba(lectura.movimientos, guardadas)
        assert len(repetidas) == 7
        assert [f.referencia for f in nuevas] == ["REF-2026-0010"]

    def test_dos_lineas_identicas_del_mismo_dia_son_dos_movimientos(self):
        """**La trampa del ticket.** Sin contarlas, la segunda se tomaría por repetida y desaparecería.

        El fichero no trae referencia ni saldo, así que las dos líneas son idénticas carácter a
        carácter: son dos compras de 20 € el mismo día, y son dos de verdad. Al volver a importar el
        mismo fichero, las dos siguen cuadrando una a una.
        """
        texto = (
            "Fecha;Concepto;Importe\n"
            "14/06/2026;COMPRA DE EJEMPLO IGUAL;-20,00\n"
            "14/06/2026;COMPRA DE EJEMPLO IGUAL;-20,00\n"
        )
        lectura = extractos.lee_extracto(texto, cuenta=CUENTA)
        assert len(lectura.movimientos) == 2
        assert lectura.movimientos[0].clave_de_duplicado.endswith("#1")
        assert lectura.movimientos[1].clave_de_duplicado.endswith("#2")

        guardadas = {f.clave_de_duplicado for f in lectura.movimientos}
        nuevas, repetidas = extractos.separa_lo_que_ya_estaba(lectura.movimientos, guardadas)
        assert nuevas == ()
        assert len(repetidas) == 2

    def test_la_clave_lleva_la_cuenta_dentro(self):
        """El mismo movimiento no está en dos cuentas: la misma línea en otra cuenta es otra línea."""
        principal = _lee(PRINCIPAL)
        ahorro = _lee(AHORRO, cuenta=OTRA_CUENTA)
        # La referencia REF-2026-0004 es la misma en las dos cuentas: es el traspaso, con su dos
        # lados, y el banco le pone el mismo número a los dos.
        assert {f.referencia for f in principal.movimientos} & {
            f.referencia for f in ahorro.movimientos
        } == {"REF-2026-0004"}
        claves_principal = {f.clave_de_duplicado for f in principal.movimientos}
        claves_ahorro = {f.clave_de_duplicado for f in ahorro.movimientos}
        assert not (claves_principal & claves_ahorro)

    def test_la_huella_del_fichero_dice_si_es_el_mismo_fichero(self):
        assert extractos.huella_del_fichero(PRINCIPAL.read_bytes()) == extractos.huella_del_fichero(
            PRINCIPAL.read_bytes()
        )
        assert extractos.huella_del_fichero(PRINCIPAL.read_bytes()) != extractos.huella_del_fichero(
            AHORRO.read_bytes()
        )

    def test_los_acentos_del_concepto_se_leen_igual_en_utf8_y_en_windows(self):
        """Los dos juegos de caracteres que exporta una banca de verdad.

        Si el mismo fichero, guardado de una manera o de otra, diera claves distintas, el agricultor
        que lo descargue dos veces con dos programas distintos duplicaría el extracto entero. Y el
        concepto se usa para buscar la referencia y el nombre de la otra parte: un concepto roto es una
        conciliación que no se propone.
        """
        texto = (
            "Fecha;Concepto;Importe;Saldo\n"
            "14/06/2026;COMISIÓN DE MANTENIMIENTO EJEMPLO;-12,00;100,00\n"
        )
        en_utf8 = extractos.lee_extracto(extractos.lee_el_texto(texto.encode("utf-8")), cuenta=CUENTA)
        en_windows = extractos.lee_extracto(
            extractos.lee_el_texto(texto.encode("cp1252")), cuenta=CUENTA
        )
        assert (
            en_utf8.movimientos[0].concepto
            == en_windows.movimientos[0].concepto
            == "COMISIÓN DE MANTENIMIENTO EJEMPLO"
        )
        assert (
            en_utf8.movimientos[0].clave_de_duplicado
            == en_windows.movimientos[0].clave_de_duplicado
        )


# ==========================================================================
# A07: un traspaso entre cuentas propias no es ni un ingreso ni un gasto
# ==========================================================================


class TestUnTraspasoPropioNoEsIngresoNiGasto:
    def test_un_traspaso_entre_dos_cuentas_propias_deja_dos_movimientos_atados(self):
        """El caso A07 del contrato, literal: «Traspaso propio 500 EUR → dos movimientos
        vinculados, cero ingreso/gasto operativo»."""
        filas = list(_lee(PRINCIPAL).movimientos) + list(_lee(AHORRO, cuenta=OTRA_CUENTA).movimientos)
        traspasos = extractos.detectar_traspasos(filas, cuentas_propias=LAS_DOS_PROPIAS)
        assert len(traspasos) == 1
        traspaso = traspasos[0]
        assert traspaso.importe == Decimal("500.00")
        assert traspaso.dias_de_diferencia == 1
        assert traspaso.cuentas == (CUENTA, OTRA_CUENTA)

        marcadas = extractos.marca_los_traspasos(filas, traspasos)
        resumen = extractos.resumen_de_lo_que_ha_entrado_y_salido(marcadas, traspasos)
        # Los 500 € no son ni un ingreso ni un gasto: solo han cambiado de sitio, y se cuentan una
        # vez (lo que salió de una cuenta), no dos.
        assert resumen.importe_de_traspasos == Decimal("500.00")
        assert resumen.traspasos == 1
        # Y lo que de verdad ha entrado y salido, sin contar el traspaso ni la línea sin importe.
        assert resumen.entradas == Decimal("1208.65")
        assert resumen.salidas == Decimal("626.15")
        assert resumen.sin_importe == 1

    def test_sin_marcarlo_el_traspaso_se_contaria_como_ingreso_y_como_gasto(self):
        """**La prueba que demuestra que la regla hace algo.**

        Es lo que pasaría sin el vínculo: los mismos 500 € sumarían como un ingreso en una cuenta y
        como un gasto en la otra, y el margen de la explotación saldría con 500 € de más por cada
        lado por haber movido dinero de sitio.
        """
        filas = list(_lee(PRINCIPAL).movimientos) + list(_lee(AHORRO, cuenta=OTRA_CUENTA).movimientos)
        sin_marcar = extractos.resumen_de_lo_que_ha_entrado_y_salido(filas)
        assert sin_marcar.importe_de_traspasos == Decimal("0.00")
        assert sin_marcar.traspasos == 0
        # Los mismos 500 € sumados como ingreso (en la cuenta de ahorro) y como gasto (en la
        # principal): 500 € de más por cada lado, que es lo que el vínculo evita.
        assert sin_marcar.entradas == Decimal("1708.65")
        assert sin_marcar.salidas == Decimal("1126.15")

        traspasos = extractos.detectar_traspasos(filas, cuentas_propias=LAS_DOS_PROPIAS)
        con_marca = extractos.resumen_de_lo_que_ha_entrado_y_salido(
            extractos.marca_los_traspasos(filas, traspasos), traspasos
        )
        assert sin_marcar.entradas - con_marca.entradas == Decimal("500.00")
        assert sin_marcar.salidas - con_marca.salidas == Decimal("500.00")

    def test_lo_marcado_en_los_movimientos_basta_para_no_contarlo(self):
        """El caso de la pantalla: cuando el traspaso ya está atado, el resumen solo tiene las filas.

        El vínculo se guarda en los dos movimientos (`pareja_de_traspaso_id`), y a partir de ahí ya no
        hay ninguna lista de traspasos que pasar. Si el resumen mirara solo la lista que se le da, los
        500 € volverían a contarse como ingreso y como gasto el día que se lee lo guardado.
        """
        filas = list(_lee(PRINCIPAL).movimientos) + list(_lee(AHORRO, cuenta=OTRA_CUENTA).movimientos)
        traspasos = extractos.detectar_traspasos(filas, cuentas_propias=LAS_DOS_PROPIAS)
        marcadas = extractos.marca_los_traspasos(filas, traspasos)
        # Sin pasarle la lista de traspasos: solo las filas ya marcadas.
        resumen = extractos.resumen_de_lo_que_ha_entrado_y_salido(marcadas)
        assert resumen.importe_de_traspasos == Decimal("500.00")
        assert resumen.traspasos == 1
        assert resumen.entradas == Decimal("1208.65")
        assert resumen.salidas == Decimal("626.15")

    def test_un_pago_a_un_proveedor_y_un_cobro_iguales_no_son_un_traspaso(self):
        """Dos hechos distintos que casualmente cuadran no se atan."""
        filas = [
            _una_fila(cuenta="Cuenta A", importe="500.00", signo=extractos.SALE),
            _una_fila(cuenta="Cuenta B", importe="500.00", signo=extractos.ENTRA),
        ]
        assert extractos.detectar_traspasos(filas, cuentas_propias={"Cuenta A": False, "Cuenta B": False}) == ()
        # Y con una sola cuenta propia, tampoco.
        assert extractos.detectar_traspasos(filas, cuentas_propias={"Cuenta A": True, "Cuenta B": False}) == ()

    def test_dos_apuntes_en_la_misma_cuenta_no_son_un_traspaso(self):
        """El contrario en la misma cuenta es una devolución, no dinero que cambia de sitio."""
        filas = [
            _una_fila(cuenta=CUENTA, importe="500.00", signo=extractos.SALE),
            _una_fila(cuenta=CUENTA, importe="500.00", signo=extractos.ENTRA),
        ]
        assert extractos.detectar_traspasos(filas, cuentas_propias=LAS_DOS_PROPIAS) == ()

    def test_con_mas_de_tres_dias_de_diferencia_no_se_propone(self):
        filas = [
            _una_fila(cuenta=CUENTA, importe="500.00", signo=extractos.SALE, fecha=dt.date(2026, 6, 1)),
            _una_fila(
                cuenta=OTRA_CUENTA, importe="500.00", signo=extractos.ENTRA, fecha=dt.date(2026, 6, 10)
            ),
        ]
        assert extractos.detectar_traspasos(filas, cuentas_propias=LAS_DOS_PROPIAS) == ()
        # Y a tres días sí: es lo que tarda una transferencia entre dos entidades.
        filas[1] = _una_fila(
            cuenta=OTRA_CUENTA, importe="500.00", signo=extractos.ENTRA, fecha=dt.date(2026, 6, 4)
        )
        assert len(extractos.detectar_traspasos(filas, cuentas_propias=LAS_DOS_PROPIAS)) == 1

    def test_un_importe_distinto_no_es_el_mismo_dinero(self):
        """Un traspaso es el mismo dinero: si lleva comisión, la comisión es otra línea."""
        filas = [
            _una_fila(cuenta=CUENTA, importe="500.00", signo=extractos.SALE),
            _una_fila(cuenta=OTRA_CUENTA, importe="499.00", signo=extractos.ENTRA),
        ]
        assert extractos.detectar_traspasos(filas, cuentas_propias=LAS_DOS_PROPIAS) == ()

    def test_un_movimiento_solo_puede_estar_en_un_traspaso(self):
        filas = [
            _una_fila(cuenta=CUENTA, importe="500.00", signo=extractos.SALE),
            _una_fila(cuenta=OTRA_CUENTA, importe="500.00", signo=extractos.ENTRA),
            _una_fila(cuenta="Cuenta tercera", importe="500.00", signo=extractos.ENTRA),
        ]
        traspasos = extractos.detectar_traspasos(
            filas, cuentas_propias={CUENTA: True, OTRA_CUENTA: True, "Cuenta tercera": True}
        )
        assert len(traspasos) == 1
        usadas = [clave for traspaso in traspasos for clave in traspaso.claves]
        assert len(usadas) == len(set(usadas)) == 2

    def test_un_traspaso_no_se_propone_para_conciliar(self):
        """El dinero que solo ha cambiado de sitio no salda ninguna factura."""
        fila = _una_fila(importe="500.00", signo=extractos.SALE)
        marcada = extractos.marca_los_traspasos(
            [fila, _una_fila(signo=extractos.ENTRA)],
            [extractos.Traspaso(fila.clave_de_duplicado, "otra", Decimal("500.00"), 0, (CUENTA, "X"))],
        )[0]
        assert marcada.es_traspaso_propio is True
        assert (
            extractos.por_que_no_se_puede_conciliar(marcada) == extractos.NO_PORQUE_ES_UN_TRASPASO
        )
        assert extractos.proponer_conciliaciones(marcada, [_una_factura()]) == ()


# ==========================================================================
# Un importe que no consta NO es cero, de punta a punta
# ==========================================================================


class TestUnImporteQueNoConstaNoEsCero:
    """La cadena entera: fichero → dato → cuenta → pantalla → exportación."""

    def test_en_el_fichero_una_casilla_vacia_es_no_lo_se_y_no_cero(self):
        lectura = _lee(PRINCIPAL)
        sin_importe = [f for f in lectura.movimientos if f.importe is None]
        assert len(sin_importe) == 1
        fila = sin_importe[0]
        assert fila.signo is None
        assert extractos.IMPORTE_NO_CONSTA in fila.falta
        assert extractos.AVISO_IMPORTES_QUE_NO_CONSTAN in [a.codigo for a in lectura.avisos]

    def test_no_se_suma_como_si_fuera_cero(self):
        """Y el resumen lo **cuenta** en vez de callárselo: un total que calla que le faltan datos
        es un total que miente."""
        filas = _lee(PRINCIPAL).movimientos
        resumen = extractos.resumen_de_lo_que_ha_entrado_y_salido(filas)
        assert resumen.sin_importe == 1
        # La suma de la columna, hecha a mano sobre lo que sí se sabe:
        assert resumen.salidas == Decimal("1126.15")
        assert resumen.entradas == Decimal("1205.40")
        # Y si el importe que no consta se hubiera puesto a cero, el resumen sería el mismo: por eso
        # lo que protege de verdad es el **contador**, que está arriba.
        assert resumen.sin_importe > 0

    def test_un_movimiento_sin_importe_no_se_puede_conciliar_y_se_dice_por_que(self):
        fila = [f for f in _lee(PRINCIPAL).movimientos if f.importe is None][0]
        assert fila.se_puede_conciliar is False
        assert (
            extractos.por_que_no_se_puede_conciliar(fila) == extractos.NO_PORQUE_NO_CONSTA_EL_IMPORTE
        )
        assert extractos.proponer_conciliaciones(fila, [_una_factura()]) == ()
        assert (
            extractos.estado_de_conciliacion(fila.importe, None)
            == extractos.NO_SE_PUEDE_CONCILIAR
        )
        assert extractos.lo_que_falta_por_conciliar(fila.importe, None) is None

    def test_revisar_una_conciliacion_de_un_movimiento_sin_importe_lo_dice(self):
        fila = [f for f in _lee(PRINCIPAL).movimientos if f.importe is None][0]
        revision = extractos.revisa_una_conciliacion(
            movimiento=fila, imputaciones=[(_una_factura(), Decimal("100.00"))]
        )
        assert revision.problemas == (extractos.PROBLEMA_NO_CONSTA_EL_IMPORTE,)
        assert revision.se_puede_guardar is False
        assert revision.lineas == ()

    def test_en_el_csv_que_se_exporta_sale_en_blanco_y_nunca_como_cero(self):
        lectura = _lee(PRINCIPAL)
        lineas = extractos.a_csv(lectura.movimientos).splitlines()
        la_del_importe_desconocido = [l for l in lineas if "ANOTACION SIN IMPORTE" in l][0]
        casillas = la_del_importe_desconocido.split(";")
        assert casillas[4] == "", "el importe que no consta no puede salir como un número"
        assert "0,00" not in la_del_importe_desconocido
        assert "no consta el importe" in la_del_importe_desconocido
        # Y el resto del fichero sí lleva sus números.
        con_importe = [l for l in lineas if "COMISIÓN DE MANTENIMIENTO" in l][0]
        assert con_importe.split(";")[4] == "12,00"

    def test_en_el_csv_un_movimiento_conciliado_dice_como_esta(self):
        filas = _lee(PRINCIPAL).movimientos
        conciliado = {filas[2].clave_de_duplicado: Decimal("1205.40")}
        lineas = extractos.a_csv(filas, conciliado=conciliado).splitlines()
        la_del_cobro = [l for l in lineas if "COOPERATIVA EJEMPLO" in l][0]
        assert la_del_cobro.split(";")[7] == "conciliado"
        a_medias = {filas[2].clave_de_duplicado: Decimal("200.00")}
        lineas = extractos.a_csv(filas, conciliado=a_medias).splitlines()
        la_del_cobro = [l for l in lineas if "COOPERATIVA EJEMPLO" in l][0]
        assert la_del_cobro.split(";")[7] == "conciliado a medias"


# ==========================================================================
# La conciliación: muchos a muchos, con parciales y agrupados
# ==========================================================================


class TestPagosParcialesYAgrupados:
    def test_una_factura_a_la_que_le_falta_justo_el_importe_se_propone_exacta(self):
        fila = _una_fila(importe="1205.40", signo=extractos.ENTRA)
        factura = _una_factura(pendiente="1205.40")
        propuestas = extractos.proponer_conciliaciones(fila, [factura])
        assert len(propuestas) == 1
        assert propuestas[0].tipo == extractos.PROPUESTA_EXACTA
        assert propuestas[0].documentos == (factura.etiqueta,)
        assert extractos.PORQUE_EL_IMPORTE_CUADRA in propuestas[0].porque
        assert propuestas[0].sobrante == Decimal("0.00")

    def test_un_solo_ingreso_que_salda_tres_facturas_se_propone_agrupada(self):
        """Muchos a muchos: el contrato lo pide para «pagos parciales o agrupados»."""
        fila = _una_fila(importe="600.00", signo=extractos.ENTRA)
        facturas = [
            _una_factura(documento_id=1, importe="250.00", pendiente="250.00"),
            _una_factura(documento_id=2, importe="200.00", pendiente="200.00"),
            _una_factura(documento_id=3, importe="150.00", pendiente="150.00"),
        ]
        propuestas = extractos.proponer_conciliaciones(fila, facturas)
        agrupadas = [p for p in propuestas if p.tipo == extractos.PROPUESTA_AGRUPADA]
        assert len(agrupadas) == 1
        assert agrupadas[0].total == Decimal("600.00")
        assert len(agrupadas[0].lineas) == 3
        assert extractos.PORQUE_LA_SUMA_CUADRA in agrupadas[0].porque

    def test_una_suma_que_no_cuadra_no_se_propone(self):
        """Los 20 € que faltarían serían un invento."""
        fila = _una_fila(importe="500.00", signo=extractos.ENTRA)
        facturas = [
            _una_factura(documento_id=1, importe="250.00", pendiente="250.00"),
            _una_factura(documento_id=2, importe="230.00", pendiente="230.00"),
        ]
        assert extractos.proponer_conciliaciones(fila, facturas) == ()

    def test_un_pago_parcial_se_propone_parcial(self):
        """El caso A06: factura de 121 € y pago de 40 €."""
        fila = _una_fila(importe="40.00", signo=extractos.ENTRA)
        factura = _una_factura(importe="121.00", pendiente="121.00")
        propuestas = extractos.proponer_conciliaciones(fila, [factura])
        assert [p.tipo for p in propuestas] == [extractos.PROPUESTA_PARCIAL]
        assert propuestas[0].total == Decimal("40.00")
        assert extractos.lo_que_falta_por_conciliar(
            factura.pendiente, propuestas[0].total
        ) == Decimal("81.00")

    def test_un_papel_cuyo_pendiente_no_se_sabe_no_se_propone(self):
        """Suponer que le falta todo sería inventarse un número."""
        fila = _una_fila(importe="40.00", signo=extractos.ENTRA)
        sin_pendiente = _una_factura(pendiente=None)
        assert sin_pendiente.se_puede_conciliar is False
        assert extractos.proponer_conciliaciones(fila, [sin_pendiente]) == ()

    def test_un_ingreso_no_salda_una_factura_que_se_debe_pagar(self):
        """El lado del dinero tiene que ser el mismo."""
        entra = _una_fila(importe="320.00", signo=extractos.ENTRA)
        compra = _una_factura(
            clase=extractos.FACTURA_DE_COMPRA, importe="320.00", pendiente="320.00"
        )
        assert extractos.proponer_conciliaciones(entra, [compra]) == ()
        sale = _una_fila(importe="320.00", signo=extractos.SALE)
        assert len(extractos.proponer_conciliaciones(sale, [compra])) == 1

    def test_la_referencia_en_el_concepto_es_lo_que_mas_puntua(self):
        """El porqué de una propuesta tiene que poder leerse, y lo que más la explica es la referencia."""
        fila = _una_fila(
            importe="1205.40", signo=extractos.ENTRA, concepto="TRANSFERENCIA FACTURA F-2026-014"
        )
        con_referencia = _una_factura(referencia="F-2026-014")
        otra = _una_factura(documento_id=2, referencia="F-2026-099")
        propuestas = extractos.proponer_conciliaciones(fila, [otra, con_referencia])
        assert propuestas[0].documentos == (con_referencia.etiqueta,)
        assert extractos.PORQUE_LA_REFERENCIA_ESTA_EN_EL_CONCEPTO in propuestas[0].porque
        assert propuestas[0].puntuacion > propuestas[1].puntuacion

    def test_el_nombre_de_la_otra_parte_tambien_cuenta(self):
        fila = _una_fila(importe="1205.40", signo=extractos.ENTRA, concepto="COBRO COOPERATIVA EJEMPLO")
        propuesta = extractos.proponer_conciliaciones(fila, [_una_factura()])[0]
        assert extractos.PORQUE_EL_NOMBRE_ESTA_EN_EL_CONCEPTO in propuesta.porque

    def test_se_reparte_por_orden_hasta_agotar_el_dinero(self):
        """Un ingreso que paga tres papeles sin decir cuánto a cada uno."""
        facturas = [
            _una_factura(documento_id=1, importe="100.00", pendiente="100.00"),
            _una_factura(documento_id=2, importe="200.00", pendiente="200.00"),
            _una_factura(documento_id=3, importe="300.00", pendiente="300.00"),
        ]
        lineas = extractos.reparte_lo_que_queda(importe=Decimal("250.00"), pendientes=facturas)
        assert [(l.documento.documento_id, l.importe) for l in lineas] == [
            (1, Decimal("100.00")),
            (2, Decimal("150.00")),
        ]

    def test_se_reparte_lo_que_se_puede_con_un_papel_sin_pendiente_conocido(self):
        facturas = [
            _una_factura(documento_id=1, pendiente=None),
            _una_factura(documento_id=2, importe="200.00", pendiente="200.00"),
        ]
        lineas = extractos.reparte_lo_que_queda(importe=Decimal("250.00"), pendientes=facturas)
        assert [(l.documento.documento_id, l.importe) for l in lineas] == [(2, Decimal("200.00"))]

    def test_no_se_puede_repartir_un_importe_que_no_se_sabe(self):
        assert extractos.reparte_lo_que_queda(importe=None, pendientes=[_una_factura()]) == ()

    def test_no_se_imputa_mas_de_lo_que_le_falta_al_papel(self):
        factura = _una_factura(pendiente="81.00")
        revision = extractos.revisa_una_conciliacion(
            movimiento=_una_fila(importe="500.00", signo=extractos.ENTRA),
            imputaciones=[(factura, Decimal("100.00"))],
        )
        assert revision.problemas == (extractos.PROBLEMA_MAS_QUE_EL_PENDIENTE,)
        assert revision.lineas == ()
        assert revision.se_puede_guardar is False

    def test_no_se_imputa_mas_de_lo_que_dice_el_movimiento(self):
        facturas = [
            _una_factura(documento_id=1, pendiente="400.00"),
            _una_factura(documento_id=2, pendiente="400.00"),
        ]
        revision = extractos.revisa_una_conciliacion(
            movimiento=_una_fila(importe="500.00", signo=extractos.ENTRA),
            imputaciones=[(facturas[0], Decimal("400.00")), (facturas[1], Decimal("400.00"))],
        )
        assert revision.problemas == (extractos.PROBLEMA_MAS_QUE_EL_MOVIMIENTO,)
        # La primera sí cabe, y se queda: no se pierde lo que ya se había repartido bien.
        assert [(l.documento.documento_id, l.importe) for l in revision.lineas] == [
            (1, Decimal("400.00"))
        ]

    def test_el_mismo_papel_dos_veces_no_vale(self):
        factura = _una_factura(pendiente="500.00")
        revision = extractos.revisa_una_conciliacion(
            movimiento=_una_fila(importe="500.00", signo=extractos.ENTRA),
            imputaciones=[(factura, Decimal("200.00")), (factura, Decimal("100.00"))],
        )
        assert revision.problemas == (extractos.PROBLEMA_DOCUMENTO_REPETIDO,)
        assert revision.total == Decimal("200.00")

    def test_un_papel_cuyo_pendiente_no_se_sabe_se_rechaza_al_conciliar(self):
        factura = _una_factura(pendiente=None)
        revision = extractos.revisa_una_conciliacion(
            movimiento=_una_fila(importe="500.00", signo=extractos.ENTRA),
            imputaciones=[(factura, Decimal("100.00"))],
        )
        assert revision.problemas == (extractos.PROBLEMA_DOCUMENTO_SIN_PENDIENTE,)

    def test_un_importe_cero_o_negativo_al_conciliar_no_vale(self):
        factura = _una_factura(pendiente="500.00")
        revision = extractos.revisa_una_conciliacion(
            movimiento=_una_fila(importe="500.00", signo=extractos.ENTRA),
            imputaciones=[(factura, Decimal("0.00"))],
        )
        assert revision.problemas == (extractos.PROBLEMA_IMPORTE_NO_VALE,)

    def test_una_conciliacion_buena_se_puede_guardar_y_dice_lo_que_sobra(self):
        factura = _una_factura(pendiente="81.00")
        revision = extractos.revisa_una_conciliacion(
            movimiento=_una_fila(importe="100.00", signo=extractos.ENTRA),
            imputaciones=[(factura, Decimal("81.00"))],
        )
        assert revision.se_puede_guardar is True
        assert revision.total == Decimal("81.00")
        assert revision.sobrante == Decimal("19.00")

    def test_el_estado_de_un_movimiento_dice_a_medias_o_conciliado(self):
        assert extractos.estado_de_conciliacion(Decimal("121.00"), None) == extractos.SIN_CONCILIAR
        assert (
            extractos.estado_de_conciliacion(Decimal("121.00"), Decimal("40.00"))
            == extractos.CONCILIADO_EN_PARTE
        )
        assert (
            extractos.estado_de_conciliacion(Decimal("121.00"), Decimal("121.00"))
            == extractos.CONCILIADO
        )
        assert extractos.estado_de_conciliacion(None, Decimal("40.00")) == extractos.NO_SE_PUEDE_CONCILIAR
        assert extractos.lo_que_falta_por_conciliar(Decimal("121.00"), Decimal("40.00")) == Decimal("81.00")
        assert extractos.lo_que_falta_por_conciliar(Decimal("40.00"), Decimal("121.00")) == Decimal("0.00")


# ==========================================================================
# Conciliar no crea nada: ni un gasto, ni una factura, ni un movimiento
# ==========================================================================


class TestConciliarNoCreaNada:
    def test_las_imputaciones_apuntan_a_los_papeles_que_ya_existian(self):
        """**El corazón de la regla.** Si el módulo pudiera fabricar un documento, aquí saldría uno."""
        fila = _una_fila(importe="600.00", signo=extractos.ENTRA)
        facturas = [
            _una_factura(documento_id=1, importe="250.00", pendiente="250.00"),
            _una_factura(documento_id=2, importe="200.00", pendiente="200.00"),
            _una_factura(documento_id=3, importe="150.00", pendiente="150.00"),
        ]
        antes = {f.etiqueta for f in facturas}
        propuestas = extractos.proponer_conciliaciones(fila, facturas)
        for propuesta in propuestas:
            for linea in propuesta.lineas:
                assert linea.documento.etiqueta in antes
                # Y es **el mismo** papel, no una copia con los mismos números.
                assert any(linea.documento is f for f in facturas)

    def test_el_reparto_tampoco_crea_papeles(self):
        facturas = [_una_factura(documento_id=9, pendiente="100.00")]
        lineas = extractos.reparte_lo_que_queda(importe=Decimal("100.00"), pendientes=facturas)
        assert [l.documento is facturas[0] for l in lineas] == [True]
        assert lineas[0].documento.pendiente == Decimal("100.00")

    def test_conciliar_no_cambia_el_importe_del_papel_ni_el_del_movimiento(self):
        """Lo único que cambia con una conciliación es **a qué apunta el dinero**."""
        fila = _una_fila(importe="40.00", signo=extractos.ENTRA)
        factura = _una_factura(importe="121.00", pendiente="121.00")
        revision = extractos.revisa_una_conciliacion(
            movimiento=fila, imputaciones=[(factura, Decimal("40.00"))]
        )
        assert revision.se_puede_guardar
        assert fila.importe == Decimal("40.00")
        assert factura.importe == Decimal("121.00")
        assert factura.pendiente == Decimal("121.00")
        # Y lo que le queda por cobrar es lo que se calcula, sin tocar el papel:
        assert extractos.lo_que_falta_por_conciliar(
            factura.importe, revision.total
        ) == Decimal("81.00")


class TestDeshacerDejaTodoComoEstaba:
    """La mitad del ticket: **deshacer una conciliación tiene que dejar todo como estaba.**

    Y la otra mitad: **no puede borrar el movimiento del banco**. El banco ya movió ese dinero; lo
    único que se puede deshacer es a qué papeles se había apuntado. Por eso lo que se deshace son los
    vínculos, y el movimiento se queda con su importe, su fecha y su concepto.
    """

    @staticmethod
    def _pendiente_de(importe: Decimal, imputado: Decimal) -> Decimal:
        """Lo que le falta a un papel: su importe menos lo que se le ha imputado."""
        return extractos.lo_que_falta_por_conciliar(importe, imputado)

    def test_deshacer_devuelve_a_cada_papel_lo_que_se_le_habia_imputado(self):
        """Un ingreso de 600 € que salda tres facturas: se concilia, y se deshace."""
        fila = _una_fila(importe="600.00", signo=extractos.ENTRA)
        facturas = [
            _una_factura(documento_id=1, importe="250.00", pendiente="250.00"),
            _una_factura(documento_id=2, importe="200.00", pendiente="200.00"),
            _una_factura(documento_id=3, importe="150.00", pendiente="150.00"),
        ]
        pendientes_antes = {f.etiqueta: f.pendiente for f in facturas}
        propuesta = [
            p
            for p in extractos.proponer_conciliaciones(fila, facturas)
            if p.tipo == extractos.PROPUESTA_AGRUPADA
        ][0]
        assert propuesta.total == Decimal("600.00")

        # Lo imputado a cada papel, antes (nada), al conciliar (lo que dice la propuesta) y después de
        # deshacer (vuelve a nada).
        imputado_antes = {f.etiqueta: Decimal("0.00") for f in facturas}
        imputado_al_conciliar = {
            f.etiqueta: imputado_antes[f.etiqueta]
            + next((l.importe for l in propuesta.lineas if l.documento is f), Decimal("0.00"))
            for f in facturas
        }
        assert imputado_al_conciliar == {
            "factura_emitida:1": Decimal("250.00"),
            "factura_emitida:2": Decimal("200.00"),
            "factura_emitida:3": Decimal("150.00"),
        }
        pendientes_al_conciliar = {
            f.etiqueta: self._pendiente_de(f.importe, imputado_al_conciliar[f.etiqueta])
            for f in facturas
        }
        assert pendientes_al_conciliar == {
            "factura_emitida:1": Decimal("0.00"),
            "factura_emitida:2": Decimal("0.00"),
            "factura_emitida:3": Decimal("0.00"),
        }

        # Y se deshace: todo vuelve **exactamente** a como estaba.
        devoluciones = extractos.deshace_una_conciliacion(propuesta.lineas)
        devuelto = {d.documento.etiqueta: d.importe for d in devoluciones}
        imputado_despues = {
            f.etiqueta: imputado_al_conciliar[f.etiqueta] - devuelto.get(f.etiqueta, Decimal("0.00"))
            for f in facturas
        }
        assert imputado_despues == imputado_antes
        pendientes_despues = {
            f.etiqueta: self._pendiente_de(f.importe, imputado_despues[f.etiqueta]) for f in facturas
        }
        assert pendientes_despues == pendientes_antes
        assert sum(devuelto.values()) == fila.importe == Decimal("600.00")

    def test_deshacer_un_pago_parcial_devuelve_el_pendiente_de_antes(self):
        """40 € imputados a una factura de 121 €: al deshacer, la factura vuelve a deber 121, no 81."""
        fila = _una_fila(importe="40.00", signo=extractos.ENTRA)
        factura = _una_factura(importe="121.00", pendiente="121.00")
        assert self._pendiente_de(factura.importe, Decimal("0.00")) == Decimal("121.00")

        revision = extractos.revisa_una_conciliacion(
            movimiento=fila, imputaciones=[(factura, Decimal("40.00"))]
        )
        assert revision.se_puede_guardar is True
        al_conciliar = self._pendiente_de(factura.importe, revision.total)
        assert al_conciliar == Decimal("81.00")

        devoluciones = extractos.deshace_una_conciliacion(revision.lineas)
        assert [(d.documento.etiqueta, d.importe) for d in devoluciones] == [
            ("factura_emitida:1", Decimal("40.00"))
        ]
        devuelto = sum(d.importe for d in devoluciones)
        despues = self._pendiente_de(factura.importe, revision.total - devuelto)
        assert despues == Decimal("121.00") == factura.pendiente
        # Y el movimiento sigue entero: no se ha borrado ni se ha partido.
        assert fila.importe == Decimal("40.00")
        assert fila.concepto is not None and fila.fecha is not None

    def test_deshacer_no_devuelve_nada_de_las_imputaciones_que_no_existen(self):
        assert extractos.deshace_una_conciliacion([]) == ()


# ==========================================================================
# Aislamiento entre fincas
# ==========================================================================


class TestAislamientoEntreFincas:
    def test_un_movimiento_no_propone_nada_de_otra_finca(self):
        mío = _una_fila(importe="1205.40", signo=extractos.ENTRA, explotacion_id=1)
        de_otra = _una_factura(documento_id=7, pendiente="1205.40", explotacion_id=2)
        assert extractos.proponer_conciliaciones(mío, [de_otra]) == ()

    def test_conciliar_a_mano_con_un_papel_de_otra_finca_se_rechaza(self):
        mío = _una_fila(importe="1205.40", signo=extractos.ENTRA, explotacion_id=1)
        de_otra = _una_factura(documento_id=7, pendiente="1205.40", explotacion_id=2)
        revision = extractos.revisa_una_conciliacion(
            movimiento=mío, imputaciones=[(de_otra, Decimal("1205.40"))]
        )
        assert extractos.PROBLEMA_DE_OTRA_FINCA in revision.problemas
        assert revision.lineas == ()

    def test_las_filas_que_se_leen_llevan_su_finca(self):
        """Y eso empieza en la lectura: la finca viaja en el dato desde el fichero."""
        lectura = _lee(PRINCIPAL, explotacion_id=42)
        assert {f.explotacion_id for f in lectura.movimientos} == {42}


# ==========================================================================
# El rastro: quién, cuándo y qué se deshizo
# ==========================================================================


class TestElRastroDeUnaConciliacion:
    """Lo que se puede comprobar hoy del rastro, y lo que necesita la base de datos.

    El rastro de verdad (la fila de auditoría, la fecha, el usuario y el motivo del deshizo) vive en
    el router, porque es él quien guarda. Aquí se comprueba **la parte que se puede comprobar sin
    base de datos**: que el rastro que se va a escribir lleva las cuatro cosas, y que el vocabulario
    de acciones cabe en su columna.
    """

    def test_el_router_escribe_el_rastro_con_texto_fijo_y_corto(self):
        """La columna `auditoria.accion` mide 80, y en PostgreSQL pasarse tumba la operación entera.

        Se leen del código las etiquetas de verdad (el guardián del programa,
        `tests/test_las_etiquetas_del_rastro_caben.py`, hace lo mismo con todo el programa).
        """
        raiz = pathlib.Path(__file__).resolve().parents[1]
        texto = (raiz / "app" / "routers" / "extractos_api.py").read_text(encoding="utf-8")
        etiquetas = re.findall(r'accion="([^"]+)"', texto)
        assert len(etiquetas) >= 4, (
            "el router no escribe las acciones del rastro con texto fijo: " f"solo se han leído {etiquetas}"
        )
        for etiqueta in etiquetas:
            assert len(etiqueta) <= 80, etiqueta
            assert etiqueta.isascii(), f"una etiqueta del rastro no puede llevar tildes: {etiqueta}"

    def test_el_rastro_guarda_lo_que_se_deshizo_con_el_motivo(self):
        texto = pathlib.Path(__file__).resolve().parents[1] / "app" / "routers" / "extractos_api.py"
        codigo = texto.read_text(encoding="utf-8")
        for pieza in (
            "deshecha_por_usuario_id",
            "deshecha_en",
            "motivo_del_deshacer",
            "usuario_id",
        ):
            assert pieza in codigo, (
                f"el rastro de una conciliación deshecha tiene que guardar «{pieza}»: quién, cuándo "
                "y qué se deshizo. No basta con borrar el vínculo."
            )


# ==========================================================================
# Lo que falta por integrar, y cómo se comprueba cuando esté
# ==========================================================================

# Las piezas que este ticket necesita y que **no puede escribir él**: las tablas, los esquemas, el
# registro del router, los textos y el menú los integra el coordinador (es el reparto del apartado
# 47.5 del seguimiento). Mientras falten, las pruebas del recorrido por la API se saltan **diciendo
# qué falta**, en vez de quedarse en verde sin haber comprobado nada.
PIEZAS_QUE_FALTAN_POR_INTEGRAR = {
    "tabla cuentas_bancarias": "CuentaBancaria",
    "tabla perfiles_de_extracto": "PerfilDeExtracto",
    "tabla movimientos_de_extracto": "MovimientoDeExtracto",
    "tabla conciliaciones_de_movimiento": "ConciliacionDeMovimiento",
    "tabla importaciones_de_extracto": "ImportacionDeExtracto",
}


def _lo_que_falta_por_integrar() -> list[str]:
    """Lo que este ticket necesita y no puede escribir él, leído de verdad de `app.models`.

    Se mira con `hasattr` y no con una lista escrita a mano: el día que el coordinador integre las
    tablas, esta función devuelve la lista vacía sola, sin que nadie se acuerde de tocar nada.
    """
    return [
        nombre
        for nombre, atributo in PIEZAS_QUE_FALTAN_POR_INTEGRAR.items()
        if not hasattr(models, atributo)
    ]


@pytest.fixture(scope="module")
def lo_que_falta() -> list[str]:
    return _lo_que_falta_por_integrar()


class TestLoQueFaltaEstaDicho:
    def test_el_mapa_de_lo_que_falta_se_mira_de_verdad(self):
        """Un guardián que no encuentra nada no está comprobando nada.

        Esta prueba comprueba el **extractor**: hoy las cinco tablas faltan, y tiene que verlo. El día
        que el coordinador las integre, esta prueba seguirá pasando (dirá que no falta ninguna).
        """
        falta = _lo_que_falta_por_integrar()
        if falta:
            assert set(falta) <= set(PIEZAS_QUE_FALTAN_POR_INTEGRAR)
            assert len(falta) == len(PIEZAS_QUE_FALTAN_POR_INTEGRAR), (
                "se han leído mal las tablas que faltan: " + ", ".join(falta)
            )

    def test_lo_que_falta_esta_escrito_en_el_informe(self):
        """Y lo que falta, con su nombre exacto, tiene que estar en `docs/T20_EXTRACTOS.md`.

        Es lo que impide que un ticket se entregue diciendo «falta integrar» sin decir **qué**, y que
        lo que falta se olvide en cuanto pasa la ronda.
        """
        informe = pathlib.Path(__file__).resolve().parents[2] / "docs" / "T20_EXTRACTOS.md"
        assert informe.is_file(), "falta el informe del ticket: docs/T20_EXTRACTOS.md"
        texto = informe.read_text(encoding="utf-8")
        for nombre, atributo in PIEZAS_QUE_FALTAN_POR_INTEGRAR.items():
            assert atributo in texto, f"el informe no dice que hace falta {atributo} ({nombre})"
        for nombre in (
            "extractos_api",
            "include_router",
        ):
            assert nombre in texto, f"el informe no dice qué hacer con «{nombre}»"

    def test_los_ficheros_de_ejemplo_del_extracto_no_estan_ignorados(self):
        """Los extractos de ejemplo tienen que **viajar con el código**.

        `.gitignore` tiene una regla `*.csv` (para no subir lo que el programa **escribe**) con
        excepciones para los ficheros que el programa **lee**, y entre esas excepciones están los
        ficheros de `data/`. Los de `backend/tests/datos/` son de la misma clase: si no se añaden, la
        suite entera de este ticket falla en cualquier copia recién hecha, y aquí no se notaría. Es el
        mismo aviso que el propio `.gitignore` deja escrito en un comentario.
        """
        raiz = pathlib.Path(__file__).resolve().parents[2]
        gitignore = (raiz / ".gitignore").read_text(encoding="utf-8")
        assert "*.csv" in gitignore, (
            "el `.gitignore` ya no ignora los CSV: mira si esta prueba sigue teniendo sentido"
        )
        if "!backend/tests/datos/" not in gitignore:
            pytest.skip(
                "el `.gitignore` se come los extractos de ejemplo: añade la línea "
                "`!backend/tests/datos/` (o `!backend/tests/datos/*.csv`) para que viajen con el código"
            )

    def test_los_textos_que_pide_el_router_estan_en_textos_py(self):
        """Si el router pide un mensaje que no existe, el texto sale en blanco delante del agricultor.

        Se saltan los que todavía no están integrados (y se listan), y en cuanto estén, esta prueba
        comprueba de verdad que el mensaje existe y no está vacío.
        """
        claves = _las_claves_de_texto_que_pide_el_router()
        assert len(claves) >= 5, f"el extractor de claves se ha roto: solo ha visto {claves}"
        faltan = sorted(clave for clave in claves if clave not in textos.MENSAJES)
        if faltan:
            pytest.skip("mensajes que todavía no están en textos.py: " + ", ".join(faltan))
        for clave in claves:
            assert textos.MENSAJES[clave].strip(), f"el mensaje {clave} está vacío"


def _las_claves_de_texto_que_pide_el_router() -> set[str]:
    """Las claves de mensaje que pide el router de los extractos. Se leen del código, no de una lista.

    Es el mismo truco que usa `tests/test_que_no_falte_ningun_texto.py` con el JavaScript, y por el
    mismo motivo: una lista escrita a mano se queda vieja y deja de comprobar.
    """
    raiz = pathlib.Path(__file__).resolve().parents[1]
    codigo = (raiz / "app" / "routers" / "extractos_api.py").read_text(encoding="utf-8")
    return set(re.findall(r'textos\.mensaje\(\s*"([A-Za-z0-9_]+)"', codigo)) | set(
        re.findall(r'textos\.con_cuenta\(\s*textos\.[A-Z_]+\s*,\s*"([A-Za-z0-9_]+)"', codigo)
    )


@pytest.mark.skipif(
    bool(_lo_que_falta_por_integrar()),
    reason="faltan por integrar: " + ", ".join(_lo_que_falta_por_integrar()),
)
class TestElRecorridoPorLaApi:
    """El recorrido entero: cuenta → vista previa → importar → revisar → conciliar → deshacer.

    Se salta mientras falten las tablas, el `include_router` y los textos, y el día que estén se
    ejecuta entero: es lo que comprueba lo que **no se puede comprobar sin base de datos** (que
    conciliar no crea ninguna factura ni ningún cobro, que deshacer deja el rastro y que el extracto
    de una finca no se ve desde otra).

    Las mismas comprobaciones se han pasado a mano contra las tablas propuestas, en un SQLite
    temporal, antes de entregar el ticket (está contado en `docs/T20_EXTRACTOS.md`). Aquí quedan para
    que se sigan comprobando solas.
    """

    FICHERO = PRINCIPAL

    # --- ayudantes ---

    def _crear_cuenta(self, cliente, cuenta, *, nombre: str = CUENTA, ultimos: str = "5555"):
        respuesta = cliente.post(
            "/api/bancos/cuentas",
            headers=cuenta["cabeceras"],
            json={
                "nombre": nombre,
                "banco": "Banco del Paramo, S.A.",
                "ultimos_digitos": ultimos,
                "propia": True,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def _importar(self, cliente, cuenta, cuenta_id, *, fichero=None, clave_de_reenvio=None):
        fichero = fichero or self.FICHERO
        datos = {"cuenta_id": str(cuenta_id)}
        if clave_de_reenvio:
            datos["clave_de_reenvio"] = clave_de_reenvio
        with fichero.open("rb") as abierto:
            respuesta = cliente.post(
                "/api/bancos/extractos/importar",
                headers=cuenta["cabeceras"],
                files={"fichero": (fichero.name, abierto, "text/csv")},
                data=datos,
            )
        assert respuesta.status_code == 200, respuesta.text
        return respuesta.json()

    def _vista_previa(self, cliente, cuenta, cuenta_id):
        with self.FICHERO.open("rb") as abierto:
            respuesta = cliente.post(
                "/api/bancos/extractos/vista-previa",
                headers=cuenta["cabeceras"],
                files={"fichero": (self.FICHERO.name, abierto, "text/csv")},
                data={"cuenta_id": str(cuenta_id)},
            )
        assert respuesta.status_code == 200, respuesta.text
        return respuesta.json()

    def _una_factura_nuestra(self, cliente, cuenta, importe: str):
        """Una entrega y su factura: lo que hace que haya un papel al que apuntar dinero."""
        campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        venta = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "comercializada",
                "fecha": "2026-06-05",
                "producto": "Trigo blando",
                "cantidad": 1000,
                "unidad": "kg",
                "comprador": "Cooperativa Agricola Ejemplo",
                "importe": importe,
            },
        )
        assert venta.status_code == 201, venta.text
        factura = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={
                "fecha": "2026-06-10",
                "cliente": "Cooperativa Agricola Ejemplo",
                "entregas": [venta.json()["id"]],
            },
        )
        assert factura.status_code == 201, factura.text
        return factura.json()

    def _el_movimiento(self, cliente, cuenta, texto: str):
        items = cliente.get(
            f"/api/bancos/movimientos?texto={texto}", headers=cuenta["cabeceras"]
        ).json()["items"]
        assert items, f"no encuentro ningún movimiento con «{texto}»"
        return items[0]

    # --- el recorrido ---

    def test_la_vista_previa_lee_y_no_guarda_nada(self, cliente, cuenta):
        cuenta_bancaria = self._crear_cuenta(cliente, cuenta)
        vista = self._vista_previa(cliente, cuenta, cuenta_bancaria["id"])
        assert len(vista["movimientos"]) == 7
        assert vista["nuevas"] == 7
        assert vista["resumen"]["sin_importe"] == 1
        assert vista["formato_de_fecha"] == "d/m/Y"
        # Y no ha guardado nada: leer no es apuntar.
        assert cliente.get("/api/bancos/movimientos", headers=cuenta["cabeceras"]).json()["total"] == 0

    def test_el_recorrido_entero_sin_duplicar_ni_un_movimiento(self, cliente, cuenta):
        cuenta_bancaria = self._crear_cuenta(cliente, cuenta)
        primera = self._importar(cliente, cuenta, cuenta_bancaria["id"], clave_de_reenvio="subida-1")
        assert primera["creados"] == 7
        assert primera["repetidos"] == 0

        # El mismo fichero otra vez: no se añade nada y se dice.
        segunda = self._importar(cliente, cuenta, cuenta_bancaria["id"])
        assert segunda["creados"] == 0
        assert segunda["repetidos"] == 7
        assert segunda["el_fichero_ya_estaba"] is True

        # Y reenviar la misma subida (el móvil sin cobertura) devuelve lo de antes, sin apuntar nada.
        reenvio = self._importar(
            cliente, cuenta, cuenta_bancaria["id"], clave_de_reenvio="subida-1"
        )
        assert reenvio["ya_estaba"] is True
        assert reenvio["creados"] == 7  # lo que hizo la primera vez

        listado = cliente.get(
            f"/api/bancos/movimientos?cuenta_id={cuenta_bancaria['id']}",
            headers=cuenta["cabeceras"],
        ).json()
        assert listado["total"] == 7
        assert listado["agregados"]["importes_que_no_constan"] == 1

    def test_en_el_csv_lo_que_no_consta_sale_en_blanco(self, cliente, cuenta):
        cuenta_bancaria = self._crear_cuenta(cliente, cuenta)
        self._importar(cliente, cuenta, cuenta_bancaria["id"])
        respuesta = cliente.get("/api/bancos/movimientos.csv", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200
        la_del_importe_desconocido = [
            linea for linea in respuesta.text.splitlines() if "ANOTACION SIN IMPORTE" in linea
        ][0]
        assert la_del_importe_desconocido.split(";")[4] == ""
        assert "0,00" not in la_del_importe_desconocido

    def test_un_pago_parcial_y_deshacerlo_deja_todo_como_estaba(self, cliente, cuenta, db_sesion):
        """El caso A06 con un movimiento del banco: factura de 1.205,40 y un pago de 500."""
        from app import models as modelos

        cuenta_bancaria = self._crear_cuenta(cliente, cuenta)
        self._importar(cliente, cuenta, cuenta_bancaria["id"])
        self._una_factura_nuestra(cliente, cuenta, "1205.40")
        movimiento = self._el_movimiento(cliente, cuenta, "COOPERATIVA")

        pendientes = cliente.get("/api/bancos/pendientes", headers=cuenta["cabeceras"]).json()
        papel = next(p for p in pendientes if p["clase"] == extractos.FACTURA_EMITIDA)
        assert papel["pendiente"] == "1205.40"

        # Lo que el programa propone, sin que se lo pidan.
        propuestas = cliente.get(
            f"/api/bancos/movimientos/{movimiento['id']}/propuestas", headers=cuenta["cabeceras"]
        ).json()
        assert propuestas["propuestas"], "no propone nada para un cobro que cuadra exacto"
        assert propuestas["propuestas"][0]["tipo"] == extractos.PROPUESTA_EXACTA
        assert propuestas["propuestas"][0]["porque"], "una propuesta sin motivo no se puede revisar"
        # Y proponer no apunta nada.
        assert (
            cliente.get(
                f"/api/bancos/movimientos/{movimiento['id']}/propuestas", headers=cuenta["cabeceras"]
            ).json()["movimiento"]["estado"]
            == extractos.SIN_CONCILIAR
        )

        def cuantas(tabla) -> int:
            return db_sesion.query(tabla).count()

        antes = (cuantas(modelos.Factura), cuantas(modelos.Cobro), cuantas(modelos.FacturaEmitida))

        # Se apunta medio pago.
        conciliado = cliente.post(
            f"/api/bancos/movimientos/{movimiento['id']}/conciliar",
            headers=cuenta["cabeceras"],
            json={
                "imputaciones": [
                    {"clase": papel["clase"], "documento_id": papel["documento_id"], "importe": "500.00"}
                ]
            },
        )
        assert conciliado.status_code == 200, conciliado.text
        estado = conciliado.json()["movimiento"]
        assert estado["estado"] == extractos.CONCILIADO_EN_PARTE
        assert str(estado["por_conciliar"]) == "705.40"
        # **Conciliar no ha creado ningún documento.**
        assert antes == (
            cuantas(modelos.Factura),
            cuantas(modelos.Cobro),
            cuantas(modelos.FacturaEmitida),
        ), "conciliar ha creado un documento: eso es contar el dinero dos veces"
        # Y la factura queda a medias, con lo que le falta dicho.
        pendiente = cliente.get("/api/bancos/pendientes", headers=cuenta["cabeceras"]).json()[0]
        assert pendiente["pendiente"] == "705.40"

        # Se deshace: el movimiento sigue y el papel vuelve a deber lo de antes.
        deshecho = cliente.post(
            f"/api/bancos/movimientos/{movimiento['id']}/desconciliar",
            headers=cuenta["cabeceras"],
            json={},
        )
        assert deshecho.status_code == 200, deshecho.text
        assert deshecho.json()["movimiento"]["id"] == movimiento["id"]
        assert deshecho.json()["movimiento"]["importe"] == movimiento["importe"]
        assert str(deshecho.json()["movimiento"]["imputado"]) == "0.00"
        assert (
            cliente.get("/api/bancos/pendientes", headers=cuenta["cabeceras"]).json()[0]["pendiente"]
            == "1205.40"
        )

        # Y queda el rastro: quién concilió, quién deshizo, cuándo y con qué motivo.
        rastro = (
            db_sesion.query(modelos.Auditoria)
            .filter(
                modelos.Auditoria.accion.in_(
                    ["conciliar_movimiento", "desconciliar_movimiento"]
                )
            )
            .all()
        )
        assert len(rastro) == 2
        assert all(fila.usuario_id is not None for fila in rastro)
        la_conciliacion = db_sesion.query(models.ConciliacionDeMovimiento).one()
        assert la_conciliacion.anulada is True
        assert la_conciliacion.deshecha_en is not None
        assert la_conciliacion.deshecha_por_usuario_id is not None
        assert la_conciliacion.motivo_del_deshacer
        # Y el vínculo deshecho no se borra: se queda con lo que se deshizo.
        assert la_conciliacion.importe == Decimal("500.00")

    def test_lo_que_se_propone_nunca_es_dinero_ya_apuntado(self, cliente, cuenta):
        """Un botón propuesto tiene que poder pulsarse, y nunca dos veces sobre el mismo dinero.

        Es el recorrido 3 tal y como lo hace un agricultor: revisa lo que el programa propone, lo apunta,
        vuelve a mirar y **no puede encontrarse la misma propuesta otra vez**. Si se encontrara, el botón
        «Apuntar esta» llevaría a un error del servidor —porque el dinero de ese movimiento ya está
        apuntado— y ese es el fallo que este test fija: se propone **con lo que le queda al movimiento**,
        y cuando no le queda nada se dice, en vez de ofrecer lo imposible.
        """
        cuenta_bancaria = self._crear_cuenta(cliente, cuenta)
        self._importar(cliente, cuenta, cuenta_bancaria["id"])
        self._una_factura_nuestra(cliente, cuenta, "1205.40")
        movimiento = self._el_movimiento(cliente, cuenta, "COOPERATIVA")
        pendientes = cliente.get("/api/bancos/pendientes", headers=cuenta["cabeceras"]).json()
        papel = next(p for p in pendientes if p["clase"] == extractos.FACTURA_EMITIDA)

        # Se apunta medio pago, a mano.
        medio = cliente.post(
            f"/api/bancos/movimientos/{movimiento['id']}/conciliar",
            headers=cuenta["cabeceras"],
            json={
                "imputaciones": [
                    {"clase": papel["clase"], "documento_id": papel["documento_id"], "importe": "500.00"}
                ]
            },
        )
        assert medio.status_code == 200, medio.text

        # Lo que queda del movimiento: 705,40. Y eso —ni más— es lo que se puede proponer.
        quedan = cliente.get(
            f"/api/bancos/movimientos/{movimiento['id']}/propuestas", headers=cuenta["cabeceras"]
        ).json()
        assert quedan["por_conciliar"] == "705.40"
        assert quedan["ya_apuntado"] is False
        assert quedan["texto_ya_apuntado"] is None
        totales = {propuesta["total"] for propuesta in quedan["propuestas"]}
        assert totales <= {"705.40"}, f"propone apuntar más de lo que queda: {sorted(totales)}"

        # Y la propuesta que queda **se puede pulsar**: es exactamente lo que manda la pantalla. Aquí
        # cuadra exacta, porque a la factura le faltan justo los 705,40 que le quedan al movimiento.
        la_que_queda = quedan["propuestas"][0]
        assert la_que_queda["tipo"] == extractos.PROPUESTA_EXACTA
        assert la_que_queda["total"] == "705.40"
        segundo = cliente.post(
            f"/api/bancos/movimientos/{movimiento['id']}/conciliar",
            headers=cuenta["cabeceras"],
            json={"imputaciones": la_que_queda["imputaciones"]},
        )
        assert segundo.status_code == 200, (
            "la propuesta que enseña la pantalla no se puede apuntar: " + segundo.text
        )
        assert segundo.json()["movimiento"]["estado"] == extractos.CONCILIADO
        assert str(segundo.json()["movimiento"]["imputado"]) == "1205.40"

        # Ya está apuntado entero: ni propuestas, ni un botón que no pueda funcionar.
        entero = cliente.get(
            f"/api/bancos/movimientos/{movimiento['id']}/propuestas", headers=cuenta["cabeceras"]
        ).json()
        assert entero["ya_apuntado"] is True
        assert entero["propuestas"] == [], "con el movimiento apuntado entero no se propone nada"
        assert entero["texto_ya_apuntado"], "y se dice por qué no hay nada que proponer"
        assert "deshaz" in entero["texto_ya_apuntado"].lower(), "la frase tiene que decir qué hacer"
        assert entero["por_conciliar"] == "0.00"

        # Y el papel sigue esperando lo suyo: 1205,40 - 1205,40 = 0, pero la factura no se ha tocado.
        pendiente = cliente.get("/api/bancos/pendientes", headers=cuenta["cabeceras"]).json()
        assert all(p["documento_id"] != papel["documento_id"] for p in pendiente), (
            "una factura ya saldada no es un pendiente"
        )

    def test_un_movimiento_puede_saldar_dos_papeles_a_la_vez(self, cliente, cuenta):
        """Muchos a muchos: el contrato lo pide para «pagos parciales o agrupados»."""
        cuenta_bancaria = self._crear_cuenta(cliente, cuenta)
        self._importar(cliente, cuenta, cuenta_bancaria["id"])
        primera = self._una_factura_nuestra(cliente, cuenta, "300.00")
        segunda = self._una_factura_nuestra(cliente, cuenta, "405.40")
        movimiento = self._el_movimiento(cliente, cuenta, "COOPERATIVA")

        respuesta = cliente.post(
            f"/api/bancos/movimientos/{movimiento['id']}/conciliar",
            headers=cuenta["cabeceras"],
            json={
                "imputaciones": [
                    {"clase": extractos.FACTURA_EMITIDA, "documento_id": primera["id"], "importe": "300.00"},
                    {"clase": extractos.FACTURA_EMITIDA, "documento_id": segunda["id"], "importe": "405.40"},
                ]
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        hechas = respuesta.json()["conciliaciones"]
        assert len(hechas) == 2
        # **Los importes viajan como texto decimal, y eso es el contrato de la casa** (`dinero.a_texto`):
        # un `float` en el navegador haría que el total de la pantalla dejara de coincidir con el de la
        # base por céntimos. Así que se suman convirtiéndolos, y con el cero también `Decimal` para que
        # `sum` no empiece con un entero. Esta línea estaba escrita como `sum(h["importe"] …)` y **no se
        # había ejecutado nunca**: era una de las pruebas que se saltaban hasta integrar las tablas.
        assert sum((Decimal(h["importe"]) for h in hechas), Decimal("0")) == Decimal("705.40")
        assert respuesta.json()["movimiento"]["estado"] == extractos.CONCILIADO_EN_PARTE
        # Y los dos papeles quedan saldados.
        pendientes = cliente.get("/api/bancos/pendientes", headers=cuenta["cabeceras"]).json()
        assert pendientes == []

    def test_el_mismo_dinero_no_se_puede_apuntar_dos_veces_al_mismo_papel(self, cliente, cuenta):
        cuenta_bancaria = self._crear_cuenta(cliente, cuenta)
        self._importar(cliente, cuenta, cuenta_bancaria["id"])
        factura = self._una_factura_nuestra(cliente, cuenta, "1205.40")
        movimiento = self._el_movimiento(cliente, cuenta, "COOPERATIVA")
        cuerpo = {
            "imputaciones": [
                {"clase": extractos.FACTURA_EMITIDA, "documento_id": factura["id"], "importe": "300.00"},
                {"clase": extractos.FACTURA_EMITIDA, "documento_id": factura["id"], "importe": "300.00"},
            ]
        }
        respuesta = cliente.post(
            f"/api/bancos/movimientos/{movimiento['id']}/conciliar",
            headers=cuenta["cabeceras"],
            json=cuerpo,
        )
        assert respuesta.status_code == 422, respuesta.text

    def test_un_traspaso_entre_cuentas_propias_se_ata_y_no_cuenta(self, cliente, cuenta):
        """El caso A07, por la API."""
        principal = self._crear_cuenta(cliente, cuenta)
        ahorro = self._crear_cuenta(cliente, cuenta, nombre=OTRA_CUENTA, ultimos="4444")
        self._importar(cliente, cuenta, principal["id"])
        self._importar(cliente, cuenta, ahorro["id"], fichero=AHORRO)
        sale = self._el_movimiento(cliente, cuenta, "TRASPASO A CUENTA")
        entra = self._el_movimiento(cliente, cuenta, "TRASPASO DESDE LA CUENTA")
        atado = cliente.post(
            f"/api/bancos/movimientos/{sale['id']}/traspaso",
            headers=cuenta["cabeceras"],
            json={"otro_movimiento_id": entra["id"]},
        )
        assert atado.status_code == 200, atado.text
        assert atado.json()["movimiento"]["es_traspaso_propio"] is True
        assert atado.json()["movimiento"]["pareja_de_traspaso_id"] == entra["id"]
        # Y se puede deshacer: vuelven a contar cada uno por su lado.
        quitado = cliente.post(
            f"/api/bancos/movimientos/{sale['id']}/traspaso",
            headers=cuenta["cabeceras"],
            json={"otro_movimiento_id": None},
        )
        assert quitado.status_code == 200, quitado.text
        assert quitado.json()["movimiento"]["es_traspaso_propio"] is False

    def test_corregir_el_importe_que_no_consta(self, cliente, cuenta):
        """Y para el importe que no consta, la puerta que lo arregla."""
        cuenta_bancaria = self._crear_cuenta(cliente, cuenta)
        self._importar(cliente, cuenta, cuenta_bancaria["id"])
        movimiento = self._el_movimiento(cliente, cuenta, "SIN IMPORTE")
        assert movimiento["importe"] is None
        assert movimiento["se_puede_conciliar"] is False

        # Un importe sin decir si entra o sale no vale: un movimiento así no se puede sumar.
        sin_signo = cliente.put(
            f"/api/bancos/movimientos/{movimiento['id']}",
            headers=cuenta["cabeceras"],
            json={"importe": "18.50"},
        )
        assert sin_signo.status_code == 422, sin_signo.text

        corregido = cliente.put(
            f"/api/bancos/movimientos/{movimiento['id']}",
            headers=cuenta["cabeceras"],
            json={"importe": "18.50", "signo": extractos.SALE, "motivo": "Lo he mirado en el recibo"},
        )
        assert corregido.status_code == 200, corregido.text
        assert corregido.json()["importe"] == "18.50"
        assert corregido.json()["se_puede_conciliar"] is True

    def test_el_extracto_de_una_finca_no_se_ve_desde_otra(self, cliente, cuenta, crear_cuenta):
        cuenta_bancaria = self._crear_cuenta(cliente, cuenta)
        self._importar(cliente, cuenta, cuenta_bancaria["id"])
        movimiento = self._el_movimiento(cliente, cuenta, "COOPERATIVA")
        otra = crear_cuenta("otro@ejemplo.test")

        assert (
            cliente.put(
                f"/api/bancos/cuentas/{cuenta_bancaria['id']}",
                headers=otra["cabeceras"],
                json={"nombre": "Esta no es mía"},
            ).status_code
            == 404
        )
        assert cliente.get("/api/bancos/movimientos", headers=otra["cabeceras"]).json()["total"] == 0
        assert (
            cliente.post(
                f"/api/bancos/movimientos/{movimiento['id']}/desconciliar",
                headers=otra["cabeceras"],
                json={},
            ).status_code
            == 404
        )
        assert (
            cliente.get(
                f"/api/bancos/movimientos/{movimiento['id']}/propuestas", headers=otra["cabeceras"]
            ).status_code
            == 404
        )
        assert cliente.get("/api/bancos/pendientes", headers=otra["cabeceras"]).json() == []
