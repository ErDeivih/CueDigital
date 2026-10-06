"""El test que mantiene la promesa de "cero jerga".

Revisar a ojo una pantalla cada vez no funciona: en cuanto pasa un mes, alguien
vuelve a escribir "campo obligatorio". Este test recorre TODOS los textos que puede
llegar a leer un agricultor y falla si aparece una palabra que no diría en voz alta.

Es el caso M-31 del documento del MVP, y es un test automático a propósito.
"""

from __future__ import annotations

import string
import unicodedata

from app import textos


def sin_tildes(texto: str) -> str:
    """Quita las tildes para poder buscar pistas sin pelearse con los acentos.

    Sin esto, "Míralo otra vez" no se detecta buscando "mira", y el test daría un
    falso suspenso sobre un mensaje que sí dice qué hacer.
    """
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn").lower()


class TestSinJerga:
    def test_ningun_texto_lleva_palabras_del_mostrador(self):
        problemas: dict[str, list[str]] = {}
        for texto in textos.textos_visibles():
            # Las direcciones de internet no se revisan: sus palabras son del sitio oficial (ver
            # `textos.es_una_direccion`). Lo que se revisa es el texto del enlace, que sí se lee.
            encontradas = textos.palabras_prohibidas_encontradas(texto)
            if encontradas:
                problemas[texto[:90]] = encontradas
        assert not problemas, f"Hay textos con jerga: {problemas}"

    def test_la_lista_negra_no_se_ha_vaciado(self):
        # Si alguien vacía la lista, el test anterior pasaría sin comprobar nada.
        assert len(textos.PALABRAS_PROHIBIDAS) >= 15
        assert "error" in textos.PALABRAS_PROHIBIDAS
        assert "fitosanitario" in textos.PALABRAS_PROHIBIDAS

    def test_hay_textos_suficientes_que_revisar(self):
        assert len(textos.textos_visibles()) >= 40

    def test_el_detector_detecta_de_verdad(self):
        # Un test que no puede fallar no sirve de nada.
        assert textos.palabras_prohibidas_encontradas("Error de validación") != []
        assert textos.palabras_prohibidas_encontradas("Has puesto más producto del que permite la etiqueta") == []


class TestMensajes:
    def test_todos_los_huecos_tienen_nombre_valido(self):
        analizador = string.Formatter()
        for codigo, plantilla in textos.MENSAJES.items():
            for _literal, campo, _formato, _conversion in analizador.parse(plantilla):
                if campo is None:
                    continue
                assert campo.isidentifier(), f"{codigo}: el hueco {campo!r} no es un nombre válido"

    def test_cada_mensaje_se_puede_rellenar(self):
        """Un mensaje con un hueco que nadie rellena reventaría delante del agricultor."""
        analizador = string.Formatter()
        for codigo, plantilla in textos.MENSAJES.items():
            campos = [c for _l, c, _f, _c in analizador.parse(plantilla) if c]
            relleno = textos.mensaje(codigo, **{campo: "X" for campo in campos})
            assert "{" not in relleno, f"{codigo} se ha quedado sin rellenar"

    def test_un_codigo_que_no_existe_falla_en_alto(self):
        # Preferimos que reviente aquí a que salga un texto vacío en pantalla.
        try:
            textos.mensaje("V999_inventado")
        except KeyError:
            return
        raise AssertionError("Un mensaje inexistente debería dar error")

    def test_los_mensajes_que_bloquean_dicen_que_hacer(self):
        """Estructura obligatoria: qué pasa + qué hago ahora.

        Se comprueba en los mensajes que impiden guardar, que son los que dejan al
        agricultor parado delante de la pantalla.
        """
        bloqueantes = [
            "V1_sin_registro",
            "V1_no_autorizado",
            "V3_dosis_excedida",
            "V4_superficie_excedida",
            "V6_carne_caducado",
            "V6_sin_carne",
            "V7_iteaf_caducada",
            "V7_sin_iteaf",
            "V9_no_puedes_cosechar",
            "V10_sin_justificacion",
            "V15_no_ecologico",
            "V18_sin_parcela",
        ]
        for codigo in bloqueantes:
            mensaje = textos.MENSAJES[codigo]
            assert len(mensaje) > 25, f"{codigo} es demasiado corto para explicar nada"
            plano = sin_tildes(mensaje)
            # Un verbo de instrucción: no vale solo describir el problema.
            pistas = (
                "pon",
                "mira",
                "corrige",
                "bajalo",
                "renueva",
                "cambia",
                "pasala",
                "usa",
                "dinos",
                "tienes",
                "podras",
                "pregunta",
                "revisa",
            )
            assert any(pista in plano for pista in pistas), (
                f"{codigo} no dice qué hacer: {mensaje}"
            )


class TestSingularYPlural:
    def test_el_singular_y_el_plural_estan_los_dos(self):
        """ "1 apuntes" es lo primero que hace desconfiar de un programa."""
        for base in ("A6", "A7", "A9"):
            assert textos.MENSAJES.get(f"{base}_uno"), f"falta {base}_uno"
            assert textos.MENSAJES.get(f"{base}_varios"), f"falta {base}_varios"

    def test_los_textos_que_llevan_cuenta_tienen_singular_y_plural(self):
        """Los demás textos con el número delante también (rediseño de la ronda 84).

        Estos se quedaron con el plural cuando se arreglaron los mensajes: la lista de papeles decía «Tienes
        1 papeles guardados», «qué hay sembrado» decía «A 1 parcelas les falta decir qué tienen este año» y
        el aviso de la cabecera, «1 cosas apuntadas esperando a que haya cobertura» —justo el aviso que sale
        cuando el agricultor está en el campo sin cobertura—. Ahora el servidor manda las dos formas y el
        singular se elige con el número; esta prueba es la que impide que el siguiente texto de cuenta
        llegue solo en plural.
        """
        for diccionario, base, donde in (
            (textos.CULTIVOS, "faltan", "qué hay sembrado"),
            (textos.CESTA, "cuantos", "lo que tengo en el almacén"),
            (textos.DOCUMENTOS, "cuantos", "los papeles"),
            (textos.INTERFAZ, "pendientes", "el aviso de apuntes sin mandar"),
            (textos.CUADERNO_CYL, "hojas_datos", "el cuaderno de la Junta"),
            # **Los pies de las tablas del ordenador** (30/09/2026). Se añadieron aquí después de verlo en
            # una captura: las claves del singular estaban escritas `_una` («1 tierra», «1 factura», que son
            # femeninas) y el ayudante `conCuenta` busca `_uno`, así que con una sola tierra la tabla decía
            # **«1 tierras»** y con una sola factura, «1 facturas». Esta prueba es la que existe para esto.
            (textos.TABLA, "resumen_tierras", "el pie de la tabla de tierras"),
            (textos.TABLA, "resumen_apuntes", "el pie de la tabla del cuaderno"),
            (textos.TABLA, "resumen_anos", "el pie de la tabla de los años"),
            (textos.TABLA, "resumen_facturas", "el pie de la tabla de facturas"),
            (textos.TABLA, "resumen_facturas_sin_total", "el pie cuando falta el total"),
            (textos.TABLA, "firmados", "los apuntes firmados"),
            # **Qué tiene dentro un año, dicho por lo que es** (30/09/2026). Los tres textos llevan número,
            # y el singular importa: «1 tierras con su cultivo dicho» es lo que se leería sin él.
            (textos.CAMPANAS, "apuntes", "lo que tiene dentro un año, en la pantalla de los años"),
            (textos.CAMPANAS, "cultivo_dicho", "las tierras con su cultivo dicho"),
            (textos.CAMPANAS, "otras_cosas", "lo demás que hay dentro de un año"),
            # **El libro del almacén** (T09, 03/10/2026): los albaranes que han llegado y lo que hay
            # apuntado dentro. Con uno solo se leería «Tienes 1 albaranes apuntados», que es lo que
            # esta prueba existe para impedir.
            (textos.ALMACEN, "cuantos_albaranes", "lo que ha llegado al almacén"),
            (textos.ALMACEN, "cuantos_articulos", "lo que hay apuntado en el almacén"),
            # **La bandeja documental (T08, S10, 06/10/2026)**: el pie de la lista de lo que hay que
            # revisar. Con un solo papel se leería «Tienes 1 papeles en la bandeja», que es lo que
            # esta prueba existe para impedir.
            (textos.BANDEJA, "cuantos", "la bandeja de los papeles"),
        ):
            assert diccionario.get(f"{base}_uno"), f"falta el singular de {base} ({donde})"
            assert diccionario.get(base), f"falta el plural de {base} ({donde})"
            # Y el singular no puede llevar el número dentro: es «1 papel», no «{cuantos} papel».
            assert "{cuantos" not in diccionario[f"{base}_uno"], (
                f"el singular de {base} ({donde}) lleva el número dentro"
            )

    def test_con_cuenta_elige_la_forma_y_rellena_el_numero(self):
        """El ayudante que usan los sitios donde el servidor compone la frase."""
        assert textos.con_cuenta(textos.DOCUMENTOS, "cuantos", 1) == "Tienes 1 papel guardado."
        assert textos.con_cuenta(textos.DOCUMENTOS, "cuantos", 3) == "Tienes 3 papeles guardados."
        # Y sin singular escrito, se usa el plural de siempre: en pantalla nunca se queda un hueco.
        assert textos.con_cuenta({"cuantos": "{cuantos} cosas"}, "cuantos", 1) == "1 cosas"
        assert textos.con_cuenta({}, "cuantos", 2) == ""

    def test_con_uno_se_usa_el_singular(self):
        assert textos.mensaje_con_cuenta("A9", 1).startswith("Un apunte no dice")

    def test_con_varios_se_usa_el_plural(self):
        varios = textos.mensaje_con_cuenta("A9", 3)
        assert varios.startswith("3 apuntes no dicen")

    def test_el_singular_no_se_queda_con_un_hueco_sin_rellenar(self):
        assert "{" not in textos.mensaje_con_cuenta("A7", 1)


class TestAyudaPorCampo:
    def test_los_campos_importantes_tienen_explicacion(self):
        importantes = (
            "parcela.ref_sigpac",
            "parcela.superficie_ha",
            "producto.numero_registro",
            "producto.plazo_seguridad_dias",
            "tratamiento.fecha",
            "tratamiento.justificacion",
            "tratamiento.dosis",
            "fertilizacion.kg_ha_producto",
            "fertilizacion.riqueza",
        )
        for campo in importantes:
            datos = textos.ayuda(campo)
            assert datos is not None, f"Falta la explicación de {campo}"

    def test_cada_explicacion_tiene_las_cuatro_partes(self):
        for campo, datos in textos.AYUDA.items():
            for parte in ("titulo", "que_es", "por_que", "ejemplo", "si_falta"):
                assert datos.get(parte), f"{campo} no tiene {parte}"

    def test_cada_explicacion_dice_que_pasa_si_falta_el_dato(self):
        # "si_falta" no puede ser una cadena vacía ni un "—": el agricultor tiene que
        # saber qué se pierde si lo deja en blanco.
        for campo, datos in textos.AYUDA.items():
            assert len(datos["si_falta"]) > 15, f"{campo}: falta explicar las consecuencias"


class TestPorques:
    def test_estan_los_porques_que_importan(self):
        for clave in (
            "para_que_sirve",
            "papel_o_digital",
            "que_pasa_si_no_lo_llevo",
            "por_que_dias_de_espera",
            "por_que_zona_nitratos",
        ):
            assert clave in textos.PORQUE

    def test_cada_porque_tiene_su_titulo_corto(self):
        """En la pantalla de ayuda cada porqué sale **con su nombre** (ronda 83).

        Sin título, los porqués son párrafos largos seguidos y no se sabe dónde acaba uno y empieza el
        siguiente: se leen como un muro. Esta prueba es la que impide que el siguiente porqué que se añada
        llegue sin nombre —y sin nombre no se encuentra—.
        """
        sin_titulo = sorted(clave for clave in textos.PORQUE if not textos.PORQUE_TITULOS.get(clave))
        assert sin_titulo == [], f"estos porqués saldrían sin título en la ayuda: {sin_titulo}"
        sobran = sorted(clave for clave in textos.PORQUE_TITULOS if clave not in textos.PORQUE)
        assert sobran == [], f"hay títulos de porqués que no son de ningún porqué: {sobran}"
        for clave, titulo in textos.PORQUE_TITULOS.items():
            assert len(titulo) <= 45, f"el título de {clave} es un párrafo, no un título: {titulo}"

    def test_cada_punto_de_la_ley_tiene_su_titulo(self):
        """Los seis puntos de la ley, cada uno con su nombre (ronda 83).

        Estaban los seis bajo el mismo rótulo del apartado y se leían como un muro. El título se busca en
        `PANTALLA_AYUDA` con el nombre del punto y la terminación `_titulo`, que es como lo monta `app.js`.
        """
        puntos = [clave for clave in textos.PANTALLA_AYUDA if clave.startswith("ley_") and not clave.endswith("_titulo") and clave != "ley_titulo"]
        assert len(puntos) == 6, f"se esperaban seis puntos de la ley y hay {len(puntos)}: {puntos}"
        for clave in puntos:
            titulo = textos.PANTALLA_AYUDA.get(f"{clave}_titulo", "")
            assert titulo, f"el punto {clave} de la ley saldría sin título en la ayuda"
            assert titulo != textos.PANTALLA_AYUDA["ley_titulo"], (
                f"el punto {clave} repite el rótulo del apartado en vez de tener el suyo"
            )

    def test_el_porque_de_los_plazos_dice_las_fechas_clave(self):
        papel = textos.PORQUE["papel_o_digital"]
        assert "31 de diciembre de 2026" in papel
        assert "1 de enero de 2027" in papel
