"""Sonda temporal: comprobar que las puertas del almacén y de los trabajos contestan."""

from __future__ import annotations


def test_las_puertas_contestar(cliente, cuenta):
    for ruta in (
        "/api/almacen/existencias",
        "/api/productos/cesta/situacion",
        "/api/trabajos/que-falta",
    ):
        respuesta = cliente.get(ruta, headers=cuenta["cabeceras"])
        print(ruta, respuesta.status_code)
        assert respuesta.status_code in (200, 404)
