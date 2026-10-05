"""Lo que se guarda tiene que **caber** en su columna, y decirlo en castellano.

POR QUÉ EXISTE ESTE FICHERO (02/10/2026) — y es un defecto de producción de verdad, medido.

**Un `VARCHAR(n)` en SQLite no comprueba nada**: guarda un texto de 300 caracteres en una columna de 200
tan contento. **En PostgreSQL sí**: la fila se rechaza con `StringDataRightTruncation`, y como el apunte y
su rastro van en la **misma transacción**, **lo que se pierde es la operación entera**.

Lo destapó la revisión de T12 en el dinero (nueve campos), y al medirlo resultó ser **de 170 campos**: los
esquemas de entrada de este programa dejan meter texto sin tope en campos que acaban en columnas con tope.
Es decir: **el mismo cuerpo que se apunta en el ordenador del agricultor no se puede apuntar en
producción**, y como `app.js` reintenta los 5xx **para siempre**, cada uno de esos casos es un bucle.

El arreglo **no son 170 topes escritos a mano** —se quedarían viejos igual que se quedó el `varchar(30)`
del rastro—, sino la comprobación de `database._comprobar_que_los_textos_caben`, que mira **lo que se va a
escribir** justo antes de escribirlo: el día que alguien añada una columna o cambie un ancho, no hay nada
que acordarse. Y de paso arregla la otra mitad: **las dos bases dejan de comportarse distinto**.

Aquí se comprueba el camino entero, con un campo real que **no tiene tope en su esquema**
(`TratamientoEntrada.plaga`, que acaba en `tratamientos.plaga`, de 200 caracteres), así que el 422 que se
mide **no puede venir de la validación del esquema**: viene de esta comprobación.
"""

from __future__ import annotations

from app import models

UN_TEXTO_QUE_NO_CABE = "P" * 300
UN_TEXTO_QUE_SI_CABE = "P" * 200


class TestUnTextoQueNoCabeSeParaAntesDeEscribir:
    def test_por_la_api_es_422_y_no_500(
        self, cliente, cuenta, nuevo_tratamiento_en_instalacion
    ):
        """**422, no 500**: un dato mal mandado no es un fallo del programa.

        Y no es un detalle de estilo: `app.js` **reintenta los 5xx para siempre**, así que un 500 aquí
        dejaría la cola del móvil dando vueltas con el mismo apunte.
        """
        cuerpo = nuevo_tratamiento_en_instalacion(plaga=UN_TEXTO_QUE_NO_CABE)
        respuesta = cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json=cuerpo)
        assert respuesta.status_code == 422, (
            f"se esperaba 422 (dato mal mandado) y salió {respuesta.status_code}: {respuesta.text[:200]}"
        )

    def test_y_el_aviso_dice_que_texto_donde_y_cuanto_cabe(
        self, cliente, cuenta, nuevo_tratamiento_en_instalacion
    ):
        cuerpo = nuevo_tratamiento_en_instalacion(plaga=UN_TEXTO_QUE_NO_CABE)
        respuesta = cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json=cuerpo)
        detalle = respuesta.json().get("detail", "")
        assert "tratamientos.plaga" in detalle, detalle
        assert "300" in detalle and "200" in detalle, detalle
        assert "No se ha guardado nada" in detalle, detalle

    def test_y_no_ha_quedado_ninguna_fila_a_medias(
        self, cliente, cuenta, nuevo_tratamiento_en_instalacion
    ):
        """**La operación entera se para, no se pierde a medias.**

        Es lo que hacía PostgreSQL: el apunte fallaba y con él la transacción. Aquí se comprueba que
        tampoco queda nada escrito.
        """
        antes = cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json()
        cuerpo = nuevo_tratamiento_en_instalacion(plaga=UN_TEXTO_QUE_NO_CABE)
        cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json=cuerpo)
        despues = cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json()
        assert len(despues) == len(antes), f"se ha escrito algo: {antes} → {despues}"

    def test_lo_que_si_cabe_se_guarda_igual(self, cliente, cuenta, nuevo_tratamiento_en_instalacion):
        """El control: la comprobación no puede estorbar a lo que sí cabe.

        Sin esta prueba, un guardián demasiado celoso —que rechazara cualquier texto largo— pasaría las
        tres de arriba y no se notaría.
        """
        cuerpo = nuevo_tratamiento_en_instalacion(plaga=UN_TEXTO_QUE_SI_CABE)
        respuesta = cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json=cuerpo)
        assert respuesta.status_code in (200, 201), respuesta.text[:200]
        assert len(respuesta.json().get("plaga", "")) == 200


class TestLaComprobacionEsDelProgramaYNoDelMotor:
    def test_la_columna_del_ejemplo_mide_lo_que_dice_la_prueba(self):
        """Si alguien cambia el ancho de esa columna, esta prueba lo dice antes que nadie.

        La prueba de arriba mide «300 contra 200»: si la columna pasara a medir 400, la comprobación
        seguiría pasando y **no estaría comprobando nada**.
        """
        ancho = models.Base.metadata.tables["tratamientos"].columns["plaga"].type.length
        assert ancho == 200, (
            f"`tratamientos.plaga` mide {ancho} y esta prueba da por hecho 200: actualiza los textos "
            "largos de arriba (y comprueba que la comprobación sigue cazando el caso)"
        )
        assert len(UN_TEXTO_QUE_NO_CABE) > ancho
        assert len(UN_TEXTO_QUE_SI_CABE) == ancho
