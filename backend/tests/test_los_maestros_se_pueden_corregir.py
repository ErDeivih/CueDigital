"""Corregir y borrar las fichas de lo que se usa: productos, abonos, aplicadores, asesores, máquinas y naves (ronda 94).

LO QUE SE PRUEBA AQUÍ, Y POR QUÉ

David lo pidió con estas palabras: «recuerda también dejar borrar las cosas que introduzca porque
puede que me equivoque, o modificar también». La ronda 91 lo hizo con los apuntes del cuaderno
(tratamientos, abonos, labores y cosechas) y la 92 con las tierras y los grupos. Las **fichas de lo
que se usa** —«Mis parcelas, productos y máquinas»— se quedaron fuera, y son justo las que más se
escriben a mano y a toda prisa: el número de registro copiado del bote, la fecha de la ITV, el tipo
de carné, la riqueza del abono.

Estas pruebas defienden las cinco cosas que hacen que corregir y borrar una ficha sea de fiar y no
un agujero por el que se cuela un cuaderno que dice lo que no es:

  1. **Corregir cambia esa ficha, no da de alta otra.** El identificador sigue siendo el mismo, y de
     él cuelgan los apuntes que la usaron (un tratamiento guarda el producto, el aplicador, la
     máquina y la nave; un abono, el abono). Dos fichas donde había una es un cuaderno que dice que
     se usaron dos cosas distintas.
  2. **Lo que había no se pierde**: queda en la auditoría, campo por campo (`correcciones`).
  3. **Las reglas son las mismas que al dar de alta la ficha**, porque es la misma función. Una
     corrección rechazada no deja la ficha a medias.
  4. **Una ficha que está dentro de un apunte NO se borra**: se contesta 409 diciendo cuántas cosas
     la usan y qué hacer. Borrarla dejaría esos apuntes sin poder decir qué se echó, con qué máquina
     o dónde, que es lo único que este programa no puede estropear.
  5. **La corrección no borra lo que el formulario no puede devolver**: hay columnas que la API no
     devuelve (el NIF del que aplica, el número de serie de la máquina…), y si la corrección las
     copiara sin más, ponerle el nombre bueno a una ficha **borraría** esos datos en silencio.

La tabla `MAESTROS_DATOS` de abajo es el corazón del fichero: las seis fichas se prueban **exactamente
igual**, para que ninguna se quede sin probar por descuido, y cada caso se lee porque trae su ruta,
sus datos y cómo se usa.
"""

from __future__ import annotations

import json

from dataclasses import dataclass, field
from typing import Callable

import pytest
from sqlalchemy import select

from app import models, textos
from app.routers import maestros as router_de_maestros
from app.schemas import (
    AplicadorEntrada,
    AplicadorSalida,
    AsesorEntrada,
    AsesorSalida,
    EquipoEntrada,
    EquipoSalida,
    FertilizanteEntrada,
    FertilizanteSalida,
    InstalacionEntrada,
    InstalacionSalida,
    ProductoEntrada,
    ProductoSalida,
)


# --------------------------------------------------------------------------
# Cómo se usa cada ficha: sin esto no hay nada que la defienda de un borrado
# --------------------------------------------------------------------------


def _un_tratamiento(cliente, cabeceras, piezas, fecha="2026-05-01", **cambios) -> dict:
    """Apunta un tratamiento, que es lo que usa cuatro de las seis fichas.

    Se le cambia lo que pruebe cada test (`producto_id`, `aplicador_id`, `equipo_id`…). Los datos de
    base son los de un tratamiento correcto (`tests.conftest`): un producto con número de registro,
    dentro de la superficie de la tierra y con su justificación, que es lo que las comprobaciones del
    cuaderno exigen para dejarlo guardar.
    """
    cuerpo = {
        "campana_id": piezas["campana"]["id"],
        "fecha": fecha,
        "parcela_id": piezas["parcela"]["id"],
        "superficie_tratada_ha": 2.43,
        "justificacion": "Vi la plaga o la hierba en el campo",
        "producto_id": piezas["producto"]["id"],
        "dosis": 0.8,
        "franja_seguridad_respetada": True,
    }
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/tratamientos", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _usa_el_producto(cliente, cabeceras, piezas, ficha_id, fecha="2026-05-01") -> dict:
    return _un_tratamiento(cliente, cabeceras, piezas, fecha=fecha, producto_id=ficha_id)


def _usa_el_aplicador(cliente, cabeceras, piezas, ficha_id, fecha="2026-05-01") -> dict:
    return _un_tratamiento(cliente, cabeceras, piezas, fecha=fecha, aplicador_id=ficha_id)


def _usa_el_asesor(cliente, cabeceras, piezas, ficha_id, fecha="2026-05-01") -> dict:
    return _un_tratamiento(cliente, cabeceras, piezas, fecha=fecha, asesor_id=ficha_id)


def _usa_el_equipo(cliente, cabeceras, piezas, ficha_id, fecha="2026-05-01") -> dict:
    return _un_tratamiento(cliente, cabeceras, piezas, fecha=fecha, equipo_id=ficha_id)


def _usa_el_abono(cliente, cabeceras, piezas, ficha_id, fecha="2026-02-20") -> dict:
    """Un apunte de abonado, que es quien usa la ficha del abono."""
    respuesta = cliente.post(
        "/api/fertilizaciones",
        headers=cabeceras,
        json={
            "campana_id": piezas["campana"]["id"],
            "fecha": fecha,
            "parcela_id": piezas["parcela"]["id"],
            "superficie_ha": 2.43,
            "fertilizante_id": ficha_id,
            "kg_ha_producto": 300.0,
            "modo_aplicacion": "al suelo",
            "momento": "fondo",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _usa_la_instalacion(cliente, cabeceras, piezas, ficha_id, fecha="2026-06-10") -> dict:
    """Tratar una nave: el producto no se echa en la tierra, se echa en un local."""
    respuesta = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": piezas["campana"]["id"],
            "fecha": fecha,
            "tipo": "instalaciones",
            "instalacion_id": ficha_id,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": piezas["producto"]["id"],
            "dosis": 0.5,
            "plazo_reentrada_dias": 3,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --------------------------------------------------------------------------
# Las seis fichas, en una tabla
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Maestro:
    """Una de las seis fichas de «Mis parcelas, productos y máquinas», con lo que hace falta probar.

    `campo` y `valor` son **lo que se corrige**: un dato que el agricultor teclea y se equivoca al
    teclear. `no_vale` es lo que el alta rechaza, para comprobar que corregir tampoco lo acepta. Y
    `usa` es cómo se apunta algo que la usa, que es la razón por la que no se puede borrar.
    """

    nombre: str  # cómo se llama en la auditoría
    ruta: str  # dónde vive en la API: el alta, la corrección y el borrado son la misma ruta
    modelo: type  # la tabla de verdad, para mirar lo que se ha guardado
    columna: str  # la columna con la que los apuntes apuntan a esta ficha
    apuntes: type  # la tabla de los apuntes que la usan
    lista_de_apuntes: str  # dónde se ven esos apuntes
    entrada: type  # el esquema que acepta el alta (y la corrección: es el mismo)
    salida: type  # el esquema con el que se lee
    alta: dict  # un cuerpo de alta completo y correcto
    campo: str  # qué campo se corrige
    valor: object  # y con qué valor se queda
    no_vale: dict  # lo que el alta no acepta
    usa: Callable  # cómo se apunta algo que la usa
    se_manda_y_no_vuelve: dict = field(default_factory=dict)  # se acepta, pero no se devuelve
    no_vuelven_al_formulario: tuple[str, ...] = ()

    @property
    def correccion(self) -> dict:
        """El cuerpo de la corrección: el alta entera con **una cosa** cambiada.

        Es el cuerpo entero a propósito: `PUT` acepta exactamente el mismo esquema que el alta, y esa
        es la gracia —el formulario se rellena con lo que devuelve la API, así que al corregir se
        manda todo otra vez—.
        """
        return {**self.alta, self.campo: self.valor}

    @property
    def alta_que_no_vale(self) -> dict:
        """El mismo alta con lo que las reglas del alta no dejan pasar."""
        return {**self.alta, **self.no_vale}


MAESTROS_DATOS = [
    Maestro(
        nombre="producto",
        ruta="/api/productos",
        modelo=models.ProductoFitosanitario,
        columna="producto_id",
        apuntes=models.TratamientoFitosanitario,
        lista_de_apuntes="/api/tratamientos",
        entrada=ProductoEntrada,
        salida=ProductoSalida,
        alta={
            "nombre_comercial": "Ejemplo 25 EC",
            "numero_registro": "24.123",
            "materia_activa": "Tebuconazol",
            "dosis_maxima": 0.8,
            "unidad_dosis": "L/ha",
            "plazo_seguridad_dias": 21,
            "lote": "L-2026-01",
        },
        campo="nombre_comercial",
        valor="Ejemplo 25 EC (el del bote grande)",
        no_vale={"dosis_maxima": 0},
        usa=_usa_el_producto,
    ),
    Maestro(
        nombre="fertilizante",
        ruta="/api/fertilizantes",
        modelo=models.Fertilizante,
        columna="fertilizante_id",
        apuntes=models.RegistroFertilizacion,
        lista_de_apuntes="/api/fertilizaciones",
        entrada=FertilizanteEntrada,
        salida=FertilizanteSalida,
        alta={
            "nombre": "Nitrato amónico 33,5%",
            "tipo": "mineral",
            "riqueza_n": 33.5,
            "riqueza_p": 0.0,
            "riqueza_k": 0.0,
        },
        campo="riqueza_n",
        valor=27.0,
        no_vale={"riqueza_n": 120.0},
        usa=_usa_el_abono,
    ),
    Maestro(
        nombre="aplicador",
        ruta="/api/aplicadores",
        modelo=models.Aplicador,
        columna="aplicador_id",
        apuntes=models.TratamientoFitosanitario,
        lista_de_apuntes="/api/tratamientos",
        entrada=AplicadorEntrada,
        salida=AplicadorSalida,
        alta={
            "nombre": "David Pérez",
            "numero_ropo": "ROPO-1234",
            "numero_carne": "C-123456",
            "tipo_carne": "Cualificado",
            "fecha_caducidad_carne": "2030-01-01",
        },
        campo="nombre",
        valor="David Pérez Velasco",
        no_vale={"tipo_carne": "nivel 2"},
        usa=_usa_el_aplicador,
        se_manda_y_no_vuelve={"nif": "70922320A"},
        no_vuelven_al_formulario=("nif",),
    ),
    Maestro(
        nombre="asesor",
        ruta="/api/asesores",
        modelo=models.Asesor,
        columna="asesor_id",
        apuntes=models.TratamientoFitosanitario,
        lista_de_apuntes="/api/tratamientos",
        entrada=AsesorEntrada,
        salida=AsesorSalida,
        alta={
            "nombre": "Ana García Ruiz",
            "numero_ropo": "ROPO-ASESOR-778",
            "ambito": "gip",
            "entidad_certificacion": "Producción Integrada de Castilla y León",
        },
        campo="numero_ropo",
        valor="ROPO-ASESOR-779",
        no_vale={"ambito": "de todo un poco"},
        usa=_usa_el_asesor,
        se_manda_y_no_vuelve={"nif": "12345678Z"},
        no_vuelven_al_formulario=("nif",),
    ),
    Maestro(
        nombre="equipo",
        ruta="/api/equipos",
        modelo=models.EquipoAplicacion,
        columna="equipo_id",
        apuntes=models.TratamientoFitosanitario,
        lista_de_apuntes="/api/tratamientos",
        entrada=EquipoEntrada,
        salida=EquipoSalida,
        alta={
            "nombre": "Pulverizador grande",
            "tipo": "Atomizador",
            "numero_roma": "ROMA-9876",
            "fecha_iteaf": "2024-03-01",
            "fecha_proxima_iteaf": "2029-03-01",
        },
        campo="fecha_proxima_iteaf",
        valor="2030-03-01",
        no_vale={"nombre": ""},
        usa=_usa_el_equipo,
        se_manda_y_no_vuelve={"numero_serie": "SN-2026-0001"},
        no_vuelven_al_formulario=("numero_serie",),
    ),
    Maestro(
        nombre="instalacion",
        ruta="/api/instalaciones",
        modelo=models.Instalacion,
        columna="instalacion_id",
        apuntes=models.TratamientoFitosanitario,
        lista_de_apuntes="/api/tratamientos",
        entrada=InstalacionEntrada,
        salida=InstalacionSalida,
        alta={
            "alias": "El almacén grande",
            "tipo": "almacen",
            "municipio": "Peñaranda de Bracamonte",
            "uso": "Guardar el grano",
        },
        campo="alias",
        valor="El almacén de arriba",
        no_vale={"tipo": "castillo"},
        usa=_usa_la_instalacion,
        se_manda_y_no_vuelve={"observaciones": "Tiene el techo de uralita"},
        no_vuelven_al_formulario=("creada_en", "observaciones"),
    ),
]

# Un caso por ficha, con su nombre delante para que el fallo se lea de un vistazo.
MAESTROS = [pytest.param(maestro, id=maestro.nombre) for maestro in MAESTROS_DATOS]
POR_NOMBRE = {maestro.nombre: maestro for maestro in MAESTROS_DATOS}

# Las fichas que tienen alguna columna que se acepta al dar de alta pero **no vuelve** en la
# respuesta (y por tanto el formulario de corregir no puede mandar). El producto y el abono no
# tienen ninguna hoy, y eso también se prueba (`test_solo_se_corrige_lo_que_el_formulario_puede...`).
CON_LO_QUE_NO_SE_DEVUELVE = [
    pytest.param(maestro, id=maestro.nombre)
    for maestro in MAESTROS_DATOS
    if maestro.no_vuelven_al_formulario
]

# Las seis fichas vistas como la columna con la que un apunte las usa, que es lo que se cuenta antes
# de borrar. `correcciones.tablas_que_apuntan_a` lo saca de la base de datos de verdad: esta tabla
# solo dice **qué tablas** tienen que salir hoy para cada columna.
#
# **`articulos` entra en las dos primeras desde T09** (03/10/2026, el almacén por lote). El artículo
# del almacén se engancha a la ficha del producto o del abono, y eso es una dependencia de verdad por
# el mismo motivo que las otras: sin la ficha, el artículo se queda sin decir **qué es** —y la base de
# datos no admitiría la fila—, así que borrar una ficha que está en el almacén contesta 409 con su
# cuenta, en vez de reventar al guardar. El agricultor que quiera quitar ese producto de la cesta
# tiene su camino: anular o borrar antes lo que lo usa, o corregir la ficha en vez de borrarla.
COLUMNAS = {
    "producto_id": ["articulos", "lineas_de_factura", "tratamientos"],
    "fertilizante_id": ["articulos", "fertilizaciones", "lineas_de_factura"],
    "aplicador_id": ["tratamientos"],
    "asesor_id": ["tratamientos"],
    "equipo_id": ["labores", "tratamientos"],
    "instalacion_id": ["analiticas", "tratamientos"],
}

# Y las rutas nuevas, escritas a mano: si alguna desaparece, la prueba de las rutas lo dice.
RUTAS_NUEVAS = {
    ("PUT", "/api/productos/{producto_id}"),
    ("DELETE", "/api/productos/{producto_id}"),
    ("PUT", "/api/fertilizantes/{fertilizante_id}"),
    ("DELETE", "/api/fertilizantes/{fertilizante_id}"),
    ("PUT", "/api/aplicadores/{aplicador_id}"),
    ("DELETE", "/api/aplicadores/{aplicador_id}"),
    ("PUT", "/api/asesores/{asesor_id}"),
    ("DELETE", "/api/asesores/{asesor_id}"),
    ("PUT", "/api/equipos/{equipo_id}"),
    ("DELETE", "/api/equipos/{equipo_id}"),
    ("PUT", "/api/instalaciones/{instalacion_id}"),
    ("DELETE", "/api/instalaciones/{instalacion_id}"),
}


def _la_ficha(cliente, cabeceras, maestro: Maestro, **cambios) -> dict:
    """Da de alta una ficha como lo hace la pantalla, con lo que pruebe cada test."""
    respuesta = cliente.post(maestro.ruta, headers=cabeceras, json={**maestro.alta, **cambios})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _las_fichas(cliente, cabeceras, maestro: Maestro) -> list[dict]:
    respuesta = cliente.get(maestro.ruta, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _auditoria(db, entidad: str, entidad_id: int, accion: str):
    """El rastro que ha dejado una corrección o un borrado."""
    return list(
        db.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == entidad,
                models.Auditoria.entidad_id == entidad_id,
                models.Auditoria.accion == accion,
            )
        )
    )


def _lo_guardado(db, maestro: Maestro, ficha_id: int):
    """La fila de verdad, leída de la tabla.

    Se mira la base de datos y no la API cuando el dato que hay que comprobar **no sale por la API**
    (el número de serie, las observaciones de la nave, la fecha en que se apuntó).
    """
    fila = db.scalar(select(maestro.modelo).where(maestro.modelo.id == ficha_id))
    assert fila is not None, "la ficha ha desaparecido de la tabla"
    return fila


def _el_apunte_de(cliente, cabeceras, maestro: Maestro, apunte: dict) -> dict:
    """El apunte que usa la ficha, leído de la lista de apuntes del cuaderno."""
    listado = cliente.get(maestro.lista_de_apuntes, headers=cabeceras)
    assert listado.status_code == 200, listado.text
    return [fila for fila in listado.json() if fila["id"] == apunte["id"]][0]


@pytest.fixture
def piezas(campana, parcela, producto, fertilizante, equipo) -> dict:
    """Todo lo que hace falta para apuntar algo que use una ficha.

    El producto, el abono y la máquina que se usan de base son los de la suite
    (`tests.conftest`), no los de la prueba: lo que se prueba es la ficha que se acaba de dar de alta,
    y el resto de la petición tiene que ser correcto para que el apunte se pueda guardar.
    """
    return {
        "campana": campana,
        "parcela": parcela,
        "producto": producto,
        "fertilizante": fertilizante,
        "equipo": equipo,
    }


# --------------------------------------------------------------------------
# Corregir
# --------------------------------------------------------------------------


class TestCorregirUnaFicha:
    @pytest.mark.parametrize("maestro", MAESTROS)
    def test_cambia_los_datos_y_sigue_siendo_la_misma_ficha(self, cliente, cuenta, maestro):
        """Corregir es cambiar esa ficha, no dar de alta otra.

        No es un detalle de estilo: de ella cuelgan los apuntes (qué producto se echó, quién lo echó,
        con qué máquina), y el identificador es el que viaja a la Junta. Si corregir diera de alta
        otra, la ficha con los apuntes se quedaría con los datos malos.
        """
        ficha = _la_ficha(cliente, cuenta["cabeceras"], maestro)

        respuesta = cliente.put(
            f"{maestro.ruta}/{ficha['id']}",
            headers=cuenta["cabeceras"],
            json=maestro.correccion,
        )

        assert respuesta.status_code == 200, respuesta.text
        corregida = respuesta.json()
        assert corregida["id"] == ficha["id"], "es la misma ficha, no otra"
        assert corregida[maestro.campo] == maestro.valor

        listado = _las_fichas(cliente, cuenta["cabeceras"], maestro)
        assert [fila["id"] for fila in listado] == [ficha["id"]], "no hay dos fichas"
        assert listado[0][maestro.campo] == maestro.valor

    @pytest.mark.parametrize("maestro", MAESTROS)
    def test_lo_que_habia_queda_en_el_rastro(self, cliente, cuenta, db_sesion, maestro):
        """El cuaderno enseña lo nuevo y el programa **sí sabe** qué decía antes, campo por campo."""
        ficha = _la_ficha(cliente, cuenta["cabeceras"], maestro)
        antes = ficha[maestro.campo]

        cliente.put(
            f"{maestro.ruta}/{ficha['id']}",
            headers=cuenta["cabeceras"],
            json=maestro.correccion,
        )

        rastro = _auditoria(db_sesion, maestro.nombre, ficha["id"], "corregir")
        assert len(rastro) == 1
        assert rastro[0].datos[maestro.campo] == [antes, maestro.valor]
        assert rastro[0].fecha is not None
        assert rastro[0].usuario_id == cuenta["usuario_id"], "queda quién lo corrigió"

    @pytest.mark.parametrize("maestro", MAESTROS)
    def test_una_correccion_que_no_cumple_las_reglas_del_alta_se_rechaza(
        self, cliente, cuenta, maestro
    ):
        """Corregir no puede ser la puerta de atrás para meter lo que el alta no deja.

        Se prueba con lo mismo que rechaza el alta de cada ficha: una dosis de cero, una riqueza de
        más de 100, un tipo de carné que no existe, un ámbito inventado, una ficha sin nombre y un
        tipo de instalación que no está en la lista.
        """
        ficha = _la_ficha(cliente, cuenta["cabeceras"], maestro)

        respuesta = cliente.put(
            f"{maestro.ruta}/{ficha['id']}",
            headers=cuenta["cabeceras"],
            json=maestro.alta_que_no_vale,
        )

        assert respuesta.status_code == 422, respuesta.text
        # Y la ficha sigue como estaba: una corrección rechazada no la deja a medias.
        guardada = _las_fichas(cliente, cuenta["cabeceras"], maestro)[0]
        assert guardada[maestro.campo] == ficha[maestro.campo]
        for nombre in maestro.alta:
            if nombre in guardada:
                assert guardada[nombre] == ficha[nombre], f"{nombre} se ha quedado a medias"

    @pytest.mark.parametrize("maestro", MAESTROS)
    def test_la_ficha_de_otra_finca_no_se_toca(self, cliente, cuenta, crear_cuenta, maestro):
        """Corregir la ficha de otro agricultor contesta lo mismo que si no existiera (404, no 403)."""
        ficha = _la_ficha(cliente, cuenta["cabeceras"], maestro)
        otro = crear_cuenta("otro@ejemplo.test")

        respuesta = cliente.put(
            f"{maestro.ruta}/{ficha['id']}",
            headers=otro["cabeceras"],
            json=maestro.correccion,
        )

        assert respuesta.status_code == 404
        assert (
            _las_fichas(cliente, cuenta["cabeceras"], maestro)[0][maestro.campo]
            == ficha[maestro.campo]
        )

    @pytest.mark.parametrize("maestro", MAESTROS)
    def test_sin_entrar_no_se_corrige_nada(self, cliente, cuenta, maestro):
        ficha = _la_ficha(cliente, cuenta["cabeceras"], maestro)

        respuesta = cliente.put(f"{maestro.ruta}/{ficha['id']}", json=maestro.correccion)

        assert respuesta.status_code == 401


# --------------------------------------------------------------------------
# Borrar
# --------------------------------------------------------------------------


class TestBorrarUnaFicha:
    @pytest.mark.parametrize("maestro", MAESTROS)
    def test_se_borra_la_que_no_usa_nadie_y_desaparece_del_listado(
        self, cliente, cuenta, maestro
    ):
        """Una ficha recién apuntada, con la que no se ha hecho nada, se borra sin más.

        Es el caso normal de «me he equivocado al darla de alta»: un producto que no llegó a usarse,
        una máquina que estaba repetida. Si esto no se pudiera deshacer, la lista se llenaría de
        fichas mal escritas que después salen en los desplegables.
        """
        ficha = _la_ficha(cliente, cuenta["cabeceras"], maestro)

        respuesta = cliente.delete(f"{maestro.ruta}/{ficha['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json() == {"borrado": True, "id": ficha["id"]}
        assert _las_fichas(cliente, cuenta["cabeceras"], maestro) == []
        # Y borrarla otra vez contesta lo mismo que si no existiera.
        assert (
            cliente.delete(
                f"{maestro.ruta}/{ficha['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 404
        )

    @pytest.mark.parametrize("maestro", MAESTROS)
    def test_lo_borrado_queda_escrito_en_el_rastro(self, cliente, cuenta, db_sesion, maestro):
        """El cuaderno no la enseña, y el programa sí sabe qué había y qué día se borró."""
        ficha = _la_ficha(cliente, cuenta["cabeceras"], maestro)

        cliente.delete(f"{maestro.ruta}/{ficha['id']}", headers=cuenta["cabeceras"])

        rastro = _auditoria(db_sesion, maestro.nombre, ficha["id"], "borrar")
        assert len(rastro) == 1
        assert rastro[0].datos[maestro.campo] == ficha[maestro.campo]
        assert rastro[0].fecha is not None
        assert rastro[0].usuario_id == cuenta["usuario_id"]

    @pytest.mark.parametrize("maestro", MAESTROS)
    def test_una_ficha_que_esta_dentro_de_un_apunte_no_se_borra(
        self, cliente, cuenta, db_sesion, piezas, maestro
    ):
        """Borrar la ficha que usa un apunte lo dejaría diciendo algo que ya no se sabe qué era."""
        ficha = _la_ficha(cliente, cuenta["cabeceras"], maestro)
        apunte = maestro.usa(cliente, cuenta["cabeceras"], piezas, ficha["id"])

        respuesta = cliente.delete(f"{maestro.ruta}/{ficha['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 409, respuesta.text
        assert respuesta.json()["detail"] == textos.mensaje_con_cuenta("B5_en_uso", 1)
        # Y sigue ahí, y su apunte sigue apuntando a ella.
        assert ficha["id"] in [
            fila["id"] for fila in _las_fichas(cliente, cuenta["cabeceras"], maestro)
        ]
        sigue = db_sesion.scalar(select(maestro.apuntes).where(maestro.apuntes.id == apunte["id"]))
        assert sigue is not None, "el apunte ha desaparecido con la ficha"
        assert getattr(sigue, maestro.columna) == ficha["id"]

        # Y la lista de apuntes del cuaderno lo sigue enseñando. Ojo con un detalle que no es de esta
        # ronda pero conviene dejar escrito: `FertilizacionSalida` **no devuelve el identificador del
        # abono** (devuelve su nombre copiado), así que de ese apunte solo se puede comprobar por la
        # API que sigue en la lista; a qué ficha apunta se comprueba en la tabla, aquí arriba.
        guardado = _el_apunte_de(cliente, cuenta["cabeceras"], maestro, apunte)
        if maestro.columna in guardado:
            assert guardado[maestro.columna] == ficha["id"]

    @pytest.mark.parametrize("maestro", MAESTROS)
    def test_el_mensaje_dice_cuantas_cosas_la_usan_y_que_hacer(
        self, cliente, cuenta, piezas, maestro
    ):
        """El «no» con el número delante y con las dos salidas: sin eso deja al agricultor parado.

        Se apuntan **dos** cosas que la usan, para comprobar que la cuenta las suma y no se queda en
        una (y que el mensaje pasa a plural, que es lo que hace que no parezca escrito por una
        máquina).
        """
        ficha = _la_ficha(cliente, cuenta["cabeceras"], maestro)
        maestro.usa(cliente, cuenta["cabeceras"], piezas, ficha["id"])
        maestro.usa(cliente, cuenta["cabeceras"], piezas, ficha["id"], fecha="2026-05-02")

        respuesta = cliente.delete(f"{maestro.ruta}/{ficha['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 409
        detalle = respuesta.json()["detail"]
        assert "2 apuntes" in detalle, detalle
        assert "Cámbialos o bórralos antes" in detalle, detalle
        assert "corrige esto en vez de borrarlo" in detalle, detalle

    @pytest.mark.parametrize("maestro", MAESTROS)
    def test_la_ficha_de_otra_finca_no_se_borra(self, cliente, cuenta, crear_cuenta, maestro):
        ficha = _la_ficha(cliente, cuenta["cabeceras"], maestro)
        otro = crear_cuenta("otro@ejemplo.test")

        respuesta = cliente.delete(f"{maestro.ruta}/{ficha['id']}", headers=otro["cabeceras"])

        assert respuesta.status_code == 404
        assert len(_las_fichas(cliente, cuenta["cabeceras"], maestro)) == 1

    @pytest.mark.parametrize("maestro", MAESTROS)
    def test_sin_entrar_no_se_borra_nada(self, cliente, cuenta, maestro):
        ficha = _la_ficha(cliente, cuenta["cabeceras"], maestro)

        assert cliente.delete(f"{maestro.ruta}/{ficha['id']}").status_code == 401


# --------------------------------------------------------------------------
# Qué se cuenta antes de borrar
# --------------------------------------------------------------------------


class TestLoQueSeCuentaAntesDeBorrar:
    """La cuenta de lo que usa una ficha se saca de la base de datos, y esto la mantiene honesta."""

    @pytest.mark.parametrize("columna", sorted(COLUMNAS))
    def test_las_tablas_que_apuntan_a_cada_ficha_se_cuentan_todas(self, columna):
        """Las que hay hoy, por su nombre.

        Si mañana se añade un apunte nuevo que use una ficha —como se añadieron los análisis y las
        ventas a las tierras—, esta prueba falla y obliga a decidir: o cuenta como dependencia, o hay
        que escribir por qué no. Sin ella, la cuenta se quedaría corta en silencio y borrar una ficha
        reventaría al guardar (la base de datos no deja un apunte sin su ficha) o, peor, se llevaría
        el apunte por delante.
        """
        from app import correcciones

        assert [
            modelo.__tablename__ for modelo in correcciones.tablas_que_apuntan_a(columna)
        ] == COLUMNAS[columna]

    def test_el_almacen_no_es_una_tabla_mas(self):
        """«Situación Cesta» no se lleva en una tabla: se calcula de lo comprado y lo gastado.

        Por eso el producto tiene las tablas que lo usan —los tratamientos, que dicen lo gastado, y
        las líneas de factura, que dicen lo comprado— y no hay ninguna tabla de la cesta que borrar.
        Se prueba a propósito, porque es la clase de suposición que hace que alguien cuente una tabla
        que no existe y no cuente la que sí.

        **Desde T09 (03/10/2026) hay además un libro de movimientos del almacén**
        (`movimientos_de_existencias`), y no contradice esto: el libro cuenta **lo que entró por el
        albarán y lo que salió con su apunte**, y la cesta sigue calculándose igual, de las facturas y
        de los tratamientos. Son dos vistas distintas de lo mismo y **no se suman** (el porqué, en
        `servicios.py` y en `tests/test_recepciones_lotes_y_movimientos.py`). Lo que esta prueba sigue
        diciendo es que la cesta no vive en ninguna tabla.
        """
        from app import correcciones

        assert "producto_id" in models.TratamientoFitosanitario.__table__.columns
        assert "producto_id" in models.LineaDeFactura.__table__.columns
        assert "movimientos" not in [
            modelo.__tablename__ for modelo in correcciones.tablas_que_apuntan_a("producto_id")
        ]

    def test_un_abono_que_esta_en_un_plan_no_se_borra(self, cliente, cuenta, campana, parcela):
        """El plan de abono no tiene una columna que apunte al abono, pero lo usa de verdad.

        `planes_abonado.detalle` es una columna JSON: dentro guarda qué abono se piensa echar, con su
        identificador y su nombre. Y el papel del cuaderno **saca el nombre del abono de la ficha**
        cuando el plan solo trae la ficha (`routers/cuaderno.py`). Si se pudiera borrar, el plan se
        imprimiría sin decir qué abono pensaba echar, y sin que nada avisara: no hay clave foránea ni
        cascada que lo impida. Por eso se cuenta aparte, y aquí se prueba que se cuenta.
        """
        abono = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Urea 46", "tipo": "mineral", "riqueza_n": 46.0},
        ).json()
        plan = cliente.post(
            "/api/planes",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "parcela_id": parcela["id"],
                "cultivo": "Trigo blando",
                "superficie_ha": 2.43,
                "detalle": [
                    {"fertilizante_id": abono["id"], "kg_ha": 300.0, "momento": "fondo"}
                ],
            },
        )
        assert plan.status_code == 201, plan.text

        respuesta = cliente.delete(
            f"/api/fertilizantes/{abono['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == textos.mensaje_con_cuenta("B5_en_uso", 1)
        assert len(cliente.get("/api/fertilizantes", headers=cuenta["cabeceras"]).json()) == 1

    def test_un_abono_sin_plan_y_sin_apuntes_si_se_borra(self, cliente, cuenta, fertilizante):
        """Y el plan solo cuenta cuando lleva esa ficha dentro, no siempre."""
        assert (
            cliente.delete(
                f"/api/fertilizantes/{fertilizante['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 200
        )

    def test_un_producto_enganchado_a_una_factura_tampoco_se_borra(self, cliente, cuenta):
        """La línea de factura engancha el producto para saber cuánto se ha comprado de él.

        Sin esa ficha, la cesta no puede comparar lo comprado con lo gastado, que es justo lo que
        contesta el botón «Situación Cesta».
        """
        producto = _la_ficha(cliente, cuenta["cabeceras"], POR_NOMBRE["producto"])
        factura = cliente.post(
            "/api/facturas",
            headers=cuenta["cabeceras"],
            data={
                "datos": json.dumps(
                    {
                        "fecha": "2026-03-15",
                        "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
                        "numero_factura": "2026/00123",
                        "lineas": [
                            {
                                "descripcion": "EJEMPLO 25 EC 20 L",
                                "cantidad": 40,
                                "unidad": "L",
                                "producto_id": producto["id"],
                            }
                        ],
                    }
                )
            },
        )
        assert factura.status_code == 201, factura.text
        assert factura.json()["lineas"][0]["producto_id"] == producto["id"]

        borrado = cliente.delete(
            f"/api/productos/{producto['id']}", headers=cuenta["cabeceras"]
        )

        assert borrado.status_code == 409
        assert borrado.json()["detail"] == textos.mensaje_con_cuenta("B5_en_uso", 1)


# --------------------------------------------------------------------------
# Lo que la corrección no puede borrar
# --------------------------------------------------------------------------


class TestLoQueLaCorreccionNoPuedeBorrar:
    """La regla que protege lo que el formulario no puede devolver, con nombre y comprobada."""

    @pytest.mark.parametrize("maestro", MAESTROS)
    def test_solo_se_corrige_lo_que_el_formulario_puede_mandar_de_vuelta(self, maestro):
        """**Solo se cambia lo que la API acepta al dar de alta y devuelve al leer.**

        El formulario de corregir se rellena con lo que devuelve la API, así que una columna que no
        sale en la respuesta es un dato que el agricultor no puede mandar de vuelta: copiarla del
        registro preparado lo **borraría** sin que nadie se entere (y sin que la auditoría lo dijera,
        porque estaría comparando el valor nuevo contra sí mismo).

        En el producto y en el abono no hay ninguna de esas columnas hoy —todo lo que la tabla guarda
        se puede dar de alta, leer y corregir—, y eso también se comprueba: el día que se añada una
        columna que no salga en la respuesta, esta prueba avisa.
        """
        assert sorted(
            router_de_maestros._columnas_que_una_correccion_no_toca(
                maestro.modelo, maestro.entrada, maestro.salida
            )
        ) == sorted(maestro.no_vuelven_al_formulario)

        # Y se quedan fuera por el motivo que dice la regla, no por casualidad.
        for columna in maestro.no_vuelven_al_formulario:
            assert columna not in maestro.salida.model_fields, (
                f"{columna} no se devuelve, así que el formulario no lo tiene"
            )

    @pytest.mark.parametrize("maestro", CON_LO_QUE_NO_SE_DEVUELVE)
    def test_lo_que_la_api_no_devuelve_sobrevive_a_la_correccion(
        self, cliente, cuenta, db_sesion, maestro
    ):
        """El dato que no viaja al móvil no se puede perder al ponerle el nombre bueno a la ficha.

        Son cuatro casos de verdad: el **NIF** del que aplica y del que asesora (está en la tabla y se
        acepta al dar de alta, pero la respuesta no lo devuelve), el **número de serie** de la máquina
        y las **observaciones** de la nave. Y en la nave hay además un quinto, que no se puede mandar
        de ninguna manera: la **fecha en que se apuntó** (`creada_en`), que se llama en femenino y por
        eso se le escapa la protección de `correcciones` (que cuida `creado_en`).
        """
        ficha = _la_ficha(
            cliente, cuenta["cabeceras"], maestro, **maestro.se_manda_y_no_vuelve
        )
        for columna, valor in maestro.se_manda_y_no_vuelve.items():
            # Primero: se ha aceptado al dar de alta y **no vuelve**. Si volviera, el formulario lo
            # tendría y no haría falta esta protección.
            assert columna not in ficha, f"{columna} sí vuelve, así que el formulario lo tiene"
            assert getattr(_lo_guardado(db_sesion, maestro, ficha["id"]), columna) == valor

        antes = getattr(_lo_guardado(db_sesion, maestro, ficha["id"]), "creada_en", None)

        respuesta = cliente.put(
            f"{maestro.ruta}/{ficha['id']}",
            headers=cuenta["cabeceras"],
            json=maestro.correccion,
        )
        assert respuesta.status_code == 200, respuesta.text

        db_sesion.expire_all()
        guardada = _lo_guardado(db_sesion, maestro, ficha["id"])
        assert str(getattr(guardada, maestro.campo)) == str(maestro.valor), (
            "la corrección no se ha guardado"
        )
        for columna, valor in maestro.se_manda_y_no_vuelve.items():
            assert getattr(guardada, columna) == valor, f"la corrección ha borrado {columna}"
        if "creada_en" in maestro.no_vuelven_al_formulario:
            assert antes is not None
            assert guardada.creada_en == antes, "la fecha en que se apuntó no puede cambiar"
        # Y el rastro no puede decir que eso ha cambiado, porque no ha cambiado.
        rastro = _auditoria(db_sesion, maestro.nombre, ficha["id"], "corregir")
        for columna in maestro.no_vuelven_al_formulario:
            assert columna not in rastro[0].datos, f"el rastro dice que {columna} cambió"


# --------------------------------------------------------------------------
# Nada de lo que ya había se ha roto
# --------------------------------------------------------------------------


class TestLaListaDeRutasNoSeHaRoto:
    """Corregir y borrar **se añaden**: nada de lo que ya había puede desaparecer por el camino."""

    def test_las_rutas_de_siempre_siguen_ahi(self):
        """Se mira la lista de rutas que publica la aplicación, no una respuesta.

        Así esta prueba caza una ruta que se pierda aunque su pantalla no se use en ninguna otra
        prueba del fichero. Se lee del esquema que la aplicación publica (`/openapi.json`) y no de
        `app.routes` porque los routers se incluyen en diferido y ahí solo se ven los envoltorios.
        """
        from app.main import app

        esquema = app.openapi()["paths"]
        publicadas = {
            (metodo.upper(), ruta) for ruta, metodos in esquema.items() for metodo in metodos
        }
        de_siempre = {
            ("GET", "/api/productos"),
            ("POST", "/api/productos"),
            ("GET", "/api/productos/{producto_id}"),
            ("GET", "/api/productos/cesta/situacion"),
            ("GET", "/api/fertilizantes"),
            ("POST", "/api/fertilizantes"),
            ("GET", "/api/aplicadores"),
            ("POST", "/api/aplicadores"),
            ("GET", "/api/asesores"),
            ("POST", "/api/asesores"),
            ("GET", "/api/equipos"),
            ("POST", "/api/equipos"),
            ("GET", "/api/instalaciones"),
            ("POST", "/api/instalaciones"),
            ("GET", "/api/instalaciones/{instalacion_id}"),
            ("GET", "/api/avisos"),
        }
        assert de_siempre <= publicadas, f"faltan rutas de antes: {sorted(de_siempre - publicadas)}"
        assert RUTAS_NUEVAS <= publicadas, f"faltan las rutas nuevas: {sorted(RUTAS_NUEVAS - publicadas)}"

    def test_el_alta_y_el_listado_contestan_lo_mismo_que_antes(self, cliente, cuenta):
        """Lo que ya hacían sigue haciéndolo igual: esto es añadir, no cambiar.

        Lo que se ha movido es **el cuerpo del alta** a una función que usan el alta y la corrección
        (`_preparar_X_guardable`). Si ese traslado se hubiera llevado por delante una comprobación o
        una normalización, se vería aquí: el tipo de carné se sigue guardando en minúsculas y sin
        espacios, y los tipos que no existen se siguen rechazando con la lista delante.
        """
        aplicador = cliente.post(
            "/api/aplicadores",
            headers=cuenta["cabeceras"],
            json={"nombre": "Alguien", "tipo_carne": "  Cualificado "},
        )
        assert aplicador.status_code == 201, aplicador.text
        assert aplicador.json()["tipo_carne"] == "cualificado"

        assert (
            cliente.post(
                "/api/aplicadores",
                headers=cuenta["cabeceras"],
                json={"nombre": "Alguien", "tipo_carne": "nivel 2"},
            ).status_code
            == 422
        )
        assert (
            cliente.post(
                "/api/asesores",
                headers=cuenta["cabeceras"],
                json={"nombre": "Ana", "ambito": "de todo un poco"},
            ).status_code
            == 422
        )
        assert (
            cliente.post(
                "/api/instalaciones",
                headers=cuenta["cabeceras"],
                json={"alias": "La nave", "tipo": "castillo"},
            ).status_code
            == 422
        )

        # Y el listado sigue enseñando lo mismo que el alta devuelve.
        listado = cliente.get("/api/aplicadores", headers=cuenta["cabeceras"]).json()
        assert [ficha["id"] for ficha in listado] == [aplicador.json()["id"]]
        assert listado[0]["nombre"] == "Alguien"
