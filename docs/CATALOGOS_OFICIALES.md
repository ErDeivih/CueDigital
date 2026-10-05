# Los catálogos oficiales: qué se baja, qué no, y por qué

El cuaderno tiene campos que se rellenan con **códigos oficiales** (unidades de medida, tipos de
producto, materias activas, clases de plaga, especies…). Este programa **no se los inventa nunca**:
o los baja de donde los publica la administración, con su dirección y su huella, o dice que no los
tiene. Este documento cuenta qué hay, de dónde sale y qué falta.

| Qué | Dónde |
|---|---|
| **Lo que se baja hoy** | `data/fega/`, con `LEEME.md` y `procedencia.json` |
| **El guion que lo baja** | `backend/scripts/bajar_catalogos_fega.py` |
| **Las pruebas del guion** | `backend/tests/test_bajar_catalogos_fega.py` (15 pruebas, ninguna sale a internet) |
| **Lo que no se puede bajar, y a quién se le pide** | [`FUENTES_OFICIALES_PENDIENTES.md`](FUENTES_OFICIALES_PENDIENTES.md) y [`CORREO_LISTO_PARA_ENVIAR.md`](CORREO_LISTO_PARA_ENVIAR.md) |

---

## 1. Lo que se baja, y de dónde

Comprobado el **27/09/2026**, **sin captcha y sin registro**. Todo con su código HTTP, su tipo de
contenido y su huella SHA-256 en `data/fega/procedencia.json`.

**Del FEGA** (Fondo Español de Garantía Agraria), que es quien publica el diseño del cuaderno:

- El **Documento Técnico SIEX 3.11** (el diseño completo, con los catálogos).
- El **Anexo V**: la definición de las variables de REA y del cuaderno, hoja por hoja.
- El **Anexo VI**: el interfaz único común v3.11.4 — el documento del que salen el descriptor y el
  esquema JSON que ya estaban en `data/iuws_fuentes/`. **Su huella coincide** con la que ya estaba
  apuntada, así que el descriptor del programa es el del documento oficial de hoy.
- Los **Anexos VIII, IX y X**: los modelos de autorización y el procedimiento.

**Del MAPA**, del buscador del Registro de Productos Fitosanitarios (`servicio.mapa.gob.es/regfiweb`):

- **15 tablas de codificación**: unidades de medida, frases de prudencia (las «P»), clasificaciones,
  riesgos (las «H»), utilizaciones, ámbitos, funciones, tipos de preparado, tipos de usuario, sistemas
  de cultivo, coformulantes, acciones, translocaciones, métodos de aplicación y tipos de sustancia.
- El **listado completo de productos registrados**: 3.087 filas, el registro oficial entero.
- La **clasificación oficial de plagas** (5 hojas: malas hierbas, artrópodos y gasterópodos,
  enfermedades y reguladores) y la **jerarquía de especies vegetales**, que es como se llama
  oficialmente cada cultivo.

> **Cómo se entra, dicho claro.** El buscador del MAPA **no tiene captcha y no hace falta entrar**: lo
> único que hace el guion es **la misma petición que hace su propia página** cuando alguien pulsa el
> botón de exportar (está leído de su propio `site.min.js`: un `POST` a
> `/regfiweb/Exportaciones/ExportExcel`). Se va **despacio** (una petición cada dos segundos), con un
> cliente que **se identifica**, y **no se modifica nada**: solo se descargan ficheros. Se comprobó
> además el `robots.txt` de los tres dominios antes de empezar, y ninguna de estas direcciones está
> prohibida.

---

## 2. Lo que NO se baja, y por qué

Esto es la parte importante de este documento.

### 2.1 Los valores de los catálogos de SIEX (detrás de un captcha)

Es el catálogo que hace falta para el volcado oficial: los **códigos numéricos** de producto, unidad
de medida, justificación, eficacia… Están en el portal público del FEGA, y **detrás de un captcha de
Google** (reCAPTCHA). Comprobado por los dos lados:

- En el **código del propio portal**: carga `recaptcha/api.js` y usa `ngx-captcha`; la descarga del
  ZIP de catálogos exige el token que emite el navegador.
- En los **documentos oficiales**: el Anexo VII del Documento Técnico **solo enlaza al portal**; no
  publica los valores.

**No se pasa el captcha.** Saltarse un captcha es saltarse la norma de una web, y este programa no lo
hace. Lo que sí se tiene es la **estructura** de esos catálogos (nombres y columnas de las 287
tablas), que es pública y se baja con `scripts/bajar_catalogos_siex.py`. **Los valores hay que
pedirlos**, y el correo ya está redactado.

### 2.2 Lo que exige certificado

El interfaz de la Junta (IUWS) exige certificado de cliente y alta como empresa. Eso se prueba aparte,
a mano, con `scripts/probar_iuws.py`; lo que contesta está en [`INTEGRACION_IUWS.md`](INTEGRACION_IUWS.md).

### 2.3 Lo que no se guarda porque no se puede ni abrir

El fichero de **autorizaciones excepcionales** del MAPA (33 MB) es un Excel **antiguo** (`.xls`), y
este proyecto solo sabe leer los modernos (`.xlsx`). Se descarga, pero **no se guarda**: guardar un
fichero que no se puede leer es guardar algo que nadie va a poder comprobar. Si algún día hace falta,
se añade el lector y se prueba.

### 2.4 Lo que su `robots.txt` prohíbe

El buscador interno del FEGA (`/search/site`) está prohibido expresamente para los rastreadores. **No
se usa.** Hay una prueba que revienta si alguien mete esa dirección (o la del captcha, o la del portal
con contraseña) en cualquier constante de descarga del guion.

---

## 3. Dos catálogos que se llaman parecido, y no son lo mismo

Es el error caro, y por eso está avisado en la primera línea del `LEEME` de la carpeta:

| | `Unidades` | `UNIDADES_MEDIDA` |
|---|---|---|
| **Quién lo publica** | El MAPA, en el registro de productos fitosanitarios | El FEGA, en SIEX (el cuaderno) |
| **Para qué** | Las unidades del registro de fitosanitarios | Las unidades de medida del cuaderno oficial |
| **¿Se puede bajar?** | **Sí**, está en `data/fega/mapa_unidades.xlsx` (124 filas) | **No**: sus valores están detrás del captcha |

**Parecerse no es ser.** Este proyecto tiene esa regla escrita desde el principio (`catalogos_siex.py`):
una correspondencia solo vale si los dos nombres son **exactamente iguales**. Mezclar estos dos
catálogos sería meter un código del MAPA donde el cuaderno espera uno del FEGA, y el volcado se
rechazaría… o peor, se aceptaría mal.

---

## 4. ¿Siguen siendo los oficiales? (la comprobación que se puede repetir)

Un dato oficial bajado **no se queda quieto**: la administración publica una corrección, cambia un
listado o añade municipios, y el programa seguiría con la copia vieja **sin que nadie se entere**. Y
peor: la documentación que da cifras («387 municipios y 24 zonas») dejaría de ser verdad en silencio.

Para eso está `backend/scripts/comprobar_fuentes_oficiales.py`:

```bash
cd backend
../.venv/Scripts/python.exe scripts/comprobar_fuentes_oficiales.py
```

Vuelve a pedir **todas** las direcciones apuntadas en los `procedencia.json` y dice, una por una, si
siguen siendo las mismas. Termina con código 1 si alguna ha cambiado, para que se note.

**Y no compara siempre lo mismo, porque no todas las fuentes son iguales:**

| Clase de fuente | Cómo se comprueba | Por qué |
|---|---|---|
| Un **fichero publicado y quieto** (una norma, un anexo, el Excel de zonas vulnerables) | **Su huella SHA-256** | Si cambia un byte, ha cambiado el dato |
| Un **listado que el servidor genera cada vez** (las exportaciones del registro de fitosanitarios del MAPA) | **Cuántas filas trae** | Lleva dentro la hora en que se generó, así que **su huella cambia aunque los datos sean los mismos**. Comparando la huella saldría «ha cambiado» todos los días, y un aviso que salta siempre es un aviso que se deja de mirar |

**Comprobado el 27/09/2026:** las **26 fuentes** siguen siendo las mismas. Entre ellas, el Excel de
zonas vulnerables a nitratos es byte a byte el que hay bajado (misma huella, `last-modified`
19/05/2026), así que la lista de **387 municipios y 24 zonas** sigue vigente.

> **Y esto fue lo que destapó un fallo de la propia procedencia.** La primera vez que se ejecutó, 16
> fuentes salieron como «cambiadas» y no había cambiado ninguna: eran las tablas del MAPA, que se
> generan al pedirlas. Al mirarlo se vio que la procedencia apuntaba `…/ExportExcel
> (tipoExportacion=Unidades)` —una dirección con un paréntesis que **no existe**— y que no decía que
> se pedían con POST. Se arregló: ahora la procedencia guarda **cómo se pidió** y **con cuántas filas
> se bajó**, que es lo que hace falta para poder repetir la comprobación dentro de un mes.

---

## 5. Qué falta por hacer con esto

1. **Usar los catálogos bajados donde el programa ya los necesita.** El programa tiene listas propias
   (unidades de compra, unidades de dosis, eficacia…) que hoy están escritas a mano y avisadas como
   «nuestras». Donde el catálogo oficial **coincida exactamente**, se puede pasar a usar el oficial,
   diciendo de dónde sale. **No se hace a la ligera**: hay que comparar valor por valor y decirlo.
2. **El listado de productos** (3.087 filas) permite una comprobación de verdad: la primera hoja trae
   las columnas `NumRegistro`, `Nombre`, `Titular`, `Fabricante`, `Formulado`, **`Estado`** y
   `Observaciones`. **Ya está hecha** (ronda 30): cuando un producto apunta un **nº de registro**, el
   programa lo comprueba contra el listado oficial y, si no cuadra, **avisa** —en la lista de «cosas
   que conviene que mires», junto a los avisos del carné y de la ITV—. Son tres avisos distintos y
   **ninguno bloquea nada**:

   | Qué pasa | Qué dice el aviso |
   |---|---|
   | El número no está en el registro oficial | «no aparece en el listado oficial de productos del MAPA… míralo en la etiqueta del envase» |
   | El número está, pero **no está vigente** (retirado) | Lo dice con el estado que figura en el registro, y que lo confirme con quien se lo vendió. Este es **urgente** |
   | El número está escrito de otra forma (`ES-849` por `ES-00849`) | Le dice **cómo lo escribe el registro**, en vez de decirle que no existe: una alarma falsa hace que se deje de hacer caso a las de verdad |

   **Y lo más importante:** si el listado no está bajado, el programa **no dice nada**. «No lo sé» no
   es «no existe», y un programa que asegura que un producto no existe cuando en realidad no tiene la
   lista es peor que uno que se calla. Hay una prueba para cada uno de los tres avisos y otra para
   este silencio.
3. **Pedir los valores de SIEX** (correo redactado) y, cuando lleguen, cargarlos con su procedencia.

---

## 6. Cómo se comprueba

```bash
cd backend
# Baja todo lo permitido (tarda: va despacio a propósito)
../.venv/Scripts/python.exe scripts/bajar_catalogos_fega.py

# Rehace el LEEME con lo que ya está, SIN tocar la red
../.venv/Scripts/python.exe scripts/bajar_catalogos_fega.py --sin-descarga

# Las pruebas (ninguna sale a internet)
../.venv/Scripts/python.exe -m pytest tests/test_bajar_catalogos_fega.py -q
```

Si una fuente no contesta, el guion **se para y lo dice con su dirección y su código HTTP**: nunca
deja un fichero de relleno. Y si un fichero llega con la forma equivocada (una página web donde se
esperaba un Excel), **tampoco se guarda**: eso es la firma de un captcha o de un error del servidor.
