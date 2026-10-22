# AGENTS.md — Cómo trabajar en CUE Digital

> **Este fichero es un convenio de trabajo, no una descripción del proyecto.** Se lee
> siempre, antes que nada. Si eres un agente y vas a tocar este repositorio, empieza
> aquí.

**Qué es esto, en una frase:** gestión de la explotación agraria con un cuaderno de
campo integrado. El alcance solicitado incluye despacho y campo; leer el contrato
`docs/CONTRATO_IMPLEMENTACION_CRM.md` y `docs/MATRIZ_NORMATIVA_CRM.md` junto al plan.
Las fechas legales se comprueban por obligación y supuesto, no por esta descripción.

**Quién lo usa:** un agricultor de 50 a 70 años, de pie en una parcela, con el móvil en
una mano, el sol de frente y sin cobertura. Todo lo que hagas se juzga contra esa
escena en el modo de campo. El modo de despacho también debe servir al agricultor y
a quien le ayuda: tablas, mapas, cuentas y planificación. Las restricciones antiguas
de navegación móvil no prohíben menús y secciones en escritorio. Mantener ambos modos.

---

## 1. La regla principal

**No entregues nada con los tests en rojo, y no pidas permiso para arreglarlos.**

El orden es siempre este:

1. **Mira qué tests existen YA.** La suite es el contrato. Si vas a cambiar un
   comportamiento, el test que lo cubre es lo primero que hay que leer.
2. **Implementa.**
3. **Corre los tests.** Todos.
4. **Arregla lo que se rompa.**
5. **Corre la prueba de humo** contra un servidor de verdad.
6. **Resume:** qué cambió, qué ficheros, qué tests corriste y que pasaron.

Si un cambio rompe un test: **o se arregla el cambio, o se actualiza el test explicando
por qué el comportamiento nuevo es el bueno.** Nunca borres ni desactives un test para
que pase. Si no hay test para lo que estás tocando, **escríbelo**.

---

## 2. Los tests de ESTE proyecto

```bash
cd backend

# Python (5629 tests): cálculos, registro obligatorio, textos, interfaz, contrato,
# certificado, firma, instalaciones, plan de abono, análisis, medidas preventivas, dictado,
# documentación anexa, el cliente del interfaz de la Junta, la comprobación de la firma,
# varias cuentas dentro de una misma finca, las tierras en el mapa y en la tabla (T06),
# las semillas y las siembras (T10), los contactos (T11) y la maquinaria (T14)
../.venv/Scripts/python.exe -m pytest

# JavaScript (1190 tests): la lógica del móvil y la interfaz, pulsando botones de verdad
node --test "tests_js/*.test.js"

# Recorrido completo contra un servidor de verdad (hay que tenerlo levantado)
../.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000   # en otra terminal
../.venv/Scripts/python.exe scripts/humo.py http://127.0.0.1:8000
```

En Windows, el intérprete es `../.venv/Scripts/python.exe`; en Linux,
`../.venv/bin/python`. Si no existe el entorno:

```bash
cd backend && python -m venv ../.venv && ../.venv/Scripts/python.exe -m pip install -r requirements.txt
```

| Fichero | Qué garantiza |
|---|---|
| `tests/test_legal.py` | Los cálculos: días de espera, abono puro, dosis, vigencias |
| `tests/test_geo.py` | Centro de la parcela y distancia entre parcelas |
| `tests/test_sin_jerga.py` | Ningún texto lleva jerga, y los avisos dicen qué hacer |
| `tests/test_registro_obligatorio.py` | Los casos de aceptación, de punta a punta |
| `tests/test_interfaz.py` | La pantalla se sirve, con su tipo, sin jerga, y **ninguna pregunta se queda en blanco** (ni en la aplicación ni en la copia de textos que usan los tests del móvil) |
| `tests/test_design_md.py` | El contrato de diseño y el CSS dicen lo mismo |
| `tests/test_borradores.py` | El dictado entiende y, sobre todo, no inventa |
| `tests/test_certificado.py` | El certificado: leerlo, y **no creerse una cabecera falsificada** |
| `tests/test_firma.py` | La firma: que la huella sea estable y que se note si algo cambia después |
| `tests/test_instalaciones.py` | Las naves y las clases de tratamiento (parcela, semilla, postcosecha, nave) |
| `tests/test_plan_abonado.py` | El plan de abono, su comparación, y **que actualizar no reviente** |
| `tests/test_analiticas.py` | Los análisis: el catálogo como puerta, el boletín subido sin salirse de su carpeta, y el enganche con el plan |
| `tests/test_medidas_preventivas.py` | Las medidas de la finca: que lo declarado alimente el apunte de cada tratamiento, y que desmarcar no borre |
| `tests/test_lista_de_la_junta.py` | Que la lista de lo que falta **sume 21** y que los números de la documentación no se queden viejos |
| `tests/test_cosecha_comercializada.py` | Lo que se vende: que cuadre con lo cosechado, y que una unidad de lechugas no se sume con kilos |
| `tests/test_iuws.py` | El IUWS: las direcciones del anexo, los 19 mensajes, y **que lo que no se sabe no se inventa** |
| `tests/test_asesor_semilla_y_agua.py` | El asesor, la semilla y el agua de riego: las tres últimas secciones que estaban a medias |
| `tests/test_seguridad_de_las_claves.py` | Que el atajo de la suite (bajar las iteraciones de la clave) **no se pueda colar en producción** |
| `tests/test_sigpac.py` | El conector del SIGPAC: el parser contra una respuesta **de verdad** guardada, los 933 productos oficiales, y que sin cobertura se diga |
| `tests/test_nitratos.py` | Las reglas de la zona de nitratos: el tope de 170 kg, la pendiente del 15 %, y que lo que no se sabe se diga |
| `tests/test_cuaderno_cyl.py` | El cuaderno de la Junta (el Cuecyl): que se lea lo que pone el papel, que **subirlo dos veces no duplique ninguna tierra**, y que no se pise lo que el agricultor ya había escrito |
| `tests/test_facturas.py` | Las facturas: leer un PDF y una foto, que las cuentas cuadren o se avise, y que lo comprado salga de las facturas |
| `tests_js/nucleo.test.js` | Números en castellano, cola sin cobertura, repetir |
| `tests_js/interfaz.test.js` | `app.js` arranca y **los botones llevan a algún sitio** |

**Mínimo antes de dar algo por terminado:** que pase `pytest` y que pase
`node --test`. Si has tocado algo que se ve en pantalla, además la prueba de humo.

> **La suite tiene que seguir siendo rápida.** Estuvo en seis minutos porque cada test creaba
> y tiraba las 21 tablas, y eso son 422 ms por test. Ahora el esquema se crea una vez por
> sesión y cada test vacía las tablas (~20 ms), y la clave se deriva 1.000 veces en vez de
> 240.000. Son **30 segundos**. Si alguien vuelve a meter algo que tarde medio segundo por
> test, se verá aquí: una suite lenta se deja de ejecutar, y una suite que no se ejecuta no
> protege nada.

---

## 3. Las reglas que no se doblan

Cada una tiene su motivo y su test. Si vas a saltarte una, entiende primero por qué
está.

### 3.1. Cero jerga en lo que lee el agricultor

Palabras prohibidas en pantalla: *error, validación, cumplimentar, epígrafe,
dosificación, trazabilidad, interfaz, sincronizar, sesión, campo obligatorio, operación
cultural, fitosanitario, DGC, UHC*. La lista viva está en `app/textos.py`
(`PALABRAS_PROHIBIDAS`) y **la comprueban tres tests**.

- **Todo el texto que ve el agricultor vive en `backend/app/textos.py`.** No en los
  routers, no en el HTML, no en el JavaScript.
- Si escribes un texto en `app.js`, `test_el_javascript_no_lleva_jerga_en_sus_textos` lo
  caza. Si lo escribes en un router, deja de estar cubierto: por eso los mensajes se
  piden con `textos.mensaje("CODIGO")`.
- Si añades un texto nuevo, **añádelo a `textos.py` y a `textos_visibles()`** para que el
  test lo revise.

### 3.2. `DESIGN.md` es el contrato de la interfaz

- Se lee antes de tocar nada visual. Es la especificación oficial de
  [google-labs-code/design.md](https://github.com/google-labs-code/design.md).
- **Todos los colores viven en `:root` de `estilos.css` y en ningún otro sitio.** Hay un
  test que cuenta los colores sueltos que quedan fuera.
- Si cambias un token, un tamaño o una regla: **cámbialo en los dos ficheros**. Si no,
  `test_design_md.py` se pone rojo, que es justo lo que tiene que pasar.
- El validador oficial debe seguir dando **0 errores y 0 advertencias**:

  ```bash
  npx --yes -p "@google/design.md" designmd lint DESIGN.md
  ```

  (En Windows, usa el alias `designmd`: el sufijo `.md` choca con la asociación de
  ficheros.) **Los tests no llaman a ese comando a propósito**: un test que necesita
  Node, npm y conexión no es un test, es una lotería. Lo mismo se comprueba en Python.

### 3.3. Nada se inventa

- **Un dato que no se sabe queda en blanco.** Nunca se rellena "algo parecido".
- La zona vulnerable a nitratos vale `None` ("no lo sé") si no hay listado o faltan
  código INE y pareja municipio/provincia. El listado municipal del Decreto 5/2020 está
  cargado desde IDECyL; nunca se deduce la provincia solo del nombre del municipio.
- Al crear una parcela manual tampoco se copia el municipio de la explotación: puede
  estar en otro lugar. El formulario pide municipio y provincia opcionales; sin
  ubicación propia se conserva `None`, aunque el listado esté cargado.
- Si el listado oficial dice que sí, **manda sobre lo que diga el agricultor**. No es
  una opinión suya.
- Los anexos III y V de la Orden MAV/398/2022 están cargados. Solo el III produce un
  aviso no bloqueante cuando zona, cultivo y sistema coinciden exactamente; las notas,
  excepciones y los periodos relativos del V requieren revisar el caso.

### 3.4. Nada se borra

- Los apuntes se **anulan con un motivo** (`anulado` + `motivo_anulacion`) y queda el
  rastro en la tabla `auditoria`. Un cuaderno editable sin huella no sirve en una
  inspección, que es justo para lo que existe.
- Los datos de la etiqueta **se copian al apunte**: si mañana se corrige la ficha de un
  producto, el apunte histórico no puede cambiar con él.

### 3.5. Aislamiento entre fincas

- **`explotacion_id` va en todas las tablas de negocio.** Es lo que impide que un
  agricultor vea los datos de otro. Si añades una tabla y se te olvida, se rompe.
- Todo se consulta pasando por `obtener_de_la_explotacion()` (que devuelve **404, no
  403**, para no filtrar si un identificador existe en otra finca).

### 3.6. Cálculos legales aislados

- `app/legal.py` son funciones **puras**, con tests propios, sin base de datos ni
  servidor. Si un cálculo está mal, el agricultor puede perder una cosecha.
- `app/validaciones.py` son las reglas que impiden guardar algo ilegal. Devuelven
  `Aviso(codigo, mensaje, bloquea, campo)` con el mensaje **ya escrito**.

### 3.7. La pantalla no se compila

- Son ficheros servidos por el propio programa. **No hay compilación de producción**;
  el proyecto ya utiliza React UMD y componentes en `web/react/`. No introducir otra
  cadena de compilación como consecuencia automática del rediseño.
- El motivo no es pereza: el servidor donde se instale no tiene por qué tener Node, y en
  un móvil con mala cobertura una página ligera se abre y medio megabyte no.
- **Los tipos MIME se declaran a mano en `main.py`.** En Windows, Python los saca del
  registro y un `.js` puede salir como `text/plain`; el navegador entonces **rechaza el
  módulo** y la pantalla se queda en blanco sin decir por qué.

### 3.8. El dictado y cualquier modelo futuro no escriben en el cuaderno

- `POST /api/borradores/desde-texto` **devuelve una propuesta**, no guarda nada. Hay un
  test que lo comprueba.
- `BorradorSalida` (en `schemas.py`) **es el contrato** para cualquier modelo. Si algún
  día se enchufa uno, tiene que devolver exactamente eso y el agricultor lo confirma.
- **Regla de oro del dictado:** *"dos litros"* puede ser la dosis por hectárea o el total
  empleado. Confundirlos es un error de diez veces. Si no está claro, se apunta lo oído
  con `campo: null` y se pregunta.

### 3.9. Actualizar no puede romper nada

- **`crear_tablas()` añade las columnas que falten a las tablas que ya existen.** Hace
  falta porque `create_all` crea tablas nuevas pero **no toca las que ya están**: sin
  esto, al añadir un campo el programa arranca bien y después revienta con un «no such
  column» delante del agricultor.
- **Si añades una columna nueva a una tabla, no tienes que hacer nada más**: se añade
  sola al arrancar, con el valor por defecto de Python. Si es obligatoria y no tiene
  valor por defecto, no se puede añadir en SQLite y aparece en la lista de «imposibles».
- Hay tests que crean una tabla a la antigua y comprueban que se pone al día.

### 3.10. Lo que sube el agricultor no va a la base de datos ni al repositorio

Vale para los boletines de laboratorio, y valdrá para las fotos de etiquetas y de
albaranes.

- **El fichero va al disco; en la base de datos solo queda la referencia** (nombre, ruta
  relativa, tipo y tamaño). Un boletín con fotos son varios megas, y meterlo en una columna
  hace que la copia de seguridad del agricultor deje de poderse manejar.
- **El nombre del fichero que manda el navegador NUNCA se usa como ruta.** La ruta la pone
  el programa: carpeta por finca y nombre por identificador más un aleatorio. Un nombre
  como `../../app/main.py` escribiría fuera de su carpeta. Hay un test que lo comprueba
  **mirando el disco**, no confiando en el código.
- **La carpeta está en el `.gitignore`.** Son papeles del agricultor, con su NIF. Se cambia
  de sitio con `CUEDIGITAL_ADJUNTOS`, que es lo que hace falta en el servidor de verdad.
- **Los tests no escriben nada fuera de una carpeta temporal.** `conftest.py` fija
  `CUEDIGITAL_DATABASE_URL` **y** `CUEDIGITAL_ADJUNTOS` antes de importar nada de `app`. Lo
  segundo se descubrió limpiando: sin fijarlo, cada ejecución de la suite dejaba boletines de
  laboratorio de verdad en `backend/datos/adjuntos`, y no daba ningún fallo. Un test que
  ensucia el disco de quien lo ejecuta es un test que acaba mintiendo.

---

## 4. Recetas

### Añadir un campo a un registro

1. Columna en `models.py`.
2. Si es de entrada, en `schemas.py`.
3. Si se calcula o se valida, en `legal.py` o `validaciones.py`.
4. Pregunta y pista en `textos.py` (`ETIQUETAS`), y ayuda en `AYUDA` si hace falta.
5. Paso en el asistente de `app.js`.
6. **Test** del cálculo o de la regla, y caso en `test_registro_obligatorio.py`.
7. Si sale en el papel, en `routers/cuaderno.py` (PDF y CSV).

### Añadir un mensaje al agricultor

1. Clave y texto en `textos.MENSAJES`. Estructura obligatoria: **qué pasa + qué hago
   ahora**.
2. Si lleva huecos `{asi}`, `test_cada_mensaje_se_puede_rellenar` comprobará que se
   rellenan.
3. Si **bloquea**, `test_los_mensajes_que_bloquean_dicen_que_hacer` exige que lleve una
   instrucción. No vale describir el problema y callarse.
4. Si cuenta cosas, **singular y plural** (`_uno` / `_varios`): "1 apuntes" es lo primero
   que hace desconfiar de un programa.

### Añadir una pantalla

1. Vocabulario en `textos.py` (nunca en `app.js`).
2. Función `pantallaX()` que llama a `pintar(html)`.
3. Botones con `data-accion`, y su rama en el manejador de clics.
4. Ayuda por campo si pide datos.
5. Test en `tests_js/interfaz.test.js` que **pulse el botón** y compruebe que llega.
6. Lee §5 abajo antes de darla por buena.

### Añadir un registro nuevo (una tabla)

1. Modelo con `explotacion_id`.
2. Esquema de entrada y de salida.
3. Router con `obtener_de_la_explotacion`.
4. Validaciones en `validaciones.py` si la ley impone algo.
5. Salida en el PDF y en el CSV.
6. Pantalla, siguiendo la receta de arriba.
7. Caso de aceptación en `test_registro_obligatorio.py` **y** en `scripts/humo.py`.

### Encadenar un registro con otro

Cuando dos secciones del cuaderno dicen lo mismo desde dos sitios distintos —el plan y los
abonos, el análisis y el plan, las medidas de la finca y las de cada apunte—, hay una regla
que ya se ha aplicado tres veces y conviene repetir:

1. **Que uno alimente al otro, no que se copien.** Lo declarado en la finca **ya sale
   marcado** al apuntar; el plan **lee** el análisis. Copiar de un sitio a otro en el momento
   de guardar escribe en el cuaderno algo que no pasó ese día.
2. **Un aviso, nunca un bloqueo, cuando falta el otro lado.** El agricultor puede apuntar hoy
   y rellenar la otra sección mañana.
3. **Que el aviso diga dónde se arregla**, con el nombre exacto de la pantalla.
4. **Una prueba que lo ate**, y otra que compruebe que **no se pisan**: el apunte guarda lo
   de ese día aunque después cambies lo de la finca.

### Guardar un dato del cuaderno

Regla que ya se ha aplicado tres veces (plan de abono, análisis, semilla y agua): **si la
norma pide un dato con nombre y número, va en su propia columna, no dentro de un JSON de
texto libre.**

- `Labor.detalles` era un JSON y ahí un dato no se puede consultar, no se puede sumar y no se
  puede volcar. Los campos de siembra y de riego se sacaron a columnas y ahora tienen su
  número de campo del contenido mínimo.
- El JSON se queda para lo que de verdad no encaja en ningún sitio, y no como cajón de sastre.
- Un campo vacío se guarda como `None` («no lo sé») y **no** como `0` («es cero»). En un
  volcado oficial esa diferencia es la que hace que un dato sea verdad o mentira.

### Que un dato que existe tenga puerta, y que la puerta esté probada

El fallo que más se repite en este proyecto no es un cálculo mal hecho: es **un dato que el
programa ya guarda y que el agricultor no puede meter por ningún sitio**, o una pantalla que
existe y que ningún test mira. Dos formas concretas, las dos encontradas de verdad:

- **Un campo en el modelo sin pantalla que lo pregunte.** El anexo II pedía el cultivo del año
  anterior y si se había usado una herramienta para el plan, y las dos columnas existían sin
  que nadie las preguntara. Cerrar un hueco así es **añadir la pantalla**, no solo el campo.
- **Una pregunta que el test pinta en blanco.** Los tests de JavaScript usan una copia de los
  textos de la interfaz (`tests_js/interfaz.test.js`). Si una clave no está en esa copia, la
  pregunta sale vacía en el test y **el test da por bueno cualquier cosa**. Pasó con
  `plan.herramienta`: el test buscaba la pregunta, no la encontraba, y en vez de avisar se
  plantaba en el resumen del asistente.

Para que no vuelva a pasar sin que salte, en `tests/test_interfaz.py` hay dos guardianes que
**no llevan ninguna lista a mano**: sacan las claves del propio `app.js`.

- `TestCadaPreguntaTieneSuTexto`: todas las claves del mapa de campos tienen su pregunta escrita.
- `TestLasPreguntasDelAsistenteEstanYSeComprueban`: las preguntas de las pantallas del asistente
  (`et("clave")`, `pi("clave")`, `t("etiquetas.clave.pregunta")`) **se sirven** y **están en la
  copia del test**, y la copia dice **la misma pregunta** que la aplicación.

> Cuando añadas una pantalla al asistente, estos tests te van a pedir dos cosas: el texto en
> `textos.py` y la línea en la copia del test. No son trámites: son las dos formas que tiene
> esta aplicación de quedarse con una pregunta en blanco delante del agricultor.

### Leer un fichero oficial: por la etiqueta, nunca por la letra de la columna

El cuaderno digital de Castilla y León (el Cuecyl) se lee en `app/cuaderno_cyl.py`, y de ahí salen
tres reglas que valen para cualquier fichero que publique una administración:

1. **Se busca cada dato por el texto de su etiqueta o de su cabecera** («Superficie Cultivada (ha)»,
   «Término municipal»), nunca por «la columna L» ni por «la fila 14». La plantilla de la Junta
   **cambió entre 2024 y 2025** (23 hojas y luego 25), y con coordenadas fijas la lectura se rompe
   en silencio y devuelve datos de otro sitio.
2. **Ojo con «la celda de al lado».** En la hoja 1.1, el «Nº Registro de Explotaciones Nacional»
   está vacío y a su derecha está **la etiqueta** del autonómico: leyendo el primer valor que
   aparezca hacia la derecha, el número autonómico acababa apuntado como nacional. Hay que parar
   cuando lo siguiente que hay es otra etiqueta.
3. **En blanco es «no lo sé».** La casilla de zona de nitratos viene marcada con «Sí» en las
   parcelas que lo están y **en blanco en todas las demás**. Un `False` ahí sería una comprobación
   que nadie ha hecho.

> Y una trampa de la interfaz que costó un test: **pintar la pantalla borra la casilla del
> fichero**. Si el fichero que ha elegido el agricultor solo vive en el `<input>`, al repintar
> (para poner «Abriendo el cuaderno…») se pierde y la pantalla dice que no ha elegido nada. El
> fichero se guarda en el estado **antes** de repintar.

### Leer un documento que llega como foto o como PDF

Las facturas (`app/facturas.py`) se leen del PDF, del escaneo o de la foto, y de ahí salen cuatro
reglas que valen para cualquier lectura de un papel:

1. **Primero el texto de verdad, y el OCR solo si no hay.** Un PDF del proveedor trae las letras
   dentro: se leen con `pdfplumber`, sin equivocarse. Solo si el PDF no tiene letras (es un escaneo)
   o si es una foto se llama al lector de letras.
2. **La aritmética es la prueba.** cantidad × precio = importe, la suma de las líneas = la base,
   base + IVA = total. Cuando no cuadra, **se dice en la pantalla**. Es lo que convierte una lectura
   en algo que se puede revisar: un número mal leído de la columna de al lado se caza solo.
3. **Lo que se lee es una propuesta, nunca un dato.** Se enseña todo para que el agricultor lo
   corrija antes de guardar. Eso es lo que permite usar una foto hecha con el móvil.
4. **Sin lector de letras instalado, se dice.** No se inventa nada: la factura se guarda como
   justificante y los datos se escriben a mano. El lector es un programa aparte (Tesseract) y sus
   idiomas viven en `data/ocr/tessdata`, que se usa con `TESSDATA_PREFIX` **sin tocar la instalación
   del sistema**.

> **El lector de letras lee distinto según el idioma, y eso rompe expresiones.** Con el inglés,
   «FACTURA Nº 2026/00123» se leía bien; con el español instalado, el mismo papel salió como
   «FACTURA N* 2026/00123» y el número de factura se perdía. La expresión que lo busca admite ya las
   formas en que el lector escribe el masculino ordinal (`Nº`, `N*`, `N.º`, `NUM.`). **Cuando se
   cambie el idioma del lector, hay que volver a probar la lectura con una foto de verdad.**

### Un campo que existe y una puerta que lo rechaza

La cuarta vez que aparece la misma familia de fallo, y ahora con una forma nueva: **el dato estaba en
el modelo, la pantalla lo preguntaba y el endpoint lo rechazaba**. Al añadir a `Explotacion` los datos
de la portada del cuaderno (nº de registro, dirección, localidad, código postal, teléfono, correo),
`PUT /api/mi-finca` seguía teniendo su lista blanca de campos permitidos **escrita a mano**, así que
contestaba «No se pueden cambiar estos datos»… y la portada del cuaderno salía en blanco.

> **Cuando añadas un campo a un modelo que se edita desde una pantalla, busca su endpoint.** En este
> programa hay sitios donde los campos sí se copian solos (`**datos.model_dump()`) y sitios donde hay
> una lista a mano. Los de la lista a mano no avisan: el dato se pierde en silencio, y el único
> síntoma es un hueco en un papel. Lo encontró el test que escribe el cuaderno y comprueba la portada.

### Los guardianes de los tests también se prueban

Dos veces en este proyecto un test que **revisa** otros ficheros ha resultado estar mirando mal, y las
dos veces se arregló el test y se le escribió su propia prueba (están en `tests/test_interfaz.py`):

- `quita_comentarios_js` quitaba los comentarios de `app.js` con una expresión regular. Al encontrarse
  un `/*` dentro de unas comillas —`accept=".pdf,image/*"`— se comía **todo** hasta el siguiente `*/`,
  y lo que se comía **no se revisaba**. Ahora es un recorrido que respeta las cadenas y las
  expresiones regulares (`.replace(/"/g, …)` también lo rompía, por la comilla de dentro).
- El que saca de las plantillas el texto que ve el agricultor cortaba las expresiones con llaves
  dentro y metía código en la revisión de jerga. Ahora cuenta llaves y salta las cadenas de dentro.

**La regla que sale de ahí: si un test lee ficheros y los interpreta, ese test necesita su propia
prueba.** Un test que se come el fichero es peor que no tenerlo, porque da la sensación de que revisa.

### Cuando algo oficial se puede consultar por internet

El SIGPAC (ronda 10) demostró que a veces lo que parecía imposible **sí se puede conseguir**:
servicios públicos, sin autenticación, con dirección documentada. Antes de dar algo por perdido,
busca si el organismo lo publica.

1. **Se busca la dirección en el documento oficial**, no se prueba a adivinar rutas. El orden de
   los parámetros de `recinfo` sale del ejemplo del documento del FEGA.
2. **Se llama de verdad una vez y se mira la respuesta.** Lo que devuelve el servicio se guarda
   como ejemplo en `data/`, y **el parser se escribe contra eso**, no contra lo que uno supone.
3. **Los tests no salen a internet.** Prueban el parser contra el ejemplo guardado. Un test que
   depende de que el servicio de otro esté disponible es una lotería.
4. **La prueba de humo sí sale a internet**, y es donde se descubre que el servicio ha cambiado.
   Ahí sí se comprueba que el FEGA sigue contestando como dice su documento.
5. **Si una lista oficial tiene los códigos que faltaban, se usa.** El catálogo de productos del
   SIGPAC (933) rellenó el hueco que el descriptor del IUWS dejaba abierto. Y lo que no esté en
   la lista sigue saliendo **vacío**, nunca con un valor parecido.

**Y una quinta cosa, que se aprendió en la ronda 12: llama a la dirección oficial entera, aunque
creas que no puedes.** El IUWS parecía inalcanzable sin certificado, y resulta que **el método
de versión no está securizado**: contesta hoy, sin nada configurado. Eso fue lo que permitió
comprobar de una vez que los siete métodos existen, que el certificado lo exige el servidor, y
—esto es lo que más valía— que **la dirección que trae el programa por defecto no publica los
métodos** (da 404), con lo que la prueba de conexión decía «404» y parecía culpa de quien la
leía. Lo comprobado se apunta **en el programa** (`iuws.COMPROBADO_CONTRA_EL_INTERFAZ`,
`iuws.COMPROBADO_ENTORNO_INTEGRACION`) para que no se olvide y para que un test falle si alguien
cambia una dirección sin volver a llamar.

> **Corolario que vale para todo lo que venga:** el estado HTTP no dice si ha ido bien. El
> interfaz de la Junta contesta `200` con un cuerpo de error dentro. Hay que leer el cuerpo.
> Esto se encontró con un test y estaba a punto de quedarse como «comunicación establecida».

### Cuando algo oficial no se puede hacer entero
Ya ha pasado tres veces: el listado de zonas vulnerables, los límites de nitrógeno de la
Orden MAV/398/2022 y los valores de los catálogos oficiales. La receta es siempre la misma y
**no se negocia**:

> **Y una lección que costó una ronda entera:** el descriptor del cuaderno se dio por perdido
> durante semanas («lo tendrá que mandar FEGA»). Estaba **incrustado dentro del propio Word
> del Anexo VI**, en dos libros Excel y un paquete OLE con el JSON. Antes de declarar que algo
> oficial no existe, **mira dentro del documento oficial**, no solo los enlaces de la página.

1. **Se implementa todo lo que sí está documentado**, y se prueba contra los ejemplos del
   documento oficial. En el IUWS, por ejemplo, las seis direcciones salen literales del anexo
   y hay un test por cada ejemplo.
2. **Lo que falta se declara**, con lo que es, para qué hace falta y **de quién depende**
   (`iuws.QUE_FALTA`, `catalogos.es_zona_vulnerable` devolviendo `None`).
3. **Lo que falta no se rellena con un valor por defecto.** Un `None` («no lo sé») y un `False`
   («no») no son lo mismo; un campo de catálogo vacío y un código inventado tampoco.
4. **Se dice en la pantalla y en la documentación**, no solo en un comentario del código.
5. **Se escribe el test que impide que alguien lo "arregle"** rellenándolo con algo que parece
   razonable. Ver `test_iuws.py::TestElPaqueteNoSeHacePasarPorElVolcado`.

> El motivo de tanto cuidado: un dato inventado en un volcado oficial no da error al
> generarlo. Da error meses después, delante de un inspector, y entonces nadie sabe de dónde
> salió.

### Comprobar algo que viene de fuera (una firma, un fichero, una respuesta)

La regla que salió de la ronda 12, cuando se empezó a comprobar la firma del cuaderno:

1. **Lo que llega de fuera se abre y se mira, no se guarda a ciegas.** El fichero de firma se
   guardaba sin leerlo. Se podía subir un fichero de texto o la firma de otro agricultor, y
   nadie se enteraba. Si algo entra al sistema, hay que mirarlo.
2. **Hay tres finales, no dos: bien, mal, y no lo he podido comprobar.** El tercero no se puede
   tratar como el segundo. Rechazar algo que no sabes leer es acusar a alguien de algo que no ha
   hecho: a un agricultor con certificado de curva elíptica se le guarda la firma y se le dice
   que no se ha podido comprobar. Confundirlos está prohibido.
3. **Nada de añadir librerías grandes "por si acaso".** Aquí se comprueba una firma RSA sin
   ninguna librería de criptografía, porque hace falta una potencia modular y `pow` la hace
   Python. Antes de añadir una dependencia, mira si lo que necesitas son treinta líneas.
4. **Los tests se escriben contra ficheros de verdad, no contra inventos propios.** Las firmas
   de `tests/fixtures/firma_cades/` las hizo OpenSSL. Probar un lector con ficheros escritos por
   ese mismo lector solo demuestra que eres coherente contigo mismo.
5. **Dos textos para dos lectores.** `motivo` dice qué ha pasado con los nombres de las cosas, y
   eso va a la auditoría porque sirve para investigar; `explicacion` dice lo mismo en palabras
   de agricultor, y es lo único que puede acabar en su pantalla. Esto se descubrió con el test
   de la jerga: la explicación técnica se estaba colando en el mensaje del agricultor, y el
   test la cazó.
6. **Lo que no se comprueba se declara en el propio resultado** (`cadena_de_confianza_comprobada`
   en falso, `no_comprobado` con la lista). No en un comentario: en el dato que se guarda, para
   que dentro de un año se sepa qué se miró al aceptarlo.

### Añadir algo que se mide en varias unidades

El grano se vende en kilos o en toneladas, la fruta en unidades, y el abono en kilos o litros.
Cuando un dato se puede expresar de varias maneras:

1. **Se guarda el número tal cual lo escribió el agricultor** y su unidad aparte. Lo que se
   convierte se calcula **al vuelo** (`catalogos.kilos_de_una_venta`), no se guarda: si un día
   cambia el factor, el apunte histórico no se queda mintiendo.
2. **Lo que no se puede convertir, no se convierte.** Una unidad de lechugas no pesa lo que
   dice el número, así que se queda fuera de los totales de kilos en vez de sumarse con ellos.
   Es mejor un total que significa algo que uno que mezcla peras con manzanas.
3. **Se dice en el informe que hay datos fuera del total**, o el agricultor creerá que la suma
   está mal.
4. **Los totales que se comparan entre sí se calculan siempre en la misma unidad** (kilos), o
   la comparación sería falsa sin que nadie se diera cuenta.

---

## 5. La interfaz: lo que NO se hace

Detalle completo en [`docs/GUIA_UI_UX.md`](docs/GUIA_UI_UX.md). Resumen ejecutivo:

- **CAMBIO DEL 26/09/2026, decidido por David: la interfaz se rehace en React.** Lo pidió él, con
  estas palabras: «rehaz toda la ui con react aunque haya que rehacer pruebas». Se hace así, con
  estas condiciones, y los motivos de la regla anterior (que están en
  [`docs/UI_Y_AGENTES.md`](docs/UI_Y_AGENTES.md)) siguen siendo válidos y hay que respetarlos:

  1. **La aplicación tiene que seguir funcionando sin cobertura** y sirviéndose como ficheros
     estáticos desde el mismo servidor. Si React lo rompe, no vale.
  2. **Los textos siguen viviendo en `textos.py`.** React no cambia eso: los componentes los piden por
     `/api/interfaz` igual que ahora.
  3. **El contrato de diseño sigue mandando**: `DESIGN.md` con 0 errores y 0 avisos, y el mismo
     `designmd lint`. De hecho `DESIGN.md` es lo que se le sube a Stitch para que diseñe **dentro de
     nuestras reglas** (`backend/scripts/disenar_con_stitch.py`).
  4. **Las pruebas de la interfaz se rehacen, no se tiran.** Eran 200 pruebas de JavaScript que
     cargan `app.js` en un DOM de mentira y comprueban lo que se ve; al pasar una pantalla a React
     se rehacen contra el componente. **Mientras dure la migración, la interfaz vieja tiene que
     seguir funcionando**: no se puede dejar al agricultor con una pantalla a medias.
  5. **La lógica del servidor no se toca por esto.** Los endpoints, los cálculos y los textos son los
     mismos: lo que cambia es cómo se pinta.

  **La migración a React está TERMINADA (ronda 72).** Las **27 pantallas** de la aplicación son React: no
  queda ni una que se pinte con `innerHTML` (la función `pintar()` se borró y el único sitio que escribe en
  la pantalla es `montar()`). Las últimas fueron «mi cuaderno» (sus nueve bloques), los avisos de error y
  **el asistente de apuntar**, cuyos 65 pasos ya estaban en React y cuyo envoltorio era lo último que
  quedaba. La guía completa —por qué sin compilar, cómo se añade una pantalla, cómo se prueba y **qué
  queda sin resolver**— está en [`docs/REACT.md`](docs/REACT.md), y se lee antes de tocar cualquier
  pantalla. La lista de lo que está hecho vive en el propio código: `PANTALLAS_EN_REACT`, al principio de
  `backend/web/app.js`, y hay tres pruebas en `backend/tests/test_la_migracion_a_react.py` que impiden
  **volver atrás** (que reaparezca un paso con `pintar:`, que los pasos dejen de ser de React o que vuelva
  un `innerHTML` de pantallas).
- **No cambies los seis botones de la pantalla de inicio**, ni su orden. Lo que funciona,
  no se mueve.
- **No escribas un texto para el agricultor fuera de `textos.py`.**
- **No uses el color para informar en solitario**: todo lo que dice el color lo dice
  también una palabra o un icono.
- **No añadas sombras, degradados, transparencias ni animaciones.** Al sol no se ven y
  en un móvil barato cuestan.
- **No bloquees un apunte por un campo opcional.** Se guarda y se avisa.
- **No dejes al agricultor sin salida.** Si le dices que le falta algo, dale el botón que
  lo arregla. Esto ya estuvo mal una vez: la aplicación decía "añade tu primera parcela"
  sin dejar hacerlo.

---

## 6. Mapa del proyecto

```
DESIGN.md                    El contrato de diseño. Se lee antes de tocar la interfaz.
docs/
├── GUIA_UI_UX.md            Cómo debe ser la interfaz. Patrones, recetas y comprobaciones.
├── REACT.md                 La migración de la interfaz a React: por qué sin compilar, qué
│                            pantallas están hechas y cuáles no, cómo se añade la siguiente,
│                            cómo se prueba y lo que queda por resolver. Se lee ANTES de tocar
│                            una pantalla.
├── UI_Y_AGENTES.md          Generative UI, agentes y qué se descarta, con motivos.
├── QUIEN_ENTRA_EN_LA_FINCA.md  Varias cuentas en la misma finca: quién manda (el titular y los
│                            ayudantes), en qué finca se está trabajando, por qué cambiar de
│                            finca cambia el vale, y las cuatro puertas del servidor. Se lee
│                            ANTES de tocar los accesos o el aislamiento entre fincas.
├── INTEGRACION_IUWS.md      El volcado oficial a la Junta: qué hay, qué falta y de quién.
├── FUENTES_OFICIALES_PENDIENTES.md  Fuentes, lagunas y consultas concretas a FEGA y CyL.
├── LO_QUE_OBLIGA_LA_LEY.md  Qué obliga la ley y qué no, con comillas literales del BOE.
├── SERVICIOS_DEL_SIGPAC.md  Los mapas y las once consultas oficiales del SIGPAC, con su
│                            dirección exacta y lo que devuelve cada una. Se lee ANTES de
│                            tocar el mapa o de pedir un dato al SIGPAC.
├── LO_QUE_SE_APUNTA_POR_TIERRA.md  Qué se apunta de cada tierra, campo por campo, y lo que
│                            falta con sus tres motivos (el código de la DGC, los catálogos que
│                            no se publican, y lo que se puede tapar aquí). Se lee ANTES de
│                            decir que el registro está completo.
└── LO_QUE_PIDE_LA_JUNTA.md  Lista verificada de lo que falta para cumplir.
backend/
├── app/
│   ├── main.py              Arranque, routers y ficheros de la pantalla
│   ├── database.py          Motor (SQLite en local, PostgreSQL/PostGIS en producción)
│   ├── models.py            Tablas
│   ├── schemas.py           Entrada y salida de la API
│   ├── legal.py             LOS CÁLCULOS LEGALES
│   ├── validaciones.py      Las reglas que impiden guardar algo ilegal
│   ├── textos.py            TODO el texto que ve el agricultor
│   ├── catalogos.py         Medidas preventivas, provincias, zonas vulnerables,
│   │                        clases de análisis y los números de cada boletín
│   ├── borradores.py        El dictado (lógica pura, sin navegador)
│   ├── certificados.py      Leer el certificado digital y sacar el NIF
│   ├── firma.py             La huella del cuaderno y la orden de AutoFirma
│   ├── sigpac.py            El conector con el SIGPAC: recintos y códigos oficiales
│   ├── iuws.py              El protocolo del volcado oficial: direcciones, mensajes, sobre
│   ├── iuws_contenido.py    El contenido mínimo del CUE, campo por campo y numerado
│   ├── iuws_cliente.py      Las llamadas al interfaz y la validación contra el esquema oficial
│   ├── iuws_descriptor.py   La tabla de campos del descriptor oficial: qué es obligatorio y
│   │                        de qué catálogo sale cada campo
│   ├── iuws_mapeo.py        Qué campo oficial sale de qué dato nuestro, y qué le falta a cada
│   │                        uno: si depende de FEGA, de una pantalla nuestra o de nadie. Y el
│   │                        mapa de los 18 bloques, sacado del esquema y del descriptor
│   ├── catalogos_siex.py    Los catálogos que publica SIEX y a cuál corresponde cada uno que
│   │                        pide el descriptor (solo si el nombre coincide exactamente)
│   ├── servicios.py         Lógica de negocio
│   ├── geo.py               Centroides, distancias y los vértices de un trozo (para el mapa)
│   ├── security.py          Claves y tokens
│   ├── mapa.py  (router)    El mapa: la foto del campo, los linderos y el toque para elegir la
│   │                        parcela. Las imágenes las sirve el programa, no el navegador.
│   â””â”€â”€ routers/             cuenta, finca, parcelas, maestros, registro, cuaderno,
│                            interfaz, borradores, firmas, plan de abono, análisis,
│                            medidas preventivas, lo que se vende, volcado oficial
├── web/                     La pantalla, sin compilación
│   ├── vendor/              React 18, ReactDOM y htm, tal y como los publica su fabricante.
│   │                        No se editan a mano: se bajan con scripts/bajar_react.py
│   ├── react/               Las pantallas escritas en React (inicio, confirmación, «mis
│   │                        cosas», «los papeles», el almacén, «qué hay sembrado», la ayuda y
│   │                        «mis datos»), `componentes.js` (el botón con su flecha, el dibujo de
│   │                        la parcela y el aviso de error) y `montar.js`, el único sitio que
│   │                        habla con ReactDOM
├── tests/                   Tests de Python
├── tests_js/                Tests de JavaScript
├── scripts/humo.py        Recorrido completo contra un servidor de verdad
├── scripts/cambiar_la_clave.py  Cambiar la clave desde este ordenador (si se olvida)
├── scripts/comprobar_en_un_navegador.py  Abre Chrome sin ventana y comprueba que la
│                                    pantalla la dibuja React de verdad (y guarda una captura)
├── scripts/comprobar_el_recorrido.py  **El recorrido del encargo, pulsando de verdad**:
│                                    Inicio → Tierras → buscar una tierra entre 64 → su ficha →
│                                    planificar un trabajo → su historial → volver a la lista. Se
│                                    hace con la explotación de 64 tierras que crea
│                                    `datos_representativos.py` y guarda una captura por paso.
│                                    Necesita un servidor: `python scripts/comprobar_el_recorrido.py
│                                    http://127.0.0.1:8029`
├── scripts/comprobar_el_armazon.py    El menú agrupado y la navegación por teclado a 390, 712,
│                                    1024 y 1440 px, con sesión de verdad
├── scripts/comprobar_escape_en_la_ficha.py  Que Escape, en la ficha de una tierra, vuelva a la
│                                    lista de tierras y no a la agenda de trabajos
└── scripts/mirar_pantallas.py     Identifica cada pantalla (ruta, elemento propio, sin formulario
                                     de entrar y con sus datos) y guarda las capturas de las cuatro
                                     pantallas × cuatro anchos, con la explotación de 64 tierras
data/zv_cyl.csv              387 municipios derivados del Excel oficial de IDECyL
data/municipios_cyl.csv      Los 2.248 municipios de Castilla y León, del diccionario del INE:
                             nombre, provincia, código INE (5 cifras) y código de municipio
                             (3 cifras, el que sale en el visor del SIGPAC). Se rehace con
                             scripts/bajar_municipios_ine.py. Con esta lista el agricultor
                             ELIGE su pueblo en vez de teclear códigos.
data/municipios_ine_fuentes/ La copia literal del diccionario del INE, con su huella y su LEEME.
data/sigpac/                 Datos OFICIALES del SIGPAC, bajados con scripts/bajar_sigpac.py:
                             933 productos, 34 usos, incidencias… y respuestas DE VERDAD
                             guardadas como ejemplo: un recinto, los recintos de una parcela,
                             el recinto que contiene un punto (el del mapa), la referencia
                             catastral de la parcela y una intersección con nitratos que SÍ y
                             otra que NO. Los tests leen de aquí: no salen a internet.
                             Para qué sirve cada servicio: docs/SERVICIOS_DEL_SIGPAC.md.
data/iuws_fuentes/           Los ficheros OFICIALES del IUWS, extraidos del Anexo VI del FEGA
                             (v3.11.4) y guardados SIN TOCAR: el descriptor CUE, su esquema
                             JSON y el descriptor REA. Su LEEME.md lleva la huella SHA-256 de
                             cada uno y de donde salen. NO se editan: si hay que derivar algo,
                             se deriva a otro fichero.
data/iuws_descriptor_cue.ejemplo.json
                             Plantilla del descriptor del cuaderno, para rellenar a mano. Se
                             copia a `iuws_descriptor_cue.json` y se rellena.
data/iuws_campos_del_cuaderno.json
                             DERIVADO de la hoja EstructuraCuadernoWS del descriptor oficial:
                             107 bloques, 402 campos, 175 obligatorios y el catálogo que pide
                             cada campo. OJO: el descriptor oficial omite la llave `{` en 14
                             cabeceras de bloque, así que hay que detectar los bloques por la
                             columna de ocurrencia (`0..n`, `1..n`), no por la llave. Se rehace
                             con scripts/sacar_campos_del_descriptor.py. Lo dice dentro de sí.
data/siex_catalogos.json     Los 287 catálogos que publica SIEX: su nombre, su identificador y
                             sus columnas. NO son los valores (esos están detrás de un captcha).
                             Se rehace con scripts/bajar_catalogos_siex.py.
datos/adjuntos/              Boletines de laboratorio subidos. EN EL .gitignore.
```

---

## 7. Trampas del entorno

- **Windows.** `Set-Content -Encoding utf8NoBOM` no existe: usa
  `[System.IO.File]::WriteAllText(ruta, texto, New-Object System.Text.UTF8Encoding($false))`.
- **`Get-Content -Raw | Set-Content` destroza los acentos.** Decodifica con la página de códigos
  del sistema y reescribe en UTF-8, así que «ó» queda como «Ã³» y el fichero deja de compilar
  (`SyntaxError: invalid character '³'`). Pasó el 11/02 con un fichero de tests y **otra vez el
  24/09 con los cuatro documentos grandes** (README, AGENTS y dos de `docs/`), por hacer un
  `-replace` de números con esta consola. Para editar ficheros con tildes, usa las herramientas de
  edición, no un `-replace` de PowerShell. Si ya ha pasado, la vuelta atrás es exacta:
  `texto.encode("cp1252").decode("utf-8")` quitando antes la marca de orden de bytes
  (`utf-8-sig`), y **línea a línea**: en un fichero a medias, el viaje redondo del fichero entero
  revienta por las líneas buenas y no arregla nada. Hay un test que lo comprueba línea a línea
  (`tests/test_ficheros_de_texto.py`). **Los cinco bytes que no existen en cp1252 —0x81, 0x8D,
  0x8F, 0x90 y 0x9D— hay que mirarlos a mano**: Python sabe *leerlos* pero **no sabe volver a
  escribirlos**, así que la vuelta atrás falla justo en las líneas que los llevan, y son las de las
  **mayúsculas acentuadas** («MÁQUINAS») y las de media docena de emojis. El 03/10/2026 eso dejó 14
  líneas sin reparar en la primera pasada. Y van **tres veces en una sola sesión** (los cuatro
  documentos, `models.py` y `app.js`): la regla no es «ten cuidado», es **no usar `Get-Content`/
  `Set-Content` sobre un fichero del proyecto, nunca**.
- **Acentos en la consola.** Pon `$env:PYTHONIOENCODING="utf-8"` o los `print` con tildes
  revientan.
- **`Push-Location backend` desde dentro de `backend`** falla en silencio y los tests se
  ejecutan en el sitio equivocado dando errores raros. Usa rutas absolutas.
- **SQLite por defecto.** No hace falta levantar nada para desarrollar ni para los tests.
  En producción, `CUEDIGITAL_DATABASE_URL`.
- **La geometría es texto WKT**, no `Geometry`. Así el mismo código funciona en SQLite y
  en PostgreSQL. Al pasar a PostGIS se cambia esa columna.

---

## 8. Definición de «terminado»

- [ ] `pytest` en verde.
- [ ] `node --test "tests_js/*.test.js"` en verde.
- [ ] `scripts/humo.py` contra un servidor de verdad, todo correcto.
- [ ] Si hay texto nuevo: está en `textos.py` y pasa el test de jerga.
- [ ] Si hay algo visual: `DESIGN.md` y `estilos.css` dicen lo mismo, y el validador
      oficial sigue en 0 errores y 0 advertencias.
- [ ] Si hay un dato nuevo que no se sabe: se queda en blanco, no se inventa.
- [ ] Si hay una regla legal nueva: tiene su test con el caso que la incumple.
- [ ] Si le dices al agricultor que le falta algo: le das el botón que lo arregla.
- [ ] El resumen dice qué cambió, qué ficheros y qué tests corriste.



## Contexto de GitHub y del chat en la nube

Antes de continuar, leer CONTEXTO_PARA_EL_CHAT.md y DESARROLLO_EN_LA_NUBE.md.
La cola y las revisiones independientes están en contexto_agentes/. Sus rutas Windows
son históricas: usar las copias del checkout remoto. No probar contra datos reales.
En Linux puede prepararse el entorno con bash .codex/setup.sh.
