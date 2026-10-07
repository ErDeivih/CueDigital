"""La búsqueda global: una caja en la cabecera que busca en todo lo del agricultor.

**Por qué existe** (07/10/2026, del encargo del rediseño, apartado 3: la cabecera lleva «búsqueda
global»). Hasta ahora cada pantalla tenía su buscador —el de tierras, el de cuentas, el del SIGPAC— y no
había ninguna forma de preguntar «¿dónde está esto?» sin saber antes en qué pantalla está.

## Lo que busca hoy, y lo que no

Esta primera puerta busca **en las tierras** —por su nombre (`alias`) y por su referencia oficial
(`ref_sigpac`)— y **en los gastos** (por su concepto, con lo que costaron). Todo **filtrado por la
explotación de la sesión**: lo de otra finca no sale ni aunque se sepa el nombre exacto (y no se dice
que exista).

**Lo que falta, y hay que hacerlo en la vuelta siguiente** (dicho aquí para que no se crea que ya está):
los papeles, las personas y las máquinas. La forma de la respuesta está pensada para eso —grupos de
resultados—, así que añadir cada uno es una consulta más, no un rediseño.

Y falta **la caja en la cabecera**: hoy esta puerta se puede llamar, pero la pantalla que la usa todavía
no existe.

## Cómo se coteja el texto

**Con el mismo cotejo que el buscador de tierras** (`parcelas._como_se_busca`: sin tildes, en minúsculas
y con los espacios de dentro juntos). Es a propósito y está escrito allí por qué: si el servidor junta las
opciones de una manera y la pantalla coteja de otra, los números dejan de cuadrar y el agricultor deja de
creerse lo que lee.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from .. import models, textos
from ..deps import Db, ExplotacionActual
from .parcelas import _como_se_busca

router = APIRouter(prefix="/api", tags=["buscar"])

# Cuántos resultados se devuelven por grupo. **No es una página que se pasa**: es un tope para que una
# búsqueda de una letra no devuelva las 64 tierras y monte una lista que nadie lee. Lo que se corta se
# dice (`cortado`), que es la regla de la casa: un número que calla lo que falta miente.
TOPE_POR_GRUPO = 10

# Y por debajo de esto no se busca: con una letra saldría casi todo, y una lista con casi todo no ayuda a
# encontrar nada. Se dice con una frase en vez de devolver vacío sin explicación.
MINIMO_PARA_BUSCAR = 2


@router.get("/buscar")
def buscar(
    db: Db,
    explotacion: ExplotacionActual,
    texto: str = Query("", description="Lo que se escribe en la caja de la cabecera"),
) -> dict:
    """Busca en lo del agricultor y devuelve los resultados **por grupos**.

    La respuesta dice siempre lo mismo, aunque no haya nada: el texto buscado, si se ha buscado algo (y
    por qué no, cuando es el caso) y los grupos con sus resultados y su cuenta.
    """
    buscado = (texto or "").strip()
    if len(buscado) < MINIMO_PARA_BUSCAR:
        return {
            "texto": buscado,
            "buscado": False,
            "motivo": "muy_corto",
            "grupos": [],
        }

    cotejado = _como_se_busca(buscado)

    # **Las tierras de esta explotación**, por su nombre o por su referencia. El filtro por explotación no
    # es un adorno: es lo que hace que buscar no sea una forma de enterarse de lo que hay en otra finca.
    tierras = db.scalars(
        select(models.Parcela)
        .where(
            models.Parcela.explotacion_id == explotacion.id,
            or_(
                models.Parcela.alias.ilike(f"%{buscado}%"),
                models.Parcela.ref_sigpac.ilike(f"%{buscado}%"),
            ),
        )
        .order_by(models.Parcela.alias)
        .limit(TOPE_POR_GRUPO + 1)
    ).all()

    # Y se coteja también sin tildes, para que «Machacon» encuentre «Machacón» (es el caso que está
    # documentado en `parcelas._como_se_busca`). Se hace en memoria porque son las tierras de una finca
    # —decenas, no miles— y así el cotejo es **exactamente** el mismo que el de la pantalla.
    encontradas = {tierra.id: tierra for tierra in tierras}
    for tierra in db.scalars(
        select(models.Parcela).where(models.Parcela.explotacion_id == explotacion.id)
    ).all():
        if tierra.id in encontradas:
            continue
        if cotejado and cotejado in _como_se_busca(tierra.alias or ""):
            encontradas[tierra.id] = tierra

    suyas = sorted(encontradas.values(), key=lambda tierra: (tierra.alias or "").lower())
    cortado = len(suyas) > TOPE_POR_GRUPO
    suyas = suyas[:TOPE_POR_GRUPO]

    # **Y los gastos** (07/10/2026): lo otro que más se busca con un nombre en la cabeza («el gasóleo»,
    # «la reparación del tractor»). Por el concepto, y **con su importe**, que es lo que se quiere saber
    # al encontrarlo. Un gasto sin importe se enseña igual, sin cifra: callarlo sería esconder que existe.
    #
    # **Se coteja igual que las tierras, y por el mismo motivo**: el concepto guardado lleva sus tildes
    # («Gasóleo») y lo que se teclea casi nunca («gasoleo»), así que un `ilike` a secas no los junta. La
    # primera versión de esto lo hacía con `ilike` y las pruebas lo cazaron.
    candidatos = db.scalars(
        select(models.Gasto)
        .where(models.Gasto.explotacion_id == explotacion.id)
        .order_by(models.Gasto.fecha.desc().nullslast())
    ).all()
    gastos = [gasto for gasto in candidatos if cotejado and cotejado in _como_se_busca(gasto.concepto or "")]
    cortado_gastos = len(gastos) > TOPE_POR_GRUPO
    gastos = gastos[:TOPE_POR_GRUPO]

    # **Y las personas y las empresas** (07/10/2026): con quién se trata —de quién es la factura, quién
    # vende, quién compra—. Es lo que se busca con un nombre propio en la cabeza, que es justo lo que un
    # buscador tiene que resolver. Se enseña el teléfono o el NIF, que es lo que distingue a dos personas
    # que se llaman igual.
    candidatos_contactos = db.scalars(
        select(models.Contacto)
        .where(models.Contacto.explotacion_id == explotacion.id)
        .order_by(models.Contacto.nombre)
    ).all()
    contactos = [
        contacto
        for contacto in candidatos_contactos
        if cotejado and cotejado in _como_se_busca(contacto.nombre or "")
    ]
    cortado_contactos = len(contactos) > TOPE_POR_GRUPO
    contactos = contactos[:TOPE_POR_GRUPO]

    # **Y las máquinas** (07/10/2026): el tractor, el remolque, el apero. Se buscan por su nombre y **por su
    # matrícula**, que es como se las nombra cuando se habla de ellas en el taller. Al lado se enseña la
    # matrícula (o el número de serie, para lo que no la tiene): es lo que distingue dos tractores.
    #
    # (Estuvo fuera una vuelta por no poder probarlo: dar de alta una máquina por la API exige `clase`,
    # `propiedad` y `disponibilidad` —las tres sin valor de partida, y con razón— y no supe qué valores
    # admite hasta que los leí en `maquinaria.py`. Ahora tiene su prueba.)
    candidatas_maquinas = db.scalars(
        select(models.Maquina)
        .where(models.Maquina.explotacion_id == explotacion.id)
        .order_by(models.Maquina.nombre)
    ).all()
    maquinas = [
        maquina
        for maquina in candidatas_maquinas
        if cotejado
        and (
            cotejado in _como_se_busca(maquina.nombre or "")
            or cotejado in _como_se_busca(maquina.matricula or "")
        )
    ]
    cortado_maquinas = len(maquinas) > TOPE_POR_GRUPO
    maquinas = maquinas[:TOPE_POR_GRUPO]

    # **Y los papeles** (07/10/2026): los contratos, las facturas y los albaranes. Es lo que se busca
    # cuando en una inspección se pregunta «¿dónde está el contrato de esa tierra?». Por su título, que es
    # como el agricultor los nombra, y al lado se enseña su tipo (contrato, factura…), que es lo que
    # distingue un papel de otro que se llama parecido.
    candidatos_papeles = db.scalars(
        select(models.DocumentoAnexo)
        .where(models.DocumentoAnexo.explotacion_id == explotacion.id)
        .order_by(models.DocumentoAnexo.titulo)
    ).all()
    papeles = [
        papel
        for papel in candidatos_papeles
        if cotejado and cotejado in _como_se_busca(papel.titulo or "")
    ]
    cortado_papeles = len(papeles) > TOPE_POR_GRUPO
    papeles = papeles[:TOPE_POR_GRUPO]

    grupos = []
    if suyas:
        grupos.append(
            {
                "clave": "tierras",
                "cuantos": len(suyas),
                "cortado": cortado,
                "resultados": [
                    {
                        "id": tierra.id,
                        "etiqueta": tierra.alias or "",
                        "detalle": tierra.ref_sigpac or "",
                    }
                    for tierra in suyas
                ],
            }
        )
    if gastos:
        grupos.append(
            {
                "clave": "gastos",
                "cuantos": len(gastos),
                "cortado": cortado_gastos,
                "resultados": [
                    {
                        "id": gasto.id,
                        "etiqueta": gasto.concepto or "",
                        "detalle": _el_importe_de_un_gasto(gasto),
                    }
                    for gasto in gastos
                ],
            }
        )
    if contactos:
        grupos.append(
            {
                "clave": "personas",
                "cuantos": len(contactos),
                "cortado": cortado_contactos,
                "resultados": [
                    {
                        "id": contacto.id,
                        "etiqueta": contacto.nombre or "",
                        # Lo que distingue a dos personas que se llaman igual: su teléfono o su NIF. Si no
                        # consta ninguno, no se enseña un hueco.
                        "detalle": contacto.telefono or contacto.nif or "",
                    }
                    for contacto in contactos
                ],
            }
        )
    # (El grupo de las máquinas va aquí, cuando tenga su prueba: ver la nota de arriba.)
    if papeles:
        grupos.append(
            {
                "clave": "papeles",
                "cuantos": len(papeles),
                "cortado": cortado_papeles,
                "resultados": [
                    {
                        "id": papel.id,
                        "etiqueta": papel.titulo or "",
                        # El tipo, que es lo que distingue dos papeles que se llaman parecido. Si no consta,
                        # no se enseña un hueco.
                        "detalle": papel.tipo or "",
                    }
                    for papel in papeles
                ],
            }
        )
    if maquinas:
        grupos.append(
            {
                "clave": "maquinas",
                "cuantos": len(maquinas),
                "cortado": cortado_maquinas,
                "resultados": [
                    {
                        "id": maquina.id,
                        "etiqueta": maquina.nombre or "",
                        # La matrícula, o el número de serie de lo que no la tiene. Si no consta ninguna de
                        # las dos, no se enseña un hueco.
                        "detalle": maquina.matricula or maquina.numero_serie or "",
                    }
                    for maquina in maquinas
                ],
            }
        )
    return {"texto": buscado, "buscado": True, "motivo": "", "grupos": grupos}


def _el_importe_de_un_gasto(gasto: models.Gasto) -> str:
    """El importe, escrito; y si no consta, **nada** (ni un cero ni un guion, que dirían que costó cero).

    Se dice con la palabra del servidor y no con un número inventado: un gasto sin importe es un gasto del
    que no se sabe lo que costó, y eso es lo que hay que leer.
    """
    if gasto.importe is None:
        return textos.ALMACEN.get("no_se_sabe", "") or "No consta"
    return f"{gasto.importe:.2f} €".replace(".", ",")
