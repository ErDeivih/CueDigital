"""**Una tierra dada de alta solo con la referencia del SIGPAC tiene que quedar con sus códigos**
(IMP-25, 08/11/2026).

El fallo se vio con el GeoPackage real de Salamanca: un cliente apuntaba su tierra **solo con la
referencia del papel** (`37-70-0-0-503-51-1`), la tierra se guardaba con `codigo_ine`, `poligono`,
`numero_parcela` y `numero_recinto` **en blanco**, y después el mapa no podía ponerle el contorno
porque no sabía qué recinto buscar. La referencia **lleva dentro los siete números**: el dato estaba
y no tenía puerta.

Aquí se prueba la primera mitad del arreglo, **la del alta** (`POST /api/parcelas`):

  · con solo la referencia, los cuatro códigos quedan rellenos;
  · lo que ya venga informado **no se pisa** (manda el agricultor);
  · una referencia que no se entiende **no bloquea el alta** y no inventa nada;
  · la del visor (seis números) no trae recinto: ese campo se queda en blanco, no se adivina.

La segunda mitad (que las tierras **ya guardadas** casen al leer el mapa) está en
`tests/test_geopackage_sigpac.py`: `test_una_parcela_guardada_solo_con_la_referencia_casa`.

No se sale a internet: el alta solo lee la referencia, no pregunta al SIGPAC.
"""

from __future__ import annotations

from app import models


def _el_alta(cliente, cabeceras, **cambios) -> dict:
    datos = {"alias": "El Prado", "superficie_ha": 4.9016}
    datos.update(cambios)
    respuesta = cliente.post("/api/parcelas", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_el_alta_solo_con_la_referencia_rellena_los_codigos(cliente, cuenta):
    tierra = _el_alta(cliente, cuenta["cabeceras"], ref_sigpac="37-70-0-0-503-51-1")

    assert tierra["codigo_ine"] == "37070"
    assert (tierra["poligono"], tierra["numero_parcela"], tierra["numero_recinto"]) == (503, 51, 1)
    # Los nombres no se inventan desde los códigos: el alta no los toca.
    assert tierra["municipio"] == ""
    assert tierra["provincia"] == ""


def test_la_referencia_del_visor_deja_el_recinto_en_blanco(cliente, cuenta):
    """Seis números: provincia, municipio, agregado, zona, polígono y parcela. El recinto no viene."""
    tierra = _el_alta(cliente, cuenta["cabeceras"], ref_sigpac="37:70:0:0:503:51")

    assert tierra["codigo_ine"] == "37070"
    assert (tierra["poligono"], tierra["numero_parcela"]) == (503, 51)
    assert tierra["numero_recinto"] is None, "el recinto no se adivina"


def test_la_referencia_catastral_tambien_da_los_codigos(cliente, cuenta):
    tierra = _el_alta(cliente, cuenta["cabeceras"], ref_sigpac="37070A50300051000AQ")

    assert tierra["codigo_ine"] == "37070"
    assert (tierra["poligono"], tierra["numero_parcela"]) == (503, 51)


def test_no_se_pisan_los_codigos_que_ya_vienen_informados(cliente, cuenta):
    """Si el agricultor escribió su polígono y su parcela, mandan los suyos aunque no coincidan."""
    tierra = _el_alta(
        cliente,
        cuenta["cabeceras"],
        ref_sigpac="37-70-0-0-503-51-1",
        poligono=999,
        numero_parcela=88,
        codigo_ine="37999",
    )

    assert tierra["poligono"] == 999
    assert tierra["numero_parcela"] == 88
    assert tierra["codigo_ine"] == "37999"
    # Y lo que faltaba sí se completa desde la referencia.
    assert tierra["numero_recinto"] == 1


def test_una_referencia_que_no_se_entiende_no_bloquea_el_alta(cliente, cuenta):
    """Basura en la referencia: la tierra se guarda igual, con los códigos en blanco («no lo sé»)."""
    tierra = _el_alta(cliente, cuenta["cabeceras"], ref_sigpac="esto no son numeros")

    assert tierra["ref_sigpac"] == "esto no son numeros"
    assert tierra["codigo_ine"] is None
    assert tierra["poligono"] is None
    assert tierra["numero_parcela"] is None
    assert tierra["numero_recinto"] is None


def test_una_referencia_con_demasiados_numeros_tampoco_rompe(cliente, cuenta):
    """Ocho números no son ninguna de las tres formas que valen: se guarda igual, sin códigos.

    (La referencia catastral sí se acepta aunque le falte la última letra: así la lee el programa,
    con las tres formas que el agricultor tiene delante.)
    """
    tierra = _el_alta(cliente, cuenta["cabeceras"], ref_sigpac="1-2-3-4-5-6-7-8")

    assert tierra["codigo_ine"] is None
    assert tierra["poligono"] is None
    assert tierra["numero_recinto"] is None


def test_sin_referencia_el_alta_no_se_toca(cliente, cuenta, db_sesion):
    """Sin referencia no hay nada que completar: la tierra se guarda como siempre."""
    tierra = _el_alta(cliente, cuenta["cabeceras"], poligono=12, numero_parcela=3)
    assert tierra["poligono"] == 12 and tierra["numero_parcela"] == 3
    assert tierra["codigo_ine"] is None
    assert tierra["numero_recinto"] is None

    db_sesion.expire_all()
    guardada = db_sesion.get(models.Parcela, tierra["id"])
    assert guardada.numero_recinto is None
