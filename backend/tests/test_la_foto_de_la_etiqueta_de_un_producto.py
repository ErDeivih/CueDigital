"""La foto de la etiqueta del producto (CRM-07 #10, 14/10/2026).

**La columna existia y no la usaba nadie.** `ProductoFitosanitario.foto_etiqueta` (`models.py:439`) se
daba de alta, se leia… y **ningun router la escribia**. El contrato pide «fotos de etiqueta/justificante
**como evidencia**», asi que estas pruebas defienden lo que hace falta para que la promesa sea verdad:

1. **Se sube y se puede ver**: el papel queda guardado y el programa lo sirve.
2. **Un producto sin foto lo dice**: 404, y con su frase, no con una pantalla rota.
3. **Y la foto de una finca no la ve otra**: lo mismo que con cualquier papel del cuaderno.

**Lo que NO se prueba aqui, a proposito**: *que el fichero este en el disco y no en la base*. Eso lo
garantiza `app/adjuntos.py`, que ya tiene sus propias pruebas, y esta puerta **lo usa** en vez de
inventarse otra forma de guardar.
"""

from __future__ import annotations

# Un PNG de mentira pero con su cabecera de verdad: la casa comprueba el tipo del fichero.
UNA_FOTO = b"\x89PNG\r\n\x1a\n" + b"la etiqueta del producto, con su dosis y su plazo"


def _subir(cliente, cuenta, producto, contenido=UNA_FOTO, nombre="etiqueta.png", tipo="image/png"):
    return cliente.post(
        f"/api/productos/{producto['id']}/etiqueta",
        headers=cuenta["cabeceras"],
        files={"fichero": (nombre, contenido, tipo)},
    )


def test_la_foto_de_la_etiqueta_se_sube_y_se_puede_ver(cliente, cuenta, producto):
    subida = _subir(cliente, cuenta, producto)
    assert subida.status_code == 200, subida.text
    # La puerta devuelve la ficha del producto, ya con su foto.
    assert subida.json()["foto_etiqueta"], "la ficha no dice donde quedo la foto"

    vista = cliente.get(f"/api/productos/{producto['id']}/etiqueta", headers=cuenta["cabeceras"])
    assert vista.status_code == 200, vista.text
    assert vista.content == UNA_FOTO, "lo que se sirve no es lo que se subio"


def test_un_producto_sin_foto_lo_dice(cliente, cuenta, producto):
    # Un producto recien dado de alta no tiene foto, y la puerta lo dice con su frase.
    respuesta = cliente.get(f"/api/productos/{producto['id']}/etiqueta", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 404, respuesta.text
    assert "etiqueta" in respuesta.text


def test_la_foto_de_una_finca_no_la_ve_otra(cliente, cuenta, producto, crear_cuenta):
    # **La regla de toda la API**: eso no esta en tu cuaderno. Ni verla, ni subirla.
    assert _subir(cliente, cuenta, producto).status_code == 200
    la_ajena = crear_cuenta("ajena-foto@ejemplo.test", nombre="El vecino")

    ajena = cliente.get(f"/api/productos/{producto['id']}/etiqueta", headers=la_ajena["cabeceras"])
    assert ajena.status_code in (403, 404), ajena.text
    assert ajena.content != UNA_FOTO, "la foto de una finca ha salido por la puerta de otra"


def test_se_puede_volver_a_subir_y_la_nueva_manda(cliente, cuenta, producto):
    # Corregir la foto es subir otra: la ficha se queda con la nueva y la vieja se borra **despues**.
    assert _subir(cliente, cuenta, producto).status_code == 200
    otra = UNA_FOTO + b" (corregida)"
    segunda = _subir(cliente, cuenta, producto, contenido=otra, nombre="etiqueta-2.png")
    assert segunda.status_code == 200, segunda.text

    vista = cliente.get(f"/api/productos/{producto['id']}/etiqueta", headers=cuenta["cabeceras"])
    assert vista.content == otra, "el programa sigue sirviendo la foto vieja"
