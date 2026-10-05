# El cuaderno de la Junta (el Cuecyl): leerlo y traer sus tierras

Este documento cuenta **qué es el cuaderno digital de Castilla y León**, de dónde sale el fichero
que se lee, qué trae dentro y qué hace este programa con él. Está escrito a partir de **tres
cuadernos de verdad** (campañas 2024, 2025 y 2026) y de las instrucciones oficiales de la Junta.

## 1. Qué es, y de dónde sale (direcciones oficiales)

La Consejería de Agricultura, Ganadería y Desarrollo Rural de Castilla y León tiene su propia
aplicación para llevar el cuaderno digital: el **Cuecyl** (Cuaderno digital de explotación agrícola
de Castilla y León). Sus instrucciones oficiales son:

> **Instrucciones para la cumplimentación del cuaderno digital de explotación agrícola mediante la
> aplicación informática desarrollada por la Comunidad de Castilla y León.** Consejería de
> Agricultura, Ganadería y Desarrollo Rural. Actualización: enero de 2025.
> <https://agriculturaganaderia.jcyl.es/web/jcyl/binarios/198/91/Instrucciones_cumplimentaci%C3%B3n_Cuecyl_ene%202025.pdf>
> SHA-256 del PDF descargado el 25/09/2026:
> `c9ac63ea2f8e215ad50b931b7f4e27f93f764133c6aa5f120ce65738b4a44754` (30 páginas, 3.828.796 bytes).

De ese documento salen los cuatro datos que hacen falta para entender todo lo demás:

| Qué dice el documento oficial | Qué significa para este programa |
|---|---|
| «El Cuecyl es el cuaderno digital de explotación agrícola que ha desarrollado la Consejería. **No obstante, es decisión de los agricultores utilizar este cuaderno o bien un cuaderno digital comercial**» | Llevar el cuaderno con este programa es legal: es el artículo 10.3 del RD 1054/2022 que ya está documentado en [`LO_QUE_OBLIGA_LA_LEY.md`](LO_QUE_OBLIGA_LA_LEY.md) |
| El acceso es en **<https://particulares.ayg.jcyl.es>** (el titular, como particular) o **<https://ayg.jcyl.es>** (entidad colaboradora), y hace falta **certificado digital, DNI electrónico o el CPI de la explotación** | De ahí sale el botón de «TRAER MIS TIERRAS»: el fichero lo descarga el agricultor de ahí, y este programa lo lee |
| «**Antes de dar de alta un nuevo cuaderno**, el titular debe actualizar las DGC de su explotación para la nueva campaña»: fuera del periodo de la Solicitud Única se hace en el **Reacyl** (<https://agriculturaganaderia.jcyl.es/web/es/registro-explotaciones-agrarias-castilla.html>, apartado 3) | Es el motivo de que un cuaderno recién descargado traiga las parcelas de la Solicitud Única y **nada más** |
| «El titular debe **crear un cuaderno para cada campaña** agrícola» | Se lee el año del propio fichero y las tierras se apuntan en **esa** campaña, no en la del año en curso |

## 2. El fichero: 25 hojas, y solo dos con datos

El Cuecyl exporta el cuaderno a un libro de cálculo que se llama `CuadernoExplotacion_<NIF>.xlsx`.
Los tres cuadernos de verdad que se han mirado tienen esta pinta:

| Hojas | 2024 | 2025 | 2026 | Qué son |
|---|---|---|---|---|
| 1.1 | ✅ | ✅ | ✅ | Datos generales de la explotación (titular, NIF, registros, dirección, teléfono, correo) |
| 1.2, 1.3 y 1.4 | ✅ | ✅ | ✅ | Personas que intervienen, equipos de aplicación (ROMA, fecha de adquisición e inspección) y asesor |
| 2.1 | ✅ | ✅ | ✅ | **Las parcelas**: referencia SIGPAC, uso, superficie SIGPAC, superficie cultivada, especie/variedad, ecorregimen, secano/regadío, aire libre, zona de nitratos |
| 2.2 | ✅ | ✅ | ✅ | Datos medioambientales: captaciones de agua de consumo humano y zonas específicas |
| 3.1 · 3.1 bis | ✅ | ✅ | ✅ | Tratamientos por parcela (y la hoja del asesor, con sus validaciones y firmas) |
| 3.2 | ✅ | ✅ | ✅ | Uso de semilla tratada |
| 3.3 · 3.4 · 3.5 | ✅ | ✅ | ✅ | Tratamientos de postcosecha, de locales de almacenamiento y de medios de transporte |
| 4 | ✅ | ✅ | ✅ | Análisis de residuos |
| 5 | ✅ | ✅ | ✅ | Cosecha comercializada (con el cliente y su RGSEAA) |
| 6 | ✅ | ✅ | ✅ | Registro de fertilización — el propio cuaderno lo marca **«OPCIONAL [EXCEPTO ZONAS VULNERABLES]»** |
| 7 · 7.1 · 7.2 | ✅ | ✅ | ✅ | Datos agroambientales de Castilla y León (labores, siembra, recolección, pastoreo) y los de agroindustriales sostenibles (fertilización y riego) |
| 8 | ✅ | ✅ | ✅ | Viñedo con D.O.P./I.G.P. (vacía si no hay viñedo) |
| 9.1 · 9.1.1 · 9.1.2 | ❌ | ✅ | ✅ | **Datos para las ayudas directas**: fertilización y riego de los ecorregímenes, y el **plan de abonado** |
| 9.3 · 9.4 · 9.5 · 9.6 | ✅ | ✅ | ✅ | Siega sostenible, islas de biodiversidad, cubiertas vegetales y cubiertas inertes |
| doc | ✅ | ✅ | ✅ | **Documentación a conservar junto al cuaderno**: facturas de los productos, contratos con las empresas que tratan, certificados de inspección de los equipos, resguardos de Sigfito, boletines de análisis, documentación del asesoramiento y albaranes de venta de la cosecha |

**La plantilla cambia entre años**: el cuaderno de 2024 tiene 23 hojas y el de 2025 y 2026 tiene
25, porque en 2025 se añadieron las tres hojas de las ayudas directas. Por eso el lector **no
depende de los números de fila ni de las letras de columna**: busca cada dato por el texto de su
etiqueta o de su cabecera, y si una hoja cambia de sitio sigue funcionando.

**Lo que trae un cuaderno recién descargado es la hoja 1.1 y la 2.1.** Las hojas de registro (los
tratamientos, los abonos, las labores, la cosecha, los análisis) **están vacías**: son las que el
agricultor va rellenando durante la campaña, y en la aplicación de la Junta es ella la que las
escribe. En los tres cuadernos mirados, de las 25 hojas solo esas dos tenían datos.

## 3. Qué hace este programa con él

**Traer las tierras, sin teclearlas.** Es el botón «TRAER MIS TIERRAS» de la pantalla de añadir una
parcela, y funciona en dos pasos:

1. **Se lee y se enseña.** `POST /api/cuaderno-cyl/leer` devuelve un resumen de lo que trae el
   papel —campaña, titular, cuántas líneas, cuántas tierras distintas, hectáreas declaradas,
   pueblos, cultivos, cuántas tierras están en zona de nitratos, cuántas tierras van partidas en
   trozos y los avisos— y **no escribe nada**. Así el agricultor ve lo que va a pasar antes de que
   le aparezcan 51 parcelas en la lista.
2. **Se apunta.** `POST /api/cuaderno-cyl/importar` da de alta las tierras y sus cultivos en la
   campaña del cuaderno, y devuelve qué ha pasado con cada línea.

### Las seis decisiones que hay que entender antes de tocar esto

1. **Se busca por la etiqueta y por la cabecera, no por la letra de la columna.** Así la misma
   lectura vale para las tres versiones de la plantilla, y un test puede comprobar que **todas**
   las columnas que se usan existen en un fichero oficial de verdad.
2. **Un dato que está en blanco se queda en blanco.** La casilla «parcela ubicada en zona
   nitratos» está marcada con «Sí» en las parcelas que lo están y **en blanco en todas las demás**:
   en blanco es «no lo han declarado», no «no está». Poner ahí un «no» sería inventarse una
   comprobación que nadie ha hecho, que es justo lo que este programa no hace nunca.
3. **Una tierra que el papel parte en trozos se apunta en trozos.** El cuaderno escribe **una línea
   por cultivo y superficie declarada**: en el cuaderno real de 2026, el recinto 1 de la parcela 24
   del polígono 507 sale tres veces (barbecho 4,44 ha, avena 0,46 ha y avena 0,13 ha). Aquí se
   apunta igual, porque es lo que hay de verdad: si se juntara todo en una parcela de 5,07 ha, el
   programa dejaría echar producto para 5 hectáreas de avena cuando solo hay 0,13.
4. **La superficie de la tierra es la que se cultiva; la del recinto se guarda aparte.** La hoja
   2.1 pide las dos por separado («Superficie SIGPAC (ha)» y «Superficie Cultivada (ha)») y no son
   lo mismo. Para las dosis manda la cultivada (`Parcela.superficie_ha`); la del recinto entero se
   guarda en `Parcela.superficie_sigpac_ha` para poder rellenar la hoja 2.1.
5. **Lo que ya está escrito no se pisa**, y se puede subir las veces que haga falta: una tierra que
   ya estaba apuntada y no tenía cultivo se queda con el del cuaderno; una que ya tenía otro
   cultivo declarado en esa campaña **no** se cambia; y el mismo fichero subido dos veces **no
   duplica ninguna tierra**.
6. **El nombre y el NIF no se copian del cuaderno.** El NIF es lo que identifica al titular delante
   de la administración y lo que se compara con el certificado digital, y el cuaderno lo escribe
   con el formato de su registro («0-70922320-A», con un cero delante que un DNI no lleva).
   Copiarlo tal cual dejaría un NIF que no coincide con el del certificado.

### Lo que se apunta de cada línea

En la parcela: la referencia del SIGPAC (las siete partes), el pueblo, el polígono, la parcela, el
recinto, el uso, la superficie cultivada, la del recinto, si es de secano o de regadío y la casilla
de zona de nitratos. En el cultivo de la campaña: la especie, la variedad, el **ecorregimen** (el
«P3» del cuaderno) y la superficie cultivada de esa línea.

El nombre que se le pone a cada tierra **sale del papel**, no se inventa: «1/5-1 AVENA (0.46 ha)»
es el polígono, la parcela, el recinto y lo que tiene sembrado. Un nombre inventado («El Prado») no
lo reconocería; y el que use en casa lo puede poner él.

## 3 bis. Sacarlo relleno, y decir lo que falta

Además de traer las tierras del cuaderno de la Junta, el programa **escribe su cuaderno relleno**:
`GET /api/cuaderno-cyl/exportar` devuelve el libro con las **25 hojas** del cuaderno oficial, con sus
nombres, sus cabeceras y sus columnas, y con lo que el agricultor tiene apuntado dentro.

**Qué se rellena hoy:**

| Hoja | De dónde salen los datos |
|---|---|
| 1.1 Datos generales | De «tu finca» (nombre, NIF, registros, dirección, teléfono, correo) |
| 1.2 Personas · 1.3 Máquinas · 1.4 Asesor | De «Mis cosas»: aplicadores (con su nº de ROPO y su tipo de carné marcado con una cruz), máquinas (con marca, modelo, nº de ROMA, fecha de adquisición y última inspección) y asesores |
| 2.1 Las parcelas | De «Mis parcelas»: referencia del SIGPAC, término municipal con su código, uso, superficies, especie y variedad, ecorregimen, secano/regadío y zona de nitratos |
| 3.1 Tratamientos | De cada apunte: parcela (por su número de orden), cultivo, fecha, hectáreas, problema, aplicador, máquina, producto con su **nº de registro**, dosis, eficacia y observaciones |
| 4 Análisis | De «Análisis»: fecha, material, parcela por su número de orden, boletín, laboratorio y sustancias |
| 5 Lo vendido | De «Lo que he vendido»: fecha, producto, kilos, nº de albarán, lote y comprador |
| 6 Abonado | De cada abono: parcela, abono, **nº de albarán**, riqueza N/P/K, dosis y **tipo de fertilización** (AF/AC/F, los códigos del cuaderno) |
| 7 Labores, siembra y recolección | De «Otro trabajo»: tipo de labor, fechas, dosis de siembra y fecha de recolección |
| 9.1.2 Plan de abonado | Del plan: necesidades N/P/K, producción esperada y **cultivo precedente** (calculado del historial) |
| doc Documentación | La lista oficial de papeles a conservar, más **lo que el agricultor tiene guardado** (sus papeles y sus facturas) |

**Qué no se rellena todavía, y se dice una por una** (ronda 28): de las 25 hojas, **10 se escriben solas**
con lo que el agricultor tiene apuntado y **15 no**. Las 15 son la 2.2 (datos medioambientales de las
parcelas), la 3.1 bis (validación del asesor), la 3.2 (semilla tratada), la 3.3, 3.4 y 3.5
(postcosecha, naves y almacenes, medios de transporte), la 7.1 y 7.2 (abonado y riego de las ayudas
agroambientales), la 8 (viñedo con denominación de origen), la 9.1 y 9.1.1 (abonado y riego de los
ecorregímenes) y la 9.3 a 9.6 (siega sostenible, islas de biodiversidad, cubiertas vegetales y
cubiertas inertes).

**Cada una de esas 15 se declara en el informe, y no con un «ya se hará»**: se dice qué pide la hoja,
donde se apunta ese dato en este programa, **cuántos apuntes del agricultor irían dentro** (por
ejemplo: «tienes 3 apuntes de semilla tratada») y **qué falta para poder escribirla sola**. Lo que
falta, en todas ellas, es lo mismo: **el sitio exacto de cada columna** de la hoja oficial, que se
copió de cuadernos de verdad para las diez hojas que sí se escriben y que para estas quince **no se
tiene y no se inventa** — una hoja con las columnas cambiadas de sitio parece rellena y está mal, y eso
es peor que una hoja en blanco. Mientras tanto, la hoja se termina a mano en el fichero o en el
cuaderno de la Junta (<https://particulares.ayg.jcyl.es>), y eso lo dice el propio informe.

> **Esto antes estaba mal contado, y por eso se arregló.** Hasta la ronda 28 el programa avisaba de
> **dos** hojas (la 2.2 y la 3.2) y de las otras trece no decía nada: se entregaban en blanco sin que
> el agricultor supiera si le faltaban datos o si era el programa el que no las escribía. Hay una
> prueba que ahora lo impide: **cada una de las 25 hojas tiene que estar o en la lista de las que se
> escriben o en la de las que no**, y cada una de las 15 tiene que salir en el informe con su motivo.

**Y una corrección de fondo en la hoja 3.1** (la de los tratamientos de las parcelas): hasta la ronda
28 se llevaba **todos** los tratamientos, incluidos los de la semilla, los del producto ya recogido y
los de las naves. El cuaderno oficial tiene una hoja para cada cosa (3.2, 3.3 y 3.4), y esos apuntes
salían en la hoja de las parcelas con la casilla «Id. Parcelas» vacía, que es justo lo que mira quien
revisa un cuaderno. Ahora la 3.1 lleva solo los de la tierra, y los demás **se cuentan en el informe,
en la línea de su hoja**, mientras esas hojas no se sepan escribir.

### Y lo más útil: la lista de lo que falta

`GET /api/cuaderno-cyl/que-falta` devuelve **qué datos pide el cuaderno y no están puestos**, cada
uno con **dónde se apunta**. No es una lista escrita a mano: sale de comparar las 25 hojas del
cuaderno oficial con lo que el agricultor tiene apuntado. Ejemplos de verdad:

```
· tus tierras: sin ellas no hay cuaderno            → Mis parcelas → añadir
· las máquinas con las que echas el producto
  (pulverizador, atomizador, mochila…), con su
  nº de ROMA y la fecha de su última inspección     → Mis cosas → máquinas de echar producto
· quién echa los productos (nombre, NIF y ROPO)     → Mis cosas → aplicadores
· del abono del 20/03/2026: el nº de albarán
  (viene en la factura del abono), si fue de fondo,
  de cobertera o fertirrigación                     → Abonar (o el apunte, para corregirlo)
· el plan de abonado del año                        → Plan de abono del año
· las facturas de lo que compras                    → Lo que tengo en el almacén → Mis facturas
```

**Dos detalles que importan:**

1. **Una máquina que no va en el ROMA no tiene ITEAF**, así que no se le pide ni el número ni la
   inspección: es la diferencia entre las tres pestañas de la app oficial (maquinaria propia, ajena y
   equipos sin ROMA). Pedir un dato que no existe es la forma más rápida de que nadie se fíe de una
   lista.
2. **Lo que no está se queda en blanco** en el fichero, nunca con un cero ni con un dato parecido.

### La prueba que más vale: la ida y vuelta

El cuaderno que escribe el programa **se vuelve a leer con el lector del cuaderno**
(`app/cuaderno_cyl.py`) en un test: se traen las tierras del cuaderno de ejemplo, se saca el cuaderno
relleno y se comprueba que el lector saca **las mismas tierras, con la misma referencia del SIGPAC y
el mismo año**. Si el fichero que saca el programa no se puede leer con el mismo lector que lee los de
la Junta, es que no es el cuaderno.

## 4. Lo que todavía no se hace (y de quién depende)

**Lo que sí se ha cerrado después** (ronda 28): el **tipo de carné** de quien echa el producto ya
es una **lista cerrada** con los cuatro que distingue la hoja 1.2 —básico, cualificado, fumigador y
piloto—, en vez de un texto libre: en el cuaderno esa casilla se marca con una cruz, y con un texto
libre la cruz no se podía poner (¿«Cualificado», «cualificado» o «nivel 2»?). Se guarda la clave
canónica y se enseña el nombre del carné.

**Y lo que se cerró en la ronda 26:** el **nº de albarán** y el **tipo de fertilización**
(F, AF o AC) ya se preguntan al apuntar un abono, que es lo que pide la hoja 6; y las **facturas**
se suben, se leen y se guardan, que es de donde salen la «empresa suministradora» y el «nº de
factura» de la hoja 9.1 (ver [`FACTURAS.md`](FACTURAS.md)).

| Qué | Estado |
|---|---|
| Leer las **hojas de registro** del cuaderno (3.1 a 9.6) | **Pendiente**: los cuadernos mirados las tienen vacías, así que no hay ningún caso real con el que comprobar la lectura. Cuando el agricultor traiga uno con datos dentro, se lee y se apunta |
| **Rellenar** el cuaderno oficial con los datos de este programa | **Hecho** (ronda 27): ver el apartado 3 bis |
| Rellenar las hojas 2.2, 3.1 bis, 3.2, 3.3 a 3.5, 7.1, 7.2, 8, 9.1, 9.1.1 y 9.3 a 9.6 | **Pendiente y contado hoja por hoja** (ronda 28): son **15 de las 25**. El programa **ya no las deja pasar en silencio**: cada una sale en el informe diciendo qué pide, dónde se apunta ese dato aquí, cuántos apuntes van dentro y **qué falta para escribirla sola** (el sitio exacto de cada columna de la hoja oficial, que no se tiene y no se inventa). Mientras tanto se completan a mano en el fichero o en el cuaderno de la Junta (<https://particulares.ayg.jcyl.es>) |
| Presentarlo por vía telemática | **Necesita el certificado del titular** (o el DNI electrónico, o el CPI): el acceso al Cuecyl lo exige. El agricultor ha autorizado el uso de su certificado; queda montarlo (ver la ronda siguiente) |
| Los datos que pide el cuaderno y el programa no guarda todavía | Se van cerrando por rondas: ver [`LO_QUE_SE_APUNTA_POR_TIERRA.md`](LO_QUE_SE_APUNTA_POR_TIERRA.md) |

## 5. Cómo se comprueba

| Qué | Cómo |
|---|---|
| La lectura del fichero | `backend/tests/test_cuaderno_cyl.py` (41 pruebas), contra `backend/tests/datos/cuaderno_cyl_de_ejemplo.xlsx` |
| El fichero de ejemplo | Se fabrica con `python scripts/hacer_cuaderno_de_ejemplo.py`, con **datos inventados**: los cuadernos de verdad llevan el nombre, el NIF y las tierras de una persona y eso no entra en el repositorio. Ver `backend/tests/datos/LEEME.md` |
| La pantalla | `backend/tests_js/interfaz.test.js`: ofrecer el cuaderno, leerlo sin apuntar nada, apuntarlo al confirmar, avisar si el fichero no es el cuaderno y no intentarlo sin conexión |
| Contra un servidor de verdad | `python scripts/humo.py <dirección>`, apartado **28** |
