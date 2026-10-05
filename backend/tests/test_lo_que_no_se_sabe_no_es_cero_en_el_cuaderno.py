"""Lo que no se sabe **no se escribe como un cero en el cuaderno**.

POR QUÉ EXISTE ESTE FICHERO (02/10/2026) — es el defecto **A9** de la auditoría de valores por defecto
(`docs/T02_VALORES_POR_DEFECTO.md`), que estaba **documentado y sin arreglar**.

`tratamientos.dosis` y `tratamientos.cantidad_total` **admiten «no se sabe»** desde que se arreglaron los
valores por defecto graves. Pero **las dos salidas del cuaderno seguían escribiendo `0`**:

```python
f"{legal.formatea_numero(t.dosis or 0, 4)} {t.unidad_dosis}"     # el CSV
legal.formatea_numero(t.cantidad_total or 0, 4)                  # el CSV
```

Y eso es lo peor que se puede hacer aquí, por dos motivos:

1. **El CSV y el PDF del cuaderno son el documento que el agricultor firma.** Un cero ahí no es un hueco:
   es una afirmación —«eché cero producto»— que nadie ha hecho.
2. Con la unidad pegada, un hueco se leía «` kg/ha`»: una unidad sin número.

La regla del proyecto está escrita desde el principio —*no conviertas datos ausentes en cero*— y esta misma
fila **ya lo hacía bien con el plazo de seguridad** (`… if … is not None else ""`). Estas dos columnas se
quedaron atrás.

Las dos pruebas de abajo buscan **la cadena exacta que salía con el defecto**, así que **fallan con el
código de antes** y pasan con el de ahora.
"""

from __future__ import annotations

import io


def _un_tratamiento_sin_dosis(cliente, cuenta, campana, parcela, producto) -> dict:
    """Un tratamiento apuntado **sin la dosis**, que es el caso del defecto.

    El programa lo admite a propósito: si el agricultor no la apuntó, el cuaderno tiene que decir que no
    se sabe, no inventarse un cero.
    """
    respuesta = cliente.post(
        "/api/tratamientos",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "fecha": "2026-06-01",
            "parcela_id": parcela["id"],
            "producto_id": producto["id"],
            "justificacion": "Vi la plaga o la hierba en el campo",
            "plazo_reentrada_dias": 3,
            # Las hectáreas sí se saben (el programa las pide): lo que no se apuntó es la **dosis**.
            "superficie_tratada_ha": 2.0,
            # La unidad del producto de prueba («Ejemplo 25 EC» es L/ha). Si saliera un cero inventado,
            # la celda diría exactamente «0,0000 L/ha».
            "unidad_dosis": "L/ha",
        },
    )
    assert respuesta.status_code in (200, 201), respuesta.text
    return respuesta.json()


class TestElCuadernoNoInventaCeros:
    def test_en_el_csv_la_dosis_que_no_se_sabe_sale_vacia(
        self, cliente, cuenta, campana, parcela, producto
    ):
        """**La prueba del defecto.** Antes salía `0,0000 kg/ha`."""
        _un_tratamiento_sin_dosis(cliente, cuenta, campana, parcela, producto)

        csv = cliente.get(
            f"/api/cuaderno/export.csv?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        )
        assert csv.status_code == 200, csv.text
        texto = csv.content.decode("utf-8")

        assert "0,0000 L/ha" not in texto, (
            "el cuaderno escribe «0,0000 L/ha» de un tratamiento cuya dosis no se apuntó: "
            "un cero ahí no es un hueco, es una afirmación que nadie ha hecho"
        )
        assert "; L/ha;" not in texto, (
            "hay una celda que es solo la unidad: la dosis vacía se está escribiendo como « L/ha», "
            "que se lee como un número que falta"
        )

    def test_en_el_pdf_la_dosis_que_no_se_sabe_tampoco_sale_como_cero(
        self, cliente, cuenta, campana, parcela, producto
    ):
        """Y en el PDF, que es **el documento que se firma**, lo mismo."""
        _un_tratamiento_sin_dosis(cliente, cuenta, campana, parcela, producto)

        pdf = cliente.get(
            f"/api/cuaderno/pdf?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        )
        assert pdf.status_code == 200, pdf.text
        assert pdf.content[:4] == b"%PDF", "eso no es un PDF"

        import pdfplumber

        with pdfplumber.open(io.BytesIO(pdf.content)) as documento:
            texto = "\n".join((pagina.extract_text() or "") for pagina in documento.pages)

        # El producto tiene que estar (si no, la prueba no estaría mirando la fila que cree).
        assert producto["nombre_comercial"] in texto, (
            "el producto no aparece en el PDF: la prueba no está mirando donde cree"
        )
        assert "0,00 L/ha" not in texto, (
            "el PDF del cuaderno (el que se firma) escribe «0,00 L/ha» de un tratamiento cuya dosis "
            "no se apuntó"
        )

    def test_lo_que_si_se_apunta_se_sigue_escribiendo(
        self, cliente, cuenta, campana, parcela, producto
    ):
        """El control: la dosis que **sí** se apuntó no puede desaparecer del cuaderno.

        Sin esta prueba, «dejar la celda vacía» podría estar vaciando también lo que se sabe.
        """
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-06-02",
                "parcela_id": parcela["id"],
                "producto_id": producto["id"],
                "justificacion": "Vi la plaga o la hierba en el campo",
                "plazo_reentrada_dias": 3,
                "superficie_tratada_ha": 2.0,
                # Por debajo del tope de la etiqueta del producto de prueba (0,8 L/ha).
                "dosis": 0.5,
                "unidad_dosis": "L/ha",
            },
        )
        assert respuesta.status_code in (200, 201), respuesta.text

        csv = cliente.get(
            f"/api/cuaderno/export.csv?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        )
        texto = csv.content.decode("utf-8")
        assert "0,5000 L/ha" in texto, (
            "la dosis que sí se apuntó (0,5 L/ha) no sale en el cuaderno: "
            "la prueba del defecto estaría vaciando también lo que se sabe"
        )
