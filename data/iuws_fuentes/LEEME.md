# Fuentes oficiales del IUWS — no se tocan

Estos ficheros son **documentos oficiales**, no material del proyecto. Se guardan tal y como
los publica el FEGA, **sin modificar ni un byte**, para poder demostrar de dónde sale cada
dato. **No se editan**: si hace falta derivar algo (una tabla, un resumen), se deriva a otro
fichero y se dice aquí.

## De dónde salen

Los tres vienen del mismo sitio: el **Anexo VI. Interfaz Único Común, v3.11.4**, que el FEGA
publica en su página de documentación técnica agrícola de SIEX. Y no están enlazados como
ficheros sueltos: van **incrustados dentro del Word**.

```
https://www.fega.gob.es/es/siex/documentacion-tecnica-agricola-siex
  → Anexo VI. Interfaz Único Común v3.11.4 (.docx)
      word/embeddings/Microsoft_Excel_Worksheet.xlsx   → descriptor REA
      word/embeddings/Microsoft_Excel_Worksheet1.xlsx  → descriptor CUE
      word/embeddings/oleObject1.bin                   → paquete OLE con el esquema JSON
```

El Word descargado el 22/09/2026 tiene esta huella, para que se pueda comprobar que es el
mismo documento del que se sacó todo:

```
SHA-256 del Anexo VI v3.11.4 (.docx):
8acd60aca62e002533ac8c4aa45d2ffb820fa94c849f72d11bff63474f418d5d
```

## Los ficheros, y su huella

| Fichero | Qué es | SHA-256 |
|---|---|---|
| `BdcSix-DS-DisenoCUE_3.11.4.xlsx` | **Descriptor del cuaderno CUE.** Lleva la hoja `EstructuraCuadernoWS` y la marca «Versión 3.11.4» | `eec4e809732e17cd845343db1e0b7bb51507b8878c8f6c0f4d57039cac752217` |
| `BdcSix-DS-DisenoCUE_3.11.4.schema.json` | **Esquema JSON del cuaderno** (borrador 7). Es el que se usa para validar antes de mandar | `f7be0ec1b58271936806a27a3eeb592d3e5804e218927f0f9a15d7dac9555e5f` |
| `BdcSix-DS-DisenoRegistroREA_3.11.xlsx` | **Descriptor del REA**, para cotejar las descargas | `20db35c973159241c3fc06834881286998cc3582a153aecee167cc144c52bb46` |

El nombre que tenía el esquema dentro del Word era `BdcSix-DS-DiseñoCUE_3.11.4.json` (con
eñe). Aquí se guarda como `.schema.json` y sin eñe, para que no dé guerra en ningún sistema
de ficheros. **El contenido es el mismo byte a byte**, y así se comprobó: la carga del paquete
OLE coincide exactamente con este fichero.

## Cómo se comprobó (y cómo volver a comprobarlo)

Lo que hace fiable esto no es una nota escrita a mano: es que **las huellas coinciden con las
de dentro del Word oficial**.

1. Se descarga el Anexo VI y se abre como un ZIP.
2. Se calcula el SHA-256 de `word/embeddings/Microsoft_Excel_Worksheet.xlsx` y de
   `Microsoft_Excel_Worksheet1.xlsx` y se comparan con los de la tabla. **Coinciden.**
3. El esquema no es una parte suelta del ZIP: está dentro de `oleObject1.bin`, que es un
   fichero OLE compuesto con un flujo `Ole10Native` (un «paquete» de Windows). Ese flujo
   empieza con el nombre original del fichero y la ruta del equipo que lo creó —de una persona
   del FEGA, en `C:\Users\dcollado\...`— y después lleva el JSON. El contenido de
   `BdcSix-DS-DisenoCUE_3.11.4.schema.json` es **exactamente** esa carga.

## Lo que NO hay aquí

- **Los valores de los catálogos** (los códigos de producto, unidad, justificación, eficacia…).
  El portal público de SIEX publica la **estructura** de sus 287 catálogos en
  `https://www3.sede.fega.gob.es/bdcsixpor/tablas/configJson`, y eso se puede consultar sin
  certificado, pero **los datos de cada tabla están detrás de un captcha**. No se inventan.
- **La clave privada ni ningún certificado.** Eso no entra en el repositorio: va por variables
  de entorno.
