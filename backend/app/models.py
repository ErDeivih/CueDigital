"""Tablas de la base de datos.

Dos decisiones que conviene entender antes de tocar esto:

1. **Los nombres van en castellano.** El dominio es castellano (parcela,
   tratamiento, abonado) y las validaciones son legales. Traducir "DGC" a "plot"
   solo sirve para que el programador y el agricultor hablen de cosas distintas.

2. **`explotacion_id` está en todas las tablas de negocio.** Es lo que garantiza
   que un agricultor no pueda ver ni tocar los datos de otro. Si se añade una
   tabla nueva y se olvida esa columna, se rompe el aislamiento: el test
   `test_aislamiento_entre_explotaciones` lo detecta.

3. **Nada desaparece sin dejar rastro.** Los registros se pueden **anular** (`anulado` +
   `motivo_anulacion`), que los deja tachados y visibles, y desde la ronda 91 también se pueden
   **corregir y borrar** desde la propia aplicación, porque el dueño del proyecto lo pidió así:
   «recuerda también dejar borrar las cosas que introduzca porque puede que me equivoque, o modificar
   también». Lo que no cambia es el fondo de la regla: las dos operaciones **escriben en
   `auditoria`** lo que había antes, así que el programa siempre sabe qué hubo y qué se hizo con
   ello. Lo cuenta entero `app/correcciones.py`; aquí queda dicho para que nadie «arregle» esto
   quitando el rastro.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .dinero import Dinero, Precio


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------------
# Explotación y usuarios
# --------------------------------------------------------------------------


class Explotacion(Base):
    __tablename__ = "explotaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    nif: Mapped[str] = mapped_column(String(20), index=True)
    codigo_siex: Mapped[str | None] = mapped_column(String(40))
    ccaa: Mapped[str] = mapped_column(String(60), default="Castilla y León")
    provincia: Mapped[str] = mapped_column(String(60), default="")
    municipio: Mapped[str] = mapped_column(String(120), default="")
    # **Tres estados, y nace sin contestar** (A13 de `docs/T02_VALORES_POR_DEFECTO.md`, 05/10/2026).
    # Antes nacía en `False`, y ese «no» que nadie había dicho hacía dos cosas graves: **apagaba la
    # comprobación ecológica entera** —si la finca es ecológica y nadie marca la casilla, el programa deja
    # de avisar de que un producto no vale para ecológico, y el agricultor cree que vigila algo que ha
    # dejado de vigilar— y **salía escrito en el documento que se firma** («En ecológico: False»). `None`
    # es «no lo sé», y con el tercer estado el programa avisa en vez de callar.
    produccion_ecologica: Mapped[bool | None] = mapped_column(Boolean, default=None)

    # Los datos de la portada del cuaderno de la Junta (hoja «1.1 DATOS GENERALES DE LA
    # EXPLOTACIÓN»). No son adorno: **sin ellos no se puede rellenar esa hoja**, y esa hoja es la
    # primera del cuaderno que se presenta. Se piden en la pantalla de la finca.
    #
    # Ojo con no confundir tres números que se parecen y no son lo mismo, porque cada uno va a un
    # sitio distinto:
    #   · `codigo_siex`    — el `CodigoSIEX` que se manda al interfaz del FEGA (IUWS).
    #   · `registro_autonomico` — el nº de registro de la explotación en Castilla y León (el
    #     «0837267320» que trae la hoja 1.1 de David, por ejemplo).
    #   · `registro_nacional` — el nº de registro nacional de la explotación (REGA).
    registro_nacional: Mapped[str | None] = mapped_column(String(40))
    registro_autonomico: Mapped[str | None] = mapped_column(String(40))
    direccion: Mapped[str | None] = mapped_column(String(200))
    localidad: Mapped[str | None] = mapped_column(String(120))
    codigo_postal: Mapped[str | None] = mapped_column(String(10))
    telefono: Mapped[str | None] = mapped_column(String(40))
    correo: Mapped[str | None] = mapped_column(String(200))
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    parcelas: Mapped[list["Parcela"]] = relationship(back_populates="explotacion")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    # La finca **en la que está trabajando ahora** esta cuenta. Una cuenta puede tener acceso a varias
    # fincas (ver `AccesoAFinca`); esta columna dice en cuál está, y es la que usan todas las consultas.
    # Cambiar de finca es cambiar esta columna y volver a entrar (ver `routers/fincas_api.py`).
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    clave_hash: Mapped[str] = mapped_column(String(200))
    es_titular: Mapped[bool] = mapped_column(Boolean, default=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    explotacion: Mapped[Explotacion] = relationship()


class AccesoAFinca(Base):
    """Quién puede entrar en una finca (una explotación puede tener **varias cuentas**).

    POR QUÉ EXISTE

    Hasta la ronda 89 una cuenta estaba atada a una sola finca: `usuarios.explotacion_id` era el único
    sitio donde se decía de quién era una finca. Eso deja fuera lo normal en el campo: el matrimonio que
    lleva la misma finca, el hijo que echa una mano los veranos o el técnico que apunta lo que se ha
    hecho. David lo pidió tal cual: «quiero que una explotación puedan acceder varias cuentas, no solo 1».

    CÓMO QUEDA

      · `usuarios.explotacion_id` sigue diciendo **en qué finca está trabajando** esa cuenta, así que
        **todo lo que ya había no cambia**: el aislamiento sigue siendo el mismo (`explotacion_id` en cada
        tabla y 404 para lo de otra finca).
      · Esta tabla dice **en qué fincas puede entrar** cada cuenta, y con qué papel.
      · El titular de la finca es quien la creó: puede añadir y quitar cuentas. Un ayudante puede usar la
        finca entera (apuntar, corregir, anular, sacar el cuaderno) pero **no** decir quién más entra.

    **La finca propia no se puede quitar**: así ninguna cuenta se queda sin finca en la que trabajar.
    """

    __tablename__ = "accesos_a_fincas"
    __table_args__ = (
        UniqueConstraint("usuario_id", "explotacion_id", name="uq_acceso_usuario_finca"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    # «titular» (quien la creó) o «ayudante» (a quien le han dado acceso).
    papel: Mapped[str] = mapped_column(String(20), default="ayudante")
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped[Usuario] = relationship()
    explotacion: Mapped[Explotacion] = relationship()


# --------------------------------------------------------------------------
# Campaña y parcelas
# --------------------------------------------------------------------------


class Campana(Base):
    __tablename__ = "campanas"
    __table_args__ = (UniqueConstraint("explotacion_id", "anio", name="uq_campana_anio"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    anio: Mapped[int] = mapped_column(Integer)
    fecha_inicio: Mapped[dt.date] = mapped_column(Date)
    fecha_fin: Mapped[dt.date] = mapped_column(Date)
    cerrada: Mapped[bool] = mapped_column(Boolean, default=False)
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class Parcela(Base):
    """Una parcela (DGC / recinto SIGPAC).

    `superficie_oficial` distingue la superficie que viene del SIGPAC (no se puede
    tocar a mano) de la estimada por el agricultor. Es una distinción que exige el
    cuaderno y que además evita discusiones: la oficial manda.
    """

    __tablename__ = "parcelas"
    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    alias: Mapped[str] = mapped_column(String(120))
    ref_sigpac: Mapped[str | None] = mapped_column(String(60), index=True)
    provincia: Mapped[str] = mapped_column(String(60), default="")
    municipio: Mapped[str] = mapped_column(String(120), default="")
    codigo_ine: Mapped[str | None] = mapped_column(String(10))
    poligono: Mapped[int | None] = mapped_column(Integer)
    numero_parcela: Mapped[int | None] = mapped_column(Integer)
    numero_recinto: Mapped[int | None] = mapped_column(Integer)
    # Las otras dos partes de la referencia del SIGPAC. Van en 0 cuando no hay, que es lo normal
    # —la parcela del visor `37:70:0:0:503:51` es provincia 37, municipio 70, agregado 0, zona 0—,
    # pero hay parcelas con agregado o con zona distintos de cero, y sin estas dos columnas su
    # referencia no se podía ni guardar ni comprobar.
    agregado: Mapped[int] = mapped_column(Integer, default=0)
    zona: Mapped[int] = mapped_column(Integer, default=0)
    # La referencia catastral de la parcela (la de la Sede del Catastro, 20 caracteres). Se guarda
    # porque el contenido mínimo del CUE la pide por su nombre (`ReferenciaCatastral`) y porque es
    # la que el agricultor tiene en el papel cuando va a la oficina. **No se calcula**: se guarda
    # si él la pega, y si no, se queda vacía.
    referencia_catastral: Mapped[str | None] = mapped_column(String(30))
    # **La superficie que se cultiva: tres estados, y el que falta no es un cero** (A7 de
    # `docs/T02_VALORES_POR_DEFECTO.md`). `None` quiere decir «todavía no sabemos cuántas hectáreas
    # tiene» —el papel de la Junta deja esa casilla en blanco en varias tierras, y el SIGPAC tampoco
    # siempre manda la superficie—, y **no** «tiene cero hectáreas». Antes el defecto era `0.0`, y un
    # cero ahí no era un número feo en una lista: como todas las comprobaciones de superficie comparan
    # contra esta, la tierra pasaba a no poder tratarse ni abonarse (cualquier superficie la supera).
    # Por eso `None` es la respuesta buena y por eso esta columna admite el tercer estado.
    #
    # Ojo, que **no es la superficie del recinto del SIGPAC**: esa es otra magnitud a propósito
    # (`superficie_sigpac_ha`, aquí debajo) y no se copia nunca sola.
    superficie_ha: Mapped[float | None] = mapped_column(Float, default=None)
    superficie_oficial: Mapped[bool] = mapped_column(Boolean, default=False)
    # La superficie del **recinto** según el SIGPAC, que no siempre es la que se cultiva: el
    # cuaderno de la Junta pide las dos por separado («Superficie SIGPAC (ha)» y «Superficie
    # Cultivada (ha)») porque dentro de un mismo recinto puede haber barbecho y dos trozos de
    # avena. `superficie_ha` es la que se cultiva y se trata —es la que se usa para las dosis— y
    # esta es la oficial del recinto entero. Vacío quiere decir «no lo sé», nunca 0.
    superficie_sigpac_ha: Mapped[float | None] = mapped_column(Float)
    uso_sigpac: Mapped[str | None] = mapped_column(String(80))
    # secano | regadio | **None = no lo sé** (A10 de `docs/T02_VALORES_POR_DEFECTO.md`, 05/10/2026). Nacía
    # en `"secano"`, así que **lo que no se sabía se declaraba de secano** y la exportación de la Junta
    # acababa escribiendo «S» de una tierra que puede ser de regadío. El resumen del cuaderno ya cuenta las
    # líneas sin sistema (`cuaderno_cyl._lee_sistema` se niega a ponerlo por defecto).
    sistema: Mapped[str | None] = mapped_column(String(20))
    pendiente_pct: Mapped[float | None] = mapped_column(Float)
    # **Tres estados también aquí** (A12 de `docs/T02_VALORES_POR_DEFECTO.md`, 05/10/2026). Nacían en
    # `False`, así que una tierra sin contestar se leía como «aquí no hay ni río ni toma de agua». De estos
    # dos campos dependen las **restricciones de abonado** (Orden MAV/398/2022) y la **franja de seguridad**
    # de un tratamiento: un «no» que nadie ha dicho **aligera las reglas que le aplican al agricultor**.
    # `None` es «no lo sé», y entonces el programa dice que no ha podido comprobarlo.
    masa_agua_cerca: Mapped[bool | None] = mapped_column(Boolean, default=None)
    captacion_consumo_humano: Mapped[bool | None] = mapped_column(Boolean, default=None)
    # None = no lo sabemos (falta listado o ubicación verificable de esta parcela).
    zona_vulnerable_nitratos: Mapped[bool | None] = mapped_column(Boolean, default=None)
    # WKT. Ver la nota sobre PostGIS en database.py.
    geometria: Mapped[str | None] = mapped_column(Text)
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    explotacion: Mapped[Explotacion] = relationship(back_populates="parcelas")
    cultivos: Mapped[list["ParcelaCultivo"]] = relationship(
        back_populates="parcela", cascade="all, delete-orphan"
    )

    @property
    def centro(self) -> list[float] | None:
        """El centro de la parcela, en `[longitud, latitud]`, o `None` si no tiene forma.

        Es lo que necesita el mapa para abrirse en la tierra del agricultor: sin esto, la primera
        pantalla del mapa no sabría por dónde empezar y habría que pedirle que se buscara a sí
        mismo. Se calcula y no se guarda, por lo mismo que el dibujo: si se guardara, una
        corrección de la forma dejaría el centro mintiendo.
        """
        if not self.geometria:
            return None
        from . import geo

        centro = geo.centroide_wkt(self.geometria)
        return [centro[0], centro[1]] if centro else None

    @property
    def dibujo(self) -> str | None:
        """La forma del trozo, lista para pintar, o `None` si no tiene forma.

        Es una propiedad calculada y no una columna a propósito: si se guardara, una corrección
        de la geometría dejaría el dibujo viejo, y un dibujo que no es el de la parcela es peor
        que no tener dibujo.

        El cálculo se hace aquí y no en la pantalla porque el WKT es un texto largo que no tiene
        por qué viajar al móvil: lo que viaja es la línea que se pinta, que son unos cientos de
        caracteres. Y se importa `geo` dentro de la función para no montar un círculo de
        importaciones al cargar los modelos.
        """
        from . import geo

        return geo.dibujo_svg(self.geometria)


class ParcelaCultivo(Base):
    """Qué se cultiva en una parcela durante una campaña."""

    __tablename__ = "parcela_cultivos"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    parcela_id: Mapped[int] = mapped_column(ForeignKey("parcelas.id"), index=True)
    campana_id: Mapped[int] = mapped_column(ForeignKey("campanas.id"), index=True)
    especie: Mapped[str] = mapped_column(String(120))
    variedad: Mapped[str | None] = mapped_column(String(120))
    # secano | regadio | **None = no lo sé** (A10, ver la nota larga en `Parcela.sistema`). El cultivo de
    # una campaña nace sin sistema declarado, no de secano: la exportación de la Junta lo escribía como
    # «S» sin que nadie lo hubiera dicho.
    sistema: Mapped[str | None] = mapped_column(String(20))
    fecha_inicio: Mapped[dt.date | None] = mapped_column(Date)
    fecha_fin: Mapped[dt.date | None] = mapped_column(Date)

    # El ecorregimen o práctica con la que se acoge esa tierra (la hoja 2.1 del cuaderno de la
    # Junta la llama «Ecoregimen/ Práctica (4)» y en el cuaderno de verdad viene «P3», que es
    # rotación de cultivos). Se guarda tal y como viene del cuaderno: **no hay lista oficial de
    # valores publicada**, así que no se cierra a un catálogo que no existe.
    ecorregimen: Mapped[str | None] = mapped_column(String(40))
    # La superficie cultivada de esa línea, que **no** es la del recinto entero: el cuaderno
    # oficial distingue «Superficie SIGPAC (ha)» de «Superficie Cultivada (ha)». Cuando una
    # tierra se parte en varias líneas (barbecho por un lado, avena por otro), la superficie que
    # se declara es esta. Vacío quiere decir «no lo sé», nunca 0.
    superficie_cultivada_ha: Mapped[float | None] = mapped_column(Float)

    parcela: Mapped[Parcela] = relationship(back_populates="cultivos")


grupo_parcela = Table(
    "grupo_parcela",
    Base.metadata,
    Column("grupo_id", ForeignKey("grupos_parcelas.id", ondelete="CASCADE"), primary_key=True),
    Column("parcela_id", ForeignKey("parcelas.id", ondelete="CASCADE"), primary_key=True),
)


class GrupoParcelas(Base):
    """Unidad Homogénea de Cultivo: parcelas que se llevan igual.

    Su fin es ahorrar trabajo: un tratamiento en seis parcelas de trigo debería
    costar UN registro, no seis. La app oficial lo llama UHC y lo considera
    opcional; aquí es una función de primera clase porque el mayor enemigo del
    cuaderno digital es que dé pereza.
    """

    __tablename__ = "grupos_parcelas"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"))
    cultivo: Mapped[str | None] = mapped_column(String(120))
    # secano | regadio | **None = no lo sé** (A10, ver la nota larga en `Parcela.sistema`): un grupo de
    # tierras recién creado no es de secano, es un grupo del que todavía no se sabe el sistema.
    sistema: Mapped[str | None] = mapped_column(String(20))
    creado_automaticamente: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    parcelas: Mapped[list[Parcela]] = relationship(secondary=grupo_parcela)


class Instalacion(Base):
    """Una nave, un almacén, un invernadero o una balsa.

    Hace falta por dos motivos, y los dos son obligaciones del cuaderno:

    1. **Tratamientos de instalaciones**: cuando se trata un almacén contra insectos o
       roedores, el producto NO se echa en la parcela, se echa en un local. Sin este
       registro, esa sección del cuaderno no se puede cumplimentar de ninguna manera.
    2. **Cosecha comercializada y postcosecha**: saber dónde se guardó y dónde se trató
       el producto ya recogido es parte de la trazabilidad.

    La referencia catastral es lo que identifica el local delante de la administración,
    porque una nave no tiene recinto SIGPAC.
    """

    __tablename__ = "instalaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    alias: Mapped[str] = mapped_column(String(120))
    # almacen | nave | invernadero | balsa | silo | otro
    tipo: Mapped[str] = mapped_column(String(30), default="almacen")
    referencia_catastral: Mapped[str | None] = mapped_column(String(40))
    municipio: Mapped[str] = mapped_column(String(120), default="")
    uso: Mapped[str | None] = mapped_column(String(200))
    superficie_m2: Mapped[float | None] = mapped_column(Float)
    observaciones: Mapped[str | None] = mapped_column(Text)
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


# --------------------------------------------------------------------------
# Maestros: productos, abonos, personas y máquinas
# --------------------------------------------------------------------------


class ProductoFitosanitario(Base):
    """Un producto de la "cesta de la compra".

    La aplicación oficial lo dice claro: todos los productos para aplicar deben
    estar antes en la cesta. Por eso un tratamiento solo puede usar un producto
    que exista aquí.
    """

    __tablename__ = "productos_fitosanitarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    nombre_comercial: Mapped[str] = mapped_column(String(200))
    numero_registro: Mapped[str | None] = mapped_column(String(40), index=True)
    materia_activa: Mapped[str | None] = mapped_column(String(300))
    tipo_producto: Mapped[str | None] = mapped_column(String(120))
    # Límites de la etiqueta. Sin estos datos el programa no puede avisar de nada.
    dosis_maxima: Mapped[float | None] = mapped_column(Float)
    unidad_dosis: Mapped[str] = mapped_column(String(10), default="L/ha")
    plazo_seguridad_dias: Mapped[int | None] = mapped_column(Integer)
    lote: Mapped[str | None] = mapped_column(String(60))
    fecha_caducidad: Mapped[dt.date | None] = mapped_column(Date)
    cantidad_comprada: Mapped[float | None] = mapped_column(Float)
    unidad_compra: Mapped[str] = mapped_column(String(10), default="L")
    fecha_compra: Mapped[dt.date | None] = mapped_column(Date)
    proveedor: Mapped[str | None] = mapped_column(String(200))
    # **Tres estados, y el defecto no afirma nada.** `None` es «nadie ha comprobado si este
    # producto sigue autorizado»; `False` es «está retirado o caducado y no se puede usar». Antes el
    # defecto era `True`, que es la ausencia de un dato convertida en un permiso: bastaba con no
    # tocar la casilla —el bloque de la autorización está plegado y pone «opcional»— para que el
    # programa diera por bueno que el producto se puede usar, y las comprobaciones de
    # `validaciones.py` no podían saltar nunca. Un producto del que no se sabe nada no bloquea
    # (no se puede dejar al agricultor sin apuntar lo que ha hecho), pero se avisa.
    autorizado: Mapped[bool | None] = mapped_column(Boolean, default=None)
    # Lo mismo, y aquí el defecto permissivo tenía además un efecto concreto: en una finca
    # ecológica, `permitido_ecologico = True` por defecto apagaba el aviso `V15_no_ecologico`.
    permitido_ecologico: Mapped[bool | None] = mapped_column(Boolean, default=None)
    # Nº y vigencia de una autorización excepcional (art. 53 RD 1311/2012).
    autorizacion_excepcional: Mapped[str | None] = mapped_column(String(120))
    autorizacion_hasta: Mapped[dt.date | None] = mapped_column(Date)
    foto_etiqueta: Mapped[str | None] = mapped_column(String(400))
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class Fertilizante(Base):
    __tablename__ = "fertilizantes"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    tipo: Mapped[str] = mapped_column(String(30), default="mineral")
    # **La composición, con tres estados** (A6 de `docs/T02_VALORES_POR_DEFECTO.md`): `None` es «no
    # me han dicho la composición» y `0.0` es «lleva cero de este nutriente», que es un dato de
    # verdad —un nitrato amónico tiene 33,5 % de nitrógeno y 0 % de fósforo y potasio—. Antes el
    # defecto era `0.0`, así que las dos cosas eran la misma al guardarse, y la ficha de un abono
    # del que nadie sabía nada afirmaba los tres ceros.
    riqueza_n: Mapped[float | None] = mapped_column(Float, default=None)
    riqueza_p: Mapped[float | None] = mapped_column(Float, default=None)
    riqueza_k: Mapped[float | None] = mapped_column(Float, default=None)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class Aplicador(Base):
    """Quien echa el producto: el propio agricultor, un trabajador o una empresa."""

    __tablename__ = "aplicadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    nif: Mapped[str | None] = mapped_column(String(20))
    es_empresa: Mapped[bool] = mapped_column(Boolean, default=False)
    numero_ropo: Mapped[str | None] = mapped_column(String(60))
    numero_carne: Mapped[str | None] = mapped_column(String(60))
    tipo_carne: Mapped[str | None] = mapped_column(String(60))
    fecha_caducidad_carne: Mapped[dt.date | None] = mapped_column(Date)
    # Solo para instalaciones fijas de aplicación o tratamientos aéreos.
    numero_reganip: Mapped[str | None] = mapped_column(String(60))
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class Asesor(Base):
    """El técnico que asesora: la gestión integrada de plagas y la producción integrada.

    La app oficial lo tiene en «Cuaderno: Asesores/Aplicadores», y el contenido mínimo del
    CUE lo pide en el bloque de tratamientos fitosanitarios (campos 44 a 53: fecha, nombre,
    apellidos, razón social, NIF, **nº de inscripción ROPO**, validación del tratamiento,
    marca de confirmación y contrato de asesoramiento).

    **Por qué es un registro aparte del aplicador.** Son dos personas distintas y la ley las
    distingue: el **asesor** dice qué hay que hacer (y tiene que estar inscrito como asesor),
    y el **aplicador** lo hace (y tiene que tener el carné de aplicador). Muchas veces es la
    misma persona, pero no siempre, y meterlas en la misma tabla haría imposible saber cuál de
    los dos papeles tiene cada uno.

    Ojo con un detalle que es fácil de confundir: **los dos llevan un número de ROPO**, porque
    el ROPO inscribe por separado a asesores y a aplicadores. El documento de SIEX pide «Nº
    inscripción ROPO» en los dos sitios: campo 33 para el aplicador y campo 50 para el asesor.
    Lo que distingue al asesor aquí son su `ambito` y su `entidad_certificacion`.

    Decisión sobre el ROPO: el número de inscripción es obligatorio para poder volcar el
    cuaderno —el interfaz rechaza un asesor que no encuentre en ROPO, con el error
    `ERROR_VALIDAR_ASESOR`—, así que un tratamiento con asesor y sin ROPO **no se puede
    guardar**. Es la misma regla que con el carné del aplicador.
    """

    __tablename__ = "asesores"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    nif: Mapped[str | None] = mapped_column(String(20))
    es_empresa: Mapped[bool] = mapped_column(Boolean, default=False)

    # El número de inscripción en el registro ROPO de asesores. Ver `catalogos.AMBITOS_ASESOR`.
    numero_ropo: Mapped[str | None] = mapped_column(String(60))
    ambito: Mapped[str | None] = mapped_column(String(40))

    # La entidad que certifica: producción integrada, ecológico… Es a quien se le pregunta si
    # el asesoramiento vale para la ayuda que se esté cobrando.
    entidad_certificacion: Mapped[str | None] = mapped_column(String(200))
    telefono: Mapped[str | None] = mapped_column(String(40))
    correo: Mapped[str | None] = mapped_column(String(200))

    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class EquipoAplicacion(Base):
    """Una máquina de echar producto: el pulverizador, el atomizador, la mochila…

    ## Lo que pide el cuaderno de la Junta

    Su hoja 1.3 («Equipos de aplicación de productos fitosanitarios propios de la explotación») pide:
    **descripción del equipo con tipo, marca y modelo** (nota al pie 3), **nº de inscripción en el
    ROMA** (nota 4: en los equipos en los que no sea obligatoria la inscripción, el nº de registro
    que corresponda) y **la fecha de adquisición y la de la última inspección**.

    ## Las tres pestañas de la app oficial, que son tres cosas distintas

    La aplicación de la Junta tiene tres listas de maquinaria, y no son lo mismo:

    * **Maquinaria propia**: la inscrita en el ROMA a nombre del titular.
    * **Maquinaria ajena**: la inscrita en el ROMA que **no es del titular** pero se ha usado (por
      ejemplo, cuando el tratamiento lo hace una empresa de servicios).
    * **Equipos NO ROMA**: lo que no se inscribe en el ROMA: mochilas, carretillas, aperos.

    Por eso está `titularidad`: sin ella, en el cuaderno no se puede decir cuál de las tres es, y la
    fecha de inspección significa cosas distintas en cada caso (un equipo sin ROMA no tiene ITEAF).
    """

    __tablename__ = "equipos_aplicacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str | None] = mapped_column(String(80))
    # De quién es la máquina y si va inscrita en el ROMA. Ver la nota de arriba: son las tres
    # pestañas de la app oficial (propia, ajena y equipos sin ROMA). **Y `None` es «no lo sé»** (A11,
    # 05/10/2026): nacía en `"propia"`, así que **la máquina de otro quedaba como tuya** sin que nadie lo
    # hubiera dicho, y en la hoja 1.3 una propia y una ajena no se apuntan igual.
    titularidad: Mapped[str | None] = mapped_column(String(20))
    marca: Mapped[str | None] = mapped_column(String(80))
    modelo: Mapped[str | None] = mapped_column(String(80))
    numero_roma: Mapped[str | None] = mapped_column(String(60))
    numero_serie: Mapped[str | None] = mapped_column(String(80))
    fecha_adquisicion: Mapped[dt.date | None] = mapped_column(Date)
    fecha_iteaf: Mapped[dt.date | None] = mapped_column(Date)
    fecha_proxima_iteaf: Mapped[dt.date | None] = mapped_column(Date)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


# --------------------------------------------------------------------------
# La maquinaria de la finca (T14, E8)
#
# **Por qué hay cuatro tablas nuevas y no se ha reutilizado `EquipoAplicacion`.** El contrato lo
# dice por su nombre en su §9: «`EquipoAplicacion` no cubre toda la maquinaria». Y es verdad, con
# esas palabras: `EquipoAplicacion` es **una máquina de echar producto** —tres pestañas del cuaderno
# de la Junta, número de ROMA, ITEAF— y de ahí no salen ni un apero, ni un remolque, ni la
# cosechadora, ni las horas, ni el seguro, ni las averías. Dar de alta un remolque como «equipo de
# aplicación» habría acabado pidiéndole un ROMA que no tiene y una ITEAF que no le toca, que es
# justo el dato inventado que este proyecto no escribe.
#
# Lo que sí se hace es **enlazarlos cuando son la misma máquina** (`equipo_aplicacion_id`): el
# pulverizador que ya estaba en el cuaderno aparece en la lista de maquinaria sin volver a
# escribirlo, y desde ahí se corrige una sola vez. Los equipos del cuaderno que todavía no están en
# esta lista se enseñan aparte, diciéndolo, para que nadie crea que se han perdido.
#
# **Y la regla que manda en todo el T14: aquí no se deduce qué inspección le toca a una máquina.**
# Ni por su nombre, ni por su clase, ni por su marca. La aplicabilidad la declara el agricultor
# (`obligaciones_de_maquina`, con `si`/`no`/`no_se` y con el origen de lo que dice), la
# clasificación técnica se pide y se guarda tal cual, y la próxima fecha es **la que trae el papel**
# (`inspecciones_de_maquina.proxima_fecha`), copiada. La lógica está en `app/maquinaria.py`, que es
# un módulo puro y lo cuenta entero.
# --------------------------------------------------------------------------


class Maquina(Base):
    """Una máquina de la finca: el tractor, el remolque, el apero, la cosechadora, el pulverizador.

    Sustituye a la idea de «la maquinaria es `EquipoAplicacion`» (ver la nota de arriba). Es una
    **ficha** —se corrige en el sitio y se puede borrar si no la usa nada—, como las otras fichas de
    lo que se usa, y de ella cuelgan tres cosas: sus obligaciones, sus inspecciones y sus averías.

    ## Los dos campos que hay que entender antes de tocar esto

    * **`clase`** es de qué tipo de máquina se trata, con **nuestras** palabras (tractor, remolque,
      apero, cosechadora, equipo de aplicación, otro). Agrupa la lista y permite leer una fila de un
      vistazo. **No decide nada**: no se usa para saber qué inspecciones le tocan, y hay una prueba
      que lo exige.
    * **`clasificacion_tecnica`** es lo que dice el papel —la ficha del ROMA o el certificado de la
      última inspección— sobre la clasificación de esa máquina. Es **texto libre a propósito**: el
      programa no tiene transcrita la tabla de clasificaciones (es el trabajo legal L07 de
      `docs/MATRIZ_NORMATIVA_CRM.md`, pendiente), así que ofrecer una lista cerrada sería inventarse
      la regla. Vacío quiere decir **«no se sabe»**, y entonces la pantalla lo pide en vez de
      suponerlo: sin clasificación no hay forma de saber qué le toca, y el programa lo dice.

    ## Y tres campos que nacen en «no se sabe» a propósito

    `propiedad`, `disponibilidad` y la aplicabilidad de cada obligación **no nacen diciendo que
    todo está bien**. El contrato lo pide en su §9 («Revisar defaults permisivos antes de
    reutilizarlos»): un campo que por defecto dijera «no necesita inspección» convierte «no lo sé» en
    «cumple», y eso en un programa que le dice al agricultor qué le obliga la ley es una mentira con
    consecuencias. Aquí el valor de partida es `no_se` y la pantalla lo pregunta.
    """

    __tablename__ = "maquinas"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    # Nuestra clasificación para leer la lista. No decide ninguna obligación: ver la cabecera.
    clase: Mapped[str] = mapped_column(String(40), default="otro", index=True)
    # La del papel (ROMA o certificado). Texto libre y puede estar vacío: ver la cabecera.
    clasificacion_tecnica: Mapped[str | None] = mapped_column(String(200))

    # Cómo se identifica: matrícula si la tiene (tractor, remolque, cosechadora) o número de serie
    # (apero). Las dos pueden estar vacías, y las dos se guardan tal cual se leen del papel.
    matricula: Mapped[str | None] = mapped_column(String(30))
    numero_serie: Mapped[str | None] = mapped_column(String(80))
    # El de inscripción en el ROMA. Se apunta aquí **aunque no se sepa si le toca tenerlo**: es un
    # dato del papel, no una afirmación de que la máquina esté obligada a estar inscrita.
    numero_roma: Mapped[str | None] = mapped_column(String(60))

    marca: Mapped[str | None] = mapped_column(String(80))
    modelo: Mapped[str | None] = mapped_column(String(80))
    anio: Mapped[int | None] = mapped_column(Integer)
    # De quién es: propiedad o alquiler (`maquinaria.PROPIEDADES`). Nace en `no_se`: no se puede
    # deducir de nada, y en la hoja del cuaderno una máquina propia y una alquilada no se apuntan
    # igual (ver `T02_VALORES_POR_DEFECTO.md`, A11).
    propiedad: Mapped[str] = mapped_column(String(20), default="no_se")

    # Las horas del cuenta-horas, si la máquina lo tiene y el agricultor lo mira. `None` es «no lo
    # sé»: un cero diría que la máquina no ha trabajado nunca.
    horas: Mapped[float | None] = mapped_column(Float)

    # Si se puede contar con ella para trabajar hoy (`maquinaria.DISPONIBILIDADES`). Nace en `no_se`
    # por lo mismo que la propiedad, y **no se deduce de las averías**: una máquina con una avería
    # apuntada puede estar trabajando igual, y quien lo sabe es el agricultor.
    disponibilidad: Mapped[str] = mapped_column(String(20), default="no_se", index=True)

    # Cuando la máquina **es** uno de los equipos de aplicación del cuaderno (hoja 1.3), aquí se
    # dice cuál: así el pulverizador no se escribe dos veces y la lista de maquinaria y el cuaderno
    # hablan de la misma máquina. Vacío es «esta máquina no está en la hoja 1.3», que es lo normal en
    # un apero o un remolque.
    equipo_aplicacion_id: Mapped[int | None] = mapped_column(ForeignKey("equipos_aplicacion.id"))

    notas: Mapped[str | None] = mapped_column(Text)
    # El identificador de la petición, como en una inspección o una avería: **dos toques del mismo
    # botón no pueden dar de alta dos veces la misma máquina**. Lo manda la pantalla al abrir el
    # formulario (no al guardar: `claveDeReenvio` en `app.js` explica por qué), y la columna nace
    # vacía, así que en una base ya creada `asegurar_columnas` la añade al arrancar.
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class ObligacionDeMaquina(Base):
    """Lo que el agricultor declara sobre una obligación de una máquina: si le aplica, y de dónde sale.

    **Por qué esto es una tabla y no cinco columnas en la máquina.** Porque son cinco cosas
    distintas que se declaran por separado y cada una con su origen: la ITV la dice el papel de la
    ITV, el ROMA la hoja del registro, y el mantenimiento lo dice el agricultor. Con cinco columnas
    habría cinco fechas y ningún sitio donde escribir de dónde sale cada una.

    **Los tres estados, y por qué el de partida es `no_se`.** `si` (le aplica), `no` (no le aplica) y
    `no_se` (no se sabe). Una máquina recién dada de alta **no tiene ninguna fila aquí**, y la ficha
    enseña las cinco obligaciones en «no se sabe»: eso es lo que evita el defecto que el contrato
    señala, que es dar por bueno lo que nadie ha comprobado. Y `origen` dice de dónde sale lo
    declarado (`documento`, `el_agricultor` o `no_se`), porque «no le aplica» sin decir quién lo dice
    no vale nada delante de una inspección.
    """

    __tablename__ = "obligaciones_de_maquina"
    __table_args__ = (UniqueConstraint("maquina_id", "tipo", name="una_por_maquina_y_obligacion"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    maquina_id: Mapped[int] = mapped_column(ForeignKey("maquinas.id"), index=True)
    # itv | iteaf | mantenimiento | seguro | roma (`maquinaria.OBLIGACIONES`).
    tipo: Mapped[str] = mapped_column(String(20))
    # si | no | no_se. Ver la cabecera: `no_se` no es «no le aplica».
    aplicabilidad: Mapped[str] = mapped_column(String(10), default="no_se")
    # documento | el_agricultor | no_se.
    origen: Mapped[str] = mapped_column(String(20), default="no_se")
    # **La fecha de la próxima, cuando se sabe y NO hay ninguna inspección apuntada de la que sacarla.**
    # Es el caso del equipo de echar producto que trae el cuaderno: su hoja 1.3 admite la fecha de la
    # próxima ITEAF sin la de la última, y las dos se preguntan por separado. Sin esta columna, traer ese
    # equipo a la lista **hacía desaparecer una fecha que el agricultor ya tenía escrita** (lo encontró la
    # revisión del ticket): una inspección no se puede crear sin fecha —no diría cuándo fue—, así que la
    # próxima se guarda aquí, con su obligación, y la ficha la enseña diciendo que **no se sabe cuándo fue
    # la última**. Es una fecha **copiada**, nunca calculada: la escribió el agricultor.
    proxima_fecha_declarada: Mapped[dt.date | None] = mapped_column(Date)
    notas: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class InspeccionDeMaquina(Base):
    """Una inspección, un mantenimiento o una renovación: **un hecho con su fecha**.

    Es la parte que el contrato pide «separada» de la obligación: la obligación dice si eso le toca
    a la máquina; esto dice qué pasó, cuándo, cómo salió y qué papel lo demuestra.

    ## Lo que se guarda y lo que no se calcula

    * **`proxima_fecha` es la que trae el papel**, copiada. El programa **no la calcula** sumando un
      plazo: no tiene transcrita la tabla de plazos por clasificación técnica (L07), y una fecha
      calculada sin fuente es un dato inventado con la misma cara que uno verdadero. Si el papel no
      la trae, se queda vacía y la pantalla dice que no se sabe.
    * **`resultado` nace en `no_consta`**, que no es `favorable`. Una inspección apuntada sin decir
      cómo salió deja la máquina en «no se sabe», que es la verdad.
    * **`documento_id` puede estar vacío y eso es un caso normal**, no un error: el contrato pide que
      una inspección sin documento se pueda apuntar y que se diga que no lo trae. Cuando tiene papel,
      el papel es un documento de «los papeles» (`DocumentoAnexo`), y borrar ese papel se contesta
      con un 409 en vez de dejar la inspección apuntando a algo que ya no está.

    ## Nada se borra sin rastro

    Una inspección se puede **corregir** (misma fila, queda en la auditoría), **anular** (`anulado` +
    `motivo_anulacion`: sigue en el cuaderno, tachada) y **borrar** si fue un apunte equivocado.
    La anulada **no cuenta** para la última inspección ni para la próxima fecha: si contara, anular
    lo apuntado por error no arreglaría nada.
    """

    __tablename__ = "inspecciones_de_maquina"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    maquina_id: Mapped[int] = mapped_column(ForeignKey("maquinas.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(20), index=True)

    # La fecha del papel. Es obligatoria: una inspección sin fecha no dice nada.
    fecha: Mapped[dt.date] = mapped_column(Date, index=True)
    # favorable | desfavorable | no_consta. Ver la cabecera.
    resultado: Mapped[str] = mapped_column(String(20), default="no_consta")
    # **La del papel, no una calculada.** Ver la cabecera.
    proxima_fecha: Mapped[dt.date | None] = mapped_column(Date)
    # El papel que lo demuestra, si lo hay. Vacío es «no lo trae», y se dice en la pantalla.
    documento_id: Mapped[int | None] = mapped_column(ForeignKey("documentos_anexos.id"))

    notas: Mapped[str | None] = mapped_column(Text)
    # El identificador de la petición, para que el móvil pueda reintentar sin apuntar dos veces la
    # misma inspección cuando vuelve la cobertura (el caso A12 del contrato).
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class AveriaDeMaquina(Base):
    """Lo que se ha roto, cuándo, y si ya está arreglado.

    El contrato lo pide con dos palabras: «registro de averías». Sirve para lo que de verdad pasa en
    el campo: la máquina se queda en el taller y a la semana nadie se acuerda de por qué.

    **`resuelta` admite tres valores y no nace en ninguno**: `True` (arreglada), `False` (sigue sin
    arreglar) y `None` (no lo sé). Nacer en `False` daría por rota una máquina que igual ya se
    arregló, y nacer en `True` es lo que este ticket no puede hacer: convertir «no lo sé» en
    «está bien». El formulario lo pregunta y no se puede guardar sin contestar.

    **La avería no cambia la disponibilidad de la máquina sola.** Son dos datos distintos y el
    programa los enseña juntos pero no los mezcla: una máquina con una avería apuntada puede estar
    trabajando (con el apero que sí va), y el que lo sabe es el agricultor.
    """

    __tablename__ = "averias_de_maquina"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    maquina_id: Mapped[int] = mapped_column(ForeignKey("maquinas.id"), index=True)

    fecha: Mapped[dt.date] = mapped_column(Date, index=True)
    que_paso: Mapped[str] = mapped_column(Text)
    # True / False / None («no lo sé»). Ver la cabecera.
    resuelta: Mapped[bool | None] = mapped_column(Boolean)
    fecha_resuelta: Mapped[dt.date | None] = mapped_column(Date)
    # Las horas del cuenta-horas cuando se averió: es lo que pide el taller y lo que dice si la
    # máquina va por mantenimiento o por kilómetros. `None` es «no lo miré».
    horas: Mapped[float | None] = mapped_column(Float)
    notas: Mapped[str | None] = mapped_column(Text)
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


# --------------------------------------------------------------------------
# Registro obligatorio 1: tratamiento fitosanitario
# --------------------------------------------------------------------------

class TratamientoFitosanitario(Base):
    """El registro que pasa a ser electrónico obligatorio el 01/01/2027.

    Los campos que se guardan copiados (`riqueza_npk`, `dosis_maxima_etiqueta`,
    `plazo_seguridad_dias`) son deliberados: el cuaderno tiene que reflejar lo que
    decía la etiqueta EL DÍA de la aplicación. Si mañana cambia el producto en el
    catálogo, el registro histórico no puede cambiar con él.
    """

    __tablename__ = "tratamientos"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int] = mapped_column(ForeignKey("campanas.id"), index=True)

    fecha: Mapped[dt.date] = mapped_column(Date, index=True)
    hora_inicio: Mapped[str | None] = mapped_column(String(5))
    hora_fin: Mapped[str | None] = mapped_column(String(5))

    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"), index=True)
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("grupos_parcelas.id"))

    # De qué clase de aplicación se trata. La app oficial las tiene como secciones
    # separadas (tratamiento, semilla tratada, postcosecha, instalaciones) pero los datos
    # son los mismos: lo que cambia es DÓNDE y SOBRE QUÉ se aplica.
    #   parcela          -> en la tierra (lo normal)
    #   semilla_tratada  -> la semilla ya venía tratada: cuenta como aplicación
    #   postcosecha      -> al producto ya recogido, en un almacén
    #   instalaciones    -> al local (nave, almacén, invernadero)
    tipo: Mapped[str] = mapped_column(String(30), default="parcela", index=True)
    instalacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("instalaciones.id"), index=True
    )

    # Solo para postcosecha: qué producto se trató y de qué partida salió.
    producto_cosechado: Mapped[str | None] = mapped_column(String(200))
    lote_cosecha: Mapped[str | None] = mapped_column(String(60))

    superficie_tratada_ha: Mapped[float] = mapped_column(Float)
    cultivo: Mapped[str | None] = mapped_column(String(120))
    variedad: Mapped[str | None] = mapped_column(String(120))

    plaga: Mapped[str | None] = mapped_column(String(200))
    justificacion: Mapped[str | None] = mapped_column(Text)
    estado_cultivo: Mapped[str | None] = mapped_column(String(120))

    producto_id: Mapped[int | None] = mapped_column(ForeignKey("productos_fitosanitarios.id"))
    producto_nombre: Mapped[str | None] = mapped_column(String(200))
    numero_registro: Mapped[str | None] = mapped_column(String(40))
    materia_activa: Mapped[str | None] = mapped_column(String(300))
    lote_producto: Mapped[str | None] = mapped_column(String(60))

    dosis: Mapped[float | None] = mapped_column(Float)
    unidad_dosis: Mapped[str] = mapped_column(String(10), default="L/ha")
    dosis_maxima_etiqueta: Mapped[float | None] = mapped_column(Float)
    cantidad_total: Mapped[float | None] = mapped_column(Float)
    unidad_cantidad_aplicada: Mapped[str | None] = mapped_column(String(20))
    volumen_caldo_l_ha: Mapped[float | None] = mapped_column(Float)

    plazo_seguridad_dias: Mapped[int | None] = mapped_column(Integer)
    fecha_fin_plazo_seguridad: Mapped[dt.date | None] = mapped_column(Date)

    # Solo para tratamientos de instalaciones: los días que hay que esperar antes de
    # volver a entrar sin protección. Es el equivalente al plazo de seguridad, pero para
    # las personas en vez de para la cosecha.
    plazo_reentrada_dias: Mapped[int | None] = mapped_column(Integer)

    aplicador_id: Mapped[int | None] = mapped_column(ForeignKey("aplicadores.id"))
    equipo_id: Mapped[int | None] = mapped_column(ForeignKey("equipos_aplicacion.id"))

    # El asesoramiento del tratamiento: quién lo asesoró y qué dijo. Son los campos 44 a 53
    # del bloque de tratamientos fitosanitarios del contenido mínimo del CUE.
    asesor_id: Mapped[int | None] = mapped_column(ForeignKey("asesores.id"))
    asesor_fecha: Mapped[dt.date | None] = mapped_column(Date)
    # Favorable o desfavorable. `None` es «no lo he dicho», que no es lo mismo que
    # desfavorable: el agricultor puede no haber preguntado.
    asesoramiento_validado: Mapped[bool | None] = mapped_column(Boolean)
    # Hay contrato de asesoramiento firmado (necesario para algunas ayudas).
    asesoramiento_contrato: Mapped[bool | None] = mapped_column(Boolean)

    temperatura_c: Mapped[float | None] = mapped_column(Float)
    humedad_pct: Mapped[float | None] = mapped_column(Float)
    viento_kmh: Mapped[float | None] = mapped_column(Float)
    viento_direccion: Mapped[str | None] = mapped_column(String(20))

    franja_seguridad_respetada: Mapped[bool | None] = mapped_column(Boolean)
    # Si se aplicó a mano (mochila, apero de mano) en vez de con una máquina. Se pregunta porque
    # el interfaz de la Junta lo pide como campo **obligatorio** y el cuaderno no lo recogía: sin
    # él no se puede armar el bloque del aplicador. Vacío es «no lo sé», no «no».
    aplicado_a_mano: Mapped[bool | None] = mapped_column(Boolean)
    # Cómo de bien funcionó. Lista nuestra: ver `catalogos.EFICACIA_DEL_TRATAMIENTO` y el porqué.
    eficacia: Mapped[str | None] = mapped_column(String(20))
    # Si esta aplicación se hizo dentro de una zona vulnerable a nitratos, según el listado
    # oficial de la Junta. **Tres estados, y el tercero es el que importa**: `None` es «no se ha
    # podido comprobar» (la tierra no tiene municipio con código INE, el listado no está cargado,
    # o el apunte es de un grupo de tierras que pueden estar en zonas distintas) y **no** se puede
    # guardar como `False`, porque un `False` afirma que la aplicación se hizo fuera de zona.
    # Y este campo no se queda en una pantalla: entra en el documento que se firma (`firma.py`),
    # donde un `False` inventado ya no se puede corregir sin volver a firmar.
    en_zona_vulnerable: Mapped[bool | None] = mapped_column(Boolean, default=None)
    operadores_expuestos: Mapped[int | None] = mapped_column(Integer)
    incidencias: Mapped[str | None] = mapped_column(Text)
    observaciones: Mapped[str | None] = mapped_column(Text)

    # Nada se borra: se anula con un motivo y queda el rastro.
    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)

    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Decisión: las medidas preventivas se guardan como lista JSON y no en una tabla
    # aparte. El catálogo de medidas lo fija la ley y vive en `catalogos.py`, así que
    # aquí solo hace falta saber CUÁLES se marcaron. Una tabla intermedia con una
    # columna de texto sería una relación que no apunta a ninguna entidad.
    medidas: Mapped[list | None] = mapped_column(JSON, default=list)


# --------------------------------------------------------------------------
# Registro obligatorio 2: fertilización
# --------------------------------------------------------------------------


class PlanAbonado(Base):
    """El plan de abono del año: qué se va a aportar y cuánto.

    **No es un apunte, es una previsión.** Por eso se puede corregir: si a mitad de
    campaña cambia el tiempo o el precio del abono, el plan se ajusta. Lo que no se
    toca nunca son los apuntes de abono que ya se han hecho.

    `necesidad_n/p/k` son los kilos de nutriente por hectárea que el cultivo se va a
    llevar, y es contra lo que después se compara lo que de verdad se ha echado. `detalle`
    guarda el reparto previsto: qué abono, cuánto y en qué momento.
    """

    __tablename__ = "planes_abonado"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int] = mapped_column(ForeignKey("campanas.id"), index=True)
    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"))
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("grupos_parcelas.id"))
    cultivo: Mapped[str] = mapped_column(String(120))
    superficie_ha: Mapped[float] = mapped_column(Float)
    produccion_esperada_kg_ha: Mapped[float | None] = mapped_column(Float)
    necesidad_n: Mapped[float | None] = mapped_column(Float)
    necesidad_p: Mapped[float | None] = mapped_column(Float)
    necesidad_k: Mapped[float | None] = mapped_column(Float)
    aportes_suelo_agua: Mapped[float | None] = mapped_column(Float)
    # **Si se usó una herramienta para hacer el plan.** El contenido mínimo del CUE lo pide en el
    # bloque del plan de abono y no se preguntaba. Es un **sí o no**, tal y como lo pide el anexo
    # (el campo «Herramienta» es booleano): se pregunta igual y así el dato mapea exacto, sin
    # inventarse una lista de opciones ni su equivalencia.
    herramienta: Mapped[bool | None] = mapped_column(Boolean)
    detalle: Mapped[list | None] = mapped_column(JSON, default=list)

    # El análisis en el que se basa el plan. A propósito es un `Integer` y NO una
    # `ForeignKey`: la columna ya existía con ese tipo, y SQLite no sabe añadir una
    # clave foránea a una columna que ya está creada. La pertenencia a la explotación
    # la comprueba el router al guardar, que es donde de verdad se puede explicar el
    # error en castellano.
    analitica_id: Mapped[int | None] = mapped_column(Integer)
    notas: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class MedidaPreventivaDeclarada(Base):
    """Una medida preventiva que el agricultor dice que aplica en su finca.

    La app oficial la tiene en «Explotación: Medidas Preventivas», y el contenido mínimo
    del CUE la sitúa **a nivel de Explotación** (bloque «GIP a nivel de explotación»,
    apartado 1.1 «Medidas preventivas/culturales», con un solo campo: «Medida
    preventiva/cultural»).

    **Por qué es un registro aparte y no una casilla de cada tratamiento.** Son dos cosas
    distintas y las dos hacen falta:

    * **Aquí**: lo que haces normalmente en tu finca. Se declara una vez y vale para todo
      el año. Es lo que pide la administración y lo que se enseña en una inspección.
    * **En cada tratamiento** (`TratamientoFitosanitario.medidas`): lo que hiciste **esa
      vez** antes de decidir echar el producto.

    Decisión: **la medida nunca se borra.** Si un año el agricultor deja de hacer una,
    la fila se queda con `aplicada=False`. Así, cuando alguien pregunte «¿esto lo hacías
    en 2024?», la respuesta está, en vez de haber desaparecido.
    """

    __tablename__ = "medidas_preventivas"
    __table_args__ = (UniqueConstraint("explotacion_id", "medida", name="uq_medida_por_finca"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    # El código del catálogo (`catalogos.MEDIDAS_PREVENTIVAS`). No es una clave foránea
    # porque el catálogo lo fija la ley y vive en código, versionado en git: así un cambio
    # normativo se ve en el historial y no se pierde en un UPDATE.
    medida: Mapped[str] = mapped_column(String(40), index=True)
    aplicada: Mapped[bool] = mapped_column(Boolean, default=True)
    # Lo que el agricultor quiera añadir con sus palabras. Las diez medidas del catálogo no
    # cubren todo lo que se hace en el campo, y obligarle a encajarlo en una casilla sería
    # perder el dato.
    observaciones: Mapped[str | None] = mapped_column(Text)
    declarada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    actualizada_en: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Analitica(Base):
    """Un análisis de laboratorio: suelo, agua de riego, planta, cosecha o residuos.

    La app oficial lo tiene en «Otras Actividades: Analíticas» y es el bloque 13 del
    contenido mínimo del CUE (documento técnico SIEX v3.11).

    **Por qué está aquí y no en un cajón.** Un análisis de suelo es el papel más
    reutilizable que tiene un agricultor: sus números sirven para el plan de abono de
    este año y de los tres siguientes. Si vive en un PDF en el móvil, no sirve para nada.
    Por eso los valores están **por clave** (`parametros`) y no como texto libre: es lo
    que permite que el plan de abono los lea y los enseñe.

    Decisión sobre `parametros`: es una lista de diccionarios `{clave, valor, unidad}` y
    no una columna por parámetro. El motivo es que hay cinco clases de análisis y cada
    una tiene números distintos: con una columna por número, la tabla tendría veinte
    columnas casi siempre vacías. `unidad` se guarda con el valor **a propósito**, para
    que un boletín que venga en otras unidades no se lea como si fueran las mismas.

    Decisión sobre el fichero: se guarda en disco y en la base de datos solo la
    referencia. El boletín de un laboratorio es un PDF de varios megas con fotos, y
    meterlo en una columna haría la copia de seguridad del agricultor inservible.
    """

    __tablename__ = "analiticas"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int] = mapped_column(ForeignKey("campanas.id"), index=True)

    # Qué se ha analizado. Ver `catalogos.TIPOS_ANALITICA`.
    tipo: Mapped[str] = mapped_column(String(30), index=True)

    # De cuándo es la muestra y cuándo dieron el resultado. Son dos fechas distintas y
    # las dos importan: un análisis de hace tres años no vale para decidir el abono de hoy.
    fecha_toma_muestra: Mapped[dt.date] = mapped_column(Date, index=True)
    fecha_resultado: Mapped[dt.date | None] = mapped_column(Date)

    # De dónde salió la muestra. Puede ser de una parcela, de una nave o balsa, o de un
    # lote de producto ya mezclado, y por eso las tres cosas son opcionales.
    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"), index=True)
    instalacion_id: Mapped[int | None] = mapped_column(ForeignKey("instalaciones.id"))
    lote: Mapped[str | None] = mapped_column(String(80))

    # Quién lo hizo. `razon_social_laboratorio` y `nif_laboratorio` son los dos campos
    # que pide el contenido mínimo del CUE para identificar al laboratorio.
    laboratorio: Mapped[str | None] = mapped_column(String(200))
    nif_laboratorio: Mapped[str | None] = mapped_column(String(20))
    numero_informe: Mapped[str | None] = mapped_column(String(80))

    # «Tipo de análisis» y «sustancia activa detectada» del contenido mínimo del CUE. Van
    # como texto libre porque el catálogo oficial de esos dos no lo tenemos: escribir una
    # lista inventada sería peor que dejar que se copie lo que ponga el boletín.
    tipo_analisis: Mapped[str | None] = mapped_column(String(120))
    sustancia_detectada: Mapped[str | None] = mapped_column(String(200))

    # Los números del boletín: `[{clave, valor, unidad}]`. Las claves válidas de cada
    # clase están en `catalogos.PARAMETROS_ANALITICA`.
    parametros: Mapped[list | None] = mapped_column(JSON, default=list)

    # El boletín en PDF o en foto. `fichero_ruta` es relativa a la carpeta de adjuntos.
    fichero_nombre: Mapped[str | None] = mapped_column(String(200))
    fichero_ruta: Mapped[str | None] = mapped_column(String(300))
    fichero_tipo: Mapped[str | None] = mapped_column(String(100))
    fichero_bytes: Mapped[int | None] = mapped_column(Integer)

    observaciones: Mapped[str | None] = mapped_column(Text)

    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class VentaDeCosecha(Base):
    """Lo que se pone en el mercado: la cosecha comercializada y la venta directa.

    La app oficial la tiene en «Otras Actividades: Cosecha Comercializada», y el contenido
    mínimo del CUE la llama «Cosecha comercializada y/o venta directa». Es la sección que
    cierra la trazabilidad: **no es lo que recoges, es lo que sale de la finca**.

    Decisión sobre el nombre: la tabla y la ruta se llaman **venta**, aunque la sección
    oficial se llame «cosecha comercializada». El motivo es que ya existe un `/api/cosecha`
    para «he cogido la cosecha», y dos cosas distintas llamadas «cosecha» en el mismo
    programa es una trampa para quien lo lea dentro de un año. «Lo que he vendido» es,
    además, como lo dice el agricultor.

    **Lo que pide la norma** (bloque 3 del contenido mínimo, «a nivel de Explotación»):
    fecha —que puede ser un intervalo—, producto vegetal y cantidad. `tipo` distingue las
    dos clases que la norma separa: la venta a un comprador y la venta directa.

    **Lo que añadimos nosotros**, todo opcional y por un motivo claro: el lote, el comprador,
    el albarán y las parcelas de origen son lo que hace falta para responder «¿de dónde salió
    esta partida?» cuando un cliente pregunta. Sin eso, la trazabilidad se queda en la
    puerta.

    Decisión sobre el dinero: **no hay precio ni importe.** No es un olvido: lo que la norma
    pide de esta sección es producto, cantidad y fecha, y la facturación está en otra parte
    (Verifactu, factura electrónica) que todavía no toca. Meter un precio a medias sería
    empezar por el final.

    > **Eso era así hasta el T12 (E6, 03/10/2026), y el párrafo de arriba se queda porque
    > explica por qué el campo no estaba, no por qué no está.** Lo que ha cambiado es que ahora
    > **sí** hay importe, precio y vencimiento (abajo), con tres condiciones que son la mitad de
    > este ticket:
    >
    >   1. **El importe se puede no saber.** Una venta de 8.000 kg sin precio es el caso A08 del
    >      contrato: cantidad conocida e **importe pendiente**, nunca un ingreso de cero euros. Por
    >      eso la columna admite vacío y vacío quiere decir «no lo sé», no «cero».
    >   2. **El dinero no se guarda como número de coma flotante.** Estas columnas son
    >      `dinero.Dinero` y `dinero.Precio`: `Decimal` en el programa y texto decimal canónico en
    >      la base (el porqué entero, con lo que se midió, está en `app/dinero.py`).
    >   3. **Esto sigue sin ser una factura fiscal.** Lo que se apunta aquí es la entrega y su
    >      importe; la factura **nuestra**, de gestión, es `FacturaEmitida`, y el contrato dice por
    >      escrito que la emisión fiscal completa «requiere especificación normativa propia antes de
    >      activarse como tal». Aquí no hay ni un impuesto ni un número de serie oficial.
    >
    > Y sigue sin haber una tabla nueva para «lo que salió de la finca»: **esta es la entrega**.
    > El nombre «venta» se conserva porque es como la llama el agricultor y porque ya está en las
    > rutas, los textos y los papeles; renombrarla obligaría a migrar todo eso para no decir nada
    > nuevo.
    """

    __tablename__ = "ventas_de_cosecha"
    __table_args__ = (
        # **La clave de reenvío, única entre las entregas vivas** (T12). Es lo que hace que el
        # móvil que reintenta sin cobertura —o un botón pulsado dos veces— **no apunte la entrega
        # dos veces**: la segunda petición devuelve la misma entrega en vez de crear otra. Va en su
        # columna y no dentro de las observaciones (que son una frase del agricultor y no se tocan).
        #
        # Y es **parcial** (`WHERE anulado = 0`) por el mismo fallo que ya se arregló en el almacén
        # (ver `MovimientoDeExistencias`): un índice único a secas no sabe de anulaciones, así que
        # una entrega anulada seguiría ocupando su clave y el agricultor no podría volver a
        # apuntarla desde el móvil, que reenvía **con la misma clave**. Las dos formas de la
        # condición, porque el programa corre en SQLite y en PostgreSQL.
        Index(
            "uq_venta_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("anulado = 0"),
            postgresql_where=text("anulado = false"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int] = mapped_column(ForeignKey("campanas.id"), index=True)

    # "comercializada" o "venta_directa". Ver `catalogos.TIPOS_VENTA`.
    tipo: Mapped[str] = mapped_column(String(30), default="comercializada", index=True)

    # La fecha de venta. `fecha_fin` existe porque la norma la llama «fecha (intervalo de
    # tiempo)»: una partida puede salir en varios viajes. Si no se rellena, la venta fue de
    # un solo día.
    fecha: Mapped[dt.date] = mapped_column(Date, index=True)
    fecha_fin: Mapped[dt.date | None] = mapped_column(Date)

    # El producto vegetal del contenido mínimo del CUE. Va como texto porque el catálogo
    # oficial no lo tenemos en la documentación: escribir una lista inventada y presentarla
    # como la oficial sería peor que dejar que se escriba lo que pone el albarán.
    producto: Mapped[str] = mapped_column(String(200))
    variedad: Mapped[str | None] = mapped_column(String(120))

    cantidad: Mapped[float] = mapped_column(Float)
    unidad: Mapped[str] = mapped_column(String(10), default="kg")

    # Trazabilidad: de dónde salió y a quién fue.
    lote: Mapped[str | None] = mapped_column(String(80))
    comprador: Mapped[str | None] = mapped_column(String(200))
    numero_albaran: Mapped[str | None] = mapped_column(String(80))
    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"), index=True)
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("grupos_parcelas.id"))

    observaciones: Mapped[str | None] = mapped_column(Text)

    # ── El dinero y el de quién es (T12, E6, 03/10/2026) ─────────────────────────────────────
    #
    # **El cliente, como ficha.** Hasta el T11 el comprador era solo un texto (`comprador`, arriba),
    # y el texto se queda: es lo que pone el albarán y no se reescribe nunca. Esta columna es
    # **el enlace con la agenda** (`Contacto`), la misma que usan las facturas y los albaranes, y
    # es lo que permite contestar «¿cuánto me debe la cooperativa?» sin comparar nombres a ojo.
    # Vacía es «todavía no se ha enlazado», que no es lo mismo que «no tiene cliente».
    contacto_id: Mapped[int | None] = mapped_column(ForeignKey("contactos.id"), index=True)

    # **De qué cosecha salió.** Es el primero de los cuatro que el contrato manda separar: el lote
    # cosechado. Y no hay tabla nueva para él porque **ya existe**: es la labor de tipo cosecha
    # (`/api/cosecha`), con su producto, su cantidad y su tierra. Duplicarla aquí sería tener dos
    # listas de lo mismo, que es el fallo que este proyecto más veces ha pagado. El texto libre
    # `lote` de arriba se queda tal cual: es el número de partida que pone el papel, que no tiene
    # por qué ser el de la cosecha apuntada.
    cosecha_id: Mapped[int | None] = mapped_column(ForeignKey("labores.id"), index=True)

    # Lo que se sabe del importe, y **vacío es «no se sabe»**: es el A08 del contrato. Con
    # `precio_unitario` se calcula (cantidad × precio) al vuelo, sin guardar el resultado dos veces,
    # y por eso las dos columnas pueden estar: si el agricultor escribió el importe del papel,
    # manda ese y el precio queda como referencia de lo que se pactó.
    importe: Mapped[Decimal | None] = mapped_column(Dinero)
    precio_unitario: Mapped[Decimal | None] = mapped_column(Precio)
    # El día acordado de pago. Vacío es «no se ha acordado», y entonces no hay vencimiento que
    # reclamar: poner la fecha de la entrega sería inventarse un plazo que nadie ha pactado.
    vencimiento: Mapped[dt.date | None] = mapped_column(Date)

    # La clave de reenvío de la petición que la creó (ver el índice de arriba).
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))

    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# --------------------------------------------------------------------------
# La factura emitida, el cobro y los ajustes de una entrega (T12, E6, 03/10/2026)
#
# El contrato (§4, S12) empieza así: «Separar lote cosechado, entrega/albarán, factura emitida y
# cobro». Lo que hay aquí son tres de los cuatro (el lote cosechado ya existe: es la labor de tipo
# cosecha), y la separación no es un capricho de nombres. Cada uno es un hecho distinto, ocurre en
# un día distinto y se puede equivocar por su cuenta:
#
#   · La **entrega** es física: la mercancía salió de la finca y el comprador firmó un albarán.
#     Existe aunque no haya ni factura ni cobro, y **así es como se apunta** (la tabla de siempre,
#     `ventas_de_cosecha`, que no se ha duplicado).
#   · La **factura emitida** es un documento **nuestro**, de gestión, que puede agrupar varias
#     entregas y llegar semanas después. No es una factura fiscal: el contrato dice que eso
#     «requiere especificación normativa propia antes de activarse como tal», y aquí no se emite
#     ningún documento con validez ante la ley. Es la cuenta de lo que se ha entregado y de lo que
#     se debe, para que el agricultor sepa qué reclamar.
#   · El **cobro** es dinero, y puede ser **parcial**: el caso A06 del contrato es exactamente eso
#     (factura de 121 € y un pago de 40 € → pendiente 81 €).
#
# LA PROTECCIÓN QUE MANDA SOBRE TODAS LAS DEMÁS: **el dinero se cuenta una vez.** Se consigue con
# dos decisiones que están en el esquema y no en un comentario:
#
#   1. **El importe de la factura es la suma de sus líneas.** No hay una columna de total que se
#      pueda escribir a mano y solapar con las entregas que la componen: `importe_total` se
#      **calcula** de las líneas vivas cada vez que cambian y se guarda solo como la fotografía del
#      día en que se emitió.
#   2. **Una entrega viva está en una sola factura viva.** Lo impide un índice único parcial sobre
#      `LineaDeFacturaEmitida.venta_id`: agrupar dos entregas en una factura no puede duplicar los
#      ingresos porque la misma entrega no puede estar dos veces. La línea se anula (no se borra)
#      para que el rastro quede.
#
# Y sobre el **cobro**, la regla que impide el otro duplicado: un cobro se imputa a **una** factura
# y con **una** cantidad (`importe_imputado`). Un pago mayor que lo que se debe deja el sobrante
# «sin conciliar», contado aparte, en vez de dejar la factura con un pendiente negativo que no se
# puede sumar con nada.
# --------------------------------------------------------------------------


class FacturaEmitida(Base):
    """La factura **nuestra**: la cuenta de lo entregado, que puede agrupar varias entregas.

    ## Lo que es, y lo que no es (esto importa más que el resto del comentario)

    **No es un documento fiscal.** El contrato (§4, S12) lo dice con estas palabras: «La emisión
    fiscal completa requiere especificación normativa propia antes de activarse como tal». Aquí no
    hay número de serie oficial, ni impuestos, ni huella, ni cadena de firmas, ni nada que se pueda
    presentar ante nadie como una factura con validez legal. Lo que hay es **la cuenta del
    agricultor**: qué entregó, a quién, por cuánto y cuánto le queda por cobrar. Por eso los textos
    de la pantalla lo dicen tal cual («nuestra factura de gestión») y no hay ni una palabra de IVA:
    decirle a un agricultor que esto es una factura cuando no lo es sería el peor fallo posible de
    esta pantalla.

    ## El total no se escribe: se suma

    `importe_total` **no se recibe de fuera**. Se calcula sumando las líneas vivas y se guarda como
    la fotografía de lo que se emitió. Es la diferencia entre «agrupar entregas» y «sumar ingresos
    dos veces»: como la factura no tiene un importe propio que pueda solaparse con las entregas que
    la componen, no hay ninguna forma de contarlas dos veces. Si la entrega se corrige después (su
    importe pasa a ser otro), la factura **conserva lo que se emitió** y la pantalla dice que hay
    una diferencia observada —que es lo que el contrato pide: «registrar diferencias observadas sin
    forzar a que una factura original cuadre con un redondeo distinto»—.

    ## Nada cuelga de la campaña por capricho

    Sí lleva `campana_id`, y es una decisión: una factura nuestra se emite **para una campaña** (es
    la cosecha de ese año la que se factura), y así la pantalla de los años puede contarla y no
    borrar un año que tiene facturas sin decirlo. Está clasificada en `OTRAS_COSAS`
    (`routers/explotacion.py`), que es lo que exige
    `test_todas_las_tablas_del_ano_estan_clasificadas`. El **cobro**, en cambio, no cuelga del año:
    es dinero que entra un día, como el libro del almacén, y su campaña la tiene la factura que
    salda (el porqué entero está en `Cobro`).
    """

    __tablename__ = "facturas_emitidas"
    __table_args__ = (
        # Reenviar la misma factura (el móvil sin cobertura, un botón dos veces) devuelve la misma,
        # igual que en las entregas y en los albaranes del almacén. Parcial, por lo mismo: una
        # factura anulada tiene que dejar libre su clave para poder rehacerla.
        Index(
            "uq_factura_emitida_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("anulada = 0"),
            postgresql_where=text("anulada = false"),
        ),
        # Y el número de la factura se busca mucho: es por donde se reconoce un documento repetido.
        Index("ix_factura_emitida_numero", "explotacion_id", "numero"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"), index=True)

    # El número que le pone el agricultor. Vacío es «no lo he numerado», y entonces la pantalla lo
    # llama por su fecha: inventarse una numeración sería peor, porque un número inventado se mete
    # en un papel que va a manos de un cliente.
    numero: Mapped[str | None] = mapped_column(String(80))
    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)
    vencimiento: Mapped[dt.date | None] = mapped_column(Date)

    # El cliente: el texto tal cual (lo que se escribe en el papel) y, si se ha enlazado, su ficha.
    # Los dos, por el mismo motivo que en las entregas: el texto no se reescribe nunca.
    cliente: Mapped[str | None] = mapped_column(String(200))
    cliente_nif: Mapped[str | None] = mapped_column(String(20))
    contacto_id: Mapped[int | None] = mapped_column(ForeignKey("contactos.id"), index=True)

    # La suma de las líneas vivas. Vacío solo si todas sus líneas se anularon.
    importe_total: Mapped[Decimal | None] = mapped_column(Dinero)

    notas: Mapped[str | None] = mapped_column(Text)
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))

    anulada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    lineas: Mapped[list["LineaDeFacturaEmitida"]] = relationship(
        back_populates="factura", cascade="all, delete-orphan"
    )


class LineaDeFacturaEmitida(Base):
    """Una entrega dentro de una factura nuestra. **Una entrega, una línea, una factura.**

    ## Por qué es una línea con los datos copiados y no solo un enlace

    Los tres datos (`descripcion`, `cantidad`, `importe`) se **copian** del albarán el día que se
    factura. Es la regla del proyecto entera —«los datos de la etiqueta se copian al apunte: si
    mañana se corrige la ficha, el apunte histórico no puede cambiar con él»— aplicada al dinero: si
    después se corrige el importe de la entrega, la factura que ya se emitió **no cambia sola**. Lo
    que hace el programa es decir que hay una diferencia, no reescribir el documento.

    ## El índice que impide contar el dinero dos veces

    `venta_id` es único entre las líneas vivas: **una entrega viva no puede estar en dos facturas
    vivas**. Es lo que hace imposible el fallo que el ticket quiere evitar («al agrupar NO se pueden
    duplicar los ingresos») y está en la base, no en una comprobación amable que se puede olvidar.
    La línea no se borra: se anula (`anulada` + `motivo_anulacion`), y al anularla la entrega queda
    libre otra vez. Anular la factura entera anula sus líneas, por el mismo motivo.
    """

    __tablename__ = "lineas_de_factura_emitida"
    __table_args__ = (
        Index(
            "uq_linea_de_factura_por_entrega",
            "explotacion_id",
            "venta_id",
            unique=True,
            sqlite_where=text("anulada = 0"),
            postgresql_where=text("anulada = false"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    factura_emitida_id: Mapped[int] = mapped_column(
        ForeignKey("facturas_emitidas.id"), index=True
    )
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas_de_cosecha.id"), index=True)

    # La fotografía de la entrega el día que se facturó.
    descripcion: Mapped[str | None] = mapped_column(String(200))
    cantidad: Mapped[float | None] = mapped_column(Float)
    unidad: Mapped[str | None] = mapped_column(String(10))
    # Obligatorio: **una entrega sin importe no se puede facturar**, porque una factura sin importe
    # no es una factura. El programa lo dice y manda poner el precio primero (es el A08: la cantidad
    # está, el importe está pendiente, y hasta que no se sepa no hay nada que reclamar).
    importe: Mapped[Decimal] = mapped_column(Dinero, nullable=False)

    anulada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    factura: Mapped[FacturaEmitida] = relationship(back_populates="lineas")


class Cobro(Base):
    """El dinero que entra. **Puede ser parcial, y casi siempre lo es.**

    ## El caso A06, que es la prueba de que esto está bien

    «Factura 121 EUR, pago 40 EUR → pendiente 81; un segundo importe conciliado no crea una segunda
    factura». Las dos mitades están aquí:

      · **`importe_imputado`** es lo que de este cobro va contra la factura, y **nunca es más que lo
        que se debe**: con 121 € facturados y 40 € cobrados, el pendiente es 81 € exactos
        (`ventas.pendiente_de`), y eso se calcula, no se guarda.
      · **Un cobro no crea nada.** No hay ninguna ruta, ni ninguna línea de código, que emita una
        factura a partir de un pago. Conciliar un segundo importe solo dice «este dinero va contra
        esta factura, que ya existía»: el número de facturas no cambia (hay una prueba que lo fija).

    ## Lo que no se sabe a qué va, se dice que no se sabe

    Un ingreso que llega al banco sin decir de qué factura es se apunta **sin conciliar**
    (`factura_emitida_id` vacío) y la pantalla lo enseña en su lista aparte. Es lo que el contrato
    pide en su panel de Economía: «pagos sin factura quedan por conciliar». Conciliar y **deshacer**
    la conciliación no borran el movimiento original: solo cambian a qué factura apunta, y queda en
    la auditoría.

    ## Sin campaña propia, y es una decisión

    El cobro no cuelga del año, como el libro del almacén (`MovimientoDeExistencias`): **es dinero
    que entra un día**, no un apunte del cuaderno, y la campaña de lo que se cobra la tiene la
    factura a la que salda. Colgarlo del año obligaría a decidir de qué año es un pago de enero que
    salda una factura de diciembre, y esa decisión no la tiene el programa: la tiene el agricultor,
    y ya está dicha en la factura.

    ## Y los cobros tampoco cuelgan de una entrega

    Apuntan a una **factura**, no a una entrega. El motivo es que el dinero se cobra contra un
    documento, y permitir imputar un cobro a una entrega suelta abriría la puerta a contar el mismo
    euro dos veces (una por la entrega y otra por la factura que la contiene). La conciliación
    muchos a muchos —un ingreso que salda tres facturas— es el ticket T20 y no se hace aquí: se dice
    en el informe de entrega.
    """

    __tablename__ = "cobros"
    __table_args__ = (
        Index(
            "uq_cobro_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("anulado = 0"),
            postgresql_where=text("anulado = false"),
        ),
        Index("ix_cobro_fecha", "explotacion_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)

    # El día en que entró el dinero. Puede no saberse (un ingreso apuntado de memoria): vacío es
    # «no consta», no «hoy».
    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)
    # **Obligatorio, y tiene que ser mayor que cero.** Un cobro de cero euros no es un cobro, y
    # admitirlo daría una lista de movimientos con renglones que no dicen nada.
    importe: Mapped[Decimal] = mapped_column(Dinero, nullable=False)

    # La factura a la que salda, si se sabe. Vacío es «sin conciliar» (ver arriba).
    factura_emitida_id: Mapped[int | None] = mapped_column(
        ForeignKey("facturas_emitidas.id"), index=True
    )
    # Lo que de este cobro se aplica a esa factura. Vacío cuando no hay factura. **Se guarda y no se
    # recalcula** a propósito: si mañana se corrige el importe de la factura, el reparto que se hizo
    # aquel día no puede cambiar solo.
    importe_imputado: Mapped[Decimal | None] = mapped_column(Dinero)

    # De quién es el dinero. El texto, para lo que diga el banco, y la ficha cuando se enlaza.
    cliente: Mapped[str | None] = mapped_column(String(200))
    contacto_id: Mapped[int | None] = mapped_column(ForeignKey("contactos.id"), index=True)
    # transferencia | efectivo | cheque | confirming | otro (ver `ventas.FORMAS_DE_COBRO`).
    forma: Mapped[str] = mapped_column(String(20), default="transferencia")
    # La referencia del banco («TRANSF 2026/4471»), tal cual. Es lo que permite encontrar el ingreso
    # en el extracto, y por eso se guarda como texto y sin interpretar.
    referencia: Mapped[str | None] = mapped_column(String(120))
    notas: Mapped[str | None] = mapped_column(Text)

    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))

    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class AjusteDeEntrega(Base):
    """Una devolución, o un ajuste de peso, humedad o calidad sobre una entrega.

    ## Por qué no es un número suelto

    Lo pide el contrato con estas palabras: «Registrar devoluciones y ajustes de peso/humedad/calidad
    **con evidencia y origen**». Un número que cambia el importe sin decir de dónde sale es
    exactamente lo que este programa no puede tener: dentro de un año, con una inspección delante,
    nadie sabría si esos 300 kg de menos son una devolución, una báscula distinta o un error de
    tecleo. Por eso hay tres columnas obligatorias y ninguna es un texto libre suelto:

      · **`tipo`** — qué pasó: devolución, peso, humedad o calidad. Es una lista cerrada
        (`ventas.TIPOS_DE_AJUSTE`) porque son cuatro cosas distintas que se cuentan de cuatro
        maneras, y una quinta cosa que no sea ninguna de las cuatro se apunta en las observaciones
        de la entrega, no aquí.
      · **`origen`** — de dónde sale el número: del cliente, de la báscula, de un laboratorio, de un
        acuerdo o de otro sitio. También cerrada, y «otro» obliga a escribirlo en el motivo. **Es la
        columna que contesta «¿y esto quién lo dice?»**.
      · **`motivo`** — la frase del agricultor, con sus palabras. Obligatoria: un ajuste sin
        explicación es un número suelto.

    ## La evidencia

    `evidencia_descripcion` es lo que pone el papel (el número del boletín, lo que dijo el básculero)
    y las cuatro columnas `fichero_*` son el papel en sí, subido con el mismo mecanismo que los
    boletines de laboratorio y las facturas (`app/adjuntos.py`: el fichero va a disco y en la base
    queda la referencia, nunca el nombre que manda el navegador). **Se puede apuntar un ajuste sin
    fichero**, y entonces el programa lo dice en la pantalla («sin papel adjunto») en vez de dar por
    bueno que lo hay: en el campo hay veces que el papel llega después, y bloquear el apunte por eso
    sería impedir apuntar lo que de verdad pasó.

    ## El efecto sobre el importe y sobre los kilos

    `cantidad` e `importe` son **diferencias con signo** (una devolución resta: `-3000` kg,
    `-40.50` €), y la cuenta la hace `ventas.importe_de_una_entrega` sumándolas al importe de la
    entrega. Un ajuste de calidad acordado en euros no mueve los kilos, y una devolución mueve los
    dos: por eso son dos columnas y no una cantidad con una unidad.
    """

    __tablename__ = "ajustes_de_entrega"
    __table_args__ = (
        Index(
            "uq_ajuste_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("anulado = 0"),
            postgresql_where=text("anulado = false"),
        ),
        Index("ix_ajuste_de_una_entrega", "explotacion_id", "venta_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas_de_cosecha.id"), index=True)

    # devolucion | peso | humedad | calidad (ver `ventas.TIPOS_DE_AJUSTE`).
    tipo: Mapped[str] = mapped_column(String(20), index=True)
    fecha: Mapped[dt.date | None] = mapped_column(Date)

    # Las dos diferencias, con signo. Cualquiera de las dos puede no saberse (un ajuste de calidad
    # acordado solo en euros no dice kilos), y **un ajuste no puede quedarse sin ninguna de las
    # dos**: el router lo comprueba, porque un ajuste que no ajusta nada no es nada.
    cantidad: Mapped[float | None] = mapped_column(Float)
    unidad: Mapped[str | None] = mapped_column(String(10))
    importe: Mapped[Decimal | None] = mapped_column(Dinero)

    # cliente | bascula | laboratorio | acuerdo | otro (ver `ventas.ORIGENES_DE_UN_AJUSTE`).
    origen: Mapped[str] = mapped_column(String(40))
    motivo: Mapped[str] = mapped_column(Text)
    evidencia_descripcion: Mapped[str | None] = mapped_column(String(200))

    # El papel, si se ha subido: a disco y aquí solo la referencia (ver `models.Factura`).
    fichero_nombre: Mapped[str | None] = mapped_column(String(200))
    fichero_ruta: Mapped[str | None] = mapped_column(String(300))
    fichero_tipo: Mapped[str | None] = mapped_column(String(120))
    fichero_bytes: Mapped[int | None] = mapped_column(Integer)

    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))

    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class RegistroFertilizacion(Base):
    """Registro de abonado. Obligatorio desde el 01/01/2026."""

    __tablename__ = "fertilizaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int] = mapped_column(ForeignKey("campanas.id"), index=True)

    fecha: Mapped[dt.date] = mapped_column(Date, index=True)
    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"), index=True)
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("grupos_parcelas.id"))
    superficie_ha: Mapped[float] = mapped_column(Float)

    fertilizante_id: Mapped[int | None] = mapped_column(ForeignKey("fertilizantes.id"))
    fertilizante_nombre: Mapped[str | None] = mapped_column(String(200))
    tipo: Mapped[str] = mapped_column(String(30), default="mineral")
    # Copia de la riqueza en el momento del registro, por el mismo motivo que en
    # los tratamientos: el histórico no puede cambiar si alguien edita el abono.
    #
    # **Y con el tercer estado, igual que en la ficha** (A6): `None` es «no se sabe la composición de
    # este abono», no «cero». Las unidades fertilizantes (`uf_*`) se calculan a partir de la riqueza
    # (`uf = kg/ha × riqueza / 100`), así que un abono sin composición **no puede aportar un cero**:
    # no se puede calcular cuánto aporta, y decir 0 sería afirmar en el documento firmado que ese
    # estiércol no lleva nitrógeno. Por eso las `uf_*` también admiten el tercer estado y se quedan
    # en «no se sabe» cuando la riqueza no está.
    #
    # **Las filas que ya están guardadas no cambian**: los apuntes viejos tienen su `0.0` y su
    # `uf_*` calculada, se escriben exactamente igual que siempre en el texto que se firma, y por eso
    # las firmas ya hechas siguen cuadrando (hay una prueba que lo fija: `test_firma.py`).
    riqueza_n: Mapped[float | None] = mapped_column(Float, default=None)
    riqueza_p: Mapped[float | None] = mapped_column(Float, default=None)
    riqueza_k: Mapped[float | None] = mapped_column(Float, default=None)

    kg_ha_producto: Mapped[float] = mapped_column(Float)
    cantidad_total_kg: Mapped[float] = mapped_column(Float)
    uf_n_ha: Mapped[float | None] = mapped_column(Float, default=None)
    uf_p_ha: Mapped[float | None] = mapped_column(Float, default=None)
    uf_k_ha: Mapped[float | None] = mapped_column(Float, default=None)
    uf_n_total: Mapped[float | None] = mapped_column(Float, default=None)
    uf_p_total: Mapped[float | None] = mapped_column(Float, default=None)
    uf_k_total: Mapped[float | None] = mapped_column(Float, default=None)

    modo_aplicacion: Mapped[str | None] = mapped_column(String(60))
    momento: Mapped[str | None] = mapped_column(String(30))
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("planes_abonado.id"))
    # Lo que pide la hoja 6 del cuaderno de la Junta y no se preguntaba: el **nº de albarán** (que
    # es de donde salió el abono que se echó, y que es lo que demuestra la compra) y el **tipo de
    # fertilización**, que el cuaderno abrevia con tres códigos: (F) fertirrigación, (AF) abonado de
    # fondo y (AC) abonado de cobertera.
    numero_albaran: Mapped[str | None] = mapped_column(String(80))
    tipo_fertilizacion: Mapped[str | None] = mapped_column(String(20))
    # La factura de la que salió este abono, cuando el agricultor la ha traído. Es lo que permite
    # contestar «¿de qué compra es este abono?» en una inspección.
    factura_id: Mapped[int | None] = mapped_column(ForeignKey("facturas.id"))
    # Igual que en los tratamientos: `None` es «no se ha podido comprobar» y **no** es «no».
    # De este campo dependen además las reglas de la Orden MAV/398/2022, que solo se pueden
    # mirar cuando se sabe que la tierra está en zona vulnerable (ver `validaciones.py`).
    en_zona_vulnerable: Mapped[bool | None] = mapped_column(Boolean, default=None)
    nitratos_agua_riego: Mapped[float | None] = mapped_column(Float)
    observaciones: Mapped[str | None] = mapped_column(Text)

    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)

    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# --------------------------------------------------------------------------
# Labores y auditoría
# --------------------------------------------------------------------------


class Labor(Base):
    """Siembra, plantación, riego, cosecha y demás trabajos del campo."""

    __tablename__ = "labores"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int] = mapped_column(ForeignKey("campanas.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(30), index=True)
    fecha: Mapped[dt.date] = mapped_column(Date, index=True)
    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"), index=True)
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("grupos_parcelas.id"))
    superficie_ha: Mapped[float | None] = mapped_column(Float)
    cultivo: Mapped[str | None] = mapped_column(String(120))
    variedad: Mapped[str | None] = mapped_column(String(120))

    # --- Siembra y plantación (bloque 6 del contenido mínimo del CUE) ---
    #
    # Decisión: estos campos son columnas y no entradas de `detalles`, aunque `detalles` siga
    # existiendo para lo que no encaja en ninguno. El motivo es que el cuaderno oficial los
    # pide uno por uno, con nombre y número, y son los que permiten responder «¿de qué saco
    # salió esta semilla?» si un día hay un problema con una partida. Un dato que se puede
    # preguntar tiene que poder consultarse, no vivir en un texto libre.
    cantidad_semilla_kg: Mapped[float | None] = mapped_column(Float)
    dosis_siembra_kg_ha: Mapped[float | None] = mapped_column(Float)
    material_tratado: Mapped[bool | None] = mapped_column(Boolean)
    material_adquirido: Mapped[bool | None] = mapped_column(Boolean)
    fecha_adquisicion: Mapped[dt.date | None] = mapped_column(Date)
    # **Qué tratamiento recibió la semilla, cuándo y si funcionó.** Es el bloque «uso de semilla
    # tratada» del anexo II, y hasta la ronda 5 solo se apuntaba «semilla tratada: sí»: se sabía
    # que venía tratada y no con qué, que es justo lo que hay que poder contestar si un día se
    # pregunta por una partida de grano. `eficacia` usa la misma lista que la de los tratamientos
    # (ver `catalogos.EFICACIA_DEL_TRATAMIENTO`): es la misma pregunta.
    tratamiento_semilla: Mapped[str | None] = mapped_column(String(200))
    fecha_tratamiento_semilla: Mapped[dt.date | None] = mapped_column(Date)
    eficacia_tratamiento_semilla: Mapped[str | None] = mapped_column(String(20))
    lote_semilla: Mapped[str | None] = mapped_column(String(80))
    siembra_directa: Mapped[bool | None] = mapped_column(Boolean)
    densidad_plantacion: Mapped[float | None] = mapped_column(Float)
    marco_plantacion: Mapped[str | None] = mapped_column(String(60))
    # El pastoreo. Son dos preguntas de sí o no que el interfaz de la Junta exige como
    # obligatorias, y el cuaderno no las hacía: sin ellas no se puede armar el bloque del
    # pastoreo, uno de los que salen de esta misma tabla. Vacío es «no lo sé», nunca «no».
    animales_terceros: Mapped[bool | None] = mapped_column(Boolean)
    animales_propios: Mapped[bool | None] = mapped_column(Boolean)
    # **Con qué máquina se hizo.** Faltaba, y es un dato que el contenido mínimo del CUE pide en
    # los bloques de labores y de siembra («Maquinaria», con sus datos por máquina). Los
    # tratamientos ya lo tenían (`equipo_id`) y las labores no: se podía apuntar que se labró, y
    # no con qué. Es opcional a propósito, porque hay labores a mano y porque obligar a tener la
    # máquina dada de alta antes de apuntar el trabajo es la forma de que no se apunte.
    equipo_id: Mapped[int | None] = mapped_column(ForeignKey("equipos_aplicacion.id"))
    semillas_siembra: Mapped[bool | None] = mapped_column(Boolean)
    plantas_cosechadas: Mapped[bool | None] = mapped_column(Boolean)
    sin_cosechar_ambiental: Mapped[bool | None] = mapped_column(Boolean)
    restos_cosecha_depositados: Mapped[bool | None] = mapped_column(Boolean)
    fecha_establecimiento_cubierta: Mapped[dt.date | None] = mapped_column(Date)
    tipo_cobertura: Mapped[str | None] = mapped_column(String(120))
    anchura_cubierta_m: Mapped[float | None] = mapped_column(Float)
    anchura_libre_proyeccion_m: Mapped[float | None] = mapped_column(Float)
    restos_desbroce_depositados: Mapped[bool | None] = mapped_column(Boolean)
    restos_poda_depositados: Mapped[bool | None] = mapped_column(Boolean)

    # --- Riego (el agua también es un dato del cuaderno) ---
    #
    # El contenido mínimo del CUE sitúa estos datos en el subbloque de fertirrigación del
    # bloque de fertilización (campos 34 a 42). Nosotros los guardamos en la labor de riego,
    # que es donde el agricultor los apunta cuando riega, y al volcar se llevan a su sitio.
    # Está explicado en `iuws_contenido.py`.
    volumen_agua: Mapped[float | None] = mapped_column(Float)
    unidad_agua: Mapped[str | None] = mapped_column(String(10))
    origen_agua: Mapped[str | None] = mapped_column(String(40))
    sistema_riego: Mapped[str | None] = mapped_column(String(40))
    numero_contador: Mapped[str | None] = mapped_column(String(60))
    nitratos_agua: Mapped[float | None] = mapped_column(Float)

    # Detalles que cambian según el tipo y no encajan en ninguno de los de arriba. Van en
    # JSON en vez de en treinta columnas casi siempre vacías.
    detalles: Mapped[dict | None] = mapped_column(JSON)
    observaciones: Mapped[str | None] = mapped_column(Text)
    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class Auditoria(Base):
    """Quién cambió qué y cuándo.

    Es lo que permite decir con la cabeza alta que un cuaderno es de fiar: si un
    dato se corrige, queda el rastro de la corrección.
    """

    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    entidad: Mapped[str] = mapped_column(String(60))
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    # **`accion` mide 80 y no 30, y esto fue un defecto de producción** (02/10/2026). Estaba en 30, y
    # cuatro de las 31 etiquetas que el programa escribe se pasaban (35, 31, 38 y 38 caracteres:
    # `crear_desde_el_cuaderno_de_la_junta`, `crear_desde_un_lote_de_recintos`,
    # `rellenar_desde_el_cuaderno_de_la_junta` y `traer_tierras_del_cuaderno_de_la_junta`).
    #
    # **SQLite no comprueba la longitud de un `VARCHAR`**, así que en el ordenador del agricultor no
    # pasaba nada; **PostgreSQL sí**, y como la fila del rastro se escribe **en la misma transacción**
    # que la operación, lo que fallaba entero era **la operación**: traer las tierras del cuaderno de la
    # Junta, rellenar desde él, crear desde un lote de recintos y crear desde ese cuaderno **no se podían
    # hacer en producción**. Se midió al correr la suite contra PostgreSQL: 67 pruebas en rojo por esto,
    # con `StringDataRightTruncation` y la etiqueta concreta en el error.
    #
    # Se ensancha en vez de acortar las etiquetas: son identificadores internos y cuanto más digan, mejor
    # para quien lea el rastro dentro de dos años. Y hay una prueba guardiana
    # (`tests/test_las_etiquetas_del_rastro_caben.py`) que lee **todas** las etiquetas del código y
    # comprueba que ninguna se pasa de esta medida: el defecto era «un texto de longitud libre en un sitio
    # con tope fijo», y eso se vigila con una prueba, no con cuidado.
    #
    # *Para una base de PostgreSQL que ya existiera con la columna en 30 hace falta ensancharla a mano*
    # (`ALTER TABLE auditoria ALTER COLUMN accion TYPE varchar(80)`), porque `asegurar_columnas` sabe
    # **añadir** columnas que faltan, no **ensanchar** una que ya está. Hoy no hay ninguna instalación
    # así —la de producción no es PostgreSQL todavía—, y por eso no se ha construido esa pieza.
    accion: Mapped[str] = mapped_column(String(80))
    datos: Mapped[dict | None] = mapped_column(JSON)
    fecha: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class Firma(Base):
    """La firma del cuaderno, o de un apunte suelto.

    **Una firma nunca se borra ni se anula.** Una firma es la prueba de lo que había en
    un momento dado; quitarla sería borrar la prueba. Si el cuaderno cambia después de
    firmarlo, lo que se hace es **firmarlo otra vez**, y quedan las dos: así se ve la
    historia, que es justo lo que interesa en una inspección.

    `huella` es lo que se firmó: la huella del fichero canónico del cuaderno. Se guarda
    para poder comprobar, cada vez que se mire el cuaderno, que nadie lo ha cambiado
    desde entonces.

    `verificada_criptograficamente` dice si **se ha comprobado de verdad** que esa firma
    corresponde a este cuaderno y a este certificado. Desde la ronda 12 sí se comprueba, con
    `app/cades.py`, y se pone en verdadero solo cuando la comprobación ha salido bien.

    Y hay un tercer caso que importa tanto como los otros dos: **no haber podido comprobar**.
    Una firma de curva elíptica no se sabe leer aquí todavía. Eso deja el campo en falso y
    `nota_verificacion` dice por qué. Lo que **no** se hace es ponerlo en falso sin más: un
    «no» y un «no lo sé» no son lo mismo, y confundirlos sería llamar mentiroso a un
    agricultor por no saber leer su certificado.
    """

    __tablename__ = "firmas"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    # "cuaderno", "tratamiento", "fertilizacion" o "labor".
    entidad: Mapped[str] = mapped_column(String(40), index=True)
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"))

    huella: Mapped[str] = mapped_column(String(64), index=True)
    version_canonica: Mapped[int] = mapped_column(Integer, default=1)
    algoritmo: Mapped[str] = mapped_column(String(40), default="SHA256withRSA")
    formato: Mapped[str] = mapped_column(String(20), default="CAdES")

    firmante_nif: Mapped[str] = mapped_column(String(20), default="")
    firmante_nombre: Mapped[str] = mapped_column(String(200), default="")

    # El fichero de firma que devuelve AutoFirma, tal cual, en base64.
    contenido: Mapped[str | None] = mapped_column(Text)
    nombre_del_fichero: Mapped[str | None] = mapped_column(String(200))

    firmado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    verificada_criptograficamente: Mapped[bool] = mapped_column(Boolean, default=False)
    # Qué se comprobó y qué no, en palabras. Se guarda para que dentro de un año se pueda saber
    # por qué una firma vieja está marcada como no comprobada, sin tener que reproducir nada.
    nota_verificacion: Mapped[str | None] = mapped_column(Text)


class DocumentoAnexo(Base):
    """La documentación que acompaña al cuaderno: contratos, facturas, albaranes, papeles.

    **Esta sección faltaba, y se encontró leyendo las instrucciones oficiales.** La app de la
    Junta la llama «Documentación» y dice, con estas palabras: *«permite guardar la
    documentación complementaria al Cuaderno: contratos, facturas, albaranes de entrega de
    envases a Sigfito, etc. La documentación puede organizarse en distintas carpetas.»*

    Y no es un adorno: en una inspección, el cuaderno dice lo que se hizo pero **los papeles son
    los que lo demuestran**. El contrato de arrendamiento de la tierra, la factura del producto,
    el resguardo de Sigfito de los envases vacíos. Sin un sitio donde estén, acaban en una caja
    de zapatos o en el móvil de quien los hizo.

    Decisiones:

    * **El fichero va a disco, nunca a la base de datos** (`app/adjuntos.py`), por el mismo motivo
      que los boletines de laboratorio: un papel de un agricultor no puede acabar en un
      repositorio, y meter PDFs en la base haría que cada copia de seguridad pesara cientos de
      megas.
    * **`carpeta` es texto libre del agricultor**, no una lista cerrada. La app oficial dice que
      «puede organizarse en distintas carpetas» y no impone cuáles: cada uno guarda sus papeles
      como los tiene en el armario. `catalogos.CARPETAS_SUGERIDAS` son sugerencias, y hay un test
      que comprueba que son solo eso.
    * **`tipo` sí sale del documento oficial** (contrato, factura, albarán de Sigfito…) más
      `otros`, porque el documento los nombra y luego dice «etc.».
    * **Las dos salidas siguen existiendo, y no son lo mismo** (ronda 94). **Anular** es «este papel
      no era lo que yo pensaba»: se queda, con su motivo escrito y **con su fichero**, porque el
      fichero es la prueba. **Borrar** es «esto no debería estar aquí» —el agricultor se ha
      equivocado al subirlo—: entonces la fila desaparece y **el fichero se va con ella**, porque
      dejarlo en el disco es basura que nadie va a limpiar. En los dos casos queda el rastro en la
      auditoría. El porqué entero está en `routers/documentos_api.borrar`.
    """

    __tablename__ = "documentos_anexos"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"))

    # La carpeta donde el agricultor lo archiva. Texto libre: ver la decisión de arriba.
    carpeta: Mapped[str] = mapped_column(String(80), default="")
    # Cómo se llama el papel, para poder buscarlo sin abrirlo.
    titulo: Mapped[str] = mapped_column(String(200), default="")
    # De qué es: contrato, factura, albarán de Sigfito… Ver `catalogos.TIPOS_DOCUMENTO`.
    tipo: Mapped[str] = mapped_column(String(40), default="otros")
    # La fecha del papel, que no es la de subirlo: una factura de marzo se sube en junio.
    fecha: Mapped[dt.date | None] = mapped_column(Date)
    # A quién o de qué es: el proveedor, el arrendador, el número de factura.
    quien: Mapped[str | None] = mapped_column(String(200))
    notas: Mapped[str | None] = mapped_column(Text)

    # El fichero en sí. `fichero_ruta` es relativa a la carpeta de adjuntos.
    fichero_nombre: Mapped[str | None] = mapped_column(String(200))
    fichero_ruta: Mapped[str | None] = mapped_column(String(300))
    fichero_tipo: Mapped[str | None] = mapped_column(String(120))
    fichero_bytes: Mapped[int | None] = mapped_column(Integer)

    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


# --------------------------------------------------------------------------
# Facturas de compra: de dónde salió lo que se echa
# --------------------------------------------------------------------------


class Factura(Base):
    """Una factura de compra: la prueba de que el producto se compró.

    ## Por qué está esto aquí y no en un cajón

    El cuaderno de la Junta pide, en la hoja 9.1 (fertilización de los ecorregímenes), la
    **«Empresa suministradora»** y el **«Nº de factura»**; la hoja 6 pide el **«Nº de albarán»**; y
    la hoja «doc» del propio cuaderno dice que hay que conservar «las facturas u otros documentos
    que justifiquen la adquisición de los productos fitosanitarios» **durante al menos tres años**.
    O sea: sin factura, esas casillas se quedan vacías y no hay nada que enseñe de dónde salió lo
    que se echó.

    ## Lo que se guarda, y lo que no

    * **Los datos del papel tal y como los ha confirmado el agricultor.** La lectura automática hace
      una **propuesta**, y él la corrige antes de guardar: lo que queda guardado es lo que él ha
      dado por bueno, no lo que adivinó un programa.
    * **`leida_por`** dice de dónde salió la propuesta (`pdf`, `escaneo`, `foto` o `a mano`). Está
      para poder explicar después por qué una factura tiene un dato raro: si se leyó de una foto
      con el lector en inglés, es normal que una palabra con eñe esté mal escrita.
    * **El fichero se guarda** (el PDF o la foto), porque la factura es el justificante. Va a disco
      y no a la base, igual que los boletines y los papeles.
    * **Se puede anular, corregir y borrar, y cada cosa es lo suyo** (ronda 94). **Anular** deja dicho
      que no vale, con su motivo, y conserva el justificante. **Corregir** cambia la factura en su
      misma fila —y con ella sus líneas, que se rehacen— dejando en la auditoría lo que decía antes.
      **Borrar** se lleva la fila, sus líneas y el fichero del disco, pero **solo si con eso la cesta
      del almacén no empieza a decir cosas que no son**: el porqué entero, con la decisión y sus
      motivos, está en `routers/facturas_api.borrar_factura`.
    """

    __tablename__ = "facturas"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"), index=True)

    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)
    proveedor: Mapped[str | None] = mapped_column(String(200))
    proveedor_nif: Mapped[str | None] = mapped_column(String(20))
    numero_factura: Mapped[str | None] = mapped_column(String(80), index=True)
    base_imponible: Mapped[float | None] = mapped_column(Float)
    cuota_iva: Mapped[float | None] = mapped_column(Float)
    tipo_iva_pct: Mapped[float | None] = mapped_column(Float)
    total: Mapped[float | None] = mapped_column(Float)
    notas: Mapped[str | None] = mapped_column(Text)

    # De dónde salió la propuesta: pdf | escaneo | foto | a mano. Ver la decisión de arriba.
    leida_por: Mapped[str | None] = mapped_column(String(20))
    # La huella del fichero: sirve para avisar de que esa misma factura ya se subió.
    huella: Mapped[str | None] = mapped_column(String(64), index=True)

    fichero_nombre: Mapped[str | None] = mapped_column(String(200))
    fichero_ruta: Mapped[str | None] = mapped_column(String(300))
    fichero_tipo: Mapped[str | None] = mapped_column(String(120))
    fichero_bytes: Mapped[int | None] = mapped_column(Integer)

    anulada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    lineas: Mapped[list["LineaDeFactura"]] = relationship(
        back_populates="factura", cascade="all, delete-orphan"
    )


class LineaDeFactura(Base):
    """Una línea de la factura: qué se compró, cuánto y por cuánto.

    La línea puede estar **enganchada a un producto de la cesta** (`producto_id`) o a un abono
    (`fertilizante_id`). Ese enganche es lo que hace que la factura sirva para algo más que para
    guardar un papel: con él se sabe **cuánto producto se ha comprado** y se puede comparar con lo
    que se ha echado.

    Si la línea no está enganchada a nada, se guarda igual con su descripción: hay facturas que
    traen cosas que no son ni productos ni abonos (unas botas, una reparación), y esas no tienen por
    qué acabar en la cesta.
    """

    __tablename__ = "lineas_de_factura"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    factura_id: Mapped[int] = mapped_column(ForeignKey("facturas.id"), index=True)

    descripcion: Mapped[str] = mapped_column(String(200))
    cantidad: Mapped[float | None] = mapped_column(Float)
    unidad: Mapped[str | None] = mapped_column(String(20))
    precio_unitario: Mapped[float | None] = mapped_column(Float)
    importe: Mapped[float | None] = mapped_column(Float)
    # El número de registro que viene impreso en la factura, tal cual. Es el dato que identifica al
    # producto fitosanitario sin lugar a dudas, y el que permite engancharlo con la cesta.
    numero_registro: Mapped[str | None] = mapped_column(String(40))
    lote: Mapped[str | None] = mapped_column(String(60))

    producto_id: Mapped[int | None] = mapped_column(ForeignKey("productos_fitosanitarios.id"))
    fertilizante_id: Mapped[int | None] = mapped_column(ForeignKey("fertilizantes.id"))

    factura: Mapped[Factura] = relationship(back_populates="lineas")


# --------------------------------------------------------------------------
# El almacén: el artículo, el lote y el libro de movimientos (T09, 03/10/2026)
#
# Hasta aquí, «lo que tengo en el almacén» **se calculaba**: lo comprado salían de las líneas de las
# facturas y lo gastado de los tratamientos (`servicios.situacion_de_la_cesta`), y la resta se hacía
# cada vez que se miraba. Nada de eso se guardaba.
#
# Eso contestaba a «¿me queda producto?» y lo sigue contestando igual —esa cuenta **no se ha
# tocado**—, pero no contesta a tres cosas que pide una inspección y que el contrato del CRM pide
# desde el primer día:
#
#   1. **De qué lote salió lo que se echó.** Un número de lote en la etiqueta es la única forma de
#      seguirle la pista a una partida cuando el fabricante avisa de un problema.
#   2. **Qué entró de verdad y cuándo.** Una factura no prueba que la mercancía haya llegado: la
#      prueba es el albarán. Y son dos hechos distintos que pueden ocurrir con semanas de diferencia.
#   3. **Qué se perdió y qué se contó mal.** Una merma o un conteo distinto no son ni una compra ni
#      un gasto, y hasta ahora no había dónde apuntarlos.
#
# LA PROTECCIÓN QUE MANDA SOBRE TODAS LAS DEMÁS, y por la que estas tablas están hechas así:
# **la misma mercancía no puede entrar dos veces.** Se evita por dos caminos, y los dos importan:
#
#   · **La factura no mete nada en el almacén.** El hecho físico es la recepción del albarán
#     (`Recepcion`), y es ella —y solo ella— la que crea las entradas del libro. Que llegue después
#     la factura no añade ni un litro: se engancha al albarán (`Recepcion.factura_id`) y ahí se
#     acaba. Es el caso A15 del contrato, y es exactamente el fallo que este ticket tenía que
#     impedir.
#   · **Recibir dos veces el mismo albarán devuelve el mismo resultado**, no otro. Se reconoce por
#     su clave de reenvío (lo que manda la cola del móvil) y, sobre todo, por el número del albarán
#     con su proveedor y su año, que es lo que identifica un papel de verdad.
#
# Y una decisión que hay que entender para no «arreglarla»: **el libro NO se suma a la cuenta de la
# cesta**. Son dos vistas de lo mismo y se contestan por separado —`situacion_de_la_cesta` sigue
# calculando lo comprado con las facturas y lo echado con los tratamientos, tal y como está—. Si
# alguien sumara las dos, cada litro contaría dos veces. Hay una prueba que lo fija
# (`tests/test_recepciones_lotes_y_movimientos.py`, la que comprueba que recibir un albarán no
# cambia ni un número de la cesta).
# --------------------------------------------------------------------------


class Articulo(Base):
    """Lo que se compra y se gasta: un producto de tratamiento, un abono, una semilla, otra cosa.

    ## Por qué hay una tabla nueva si ya existen el producto y el abono

    Porque el almacén no solo guarda productos de tratamiento y abonos. El contrato (§4 y la pantalla
    S08) pide cuatro pestañas —productos, abonos, **semillas** y otros insumos—, y las dos fichas que
    hay no cubren las dos últimas: una semilla no es un producto de tratamiento ni un abono, y una
    garrafa de aceite hidráulico tampoco. Meterlas en `ProductoFitosanitario` sería mentir en la
    ficha del producto.

    Pero **el artículo no sustituye a esas fichas: las enlaza** (`producto_id`, `fertilizante_id`).
    Es lo que hace que el almacén siga hablando el mismo idioma que el resto del programa: el lote
    del Glifosato que entró por albarán es el Glifosato de la cesta, y el abono del saco es el abono
    que se echa en el apunte. Sin ese enlace habría dos listas de lo mismo y un día dirían cosas
    distintas.

    ## La unidad, explícita y de una sola familia

    `unidad` es la unidad en la que se cuenta este artículo en el almacén (L, kg, mL, g, cc o
    «ud» para lo que se cuenta por unidades). **Los litros no se suman con los kilos**: para eso
    hace falta la densidad, que no sabemos y cambia de un producto a otro
    (`legal.se_pueden_comparar`). Cuando la unidad no se sabe, se queda en blanco —no en «L»—, y
    entonces el almacén dice que no puede hacer la cuenta en vez de hacerla mal.
    """

    __tablename__ = "articulos"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    # fitosanitario | abono | semilla | otros. Son los códigos de `servicios.CATEGORIAS_DE_ARTICULO`,
    # y las etiquetas que lee el agricultor están en `textos.ALMACEN` (una prueba comprueba que no
    # falta ninguna).
    categoria: Mapped[str] = mapped_column(String(20), default="otros")
    # Vacío es «no se sabe en qué unidad se cuenta», que NO es litros ni kilos.
    unidad: Mapped[str | None] = mapped_column(String(10))
    # De qué ficha del programa sale este artículo, si sale de alguna (ver la decisión de arriba).
    producto_id: Mapped[int | None] = mapped_column(ForeignKey("productos_fitosanitarios.id"))
    fertilizante_id: Mapped[int | None] = mapped_column(ForeignKey("fertilizantes.id"))
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    lotes: Mapped[list["Lote"]] = relationship(back_populates="articulo")


class Lote(Base):
    """El lote de la etiqueta: el número que va impreso en el envase, y lo que caduca.

    **Las existencias son por lote, no por artículo**, y ese es el motivo de que esta tabla exista.
    «Me quedan 20 litros de Glifosato» sirve para comprar; «me quedan 20 litros del lote 4471-A»
    sirve para saber si lo que eché la semana pasada era del lote del que el fabricante ha avisado.
    Un artículo tiene varios lotes a la vez y cada uno lleva su cuenta.

    **Un movimiento siempre pertenece a un lote** (`MovimientoDeExistencias.lote_id` es obligatorio),
    y por eso no hay mercancía «suelta» que no se pueda contar. Cuando la etiqueta no dice el número
    —o el agricultor no lo ha mirado—, el lote existe igual con `numero_lote` vacío: es el lote «sin
    número», que es una cosa de verdad y no un hueco. Lo que **no** se hace es inventarse un número
    ni dar por bueno el de otro envase.

    **Lo que no se sabe se queda en blanco.** `fecha_caducidad = None` es «no lo he mirado», y no es
    lo mismo que «no caduca»: en el almacén, un vencimiento desconocido **no** se cuenta como
    vigente (contrato §10), y hay una prueba que lo fija.
    """

    __tablename__ = "lotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    articulo_id: Mapped[int] = mapped_column(ForeignKey("articulos.id"), index=True)
    # El número de la etiqueta, tal cual viene impreso. Vacío = la etiqueta no lo dice (o no se ha
    # mirado): es un lote sin número, no un lote «0».
    numero_lote: Mapped[str | None] = mapped_column(String(80))
    fecha_caducidad: Mapped[dt.date | None] = mapped_column(Date)
    # El envase. El contrato lo pide con nombre y apellido: «Unidad comercial (saco, garrafa)
    # necesita contenido por envase», y **sin la densidad no se pasa de litros a kilos**. Aquí solo
    # se guarda lo que pone el envase; convertirlo es otra cosa y no se hace sola.
    presentacion: Mapped[str | None] = mapped_column(String(80))
    contenido_por_envase: Mapped[float | None] = mapped_column(Float)
    # Dónde está guardado (el almacén, la nave del fondo, el remolque). Texto libre, como la carpeta
    # de los papeles: cada uno guarda sus cosas donde las tiene.
    ubicacion: Mapped[str | None] = mapped_column(String(120))
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    articulo: Mapped[Articulo] = relationship(back_populates="lotes")


class MovimientoDeExistencias(Base):
    """El libro: lo que entró, lo que salió, lo que se perdió y lo que se contó distinto.

    ## Los cuatro tipos, y por qué son cuatro

      · **`entrada`** — la mercancía que llega: la de un albarán (lo normal, `origen_tipo="recepcion"`),
        una compra sin albarán en la mano, o algo que vuelve (una devolución).
      · **`salida`** — lo que se gasta: un tratamiento o un abono (`origen_tipo="tratamiento"` o
        `"fertilizacion"`), o algo que se saca del almacén por otro motivo, con su explicación.
      · **`merma`** — lo que se pierde sin gastarse: un envase roto, un derrame, lo que se ha
        estropeado. **No es un consumo**: no cuenta como producto echado en la tierra, y por eso no
        se apunta como salida.
      · **`ajuste`** — lo que sale al contar el almacén y no cuadra con el papel. Su `cantidad` es
        **la diferencia** (positiva si hay más de lo que dice el libro, negativa si hay menos), y
        lleva motivo obligatorio. Así el saldo se hace siempre igual —entradas − salidas − mermas +
        ajustes— y no hay dos formas de apuntar lo mismo.

    ## La cantidad y la unidad pueden no saberse

    Las dos columnas admiten vacío **a propósito**, y esto es una decisión del encargo, no un
    descuido: un albarán que llega sin la cantidad legible se apunta igual —el hecho de que llegó la
    mercancía es un hecho— y lo que se dice es que **no se sabe cuánto**. Poner un 0 ahí sería
    afirmar que no llegó nada, y el saldo del lote saldría mal para siempre. Mientras falte el dato,
    el almacén dice de ese lote que **no puede saber lo que queda**, que es la verdad.

    Y la unidad va siempre explícita: **la cantidad total no es la dosis por hectárea**, y los litros
    no son los kilos. Un movimiento en el que no esté claro en qué se mide no se puede restar de los
    demás, y el programa lo dice en vez de suponerlo.

    ## De dónde viene y quién lo hizo

    `origen_tipo` + `origen_id` dicen **a qué apunta** el movimiento: al albarán del que salió, al
    tratamiento o al abono que lo gastó, a la factura que lo sostiene, o a nada (`manual`, cuando lo
    apunta una persona porque pasó algo que no está en ningún papel). No es una clave foránea porque
    un mismo movimiento puede venir de cuatro tablas distintas, y una columna solo puede apuntar a
    una; la pertenencia a la finca se comprueba al apuntarlo, que es donde se puede explicar en
    castellano qué ha pasado. Se cuenta la verdad: cambiar esto por cuatro columnas casi siempre
    vacías sería más difícil de leer y de equivocarse.

    `usuario_id` es **quién lo apuntó**, que es la mitad de «quién lo hizo» que el programa puede
    saber: un movimiento lo firma quien lo teclea, no quien cargó el saco.

    ## Sin campaña propia, y es una decisión (03/10/2026)

    El libro **no cuelga del año** aunque el contrato pida conservar campaña, ejercicio y fecha como
    dimensiones distintas. Se probó con `campana_id` y se quitó por un motivo que se puede comprobar:
    el año del cuaderno (`routers/explotacion.py`) tiene tres listas escritas a mano —los apuntes, las
    tierras con su cultivo y «las demás cosas»— y una prueba que exige que **toda** tabla que cuelga de
    la campaña esté nombrada en una de ellas, para que no se cuente de más en silencio. Un movimiento
    de almacén no es un apunte del cuaderno, así que habría que nombrarlo en «las demás cosas», y esa
    lista es de otro ticket: colgarlo del año sin poder decirlo habría dejado dos pruebas en rojo.

    Y lo que hace falta de la campaña **sigue estando**, en el papel que la tiene de verdad: la compra,
    en su factura (`Factura.campana_id`), y el consumo, en el apunte del que sale la salida
    (`TratamientoFitosanitario.campana_id`, `RegistroFertilizacion.campana_id`). El libro se ordena y se
    consulta **por fechas**, que es lo que un movimiento tiene. Hay una prueba que fija esta decisión
    para que nadie la deshaga sin leer esto (`test_el_almacen_no_cuelga_del_ano`).

    ## Nada se borra

    `anulado` + `motivo_anulacion`, como en todo el cuaderno. Y hay un tercer camino que conviene
    entender: **un movimiento deja de contar si el apunte del que sale está anulado**. Si se anula un
    tratamiento, lo que gastó deja de contar sin tocar el libro, porque una anulación tiene que
    revertir el efecto sin borrar la historia (contrato §2). Eso se resuelve al leer
    (`servicios.un_movimiento_cuenta`), no reescribiendo la fila: así lo que se apuntó sigue ahí,
    con su fecha y su autor, y se ve que se anuló.
    """

    __tablename__ = "movimientos_de_existencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    articulo_id: Mapped[int] = mapped_column(ForeignKey("articulos.id"), index=True)
    # Obligatorio: todo lo que hay en el almacén está en algún lote (ver `Lote`).
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"), index=True)
    # entrada | salida | merma | ajuste. Ver `servicios.TIPOS_DE_MOVIMIENTO`.
    tipo: Mapped[str] = mapped_column(String(20), index=True)
    # El día en que pasó, que puede no saberse (un albarán sin fecha). Vacío es «no consta», y en el
    # libro sale sin fecha en vez de con la de hoy, que sería inventársela.
    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)
    cantidad: Mapped[float | None] = mapped_column(Float)
    unidad: Mapped[str | None] = mapped_column(String(10))
    # recepcion | tratamiento | fertilizacion | factura | manual (ver `servicios.ORIGENES_DE_UN_MOVIMIENTO`).
    origen_tipo: Mapped[str] = mapped_column(String(20), default="manual")
    origen_id: Mapped[int | None] = mapped_column(Integer)
    # Por qué. Obligatorio en un ajuste («ajustes de inventario piden motivo», contrato §4), en una
    # merma y en una entrada que no viene de ningún papel: en los tres casos no hay documento que
    # explique el movimiento, así que lo tiene que explicar quien lo apunta.
    motivo: Mapped[str | None] = mapped_column(Text)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    # La clave de reenvío de la petición que lo creó, igual que en la recepción: es lo que hace que
    # reenviar el mismo movimiento (el móvil sin cobertura, un botón pulsado dos veces) devuelva este
    # mismo movimiento en vez de apuntar dos. Va en su columna y **no** dentro del motivo: el motivo
    # es una frase del agricultor y no se toca para meter cosas de dentro del programa.
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))

    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        # **Una salida por apunte y lote, mientras siga viva.** Reenviar el mismo consumo (el móvil
        # sin cobertura, un botón pulsado dos veces) no descuenta el doble: lo comprueba el router
        # antes de apuntar nada.
        #
        # **Y no hay una restricción única que lo fuerce en la base, a propósito.** Se puso, y hubo
        # que quitarla: una restricción única no sabe de anulaciones, así que la salida anulada
        # —que sigue en la tabla, porque nada se borra— bloquearía volver a apuntar el mismo consumo
        # corregido, que es justo lo que hay que poder hacer. El reenvío del móvil, que es el caso
        # que de verdad hay que blindar, sigue protegido por la clave de reenvío de abajo.
        #
        # **La clave de reenvío es única solo entre las salidas vivas** (03/10/2026). Aquí estaba un
        # fallo de verdad: era un `UniqueConstraint` a secas, que no sabe de anulaciones, y el
        # agricultor que anulaba una salida y volvía a mandarla desde el móvil —que es lo que la cola
        # del móvil hace, reenviar con la MISMA clave— se encontraba un error de la base en la cara
        # (`UNIQUE constraint failed`) en vez de su apunte. Y por el otro lado, la búsqueda por clave
        # devolvía la salida anulada como si la hubiera apuntado, así que el agricultor veía «hecho»
        # sin que se hubiera apuntado nada: pérdida silenciosa.
        #
        # Un índice único **parcial** (`WHERE anulado = 0`) dice lo que de verdad se quiere: la misma
        # petición no se apunta dos veces **mientras siga viva**, y una anulada deja de estorbar. La
        # protección contra dos peticiones a la vez sigue siendo de la base, que es donde tiene que
        # estar. La tabla es nueva (no existe en la base del agricultor), así que se crea ya con el
        # índice bueno.
        Index(
            "uq_movimiento_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            # Las dos formas, porque el programa está escrito para poder correr sobre PostgreSQL
            # (ver la nota de PostGIS en `database.py`): con solo `sqlite_where`, en PostgreSQL el
            # índice sería **único a secas** y volvería el fallo de la salida anulada; y al revés,
            # con solo `postgresql_where`, en SQLite no habría ninguna protección. El `0` y el
            # `false` son la misma cosa dicha en el idioma de cada uno.
            sqlite_where=text("anulado = 0"),
            postgresql_where=text("anulado = false"),
        ),
    )


class Recepcion(Base):
    """El albarán que llega con la mercancía. **Es lo que mete existencias en el almacén.**

    ## Qué es y qué no es

    Es un papel: el albarán del proveedor, con su número y su fecha, y las líneas de lo que venía. Lo
    que hace es crear **lotes y entradas** (`LineaDeRecepcion` → `Lote` + `MovimientoDeExistencias`).
    Lo que **no** hace es nada económico: la factura es otro documento y otro momento, y aquí no se
    apunta el precio de nada ni se da nada por pagado.

    ## La factura llega después, y no vuelve a meter la mercancía (A15)

    `factura_id` engancha el albarán con la factura cuando esta aparece. Enganchar **no añade
    cantidad ninguna**: la mercancía entró una vez, con el albarán, y la factura solo dice de dónde
    salió y cuánto costó. Es el caso A15 del contrato, y es donde un programa de almacén se suele
    equivocar: contar la compra por la factura *y* por el albarán.

    Como el libro, **no lleva campaña propia**: la de la compra está en su factura. El porqué entero,
    con lo que se probó, está en `MovimientoDeExistencias`.

    ## Recibir dos veces lo mismo no puede duplicar nada

    Hay dos formas de reconocer que un albarán ya está dentro, y se usan las dos:

      · **`clave_de_reenvio`** — el identificador único de la petición. Lo manda la cola del móvil
        (`id_local`, ver `web/nucleo.js`) cuando el agricultor apunta sin cobertura y el envío se
        repite al volver a haber red. Reenviar la misma petición **devuelve el mismo albarán** en vez
        de crear otro (contrato §2: «reenviar el mismo comando devuelve su resultado»).
      · **El número del albarán con su proveedor y su año** — que es lo que identifica un papel de
        verdad. Un albarán sin número no se puede reconocer así, y entonces el programa **dice que no
        lo ha podido comprobar** en vez de decir que está todo bien.

    Cuando el número y el proveedor coinciden, la recepción devuelve la que ya había. **No se
    sobreescribe nada**: ni las líneas, ni los lotes, ni las cantidades. Si el agricultor se equivocó
    al teclearlo, se anula esa y se apunta la buena — que es la única forma de que quede el rastro.
    """

    __tablename__ = "recepciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)

    # La fecha del papel. Vacía es «el albarán no la trae o no se ha mirado»: no se inventa la de hoy.
    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)
    proveedor: Mapped[str | None] = mapped_column(String(200))
    proveedor_nif: Mapped[str | None] = mapped_column(String(20))
    numero_albaran: Mapped[str | None] = mapped_column(String(80), index=True)

    # La factura que llegó después (A15). Apunta a ella para poder contestar «¿y esto de qué compra
    # salió?» sin volver a meter la mercancía.
    factura_id: Mapped[int | None] = mapped_column(ForeignKey("facturas.id"), index=True)
    # La clave de reenvío de la petición que la creó. Única dentro de la finca: es lo que hace que
    # reenviar la misma petición devuelva este mismo albarán.
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    notas: Mapped[str | None] = mapped_column(Text)

    anulada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    lineas: Mapped[list["LineaDeRecepcion"]] = relationship(
        back_populates="recepcion", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # La clave de reenvío no se repite **dentro de una finca, entre los albaranes vivos**. En
        # SQLite los vacíos no chocan entre sí (un `NULL` no es igual a otro `NULL`), así que una
        # recepción sin clave —lo normal— no molesta a las demás. Con la clave puesta, la base misma
        # impide el duplicado aunque dos peticiones entren a la vez, que es la mitad que una
        # comprobación en Python no cubre.
        #
        # **Y solo entre los vivos** (`WHERE anulada = 0`), por el mismo fallo que en los movimientos
        # (ver `MovimientoDeExistencias`): con un `UniqueConstraint` a secas, un albarán anulado
        # seguía ocupando su clave y el agricultor no podía volver a apuntarlo desde el móvil —que
        # reenvía con la misma clave—: le salía un error de la base. Anular existe justo para poder
        # apuntar la buena después.
        Index(
            "uq_recepcion_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            # Las dos formas, por lo mismo que en `MovimientoDeExistencias`: el programa puede correr
            # sobre PostgreSQL, y allí un índice único sin condición volvería a bloquear el albarán
            # anulado. El `0` y el `false` son la misma cosa en cada idioma.
            sqlite_where=text("anulada = 0"),
            postgresql_where=text("anulada = false"),
        ),
        # Y el número del albarán se busca mucho: por él se reconoce un albarán repetido.
        Index("ix_recepcion_albaran", "explotacion_id", "proveedor", "numero_albaran"),
    )


class LineaDeRecepcion(Base):
    """Una línea del albarán: qué venía, cuánto, en qué lote y hasta cuándo vale.

    De aquí salen dos cosas: el **lote** (con su número, su caducidad y su envase) y la **entrada**
    del libro. La línea guarda a qué lote dio lugar (`lote_id`) para poder contestar «¿qué albarán
    trajo este lote?», que es la pregunta que se hace cuando hay que retirar una partida.

    **La cantidad y la unidad pueden no saberse** (un albarán con la casilla borrada, un producto que
    se cuenta a ojo): se apunta la línea igual, con lo que se sepa, y el almacén dirá de ese lote que
    no puede saber lo que queda. Un 0 ahí sería decir que no vino nada.

    `linea_factura_id` es el enganche **línea a línea** con la factura, para el caso en que la
    factura y el albarán no cuadren del todo (contrato §11: «factura y recepción pueden relacionarse
    parcialmente por líneas»). Es opcional: lo normal es enganchar los dos documentos enteros
    (`Recepcion.factura_id`).
    """

    __tablename__ = "lineas_de_recepcion"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    recepcion_id: Mapped[int] = mapped_column(ForeignKey("recepciones.id"), index=True)
    articulo_id: Mapped[int] = mapped_column(ForeignKey("articulos.id"), index=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"), index=True)

    # Lo que pone el papel, tal cual. Sirve para poder comparar la línea con la factura después y
    # para saber de qué hablaba el albarán si el artículo se enganchó mal.
    descripcion: Mapped[str | None] = mapped_column(String(200))
    cantidad: Mapped[float | None] = mapped_column(Float)
    unidad: Mapped[str | None] = mapped_column(String(10))
    # El enganche opcional con la línea de la factura (ver la decisión de arriba).
    linea_factura_id: Mapped[int | None] = mapped_column(ForeignKey("lineas_de_factura.id"))
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    recepcion: Mapped[Recepcion] = relationship(back_populates="lineas")


# --------------------------------------------------------------------------
# La identidad de la tierra: la versión del recinto (T05, 02/10/2026)
# --------------------------------------------------------------------------


class VersionDeRecinto(Base):
    """Qué era una tierra —su recinto— en una campaña, según una fuente, y cuándo se consultó.

    ## Por qué hay una tabla nueva en vez de más columnas en `parcelas`

    `Parcela` guarda **lo que la tierra es hoy**: su alias, su referencia, su forma y su
    superficie. Eso contesta a «¿cómo es mi tierra?», que es la pregunta de todos los días, y no
    se ha tocado.

    Lo que no se podía contestar es la pregunta del contrato (§2.1, E2): **qué era ese recinto en
    cada campaña y de dónde se supo** —del SIGPAC, del cuaderno de la Junta, de lo que dijo el
    agricultor o de una medición en el campo—. Un recinto cambia de forma, de uso y de superficie
    entre campañas, y con una sola fila en `parcelas` lo que cambia **borra** lo de antes. Esta
    tabla lo conserva: una fila por tierra, campaña y fuente.

    Y una cosa que **no** hace, que es la mitad del motivo de que exista: **no toca el alias, las
    notas ni el historial de la tierra**. El nombre que le puso el agricultor es suyo y no viene de
    ninguna fuente; importar un lote de recintos no puede renombrarle una tierra.

    ## Las tres áreas son tres magnitudes distintas, y ninguna se deduce de otra

      · `area_geometria_ha` — lo que mide **la forma que vino**, calculado con `geo.area_ha`. Es la
        única que el programa calcula, y sirve para comparar, no para declarar.
      · `area_sigpac_ha` — la superficie que **dice el SIGPAC** de ese recinto.
      · `area_declarada_ha` — las hectáreas que el agricultor **declara o trabaja**.

    **Las declaradas nunca se sustituyen por las calculadas** (contrato §2.1, palabra por palabra:
    «Nunca sustituir hectáreas declaradas por las calculadas»). Y un área que no se sabe se queda
    en `None` —«no lo sé»—, **jamás en 0**: es la regla que gobierna todo el proyecto
    (`docs/T02_VALORES_POR_DEFECTO.md`, hallazgo A7) y aquí se aplica tres veces.

    ## Una versión por tierra, campaña y fuente: la importación repetible

    La unicidad es `(explotación, tierra, campaña, fuente)`, que es la frase del contrato traducida
    a una restricción: «una versión por campaña y fuente». Volver a importar el mismo lote
    **actualiza** esa fila en vez de crear otra, y ahí está la importación repetible que pide T05.
    Con `clave` dentro de la unicidad, un recinto que primero llegara con la referencia a medias y
    después completa acabaría con dos filas, que es justo lo que no puede pasar.

    `clave` dice **con qué recinto hablaba esa importación** (la referencia completa
    `37-70-0-0-503-51-1`, o lo que sí vino cuando viene a medias, o la huella de la forma si no vino
    ninguna referencia). Sirve para dos cosas: reconocer el mismo lote repetido y avisar cuando un
    lote trae dos recintos distintos para la misma tierra.

    ## `poligono_valido`

    Una referencia a la que le falta el recinto **no es válida**: la versión se guarda igual (el
    dato vino así) pero queda marcada, y la pantalla puede decir cuál hay que completar. Es la
    misma regla del cuaderno de la Junta: en blanco es «no lo sé», y nunca se rellena solo.

    ## Lo que no se sabe se queda en blanco

    `geometria` vacía es un recinto **sin forma**, que existe de verdad (una tierra apuntada a mano,
    un recinto del papel que nadie ha dibujado). Entra igual en la tabla, se ve en la lista y se
    cuenta en el grupo «sin forma»; lo que no se hace es dibujarle un polígono inventado.
    """

    __tablename__ = "versiones_de_recinto"
    __table_args__ = (
        # Una versión por tierra, campaña y fuente (el contrato, §2.1, palabra por palabra). Es lo
        # que hace que importar dos veces el mismo lote no duplique nada: la segunda vez se reconoce
        # la fila y, si nada ha cambiado, no se escribe.
        UniqueConstraint(
            "explotacion_id",
            "parcela_id",
            "campana_id",
            "fuente",
            name="uq_version_de_recinto",
        ),
        # Las versiones se buscan casi siempre por tierra y campaña (la ficha de una tierra, la
        # comparación entre dos campañas).
        Index("ix_version_recinto_tierra", "parcela_id", "campana_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    parcela_id: Mapped[int] = mapped_column(ForeignKey("parcelas.id"), index=True)
    campana_id: Mapped[int] = mapped_column(ForeignKey("campanas.id"), index=True)
    # sigpac | cuaderno_de_la_junta | agricultor | medicion_en_campo (`versiones_de_recinto.FUENTES`).
    # Es lo que permite decir «esto lo dice el SIGPAC» y «esto lo dijo el agricultor» sin mezclarlos.
    fuente: Mapped[str] = mapped_column(String(30))
    # Cuándo se consultó esa fuente. Vacío es «no se ha dicho cuándo»: el programa **no** pone la
    # fecha de hoy, porque eso afirmaría una consulta que quizá se hizo en marzo.
    fecha_consulta: Mapped[dt.date | None] = mapped_column(Date)

    # La clave del recinto dentro de la tierra (la referencia completa, o lo que vino).
    clave: Mapped[str] = mapped_column(String(80))
    # La referencia completa como texto, **solo cuando está completa**. Vacía si le falta algo.
    referencia: Mapped[str | None] = mapped_column(String(80))
    # La referencia, tal y como vino: la provincia y el municipio como los escriba la fuente (el
    # SIGPAC manda sus códigos, el cuaderno de la Junta el nombre del pueblo) y los números.
    provincia: Mapped[str | None] = mapped_column(String(60))
    municipio: Mapped[str | None] = mapped_column(String(120))
    agregado: Mapped[int | None] = mapped_column(Integer)
    zona: Mapped[int | None] = mapped_column(Integer)
    poligono: Mapped[int | None] = mapped_column(Integer)
    numero_parcela: Mapped[int | None] = mapped_column(Integer)
    numero_recinto: Mapped[int | None] = mapped_column(Integer)
    # ¿Están los siete números? Una referencia sin el recinto no identifica a nadie.
    poligono_valido: Mapped[bool] = mapped_column(Boolean, default=False)

    # WKT, como en `Parcela.geometria` (ver la nota sobre PostGIS en `database.py`).
    geometria: Mapped[str | None] = mapped_column(Text)
    # Las tres áreas, y ninguna se calcula a partir de otra (ver la cabecera).
    area_geometria_ha: Mapped[float | None] = mapped_column(Float)
    area_sigpac_ha: Mapped[float | None] = mapped_column(Float)
    area_declarada_ha: Mapped[float | None] = mapped_column(Float)
    uso_sigpac: Mapped[str | None] = mapped_column(String(80))
    pendiente_pct: Mapped[float | None] = mapped_column(Float)

    # sin_revisar | revisado | con_dudas (`versiones_de_recinto.ESTADOS_DE_REVISION`). Empieza en
    # «sin revisar»: una importación no es una revisión, y decir «revisado» sin que nadie lo haya
    # mirado sería justo el defecto que persigue `docs/T02_VALORES_POR_DEFECTO.md`.
    estado_revision: Mapped[str] = mapped_column(String(20), default="sin_revisar")
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


# --------------------------------------------------------------------------
# La semilla y la siembra (T10, 03/10/2026)
# --------------------------------------------------------------------------


class Semilla(Base):
    """Lo que pone la etiqueta de una semilla. **La semilla es un artículo del almacén.**

    ## Por qué esto no es un segundo almacén

    Una semilla **no se guarda dos veces**: lo que se compra, lo que entra en la nave y lo que sale
    de ella son las mismas filas que las de cualquier otro insumo (`articulos`, `lotes`,
    `movimientos_de_existencias`, `recepciones`), y la semilla sale de allí por la misma puerta que
    todo lo demás (`POST /api/almacen/salidas`). Lo único que añade esta tabla es **lo que la
    etiqueta dice y el almacén no guarda**: la especie, la variedad, la casa, la dosis que recomienda
    el fabricante, el poder germinativo y la pureza.

    Por eso cuelga de un `articulo_id` y no tiene nombre propio de producto: el nombre del artículo
    es el que el agricultor reconoce en la nave («veza común Villalobos»), y aquí está lo que viene
    impreso en el papel.

    ## Lo que no se sabe se queda en blanco, y hay dos cosas que casi nunca vienen

    **El poder germinativo y la pureza no vienen en todas las etiquetas.** Cuando no vienen, se
    quedan en `None` —«no lo dice el papel»— y la pantalla lo dice con esas palabras. Un `0` ahí
    sería afirmar que la semilla no germina, que es lo contrario de lo que pasa.

    Y lo mismo con `tratada`, que tiene **tres** respuestas y no dos: `True` (viene tratada),
    `False` (el agricultor ha mirado el papel y no lo viene) y `None` (no lo ha mirado o el papel no
    lo dice). Es la regla del proyecto (`docs/T02_VALORES_POR_DEFECTO.md`): «no lo sé» no es «no».

    ## De dónde salieron los datos

    `leida_de` dice cómo se rellenaron —`mano`, `foto`, `pdf`, `escaneo` o `texto`— y
    `idioma_del_lector` con qué se leyó la foto. No es un adorno: si dentro de un año el poder
    germinativo de una etiqueta está mal, lo primero que hay que saber es si lo escribió una persona
    o lo leyó un programa.

    **Lo que esta tabla NO es: una semilla sin confirmar.** Una fila de aquí solo existe cuando el
    agricultor ha dicho que sí a lo que se le enseñó. La lectura de una foto **no escribe nada**
    (`POST /api/semillas/etiqueta`), y por eso no hay ninguna columna de «pendiente de confirmar»:
    lo que no se ha confirmado no está.
    """

    __tablename__ = "semillas"
    __table_args__ = (
        # Un artículo, una etiqueta. Sin esto, el mismo saco podría tener dos fichas de semilla con
        # especies distintas y no habría forma de saber cuál es la buena.
        UniqueConstraint("explotacion_id", "articulo_id", name="uq_semilla_de_un_articulo"),
        Index("ix_semilla_especie", "explotacion_id", "especie"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    articulo_id: Mapped[int] = mapped_column(ForeignKey("articulos.id"), index=True)

    # Lo que identifica a la semilla en el campo. Todo puede faltar: una semilla guardada de un año
    # para otro puede haber perdido el papel, y eso no impide apuntar que se sembró.
    especie: Mapped[str | None] = mapped_column(String(120))
    variedad: Mapped[str | None] = mapped_column(String(120))
    casa_comercial: Mapped[str | None] = mapped_column(String(120))
    proveedor: Mapped[str | None] = mapped_column(String(200))
    # El número que va impreso en el envase (el del proveedor), que es con el que se reclama una
    # partida. **No sustituye al lote del almacén** (`Lote.numero_lote`): uno es lo que dice el
    # papel y el otro es de dónde sale de verdad lo que se siembra, y pueden no coincidir.
    numero_lote_proveedor: Mapped[str | None] = mapped_column(String(80))

    # La dosis que recomienda el fabricante, **con su unidad**. Es un dato de la etiqueta y no una
    # orden: quien decide cuánto se siembra es el agricultor, y lo que siembra de verdad va en
    # `Siembra.dosis_por_ha`. Confundir las dos es la confusión de diez veces que persigue el T10.
    dosis_recomendada_por_ha: Mapped[float | None] = mapped_column(Float)
    unidad_dosis: Mapped[str | None] = mapped_column(String(20))

    fecha_envasado: Mapped[dt.date | None] = mapped_column(Date)
    # Vacío es «no lo he mirado», que **no** es «no caduca» (la misma decisión que en `Lote`).
    fecha_caducidad: Mapped[dt.date | None] = mapped_column(Date)

    # Los dos números del papel que a veces no vienen. Vacío = «el papel no lo dice».
    poder_germinativo_pct: Mapped[float | None] = mapped_column(Float)
    pureza_pct: Mapped[float | None] = mapped_column(Float)
    # Tres estados: sí viene tratada, no viene, y no se sabe. Ver la cabecera.
    tratada: Mapped[bool | None] = mapped_column(Boolean)

    # La foto de la etiqueta: en la base de datos solo la referencia (nombre, ruta relativa, tipo y
    # tamaño), como en todo lo que sube el agricultor (`app/adjuntos.py` y AGENTS.md §3.10).
    etiqueta_nombre: Mapped[str | None] = mapped_column(String(200))
    etiqueta_ruta: Mapped[str | None] = mapped_column(String(400))
    etiqueta_tipo: Mapped[str | None] = mapped_column(String(100))
    etiqueta_bytes: Mapped[int | None] = mapped_column(Integer)

    # mano | foto | pdf | escaneo | texto (ver `semillas.CAMINOS_DE_LECTURA`). Por defecto «mano»:
    # una ficha que nadie ha leído de un papel la ha escrito una persona.
    leida_de: Mapped[str] = mapped_column(String(20), default="mano")
    idioma_del_lector: Mapped[str | None] = mapped_column(String(20))

    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    articulo: Mapped[Articulo] = relationship()


class Siembra(Base):
    """«En esta tierra sembré esta semilla», con la dosis por hectárea **y** la cantidad total.

    ## Las dos cifras no son la misma, y aquí se ven las dos

    `dosis_por_ha` son los kilos (o las unidades) de cada hectárea, y `cantidad_total` es lo que se
    gastó en la tierra entera. Confundirlas es un error de diez veces, así que van en **columnas
    distintas, cada una con su unidad**, y la pantalla las enseña con su nombre. Si el agricultor
    solo dice una de las dos y hay superficie, la otra se calcula —`dosis × hectáreas = total`— y
    **se dice que se ha calculado** (`cantidad_total_calculada` / `dosis_calculada`): un número
    calculado se puede revisar; un número inventado, no. Si no se puede calcular, se queda vacío y
    se pide: **nunca se pone un cero**.

    ## La semilla que se siembra sale del almacén, y sale por la puerta de siempre

    Lo que se gasta se descuenta con `POST /api/almacen/salidas`, con `apunte_tipo="siembra"` y el
    identificador de esta fila. **No hay una segunda forma de restar producto**: el libro del
    almacén sigue cuadrando, y `lote_id` dice de qué envase salió, que es lo que contesta «si el
    fabricante avisa de una partida, ¿dónde se fue?».

    Y de ahí sale lo mejor de haberlo hecho así: **anular una siembra devuelve lo que salió sin
    tocar el libro**. La salida sigue apuntada con su fecha y su autor, y deja de contar porque
    `servicios.estado_de_los_origenes` mira si la siembra está anulada (igual que un tratamiento
    anulado). Nada se borra y no quedan dos descuentos.

    ## Sin campaña propia, y es la misma decisión que en el libro del almacén

    Esta tabla **no cuelga del año** (`campana_id`) aunque una siembra pase en una campaña. El
    motivo está escrito entero en `MovimientoDeExistencias`: el año del cuaderno tiene tres listas
    escritas a mano en `routers/explotacion.py` y una prueba que exige que toda tabla que cuelgue
    del año esté nombrada en una de ellas. Una siembra se busca por **su fecha**, que es lo que un
    trabajo tiene, y la fecha ya está aquí.
    """

    __tablename__ = "siembras"
    __table_args__ = (
        # Reenviar la misma siembra (el móvil sin cobertura, un botón pulsado dos veces) no puede
        # descontar dos veces del almacén. Es la misma protección que en los movimientos y las
        # recepciones, y por el mismo motivo: **solo entre las vivas**, porque una siembra anulada
        # tiene que dejar volver a apuntarla (anular existe justo para eso).
        Index(
            "uq_siembra_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("anulada = 0"),
            postgresql_where=text("anulada = false"),
        ),
        Index("ix_siembra_tierra", "explotacion_id", "parcela_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    # La tierra donde se sembró. Obligatoria: esto es «en esta tierra sembré esta semilla», y sin la
    # tierra no hay siembra (es lo que pide el contrato en su taxonomía de trabajos).
    parcela_id: Mapped[int] = mapped_column(ForeignKey("parcelas.id"), index=True)
    # La semilla, que a su vez es el artículo del almacén (ver `Semilla`).
    semilla_id: Mapped[int] = mapped_column(ForeignKey("semillas.id"), index=True)
    # De qué envase salió. Vacío es «no se sabe de qué lote»: entonces no se puede descontar del
    # almacén, y eso se dice en vez de restarlo de un envase cualquiera.
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes.id"), index=True)

    # La fecha del trabajo. Vacía es «no consta», y no se inventa la de hoy.
    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)

    superficie_ha: Mapped[float | None] = mapped_column(Float)
    dosis_por_ha: Mapped[float | None] = mapped_column(Float)
    unidad_dosis: Mapped[str | None] = mapped_column(String(20))
    cantidad_total: Mapped[float | None] = mapped_column(Float)
    # En qué se cuenta la cantidad total, que puede ser la misma familia que la dosis o no («2.000
    # unidades» de una semilla que se dosifica en kg/ha es un dato, no un error de unidades).
    unidad_cantidad: Mapped[str | None] = mapped_column(String(10))

    # Los dos «esto lo ha calculado el programa» (ver la cabecera). Van en la fila y no en un
    # comentario porque la pantalla tiene que poder decirlo al agricultor.
    dosis_calculada: Mapped[bool] = mapped_column(Boolean, default=False)
    cantidad_total_calculada: Mapped[bool] = mapped_column(Boolean, default=False)

    notas: Mapped[str | None] = mapped_column(Text)
    # La clave de reenvío de la petición que la creó (ver el índice de arriba).
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))

    anulada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


# --------------------------------------------------------------------------
# Los contactos (T11, 03/10/2026)
# --------------------------------------------------------------------------
#
# **Qué problema resuelven, con el caso de verdad.** «Cooperativa Agrícola de Peñaranda» está escrito
# a mano en doce sitios del cuaderno: el proveedor de cuatro facturas, el de dos albaranes, el de un
# producto del catálogo, el comprador de tres ventas y el laboratorio de dos análisis. Cada vez que
# llega un papel, el agricultor vuelve a teclearla. Y si un día se equivoca y escribe «Cooperativa
# Agricola de Peñaranda» sin la tilde, el programa cree que son dos.
#
# La respuesta del T11 es **una ficha de contacto** y **un enlace desde donde está escrito el nombre**.
# Tres decisiones que hay que entender antes de tocar esto:
#
#  1. **El texto escrito NO se toca, nunca.** El nombre que el agricultor tecleó en una factura es
#     suyo y se sigue viendo en esa factura tal cual. El enlace **añade** una ficha al lado, no
#     sustituye ni reescribe nada: por eso `EnlaceDeContacto` guarda también `nombre_de_entonces`, que
#     es lo que decía el papel el día que se enlazó. Así el programa puede decir «este enlace es de
#     antes: ahora ahí pone otra cosa», que es información y no un error.
#  2. **El enlace vive en su propia tabla y no en una columna de cada documento.** Habría sido más
#     corto poner un `contacto_id` en cada una de las ocho tablas, pero entonces **el enlace no se
#     podría quitar sin escribir en un documento histórico**, y la migración no sería reversible: para
#     volver atrás habría que acordarse de qué filas se tocaron. Aquí, deshacer la migración es
#     borrar lo que la migración creó, y los documentos no se han tocado ni una vez. Es el mismo
#     patrón que `Firma` (`entidad` + `entidad_id`): una fila que apunta a otra por su nombre de tabla
#     y su identificador.
#  3. **Dos contactos con el mismo nombre PUEDEN existir.** No hay ninguna restricción de unicidad
#     sobre el nombre, y eso es a propósito: el contrato pide, en E5, que «dos contactos homónimos no
#     se mezclen». Dos hermanos pueden llamarse igual, y el programa tiene que poder apuntar a cada
#     uno. Lo que sí es único es **el enlace**: un mismo texto escrito no puede estar enlazado con dos
#     contactos a la vez, porque eso serían dos verdades sobre el mismo papel.


class Contacto(Base):
    """Una persona o una empresa con la que la finca trata: el proveedor, el comprador, el técnico.

    Los datos son los que el agricultor tiene en el papel o en la guía de teléfonos, y **todos menos
    el nombre pueden faltar**. Un contacto sin teléfono es un contacto: lo que no puede pasar es que
    el programa se invente un número, un correo o un NIF para rellenar un hueco.

    Y el nombre **se guarda como él lo escribe**. No se normaliza, no se pone en mayúsculas y no se le
    quitan las tildes: en la comparación de nombres (`app/contactos.py`) sí se quitan, pero eso es
    para decidir si dos textos se parecen, no para cambiar el suyo.
    """

    __tablename__ = "contactos"
    __table_args__ = (
        # Buscar por nombre es la mitad del uso de esta pantalla. Va con la finca por delante, como
        # todas: sin ella, la consulta recorrería los contactos de todo el mundo.
        Index("ix_contacto_nombre", "explotacion_id", "nombre"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(200))

    # **Tres estados, y el que falta no afirma nada.** `None` es «no lo sé», y no es lo mismo que
    # «es una persona»: hay nombres que no dicen si detrás hay una persona o una sociedad («Hermanos
    # Pérez», «El Cortijo»), y convertirlo en `False` sería afirmar algo que nadie ha mirado. Es la
    # misma regla del T02 y por el mismo motivo.
    es_empresa: Mapped[bool | None] = mapped_column(Boolean, default=None)

    nif: Mapped[str | None] = mapped_column(String(20))
    telefono: Mapped[str | None] = mapped_column(String(40))
    correo: Mapped[str | None] = mapped_column(String(200))
    direccion: Mapped[str | None] = mapped_column(String(200))
    localidad: Mapped[str | None] = mapped_column(String(120))
    notas: Mapped[str | None] = mapped_column(Text)

    # «a_mano» o «migracion». **Es lo que hace que la migración se pueda deshacer sin adivinar**:
    # deshacer borra lo que creó la migración y **deja lo que el agricultor ha tocado después**, con
    # su motivo escrito en la respuesta. Si no estuviera esta columna, volver atrás borraría trabajo
    # suyo, que es justo lo que no se puede hacer.
    origen: Mapped[str] = mapped_column(String(20), default="a_mano")
    # **Y esto es la otra mitad de la misma promesa.** Una ficha que creó la migración y que el
    # agricultor ha corregido después (le ha puesto el teléfono, le ha quitado un papel) **ya no es
    # de la migración**: es suya, y deshacer no puede llevársela. Se marca al corregirla o al tocarle
    # los papeles a mano, y deshacer la respeta y lo dice en la respuesta.
    editado_a_mano: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class PapelDeUnContacto(Base):
    """Qué hace esa persona o esa empresa con esta finca. **Puede hacer varios a la vez.**

    La misma cooperativa te vende la semilla, te compra el trigo y te lleva el remolque. Con una
    columna `papel` en el contacto habría que elegir uno, y elegir uno es perder los otros: por eso
    cada papel es una fila. Hay una restricción de unicidad por contacto y papel, para que el mismo
    papel no se apunte dos veces.
    """

    __tablename__ = "papeles_de_un_contacto"
    __table_args__ = (
        UniqueConstraint("contacto_id", "papel", name="uq_papel_del_contacto"),
        Index("ix_papel_contacto", "explotacion_id", "papel"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    contacto_id: Mapped[int] = mapped_column(ForeignKey("contactos.id"), index=True)
    # Las claves del catálogo de `app/contactos.py` (`PAPELES`). Es texto y no un enumerado de la base
    # a propósito: un papel nuevo no puede obligar a migrar el esquema.
    papel: Mapped[str] = mapped_column(String(40))
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class EnlaceDeContacto(Base):
    """**Un nombre escrito en el cuaderno, enlazado con su ficha de contacto.**

    Esta fila no guarda ningún dato del cuaderno: solo dice «estos ocho caracteres de aquí son esta
    persona». El texto sigue donde estaba y sigue diciendo lo mismo, que es la regla del ticket («no
    se borra ni se reescribe ni un texto histórico»).

    Tres columnas que necesitan explicación:

      · **`tabla` y `campo`** — dónde está el nombre. Salen de una lista cerrada (`contactos.ENLACES`
        en `app/contactos.py`), y **una tabla que no esté en esa lista no puede tener un enlace**:
        por aquí entra un dato del navegador, y sin la lista un nombre de tabla inventado acabaría en
        una consulta. Hay una prueba que lo comprueba.
      · **`registro_id`** — qué fila. No lleva clave ajena porque apunta a ocho tablas distintas; es
        el mismo compromiso que `Firma.entidad_id`. Cuando se borra un documento (el agricultor puede
        borrar una factura), el enlace se queda huérfano, y por eso **al leer los vínculos se comprueba
        que la fila siga existiendo**: lo que ya no está no se cuenta ni se enseña.
      · **`nombre_de_entonces`** — lo que decía el papel el día del enlace. Es lo que permite decir
        «ojo, ahí pone otra cosa desde entonces» sin haber tocado el texto nunca.
    """

    __tablename__ = "enlaces_de_contacto"
    __table_args__ = (
        # **Un texto escrito, un solo dueño.** Si el mismo proveedor de la misma factura pudiera estar
        # enlazado con dos contactos, el programa tendría dos verdades sobre el mismo papel y ninguna
        # forma de saber cuál vale.
        UniqueConstraint(
            "explotacion_id", "tabla", "campo", "registro_id", name="uq_enlace_de_un_texto"
        ),
        Index("ix_enlace_contacto", "explotacion_id", "contacto_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    contacto_id: Mapped[int] = mapped_column(ForeignKey("contactos.id"), index=True)

    tabla: Mapped[str] = mapped_column(String(60), index=True)
    campo: Mapped[str] = mapped_column(String(60))
    registro_id: Mapped[int] = mapped_column(Integer)

    nombre_de_entonces: Mapped[str | None] = mapped_column(String(200))
    # «a_mano» o «migracion»: por dónde entró este enlace. Es lo que permite deshacer la migración
    # sin tocar los enlaces que el agricultor ha hecho él.
    origen: Mapped[str] = mapped_column(String(20), default="a_mano")
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

# --------------------------------------------------------------------------
# Las cuentas de la explotación (T13, E7, 05/10/2026)
# --------------------------------------------------------------------------
#
# **CINCO REGISTROS QUE NO SON LO MISMO, Y POR QUÉ ESTÁN EN CINCO TABLAS.** El encargo lo exige con
# estas palabras: «Gasto, inversión, factura, pago y movimiento bancario son registros distintos. No
# los mezcles en una tabla ni en un nombre». Aquí eso se cumple con cinco tablas y no con una columna
# `clase`, y el motivo es que cada uno se equivoca por su cuenta:
#
#   · **El gasto** es lo que se ha consumido: el gasóleo, el abono, la reparación. Es **lo único que
#     entra en el margen de la campaña** (`gastos.APORTA_AL_COSTE`).
#   · **La inversión** es lo que se compra para durar (el tractor, la sembradora, la nave). El
#     contrato lo dice literal en S13: «Compra de activo no equivale automáticamente a gasto completo
#     del cultivo». Lo que de ella va a cada campaña lo dice el agricultor con un reparto
#     (`repartos_de_coste`) y, mientras no lo diga, **se queda sin asignar y se ve**.
#   · **La factura** es el papel del proveedor. Ya existe en este programa (`facturas`) y **no se
#     duplica**: el gasto la *apunta* con `factura_id`. Si la factura aportara coste por su cuenta,
#     cada compra contaría dos veces.
#   · **El pago** es el dinero que sale, y puede ser parcial y agrupado: por eso **no cuelga de un
#     gasto** y vive en su tabla, con las aplicaciones aparte (`aplicaciones_de_pago`).
#   · **El movimiento bancario** es lo que pone el extracto, y es del ticket siguiente (T20). Aquí no
#     hay tabla para él a propósito: el traspaso entre cuentas propias se calcula
#     (`gastos.traspaso_entre_cuentas_propias`) y **no se guarda todavía**, y eso se dice en la
#     pantalla en vez de disimularse.
#
# **Y LA PROTECCIÓN QUE MANDA SOBRE TODAS:** el dinero no se cuenta dos veces. Se consigue con dos
# decisiones que están en el esquema y no en un comentario:
#
#   1. **Conciliar un pago no crea un gasto.** La conciliación escribe en `aplicaciones_de_pago`, que
#      solo dice «este dinero va contra este gasto». No hay ninguna línea, ni en el modelo ni en el
#      router, que cree un gasto a partir de un pago.
#   2. **Un pago no puede tener aplicado más de su importe**, y un gasto no puede tener aplicado más
#      de lo que debe. Lo comprueba el router con la frase del agricultor y hay pruebas que lo fijan.
#
# **Un importe que no consta es `None` en las cinco columnas de dinero** (`importe`, `base_imponible`,
# `cuota_iva`, `valor_residual`…), nunca `0.00`: es la regla de la casa entera y en un cuaderno de
# cuentas es la diferencia entre «esta reparación no costó nada» y «no sé lo que costó».


class Gasto(Base):
    """Lo que se ha consumido: el gasóleo, el abono, la reparación, la cuota del seguro.

    Es **el único registro de este bloque que entra en el margen de la campaña**, y por eso es el que
    más cuidado tiene: el importe puede no constar (`importe` en `None`), el total que el agricultor
    leyó en el papel **manda** sobre la suma de base y cuota, y el gasto dice a qué tierra o cultivo
    va (`parcela_id`, `cultivo`) o se reparte después.

    `averia_id` es de donde sale **el coste de las averías**, que el T14 dejó declarado como de este
    ticket: la reparación es **un gasto** —con su factura y su pago, como cualquier otra— que además
    dice de qué avería salió. No se guarda un importe dentro de la avería porque un importe en dos
    sitios acaba diciendo dos cosas el día que alguien corrija una de las dos.
    """

    __tablename__ = "gastos"
    __table_args__ = (
        # Reenviar el mismo gasto (el móvil sin cobertura, un botón pulsado dos veces) devuelve el
        # mismo. Parcial, por lo mismo que en las entregas: un gasto anulado deja libre su clave.
        Index(
            "uq_gasto_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("anulado = 0"),
            postgresql_where=text("anulado = false"),
        ),
        Index("ix_gasto_fecha", "explotacion_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"), index=True)

    # El día de la compra o del consumo. Vacío es «no consta» (una reparación apuntada de memoria),
    # y el vencimiento vacío quiere decir que nadie ha pactado un plazo: poner la fecha del gasto
    # sería inventarse uno.
    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)
    vencimiento: Mapped[dt.date | None] = mapped_column(Date)

    # Qué fue, en palabras del agricultor («abono del trigo», «reparación del remolque»). Es
    # obligatorio en el esquema y no en la columna: una columna obligatoria no se puede añadir a una
    # tabla que ya existe, y aquí la puerta es el esquema.
    concepto: Mapped[str | None] = mapped_column(String(200))
    # Nuestra categoría (`gastos.CATEGORIAS_DE_GASTO`). Agrupa y permite leer una lista de un
    # vistazo, y **no decide nada**: no dice de qué máquina es ni si es una inversión.
    categoria: Mapped[str] = mapped_column(String(40), default="otro", index=True)

    proveedor: Mapped[str | None] = mapped_column(String(200))
    proveedor_nif: Mapped[str | None] = mapped_column(String(20))
    contacto_id: Mapped[int | None] = mapped_column(ForeignKey("contactos.id"), index=True)

    # El justificante: la factura de compra que ya existe en el programa. Vacío es «este gasto no
    # tiene factura» (un ticket de gasóleo), y eso no lo hace menos gasto.
    factura_id: Mapped[int | None] = mapped_column(ForeignKey("facturas.id"), index=True)
    # De qué máquina es y de qué avería salió, si se sabe. Es lo que hace que el coste de las
    # averías y el de las máquinas salgan de las cuentas de verdad y no de un número escrito aparte.
    maquina_id: Mapped[int | None] = mapped_column(ForeignKey("maquinas.id"), index=True)
    averia_id: Mapped[int | None] = mapped_column(ForeignKey("averias_de_maquina.id"), index=True)

    # **El coste directo**: cuando el gasto ya dice de qué tierra o de qué cultivo es. Lo que no se
    # sabe a qué va se apunta sin estos dos campos y se reparte después (o se queda sin asignar).
    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"), index=True)
    cultivo: Mapped[str | None] = mapped_column(String(120))

    # Las cuentas del papel, **cada una puede faltar** y ninguna se convierte en cero. El importe que
    # manda es `importe`: si el agricultor leyó «121,00 €» en el papel, ese es el total aunque
    # `base + cuota` dé 120,99 por un redondeo del proveedor. Ver `gastos.importe_de_un_gasto`.
    base_imponible: Mapped[Decimal | None] = mapped_column(Dinero)
    cuota_iva: Mapped[Decimal | None] = mapped_column(Dinero)
    tipo_iva_pct: Mapped[float | None] = mapped_column(Float)
    # **`None` es «no sé lo que costó», y es un estado de verdad** (`gastos.SIN_IMPORTE`): el
    # agricultor sabe que pagó la reparación y no se acuerda de cuánto, y el contrato dice que «un
    # apunte real con datos incompletos se guarda con pendientes». Un `0.00` aquí diría que salió
    # gratis y el margen del año saldría mejor de lo que es.
    importe: Mapped[Decimal | None] = mapped_column(Dinero)

    notas: Mapped[str | None] = mapped_column(Text)
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class InversionDeLaFinca(Base):
    """Un bien que se compra para durar: el tractor, la sembradora, la nave, el remolque.

    **No es un gasto, y ése es el motivo de que tenga su tabla.** El contrato lo dice en S13 y el
    encargo lo repite: comprar un activo **no** es un gasto completo del cultivo. Si el tractor de
    60.000 € entrara como gasto del año, el margen de esa campaña diría que se perdió dinero y los
    tres años siguientes que fue gratis, y las dos cosas serían mentira.

    **Lo que NO tiene esta tabla, y es una decisión:** no hay `vida_util` ni `cuota_de_amortizacion`.
    No hay en el programa ninguna tabla oficial de años de vida útil por tipo de bien, y este
    proyecto tiene escrito lo que se hace cuando falta una fuente: se declara. Por eso la parte que
    va a cada campaña **la dice el agricultor** con un reparto a la campaña, y mientras no la diga se
    queda sin asignar. El día que haya fuente, se añade la columna y su prueba.
    """

    __tablename__ = "inversiones_de_la_finca"
    __table_args__ = (
        Index(
            "uq_inversion_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("anulada = 0"),
            postgresql_where=text("anulada = false"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"), index=True)

    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)
    concepto: Mapped[str | None] = mapped_column(String(200))
    # Nuestra (`gastos.CATEGORIAS_DE_INVERSION`): maquinaria, apero, instalación, vehículo, terreno.
    categoria: Mapped[str] = mapped_column(String(40), default="otro", index=True)

    proveedor: Mapped[str | None] = mapped_column(String(200))
    proveedor_nif: Mapped[str | None] = mapped_column(String(20))
    contacto_id: Mapped[int | None] = mapped_column(ForeignKey("contactos.id"), index=True)
    factura_id: Mapped[int | None] = mapped_column(ForeignKey("facturas.id"), index=True)
    # Si el bien es una máquina de la lista de maquinaria, aquí se enlaza: así el tractor es uno solo
    # en las tres pantallas (la inversión, la máquina y el gasto de su reparación).
    maquina_id: Mapped[int | None] = mapped_column(ForeignKey("maquinas.id"), index=True)
    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"), index=True)

    # **`None` es «no sé lo que costó»**, igual que en un gasto, y no un cero.
    importe: Mapped[Decimal | None] = mapped_column(Dinero)
    # Lo que se espera sacar por él al final. Casi nunca se sabe, y vacío es «no lo sé».
    valor_residual: Mapped[Decimal | None] = mapped_column(Dinero)

    notas: Mapped[str | None] = mapped_column(Text)
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    anulada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class RepartoDeCoste(Base):
    """La parte de un gasto o de una inversión que se lleva a una tierra, un cultivo o una máquina.

    **Por qué esto es una tabla y no unas columnas del gasto.** Porque un gasto se reparte entre
    varias cosas a la vez (el seguro de la finca entre sus 12 tierras) y porque **el método con el
    que se repartió tiene que quedar escrito**: «lo repartió el programa por hectáreas» y «lo repartió
    el agricultor a mano» son dos cosas de fiabilidad distinta, y dentro de un año lo único que
    explicará de dónde salió esa cifra es esta columna.

    **Dos claves ajenas y no una polimórfica**: `gasto_id` o `inversion_id`, y exactamente una de las
    dos. Con `origen_tipo`/`origen_id` la cuenta de «qué usa este gasto» no encontraría las filas
    (`correcciones.tablas_que_apuntan_a` busca por el nombre de la columna), y borrar un gasto dejaría
    sus repartos apuntando al vacío.

    **`sin_asignar` es un destino de verdad**, y es la mitad del ticket: lo que no se sabe a qué va
    **no se reparte a medias**, se queda aquí entero y se dice. Un coste sin asignar **sigue siendo un
    coste conocido**: no desaparece de las cuentas, solo no está atribuido a nadie.
    """

    __tablename__ = "repartos_de_coste"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)

    # De dónde sale este trozo: un gasto o una inversión, nunca los dos y nunca ninguno.
    gasto_id: Mapped[int | None] = mapped_column(ForeignKey("gastos.id"), index=True)
    inversion_id: Mapped[int | None] = mapped_column(ForeignKey("inversiones_de_la_finca.id"), index=True)

    # A dónde va: `gastos.DESTINOS_DE_UN_REPARTO` (tierra, cultivo, maquina, campana, sin_asignar).
    destino_tipo: Mapped[str] = mapped_column(String(20), index=True)
    # El nombre o el identificador como texto. Se guarda **el texto** para que el reparto histórico no
    # cambie si mañana se renombra la tierra, y `parcela_id` aparte para poder sumar por tierra.
    destino: Mapped[str | None] = mapped_column(String(120))
    parcela_id: Mapped[int | None] = mapped_column(ForeignKey("parcelas.id"), index=True)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"), index=True)
    maquina_id: Mapped[int | None] = mapped_column(ForeignKey("maquinas.id"), index=True)

    # El trozo. **Ya redondeado al céntimo y sumando exacto** con los demás trozos del mismo gasto:
    # el céntimo del redondeo se le pone a uno y se dice a cuál (`gastos.reparto_por_peso`).
    importe: Mapped[Decimal | None] = mapped_column(Dinero)
    # area | horas | consumo | manual (`gastos.METODOS_DE_REPARTO`). **Se guarda: dentro de un año es
    # lo único que explica de dónde salió esta cifra.**
    metodo: Mapped[str] = mapped_column(String(20), default="manual")
    # **Por qué este trozo se quedó sin asignar entero**, cuando se quedó
    # (`gastos.NO_SE_REPARTE_PORQUE_*`: falta el importe del gasto, falta la superficie de una tierra o
    # falta decir el método).
    #
    # **Esta columna se añadió al integrar el ticket (05/10/2026), y su motivo es una prueba que
    # falló**: el motivo se calculaba, se usaba para el aviso y **se perdía al guardar**, así que la
    # respuesta de repartir decía «sin asignar 663,00 €» sin decir qué faltaba, y al volver a abrir el
    # gasto al día siguiente tampoco estaba. Es el mismo criterio que con `metodo`: lo que explica una
    # cifra delante de una inspección tiene que quedar escrito y no recalculado.
    no_se_reparte: Mapped[str | None] = mapped_column(String(40))
    # **Si el agricultor ha confirmado el método.** Nace en falso y no en verdadero: un reparto que
    # hizo el programa y nadie ha mirado no puede parecer confirmado.
    confirmado_por_el_agricultor: Mapped[bool] = mapped_column(Boolean, default=False)

    notas: Mapped[str | None] = mapped_column(Text)
    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class PagoDeGasto(Base):
    """El dinero que sale. **No es un gasto y no cuelga de un gasto.**

    Las dos decisiones que hacen que esto esté bien, y las dos tienen prueba:

      · **No cuelga de un gasto** (`gasto_id` no existe aquí) porque un pago puede saldar **varios**
        gastos (pagar la factura del taller y la del gasóleo con una transferencia) y un gasto puede
        pagarse con **varios** pagos. Eso se dice en `aplicaciones_de_pago`, que es una tabla aparte.
      · **No cambia el coste de nada.** El coste existe desde que se consume, se haya pagado o no; lo
        que hace un pago es cambiar **el pendiente**, que es otra cuenta.

    Un pago **sin ninguna aplicación** es un estado de verdad y no un error: es el dinero que salió y
    todavía no se sabe a qué va (se mira el banco antes que los papeles). Se queda dicho con esa
    palabra —«sin conciliar»— y la pantalla lo enseña en su lista, esperando.

    **Sin campaña propia**, como el `Cobro` del T12 y por el mismo motivo: es dinero que sale un día,
    no un apunte del cuaderno, y la campaña de lo que se paga la tiene el gasto al que salda.
    """

    __tablename__ = "pagos_de_gasto"
    __table_args__ = (
        Index(
            "uq_pago_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("anulado = 0"),
            postgresql_where=text("anulado = false"),
        ),
        Index("ix_pago_fecha", "explotacion_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)

    # El día en que salió el dinero. Vacío es «no consta», no «hoy».
    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)
    # **Obligatorio y mayor que cero**: un pago de cero euros no es un pago, y admitirlo llenaría la
    # lista de renglones que no dicen nada. Es la única columna de dinero de este bloque que no
    # admite vacío, justamente porque un pago sin importe no es nada.
    importe: Mapped[Decimal] = mapped_column(Dinero, nullable=False)

    proveedor: Mapped[str | None] = mapped_column(String(200))
    contacto_id: Mapped[int | None] = mapped_column(ForeignKey("contactos.id"), index=True)
    # transferencia | efectivo | cheque | confirming | otro (`ventas.FORMAS_DE_COBRO`, la MISMA lista
    # que la del cobro: no puede haber dos verdades sobre cómo se mueve el dinero).
    forma: Mapped[str] = mapped_column(String(20), default="transferencia")
    referencia: Mapped[str | None] = mapped_column(String(120))
    notas: Mapped[str | None] = mapped_column(Text)

    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    anulado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class AplicacionDeUnPago(Base):
    """Contra qué gasto va un pago, y cuánto. **Es lo único que crea la conciliación.**

    ## La regla del encargo, en una tabla

    «Conciliar un pago no crea un segundo gasto.» Aquí se ve por qué está escrita así: esta tabla
    **solo dice «este dinero va contra este gasto»**. No tiene importe propio de nada, no crea
    ninguna fila en `gastos` y **deshacerla es borrarla a ella** (con `correcciones.borrar`, que deja
    el rastro entero en la auditoría). El pago sigue apuntado con su importe entero y el gasto vuelve
    a estar pendiente: es literalmente el contrato —«Deshacer conciliación no borra el movimiento
    original»—, y es lo que hace que el dinero no desaparezca de ninguna de las dos pantallas.

    **Muchos a muchos**, que es lo que el contrato pide para los pagos parciales y agrupados: varias
    filas con el mismo `pago_id` (un pago que salda tres gastos) y varias con el mismo `gasto_id`
    (tres pagos que saldan uno). Y las dos cantidades están comprobadas en el router: la suma de las
    aplicaciones de un pago no pasa de su importe, y la de un gasto no pasa de lo que debe.
    """

    __tablename__ = "aplicaciones_de_pago"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    pago_id: Mapped[int] = mapped_column(ForeignKey("pagos_de_gasto.id"), index=True)
    gasto_id: Mapped[int] = mapped_column(ForeignKey("gastos.id"), index=True)
    importe: Mapped[Decimal] = mapped_column(Dinero, nullable=False)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class Subvencion(Base):
    """Una ayuda: lo que se pide, lo que se concede y lo que se cobra.

    ## Tres importes y no uno con un estado

    El contrato lo dice en S13: «Subvención prevista, concedida y cobrada son estados distintos. **No
    sumar previsión al ingreso cobrado**». Tres columnas y no una porque **los tres pueden convivir**:
    se pidió una ayuda esperando 12.000 €, concedieron 9.000 y todavía no ha entrado nada. Con una
    sola columna, apuntar la concesión borraría la previsión y el agricultor perdería la cuenta de lo
    que pidió.

    **Y el estado se deduce, no se guarda** (`gastos.estado_de_una_subvencion`): el estado más
    avanzado de los tres que consten. Guardarlo además de los importes sería tener dos verdades sobre
    lo mismo, y la del día que se apuntó dejaría de ser verdad al día siguiente.

    **Solo el importe cobrado cuenta como ingreso.** La previsión se enseña, con su palabra, en su
    propia tarjeta: un agricultor que ve su previsión sumada al ingreso cree que tiene un dinero que
    todavía no ha entrado.
    """

    __tablename__ = "subvenciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id"), index=True)

    concepto: Mapped[str | None] = mapped_column(String(200))
    organismo: Mapped[str | None] = mapped_column(String(200))
    fecha_solicitud: Mapped[dt.date | None] = mapped_column(Date)
    fecha_concesion: Mapped[dt.date | None] = mapped_column(Date)
    fecha_cobro: Mapped[dt.date | None] = mapped_column(Date)

    # **Cada uno puede faltar por su cuenta**, y vacío es «no consta»: una ayuda de la que no se sabe
    # el importe concedido no tiene concedido cero euros.
    importe_previsto: Mapped[Decimal | None] = mapped_column(Dinero)
    importe_concedido: Mapped[Decimal | None] = mapped_column(Dinero)
    importe_cobrado: Mapped[Decimal | None] = mapped_column(Dinero)

    notas: Mapped[str | None] = mapped_column(Text)
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    anulada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
