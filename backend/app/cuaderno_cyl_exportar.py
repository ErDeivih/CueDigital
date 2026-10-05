"""Escribir el cuaderno de explotación de la Junta con los datos del agricultor.

## Qué hace esto

Coge los datos que el agricultor ya tiene en el cuaderno por dentro (sus parcelas, sus tratamientos,
sus abonos, sus análisis, lo que ha vendido, sus papeles) y **los escribe en el libro de 25 hojas del
cuaderno oficial de Castilla y León**, con los mismos nombres de hoja, las mismas cabeceras y las
mismas columnas que el fichero que descarga del Cuecyl.

Se hace así, y no rellenando su fichero original, por dos motivos:

1. **Su cuaderno lleva sus datos personales.** El fichero que descarga de la Junta tiene su NIF, su
   teléfono y sus tierras, y eso no puede viajar por el programa ni entrar en el repositorio.
2. **La plantilla cambia entre campañas** (el cuaderno de 2024 tenía 23 hojas y el de 2025 y 2026
   tiene 25). Escribiendo nosotros el libro, el programa sigue funcionando con la plantilla que haya:
   lo que se replica es **el contenido y la disposición** que se leyeron de los cuadernos de verdad.

Lo que sale es un fichero que **se puede leer con el propio lector del cuaderno**
(`app/cuaderno_cyl.py`): hay un test que escribe el cuaderno, lo vuelve a leer y comprueba que dice lo
mismo. Es la mejor prueba que se le puede hacer a un escritor de ficheros.

## Y lo más importante: dice lo que falta

`escribe_el_cuaderno` devuelve, además del fichero, un **informe de lo que falta** hoja por hoja: qué
datos pide el cuaderno y no están puestos, y dónde se ponen. Eso es lo que el agricultor necesita para
terminarlo, y es la respuesta a «¿qué datos me hacen falta?»: no una lista inventada, sino **la lista
que sale de comparar el cuaderno oficial con lo que él tiene apuntado**.
"""

from __future__ import annotations

import datetime as dt
import io
from dataclasses import dataclass, field

from openpyxl import Workbook

from . import cuaderno_cyl as lector
from . import models

# Las hojas del cuaderno oficial, en su orden, con el nombre tal y como lo pone la Junta. Se copian
# del cuaderno de verdad: si un día la Junta añade una hoja, se añade aquí y ya está.
HOJAS = [
    "1.1. INF. GRAL",
    "1.2., 1.3. y 1.4. INF. GRAL",
    "2.1. DATOS PARCELAS",
    "2.2. DATOS IDEN. MEDIAMB. P.",
    "3.1. REG. FIT. x P.",
    "3.1. bis REG. FIT. x P. (ASESOR",
    "3.2. REG. USO SEMILLA TRAT.",
    "3.3. REG. TRAT. POSTCOS",
    "3.4. REG. TRAT. ALMACEN",
    "3.5. REG. TRAT. MED.TRANSP",
    "4. REG. ANALISIS",
    "5. REG. COMERC.",
    "6. REG. FERTILIZ",
    "7. DAT. AGROAMB.",
    "7.1 FERTILIZA RM Y AO",
    "7.2 RIEGO RM",
    "8. VIÑEDO CON DOP_IGP",
    "9.1. INF. FERTILIZACIÓN",
    "9.1.1. INF. RIEGO",
    "9.1.2. PLAN ABONADO",
    "9.3.  PRÁCTICA SIEGA SOSTENIBLE",
    "9.4. ISLAS BIODIVERSIDAD",
    "9.5. CUBIERTAS VEGETALES ",
    "9.6. CUBIERTAS INERTES",
    "doc",
]

# El título de cada hoja, para poder decir en el informe «estas cosas faltan en la hoja X» sin que el
# agricultor tenga que abrir el fichero a ver qué es.
TITULOS = {
    "1.1. INF. GRAL": "Datos generales de la explotación",
    "1.2., 1.3. y 1.4. INF. GRAL": "Personas, máquinas y asesor",
    "2.1. DATOS PARCELAS": "Las parcelas",
    "2.2. DATOS IDEN. MEDIAMB. P.": "Datos medioambientales de las parcelas",
    "3.1. REG. FIT. x P.": "Tratamientos de las parcelas",
    "3.1. bis REG. FIT. x P. (ASESOR": "Tratamientos con asesoramiento",
    "3.2. REG. USO SEMILLA TRAT.": "Semilla tratada",
    "3.3. REG. TRAT. POSTCOS": "Tratamientos después de la cosecha",
    "3.4. REG. TRAT. ALMACEN": "Tratamientos de naves y almacenes",
    "3.5. REG. TRAT. MED.TRANSP": "Tratamientos de medios de transporte",
    "4. REG. ANALISIS": "Análisis",
    "5. REG. COMERC.": "Lo que se ha vendido",
    "6. REG. FERTILIZ": "Abonado",
    "7. DAT. AGROAMB.": "Labores, siembra y recolección",
    "7.1 FERTILIZA RM Y AO": "Abonado de las ayudas agroambientales",
    "7.2 RIEGO RM": "Riego de las ayudas agroambientales",
    "8. VIÑEDO CON DOP_IGP": "Viñedo con denominación de origen",
    "9.1. INF. FERTILIZACIÓN": "Abonado de los ecorregímenes",
    "9.1.1. INF. RIEGO": "Riego de los ecorregímenes",
    "9.1.2. PLAN ABONADO": "Plan de abonado",
    "9.3.  PRÁCTICA SIEGA SOSTENIBLE": "Siega sostenible",
    "9.4. ISLAS BIODIVERSIDAD": "Islas de biodiversidad",
    "9.5. CUBIERTAS VEGETALES ": "Cubiertas vegetales",
    "9.6. CUBIERTAS INERTES": "Cubiertas inertes",
    "doc": "Documentación que hay que conservar",
}


# --------------------------------------------------------------------------
# Las hojas que el programa todavía NO rellena, una por una
# --------------------------------------------------------------------------
#
# **Esto es el inventario del cuaderno, y está completo a propósito.** De las 25 hojas, diez se
# escriben solas con los datos del agricultor y las otras quince todavía no. De esas quince no vale
# decir «ya se harán»: hay que decir **qué pide cada una, dónde se apunta ese dato en el programa y
# qué falta para poder escribirla sola**. Un agricultor que entrega un cuaderno con quince hojas en
# blanco tiene que saber exactamente qué le falta, y quien lea esto después tiene que saber por dónde
# seguir.
#
# **Por qué no se rellenan todavía, dicho claro:** para escribir una hoja hace falta conocer **el sitio
# exacto de cada columna** de la hoja oficial (qué va en la B, qué en la C, dónde están las dos filas
# de cabecera). Eso se copió de cuadernos de verdad para las diez hojas que sí se escriben. Para estas
# quince no se tiene, y **no se inventa**: una hoja con las columnas cambiadas de sitio es peor que una
# hoja en blanco, porque parece rellena y está mal. Lo que hace falta está dicho en cada entrada, en
# `que_falta_para_escribirla`.
#
# La entrada de cada hoja tiene:
#   - `que_pide`: lo que pide la hoja, en palabras que se entiendan.
#   - `donde_se_apunta`: dónde se apunta ese dato en este programa (o «todavía no se pregunta»).
#   - `que_falta_para_escribirla`: qué haría falta para que la escriba el programa solo.
#   - `apuntes`: opcional, cuántos apuntes de los que el agricultor ya tiene irían en esa hoja. Sirve
#     para que el informe diga «tienes 3 apuntes que van aquí» en vez de dejarle pensando si los
#     datos están o no están.
HOJAS_QUE_NO_SE_RELLENAN: dict[str, dict] = {
    "2.2. DATOS IDEN. MEDIAMB. P.": {
        "que_pide": "las captaciones de agua para consumo humano y otras zonas señaladas (zonas "
        "protegidas, parques, reservas) que haya dentro de tus tierras",
        "donde_se_apunta": "todavía no se pregunta en el programa",
        "que_falta_para_escribirla": "las columnas oficiales de la hoja y saber el listado de zonas "
        "señaladas de cada término municipal",
    },
    "3.1. bis REG. FIT. x P. (ASESOR": {
        "que_pide": "los tratamientos que ha validado un asesor, con su firma",
        "donde_se_apunta": "el asesor ya se apunta en cada tratamiento, pero no su validación",
        "que_falta_para_escribirla": "las columnas oficiales y preguntar la validación del asesor",
        "apuntes": "tratamientos_con_asesor",
    },
    "3.2. REG. USO SEMILLA TRAT.": {
        "que_pide": "cada vez que siembras semilla que ya venía tratada: de qué lote, con qué "
        "producto, cuándo se trató y si funcionó",
        "donde_se_apunta": "Echar producto → «la semilla ya venía tratada», y en la siembra",
        "que_falta_para_escribirla": "las columnas oficiales de la hoja",
        "apuntes": "tratamientos_de_semilla",
    },
    "3.3. REG. TRAT. POSTCOS": {
        "que_pide": "los tratamientos que se hacen al producto ya recogido",
        "donde_se_apunta": "Echar producto → «al producto ya recogido»",
        "que_falta_para_escribirla": "las columnas oficiales de la hoja",
        "apuntes": "tratamientos_de_postcosecha",
    },
    "3.4. REG. TRAT. ALMACEN": {
        "que_pide": "los tratamientos de las naves y los almacenes",
        "donde_se_apunta": "Echar producto → «en una nave o un almacén»",
        "que_falta_para_escribirla": "las columnas oficiales de la hoja",
        "apuntes": "tratamientos_de_instalaciones",
    },
    "3.5. REG. TRAT. MED.TRANSP": {
        "que_pide": "los tratamientos de los medios de transporte",
        "donde_se_apunta": "todavía no se distingue el transporte de una nave: este programa apunta "
        "los dos como «en una nave o un almacén»",
        "que_falta_para_escribirla": "las columnas oficiales y poder decir que el sitio tratado era "
        "un medio de transporte",
    },
    "7.1 FERTILIZA RM Y AO": {
        "que_pide": "el abonado de las ayudas agroambientales (agricultura ecológica y similares)",
        "donde_se_apunta": "el abono se apunta en «He abonado», pero no se dice a qué ayuda va",
        "que_falta_para_escribirla": "las columnas oficiales y saber a qué ayuda va cada abonado",
        "apuntes": "abonados",
    },
    "7.2 RIEGO RM": {
        "que_pide": "el riego de las ayudas agroambientales",
        "donde_se_apunta": "el riego se apunta en «He hecho un trabajo» → regar",
        "que_falta_para_escribirla": "las columnas oficiales y saber a qué ayuda va cada riego",
        "apuntes": "riegos",
    },
    "8. VIÑEDO CON DOP_IGP": {
        "que_pide": "los datos del viñedo que está en una denominación de origen o una indicación "
        "geográfica protegida",
        "donde_se_apunta": "todavía no se pregunta nada de viñedo en el programa",
        "que_falta_para_escribirla": "las columnas oficiales y las preguntas del viñedo (variedad, "
        "marco de plantación, conducción)",
    },
    "9.1. INF. FERTILIZACIÓN": {
        "que_pide": "el abonado de las tierras que cobran ecorregímenes, con las fechas y el tipo de "
        "abono, tal y como lo pide la ayuda",
        "donde_se_apunta": "He abonado (el abono ya se apunta ahí)",
        "que_falta_para_escribirla": "las columnas oficiales de la hoja",
        "apuntes": "abonados",
    },
    "9.1.1. INF. RIEGO": {
        "que_pide": "el riego de las tierras que cobran ecorregímenes: sistema de riego, agua gastada, "
        "de dónde sale el agua y el contador",
        "donde_se_apunta": "He hecho un trabajo → regar (ahí se apunta el agua, de dónde viene y el "
        "contador)",
        "que_falta_para_escribirla": "las columnas oficiales de la hoja",
        "apuntes": "riegos",
    },
    "9.3.  PRÁCTICA SIEGA SOSTENIBLE": {
        "que_pide": "la siega sostenible: cuándo se segó, a qué altura y qué se hizo con los restos",
        "donde_se_apunta": "He hecho un trabajo (los restos se apuntan en la labor)",
        "que_falta_para_escribirla": "las columnas oficiales de la hoja",
        "apuntes": "labores_de_siega",
    },
    "9.4. ISLAS BIODIVERSIDAD": {
        "que_pide": "las islas de biodiversidad: qué trozo se ha dejado sin sembrar o sin tratar y "
        "dónde está",
        "donde_se_apunta": "todavía no se pregunta en el programa",
        "que_falta_para_escribirla": "las columnas oficiales y preguntar a qué trozo se refiere",
    },
    "9.5. CUBIERTAS VEGETALES ": {
        "que_pide": "las cubiertas vegetales: cuándo se establecieron, de qué tipo y cuánto miden, y "
        "qué se ha hecho sobre ellas",
        "donde_se_apunta": "He hecho un trabajo (la cubierta se apunta en la labor)",
        "que_falta_para_escribirla": "las columnas oficiales de la hoja",
        "apuntes": "labores_con_cubierta",
    },
    "9.6. CUBIERTAS INERTES": {
        "que_pide": "las cubiertas inertes (restos de poda o desbroce depositados en el suelo)",
        "donde_se_apunta": "He hecho un trabajo (los restos de poda y desbroce se apuntan ahí)",
        "que_falta_para_escribirla": "las columnas oficiales de la hoja",
        "apuntes": "labores_con_restos",
    },
}

# Las hojas que **sí** se escriben solas. Se declara aquí, y no se deduce del código, para que una
# prueba pueda comprobar que el cuaderno no tiene ninguna hoja olvidada: cada una de las 25 tiene que
# estar o en esta lista o en la de arriba.
HOJAS_QUE_SE_RELLENAN = (
    "1.1. INF. GRAL",
    "1.2., 1.3. y 1.4. INF. GRAL",
    "2.1. DATOS PARCELAS",
    "3.1. REG. FIT. x P.",
    "4. REG. ANALISIS",
    "5. REG. COMERC.",
    "6. REG. FERTILIZ",
    "7. DAT. AGROAMB.",
    "9.1.2. PLAN ABONADO",
    "doc",
)


# Cómo se llama, en el informe, lo que se cuenta de cada hoja. El nombre va en singular y plural
# porque el informe lo lee el agricultor y «1 apuntes» canta.
COMO_SE_LLAMAN = {
    "tratamientos_con_asesor": ("tratamiento con asesor", "tratamientos con asesor"),
    "tratamientos_de_semilla": ("apunte de semilla tratada", "apuntes de semilla tratada"),
    "tratamientos_de_postcosecha": ("tratamiento de postcosecha", "tratamientos de postcosecha"),
    "tratamientos_de_instalaciones": ("tratamiento de nave o almacén", "tratamientos de nave o almacén"),
    "abonados": ("abonado", "abonados"),
    "riegos": ("riego", "riegos"),
    "labores_de_siega": ("labor de siega o cosecha", "labores de siega o cosecha"),
    "labores_con_cubierta": ("labor con cubierta", "labores con cubierta"),
    "labores_con_restos": ("labor con restos en el suelo", "labores con restos en el suelo"),
}

# La dirección oficial del cuaderno de la Junta: es donde el agricultor completa a mano lo que este
# programa todavía no escribe, y donde puede descargarse la plantilla. Va aquí, y no en un texto
# suelto de cada hoja, para que si algún día cambia se cambie en un solo sitio.
DIRECCION_DEL_CUADERNO_DE_LA_JUNTA = "https://particulares.ayg.jcyl.es"


def _cuantos_apuntes(db, explotacion, campana) -> dict[str, int]:
    """Cuenta los apuntes del agricultor que irían en cada una de las hojas que no se escriben solas.

    Esto no es un adorno: sin esto, el informe dice «esta hoja no se rellena sola» y el agricultor no
    sabe si el problema es que le faltan datos o que el programa no los escribe. Con el número
    delante, se sabe: **los datos están apuntados**, lo que falta es la hoja.
    """
    from sqlalchemy import func, select

    def cuantos(modelo, *condiciones) -> int:
        consulta = select(func.count()).select_from(modelo).where(
            modelo.explotacion_id == explotacion.id,
            *condiciones,
        )
        return int(db.scalar(consulta) or 0)

    de_la_campana = models.TratamientoFitosanitario.campana_id == (campana.id if campana else None)

    tratamientos = {
        tipo: cuantos(
            models.TratamientoFitosanitario,
            models.TratamientoFitosanitario.tipo == tipo,
            models.TratamientoFitosanitario.anulado.is_(False),
            de_la_campana,
        )
        for tipo in ("semilla_tratada", "postcosecha", "instalaciones")
    }
    labores = {
        tipo: cuantos(
            models.Labor,
            models.Labor.tipo == tipo,
            models.Labor.anulado.is_(False),
            models.Labor.campana_id == (campana.id if campana else None),
        )
        for tipo in ("riego", "cosecha", "cubierta")
    }

    return {
        "tratamientos_con_asesor": cuantos(
            models.TratamientoFitosanitario,
            models.TratamientoFitosanitario.asesor_id.is_not(None),
            models.TratamientoFitosanitario.anulado.is_(False),
            de_la_campana,
        ),
        "tratamientos_de_semilla": tratamientos["semilla_tratada"],
        "tratamientos_de_postcosecha": tratamientos["postcosecha"],
        "tratamientos_de_instalaciones": tratamientos["instalaciones"],
        "abonados": cuantos(
            models.RegistroFertilizacion,
            models.RegistroFertilizacion.anulado.is_(False),
            models.RegistroFertilizacion.campana_id == (campana.id if campana else None),
        ),
        "riegos": labores["riego"],
        "labores_de_siega": labores["cosecha"],
        "labores_con_cubierta": (
            labores["cubierta"]
            + cuantos(
                models.Labor,
                models.Labor.tipo_cobertura.is_not(None),
                models.Labor.anulado.is_(False),
                models.Labor.campana_id == (campana.id if campana else None),
            )
        ),
        "labores_con_restos": cuantos(
            models.Labor,
            (models.Labor.restos_poda_depositados.is_(True))
            | (models.Labor.restos_desbroce_depositados.is_(True)),
            models.Labor.anulado.is_(False),
            models.Labor.campana_id == (campana.id if campana else None),
        ),
    }


def _lo_que_falta_en_una_hoja_que_no_se_escribe(nombre: str, apunte: dict, cuantos: dict) -> Falta:
    """Arma la línea del informe para una hoja que el programa todavía no rellena."""
    cuenta = apunte.get("apuntes")
    cuantos_apuntes = cuantos.get(cuenta, 0) if cuenta else 0

    que_falta = (
        f"esta hoja pide {apunte['que_pide']}, y el programa todavía no la escribe sola. "
        f"Lo que falta para poder escribirla: {apunte['que_falta_para_escribirla']}"
    )
    if cuantos_apuntes:
        singular, plural = COMO_SE_LLAMAN[cuenta]
        como = singular if cuantos_apuntes == 1 else plural
        que_falta += (
            f". Los datos ya están en el programa: tienes {cuantos_apuntes} {como}, "
            f"en {apunte['donde_se_apunta']}"
        )
    elif apunte["donde_se_apunta"].startswith("todavía no"):
        que_falta += f". {apunte['donde_se_apunta'].capitalize()}"

    return Falta(
        hoja=nombre,
        que_falta=que_falta,
        donde_se_pone=(
            f"{apunte['donde_se_apunta']}, y se termina a mano en esta hoja del fichero "
            f"(o en el cuaderno de la Junta: {DIRECCION_DEL_CUADERNO_DE_LA_JUNTA})"
        ),
    )


@dataclass
class Falta:
    """Un dato que pide el cuaderno y no está puesto, con dónde se pone."""
    hoja: str
    que_falta: str
    donde_se_pone: str

    def como_dict(self) -> dict:
        return {"hoja": self.hoja, "que_falta": self.que_falta, "donde_se_pone": self.donde_se_pone}


@dataclass
class CuadernoEscrito:
    """El fichero y el informe de lo que falta."""

    contenido: bytes = b""
    anio: int | None = None
    filas_por_hoja: dict[str, int] = field(default_factory=dict)
    faltan: list[Falta] = field(default_factory=list)

    @property
    def hojas_con_datos(self) -> int:
        return sum(1 for cuantas in self.filas_por_hoja.values() if cuantas)

    def resumen(self) -> dict:
        return {
            "anio": self.anio,
            "hojas": len(HOJAS),
            "hojas_con_datos": self.hojas_con_datos,
            "filas": sum(self.filas_por_hoja.values()),
            "cuantas_faltan": len(self.faltan),
            "faltan": [falta.como_dict() for falta in self.faltan],
        }


# --------------------------------------------------------------------------
# Utilidades de escritura
# --------------------------------------------------------------------------


def _texto(valor) -> str:
    """Un valor para meter en una celda, sin dejar que un `None` se convierta en «None»."""
    if valor is None:
        return ""
    if isinstance(valor, dt.date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


def _numero(valor) -> float | None:
    return None if valor is None else float(valor)


def _riquezas(abono) -> str:
    """La casilla «Riqueza N/P/K» del cuaderno de la Junta: los tres números, o **en blanco**.

    En blanco cuando no consta la composición de ese abono (A6 de `docs/T02_VALORES_POR_DEFECTO.md`).
    Escribir «0/0/0» ahí sería rellenar con ceros lo que nadie ha declarado, que es exactamente lo
    que el propio volcado dice que no se hace en ningún otro sitio. Si solo falta uno de los tres,
    la casilla entera va en blanco: la columna es un solo dato (tres números juntos) y medio dato no
    es un dato. Quien lo mire lo verá declarado en la lista de lo que falta de esa hoja.
    """
    riquezas = (abono.riqueza_n, abono.riqueza_p, abono.riqueza_k)
    if any(valor is None for valor in riquezas):
        return ""
    return "/".join(f"{valor:g}" for valor in riquezas)


def _referencia_de_la_parcela(parcela: models.Parcela) -> str:
    """La referencia SIGPAC como la escribe el cuaderno: los siete números."""
    if parcela.ref_sigpac:
        return parcela.ref_sigpac
    partes = (
        parcela.agregado or 0,
        parcela.zona or 0,
        parcela.poligono,
        parcela.numero_parcela,
        parcela.numero_recinto,
    )
    if any(parte is None for parte in partes):
        return ""
    return (
        f"37-{parcela.codigo_ine[-3:] if parcela.codigo_ine else '0'}-{partes[0]}-{partes[1]}"
        f"-{partes[2]}-{partes[3]}-{partes[4]}"
    )


class _Escritor:
    """Escribe en las hojas y va apuntando lo que falta.

    Se lleva la cuenta de las filas de cada hoja para poder decir en el informe «en esta hoja hay 12
    líneas» y, sobre todo, para saber qué hojas se quedan **vacías**: una hoja vacía en un cuaderno
    que se entrega es lo primero que mira quien lo revisa.
    """

    def __init__(self) -> None:
        self.libro = Workbook()
        self.libro.remove(self.libro.active)
        for nombre in HOJAS:
            hoja = self.libro.create_sheet(nombre)
            # El título de la hoja, en su sitio (las oficiales lo llevan arriba a la izquierda).
            hoja["B2"] = TITULOS.get(nombre, nombre)
        self.filas: dict[str, int] = {nombre: 0 for nombre in HOJAS}
        self.faltan: list[Falta] = []

    def hoja(self, nombre: str):
        return self.libro[nombre]

    def escribe(self, nombre: str, fila: int, columna: str, valor) -> None:
        self.hoja(nombre)[f"{columna}{fila}"] = _texto(valor)

    def escribe_fila(self, nombre: str, fila: int, columnas: dict[str, object]) -> None:
        for columna, valor in columnas.items():
            self.escribe(nombre, fila, columna, valor)

    def anota(self, nombre: str) -> None:
        """Suma una línea escrita en una hoja."""
        self.filas[nombre] = self.filas.get(nombre, 0) + 1

    def falta(self, hoja: str, que_falta: str, donde_se_pone: str) -> None:
        self.faltan.append(Falta(hoja=hoja, que_falta=que_falta, donde_se_pone=donde_se_pone))


# --------------------------------------------------------------------------
# Las hojas
# --------------------------------------------------------------------------


def _hoja_1_1(escritor: _Escritor, explotacion: models.Explotacion) -> None:
    """Datos generales de la explotación: la portada del cuaderno."""
    hoja = escritor.hoja("1.1. INF. GRAL")
    hoja["B6"] = "1.1 DATOS GENERALES DE LA EXPLOTACIÓN"
    situacion = {
        "NOMBRE Y APELLIDOS O RAZÓN SOCIAL:": ("B", 7, "G", explotacion.nombre),
        "NIF:": ("Q", 7, "R", explotacion.nif),
        "Nº Registro de Explotaciones Nacional:": ("B", 8, "F", explotacion.registro_nacional),
        "Nº Registro de Explotaciones Autonómico:": (
            "K", 8, "P", explotacion.registro_autonomico,
        ),
        "Dirección:": ("B", 9, "C", explotacion.direccion),
        "Localidad:": ("I", 9, "J", explotacion.localidad),
        "C.Postal:": ("O", 9, "P", explotacion.codigo_postal),
        "Provincia:": ("Q", 9, "R", explotacion.provincia),
        "Telófono fijo:": ("B", 10, "D", ""),
        "Telófono móvil:": ("F", 10, "H", explotacion.telefono),
        "e-mail:": ("J", 10, "K", explotacion.correo),
    }
    for etiqueta, (columna, fila, columna_valor, valor) in situacion.items():
        hoja[f"{columna}{fila}"] = etiqueta
        if valor:
            hoja[f"{columna_valor}{fila}"] = _texto(valor)
    hoja["B11"] = "TITULAR O REPRESENTANTE DE LA EXPLOTACIÓN"
    hoja["B12"] = "Nombre y apellidos:"
    hoja["Q12"] = "NIF:"
    hoja["B24"] = (
        "(1) La persona firmante se hace responsable de la veracidad de los datos consignados en el "
        "presente documento."
    )
    escritor.anota("1.1. INF. GRAL")

    # Lo que falta de la portada. Sin estos datos, la hoja sale con huecos, y es la primera que se
    # mira: son cuatro datos que se ponen una vez y valen para todos los años.
    if not explotacion.registro_autonomico:
        escritor.falta(
            "1.1. INF. GRAL",
            "el nº de registro de la explotación (el «0837267320» que trae tu cuaderno de la Junta)",
            "Mis datos → tu finca",
        )
    if not explotacion.direccion or not explotacion.localidad or not explotacion.codigo_postal:
        escritor.falta(
            "1.1. INF. GRAL",
            "la dirección, la localidad y el código postal",
            "Mis datos → tu finca",
        )
    if not explotacion.telefono:
        escritor.falta("1.1. INF. GRAL", "un teléfono de contacto", "Mis datos → tu finca")


def _hoja_1_2_1_3_1_4(escritor: _Escritor, db, explotacion) -> None:
    """Personas, máquinas y asesor: las tres listas de la información general."""
    from sqlalchemy import select

    nombre = "1.2., 1.3. y 1.4. INF. GRAL"
    hoja = escritor.hoja(nombre)
    hoja["B8"] = "1.2 PERSONAS O EMPRESAS QUE INTERVIENEN EN EL TRATAMIENTO CON PRODUCTOS FITOSANITARIOS"
    hoja["B9"] = "Nº de orden"
    hoja["C9"] = "Nombre y apellidos/ Empresas de servicios"
    hoja["D9"] = "NIF"
    hoja["E9"] = "Nº Inscripción ROPO"
    hoja["F9"] = "Tipo de carné"
    hoja["G9"] = "Cualificado"
    hoja["H9"] = "Fumigador"
    hoja["I9"] = "Piloto"
    hoja["J9"] = "Asesor"

    aplicadores = list(
        db.scalars(
            select(models.Aplicador)
            .where(models.Aplicador.explotacion_id == explotacion.id)
            .order_by(models.Aplicador.nombre)
        )
    )
    fila = 11
    for orden, aplicador in enumerate(aplicadores, start=1):
        tipo = (aplicador.tipo_carne or "").strip().lower()
        escritor.escribe_fila(
            nombre,
            fila,
            {
                "B": orden,
                "C": aplicador.nombre,
                "D": aplicador.nif,
                "E": aplicador.numero_ropo,
                # El cuaderno marca el tipo de carné con una cruz en su columna. La lista de tipos
                # sale del cuaderno: básico, cualificado, fumigador y piloto.
                "F": "X" if tipo.startswith("b") else "",
                "G": "X" if tipo.startswith("cual") else "",
                "H": "X" if tipo.startswith("fumig") else "",
                "I": "X" if tipo.startswith("pilot") else "",
            },
        )
        escritor.anota(nombre)
        falta_algo = []
        if not aplicador.nif:
            falta_algo.append("el NIF")
        if not aplicador.numero_ropo:
            falta_algo.append("el nº de inscripción en ROPO")
        if not aplicador.tipo_carne:
            falta_algo.append("el tipo de carné (básico, cualificado, fumigador o piloto)")
        if falta_algo:
            escritor.falta(
                nombre,
                f"de {aplicador.nombre}: " + ", ".join(falta_algo),
                "Mis cosas → aplicadores",
            )
        fila += 1
    if not aplicadores:
        escritor.falta(
            nombre,
            "quién echa los productos (tú mismo, si los echas tú): nombre, NIF y nº de ROPO",
            "Mis cosas → aplicadores",
        )

    # 1.3 Máquinas de echar producto.
    hoja["B17"] = "1.3 EQUIPOS DE APLICACIÓN DE PRODUCTOS FITOSANITARIOS PROPIOS DE LA EXPLOTACIÓN"
    hoja["B18"] = "Nº de orden"
    hoja["C18"] = "Descripción del equipo (3)"
    hoja["E18"] = "Nº inscrip. ROMA (4)"
    hoja["G18"] = "Fecha de adquisición"
    hoja["I18"] = "Fecha de la ultima inspección"
    equipos = list(
        db.scalars(
            select(models.EquipoAplicacion)
            .where(models.EquipoAplicacion.explotacion_id == explotacion.id)
            .order_by(models.EquipoAplicacion.nombre)
        )
    )
    fila = 20
    for orden, equipo in enumerate(equipos, start=1):
        escritor.escribe_fila(
            nombre,
            fila,
            {
                "B": orden,
                "C": equipo.nombre,
                "E": equipo.numero_roma,
                "G": equipo.fecha_adquisicion,
                "I": equipo.fecha_iteaf,
            },
        )
        escritor.anota(nombre)
        falta_algo = []
        # **Solo a los equipos que van en el ROMA** se les pide el número y la fecha de la última
        # inspección: una mochila, una carretilla o un apero no se inscriben ni se inspeccionan, y
        # pedirlos sería pedir un dato que no existe. Es la diferencia entre las tres pestañas de la
        # app oficial (maquinaria propia, ajena y equipos NO ROMA).
        #
        # **Y si no consta de quién es, se pregunta eso** (A11 de `docs/T02_VALORES_POR_DEFECTO.md`):
        # esta hoja es la de los equipos **propios de la explotación**, y hasta el 05/10/2026 un
        # `(equipo.titularidad or "propia")` metía aquí al pulverizador de la empresa de servicios
        # —la máquina de otro, en la lista de las tuyas— y le pedía el ROMA y la ITEAF como si la
        # obligación fuera del agricultor. No se puede deducir de ningún dato, así que se pregunta.
        titularidad = equipo.titularidad
        if titularidad is None:
            falta_algo.append(
                "si esa máquina es tuya, es de otro o no va inscrita en el ROMA (la hoja 1.3 es la "
                "de los equipos propios)"
            )
        elif titularidad != "no_roma":
            if not equipo.numero_roma:
                falta_algo.append("el nº de inscripción en el ROMA")
            if not equipo.fecha_iteaf:
                falta_algo.append("la fecha de la última inspección")
        if falta_algo:
            escritor.falta(
                nombre,
                f"de la máquina «{equipo.nombre}»: " + ", ".join(falta_algo),
                "Mis cosas → máquinas de echar producto",
            )
        fila += 1
    if not equipos:
        escritor.falta(
            nombre,
            "las máquinas con las que echas el producto (pulverizador, atomizador, mochila…), con su "
            "nº de ROMA y la fecha de su última inspección",
            "Mis cosas → máquinas de echar producto",
        )

    # 1.4 Asesor.
    hoja["B25"] = "1.4 ASESOR, AGRUPACIÓN O ENTIDAD DE ASESORAMIENTO A LA QUE PERTENECE LA EXPLOTACIÓN"
    hoja["B26"] = "Nombre o razón social"
    hoja["E26"] = "NIF"
    hoja["G26"] = "Nº de identificación"
    hoja["I26"] = "Tipo de explotación (5)"
    asesores = list(
        db.scalars(
            select(models.Asesor)
            .where(models.Asesor.explotacion_id == explotacion.id)
            .order_by(models.Asesor.nombre)
        )
    )
    fila = 28
    for asesor in asesores:
        escritor.escribe_fila(
            nombre,
            fila,
            {"B": asesor.nombre, "E": asesor.nif, "G": asesor.numero_ropo, "I": asesor.ambito},
        )
        escritor.anota(nombre)
        fila += 1


def _la_casilla_del_sistema(sistema: str | None) -> str:
    """La casilla «Secano/Regadío» (columna O de la hoja 2.1): «S», «R» o **en blanco**.

    **En blanco cuando no se sabe, y esto es el arreglo de A10** (`docs/T02_VALORES_POR_DEFECTO.md`).
    Hasta el 05/10/2026 esta casilla se escribía con un `"R" if … else "S"`: lo que no era regadío
    salía «S», así que **una tierra cuyo sistema no había dicho nadie se declaraba de secano** en el
    fichero que se sube a la Junta. Y no es una casilla decorativa: el sistema decide contra qué
    columna del anexo III de la Orden MAV/398/2022 se compara el abonado, y el papel que se firma es
    el que vale. Vacío es lo que el propio lector del cuaderno entiende por «no lo han declarado»
    (`cuaderno_cyl._lee_sistema`: «En blanco se queda en blanco»), y quien revise el cuaderno verá
    que falta un dato en vez de leer un dato falso.

    El aviso de que falta se da aparte, en el informe de lo que falta de la hoja 2.1: aquí no se
    escribe nada que nadie haya dicho.
    """
    if sistema == "secano":
        return "S"
    if sistema == "regadio":
        return "R"
    return ""


def _hoja_2_1(escritor: _Escritor, db, explotacion, campana) -> None:
    """Las parcelas: la hoja que más se mira de todo el cuaderno."""
    from sqlalchemy import select

    nombre = "2.1. DATOS PARCELAS"
    hoja = escritor.hoja(nombre)
    hoja["B2"] = "Explotación/Titular de la explotación:"
    hoja["F2"] = explotacion.nombre
    hoja["P2"] = "AÑO"
    hoja["Q2"] = campana.anio if campana else ""
    hoja["B6"] = "2. IDENTIFICACIÓN DE LAS PARCELAS DE LA EXPLOTACIÓN"
    hoja["B11"] = "2.1 DATOS IDENTIFICATIVOS Y AGRONÓMICOS DE LAS PARCELAS"
    cabecera = {
        "B": "Nº DE ORDEN (1)",
        "C": "Código Provincia",
        "D": "Término municipal (código y nombre)",
        "E": "Código Agregado",
        "F": "Zona",
        "G": "Nº de Polígono",
        "H": "Nº de Parcela",
        "I": "Nº de Recinto",
        "J": "Uso SIGPAC",
        "K": "Superficie SIGPAC (ha)",
        "L": "Superficie Cultivada (ha)",
        "M": "Especie/ Variedad",
        "N": "Ecoregimen/ Práctica (4)",
        "O": "Secano/ Regadío",
        "P": "Cultivo principal/ secundario",
        "Q": "Fecha inicio cultivo",
        "R": "Fecha fin cultivo",
        "S": "Aire libre o protegido (3)",
        "U": "Parcela  ubicada  en zona  nitratos",
    }
    for columna, texto in cabecera.items():
        hoja[f"{columna}12"] = texto

    parcelas = list(
        db.scalars(
            select(models.Parcela)
            .where(models.Parcela.explotacion_id == explotacion.id)
            .order_by(models.Parcela.poligono, models.Parcela.numero_parcela, models.Parcela.numero_recinto)
        )
    )
    cultivos = {
        cultivo.parcela_id: cultivo
        for cultivo in db.scalars(
            select(models.ParcelaCultivo).where(
                models.ParcelaCultivo.explotacion_id == explotacion.id,
                models.ParcelaCultivo.campana_id == (campana.id if campana else None),
            )
        )
    }
    fila = 14
    for orden, parcela in enumerate(parcelas, start=1):
        cultivo = cultivos.get(parcela.id)
        especie = ""
        variedad = ""
        if cultivo is not None:
            especie = cultivo.especie or ""
            variedad = cultivo.variedad or ""
        # El sistema: el del cultivo de la campaña manda, y si no lo dice se mira el de la tierra (es el
        # mismo dato visto desde otro sitio). Lo que **no** se hace es suponerlo (A10): ver
        # `_la_casilla_del_sistema`.
        sistema = (cultivo.sistema if cultivo is not None else None) or parcela.sistema
        # El cuaderno escribe la especie y la variedad en una casilla, separadas por un punto: es lo
        # que lee el lector del cuaderno al revés (`cuaderno_cyl._lee_especie_y_variedad`).
        especie_y_variedad = f"{especie}.{variedad}" if variedad else especie
        municipio = parcela.municipio or ""
        # Las dos primeras cifras del código del INE son la provincia y las tres siguientes, el
        # término municipal: el cuaderno los pide separados, con el nombre del pueblo detrás del
        # código («70-CALVARRASA DE ARRIBA»), y así es como lo lee también el lector del cuaderno.
        codigo_ine = parcela.codigo_ine or ""
        codigo_provincia = codigo_ine[:2] if len(codigo_ine) >= 2 else "37"
        codigo_municipio = codigo_ine[-3:] if len(codigo_ine) >= 3 else ""
        escritor.escribe_fila(
            nombre,
            fila,
            {
                "B": orden,
                "C": codigo_provincia,
                "D": f"{int(codigo_municipio)}-{municipio}" if codigo_municipio.isdigit() else municipio,
                "E": parcela.agregado or 0,
                "F": parcela.zona or 0,
                "G": parcela.poligono,
                "H": parcela.numero_parcela,
                "I": parcela.numero_recinto,
                "J": parcela.uso_sigpac,
                "K": _numero(parcela.superficie_sigpac_ha or parcela.superficie_ha),
                "L": _numero(parcela.superficie_ha),
                "M": especie_y_variedad,
                "N": (cultivo.ecorregimen if cultivo else "") or "",
                "O": _la_casilla_del_sistema(sistema),
                "P": "Principal",
                "Q": cultivo.fecha_inicio if cultivo else None,
                "R": cultivo.fecha_fin if cultivo else None,
                "U": "Sí" if parcela.zona_vulnerable_nitratos else "",
            },
        )
        escritor.anota(nombre)

        falta_algo = []
        if not parcela.poligono or not parcela.numero_parcela or not parcela.numero_recinto:
            falta_algo.append("la referencia del SIGPAC (polígono, parcela y recinto)")
        if cultivo is None:
            falta_algo.append("qué tienes sembrado este año")
        elif not cultivo.ecorregimen:
            falta_algo.append("el ecorregimen o la práctica (el «P3» del cuaderno)")
        if not parcela.municipio:
            falta_algo.append("el pueblo")
        # **A10: si no se sabe el sistema, la casilla «Secano/Regadío» va en blanco y aquí se dice.**
        # Sin este aviso, el agricultor mandaría un cuaderno con un hueco que él no ha visto.
        if not _la_casilla_del_sistema(sistema):
            falta_algo.append("si esa tierra es de secano o de regadío")
        if parcela.zona_vulnerable_nitratos is None:
            falta_algo.append("si está en zona de nitratos")
        if falta_algo:
            escritor.falta(
                nombre,
                f"de la tierra «{parcela.alias}»: " + ", ".join(falta_algo),
                "Mis parcelas",
            )
        fila += 1

    if not parcelas:
        escritor.falta(
            nombre,
            "tus tierras: sin ellas no hay cuaderno. Se pueden traer del cuaderno de la Junta o "
            "apuntarlas tocando el mapa",
            "Mis parcelas → añadir",
        )
    hoja[f"B{fila + 1}"] = (
        "El titular podrá a añadir nuevas parcelas y/o líneas de declaración en caso de ser "
        "necesario. 1"
    )
    hoja[f"B{fila + 3}"] = "[1] Identificar el número de orden de las parcelas."


def _hoja_3_1(escritor: _Escritor, db, explotacion, campana) -> None:
    """Los tratamientos hechos **en la parcela**: la hoja que la ley dice que será electrónica en 2027.

    **Solo los de la parcela, y esto es una corrección con su motivo.** Hasta la ronda 28 esta hoja se
    llevaba *todos* los tratamientos, incluidos los de la semilla, los del producto ya recogido y los
    de las naves. El cuaderno oficial tiene una hoja para cada cosa (la 3.2 para la semilla tratada,
    la 3.3 para la postcosecha, la 3.4 para las naves y almacenes) y esta es la de las parcelas: un
    tratamiento de una nave aparecía aquí con la casilla «Id. Parcelas» vacía, que es justo lo que
    mira quien revisa un cuaderno. Esos apuntes **no se pierden**: se cuentan en el informe, en la
    línea de su hoja, mientras esas hojas no se sepan escribir.
    """
    from sqlalchemy import select

    nombre = "3.1. REG. FIT. x P."
    hoja = escritor.hoja(nombre)
    hoja["B8"] = "3.1. REGISTRO DE ACTUACIONES FITOSANITARIAS DE LA PARCELA"
    cabecera = {
        "B9": "Id. Parcelas (1)",
        "C9": "Cultivo",
        "E9": "Intervalo de fechas (2)",
        "F9": "Superf. Tratada (ha)",
        "G9": "Problema fitosanitario",
        "H9": "Aplicador (3)",
        "I9": "Equipo (4)",
        "J9": "Producto Fitosanitario",
        "M9": "Eficacia (5)",
        "N9": "Observaciones",
        "C10": "Especie",
        "D10": "Variedad",
        "J10": "Nombre Comercial",
        "K10": "Nº Registro",
        "L10": "Dosis (kg/ha o l/ha)",
    }
    for celda, texto in cabecera.items():
        hoja[celda] = texto

    tratamientos = list(
        db.scalars(
            select(models.TratamientoFitosanitario)
            .where(
                models.TratamientoFitosanitario.explotacion_id == explotacion.id,
                models.TratamientoFitosanitario.anulado.is_(False),
                models.TratamientoFitosanitario.campana_id == (campana.id if campana else None),
                # Los de la semilla, los de la postcosecha y los de las naves van en **otras hojas**
                # del cuaderno oficial (3.2, 3.3 y 3.4). Aquí solo los de la tierra.
                models.TratamientoFitosanitario.tipo == "parcela",
            )
            .order_by(models.TratamientoFitosanitario.fecha)
        )
    )
    parcelas = {
        parcela.id: parcela
        for parcela in db.scalars(
            select(models.Parcela).where(models.Parcela.explotacion_id == explotacion.id)
        )
    }
    productos = {
        producto.id: producto
        for producto in db.scalars(
            select(models.ProductoFitosanitario).where(
                models.ProductoFitosanitario.explotacion_id == explotacion.id
            )
        )
    }
    aplicadores = {
        aplicador.id: aplicador
        for aplicador in db.scalars(
            select(models.Aplicador).where(models.Aplicador.explotacion_id == explotacion.id)
        )
    }
    equipos = {
        equipo.id: equipo
        for equipo in db.scalars(
            select(models.EquipoAplicacion).where(
                models.EquipoAplicacion.explotacion_id == explotacion.id
            )
        )
    }
    orden_de_la_parcela = {
        parcela.id: orden for orden, parcela in enumerate(parcelas.values(), start=1)
    }

    fila = 12
    for tratamiento in tratamientos:
        producto = productos.get(tratamiento.producto_id)
        aplicador = aplicadores.get(tratamiento.aplicador_id)
        equipo = equipos.get(tratamiento.equipo_id)
        escritor.escribe_fila(
            nombre,
            fila,
            {
                "B": orden_de_la_parcela.get(tratamiento.parcela_id, ""),
                "C": tratamiento.cultivo,
                "E": tratamiento.fecha,
                "F": _numero(tratamiento.superficie_tratada_ha),
                "G": tratamiento.plaga,
                "H": aplicador.nombre if aplicador else "",
                "I": equipo.nombre if equipo else "",
                "J": producto.nombre_comercial if producto else "",
                "K": producto.numero_registro if producto else "",
                "L": _numero(tratamiento.dosis),
                "M": tratamiento.eficacia,
                "N": tratamiento.observaciones,
            },
        )
        escritor.anota(nombre)
        falta_algo = []
        if producto is None:
            falta_algo.append("el producto")
        elif not producto.numero_registro:
            falta_algo.append("el nº de registro del producto")
        if not tratamiento.justificacion:
            falta_algo.append("por qué se echó")
        if not tratamiento.plaga:
            falta_algo.append("el problema que se trataba (la plaga o la hierba)")
        if not tratamiento.eficacia:
            falta_algo.append("cómo de bien funcionó")
        if not equipo:
            falta_algo.append("con qué máquina se echó")
        if falta_algo:
            escritor.falta(
                nombre,
                f"del tratamiento del {tratamiento.fecha.strftime('%d/%m/%Y')}: " + ", ".join(falta_algo),
                "Echar producto (o el apunte, para corregirlo)",
            )
        fila += 1
    if not tratamientos:
        escritor.falta(
            nombre,
            "los tratamientos del año: cada vez que echas producto se apunta aquí solo",
            "Echar producto",
        )


def _hoja_4(escritor: _Escritor, db, explotacion, campana) -> None:
    """Los análisis."""
    from sqlalchemy import select

    nombre = "4. REG. ANALISIS"
    hoja = escritor.hoja(nombre)
    hoja["B8"] = "Fecha"
    hoja["C8"] = "Material analizado (1)"
    hoja["D8"] = "Cultivo o cosecha muestreado/s (2)"
    hoja["E8"] = "Nº Boletín de análisis"
    hoja["F8"] = "Laboratorio (Nombre y dirección)"
    hoja["G8"] = "Sustancias activas detectadas"
    analisis = list(
        db.scalars(
            select(models.Analitica)
            .where(
                models.Analitica.explotacion_id == explotacion.id,
                models.Analitica.anulado.is_(False),
            )
            .order_by(models.Analitica.fecha_toma_muestra)
        )
    )
    # El cuaderno identifica la parcela muestreada por su **número de orden** en la hoja 2.1, no por
    # su nombre: por eso se numera aquí igual que allí (mismo orden, misma cuenta).
    parcelas = list(
        db.scalars(
            select(models.Parcela)
            .where(models.Parcela.explotacion_id == explotacion.id)
            .order_by(models.Parcela.poligono, models.Parcela.numero_parcela)
        )
    )
    orden_de_la_parcela = {parcela.id: orden for orden, parcela in enumerate(parcelas, start=1)}
    fila = 10
    for analitica in analisis:
        escritor.escribe_fila(
            nombre,
            fila,
            {
                "B": analitica.fecha_toma_muestra,
                "C": analitica.tipo_analisis or analitica.tipo,
                "D": orden_de_la_parcela.get(analitica.parcela_id, ""),
                "E": analitica.numero_informe,
                "F": analitica.laboratorio,
                "G": analitica.sustancia_detectada,
            },
        )
        escritor.anota(nombre)
        falta_algo = []
        if not analitica.numero_informe:
            falta_algo.append("el nº de boletín")
        if not analitica.laboratorio:
            falta_algo.append("el laboratorio")
        if falta_algo:
            escritor.falta(
                nombre,
                "del análisis del "
                f"{analitica.fecha_toma_muestra.strftime('%d/%m/%Y')}: " + ", ".join(falta_algo),
                "Análisis (o el apunte, para corregirlo)",
            )
        fila += 1


def _hoja_5(escritor: _Escritor, db, explotacion, campana) -> None:
    """Lo que se ha vendido (la app oficial la llama «cosecha comercializada»)."""
    from sqlalchemy import select

    nombre = "5. REG. COMERC."
    hoja = escritor.hoja(nombre)
    hoja["B8"] = "Fecha"
    hoja["C8"] = "Producto"
    hoja["D8"] = "Cantidad de producto (kg)"
    hoja["E8"] = "Nº de orden parcela/s de origen (1)"
    hoja["F8"] = "Nº de albarán o factura (2)"
    hoja["G8"] = "Nº de lote (2)"
    hoja["H8"] = "Cliente"
    hoja["H9"] = "Nombre o razón social"
    hoja["I9"] = "NIF"
    hoja["J9"] = "Dirección"
    hoja["K9"] = "Nº de RGSEAA (2)"
    ventas = list(
        db.scalars(
            select(models.VentaDeCosecha)
            .where(
                models.VentaDeCosecha.explotacion_id == explotacion.id,
                models.VentaDeCosecha.anulado.is_(False),
            )
            .order_by(models.VentaDeCosecha.fecha)
        )
    )
    fila = 11
    for venta in ventas:
        escritor.escribe_fila(
            nombre,
            fila,
            {
                "B": venta.fecha,
                "C": venta.producto,
                "D": _numero(venta.cantidad),
                "F": venta.numero_albaran,
                "G": venta.lote,
                "H": venta.comprador,
            },
        )
        escritor.anota(nombre)
        fila += 1


def _hoja_6(escritor: _Escritor, db, explotacion, campana) -> None:
    """El abonado, con el nº de albarán y el tipo de abonado que pide el cuaderno."""
    from sqlalchemy import select

    nombre = "6. REG. FERTILIZ"
    hoja = escritor.hoja(nombre)
    hoja["B8"] = "Intervalo de fechas"
    hoja["C8"] = "Nº de orden de parcelas (1)"
    hoja["D8"] = "Cultivo"
    hoja["F8"] = "Tipo de abono/producto (2)"
    hoja["G8"] = "Nº de albarán"
    hoja["H8"] = "Riqueza N/P/K"
    hoja["I8"] = "Dosis (kg/ha, m3/ha)"
    hoja["J8"] = "Tipo de fertilización (3)"
    hoja["K8"] = "Observaciones"
    hoja["D9"] = "Especie"
    hoja["E9"] = "Variedad"
    abonos = list(
        db.scalars(
            select(models.RegistroFertilizacion)
            .where(
                models.RegistroFertilizacion.explotacion_id == explotacion.id,
                models.RegistroFertilizacion.anulado.is_(False),
                models.RegistroFertilizacion.campana_id == (campana.id if campana else None),
            )
            .order_by(models.RegistroFertilizacion.fecha)
        )
    )
    parcelas = list(
        db.scalars(
            select(models.Parcela)
            .where(models.Parcela.explotacion_id == explotacion.id)
            .order_by(models.Parcela.poligono, models.Parcela.numero_parcela)
        )
    )
    orden_de_la_parcela = {parcela.id: orden for orden, parcela in enumerate(parcelas, start=1)}
    # El cuaderno abrevia el tipo de abonado con tres códigos: (F) fertirrigación, (AF) abonado de
    # fondo y (AC) abonado de cobertera.
    codigos = {"fondo": "AF", "cobertera": "AC", "fertirrigacion": "F"}

    fila = 11
    for abono in abonos:
        escritor.escribe_fila(
            nombre,
            fila,
            {
                "B": abono.fecha,
                "C": orden_de_la_parcela.get(abono.parcela_id, ""),
                "D": abono.fertilizante_nombre,
                "F": abono.tipo,
                "G": abono.numero_albaran,
                # **La riqueza en blanco si no consta**, no «0/0/0» (A6 de
                # `docs/T02_VALORES_POR_DEFECTO.md`). Es la misma regla que ya sigue el resto del
                # volcado: «lo que no esté puesto sale en blanco, no con un cero ni con un dato
                # inventado» (`cuaderno_cyl_api.py`). Rellenar con ceros una casilla que nadie ha
                # declarado es lo que después no se sabe de dónde salió.
                "H": _riquezas(abono),
                "I": _numero(abono.kg_ha_producto),
                "J": codigos.get(abono.tipo_fertilizacion or "", ""),
                "K": abono.observaciones,
            },
        )
        escritor.anota(nombre)
        falta_algo = []
        if not abono.numero_albaran:
            falta_algo.append("el nº de albarán (viene en la factura del abono)")
        if not abono.tipo_fertilizacion:
            falta_algo.append("si fue de fondo, de cobertera o fertirrigación")
        if _riquezas(abono) == "":
            falta_algo.append(
                "la composición (nitrógeno, fósforo y potasio), que viene en la etiqueta del saco"
            )
        if falta_algo:
            escritor.falta(
                nombre,
                f"del abono del {abono.fecha.strftime('%d/%m/%Y')}: " + ", ".join(falta_algo),
                "Abonar (o el apunte, para corregirlo)",
            )
        fila += 1
    if not abonos:
        escritor.falta(
            nombre,
            "los abonos del año, con el nº de albarán de la compra y el tipo de abonado. Es "
            "obligatorio desde el 1 de enero de 2026",
            "Abonar",
        )


def _hoja_7(escritor: _Escritor, db, explotacion, campana) -> None:
    """Labores, siembra y recolección."""
    from sqlalchemy import select

    nombre = "7. DAT. AGROAMB."
    hoja = escritor.hoja(nombre)
    hoja["B8"] = "Nº orden de parcelas (1)"
    hoja["C8"] = "Cultivo"
    hoja["E8"] = "Datos de las labores, siembra, tratamientos, abonado y recolección"
    hoja["E9"] = "Labores previas a la siembra"
    hoja["G9"] = "Siembra"
    hoja["J9"] = "Fecha de recolección"
    hoja["K9"] = "Fecha de picado/triturado del rastrojo de la cosecha anterior"
    hoja["L9"] = "Pastoreo"
    hoja["E10"] = "Tipo de labor"
    hoja["F10"] = "Fecha de realización"
    hoja["G10"] = "Fecha"
    hoja["H10"] = "Tipo"
    hoja["I10"] = "Dosis de semilla utilizada (kg/ha)"
    hoja["L10"] = "Fecha de inicio"
    hoja["M10"] = "Fecha de finalización"

    labores = list(
        db.scalars(
            select(models.Labor)
            .where(
                models.Labor.explotacion_id == explotacion.id,
                models.Labor.anulado.is_(False),
                models.Labor.campana_id == (campana.id if campana else None),
            )
            .order_by(models.Labor.fecha)
        )
    )
    parcelas = list(
        db.scalars(
            select(models.Parcela)
            .where(models.Parcela.explotacion_id == explotacion.id)
            .order_by(models.Parcela.poligono, models.Parcela.numero_parcela)
        )
    )
    orden_de_la_parcela = {parcela.id: orden for orden, parcela in enumerate(parcelas, start=1)}

    fila = 12
    for labor in labores:
        escritor.escribe_fila(
            nombre,
            fila,
            {
                "B": orden_de_la_parcela.get(labor.parcela_id, ""),
                "C": labor.cultivo,
                "E": labor.tipo,
                "F": labor.fecha,
                "G": labor.fecha if labor.tipo in ("siembra", "plantacion") else "",
                "H": labor.tipo if labor.tipo in ("siembra", "plantacion") else "",
                "I": _numero(labor.dosis_siembra_kg_ha),
                "J": labor.fecha if labor.tipo == "cosecha" else "",
            },
        )
        escritor.anota(nombre)
        fila += 1
    if not labores:
        escritor.falta(
            nombre,
            "las labores del año (laboreo, siembra, recolección, pastoreo…): se apuntan solas "
            "cuando las apuntas en «Otro trabajo»",
            "Otro trabajo",
        )


def _hoja_9_1_2(escritor: _Escritor, db, explotacion, campana) -> None:
    """El plan de abonado: es el que pide la ayuda y el que exige la ley desde el 1/9/2026."""
    from sqlalchemy import select

    nombre = "9.1.2. PLAN ABONADO"
    hoja = escritor.hoja(nombre)
    hoja["I2"] = "AÑO:"
    hoja["A3"] = "9. DATOS RELATIVOS A LA EXPLOTACIÓN PARA SOLICITANTES DE AYUDAS DIRECTAS"
    hoja["A5"] = "9.1.2 PLAN DE ABONADO"
    cabecera = {
        "A7": "Fecha elaboración del plan de abonado",
        "B7": "Nº de orden de parcelas (1) o referencia SIGPAC",
        "C7": "Cultivo",
        "D7": "Necesidad UF N (kg/ha)",
        "E7": "Necesidad UF P2O5 (kg/ha)",
        "F7": "Necesidad UF K2O (kg/ha)",
        "G7": "Objetivo de la producción (kg/ha)",
        "H7": "Cultivo precedente",
        "I7": "Asesor codigo REGFER",
    }
    for celda, texto in cabecera.items():
        hoja[celda] = texto
    planes = list(
        db.scalars(
            select(models.PlanAbonado)
            .where(
                models.PlanAbonado.explotacion_id == explotacion.id,
                models.PlanAbonado.campana_id == (campana.id if campana else None),
            )
            .order_by(models.PlanAbonado.creado_en)
        )
    )
    parcelas = list(
        db.scalars(
            select(models.Parcela)
            .where(models.Parcela.explotacion_id == explotacion.id)
            .order_by(models.Parcela.poligono, models.Parcela.numero_parcela)
        )
    )
    orden_de_la_parcela = {parcela.id: orden for orden, parcela in enumerate(parcelas, start=1)}
    from . import servicios

    fila = 8
    for plan in planes:
        precedente = servicios.cultivo_precedente(db, explotacion, plan)
        escritor.escribe_fila(
            nombre,
            fila,
            {
                "A": plan.creado_en.date() if plan.creado_en else None,
                "B": orden_de_la_parcela.get(plan.parcela_id, ""),
                "C": plan.cultivo,
                "D": _numero(plan.necesidad_n),
                "E": _numero(plan.necesidad_p),
                "F": _numero(plan.necesidad_k),
                "G": _numero(plan.produccion_esperada_kg_ha),
                "H": (precedente or ""),
            },
        )
        escritor.anota(nombre)
        falta_algo = []
        if plan.necesidad_n is None or plan.necesidad_p is None or plan.necesidad_k is None:
            falta_algo.append("las necesidades de N, P y K")
        if not plan.produccion_esperada_kg_ha:
            falta_algo.append("lo que esperas sacar (kg/ha)")
        if not precedente:
            falta_algo.append("el cultivo del año anterior")
        if falta_algo:
            escritor.falta(
                nombre,
                f"del plan de «{plan.cultivo}»: " + ", ".join(falta_algo),
                "Plan de abono (o el plan, para corregirlo)",
            )
        fila += 1
    if not planes:
        escritor.falta(
            nombre,
            "el plan de abonado del año. Es obligatorio desde el 1 de septiembre de 2026, y lo pide "
            "la ayuda de los ecorregímenes",
            "Plan de abono del año",
        )


def _hoja_doc(escritor: _Escritor, db, explotacion) -> None:
    """Los papeles que hay que conservar junto al cuaderno, y cuáles tiene el agricultor."""
    from sqlalchemy import select

    nombre = "doc"
    hoja = escritor.hoja(nombre)
    hoja["C9"] = "DOCUMENTACIÓN A CONSERVAR JUNTO CON EL CUADERNO DE EXPLOTACIÓN"
    hoja["C11"] = (
        "Se conservarán junto al cuaderno de explotación durante al menos 3 años los siguientes "
        "documentos:"
    )
    pares = [
        "·  Facturas u otros documentos que justifiquen la adquisición de los productos fitosanitarios.",
        "·  Contratos con las empresas o personas físicas que hayan realizado los tratamientos fitosanitarios.",
        "·  Certificados de inspección de los equipos de aplicación de producto fitosanitario.",
        "·  Justificantes de entrega de los envases vacíos de los productos fitosanitarios en el correspondiente sistema de gestión.",
        "·  Boletines de análisis de residuos de productos fitosanitarios realizados sobre sus cultivos.",
        "·  Documentación relativa al asesoramiento recibido.",
        "·  Albaranes de entrega o facturas de venta de la cosecha.",
    ]
    for desplazamiento, texto in enumerate(pares):
        hoja[f"C{13 + desplazamiento}"] = texto

    papeles = list(
        db.scalars(
            select(models.DocumentoAnexo).where(
                models.DocumentoAnexo.explotacion_id == explotacion.id,
                models.DocumentoAnexo.anulado.is_(False),
            )
        )
    )
    facturas = list(
        db.scalars(
            select(models.Factura).where(
                models.Factura.explotacion_id == explotacion.id,
                models.Factura.anulada.is_(False),
            )
        )
    )
    if papeles or facturas:
        fila = 21
        hoja[f"C{fila}"] = "LO QUE TIENES GUARDADO EN EL PROGRAMA"
        fila += 1
        for papel in papeles:
            escritor.escribe(
                nombre,
                fila,
                "C",
                f"·  {papel.titulo}"
                + (f" ({papel.quien})" if papel.quien else "")
                + ("  [con fichero]" if papel.fichero_ruta else ""),
            )
            fila += 1
        for factura in facturas:
            escritor.escribe(
                nombre,
                fila,
                "C",
                f"·  Factura {factura.numero_factura or ''} de {factura.proveedor or 'un proveedor'}"
                + ("  [con fichero]" if factura.fichero_ruta else ""),
            )
            fila += 1
    if not facturas:
        escritor.falta(
            nombre,
            "las facturas de lo que compras: el cuaderno dice que hay que conservarlas tres años, y "
            "además de ahí salen el nº de factura y el nº de albarán que pide el cuaderno",
            "Lo que tengo en el almacén → Mis facturas",
        )


# --------------------------------------------------------------------------
# La puerta de entrada
# --------------------------------------------------------------------------


def escribe_el_cuaderno(db, explotacion, campana=None) -> CuadernoEscrito:
    """Escribe el cuaderno de la Junta con los datos del agricultor.

    Devuelve el fichero **y el informe de lo que falta**. Lo segundo no es un extra: es la lista de
    lo que hay que apuntar para tener el cuaderno entero, sacada de comparar el cuaderno oficial con
    lo que el agricultor tiene puesto (no de una lista escrita a mano).
    """
    escritor = _Escritor()

    _hoja_1_1(escritor, explotacion)
    _hoja_1_2_1_3_1_4(escritor, db, explotacion)
    _hoja_2_1(escritor, db, explotacion, campana)
    _hoja_3_1(escritor, db, explotacion, campana)
    _hoja_4(escritor, db, explotacion, campana)
    _hoja_5(escritor, db, explotacion, campana)
    _hoja_6(escritor, db, explotacion, campana)
    _hoja_7(escritor, db, explotacion, campana)
    _hoja_9_1_2(escritor, db, explotacion, campana)
    _hoja_doc(escritor, db, explotacion)

    # Las hojas que el programa todavía no rellena se dejan con su título y su nombre, para que el
    # fichero tenga las 25 hojas del cuaderno oficial. Y **cada una se declara en el informe**, con lo
    # que pide, con dónde se apunta ese dato aquí y con cuántos apuntes del agricultor irían dentro:
    # una hoja vacía que podría estar llena es trabajo perdido, y una hoja vacía de la que no se dice
    # nada es un agricultor pensando que se ha perdido un dato suyo.
    cuantos = _cuantos_apuntes(db, explotacion, campana)
    for nombre, apunte in HOJAS_QUE_NO_SE_RELLENAN.items():
        escritor.faltan.append(_lo_que_falta_en_una_hoja_que_no_se_escribe(nombre, apunte, cuantos))

    buffer = io.BytesIO()
    escritor.libro.save(buffer)
    return CuadernoEscrito(
        contenido=buffer.getvalue(),
        anio=campana.anio if campana else None,
        filas_por_hoja=dict(escritor.filas),
        faltan=escritor.faltan,
    )


def nombre_del_fichero(explotacion, campana) -> str:
    """El nombre que le pone la Junta a su fichero: `CuadernoExplotacion_<NIF>.xlsx`."""
    nif = "".join(caracter for caracter in (explotacion.nif or "") if caracter.isalnum())
    anio = f"_{campana.anio}" if campana else ""
    return f"CuadernoExplotacion_{nif or 'sinnif'}{anio}.xlsx"


def lee_lo_escrito(contenido: bytes) -> lector.CuadernoLeido:
    """Vuelve a leer el cuaderno que se acaba de escribir.

    Sirve para el test del recorrido completo (escribir y volver a leer), y para que el agricultor
    pueda comprobar que el fichero que se lleva dice lo que él tiene apuntado.
    """
    return lector.leer_cuaderno(contenido)
