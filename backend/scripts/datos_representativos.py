"""Una explotación **temporal** con volumen de verdad, para comprobar lo que con dos tierras no se ve.

## Por qué existe este fichero

La comprobación del navegador (`comprobar_en_un_navegador.py`) llevaba años mirando una finca de
prueba con **dos tierras y una campaña**. Con eso se comprueba que las pantallas se dibujan, pero no
se comprueba nada de lo que solo pasa **cuando hay muchas cosas**:

  · que el recuento de una lista diga el número que de verdad hay pintado;
  · que el buscador filtre (y que **lo que no casa no salga**);
  · que los filtros de la vista de las tierras dejen ver 10 de 64 y el pie lo diga;
  · que la selección múltiple marque y desmarque, y que su recuento cuadre;
  · que una exportación con un filtro puesto se lleve **lo filtrado** y no las 64;
  · que un nombre largo no rompa una tarjeta ni ensanche una tabla;
  · que lo que no se sabe se lea como hueco («Sin decir», «Sin hectáreas dichas»), **nunca como un
    cero** —que es una afirmación que nadie ha hecho (A7 y A10 de `docs/T02_VALORES_POR_DEFECTO.md`)—.

## Lo que hace, y lo que devuelve

Crea **dos explotaciones de usar y tirar** (cada una con su cuenta) contra un servidor de pruebas:

  1. **La del volumen**: 64 tierras con nombres largos, tres campañas, papeles, gastos, movimientos
     del banco, almacén, trabajos, contactos y máquinas. Todo lo que hace falta para que las listas
     sean largas y se puedan ejercitar a la vez.
  2. **La ajena**: una finca con marcas inconfundibles (`MARCADOR_AJENO`), para poder comprobar que
     **en un fichero exportado no aparece ni un registro de otra explotación**. Sin una segunda
     cuenta esto no se puede comprobar de ninguna manera.

Y **devuelve los identificadores que ha creado** (ver `Escenario`): el guion que comprueba **no puede
depender de «la primera tierra»** ni de un número escrito a mano, porque los identificadores los pone
el servidor y cambian con cada base. Todo lo que hay que abrir, buscar, marcar o exportar se pide por
el identificador que devuelve `preparar()`.

## Cómo se usa

```python
from datos_representativos import preparar

escenario = preparar("http://127.0.0.1:8021")
print(escenario.resumen())
print(escenario.tierras[0].id, escenario.tierras[0].alias)
```

O suelto, para mirarlo a mano:

```bash
cd backend
../.venv/Scripts/python.exe scripts/datos_representativos.py http://127.0.0.1:8021
```

**Se crea una explotación nueva en cada vuelta** (el correo lleva una marca con la hora y el proceso),
así que se puede repetir contra la misma base sin chocar con la vuelta anterior y sin ensuciar la
base del agricultor: esto es para un servidor de pruebas con **base temporal**, nunca para la suya.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import os
import pathlib
import sys
import tempfile
import time
import unicodedata

import httpx

# ---------------------------------------------------------------------------
# Los nombres de las 64 tierras
# ---------------------------------------------------------------------------
#
# **Se construyen, no se escriben una a una**, y los dos motivos importan:
#
#   · Hay **8 parajes × 8 colas = 64 nombres distintos y largos** (de 60 a 90 caracteres, que es lo
#     que se escribe de verdad: «El Prado de la Fuente Vieja, detrás del corral de las ovejas
#     merinas»). Un nombre de tres palabras no rompe ninguna tarjeta; uno largo, sí.
#   · El **paraje** es lo que se busca después: «dehesa boyal» casa con 8 tierras de 64, que es el
#     caso que hay que comprobar (un buscador que devuelve todo no filtra; uno que devuelve 8 de 64,
#     sí). El número de las que casan lo cuenta el propio módulo (`cuantas_casan`), no se escribe a
#     mano.
PARAJES = (
    "El Alto de la Dehesa Boyal",
    "Las Suertes de Arriba",
    "El Prado de la Fuente Vieja",
    "La Vega del Río Carrión",
    "El Teso de los Cantos Blancos",
    "Las Eras del Concejo",
    "El Llano de la Cañada Real",
    "La Ladera del Monte de Utilidad Pública",
)

COLAS = (
    "junto al camino de los molinos harineros",
    "detrás del corral de las ovejas merinas",
    "al lado del puente viejo de piedra",
    "enfrente de la nave de la maquinaria",
    "pasando el arroyo de las Navas",
    "en el término que linda con el monte",
    "donde acaba la carretera de los Huertos",
    "pegando al transformador de la luz",
)

# Los tres cultivos que se siembran, **sin tildes ni espacios raros**: lo que se elige en el filtro de
# la pantalla es la clave normalizada, y un acento de más haría fallar la comprobación por un motivo
# que no es de la pantalla.
CULTIVOS = ("TRIGO BLANDO", "CEBADA", "GIRASOL")

# Los pueblos, con el mismo reparto que un cuaderno de verdad: hay tierras sin pueblo dicho.
MUNICIPIOS = ("Calvarrasa de Arriba", "Peñaranda de Bracamonte", "Macotera", "Alba de Tormes")

# **Lo que se busca y cuántas casan.** El texto va sin tildes a propósito (el buscador de la pantalla
# coteja sin tildes, ver `filtrarLasTierras`), y sale del primer paraje: casa con las tierras 0, 8,
# 16… 56, o sea **8 de 64**.
BUSQUEDA_DE_TIERRA = "dehesa boyal"

# El texto por el que se busca en el extracto del banco: casa con **10 de los 30** movimientos de la
# cuenta principal. Los otros 20 tienen otros conceptos, así que un fichero con los 30 se nota.
BUSQUEDA_DEL_BANCO = "COSECHERA"

# **Los días del extracto empiezan en 13 y no en 1, y no es un capricho.** El programa se niega a
# adivinar una fecha que se puede leer de dos maneras (`01/06` es el 1 de junio o el 6 de enero) y
# lee el fichero entero para deducir cómo escribe las fechas ese banco: con un día mayor que 12 entre
# las líneas, el formato queda claro. Un extracto con días del 1 al 6 se queda en «fecha ambigua» y
# no se importa —que es lo correcto—, y entonces esta preparación no tendría movimientos que contar.
PRIMER_DIA_DEL_EXTRACTO = 13

# Las marcas de la explotación ajena. **Ninguna puede salir** en un fichero exportado desde la otra
# cuenta: es la comprobación de que la exportación no se lleva lo de otro agricultor.
MARCADOR_AJENO = "OTRA EXPLOTACION NO DEBE SALIR"

# La clave de las dos cuentas de prueba (el correo lleva la marca, ver `preparar`).
CLAVE = "una-clave-larga-de-prueba"

# Un PNG de verdad, de un píxel: es lo que se sube como papel para que la pantalla tenga un fichero
# que descargar. El mismo que usa la comprobación del navegador para la bandeja.
UN_PNG_DE_UN_PIXEL = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15ca89"
    "0000000a49444154789c6360000002000154a24f5f0000000049454e44ae426082"
)

NOMBRE_DEL_PAPEL_CON_FICHERO = "el-contrato-de-arrendamiento-de-la-finca.png"


def _sin_tildes(texto: str) -> str:
    """El mismo cotejo que hace la pantalla: sin tildes, sin mayúsculas y sin espacios de más."""
    plano = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(letra for letra in plano if unicodedata.category(letra) != "Mn").upper()


# ---------------------------------------------------------------------------
# Lo que se devuelve
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Tierra:
    """Una tierra creada, con lo que hace falta para comprobarla sin volver a preguntar."""

    id: int
    alias: str
    superficie_ha: float | None
    tiene_forma: bool
    cultivo: str | None
    municipio: str
    ref_sigpac: str | None


@dataclasses.dataclass(frozen=True)
class Campana:
    id: int
    anio: int


@dataclasses.dataclass
class Finca:
    """Una explotación de usar y tirar, con su cuenta y su token."""

    nombre: str
    correo: str
    token: str
    usuario_id: int
    explotacion_id: int
    campanas: list[Campana]

    @property
    def campana_actual(self) -> Campana:
        return max(self.campanas, key=lambda campana: campana.anio)


@dataclasses.dataclass
class Escenario:
    """Todo lo que ha creado la preparación, **con sus identificadores**.

    Quien comprueba usa esto y no «la primera tierra»: lo que devuelve el servidor al crear es lo
    único que se sabe de verdad.
    """

    volumen: Finca
    ajena: Finca
    tierras: list[Tierra]
    tierras_sin_superficie: list[Tierra]
    tierras_sin_forma: list[Tierra]
    tierras_sin_cultivo: list[Tierra]
    tierras_sin_pueblo: list[Tierra]
    cuenta_principal: dict
    cuenta_secundaria: dict
    documento_con_fichero: int
    documento_sin_fichero: int
    contacto_conocido: int
    contactos: list[int]
    productos: list[int]
    maquinas: list[int]
    papeles: list[int]
    gastos: list[int]
    trabajos_previstos: list[int]
    trabajos_hechos: list[int]
    tratamientos: list[int]
    búsqueda_de_tierra: str = BUSQUEDA_DE_TIERRA
    búsqueda_del_banco: str = BUSQUEDA_DEL_BANCO
    movimientos_de_la_cuenta_principal: int = 0
    movimientos_de_la_cuenta_secundaria: int = 0
    movimientos_que_casan: int = 0
    marcas_ajenas: tuple[str, ...] = ()
    cuantas: dict = dataclasses.field(default_factory=dict)

    # ------------------------------------------------------------------ lo que se cuenta solo

    @property
    def cuantas_tierras(self) -> int:
        return len(self.tierras)

    @property
    def cuantas_casan(self) -> int:
        """Cuántas tierras casa la búsqueda. **Se cuenta, no se escribe**: si un día cambia un
        paraje, el número que espera la comprobación cambia con él en vez de quedarse mintiendo."""
        buscado = _sin_tildes(self.búsqueda_de_tierra)
        return sum(1 for tierra in self.tierras if buscado in _sin_tildes(tierra.alias))

    @property
    def cuantas_casan_por_cultivo(self) -> dict[str, int]:
        cuenta: dict[str, int] = {}
        for tierra in self.tierras:
            if tierra.cultivo:
                cuenta[tierra.cultivo] = cuenta.get(tierra.cultivo, 0) + 1
        return cuenta

    def resumen(self) -> str:
        """Lo creado, en renglones, para poder decirlo en el informe y en la consola."""
        lineas = [
            f"explotación del volumen: «{self.volumen.nombre}» (id {self.volumen.explotacion_id}), "
            f"campañas {', '.join(str(c.anio) for c in self.volumen.campanas)}",
            f"explotación ajena: «{self.ajena.nombre}» (id {self.ajena.explotacion_id})",
            f"tierras: {len(self.tierras)} "
            f"(sin superficie {len(self.tierras_sin_superficie)}, "
            f"sin forma {len(self.tierras_sin_forma)}, "
            f"sin cultivo {len(self.tierras_sin_cultivo)}, "
            f"sin pueblo {len(self.tierras_sin_pueblo)})",
            f"la búsqueda «{self.búsqueda_de_tierra}» casa con {self.cuantas_casan} de {len(self.tierras)}",
            f"por cultivo: " + ", ".join(f"{k} {v}" for k, v in self.cuantas_casan_por_cultivo.items()),
            "lo demás: " + ", ".join(f"{clave} {valor}" for clave, valor in self.cuantas.items()),
            f"movimientos: cuenta principal {self.movimientos_de_la_cuenta_principal}, "
            f"cuenta secundaria {self.movimientos_de_la_cuenta_secundaria}, "
            f"y «{self.búsqueda_del_banco}» casa con {self.movimientos_que_casan}",
        ]
        return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Hablar con el servidor
# ---------------------------------------------------------------------------


class LaPreparacionFalla(RuntimeError):
    """El servidor no ha aceptado algo de lo que la preparación necesita dejar hecho."""


def _pedir(cliente: httpx.Client, metodo: str, ruta: str, **argumentos) -> httpx.Response:
    """Una petición, **con la ruta y lo que ha contestado dentro del error**.

    Sin esto, un 422 de una ruta se lee como «falló la preparación» y hay que ir a buscarlo a mano:
    con la respuesta delante, el motivo lo dice el propio servidor.
    """
    respuesta = cliente.request(metodo, ruta, **argumentos)
    if respuesta.status_code >= 400:
        detalle = respuesta.text[:500]
        raise LaPreparacionFalla(f"{metodo} {ruta} ha contestado {respuesta.status_code}: {detalle}")
    return respuesta


def _registrar(direccion: str, nombre: str, correo: str, finca: str, nif: str) -> Finca:
    """Da de alta una cuenta con su explotación y devuelve su token ya puesto."""
    with httpx.Client(base_url=direccion, timeout=60.0) as cliente:
        respuesta = _pedir(
            cliente,
            "POST",
            "/api/cuenta/registro",
            json={
                "nombre": nombre,
                "correo": correo,
                "clave": CLAVE,
                "explotacion": {"nombre": finca, "nif": nif},
            },
        )
    datos = respuesta.json()
    return Finca(
        nombre=finca,
        correo=correo,
        token=datos["token"],
        usuario_id=datos["usuario_id"],
        explotacion_id=datos["explotacion_id"],
        campanas=[],
    )


def _cliente(finca: Finca, direccion: str) -> httpx.Client:
    return httpx.Client(
        base_url=direccion,
        timeout=60.0,
        headers={"Authorization": f"Bearer {finca.token}"},
    )


# ---------------------------------------------------------------------------
# Las piezas del escenario
# ---------------------------------------------------------------------------


def _crear_campanas(cliente: httpx.Client, anios: tuple[int, ...]) -> list[Campana]:
    """Deja las campañas dichas (la del año en curso la crea el alta de la cuenta sola)."""
    ya = {campana["anio"]: campana["id"] for campana in _pedir(cliente, "GET", "/api/campanas").json()}
    for anio in anios:
        if anio in ya:
            continue
        creada = _pedir(
            cliente,
            "POST",
            "/api/campanas",
            json={
                "anio": anio,
                "fecha_inicio": dt.date(anio, 1, 1).isoformat(),
                "fecha_fin": dt.date(anio, 12, 31).isoformat(),
            },
        ).json()
        ya[anio] = creada["id"]
    return [Campana(id=ya[anio], anio=anio) for anio in sorted(ya)]


def _geometria(indice: int) -> str:
    """Un rectángulo pequeño y distinto por tierra, en WKT (`longitud latitud`), como el del SIGPAC.

    Se le da forma **solo a unas pocas** (las que casan con `indice % 11 == 0`): lo que el encargo
    pide comprobar es justo lo contrario —que una tierra **sin forma** se lea como un hueco y no
    rompa la tabla ni el mapa— pero el mapa necesita alguna con forma para tener caja y centro.
    """
    oeste = -5.70 + (indice % 8) * 0.02
    sur = 40.85 + (indice // 8) * 0.02
    return (
        f"POLYGON(({oeste} {sur}, {oeste + 0.008} {sur}, "
        f"{oeste + 0.008} {sur + 0.005}, {oeste} {sur + 0.005}, {oeste} {sur}))"
    )


def _las_64_tierras(cliente: httpx.Client, campana: Campana) -> list[Tierra]:
    """Da de alta las 64 tierras, con sus datos incompletos **a propósito**, y sus cultivos.

    Lo que se deja a medias, y por qué:

      · **sin superficie** (una de cada siete): es el caso de la tierra apuntada a mano o traída sin
        el dato. Tiene que leerse «Sin hectáreas dichas», **nunca 0,00 ha**: un cero es una
        afirmación que nadie ha hecho, y además cerraría la puerta a tratarla.
      · **sin forma** (todas menos seis): la tierra a mano no tiene dibujo del SIGPAC.
      · **sin cultivo** (una de cada cinco): no se ha declarado qué se sembró.
      · **sin pueblo** (una de cada seis): el pueblo no se sabe.
      · **sin referencia del SIGPAC** (una de cada seis): no se ha traído del visor.
    """
    tierras: list[Tierra] = []
    for indice in range(64):
        paraje = PARAJES[indice % len(PARAJES)]
        cola = COLAS[(indice // len(PARAJES)) % len(COLAS)]
        alias = f"{paraje}, {cola}"
        tiene_superficie = indice % 7 != 3
        # **La primera tierra también tiene forma** (07/10/2026): es la que usa el recorrido automático para
        # andar el camino completo (ficha → trabajo → historial), y sin forma **no se puede comprobar que su
        # ficha enseñe la forma de la parcela** —una regresión que tuvo este rediseño y ya está arreglada—.
        # Una tierra más con forma no cambia nada de lo demás: las demás siguen como estaban.
        tiene_forma = indice % 11 == 0 or indice == 1
        tiene_pueblo = indice % 6 != 5
        modulo = indice % 5
        cultivo = CULTIVOS[modulo] if modulo < 3 else None
        tiene_referencia = indice % 6 != 0
        cuerpo = {
            "alias": alias,
            "provincia": "Salamanca",
            "municipio": MUNICIPIOS[indice % len(MUNICIPIOS)] if tiene_pueblo else "",
            "superficie_ha": round(1.2 + (indice % 13) * 0.7, 2) if tiene_superficie else None,
        }
        if tiene_referencia:
            cuerpo.update(
                {
                    "ref_sigpac": f"37-70-0-0-{500 + indice}-{200 + indice}",
                    "poligono": 500 + indice,
                    "numero_parcela": 200 + indice,
                    "numero_recinto": 1,
                }
            )
        if tiene_forma:
            cuerpo["geometria"] = _geometria(indice)
        else:
            # El sistema tampoco se sabe en la mitad de las tierras: `None` es «no lo sé», y el
            # cuaderno tiene que poder decir eso en vez de dar por hecho un secano.
            cuerpo["sistema"] = "secano" if indice % 2 == 0 else None
        creada = _pedir(cliente, "POST", "/api/parcelas", json=cuerpo).json()
        if cultivo:
            _pedir(
                cliente,
                "POST",
                f"/api/parcelas/{creada['id']}/cultivos",
                json={
                    "campana_id": campana.id,
                    "especie": cultivo,
                    "sistema": "secano",
                    "fecha_inicio": f"{campana.anio - 1}-11-10",
                },
            )
        tierras.append(
            Tierra(
                id=int(creada["id"]),
                alias=alias,
                superficie_ha=cuerpo["superficie_ha"],
                tiene_forma=tiene_forma,
                cultivo=cultivo,
                municipio=cuerpo["municipio"],
                ref_sigpac=cuerpo.get("ref_sigpac"),
            )
        )
    return tierras


def _cultivos_de_otros_anios(
    cliente: httpx.Client, tierras: list[Tierra], campanas: list[Campana]
) -> None:
    """Siembra unas cuantas tierras en los años anteriores.

    Hace falta para que la tabla de «qué hay sembrado» tenga de verdad una columna de **otros años**
    y para que la comparación entre dos años de una tierra tenga con qué: con una sola campaña, esa
    mitad de la pantalla se comprueba vacía.
    """
    anteriores = [campana for campana in campanas if campana.anio < max(c.anio for c in campanas)]
    for numero, campana in enumerate(anteriores):
        for tierra in tierras[numero::13]:
            _pedir(
                cliente,
                "POST",
                f"/api/parcelas/{tierra.id}/cultivos",
                json={
                    "campana_id": campana.id,
                    "especie": CULTIVOS[(numero + 1) % len(CULTIVOS)],
                    "sistema": "secano",
                    "fecha_inicio": f"{campana.anio - 1}-10-20",
                },
            )


def _numero_en_espanol(valor: float) -> str:
    """Un número como lo escribe un extracto español: **miles con punto y decimales con coma**.

    Se escribe aquí y no se le pide al servidor porque esto es un **fichero de banco de mentira**:
    lo que se está comprobando es que el programa lo lee, no cómo lo escribe él.
    """
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _un_extracto_de_verdad(carpeta: pathlib.Path, nombre: str, conceptos: list[tuple[str, str]]) -> pathlib.Path:
    """Escribe un extracto con el mismo formato que el de ejemplo del proyecto.

    **Se genera con los conceptos que se le piden para poder contarlos después**: la comprobación de
    las descargas tiene que saber cuántos movimientos casa la búsqueda, y eso solo se sabe si los ha
    escrito quien los ha creado.
    """
    destino = carpeta / nombre
    renglones = [
        "Banco del Páramo, S.A.;Cuenta: ES00 9999 8888 7777 6666 5555;Extracto de la prueba",
        ";;;;;",
        "Fecha;Fecha valor;Concepto;Referencia;Importe;Saldo",
    ]
    saldo = 5000.0
    for numero, (concepto, importe) in enumerate(conceptos, start=1):
        saldo += float(importe.replace(",", "."))
        dia = PRIMER_DIA_DEL_EXTRACTO + (numero % 15)
        renglones.append(
            f"{dia:02d}/06/2026;{dia:02d}/06/2026;{concepto};REF-2026-{numero:04d};"
            f"{importe};{_numero_en_espanol(saldo)}"
        )
    destino.write_text("\n".join(renglones) + "\n", encoding="utf-8")
    return destino


def _importar_extracto(cliente: httpx.Client, cuenta_id: int, fichero: pathlib.Path) -> int:
    """Sube un extracto por la misma puerta que el agricultor y devuelve cuántos movimientos crea."""
    with open(fichero, "rb") as el_fichero:
        respuesta = _pedir(
            cliente,
            "POST",
            "/api/bancos/extractos/importar",
            data={"cuenta_id": str(cuenta_id)},
            files={"fichero": (fichero.name, el_fichero, "text/csv")},
        )
    return int(respuesta.json().get("creados") or 0)


# ---------------------------------------------------------------------------
# La explotación del volumen
# ---------------------------------------------------------------------------


def _la_del_volumen(
    direccion: str, marca: str, temporal: pathlib.Path, ajena: Finca
) -> tuple[Finca, Escenario]:
    finca = _registrar(
        direccion,
        nombre="Cuaderno de volumen",
        correo=f"volumen-{marca}@ejemplo.test",
        finca=f"La Explotación del Volumen de la Prueba {marca}",
        nif="12345678Z",
    )
    with _cliente(finca, direccion) as cliente:
        finca.campanas = _crear_campanas(cliente, (2024, 2025, 2026))
        campana = finca.campana_actual
        tierras = _las_64_tierras(cliente, campana)
        _cultivos_de_otros_anios(cliente, tierras, finca.campanas)

        cuantas: dict[str, int] = {"tierras": len(tierras)}

        # ---- lo que se usa -------------------------------------------------
        productos = [
            _pedir(
                cliente,
                "POST",
                "/api/productos",
                json={
                    "nombre_comercial": f"Producto de la prueba {numero:02d}",
                    "numero_registro": f"ES-{1000 + numero:05d}",
                    "unidad_dosis": "L/ha",
                    "unidad_compra": "L",
                },
            ).json()["id"]
            for numero in range(1, 13)
        ]
        cuantas["productos"] = len(productos)

        contactos = [
            _pedir(
                cliente,
                "POST",
                "/api/contactos",
                json={
                    "nombre": f"Proveedor de la prueba {numero:02d} S.L.",
                    "es_empresa": True,
                    "localidad": MUNICIPIOS[numero % len(MUNICIPIOS)],
                    "telefono": f"923 00 00 {numero:02d}",
                    "papeles": ["proveedor"],
                },
            ).json()["id"]
            for numero in range(1, 21)
        ]
        cuantas["contactos"] = len(contactos)

        # ---- el almacén ----------------------------------------------------
        articulos = []
        for numero in range(1, 9):
            articulo = _pedir(
                cliente,
                "POST",
                "/api/almacen/articulos",
                json={
                    "nombre": f"Lo que hay en la nave {numero:02d}",
                    "categoria": "fitosanitario" if numero % 2 else "abono",
                    "unidad": "L",
                    "producto_id": productos[numero - 1],
                },
            ).json()
            lote = _pedir(
                cliente,
                "POST",
                "/api/almacen/lotes",
                json={
                    "articulo_id": articulo["id"],
                    "numero_lote": f"ENV-2026-{numero:02d}",
                    "presentacion": "garrafa de 20 L",
                    "contenido_por_envase": 20.0,
                    "ubicacion": "La nave",
                },
            ).json()
            articulos.append((articulo["id"], lote["id"]))
            _pedir(
                cliente,
                "POST",
                "/api/almacen/movimientos",
                json={
                    "tipo": "entrada",
                    "lote_id": lote["id"],
                    "cantidad": 40.0,
                    "unidad": "L",
                    "fecha": "2026-03-16",
                    "motivo": "Lo que ya estaba en la nave cuando empecé el cuaderno",
                },
            )
            # Y un ajuste por envase: el libro del almacén tiene que tener las dos columnas con
            # números (lo comprado y lo que queda) y no solo entradas. **No se apunta una salida**:
            # el programa no deja sacar producto del almacén sin decir de qué trabajo sale —«apúntalo
            # desde el tratamiento o el abono, que ya saben cuánto se gastó»—, y ese camino ya lo
            # recorre la comprobación del navegador con un tratamiento de verdad.
            _pedir(
                cliente,
                "POST",
                "/api/almacen/movimientos",
                json={
                    "tipo": "ajuste",
                    "lote_id": lote["id"],
                    "cantidad": -5.0,
                    "unidad": "L",
                    "fecha": "2026-04-02",
                    "motivo": "Lo que se gastó en el tratamiento de la prueba",
                },
            )
        cuantas["articulos"] = len(articulos)
        cuantas["movimientos_de_almacen"] = len(articulos) * 2

        # ---- la maquinaria -------------------------------------------------
        maquinas = []
        for numero in range(1, 9):
            maquina = _pedir(
                cliente,
                "POST",
                "/api/maquinaria",
                json={
                    "nombre": f"La máquina de la prueba {numero:02d}",
                    "clase": "tractor" if numero % 2 else "apero",
                    "propiedad": "propia",
                    "disponibilidad": "disponible",
                    "matricula": f"{1000 + numero} ABC",
                    "horas": 1000 + numero * 137,
                },
            ).json()
            maquinas.append(maquina["id"])
        cuantas["maquinas"] = len(maquinas)

        # ---- los papeles ---------------------------------------------------
        papeles = []
        for numero in range(1, 31):
            papel = _pedir(
                cliente,
                "POST",
                "/api/documentos",
                json={
                    "titulo": f"Papel de la prueba {numero:02d}: contrato de la parcela del pago",
                    "tipo": "contrato" if numero % 3 else "factura",
                    "carpeta": ["Contratos", "Facturas", "Sigfito"][numero % 3],
                    "fecha": f"2026-0{1 + numero % 9}-1{numero % 9}",
                    "quien": f"Quien firma el papel {numero:02d}",
                    "campana_id": campana.id,
                },
            ).json()
            papeles.append(papel["id"])
        # **Uno con fichero y otro sin él**: son las dos mitades de la pantalla de los papeles (el
        # botón de descargar y el aviso de que le falta el fichero), y la descarga de verdad solo se
        # puede comprobar con uno que lo tenga.
        documento_con_fichero = papeles[0]
        _pedir(
            cliente,
            "POST",
            f"/api/documentos/{documento_con_fichero}/fichero",
            files={
                "fichero": (
                    NOMBRE_DEL_PAPEL_CON_FICHERO,
                    UN_PNG_DE_UN_PIXEL,
                    "image/png",
                )
            },
        )
        documento_sin_fichero = papeles[1]
        cuantas["papeles"] = len(papeles)

        # ---- los gastos ----------------------------------------------------
        categorias = ("gasoleo", "reparacion", "abono", "semilla", "seguro", "cuota", "otro")
        gastos = []
        for numero in range(1, 41):
            gasto = _pedir(
                cliente,
                "POST",
                "/api/gastos",
                json={
                    "campana_id": campana.id,
                    "fecha": f"2026-{1 + numero % 12:02d}-{1 + numero % 27:02d}",
                    "concepto": f"Gasto de la prueba {numero:02d} de la explotación",
                    "categoria": categorias[numero % len(categorias)],
                    "proveedor": f"Proveedor de la prueba {1 + numero % 20:02d} S.L.",
                    "parcela_id": tierras[numero % len(tierras)].id if numero % 3 == 0 else None,
                    "importe": f"{10 + numero * 3}.{numero % 100:02d}",
                },
            ).json()
            gastos.append(int(gasto["gasto"]["id"]))
        cuantas["gastos"] = len(gastos)

        # ---- los trabajos --------------------------------------------------
        #
        # **Se trabaja sobre las tierras que tienen su superficie dicha**, y con el 90 % de ella: el
        # servidor no deja tratar más hectáreas de las que tiene la parcela («La parcela tiene 1,90
        # hectáreas y has puesto 3,50»), y esa comprobación es correcta. Las tierras sin superficie
        # se quedan para lo que se está comprobando aquí: que leerse como un hueco no rompa nada.
        con_superficie = [tierra for tierra in tierras if tierra.superficie_ha]

        def una_tierra(numero: int) -> Tierra:
            return con_superficie[numero % len(con_superficie)]

        previstos = []
        hechos = []
        for numero in range(1, 13):
            tierra = una_tierra(numero)
            previsto = _pedir(
                cliente,
                "POST",
                "/api/trabajos/previstos",
                json={
                    "campana_id": campana.id,
                    "tipo": ["laboreo", "siembra", "abonado", "tratamiento"][numero % 4],
                    "fecha_prevista": f"2026-{1 + numero % 9:02d}-15",
                    "parcela_id": tierra.id,
                    "superficie_ha": round(tierra.superficie_ha * 0.9, 2),
                    "horas": 3.0,
                    "observaciones": f"Pensado para la tierra {tierra.alias}",
                },
            ).json()
            previstos.append(int(previsto["previsto"]["id"]))
            hecho = _pedir(
                cliente,
                "POST",
                "/api/trabajos",
                json={
                    "campana_id": campana.id,
                    "tipo": ["laboreo", "siembra", "abonado", "tratamiento"][numero % 4],
                    "fecha": f"2026-{1 + numero % 9:02d}-05",
                    "parcela_id": tierra.id,
                    "superficie_ha": round(tierra.superficie_ha * 0.9, 2),
                    "horas": 2.5,
                    "observaciones": f"Hecho en la tierra {tierra.alias}",
                },
            ).json()
            hechos.append(int(hecho["hecho"]["id"]))
        cuantas["trabajos_previstos"] = len(previstos)
        cuantas["trabajos_hechos"] = len(hechos)

        # ---- los tratamientos y las ventas ---------------------------------
        tratamientos = []
        for numero in range(1, 25):
            tierra = una_tierra(numero)
            tratamiento = _pedir(
                cliente,
                "POST",
                "/api/tratamientos",
                json={
                    "campana_id": campana.id,
                    "fecha": f"2026-{1 + numero % 9:02d}-{1 + numero % 27:02d}",
                    "parcela_id": tierra.id,
                    "superficie_tratada_ha": round(tierra.superficie_ha * 0.9, 2),
                    "justificacion": "Se vio la hierba en el campo",
                    "plaga": "Hierbas adventicias",
                    "producto_id": productos[numero % len(productos)],
                    "dosis": 3,
                },
            ).json()
            tratamientos.append(tratamiento["id"])
        cuantas["tratamientos"] = len(tratamientos)
        for numero in range(1, 11):
            _pedir(
                cliente,
                "POST",
                "/api/ventas",
                json={
                    "campana_id": campana.id,
                    "tipo": "comercializada",
                    "fecha": f"2026-0{1 + numero % 9}-1{numero % 9}",
                    "producto": f"Cosecha de la prueba {numero:02d}",
                    "cantidad": 1000.0 * numero,
                    "unidad": "kg",
                    "comprador": f"Proveedor de la prueba {numero:02d} S.L.",
                    "parcela_id": tierras[numero].id,
                },
            )
        cuantas["ventas"] = 10

        # ---- el banco ------------------------------------------------------
        principal = _pedir(
            cliente,
            "POST",
            "/api/bancos/cuentas",
            json={"nombre": "La cuenta principal de la prueba", "banco": "Banco del Páramo", "ultimos_digitos": "1111"},
        ).json()
        secundaria = _pedir(
            cliente,
            "POST",
            "/api/bancos/cuentas",
            json={"nombre": "La cuenta secundaria de la prueba", "banco": "Banco del Páramo", "ultimos_digitos": "2222"},
        ).json()
        # **Los conceptos se construyen contando**: 10 llevan la palabra que se busca y 20 no, así que
        # un fichero exportado con los 30 se distingue de uno con los 10 sin ambigüedad posible.
        conceptos_principal = []
        for numero in range(1, 31):
            if numero <= 10:
                concepto = f"CUOTA DE LA COSECHERA NUMERO {numero:02d}"
            else:
                concepto = f"GASTO CORRIENTE DE LA NAVE NUMERO {numero:02d}"
            conceptos_principal.append((concepto, f"-{10 + numero},50"))
        conceptos_secundaria = [
            (f"MOVIMIENTO DE LA CUENTA SECUNDARIA NUMERO {numero:02d}", f"-{5 + numero},25")
            for numero in range(1, 7)
        ]
        fichero_principal = _un_extracto_de_verdad(
            temporal, "extracto_principal.csv", conceptos_principal
        )
        fichero_secundaria = _un_extracto_de_verdad(
            temporal, "extracto_secundaria.csv", conceptos_secundaria
        )
        apuntados_principal = _importar_extracto(cliente, principal["id"], fichero_principal)
        apuntados_secundaria = _importar_extracto(cliente, secundaria["id"], fichero_secundaria)
        cuantas["movimientos_del_banco"] = apuntados_principal + apuntados_secundaria

    escenario = Escenario(
        volumen=finca,
        ajena=ajena,
        tierras=tierras,
        tierras_sin_superficie=[t for t in tierras if t.superficie_ha is None],
        tierras_sin_forma=[t for t in tierras if not t.tiene_forma],
        tierras_sin_cultivo=[t for t in tierras if not t.cultivo],
        tierras_sin_pueblo=[t for t in tierras if not t.municipio],
        cuenta_principal=principal,
        cuenta_secundaria=secundaria,
        documento_con_fichero=documento_con_fichero,
        documento_sin_fichero=documento_sin_fichero,
        contacto_conocido=contactos[0],
        contactos=contactos,
        productos=productos,
        maquinas=maquinas,
        papeles=papeles,
        gastos=gastos,
        trabajos_previstos=previstos,
        trabajos_hechos=hechos,
        tratamientos=tratamientos,
        movimientos_de_la_cuenta_principal=apuntados_principal,
        movimientos_de_la_cuenta_secundaria=apuntados_secundaria,
        movimientos_que_casan=sum(
            1
            for concepto, _ in conceptos_principal
            if _sin_tildes(BUSQUEDA_DEL_BANCO) in _sin_tildes(concepto)
        ),
        cuantas=cuantas,
    )
    return finca, escenario


# ---------------------------------------------------------------------------
# La explotación ajena
# ---------------------------------------------------------------------------


def _la_ajena(direccion: str, marca: str, temporal: pathlib.Path) -> Finca:
    """Una segunda explotación con marcas inconfundibles, para cazar una exportación que se salga.

    **Hace falta una cuenta de verdad, no vale con imaginar el caso**: lo que se comprueba es que el
    servidor filtra por explotación, y eso solo se demuestra con dos explotaciones en la misma base.
    Todo lo que crea lleva dentro `MARCADOR_AJENO`, así que basta con buscar esa cadena en el
    fichero descargado para saber si se ha colado algo que no es del agricultor.
    """
    finca = _registrar(
        direccion,
        nombre="Cuaderno ajeno",
        correo=f"ajena-{marca}@ejemplo.test",
        finca=f"La Finca Ajena de la Prueba {marca}",
        nif="87654321X",
    )
    with _cliente(finca, direccion) as cliente:
        finca.campanas = _crear_campanas(cliente, (2024, 2025, 2026))
        campana = finca.campana_actual
        tierra = _pedir(
            cliente,
            "POST",
            "/api/parcelas",
            json={
                "alias": f"TIERRA DE LA {MARCADOR_AJENO}",
                "provincia": "Salamanca",
                "municipio": "Macotera",
                "superficie_ha": 9.9,
            },
        ).json()
        _pedir(
            cliente,
            "POST",
            f"/api/parcelas/{tierra['id']}/cultivos",
            json={
                "campana_id": campana.id,
                "especie": "CENTENO",
                "sistema": "secano",
                "fecha_inicio": "2025-10-01",
            },
        )
        _pedir(
            cliente,
            "POST",
            "/api/gastos",
            json={
                "campana_id": campana.id,
                "fecha": "2026-05-05",
                "concepto": f"GASTO DE LA {MARCADOR_AJENO}",
                "categoria": "otro",
                "importe": "99,99",
            },
        )
        _pedir(
            cliente,
            "POST",
            "/api/documentos",
            json={
                "titulo": f"PAPEL DE LA {MARCADOR_AJENO}",
                "tipo": "otros",
                "carpeta": "Ajena",
                "fecha": "2026-05-06",
                "campana_id": campana.id,
            },
        )
        _pedir(
            cliente,
            "POST",
            "/api/contactos",
            json={"nombre": f"CONTACTO DE LA {MARCADOR_AJENO}", "es_empresa": True},
        )
        _pedir(
            cliente,
            "POST",
            "/api/trabajos",
            json={
                "campana_id": campana.id,
                "tipo": "laboreo",
                "fecha": "2026-05-07",
                "parcela_id": tierra["id"],
                "horas": 1.0,
                "observaciones": f"TRABAJO DE LA {MARCADOR_AJENO}",
            },
        )
        _pedir(
            cliente,
            "POST",
            "/api/productos",
            json={"nombre_comercial": f"PRODUCTO DE LA {MARCADOR_AJENO}"},
        )
        cuenta = _pedir(
            cliente,
            "POST",
            "/api/bancos/cuentas",
            json={"nombre": f"CUENTA DE LA {MARCADOR_AJENO}", "banco": "Banco del Páramo"},
        ).json()
        fichero = _un_extracto_de_verdad(
            temporal,
            "extracto_ajeno.csv",
            [(f"MOVIMIENTO DE LA {MARCADOR_AJENO}", "-1,00")],
        )
        _importar_extracto(cliente, cuenta["id"], fichero)
    return finca


# ---------------------------------------------------------------------------
# Lo que se pide desde fuera
# ---------------------------------------------------------------------------


def preparar(direccion: str, *, marca: str | None = None) -> Escenario:
    """Crea las dos explotaciones de la prueba y devuelve **todo lo que ha creado, con sus ids**.

    `marca` es lo que distingue una vuelta de otra (va en el correo de las dos cuentas). Por defecto
    se saca de la hora y del proceso, así que **se puede repetir** contra la misma base sin chocar
    con la vuelta anterior.
    """
    marca = marca or f"{int(time.time())}-{os.getpid()}"
    with tempfile.TemporaryDirectory(prefix="cuedigital-volumen-") as temporal:
        carpeta = pathlib.Path(temporal)
        # **La ajena se crea primero** para que la del volumen pueda llevarla dentro desde el
        # principio: así el escenario nunca existe a medias (con una finca y sin la otra) y quien lo
        # use no puede leer un hueco creyendo que es un dato.
        ajena = _la_ajena(direccion, marca, carpeta)
        volumen, escenario = _la_del_volumen(direccion, marca, carpeta, ajena)
    escenario.marcas_ajenas = (MARCADOR_AJENO, ajena.nombre)
    return escenario


def main() -> int:
    analizador = argparse.ArgumentParser(
        description="Crea una explotación temporal con 64 tierras y todo lo demás, y dice qué ha creado."
    )
    analizador.add_argument("direccion", nargs="?", default="http://127.0.0.1:8021")
    argumentos = analizador.parse_args()
    escenario = preparar(argumentos.direccion)
    print(escenario.resumen())
    print()
    print("las tierras, con su identificador (las cinco primeras y las cinco últimas):")
    for tierra in escenario.tierras[:5] + escenario.tierras[-5:]:
        print(f"  {tierra.id:>5}  {tierra.alias}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
