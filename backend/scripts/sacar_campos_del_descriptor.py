"""Saca del descriptor oficial la tabla de campos del cuaderno, campo por campo.

La hoja `EstructuraCuadernoWS` del descriptor es **la especificación de mapeo**: dice, por cada
campo, si es obligatorio, de qué tipo es, cómo se valida y —lo que más importa— **contra qué
catálogo**. Este script la convierte en datos para que el programa pueda comprobarla en vez de
que alguien la lea a ojo.

Se ejecuta desde `backend`:

    ../.venv/Scripts/python.exe scripts/sacar_campos_del_descriptor.py

Lo que escribe (`data/iuws_campos_del_cuaderno.json`) es **derivado**, no oficial: el fichero
oficial es el `.xlsx`, que no se toca. Por eso el JSON lleva dentro de dónde sale y con qué
huella, para poder rehacerlo y comparar.

No usa `openpyxl` a propósito: el proyecto no instala dependencias de formato para leer un
fichero oficial una vez. Se lee el `.xlsx` como lo que es, un ZIP con XML dentro.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import xml.etree.ElementTree as ET
import zipfile

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

RAIZ = pathlib.Path(__file__).resolve().parents[2]
OFICIAL = RAIZ / "data" / "iuws_fuentes" / "BdcSix-DS-DisenoCUE_3.11.4.xlsx"
SALIDA = RAIZ / "data" / "iuws_campos_del_cuaderno.json"
HOJA = "EstructuraCuadernoWS"

# Las columnas del descriptor que se usan. A..G son la jerarquía (bloque, subloque, campo),
# H la ocurrencia (`*` = obligatorio), I el tipo, J el control de formato y L las
# observaciones, que es donde el descriptor dice de qué catálogo sale cada código.
COLUMNAS_JERARQUIA = "ABCDEFG"

# La marca de un bloque. **No basta con la llave `{`**: el descriptor oficial la omite en 14
# cabeceras de bloque (entre ellas `TratamFito`, `SiembraPlantacion`, `HuertaVivero` y las listas
# de plagas, enfermedades y malas hierbas). Se descubrió cruzando la tabla con el esquema JSON, que
# sí tiene esos bloques: sin esto, sus campos quedaban colgando del bloque de arriba y el mapeo
# salía mal por un sitio que no se ve.
#
# La marca que sí es fiable es la **columna de ocurrencia**, que en un bloque dice cuántas veces
# puede repetirse (`0..n`, `1..n`, `0..1`) y en un campo solo puede ser `*` (obligatorio) o nada.
PATRON_DE_OCURRENCIA_DE_BLOQUE = re.compile(r"\d+\.\.(?:\d+|n)")


def cadenas_compartidas(z: zipfile.ZipFile) -> list[str]:
    raiz = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(f"{NS}t")) for si in raiz.findall(f"{NS}si")]


def ruta_de_la_hoja(z: zipfile.ZipFile, buscada: str) -> str | None:
    libro = z.read("xl/workbook.xml").decode("utf-8", "replace")
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8", "replace")
    destinos = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels))
    for m in re.finditer(r'<sheet[^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', libro):
        if m.group(1).strip().lower() == buscada.strip().lower():
            destino = destinos[m.group(2)]
            return destino if destino.startswith("xl/") else "xl/" + destino.lstrip("/")
    return None


def filas(z: zipfile.ZipFile, ruta: str, comunes: list[str]) -> list[dict[str, str]]:
    raiz = ET.fromstring(z.read(ruta))
    salida = []
    for fila in raiz.iter(f"{NS}row"):
        valores: dict[str, str] = {}
        for celda in fila.findall(f"{NS}c"):
            columna = re.match(r"([A-Z]+)", celda.get("r") or "")
            if not columna:
                continue
            tipo = celda.get("t")
            v = celda.find(f"{NS}v")
            if tipo == "inlineStr":
                dentro = celda.find(f"{NS}is")
                texto = "".join(t.text or "" for t in dentro.iter(f"{NS}t")) if dentro is not None else ""
            elif v is None:
                texto = ""
            elif tipo == "s":
                texto = comunes[int(v.text)]
            else:
                texto = v.text or ""
            valores[columna.group(1)] = texto.strip()
        salida.append(valores)
    return salida


def catalogo_citado(control: str, observaciones: str) -> str | None:
    """El nombre del catálogo tal y como lo escribe el descriptor, o `None` si no cita ninguno.

    **No se traduce al identificador de la tabla de SIEX.** Se comprobó que el descriptor no
    usa esos identificadores: los nombra en prosa («Catálogo de Medida preventiva/cultural»).
    Emparejarlos por parecido de nombre sería adivinar, así que se guarda lo que dice y punto.
    """
    for texto in (observaciones, control):
        limpio = texto.strip()
        if not limpio:
            continue
        m = re.match(r"^cat[aá]logo\s+de\s+(.+)$", limpio, flags=re.I)
        if m:
            return m.group(1).strip()
        if re.search(r"validar contra el cat[aá]logo", limpio, flags=re.I):
            return "sin especificar en el descriptor"
    return None


def extraer(comunes: list[str], filas_hoja: list[dict[str, str]]) -> list[dict]:
    registros: list[dict] = []
    pila: list[str] = []
    for numero, fila in enumerate(filas_hoja, 1):
        if numero == 1:
            continue
        jerarquia = [(c, fila.get(c, "")) for c in COLUMNAS_JERARQUIA if fila.get(c)]
        if not jerarquia:
            continue
        columna, valor = jerarquia[-1]
        nivel = COLUMNAS_JERARQUIA.index(columna)
        limpio = valor.strip()
        ocurrencia = fila.get("H", "").strip()
        # Bloque: o lleva llave, o su ocurrencia dice que se repite. Ver el porqué arriba.
        es_bloque = limpio.endswith("{") or bool(
            PATRON_DE_OCURRENCIA_DE_BLOQUE.fullmatch(ocurrencia)
        )
        cierra = limpio.endswith("}")
        nombre = limpio.rstrip("{}").strip()

        if cierra:
            while len(pila) > nivel:
                pila.pop()
            continue
        while len(pila) > nivel:
            pila.pop()
        if es_bloque:
            pila.append(nombre)
            # Una **lista** también puede traer su catálogo en la cabecera: la lista de
            # enfermedades, la de plagas, la de malas hierbas y la de reguladores lo traen. Se
            # apunta en el bloque, sin repartirlo a los campos de dentro: repartirlo sería
            # decidir que el catálogo de la lista es el de cada elemento, y eso no lo dice el
            # documento. Se guarda lo que dice, donde lo dice.
            registros.append(
                {
                    "tipo": "bloque",
                    "ruta": ".".join(pila),
                    "catalogo": catalogo_citado(fila.get("J", ""), fila.get("L", "")),
                }
            )
            continue

        ocurrencia = fila.get("H", "").strip()
        registros.append(
            {
                "tipo": "campo",
                "ruta": ".".join(pila + [nombre]),
                "campo": nombre,
                "obligatorio": ocurrencia == "*",
                "tipo_de_dato": fila.get("I", ""),
                # La descripción del campo, tal y como la escribe el descriptor. Se guarda porque
                # **es donde están las convenciones**: `SiembraPlantacion` dice «1 Siembra 0
                # Plantación», y eso es lo que permite rellenarlo sin inventarse nada. Sin este
                # texto, esa convención habría quedado como un «me suena que es así».
                "descripcion": fila.get("K", ""),
                "catalogo": catalogo_citado(fila.get("J", ""), fila.get("L", "")),
            }
        )
    return registros


def main() -> int:
    if not OFICIAL.exists():
        print(f"Falta el descriptor oficial: {OFICIAL}")
        return 1
    z = zipfile.ZipFile(OFICIAL)
    comunes = cadenas_compartidas(z)
    ruta = ruta_de_la_hoja(z, HOJA)
    if not ruta:
        print(f"No se encuentra la hoja {HOJA!r} en el descriptor")
        return 1

    registros = extraer(comunes, filas(z, ruta, comunes))
    campos = [r for r in registros if r["tipo"] == "campo"]
    bloques = [r for r in registros if r["tipo"] == "bloque"]
    catalogo = {r["catalogo"] for r in registros if r.get("catalogo")}

    salida = {
        "_leeme": (
            "DERIVADO, no oficial. Sale de la hoja EstructuraCuadernoWS del descriptor oficial, "
            "que NO se toca. Se rehace con scripts/sacar_campos_del_descriptor.py."
        ),
        "fuente": OFICIAL.name,
        "fuente_sha256": hashlib.sha256(OFICIAL.read_bytes()).hexdigest(),
        "hoja": HOJA,
        "bloques": len(bloques),
        "campos": len(campos),
        "obligatorios": sum(1 for c in campos if c["obligatorio"]),
        "registros": registros,
    }
    # Compacto a propósito: son 400 y pico registros y no hace falta que nadie los lea a ojo.
    # Lo que hay que poder leer es el fichero oficial, no este.
    SALIDA.write_text(
        json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    print(f"bloques: {len(bloques)}   campos: {len(campos)}   obligatorios: {salida['obligatorios']}")
    print(f"catalogos que cita el descriptor: {len(catalogo)}")
    for nombre in sorted(catalogo):
        de_campos = sum(1 for c in campos if c["catalogo"] == nombre)
        de_listas = sum(1 for b in bloques if b.get("catalogo") == nombre)
        print(f"   {de_campos:>3} campos, {de_listas} listas  {nombre}")
    print(f"escrito: {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
