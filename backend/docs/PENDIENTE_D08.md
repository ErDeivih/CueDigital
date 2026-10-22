# D08: lo que necesita, y por qué no se puede hacer aquí

> **Para qué es este documento.** D08 pide dos cosas que **necesitan material de fuera**: un **corpus autorizado** de
> facturas para medir el OCR, y una **fuente de meteo y satélite** con licencia. Esto es lo que hay, lo que se ha
> medido, y **lo que hay que pedir** para poder cerrarlo.

---

## 1 · El OCR: el camino funciona, el corpus no lo tengo

### Lo que hay, y está bien

*`app/ocr.py` usa **Tesseract** como **programa aparte**, no como librería de Python. Eso es una decisión escrita en el
propio módulo:*

- ***no engorda las dependencias*** (*EasyOCR o PaddleOCR son cientos de megas*);
- ***si no está, se dice y se sigue***: *el agricultor sube la foto, se guarda como justificante y teclea los datos;
  **lo que no se hace nunca es inventarse lo que pone el papel**;*
- ***y el idioma se declara en pantalla***: *sin el español, «PEÑARANDA» se lee «Pefiaranda»; **la aplicación lo dice
  en vez de disimularlo**.*

***Y hay una regla de seguridad, escrita en `app/lectura_evaluada.py`***: *«no confirmar compras/pagos ni autorización
fitosanitaria a partir del OCR **sin revisión**».*

### Lo que se ha medido (22/10/2026)

*`scripts/medir_el_ocr_por_campo.py`, con el Tesseract de esta máquina (**español**) y una factura **sintética**
—fabricada por el guion, sin datos de nadie—.*

| campo | ¿lo encuentra? |
|---|---|
| el proveedor | ✅ |
| el NIF | ✅ |
| el número de factura | ✅ |
| la fecha | ✅ |
| la base imponible | ✅ |
| el IVA | ✅ |
| **el total** | ✅ |

```
7 comprobaciones · 0 fallos
```

***Y un detalle que vale más que el 7 de 7***: *en la tabla, «Concepto» salió **«_concapto»**. **El OCR se equivoca en
letra pequeña** — que es exactamente por lo que la aplicación pide revisar y confirmar, y por lo que no confirma nada
sola.*

### ***Lo que falta, y no se puede inventar***

**El corpus autorizado.** *El encargo pide «resultados por campo» sobre facturas **de verdad**. Eso necesita:*

- *facturas reales, **con permiso escrito** de quien las emite para usarlas en la prueba;*
- *que alguien **diga qué pone** en cada campo (**el patrón**), que es contra lo que se mide;*
- *y facturas de los **tipos que llegan**: PDF de verdad, escaneado, y foto de móvil — cada uno falla distinto.*

***Una factura sintética dice que el lector lee. NO dice que lea las facturas de verdad.***

---

## 2 · La meteo y el satélite: **no hay nada en el código**

*Buscado en todo `app/`: **no hay una línea** de meteo, clima, satélite, NDVI, Copernicus ni AEMET.*

***Lo que haría falta para empezar, y el encargo ya lo exige***: *cada dato con **fuente, licencia, fecha y resolución**.
Es decir:*

- ***de dónde viene*** *el dato (el servicio y su versión);*
- ***qué licencia** tiene y **si permite** usarlo en una aplicación que se vende;*
- ***de cuándo es*** *— una predicción de ayer no es la de hoy, y un NDVI de hace tres semanas no dice cómo está el
  cultivo ahora—;*
- ***a qué resolución*** *— de parcela o de comarca no es lo mismo, y decirlo como si fuera de parcela sería mentir.*

***Nada de eso está, y nada de eso se puede inventar.*** *Hace falta **elegir un proveedor**, leer su licencia y
decidir si se puede usar.*

---

## 3 · Lo que hay que pedir para cerrar D08

| qué | para qué |
|---|---|
| **facturas reales con permiso** (*y que alguien diga qué pone en cada campo*) | *medir el OCR por campo de verdad* |
| **la decisión sobre meteo y satélite**: qué proveedor, con qué licencia | *poder construir algo que no sea un número inventado* |
| **y la revisión con visión** de las quince capturas de D05 | *está **EN_REVISION**: el modelo de esta sesión no ve imágenes* |

***Hasta entonces, D08 no está hecho, y este documento es la razón escrita.***
