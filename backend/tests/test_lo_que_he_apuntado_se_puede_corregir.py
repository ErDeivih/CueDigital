"""Corregir y borrar lo que uno ha introducido (ronda 91).

LO QUE SE PRUEBA AQUÍ, Y POR QUÉ

David lo pidió con estas palabras: «recuerda también dejar borrar las cosas que introduzca porque
puede que me equivoque, o modificar también». Hasta esta ronda, un apunte mal metido solo se podía
**anular**, y solo justo después de guardarlo: si se daba cuenta tres días después, o si lo que
estaba mal era la tierra, el producto o los kilos, no había forma de arreglarlo.

Estas pruebas defienden las cuatro cosas que hacen que corregir y borrar sean de fiar, y no un
agujero por el que se cuela un cuaderno que dice lo que no es:

  1. **Corregir cambia ese apunte, no crea otro.** El identificador tiene que seguir siendo el
     mismo: es el `IdAjena` que viaja a la Junta, y dos apuntes donde había uno es un cuaderno que
     dice que se trató dos veces.
  2. **Lo que había no se pierde.** Queda en la auditoría, campo por campo y con la fecha.
  3. **Las reglas son las mismas que al apuntar.** Un apunte corregido pasa por las mismas
     comprobaciones (la dosis de la etiqueta, la superficie, las fechas): si no, corregir sería la
     forma de meter en el cuaderno lo que el alta no deja.
  4. **Lo que se borra de verdad, se va**: de la lista, del cuaderno de la Junta y de los números
     del resumen. Pero el programa se queda sabiendo qué había, y **un apunte firmado no se borra**.
"""

from __future__ import annotations

import json

from app import models, textos

# La fecha de los apuntes de prueba, la misma que usa toda la suite (mayo de 2026: dentro de la
# campaña que crea el alta de cuenta). Se importa y no se copia: dos fechas que se separan son
# apuntes que caen fuera de campaña sin que nadie se entere.
from tests.conftest import FECHA_TRATAMIENTO


def _auditoria(db, entidad: str, entidad_id: int, accion: str):
    from sqlalchemy import select

    return list(
        db.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == entidad,
                models.Auditoria.entidad_id == entidad_id,
                models.Auditoria.accion == accion,
            )
        )
    )


def _firmar_el_apunte(db, cliente, cuenta, entidad: str, entidad_id: int) -> None:
    """Le pone una firma al apunte, como si se hubiera firmado el cuaderno con él dentro.

    Se escribe la fila directamente porque la firma de verdad exige haber entrado con el
    certificado digital (ver `firmas_api`), y lo que se está probando aquí no es la firma: es que
    un apunte firmado no se pueda borrar.
    """
    explotacion_id = cliente.get("/api/cuenta/yo", headers=cuenta["cabeceras"]).json()["explotacion"]["id"]
    db.add(
        models.Firma(
            explotacion_id=explotacion_id,
            entidad=entidad,
            entidad_id=entidad_id,
            huella="0" * 64,
            firmante_nif="70922320A",
            firmante_nombre="David Pérez Velasco",
        )
    )
    db.commit()


class TestCorregirUnTratamiento:
    def test_los_datos_cambiados_son_los_que_se_guardan(
        self, cliente, cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()

        respuesta = cliente.put(
            f"/api/tratamientos/{creado['id']}",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(dosis=0.4, plaga="Pulgón", justificacion="Vi pulgón"),
        )

        assert respuesta.status_code == 200, respuesta.text
        corregido = respuesta.json()
        assert corregido["id"] == creado["id"]
        assert corregido["dosis"] == 0.4
        assert corregido["plaga"] == "Pulgón"
        assert corregido["justificacion"] == "Vi pulgón"

    def test_corregir_no_apunta_otro(
        self, cliente, cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        """El identificador es el mismo, y en la lista sigue habiendo uno: no dos.

        Esto no es un detalle de estilo: lo que se manda a la Junta de cada actividad lleva como
        identificador el `id` de la fila (`IdAjena`). Si corregir creara otra fila, la Junta
        tendría el apunte malo y el bueno, y el cuaderno diría que se trató dos veces.
        """
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        cliente.put(
            f"/api/tratamientos/{creado['id']}",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(dosis=0.4),
        )

        lista = cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json()
        assert [apunte["id"] for apunte in lista] == [creado["id"]]
        assert lista[0]["dosis"] == 0.4

    def test_lo_que_habia_queda_en_el_rastro(
        self, cliente, cuenta, db_sesion, campana, parcela, producto, nuevo_tratamiento
    ):
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        cliente.put(
            f"/api/tratamientos/{creado['id']}",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(dosis=0.4),
        )

        rastro = _auditoria(db_sesion, "tratamiento", creado["id"], "corregir")
        assert len(rastro) == 1
        assert rastro[0].datos["dosis"] == [0.8, 0.4]

    def test_lo_que_cambia_se_recalcula_y_no_se_copia(
        self, cliente, cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        """Los números que el agricultor no calcula se vuelven a calcular.

        Si se copiaran del navegador, un apunte corregido podría quedarse diciendo una cosa en la
        dosis y otra en los kilos totales, que es justo lo que mira la administración.
        """
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento(dosis=0.8)
        ).json()
        assert creado["cantidad_total"] == 1.944  # 0,8 L/ha × 2,43 ha

        corregido = cliente.put(
            f"/api/tratamientos/{creado['id']}",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(dosis=0.4),
        ).json()

        assert corregido["cantidad_total"] == 0.972

    def test_un_cambio_de_fecha_mueve_el_fin_del_plazo(
        self, cliente, cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        """El plazo de seguridad se recalcula: es lo que impide cosechar antes de tiempo."""
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        assert creado["fecha_fin_plazo_seguridad"] == "2026-05-22"

        corregido = cliente.put(
            f"/api/tratamientos/{creado['id']}",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(fecha="2026-05-10"),
        ).json()

        assert corregido["fecha_fin_plazo_seguridad"] == "2026-05-31"

    def test_una_correccion_que_no_cumple_las_reglas_se_rechaza(
        self, cliente, cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        """Corregir no puede ser la puerta de atrás para meter lo que el alta no deja."""
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()

        respuesta = cliente.put(
            f"/api/tratamientos/{creado['id']}",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(dosis=9.9),  # la etiqueta permite 0,8
        )

        assert respuesta.status_code == 422
        assert "Bájalo" in respuesta.text
        # Y lo que había sigue como estaba: una corrección rechazada no deja el apunte a medias.
        guardado = cliente.get(
            f"/api/tratamientos/{creado['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert guardado["dosis"] == 0.8

    def test_el_cultivo_que_ya_habia_declarado_se_sigue_poniendo(
        self, cliente, cuenta, campana, parcela, crear_producto
    ):
        """El «campo calculado» del cuaderno de la Junta también en las correcciones."""
        cliente.post(
            "/api/parcelas/{0}/cultivos".format(parcela["id"]),
            headers=cuenta["cabeceras"],
            json={"campana_id": campana["id"], "especie": "Cebada"},
        )
        producto = crear_producto()
        datos = {
            "campana_id": campana["id"],
            "fecha": FECHA_TRATAMIENTO,
            "parcela_id": parcela["id"],
            "superficie_tratada_ha": 2.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto["id"],
            "dosis": 0.5,
        }
        creado = cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json=datos).json()

        corregido = cliente.put(
            f"/api/tratamientos/{creado['id']}",
            headers=cuenta["cabeceras"],
            json={**datos, "superficie_tratada_ha": 1.5},
        ).json()

        assert corregido["cultivo"] == "Cebada"

    def test_el_apunte_de_otra_finca_no_se_toca(
        self, cliente, cuenta, crear_cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        """Corregir el apunte de otro agricultor contesta lo mismo que si no existiera."""
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        otro = crear_cuenta("otro@ejemplo.test")

        respuesta = cliente.put(
            f"/api/tratamientos/{creado['id']}",
            headers=otro["cabeceras"],
            json=nuevo_tratamiento(),
        )

        assert respuesta.status_code == 404

    def test_sin_entrar_no_se_corrige_nada(self, cliente, cuenta, nuevo_tratamiento):
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        assert cliente.put(f"/api/tratamientos/{creado['id']}", json=nuevo_tratamiento()).status_code == 401


class TestBorrarUnApunte:
    def test_borrar_lo_quita_de_la_lista(
        self, cliente, cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()

        respuesta = cliente.delete(
            f"/api/tratamientos/{creado['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 200, respuesta.text
        assert cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json() == []
        assert (
            cliente.get(f"/api/tratamientos/{creado['id']}", headers=cuenta["cabeceras"]).status_code
            == 404
        )

    def test_lo_borrado_queda_escrito_en_el_rastro(
        self, cliente, cuenta, db_sesion, campana, parcela, producto, nuevo_tratamiento
    ):
        """El cuaderno no lo enseña, y el programa sí sabe qué había y qué día se borró."""
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        cliente.delete(f"/api/tratamientos/{creado['id']}", headers=cuenta["cabeceras"])

        rastro = _auditoria(db_sesion, "tratamiento", creado["id"], "borrar")
        assert len(rastro) == 1
        assert rastro[0].datos["dosis"] == 0.8
        assert rastro[0].datos["producto_nombre"] == "Ejemplo 25 EC"
        assert rastro[0].fecha is not None

    def test_borrar_dos_veces_no_rompe_nada(self, cliente, cuenta, nuevo_tratamiento):
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        assert cliente.delete(
            f"/api/tratamientos/{creado['id']}", headers=cuenta["cabeceras"]
        ).status_code == 200
        assert cliente.delete(
            f"/api/tratamientos/{creado['id']}", headers=cuenta["cabeceras"]
        ).status_code == 404

    def test_borrar_uno_no_toca_los_demas(
        self, cliente, cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        uno = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        otro = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(fecha="2026-05-20", plaga="Otra cosa"),
        ).json()

        cliente.delete(f"/api/tratamientos/{uno['id']}", headers=cuenta["cabeceras"])

        quedan = cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json()
        assert [apunte["id"] for apunte in quedan] == [otro["id"]]

    def test_el_apunte_de_otra_finca_no_se_borra(
        self, cliente, cuenta, crear_cuenta, nuevo_tratamiento
    ):
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        otro = crear_cuenta("otro@ejemplo.test")

        assert cliente.delete(
            f"/api/tratamientos/{creado['id']}", headers=otro["cabeceras"]
        ).status_code == 404
        assert len(cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json()) == 1

    def test_un_apunte_firmado_no_se_borra_y_se_dice_que_hacer(
        self, cliente, cuenta, db_sesion, nuevo_tratamiento
    ):
        """La firma es la prueba de lo que había: borrar el apunte la dejaría mintiendo."""
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        _firmar_el_apunte(db_sesion, cliente, cuenta, "tratamiento", creado["id"])

        respuesta = cliente.delete(
            f"/api/tratamientos/{creado['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == textos.mensaje("B1_firmado_no_se_borra")
        # Y sigue ahí: no se ha borrado «a medias».
        assert len(cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json()) == 1

    def test_un_apunte_firmado_si_se_puede_anular(
        self, cliente, cuenta, db_sesion, nuevo_tratamiento
    ):
        """La salida que da el mensaje tiene que existir de verdad, no solo estar escrita."""
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        _firmar_el_apunte(db_sesion, cliente, cuenta, "tratamiento", creado["id"])

        respuesta = cliente.post(
            f"/api/tratamientos/{creado['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me he equivocado de tierra"},
        )

        assert respuesta.status_code == 200
        assert cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json() == []

    def test_lo_borrado_desaparece_del_cuaderno(
        self, cliente, cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        """Y de los números: si el resumen siguiera contándolo, el cuaderno diría que se trató."""
        uno = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(fecha="2026-05-20"),
        )
        antes = cliente.get("/api/cuaderno/resumen", headers=cuenta["cabeceras"]).json()

        cliente.delete(f"/api/tratamientos/{uno['id']}", headers=cuenta["cabeceras"])

        despues = cliente.get("/api/cuaderno/resumen", headers=cuenta["cabeceras"]).json()
        assert despues["apuntes_de_producto"] == antes["apuntes_de_producto"] - 1


class TestCorregirYborrarAbonos:
    def test_se_corrige_y_los_numeros_se_recalculan(
        self, cliente, cuenta, campana, parcela, fertilizante, nueva_fertilizacion
    ):
        creado = cliente.post(
            "/api/fertilizaciones", headers=cuenta["cabeceras"], json=nueva_fertilizacion()
        ).json()
        assert creado["uf_n_ha"] == 100.5  # 300 kg × 33,5 % de N

        corregido = cliente.put(
            f"/api/fertilizaciones/{creado['id']}",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(kg_ha_producto=200.0),
        ).json()

        assert corregido["id"] == creado["id"]
        assert corregido["kg_ha_producto"] == 200.0
        assert corregido["uf_n_ha"] == 67.0
        assert corregido["cantidad_total_kg"] == 486.0

    def test_el_rastro_del_abono_corregido(
        self, cliente, cuenta, db_sesion, campana, parcela, fertilizante, nueva_fertilizacion
    ):
        creado = cliente.post(
            "/api/fertilizaciones", headers=cuenta["cabeceras"], json=nueva_fertilizacion()
        ).json()
        cliente.put(
            f"/api/fertilizaciones/{creado['id']}",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(kg_ha_producto=200.0),
        )

        rastro = _auditoria(db_sesion, "fertilizacion", creado["id"], "corregir")
        assert rastro[0].datos["kg_ha_producto"] == [300.0, 200.0]

    def test_el_abono_se_borra_y_queda_su_rastro(
        self, cliente, cuenta, db_sesion, campana, parcela, fertilizante, nueva_fertilizacion
    ):
        creado = cliente.post(
            "/api/fertilizaciones", headers=cuenta["cabeceras"], json=nueva_fertilizacion()
        ).json()

        assert cliente.delete(
            f"/api/fertilizaciones/{creado['id']}", headers=cuenta["cabeceras"]
        ).status_code == 200
        assert cliente.get("/api/fertilizaciones", headers=cuenta["cabeceras"]).json() == []
        assert _auditoria(db_sesion, "fertilizacion", creado["id"], "borrar")[0].datos[
            "fertilizante_nombre"
        ] == "Nitrato amónico 33,5%"

    def test_un_abono_de_mas_hectareas_que_la_tierra_no_se_puede_corregir_asi(
        self, cliente, cuenta, campana, parcela, fertilizante, nueva_fertilizacion
    ):
        """Corregir pasa por las mismas comprobaciones que apuntar.

        Se usa la superficie, que sí bloquea: echar abono para más hectáreas de las que tiene la
        tierra es un imposible. (Pasarse del tope de nitrógeno, en cambio, **avisa y no bloquea**,
        y es a propósito: ver lo que obliga la ley.)
        """
        creado = cliente.post(
            "/api/fertilizaciones", headers=cuenta["cabeceras"], json=nueva_fertilizacion()
        ).json()
        respuesta = cliente.put(
            f"/api/fertilizaciones/{creado['id']}",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(superficie_ha=9.0),
        )
        assert respuesta.status_code == 422
        # Y sigue como estaba.
        assert cliente.get(
            "/api/fertilizaciones", headers=cuenta["cabeceras"]
        ).json()[0]["superficie_ha"] == 2.43


class TestCorregirYborrarLabores:
    def _una_labor(self, campana, parcela):
        return {
            "campana_id": campana["id"],
            "tipo": "labrar",
            "fecha": "2026-03-15",
            "parcela_id": parcela["id"],
            "superficie_ha": 2.43,
            "observaciones": "Con el apero de siempre",
        }

    def test_corregir_una_labor(self, cliente, cuenta, campana, parcela):
        creado = cliente.post(
            "/api/labores", headers=cuenta["cabeceras"], json=self._una_labor(campana, parcela)
        ).json()

        corregido = cliente.put(
            f"/api/labores/{creado['id']}",
            headers=cuenta["cabeceras"],
            json={**self._una_labor(campana, parcela), "observaciones": "Al final fue con el vecino"},
        )

        assert corregido.status_code == 200, corregido.text
        assert corregido.json()["id"] == creado["id"]
        assert corregido.json()["observaciones"] == "Al final fue con el vecino"

    def test_las_observaciones_de_una_labor_no_se_pierden_al_corregirla(
        self, cliente, cuenta, campana, parcela
    ):
        """Se guardaban y no se devolvían: corregir la labor las borraba sin decir nada."""
        creado = cliente.post(
            "/api/labores", headers=cuenta["cabeceras"], json=self._una_labor(campana, parcela)
        ).json()
        assert creado["observaciones"] == "Con el apero de siempre"

        corregido = cliente.put(
            f"/api/labores/{creado['id']}",
            headers=cuenta["cabeceras"],
            json={**self._una_labor(campana, parcela), "superficie_ha": 2.0},
        ).json()

        assert corregido["superficie_ha"] == 2.0
        assert corregido["observaciones"] == "Con el apero de siempre"

    def test_una_labor_sin_tierra_no_se_puede_corregir_asi(self, cliente, cuenta, campana, parcela):
        creado = cliente.post(
            "/api/labores", headers=cuenta["cabeceras"], json=self._una_labor(campana, parcela)
        ).json()
        respuesta = cliente.put(
            f"/api/labores/{creado['id']}",
            headers=cuenta["cabeceras"],
            json={**self._una_labor(campana, parcela), "parcela_id": None},
        )
        assert respuesta.status_code == 422
        assert respuesta.json()["detail"] == textos.mensaje("V18_sin_parcela")

    def test_borrar_una_labor(self, cliente, cuenta, db_sesion, campana, parcela):
        creado = cliente.post(
            "/api/labores", headers=cuenta["cabeceras"], json=self._una_labor(campana, parcela)
        ).json()

        assert cliente.delete(
            f"/api/labores/{creado['id']}", headers=cuenta["cabeceras"]
        ).status_code == 200
        assert cliente.get("/api/labores", headers=cuenta["cabeceras"]).json() == []
        assert _auditoria(db_sesion, "labor", creado["id"], "borrar")[0].datos["tipo"] == "labrar"

    def test_una_labor_se_puede_anular(self, cliente, cuenta, campana, parcela):
        """Hasta la ronda 91 no se podía, y el aviso de «está firmado» manda a anular."""
        creado = cliente.post(
            "/api/labores", headers=cuenta["cabeceras"], json=self._una_labor(campana, parcela)
        ).json()

        respuesta = cliente.post(
            f"/api/labores/{creado['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me he equivocado"},
        )

        assert respuesta.status_code == 200
        assert cliente.get("/api/labores", headers=cuenta["cabeceras"]).json() == []


class TestCorregirYborrarLaCosecha:
    def _una_cosecha(self, campana, parcela, **cambios):
        datos = {
            "campana_id": campana["id"],
            "fecha": "2026-08-20",
            "parcela_id": parcela["id"],
            "producto": "Trigo blando",
            "cantidad_kg": 12000.0,
        }
        datos.update(cambios)
        return datos

    def test_la_maquina_de_la_cosecha_ya_no_se_pierde(self, cliente, cuenta, campana, parcela, equipo):
        """El asistente la preguntaba, el navegador la mandaba y se tiraba sin decir nada.

        El esquema no tenía el campo, así que Pydantic la descartaba. El contenido mínimo del CUE
        pide la maquinaria en su hoja de labores, y una cosecha es una labor.
        """
        creado = cliente.post(
            "/api/cosecha",
            headers=cuenta["cabeceras"],
            json=self._una_cosecha(campana, parcela, equipo_id=equipo["id"]),
        ).json()

        guardada = cliente.get("/api/labores", headers=cuenta["cabeceras"]).json()
        la_cosecha = [labor for labor in guardada if labor["id"] == creado["id"]][0]
        assert la_cosecha["equipo_id"] == equipo["id"]

    def test_corregir_una_cosecha_cambia_los_kilos(self, cliente, cuenta, campana, parcela):
        creado = cliente.post(
            "/api/cosecha", headers=cuenta["cabeceras"], json=self._una_cosecha(campana, parcela)
        ).json()

        respuesta = cliente.put(
            f"/api/cosecha/{creado['id']}",
            headers=cuenta["cabeceras"],
            json=self._una_cosecha(campana, parcela, cantidad_kg=15000.0),
        )

        assert respuesta.status_code == 200, respuesta.text
        la_cosecha = [
            labor
            for labor in cliente.get("/api/labores", headers=cuenta["cabeceras"]).json()
            if labor["id"] == creado["id"]
        ][0]
        assert la_cosecha["detalles"]["cantidad_kg"] == 15000.0

    def test_borrar_una_cosecha(self, cliente, cuenta, db_sesion, campana, parcela):
        creado = cliente.post(
            "/api/cosecha", headers=cuenta["cabeceras"], json=self._una_cosecha(campana, parcela)
        ).json()

        assert cliente.delete(
            f"/api/cosecha/{creado['id']}", headers=cuenta["cabeceras"]
        ).status_code == 200
        assert cliente.get("/api/labores", headers=cuenta["cabeceras"]).json() == []
        assert _auditoria(db_sesion, "labor", creado["id"], "borrar")[0].datos["tipo"] == "cosecha"


class TestLoQueNoSeToca:
    def test_una_factura_de_otra_finca_no_se_puede_enlazar_a_un_abono(
        self, cliente, cuenta, crear_cuenta, campana, parcela, fertilizante, nueva_fertilizacion
    ):
        """Un abono no puede salir de la factura de otra finca.

        **Esto no se comprobaba** y se encontró en la ronda 93, al hacer el borrado de facturas: el
        `factura_id` de un abono se copiaba tal cual, así que cualquiera podía dejar su abono apuntando a
        la factura de otro agricultor (y el listado devolvía ese identificador). Es la misma regla que en
        el resto de la API: lo de otra finca no está en tu cuaderno, y se contesta lo mismo que si no
        existiera.
        """
        otro = crear_cuenta("vecino@ejemplo.test", nombre="Vecino")
        # La factura se guarda con `multipart` porque en la misma petición viaja el fichero: los datos van
        # como un JSON dentro del campo `datos` (ver `facturas_api.guardar_una_factura`).
        suya = cliente.post(
            "/api/facturas",
            headers=otro["cabeceras"],
            data={
                "datos": json.dumps(
                    {
                        "proveedor": "Cooperativa del vecino",
                        "numero_factura": "V-1",
                        "fecha": "2026-02-01",
                        "base_imponible": 100.0,
                        "cuota_iva": 21.0,
                        "total": 121.0,
                        "lineas": [],
                    }
                )
            },
        )
        assert suya.status_code == 201, suya.text

        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(factura_id=suya.json()["id"]),
        )

        assert respuesta.status_code == 404
        assert respuesta.json()["detail"] == "Eso no está en tu cuaderno."

    def test_corregir_no_cambia_de_finca(
        self, cliente, cuenta, crear_cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        """La finca del apunte es la que es: una corrección no puede mover un apunte de finca."""
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        cliente.put(
            f"/api/tratamientos/{creado['id']}",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(dosis=0.4),
        )
        assert cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json()[0][
            "id"
        ] == creado["id"]

    def test_el_identificador_y_la_finca_no_son_campos_que_se_copien(self):
        """Lo que `correcciones` no toca nunca, escrito aquí para que no se «arregle» sin querer."""
        from app import correcciones

        for campo in ("id", "explotacion_id", "anulado", "motivo_anulacion"):
            assert campo in correcciones.CAMPO_QUE_NO_SE_TOCA
