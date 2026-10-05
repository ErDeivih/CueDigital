"""La firma del cuaderno.

**Para qué sirve esto, dicho sin tecnicismos.** Un cuaderno sin firmar es un documento
que cualquiera puede haber cambiado. Firmado, queda claro **quién** lo hizo y que nadie
lo ha tocado después. Eso es exactamente lo que mira una inspección, y es lo que
convierte el cuaderno en algo que vale delante de la administración.

**Cómo funciona, en tres pasos:**

1. El programa escribe el cuaderno en un **fichero de texto canónico**: siempre igual,
   con los campos siempre en el mismo orden, para que el mismo cuaderno dé siempre el
   mismo fichero. La huella (SHA-256) de ese fichero es lo que identifica esa versión
   concreta del cuaderno.
2. El agricultor firma ese fichero con **AutoFirma**, que es lo que usa para todo lo
   demás de la administración. AutoFirma lee su certificado y produce un fichero de
   firma.
3. El programa guarda la firma junto con la huella. A partir de ahí, **cada vez que se
   mire el cuaderno se vuelve a calcular la huella**: si coincide, nadie lo ha tocado;
   si no coincide, el cuaderno se ha cambiado después de firmarlo, y hay que decirlo
   bien claro.

**Lo que este módulo hace y lo que no.** Aquí se prepara el fichero y se guarda la firma. La
comprobación de que el fichero de firma corresponde de verdad a este cuaderno está en
`app/cades.py`, y desde la ronda 12 **sí se hace**: se lee el fichero de firma, se comprueba que
el resumen que lleva dentro es el del cuaderno, y se comprueba la cuenta de la firma con el
certificado. Lo que sigue sin comprobarse es **la cadena de confianza** (que el certificado lo
haya emitido una autoridad de fiar), porque eso necesita la lista de autoridades raíz; está
declarado en el resultado de `cades.verificar` y anotado en `docs/LO_QUE_PIDE_LA_JUNTA.md`.

En resumen: este módulo garantiza que **el contenido firmado no ha cambiado**, y `cades.py` que
**la firma es de quien dice y de este cuaderno**. Las dos cosas juntas son las que valen.

**Aviso importante antes de firmar de verdad:** cambiar la forma canónica (añadir un
campo a la lista, cambiar el orden, cambiar cómo se escriben los números) **invalida
todas las firmas anteriores**. Por eso la forma lleva un número de versión y por eso hay
que congelarla antes de la primera firma de un agricultor de verdad.
"""

from __future__ import annotations

import datetime as dt
import hashlib

from . import catalogos

# La versión de la forma canónica. Si se cambia la forma, hay que subir esto, y las
# firmas viejas dejarán de cuadrar (lo cual es correcto: el documento ya no es el mismo).
VERSION_CANONICA = 1

ALGORITMO = "SHA256withRSA"
FORMATO = "CAdES"

# Dónde está AutoFirma en cada sistema, según el manual oficial (sección 6).
EJECUTABLES = {
    "windows": "AutoFirmaCommandLine",
    "linux": "/usr/bin/AutoFirma",
    "mac": "/Applications/AutoFirma.app/Contents/MacOS/AutoFirmaCommandLine",
}


# --------------------------------------------------------------------------
# Escribir los datos siempre igual
# --------------------------------------------------------------------------


def numero(valor) -> str:
    """Un número escrito siempre de la misma forma.

    Se redondea a seis decimales y se quitan los ceros de detrás. Hace falta porque el
    fichero tiene que salir idéntico byte a byte cada vez que se genere: un "0.8" que
    saliera un día como "0.8000000001" cambiaría la huella y el cuaderno parecería
    manipulado sin que nadie lo hubiera tocado.
    """
    if valor is None:
        return ""
    try:
        texto = f"{float(valor):.6f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(valor)
    return texto if texto else "0"


def valor_para_firmar(valor) -> str:
    """Convierte cualquier valor en una línea de texto estable."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "si" if valor else "no"
    if isinstance(valor, (dt.date, dt.datetime)):
        return valor.isoformat()
    if isinstance(valor, float):
        return numero(valor)
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, (list, tuple)):
        return ", ".join(valor_para_firmar(item) for item in valor)
    return str(valor).strip()


def si_no_o_no_se(valor) -> str | bool:
    """Un sí, un no, o «no se sabe»: las tres cosas son distintas.

    Se usa en los campos del cuaderno que pueden quedar **sin comprobar** (por ahora, si la
    aplicación se hizo en zona vulnerable a nitratos). Un `None` ahí no es un «no»: es que nadie
    lo ha podido comprobar, y escribirlo como «no» en el documento que se firma sería dejar por
    escrito algo que no es verdad —y encima, una vez firmado, ya no se puede corregir sin firmar
    otra vez—.

    Los `True` y los `False` se siguen escribiendo igual que siempre («si» y «no») **a
    propósito**: así el texto canónico de los cuadernos ya firmados no cambia ni un byte y sus
    huellas siguen cuadrando. No hizo falta subir `VERSION_CANONICA` justo por eso: estas dos
    columnas no admitían un «no se sabe» hasta ahora, así que ningún apunte firmado puede tenerlo.
    """
    if valor is None:
        return "no se sabe"
    return bool(valor)


def numero_o_no_se(valor) -> str | float:
    """Un número, o «no se sabe» cuando nadie lo ha declarado.

    Es el mismo criterio que `si_no_o_no_se`, para la composición de un abono: sus riquezas y lo
    que aporta pueden ser **desconocidas** (A6 de `docs/T02_VALORES_POR_DEFECTO.md`), y escribir
    ahí un cero afirmaría que ese estiércol no lleva nitrógeno, fósforo ni potasio. Lo que pasa es
    que nadie ha declarado la composición, que no es lo mismo.

    **Y esto no cambia ni una firma de las hechas, por el mismo motivo que en `si_no_o_no_se`.**
    Un número se escribe igual que siempre —el `0.0` de los apuntes viejos sigue saliendo como
    «0»—, y el «no se sabe» es un estado **nuevo**: hasta ahora estas columnas eran `NOT NULL` con
    defecto `0.0`, así que ningún cuaderno firmado puede tener un abono sin composición. Por eso no
    se sube `VERSION_CANONICA` (hay una prueba que lo fija).
    """
    if valor is None:
        return "no se sabe"
    return valor


def bloque(titulo: str, campos: dict) -> str:
    """Un trozo del fichero: un título y sus campos, siempre en el mismo orden.

    Los campos van ordenados por su nombre para que el orden en que se escriban en el
    código no cambie el fichero. Y las claves van en castellano porque este fichero lo
    puede leer una persona: es el cuaderno, no un volcado de la base de datos.
    """
    lineas = [f"== {titulo}"]
    for clave in sorted(campos):
        lineas.append(f"{clave}: {valor_para_firmar(campos[clave])}")
    return "\n".join(lineas)


def huella(texto: str) -> str:
    """La huella del fichero: lo que se firma y lo que se comprueba después."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# El fichero del cuaderno
# --------------------------------------------------------------------------


CABECERA = (
    "CUADERNO DE CAMPO\n"
    "=================\n"
    "Este fichero es el cuaderno tal y como se firma. Si algo cambia en el cuaderno,\n"
    "este fichero cambia, y la firma deja de cuadrar. Por eso no se puede tocar a mano.\n"
)


def texto_del_cuaderno(
    *,
    explotacion: dict,
    campana: dict,
    tratamientos: list[dict] | None = None,
    fertilizaciones: list[dict] | None = None,
    labores: list[dict] | None = None,
) -> str:
    """Escribe el cuaderno entero de una campaña, siempre igual.

    Cada registro va en su bloque, y los bloques van numerados en el orden en que se
    generan (que el que llama debe fijar: por fecha y por identificador). El número de
    bloque importa: si se reordena el cuaderno, el fichero cambia, y eso también es un
    cambio del cuaderno.
    """
    trozos = [
        CABECERA,
        f"version: {VERSION_CANONICA}",
        "",
        bloque("FINCA", explotacion),
        "",
        bloque("AÑO", campana),
        "",
        f"=== PRODUCTOS APLICADOS ({len(tratamientos or [])})",
    ]
    for indice, registro in enumerate(tratamientos or [], start=1):
        trozos.append("")
        trozos.append(bloque(f"PRODUCTO APLICADO {indice}", registro))

    trozos.extend(["", f"=== ABONOS ({len(fertilizaciones or [])})"])
    for indice, registro in enumerate(fertilizaciones or [], start=1):
        trozos.append("")
        trozos.append(bloque(f"ABONO {indice}", registro))

    trozos.extend(["", f"=== LABORES ({len(labores or [])})"])
    for indice, registro in enumerate(labores or [], start=1):
        trozos.append("")
        trozos.append(bloque(f"LABOR {indice}", registro))

    return "\n".join(trozos) + "\n"


def texto_de_un_registro(titulo: str, campos: dict) -> str:
    """El fichero para firmar un solo registro, no el cuaderno entero."""
    return "\n".join([CABECERA, f"version: {VERSION_CANONICA}", "", bloque(titulo, campos)]) + "\n"


# --------------------------------------------------------------------------
# AutoFirma
# --------------------------------------------------------------------------


def comando_autofirma(nombre_fichero: str, sistema: str = "windows") -> str:
    """La orden que hay que ejecutar para firmar el fichero, según el manual oficial.

    Está sacada de la sección 6 del manual de AutoFirma (`11_AutoFirma_manual_firma_linea_comandos.pdf`),
    no inventada. Los comandos disponibles son sign, cosign, countersign, listaliases,
    verify y batchsign; el que hace falta aquí es `sign`.
    """
    ejecutable = EJECUTABLES.get(sistema, EJECUTABLES["windows"])
    return (
        f'"{ejecutable}" sign '
        f'-i "{nombre_fichero}" '
        f'-o "{nombre_fichero}.csig" '
        f"-format {FORMATO.lower()} "
        f"-algorithm {ALGORITMO}"
    )


# --------------------------------------------------------------------------
# Comprobar que nadie ha tocado nada
# --------------------------------------------------------------------------


ESTADO_SIN_FIRMAR = "sin_firmar"
ESTADO_FIRMADO = "firmado"
ESTADO_CAMBIADO = "cambiado_despues_de_firmar"


def estado_de_la_firma(firma, huella_actual: str) -> str:
    """Dice si el cuaderno sigue siendo el que se firmó.

    Tres respuestas posibles, y la del medio es la que importa:

    - **sin_firmar**: todavía no se ha firmado.
    - **firmado**: se firmó y nadie lo ha tocado. La huella de ahora es la misma que la
      que se firmó.
    - **cambiado_despues_de_firmar**: se firmó, y después alguien ha cambiado algo. Esto
      no significa que esté mal, pero hay que decirlo: una firma que ya no cuadra es
      peor que no tener firma, porque parece que el cuaderno está respaldado y no lo está.
    """
    if firma is None:
        return ESTADO_SIN_FIRMAR
    if firma.huella == huella_actual:
        return ESTADO_FIRMADO
    return ESTADO_CAMBIADO


# --------------------------------------------------------------------------
# Los campos que van al fichero, registro a registro
#
# Se escriben aquí, y no con un bucle automático sobre las columnas de la base de datos,
# por dos motivos. El primero: el fichero lo puede leer una persona, así que las claves
# van en castellano y los identificadores internos no van. El segundo, y más importante:
# si mañana se añade una columna a la tabla, el cuaderno firmado NO puede cambiar solo.
# Añadir un campo aquí es una decisión consciente, y sube la versión de la forma.
# --------------------------------------------------------------------------


def campos_de_un_tratamiento(
    tratamiento, parcela: str, aplicador: str, equipo: str, instalacion: str = ""
) -> dict:
    return {
        "Clase de aplicación": tratamiento.tipo,
        "Fecha": tratamiento.fecha,
        "Hora de inicio": tratamiento.hora_inicio,
        "Hora de fin": tratamiento.hora_fin,
        "Parcela": parcela,
        "Nave o almacén": instalacion,
        "Producto que se trató": tratamiento.producto_cosechado,
        "Partida de la cosecha": tratamiento.lote_cosecha,
        "Cultivo": tratamiento.cultivo,
        "Variedad": tratamiento.variedad,
        "Superficie tratada (ha)": tratamiento.superficie_tratada_ha,
        "Plaga o problema": tratamiento.plaga,
        "Motivo del tratamiento": tratamiento.justificacion,
        "Producto": tratamiento.producto_nombre,
        "Número de la etiqueta": tratamiento.numero_registro,
        "Lo que lleva dentro": tratamiento.materia_activa,
        "Lote del producto": tratamiento.lote_producto,
        "Dosis": tratamiento.dosis,
        "Unidad de la dosis": tratamiento.unidad_dosis,
        "Cantidad total": tratamiento.cantidad_total,
        "Días de espera": tratamiento.plazo_seguridad_dias,
        "Se puede coger desde": tratamiento.fecha_fin_plazo_seguridad,
        "Días para volver a entrar": tratamiento.plazo_reentrada_dias,
        "Quién lo aplicó": aplicador,
        "Máquina": equipo,
        "Temperatura (C)": tratamiento.temperatura_c,
        "Humedad (%)": tratamiento.humedad_pct,
        "Viento (km/h)": tratamiento.viento_kmh,
        "Dirección del viento": tratamiento.viento_direccion,
        "Se dejó la orilla sin tratar": tratamiento.franja_seguridad_respetada,
        # Estas dos se añadieron al mapear el cuaderno al formato de la Junta, que las exige como
        # obligatorias. Van en el documento firmado porque forman parte del registro: si se
        # contestan **después** de firmar, la huella deja de cuadrar y el programa lo dice, que es
        # justo lo que tiene que pasar.
        "Se aplicó a mano": tratamiento.aplicado_a_mano,
        "Cómo funcionó el tratamiento": catalogos.ETIQUETA_EFICACIA.get(
            tratamiento.eficacia, tratamiento.eficacia
        ),
        "En zona de nitratos": si_no_o_no_se(tratamiento.en_zona_vulnerable),
        "Lo que se hizo antes de echarlo": tratamiento.medidas,
        "Personas expuestas": tratamiento.operadores_expuestos,
        "Incidencias": tratamiento.incidencias,
        "Observaciones": tratamiento.observaciones,
        # Anular un apunte también es un cambio del cuaderno, y tiene que notarse.
        "Anulado": tratamiento.anulado,
        "Motivo de la anulación": tratamiento.motivo_anulacion,
    }


def campos_de_un_abono(registro, parcela: str) -> dict:
    return {
        "Fecha": registro.fecha,
        "Parcela": parcela,
        "Superficie (ha)": registro.superficie_ha,
        "Abono": registro.fertilizante_nombre,
        "Tipo": registro.tipo,
        # La composición y lo que aporta: si no consta, se dice «no se sabe» y no se escribe un
        # cero, que en un documento firmado se lee como una afirmación (ver `numero_o_no_se`).
        "Nitrógeno (%)": numero_o_no_se(registro.riqueza_n),
        "Fósforo (%)": numero_o_no_se(registro.riqueza_p),
        "Potasio (%)": numero_o_no_se(registro.riqueza_k),
        "Kilos por hectárea": registro.kg_ha_producto,
        "Kilos en total": registro.cantidad_total_kg,
        "Nitrógeno aportado (kg/ha)": numero_o_no_se(registro.uf_n_ha),
        "Fósforo aportado (kg/ha)": numero_o_no_se(registro.uf_p_ha),
        "Potasio aportado (kg/ha)": numero_o_no_se(registro.uf_k_ha),
        "Cómo se aplicó": registro.modo_aplicacion,
        "Momento": registro.momento,
        "En zona de nitratos": si_no_o_no_se(registro.en_zona_vulnerable),
        "Nitratos del agua de riego": registro.nitratos_agua_riego,
        "Observaciones": registro.observaciones,
        "Anulado": registro.anulado,
        "Motivo de la anulación": registro.motivo_anulacion,
    }


def campos_de_una_labor(labor, parcela: str, tipo_legible: str) -> dict:
    """Todo lo que el cuaderno sabe de una labor, para el documento que se firma.

    Faltaban los datos propios de cada tipo de labor —el agua del riego, la semilla de la siembra
    y el ganado del pastoreo—: se guardaban y no salían en el documento firmado, que es el que
    vale delante de la administración. Un dato que no está en el documento firmado es un dato que
    no está.
    """
    return {
        "Fecha": labor.fecha,
        "Labor": tipo_legible,
        "Parcela": parcela,
        "Superficie (ha)": labor.superficie_ha,
        "Cultivo": labor.cultivo,
        "Variedad": labor.variedad,
        # Siembra y plantación.
        "Semilla (kg)": labor.cantidad_semilla_kg,
        "Dosis de siembra (kg/ha)": labor.dosis_siembra_kg_ha,
        "Siembra directa": labor.siembra_directa,
        "Semilla tratada": labor.material_tratado,
        "Semilla comprada": labor.material_adquirido,
        "Fecha de la compra": labor.fecha_adquisicion,
        "Lote de la semilla": labor.lote_semilla,
        "Plantas por hectárea": labor.densidad_plantacion,
        "Marco de plantación": labor.marco_plantacion,
        # Riego.
        "Agua (volumen)": labor.volumen_agua,
        "Unidad del agua": labor.unidad_agua,
        "De dónde salió el agua": labor.origen_agua,
        "Sistema de riego": labor.sistema_riego,
        "Número de contador": labor.numero_contador,
        "Nitratos del agua (mg/l)": labor.nitratos_agua,
        # Pastoreo.
        "Animales de terceros": labor.animales_terceros,
        "Animales propios": labor.animales_propios,
        "Detalles": labor.detalles,
        "Observaciones": labor.observaciones,
        "Anulado": labor.anulado,
        "Motivo de la anulación": labor.motivo_anulacion,
    }
