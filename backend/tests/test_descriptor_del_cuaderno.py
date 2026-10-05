"""La tabla de campos del descriptor oficial del cuaderno.

Lo que se prueba aquí, y por qué importa:

1. **Que la tabla sale del descriptor que tenemos.** Se compara la huella que la tabla dice
   tener con la huella de verdad del `.xlsx` oficial. Si alguien cambia el Excel y no rehace la
   tabla, esto se pone en rojo: una tabla derivada que se queda vieja es peor que no tenerla.
2. **Que el descriptor y el esquema dicen lo mismo en la raíz.** Son dos documentos oficiales
   distintos, así que comprobar que coinciden es la única forma de saber que se están leyendo
   bien los dos.
3. **Que los catálogos se citan tal y como los escribe el descriptor**, sin traducirlos a los
   identificadores de SIEX, porque esa traducción no está en ningún documento.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app import iuws, iuws_descriptor

RAIZ = Path(__file__).resolve().parents[2]


class TestLaTablaDelDescriptor:
    def test_se_carga_la_tabla_del_proyecto(self):
        assert iuws_descriptor.cargada() is True

    def test_los_numeros_son_los_del_descriptor_oficial(self):
        """107 bloques, 402 campos y 175 obligatorios: los que salen del Excel oficial.

        Los bloques eran 93 cuando la tabla se sacaba mirando solo la llave `{`, y **estaba mal**:
        el descriptor oficial omite la llave en 14 cabeceras de bloque (entre ellas `TratamFito`),
        así que esos 14 bloques se contaban como campos y sus campos colgaban del padre de arriba.
        Se descubrió cruzando la tabla con el esquema. Ver el test de más abajo.
        """
        resumen = iuws_descriptor.resumen()
        assert resumen["bloques"] == 107
        assert resumen["campos"] == 402
        assert resumen["obligatorios"] == 175

    def test_la_tabla_sale_del_descriptor_que_tenemos_y_no_de_otro(self):
        """La huella que la tabla dice tener tiene que ser la del fichero oficial de verdad.

        Esto es lo que impide el fallo silencioso: cambiar el Excel oficial y dejar la tabla
        derivada vieja. Con la huella comparada, no puede pasar sin que salte un test.
        """
        datos = json.loads(iuws_descriptor.RUTA_TABLA.read_text(encoding="utf-8"))
        oficial = RAIZ / "data" / "iuws_fuentes" / datos["fuente"]
        assert oficial.exists(), f"la tabla dice venir de {datos['fuente']}, que no está"
        assert hashlib.sha256(oficial.read_bytes()).hexdigest() == datos["fuente_sha256"]

    def test_la_tabla_dice_que_es_derivada_y_no_oficial(self):
        """Nadie puede confundirla con un documento de la Junta: lo dice ella misma."""
        datos = json.loads(iuws_descriptor.RUTA_TABLA.read_text(encoding="utf-8"))
        assert "DERIVADO" in datos["_leeme"]
        assert "no oficial" in datos["_leeme"]

    def test_sin_tabla_se_dice_que_no_esta_y_no_se_inventa_nada(self, tmp_path):
        """Si el fichero no está, todo sale vacío y se explica por qué.

        Mismo criterio que el resto de listas oficiales del proyecto: el programa funciona sin
        ella y **dice que no la tiene**.
        """
        iuws_descriptor.olvidar()
        try:
            assert iuws_descriptor.cargar(tmp_path / "no-existe.json") is None
            assert iuws_descriptor.cargada() is False
            assert iuws_descriptor.campos() == ()
            assert iuws_descriptor.bloques() == ()
            assert iuws_descriptor.catalogos_que_pide() == ()
            resumen = iuws_descriptor.resumen()
            assert resumen["cargada"] is False
            assert resumen["campos"] == 0
            assert "sacar_campos_del_descriptor" in resumen["por_que_no"]
        finally:
            iuws_descriptor.olvidar()
            iuws_descriptor.cargar()

    def test_un_fichero_ilegible_no_revienta(self, tmp_path):
        """Un JSON roto se trata igual que uno que no está: se dice que no se tiene."""
        roto = tmp_path / "roto.json"
        roto.write_text("{ esto no es json", encoding="utf-8")
        iuws_descriptor.olvidar()
        try:
            assert iuws_descriptor.cargar(roto) is None
            assert iuws_descriptor.cargada() is False
        finally:
            iuws_descriptor.olvidar()
            iuws_descriptor.cargar()


class TestElDescriptorYElEsquemaDicenLoMismo:
    """Dos documentos oficiales distintos: si coinciden en la raíz, se están leyendo bien."""

    def test_los_campos_obligatorios_de_la_raiz_son_los_mismos(self):
        esquema = json.loads(iuws.RUTA_ESQUEMA_OFICIAL.read_text(encoding="utf-8"))
        del_esquema = set(esquema["properties"]["CUADERNO"]["items"]["required"])
        del_descriptor = {c.campo for c in iuws_descriptor.obligatorios_del_bloque("CUADERNO")}
        assert del_descriptor == del_esquema

    def test_los_nombres_de_los_campos_de_la_raiz_son_los_mismos(self):
        """Y con la misma mayúscula exacta: `IdTitular`, no `IDTitular`.

        Esto es justo lo que estaba mal en el sobre de la aplicación, y por eso está aquí.

        Se comparan solo los campos **simples**: en el esquema, `DatosExplotacion` y
        `ActividadesExplotacion` son objetos dentro de la raíz, y en el descriptor son bloques,
        así que no son lo mismo en los dos documentos.
        """
        esquema = json.loads(iuws.RUTA_ESQUEMA_OFICIAL.read_text(encoding="utf-8"))
        propiedades = esquema["properties"]["CUADERNO"]["items"]["properties"]
        simples_del_esquema = {
            nombre for nombre, definicion in propiedades.items() if definicion.get("type") != "object"
        }
        del_descriptor = {c.campo for c in iuws_descriptor.campos_del_bloque("CUADERNO")}
        assert del_descriptor == simples_del_esquema

    def test_las_longitudes_de_los_codigos_coinciden(self):
        """`CodigoSIEX` y `CodigoRea` de 14 caracteres en los dos documentos."""
        esquema = json.loads(iuws.RUTA_ESQUEMA_OFICIAL.read_text(encoding="utf-8"))
        propiedades = esquema["properties"]["CUADERNO"]["items"]["properties"]
        for campo in ("CodigoSIEX", "CodigoRea"):
            assert propiedades[campo]["minLength"] == 14
            assert propiedades[campo]["maxLength"] == 14
        del_descriptor = {c.campo: c.tipo_de_dato for c in iuws_descriptor.campos_del_bloque("CUADERNO")}
        assert del_descriptor["CodigoSIEX"] == "string(14)"
        assert del_descriptor["CodigoRea"] == "string(14)"


class TestLosCatalogos:
    def test_el_descriptor_cita_catalogos(self):
        """La tabla tiene que servir para algo: tiene que decir de qué catálogo sale cada cosa."""
        assert iuws_descriptor.catalogos_que_pide(), "sin catálogos, esta tabla no sirve de nada"

    def test_la_eficacia_del_tratamiento_es_un_catalogo_que_el_descriptor_pide(self):
        """Era una de las lagunas apuntadas: el descriptor **sí** pide ese catálogo.

        Lo que no se sabe es si SIEX publica sus valores; eso es otra cosa y no se dice aquí.
        """
        assert iuws_descriptor.catalogo_de("Eficacia") == "Eficacia del tratamiento"

    def test_los_catalogos_se_citan_tal_y_como_los_escribe_el_descriptor(self):
        """Sin traducirlos a los identificadores de SIEX: esa traducción no está documentada.

        Se comprobó que el descriptor no usa esos identificadores (solo aparecen cuatro nombres
        de registros externos), así que emparejarlos por parecido sería adivinar.
        """
        nombres = {nombre for nombre, _ in iuws_descriptor.catalogos_que_pide()}
        assert "Unidades de Medida" in nombres
        assert "Productos" in nombres
        # Ninguno tiene pinta de identificador de tabla de SIEX (mayúsculas y guiones bajos).
        assert all(not nombre.isupper() for nombre in nombres)

    def test_el_resumen_dice_cuantos_campos_dependen_de_cada_catalogo(self):
        """Para poder decir «faltan estos códigos» y no «faltan códigos»."""
        resumen = iuws_descriptor.resumen()
        assert resumen["catalogos"], "el resumen tiene que llevar los catálogos"
        for entrada in resumen["catalogos"]:
            assert entrada["nombre"]
            assert entrada["campos"] >= 1


class TestBuscarCampos:
    def test_un_nombre_corto_puede_valer_para_varios_bloques_y_se_dicen_todos(self):
        """`DGCs` aparece anidado en nueve bloques: no se elige uno, se devuelven todos.

        Elegir «el más probable» sería adivinar. Si hace falta uno solo, se pasa la ruta entera.
        """
        coinciden = iuws_descriptor.bloques_que_coinciden("DGCs")
        assert len(coinciden) > 1, "si esto falla, el descriptor ha cambiado de forma"
        assert all(ruta.endswith("DGCs") for ruta in coinciden)

        entero = iuws_descriptor.campos_del_bloque(
            "CUADERNO.ActividadesExplotacion.TratamFito.DGCs"
        )
        corto = iuws_descriptor.campos_del_bloque("DGCs")
        assert set(entero) <= set(corto), "el bloque exacto tiene que estar dentro del corto"
        assert len(corto) > len(entero), "el nombre corto junta los de los otros bloques"
        assert entero, "el bloque de las parcelas tratadas tiene campos"

    def test_no_distingue_mayusculas(self):
        assert iuws_descriptor.campos_del_bloque("dgcs") == iuws_descriptor.campos_del_bloque(
            "DGCs"
        )

    def test_un_bloque_que_no_existe_devuelve_vacio_y_no_inventa(self):
        assert iuws_descriptor.campos_del_bloque("BloqueQueNoExiste") == ()
        assert iuws_descriptor.catalogo_de("CampoQueNoExiste") is None

    def test_los_obligatorios_de_un_bloque_son_los_que_marca_el_descriptor(self):
        """En los tratamientos fitosanitarios el descriptor marca la eficacia como obligatoria.

        Y dice de qué catálogo sale, que es lo que hace falta para poder rellenarla.
        """
        campos = {c.campo: c for c in iuws_descriptor.obligatorios_del_bloque("TratamFito")}
        assert campos, "el bloque de tratamientos tiene obligatorios"
        assert "Eficacia" in campos
        assert campos["Eficacia"].tipo_de_dato == "number(1)"
        assert campos["Eficacia"].catalogo == "Eficacia del tratamiento"
        assert "IdAjenaTratamFito" in campos

    def test_el_ultimo_trozo_de_la_ruta_es_el_bloque(self):
        campo = iuws_descriptor.campos_del_bloque("ProductosFito")[0]
        assert campo.bloque.endswith("ProductosFito")
        assert campo.ruta.endswith(campo.campo)

    def test_todos_los_bloques_del_esquema_estan_en_la_tabla(self):
        """El test que habría cazado el fallo de las llaves que faltan.

        El descriptor oficial **omite la llave `{`** en 14 cabeceras de bloque, así que una tabla
        que se fíe solo de la llave pierde esos bloques y cuelga sus campos del bloque de arriba.
        Pasó, y no se notó hasta que se cruzó la tabla con el esquema: `TratamFito` parecía no
        existir en el descriptor.

        Ahora, cada bloque del esquema oficial **tiene que aparecer** en la tabla. Si alguien
        vuelve a cambiar la forma de detectar bloques, esto se pone en rojo.
        """
        esquema = json.loads(iuws.RUTA_ESQUEMA_OFICIAL.read_text(encoding="utf-8"))
        raiz = esquema["properties"]["CUADERNO"]["items"]["properties"]
        for seccion in ("DatosExplotacion", "ActividadesExplotacion"):
            for bloque in raiz[seccion]["properties"]:
                assert iuws_descriptor.bloques_que_coinciden(bloque), (
                    f"{seccion}.{bloque} no aparece en la tabla del descriptor"
                )

    def test_los_bloques_del_descriptor_que_no_estan_en_el_esquema(self):
        """Los dos documentos coinciden en los 20 bloques; el descriptor trae uno de más.

        Antes de arreglar el fallo de las llaves, esto decía lo contrario («el descriptor no tiene
        `TratamFito`»), y era falso. Queda fijado para que no se vuelva a escribir.
        """
        esquema = json.loads(iuws.RUTA_ESQUEMA_OFICIAL.read_text(encoding="utf-8"))
        raiz = esquema["properties"]["CUADERNO"]["items"]["properties"]
        del_esquema = set()
        for seccion in ("DatosExplotacion", "ActividadesExplotacion"):
            del_esquema |= set(raiz[seccion]["properties"])

        assert iuws_descriptor.bloques_que_coinciden("TratamFito")
        assert iuws_descriptor.bloques_que_coinciden("SiembraPlantacion")

        # Lo único que el descriptor tiene y el esquema no es `ActividadAgraria`. Se apunta como
        # dato: si algún día aparece en el esquema, este test lo dirá.
        solo_del_descriptor = {
            b.rsplit(".", 1)[-1]
            for b in iuws_descriptor.bloques()
            if b.count(".") == 2 and b.rsplit(".", 1)[-1] not in del_esquema
        }
        assert solo_del_descriptor == {"ActividadAgraria"}
