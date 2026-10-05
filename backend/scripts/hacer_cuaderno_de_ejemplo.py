"""Hace el cuaderno de ejemplo para los tests, **con datos inventados**.

## Por qué existe este guion

Los tests del lector del cuaderno de la Junta (el Cuecyl) necesitan un fichero de Excel que se
parezca al de verdad. Y aquí hay una regla que no se puede saltar: **los cuadernos reales de un
agricultor no entran en el repositorio**. Llevan su nombre, su NIF, su teléfono, su correo y la
situación exacta de sus tierras. Eso es suyo y de nadie más.

Así que el fichero de prueba se **fabrica** con este guion, con los mismos nombres de hoja, las
mismas etiquetas y las mismas columnas que el cuaderno oficial, pero con una explotación que no
existe: «EXPLOTACIÓN DE EJEMPLO», NIF de mentira, parcelas en un término municipal inventado
(código 99) y superficies redondas.

## De dónde salen las etiquetas y las columnas

De `app/cuaderno_cyl.py`, que es el que las busca: así el ejemplo y el lector no se pueden
separar. Pero **eso solo no basta** —si una etiqueta estuviera mal escrita en el lector, el
ejemplo la escribiría igual de mal y el test pasaría—, y por eso el lector se escribió y se
comprobó antes contra **los tres cuadernos oficiales de verdad** (campañas 2024, 2025 y 2026,
25 hojas cada uno, que es de donde salen la hoja «2.1. DATOS PARCELAS», sus dos renglones de
cabecera y sus notas al pie). Este guion reproduce esa misma estructura.

## Cómo se regenera

```bash
cd backend
../.venv/Scripts/python.exe scripts/hacer_cuaderno_de_ejemplo.py
```

Vuelve a escribir `tests/datos/cuaderno_cyl_de_ejemplo.xlsx`. Si algún día se cambia el lector,
se vuelve a lanzar y el fichero de ejemplo queda al día.
"""

from __future__ import annotations

import datetime as dt
import io
import pathlib
import sys

from openpyxl import Workbook

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import cuaderno_cyl as cyl  # noqa: E402

DESTINO = pathlib.Path(__file__).resolve().parents[1] / "tests" / "datos" / (
    "cuaderno_cyl_de_ejemplo.xlsx"
)

# Las 25 hojas del cuaderno oficial, con los nombres tal y como los pone la Junta. Las demás
# hojas van vacías a propósito: en un cuaderno recién descargado también lo están, y así el
# ejemplo se parece de verdad al fichero que sube el agricultor.
HOJAS = [
    "1.1. INF. GRAL",
    "1.2., 1.3. y 1.4. INF. GRAL",
    "2.1. DATOS PARCELAS",
    "2.2. DATOS IDEN. MEDIAMB. P.",
    "3.1. REG. FIT. x P.",
    "3.1. bis REG. FIT. x P. (ASESOR",
    "3.2. REG. USO SEMILLA TRAT.",
    "3.3. REG. TRAT. POSTCOS",
    "3.4. REG. TRAT. ALMACEN",
    "3.5. REG. TRAT. MED.TRANSP",
    "4. REG. ANALISIS",
    "5. REG. COMERC.",
    "6. REG. FERTILIZ",
    "7. DAT. AGROAMB.",
    "7.1 FERTILIZA RM Y AO",
    "7.2 RIEGO RM",
    "8. VIÑEDO CON DOP_IGP",
    "9.1. INF. FERTILIZACIÓN",
    "9.1.1. INF. RIEGO",
    "9.1.2. PLAN ABONADO",
    "9.3.  PRÁCTICA SIEGA SOSTENIBLE",
    "9.4. ISLAS BIODIVERSIDAD",
    "9.5. CUBIERTAS VEGETALES ",
    "9.6. CUBIERTAS INERTES",
    "doc",
]

ANIO = 2026

# Una explotación que no existe. El código de provincia 99 y el de municipio 99 no son de ningún
# sitio de España, y el NIF es el que se usa en los ejemplos («12345678Z»), para que nadie pueda
# confundir estos datos con los de una persona de verdad.
GENERALES = {
    "NOMBRE Y APELLIDOS O RAZÓN SOCIAL:": "EXPLOTACIÓN DE EJEMPLO",
    "NIF:": "12345678Z",
    "Nº Registro de Explotaciones Nacional:": "",  # en blanco a propósito, como en la realidad
    "Nº Registro de Explotaciones Autonómico:": "9999999999",
    "Dirección:": "CALLE DEL EJEMPLO, 1",
    "Localidad:": "PUEBLO DE EJEMPLO",
    "C.Postal:": "00000",
    "Provincia:": "PROVINCIA DE EJEMPLO",
    "Telófono fijo:": "",  # la errata «Telófono» es la del fichero oficial: se copia igual
    "Telófono móvil:": "600000000",
    "e-mail:": "ejemplo@ejemplo.test",
}

# Las líneas de parcela del ejemplo. Cada una es una línea del cuaderno: la misma tierra puede
# salir varias veces si dentro hay cultivos distintos, y eso es justo lo que hay que probar.
LINEAS = [
    # Una tierra normal: un recinto, un cultivo, sin variedad.
    {
        "municipio": "99-PUEBLO DE EJEMPLO",
        "agregado": 0,
        "zona": 0,
        "poligono": 1,
        "parcela": 1,
        "recinto": 1,
        "uso": "TA",
        "sigpac": 1.09,
        "cultivada": 1.09,
        "especie": "CEBADA",
        "ecorregimen": "P3",
        "sistema": "S",
        "principal": "Principal",
        "nitratos": "Sí",
    },
    # Con variedad, que el cuaderno escribe detrás de un punto.
    {
        "municipio": "99-PUEBLO DE EJEMPLO",
        "agregado": 0,
        "zona": 0,
        "poligono": 1,
        "parcela": 2,
        "recinto": 1,
        "uso": "TA",
        "sigpac": 4.9,
        "cultivada": 4.9,
        "especie": "VEZA VELLOSA.VILLANA",
        "ecorregimen": "P3",
        "sistema": "S",
        "principal": "Principal",
        "nitratos": "",
    },
    # Una tierra partida en tres líneas: barbecho y dos trozos de avena. Es el caso del recinto
    # que en el cuaderno de verdad sale tres veces (parcela 24 del polígono 507).
    {
        "municipio": "99-PUEBLO DE EJEMPLO",
        "agregado": 0,
        "zona": 0,
        "poligono": 1,
        "parcela": 5,
        "recinto": 1,
        "uso": "TA",
        "sigpac": 5.07,
        "cultivada": 4.44,
        "especie": "BARBECHO TRADICIONAL",
        "ecorregimen": "P3",
        "sistema": "S",
        "principal": "Principal",
        "nitratos": "",
    },
    {
        "municipio": "99-PUEBLO DE EJEMPLO",
        "agregado": 0,
        "zona": 0,
        "poligono": 1,
        "parcela": 5,
        "recinto": 1,
        "uso": "TA",
        "sigpac": 5.07,
        "cultivada": 0.46,
        "especie": "AVENA",
        "ecorregimen": "P3",
        "sistema": "S",
        "principal": "Principal",
        "nitratos": "",
    },
    {
        "municipio": "99-PUEBLO DE EJEMPLO",
        "agregado": 0,
        "zona": 0,
        "poligono": 1,
        "parcela": 5,
        "recinto": 1,
        "uso": "TA",
        "sigpac": 5.07,
        "cultivada": 0.13,
        "especie": "AVENA",
        "ecorregimen": "P3",
        "sistema": "S",
        "principal": "Principal",
        "nitratos": "",
    },
    # De regadío, en otro término municipal, y con la casilla de nitratos puesta en «No»: eso sí
    # es un «no» comprobado, y no puede acabar como las que están en blanco.
    {
        "municipio": "99-OTRO PUEBLO DE EJEMPLO",
        "agregado": 0,
        "zona": 0,
        "poligono": 2,
        "parcela": 10,
        "recinto": 1,
        "uso": "TA",
        "sigpac": 2.0,
        "cultivada": 2.0,
        "especie": "MAIZ",
        "ecorregimen": "",
        "sistema": "R",
        "principal": "Principal",
        "nitratos": "No",
    },
    # Sin decir si es secano o regadío: el cuaderno lo deja en blanco y el programa lo cuenta.
    {
        "municipio": "99-OTRO PUEBLO DE EJEMPLO",
        "agregado": 0,
        "zona": 0,
        "poligono": 2,
        "parcela": 11,
        "recinto": 2,
        "uso": "TA",
        "sigpac": 1.5,
        "cultivada": 1.5,
        "especie": "TRIGO BLANDO",
        "ecorregimen": "P3",
        "sistema": "",
        "principal": "Principal",
        "nitratos": "",
    },
    # Una línea sin recinto: no se puede identificar la tierra, así que no se da de alta y se
    # dice cuál es.
    {
        "municipio": "99-OTRO PUEBLO DE EJEMPLO",
        "agregado": 0,
        "zona": 0,
        "poligono": 2,
        "parcela": 12,
        "recinto": None,
        "uso": "TA",
        "sigpac": 0.8,
        "cultivada": 0.8,
        "especie": "CEBADA",
        "ecorregimen": "P3",
        "sistema": "S",
        "principal": "Principal",
        "nitratos": "",
    },
]


def _hoja_general(libro) -> None:
    """La hoja 1.1, con las etiquetas puestas donde las pone la Junta."""
    hoja = libro[cyl.HOJA_GENERAL]
    hoja["B2"] = "1. INFORMACIÓN GENERAL"
    hoja["B6"] = "1.1 DATOS GENERALES DE LA EXPLOTACIÓN"
    # Las etiquetas y sus valores, cada uno en su fila, tal y como están en el fichero oficial.
    situacion = {
        "NOMBRE Y APELLIDOS O RAZÓN SOCIAL:": ("B", 7, "G"),
        "NIF:": ("Q", 7, "R"),
        "Nº Registro de Explotaciones Nacional:": ("B", 8, "F"),
        "Nº Registro de Explotaciones Autonómico:": ("K", 8, "P"),
        "Dirección:": ("B", 9, "C"),
        "Localidad:": ("I", 9, "J"),
        "C.Postal:": ("O", 9, "P"),
        "Provincia:": ("Q", 9, "R"),
        "Telófono fijo:": ("B", 10, "D"),
        "Telófono móvil:": ("F", 10, "H"),
        "e-mail:": ("J", 10, "K"),
    }
    for etiqueta, (columna_etiqueta, fila, columna_valor) in situacion.items():
        hoja[f"{columna_etiqueta}{fila}"] = etiqueta
        valor = GENERALES[etiqueta]
        if valor:
            hoja[f"{columna_valor}{fila}"] = valor
    hoja["B11"] = "TITULAR O REPRESENTANTE DE LA EXPLOTACIÓN"
    hoja["B12"] = "Nombre y apellidos:"
    hoja["Q12"] = "NIF:"
    hoja["B24"] = (
        "(1) La persona firmante se hace responsable de la veracidad de los datos consignados "
        "en el presente cuaderno."
    )


def _hoja_parcelas(libro) -> None:
    """La hoja 2.1, con su cabecera de dos renglones, sus líneas y su nota al pie."""
    hoja = libro[cyl.HOJA_PARCELAS]
    hoja["B2"] = "Explotación/Titular de la explotación:"
    hoja["F2"] = GENERALES["NOMBRE Y APELLIDOS O RAZÓN SOCIAL:"]
    hoja["P2"] = "AÑO"
    hoja["Q2"] = ANIO
    hoja["B6"] = "2. IDENTIFICACIÓN DE LAS PARCELAS DE LA EXPLOTACIÓN"
    hoja["B11"] = "2.1 DATOS IDENTIFICATIVOS Y AGRONÓMICOS DE LAS PARCELAS"

    # Cabecera: la primera columna es la de «Nº DE ORDEN», que es la que busca el lector para
    # saber dónde empieza la tabla.
    cabecera = {
        "B": "Nº DE ORDEN (1)",
        "C": "Código Provincia",
        "D": "Término municipal (código y nombre)",
        "E": "Código Agregado",
        "F": "Zona",
        "G": "Nº de Polígono",
        "H": "Nº de Parcela",
        "I": "Nº de Recinto",
        "J": "Uso SIGPAC",
        "K": "Superficie SIGPAC (ha)",
        "L": "Superficie Cultivada (ha)",
        "M": "Especie/ Variedad",
        "N": "Ecoregimen/ Práctica (4)",
        "O": "Secano/ Regadío",
        "P": "Cultivo principal/ secundario",
        "Q": "Fecha inicio cultivo",
        "R": "Fecha fin cultivo",
        "S": "Aire libre o protegido (3)",
        # Esta cabecera no empieza por «zona nitratos»: el lector la encuentra por el texto que
        # lleva dentro, y el ejemplo reproduce ese detalle para que se pruebe de verdad.
        "U": "Parcela  ubicada  en zona  nitratos",
    }
    for columna, texto in cabecera.items():
        hoja[f"{columna}12"] = texto

    fila = 14
    for orden, linea in enumerate(LINEAS, start=1):
        hoja[f"B{fila}"] = float(orden)
        hoja[f"C{fila}"] = 99
        hoja[f"D{fila}"] = linea["municipio"]
        hoja[f"E{fila}"] = linea["agregado"]
        hoja[f"F{fila}"] = linea["zona"]
        hoja[f"G{fila}"] = linea["poligono"]
        hoja[f"H{fila}"] = linea["parcela"]
        if linea["recinto"] is not None:
            hoja[f"I{fila}"] = linea["recinto"]
        hoja[f"J{fila}"] = linea["uso"]
        hoja[f"K{fila}"] = linea["sigpac"]
        hoja[f"L{fila}"] = linea["cultivada"]
        hoja[f"M{fila}"] = linea["especie"]
        hoja[f"N{fila}"] = linea["ecorregimen"]
        hoja[f"O{fila}"] = linea["sistema"]
        hoja[f"P{fila}"] = linea["principal"]
        hoja[f"S{fila}"] = ""
        if linea["nitratos"]:
            hoja[f"U{fila}"] = linea["nitratos"]
        fila += 1

    # La nota al pie, con la errata del original («podrá a añadir»), justo debajo de la tabla:
    # es lo que tiene que hacer que el lector pare y no se invente una parcela más.
    hoja[f"B{fila + 1}"] = (
        "El titular podrá a añadir nuevas parcelas y/o líneas de declaración en caso de ser "
        "necesario. 1"
    )
    hoja[f"B{fila + 3}"] = "[1] Identificar el número de orden de las parcelas."


def construye() -> bytes:
    """Fabrica el cuaderno de ejemplo y devuelve el fichero **en memoria**.

    Se devuelven los bytes y no se escribe nada a propósito: así lo usan los tres sitios que lo
    necesitan sin dejar ficheros por medio — este guion, que lo guarda en `tests/datos`; los
    tests, que leen el fichero guardado; y la prueba de humo, que lo sube a un servidor de verdad
    para comprobar que todo el camino funciona con un servidor delante.
    """
    libro = Workbook()
    # `Workbook()` trae una hoja de regalo: se usa para la primera del cuaderno.
    libro.remove(libro.active)
    for nombre in HOJAS:
        libro.create_sheet(nombre)

    _hoja_general(libro)
    _hoja_parcelas(libro)

    # Fechas de ejemplo en la hoja 2.1, para probar que se leen como fechas y no como texto.
    hoja = libro[cyl.HOJA_PARCELAS]
    hoja["Q14"] = dt.date(2025, 10, 1)
    hoja["R14"] = dt.date(2026, 7, 31)

    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def main() -> None:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_bytes(construye())
    print(f"Escrito {DESTINO}")
    print(f"  {len(HOJAS)} hojas | {len(LINEAS)} líneas de parcela | campaña {ANIO}")


if __name__ == "__main__":
    main()
