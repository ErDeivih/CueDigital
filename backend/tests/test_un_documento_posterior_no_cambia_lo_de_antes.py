"""**Lo de después no reescribe lo de antes** (revision del dueño, 14/10/2026).

El informe del #6 lo pide con estas palabras: «**un documento posterior no cambia una inspeccion
historica**». Y la regla **si esta implementada** -`maquinaria.ultima_inspeccion` ordena por la **fecha
del papel**, y su docstring lo dice: «La fecha del papel manda: una inspeccion de marzo apuntada en junio
es de marzo»-, pero **no habia ni una prueba que la fijara**: era una regla que solo vivia en un
comentario, y una regla que solo vive en un comentario se pierde en el primer arreglo que alguien haga
con prisa.

Los dos casos que se prueban aqui son los dos que el dueño escribio, y son distintos:

1. **Una inspeccion mas VIEJA que llega DESPUES no adelanta a la de antes.** Lo que manda es la fecha del
   papel, no el orden en que se apunto.
2. **Y el papel que se enlaza despues NO toca lo que ya estaba apuntado.** El dato de la inspeccion de
   antes se queda como estaba: enlazar evidencia no reescribe la historia.

Se reutilizan los ayudantes de `test_t14_maquinaria.py` **a proposito**: montar aqui una maquina y una
cuenta paralelas seria una segunda forma de hacer lo mismo, y la segunda forma siempre se separa de la
primera.
"""

from __future__ import annotations

from app import maquinaria
from test_t14_maquinaria import (  # noqa: F401  (los ayudantes son el contrato de montaje del ticket)
    apuntar_inspeccion,
    crear_maquina,
    declarar,
    la_ficha,
    sus_obligaciones,
)


def test_una_inspeccion_mas_vieja_que_llega_despues_no_adelanta_a_la_de_antes(cliente, cuenta):
    """La ultima la decide **la fecha del papel**, no el orden en que se apunto."""
    cabeceras = cuenta["cabeceras"]
    maquina = crear_maquina(cliente, cabeceras)
    declarar(cliente, cabeceras, maquina["id"], "itv")

    # Primero se apunta la de **marzo**, que es la buena.
    la_de_marzo = apuntar_inspeccion(
        cliente, cabeceras, maquina["id"], tipo="itv", fecha="2026-03-14", proxima_fecha="2027-03-14"
    )
    # Y despues llega, con retraso, un papel de **febrero**: mas viejo, apuntado mas tarde.
    la_de_febrero = apuntar_inspeccion(
        cliente, cabeceras, maquina["id"], tipo="itv", fecha="2026-02-01", proxima_fecha="2027-02-01"
    )
    assert la_de_marzo["id"] != la_de_febrero["id"]

    ficha = la_ficha(cliente, cabeceras, maquina["id"])
    itv = sus_obligaciones(ficha)["itv"]
    # **La ultima es la de marzo**, aunque la de febrero se apuntara despues: manda la fecha del papel.
    assert itv["ultima_inspeccion"]["id"] == la_de_marzo["id"], (
        "la ultima inspeccion tiene que ser la del papel mas nuevo, no la que se apunto de ultima"
    )
    assert itv["ultima_inspeccion"]["fecha"] == "2026-03-14"
    # Y la proxima fecha tambien es la suya, no la de la que llego tarde.
    assert itv["proxima_fecha"] == "2027-03-14"


def test_un_papel_que_se_enlaza_despues_no_cambia_la_inspeccion_de_antes(cliente, cuenta):
    """Enlazar evidencia **no reescribe** lo que ya estaba apuntado.

    Es el caso **literal** del informe. Se apunta la inspeccion **sin papel** -que es como llega del
    campo: con la fecha del papel delante y el papel todavia en el movil-, y **despues** se sube el papel
    y se enlaza corrigiendo esa misma inspeccion. Lo que hay que poder afirmar es que **el dato de la
    inspeccion no se movio**: ni la fecha, ni la de la proxima, ni el resultado, ni la fila.

    **La llamada de la correccion esta COPIADA**, no supuesta, de
    `tests/test_revision_t14.py::test_el_papel_de_otra_finca_no_se_puede_enlazar_al_corregir_una_inspeccion`,
    que usa esa misma puerta. Es la unica del proyecto que la usa hoy, y la usa para el aislamiento entre
    fincas; aqui se usa para lo que pide el informe.
    """
    cabeceras = cuenta["cabeceras"]
    maquina = crear_maquina(cliente, cabeceras)
    declarar(cliente, cabeceras, maquina["id"], "iteaf")
    sin_papel = apuntar_inspeccion(
        cliente,
        cabeceras,
        maquina["id"],
        tipo="iteaf",
        fecha="2026-03-14",
        proxima_fecha="2029-03-14",
        resultado="favorable",
    )
    antes = dict(sin_papel)

    # Y **despues** llega el papel: se sube a «los papeles» y se enlaza a la inspeccion ya apuntada.
    papel = cliente.post(
        "/api/documentos",
        headers=cabeceras,
        json={"titulo": "El certificado que llego tarde", "tipo": "otros", "fecha": "2026-03-10"},
    ).json()
    # **Se manda la inspeccion ENTERA, y esto es un dato de la casa que conviene tener escrito**: la
    # correccion de una inspeccion es un **reemplazo completo** -`maquinaria_api.py:910` asigna
    # `proxima_fecha` directamente, sin preguntar si venia en la peticion-, al contrario que el `PUT` de
    # una **obligacion**, que si sigue la regla A1 («lo que la peticion no manda, no se borra»:
    # `maquinaria_api.py:846,851,861`). Mandarla a medias **borra lo que no se manda**, y la pantalla
    # manda el formulario entero. Aqui se hace lo mismo que la pantalla.
    con_papel = cliente.put(
        f"/api/maquinaria/{maquina['id']}/inspecciones/{sin_papel['id']}",
        headers=cabeceras,
        json={
            "tipo": antes["tipo"],
            "fecha": antes["fecha"],
            "resultado": antes["resultado"],
            "proxima_fecha": antes["proxima_fecha"],
            "documento_id": papel["id"],
        },
    )
    assert con_papel.status_code == 200, con_papel.text

    ficha = la_ficha(cliente, cabeceras, maquina["id"])
    iteaf = sus_obligaciones(ficha)["iteaf"]

    # **Lo que el informe pide, palabra por palabra**: el documento posterior no ha cambiado la
    # inspeccion historica. Ni la fecha que traia el papel, ni la de la proxima, ni el resultado.
    assert iteaf["ultima_inspeccion"]["fecha"] == antes["fecha"] == "2026-03-14"
    assert iteaf["proxima_fecha"] == antes["proxima_fecha"] == "2029-03-14"
    assert iteaf["resultado"] == antes["resultado"] == "favorable"
    # Y sigue siendo **la misma fila**: enlazar el papel no creo una inspeccion nueva que sustituya a la
    # de antes, que es la otra forma de «cambiar la historia» sin tocar ningun campo.
    assert iteaf["ultima_inspeccion"]["id"] == sin_papel["id"]
    # Y el papel quedo enlazado, que es lo que se venia a hacer.
    assert iteaf["ultima_inspeccion"]["documento_id"] == papel["id"]
