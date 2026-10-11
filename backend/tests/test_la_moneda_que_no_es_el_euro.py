"""CRM-02: una moneda que no es el euro **no se apunta como si fueran euros**.

POR QUÉ EXISTE ESTE FICHERO. Es el criterio de aceptación que **no cumplía**: «una moneda distinta no se
suma sin conversión acreditada». Y el hueco se **reprodujo midiendo**, en el camino que de verdad hacen los
bancos: el importe limpio en su columna y **la divisa en su propia columna** (`Fecha;Concepto;Importe;Divisa`
con `1.000,00;USD`). Con un perfil que declara «sin signo el dinero entra» —una configuración normal— esa
línea se apuntaba como **1.000,00 €**, y la columna de la divisa se ignoraba sin decir nada.

Lo que se hace ahora no es convertir —no hay de dónde sacar el cambio, y `app/dinero.py` dice de sí mismo que
**no convierte** monedas—: es **rechazar la fila con su motivo**, que es la misma decisión que este programa ya
toma con las letras `C`/`D` del signo, que se rechazan a propósito porque significan cosas contrarias según el
banco. **Se rechaza lo que se reconoce, y no se adivina lo que no**: un importe sin marca se lee como euros,
que es lo que es en una cuenta española.

Y una lección de método que este fichero deja escrita: **mi primer intento miraba la casilla del importe**, y
ahí una línea con `USD` pegado ya se rechazaba —con un motivo malo, «no se ha podido leer», pero se
rechazaba—. El defecto de verdad estaba en la **columna** de la divisa, y solo se vio midiendo el caso con
perfil. Las dos cosas están cubiertas: la casilla y la columna.
"""

from __future__ import annotations

from decimal import Decimal

from app import extractos

CUENTA = "Cuenta principal"


def _perfil():
    """El perfil que declara lo que el fichero no dice: sin signo, el dinero entra (y las fechas, d/m/Y)."""
    return extractos.PerfilDeFormato(
        delimitador=";",
        decimal=",",
        formato_de_fecha="d/m/Y",
        estilo_del_signo=extractos.SIGNO_EN_EL_IMPORTE,
        sin_signo_quiere_decir=extractos.ENTRA,
    )


def _lee(texto: str, perfil=None):
    return extractos.lee_extracto(
        extractos.lee_el_texto(texto.encode("utf-8")),
        perfil,
        cuenta=CUENTA,
        explotacion_id=1,
    )


class TestLaColumnaDeLaDivisa:
    """El camino por el que se colaba: la divisa en su propia columna y el importe limpio."""

    CON_DIVISA = (
        "Fecha;Concepto;Importe;Divisa\n"
        "14/06/2026;COBRO CLIENTE USA;1.000,00;USD\n"
        "15/06/2026;COBRO CLIENTE;500,00;EUR\n"
    )

    def test_la_linea_en_dolares_se_rechaza_y_la_del_euro_entra(self):
        lectura = _lee(self.CON_DIVISA, _perfil())
        assert [m.importe for m in lectura.movimientos] == [Decimal("500.00")], (
            f"la linea en dolares no puede apuntarse como si fueran euros: "
            f"{[(str(m.importe), m.concepto) for m in lectura.movimientos]}"
        )
        assert [r.motivo for r in lectura.rechazadas] == [extractos.MONEDA_DISTINTA], (
            f"y se rechaza con su motivo: {[(r.numero_de_linea, r.motivo) for r in lectura.rechazadas]}"
        )

    def test_una_divisa_vacia_no_rechaza_la_fila(self):
        """El control: la columna existe pero el banco no pone nada en esa línea. Eso son euros."""
        lectura = _lee(
            "Fecha;Concepto;Importe;Divisa\n14/06/2026;COBRO;500,00;\n", _perfil()
        )
        assert [m.importe for m in lectura.movimientos] == [Decimal("500.00")]
        assert not lectura.rechazadas

    def test_la_columna_se_reconoce_por_su_nombre_y_no_por_su_sitio(self):
        """`Moneda` en medio, `Currency` al final: da igual dónde esté, manda el nombre de la cabecera."""
        lectura = _lee(
            "Fecha;Moneda;Concepto;Importe\n"
            "14/06/2026;USD;COBRO CLIENTE USA;1.000,00\n"
            "15/06/2026;EUR;COBRO CLIENTE;500,00\n",
            _perfil(),
        )
        assert [m.importe for m in lectura.movimientos] == [Decimal("500.00")]
        assert [r.motivo for r in lectura.rechazadas] == [extractos.MONEDA_DISTINTA]


class TestLaMonedaPegadaAlImporte:
    """Y si la divisa viene pegada al número, el motivo es el bueno: «está en otra moneda»."""

    def test_una_casilla_con_dolares_dice_que_es_otra_moneda(self):
        lectura = _lee("Fecha;Concepto;Importe\n14/06/2026;COBRO;1.000,00 USD\n", _perfil())
        assert not lectura.movimientos
        assert [r.motivo for r in lectura.rechazadas] == [extractos.MONEDA_DISTINTA], (
            f"y no un «no se ha podido leer», que no dice al agricultor qué arreglar: "
            f"{[r.motivo for r in lectura.rechazadas]}"
        )

    def test_una_libra_en_el_concepto_no_rechaza_la_fila(self):
        """Se mira el importe y la divisa, **no el concepto**: «libras» ahí es una palabra, no una moneda.

        Sin esta prueba, la lista de marcas podría acabar mirándose en toda la línea y rechazando una entrega
        de 500 libras de peso apuntada en el concepto, que es un dato del negocio y no una divisa.
        """
        lectura = _lee("Fecha;Concepto;Importe\n14/06/2026;ENTREGA 500 LIBRAS DE PESO;120,00\n", _perfil())
        assert [m.importe for m in lectura.movimientos] == [Decimal("120.00")]
        assert not lectura.rechazadas
