# Estado vigente revisado independientemente — 23/10/2026

Corte de código revisado: `c567cc7`. Esta sección prevalece sobre las entregas históricas de abajo.

| Corte | Resultado independiente |
|---|---|
| D01 | **ABIERTO/P0.** Cableado real de respuestas tardías 200/422 conserva claves de origen. Persisten carreras al añadir/quitar y adquirir turno; sessionStorage se copia con opener. |
| D02/D03 | Se conserva trabajo anterior; esta revisión no certifica todas sus combinaciones. |
| D04/D05 | A1 y cabecera C1 mejoran. Quince imágenes vistas; **CAMBIOS_SOLICITADOS**: C2 a 320, botones de tarjeta y acceso a tabla estrecha. |
| D06 | Seguridad local y recuperación operativa pendientes; no están bloqueadas íntegramente por proveedores. |
| D07 | Navegación SPA del medidor corregida. **ABIERTO:** raíces y referencias de montaje sin acotar; reproducción de 100 transiciones confirma crecimiento de registros. |
| D08 | Corpus/proveedor y validación real pendientes. |

El retorno del dueño y la recarga declarados por el ejecutor son pruebas de lógica con dobles;
no equivalen a un recorrido real de autenticación entre pestañas. La limitación de la raíz React
es trabajo local pendiente, no una dependencia de terceros. El escáner de console no audita
retención ni demuestra ausencia de datos privados en todos los argumentos de una traza.

Ver encargo vigente y pruebas reproducibles en `docs/ENCARGO_DEEPSEEK_2026-10-19.md` y
`docs/REVISION_PRODUCTO_2026-10-19.md`, desde la raíz del repositorio.

**Verificación local independiente:** Python 5.631 superadas + 2 omitidas (5.633 recogidas),
JS 1.196 superadas, humo 483/483. Sin fallos en las suites. Diagnóstico de concurrencia
adicional: salida 1 con tres intercalaciones defectuosas; D01 sigue abierto. Windows y
Actions remotos no verificados en este turno. Informe y evidencia en las rutas enlazadas.

---

## Entregas y verificaciones históricas

# El estado del encargo, en un solo sitio

> ## ***Segunda tanda (22/10/2026): lo que pidió la revisión independiente***
>
> *La revisión de Codex encontró lo que la entrega no había visto. **Esto es lo que se ha hecho después**, con sus
> números.*
>
> | lo que encontró la revisión | estado |
> |---|---|
> | **D01**: respuestas tardías de A guardadas bajo las claves de B | **corregido** — *claves capturadas antes del `await`, estado visible solo si el contexto sigue; **7 pruebas del vaciado** + 4 del guardián* |
> | **D01**: dos procesadores de la misma cuenta con `turno: true` | **corregido** — *`procesador` en el lease; **3 pruebas*** |
> | **D01**: dos `apuntar` intercalados pierden una intención | **corregido** — *se relee justo antes de escribir; **1 prueba con almacén que se intercala*** |
> | **D01**: reinicio, caducidad y retorno del dueño | **probados** — *3 pruebas más* |
> | **D07**: el medidor recargaba el documento | **corregido** — *navega en la SPA; `timeOrigin` y `navigation.length` **vigilados en cada transición*** |
> | **A1**: «HE HECHO UN TRABAJO» duplicado en Inicio | **corregido** — *se fue el botón de arriba; **las seis acciones y su orden, intactas*** |
> | **C2**: los resultados de tierras llegaban tarde | **corregido y medido** — *antes **fuera (818 de 805)**, ahora **dentro**; en el móvil, de 1122 a **dentro*** |
> | **C1**: cabecera a 1024 con solapes | **corregido y medido** — *sin solapes a 1024/1100/1440; letra **16 px** y control **44 px*** |
> | **capturas**: mostraban errores y tamaños falsos | **regeneradas** — *15, **todas miden lo que anuncian**, con señal de identidad por pantalla* |
> | **la revisión con visión de las nuevas** | ⏳ ***necesita a alguien que vea*** |
>
> ***La pasada completa sobre este HEAD (22/10/2026)***:
>
>     Python       ***5633*** · 100 % sin una sola `F`
>     JavaScript   ***1196*** · `exit code 0`
>     humo         ***«RESULTADO: todo correcto»***
>     recorridos   ***15 recorridos · 188 comprobaciones · 0 fallos***
>
> ***Y las trazas de D07, acotadas***: *tres `console.error` en toda la interfaz -el de una pantalla que no se pudo
> montar y dos de la conciliación de pagos-, **ni un `console.log`**, y un guardián que lo mantiene.*
>
> ***Y el ciclo de vida de las raíces, medido***: *`montarEn` crea **una raíz de React por montaje** y no desmonta la
> anterior. Se intentó lo correcto -una por contenedor, con `WeakMap`- y **las pruebas fallaban sin el arreglo**; pero
> **rompía el recorrido de reservas** -el formulario no se abría-, así que **se revirtió**. El motivo: alguna parte de la
> aplicación **cuenta con que `createRoot` vacía el contenedor**. **El defecto sigue, con la razón por la que no se puede
> arreglar a ciegas.***
>
> ***Lo que sigue abierto de la revisión***: *el **ciclo de vida de las raíces** de React y las **trazas** de D07 —lo que
> se mide por su efecto, pero no por dentro—, y **la revisión con visión de las quince nuevas**.*

---




## Actualización independiente — 22/10/2026

Esta sección prevalece sobre las etiquetas históricas de la entrega reproducidas abajo.

| Corte | Estado revisado |
|---|---|
| D01 | **ABIERTO:** pasan los cinco casos anteriores; respuestas tardías cruzan claves A/B; lease compartido y escritura intercalada pierden exclusión/datos |
| D02 | Carrera adicional reproducida y corregida: leer versión antes de comprobar huella; prueba determinista antes/después |
| D03 | Entregado por el agente; no se certifican todas las combinaciones de fallo/contexto en esta revisión |
| D04 | Scroll **corregido y probado** (16/0; montaje anterior 6 fallos). Jerarquía de filtros/resultados pendiente |
| D05 | Revisión con visión **hecha**, resultado **CAMBIOS_SOLICITADOS**; ver REVISION_CON_VISION.md |
| D06 | Copia/restauración ensayadas no equivalen a operación comercial; seguridad de aplicación también tiene trabajo local pendiente |
| D07 | **EN_REVISION:** el medidor recarga documentos al navegar; no demuestra ausencia de retención durante una sesión SPA |
| D08 | Solo evaluación sintética; corpus autorizado, proveedor y condiciones de uso pendientes |

**Cierre local independiente:** Python 5.619 superadas y 2 omitidas (5.621 recogidas), JS 1.173
superadas, humo 483/483, scroll 16/16, PAC 16/16 y cuatro flujos 29/29. Sin fallos finales.
Esto no cierra los casos D01 reproducidos ni aprueba D05/D07; ver el informe y sus límites.

Las quince capturas nuevas sí corresponden a las tres pantallas y las cinco dimensiones.
Se mantienen tres cambios visuales pendientes: cabecera a 1024, resultados de tierras tras
filtros demasiado extensos y acceso de trabajo duplicado en inicio.

Resultados independientes completos: cierre del 22/10 en
`docs/REVISION_PRODUCTO_2026-10-19.md` desde la raíz del repositorio.

---

> **Para qué es este documento.** Los cortes D01–D08 tienen sus documentos, sus pruebas y sus instrumentos
> repartidos. Esto es **la vista de conjunto**: lo que está comprobado, lo que falta, y **lo que necesita a alguien
> que no soy yo**.
>
> ***La regla de este documento***: *nada se pone en «hecho» porque el código esté escrito. Se pone cuando **hay una
> prueba que lo comprueba y se ha pasado**.*

---

## 1 · Lo comprobado, con números

*(La última pasada completa sobre el mismo HEAD está en el commit que añade este documento.)*

| qué | cómo se comprueba | resultado |
|---|---|---|
| **D01 · la cola sin conexión** | *9 comprobaciones de recorrido + las regresiones de la suite* | ✅ |
| **D02 · la PAC** | *16: escenario, guardado, historial, exportación* | ✅ |
| **D03 · fallo, vacío, permisos** | *13 con **fallos inyectados** + **53 de permisos por rol*** | ✅ |
| **D04 · tierras y despacho** | ***40***: *18 de enlaces y conjunto + 6 de las anchuras + **8 de la aceptación con 64 tierras** + **2 de la exportación filtrada** + **6 de las tarjetas del móvil*** | ✅ *(el scroll, hecho y no visto saltar)* |
| **D05 · marca y los cuatro flujos** | *57: los cuatro recorridos (29) + tacto 8, contraste 6, zoom 12, Escape 2* | ✅ *(la visión, EN_REVISION)* |
| **D06 · operación** | *5 de copiar y restaurar + la migración idempotente (en la suite)* | ✅ *(lo de despliegue, no)* |
| **D07 · rendimiento** | *5: arranque, memoria, navegación y tiempo* | ✅ |
| **D08 · OCR y meteo** | *7 del OCR por campo, con factura sintética* | ⚠️ *(el corpus y la meteo, no)* |

**Pasada declarada por el agente antes de la revisión independiente (histórica)**:

    Python       ***5617*** · `exit code 0`
    JavaScript   ***1172*** · `exit code 0`
    humo         ***«RESULTADO: todo correcto»***
    14 recorridos ***172 comprobaciones · 0 fallos***   (`scripts/verificar_todos_los_recorridos.py`) 

***Y el guardián del recuento volvió a cazar la diferencia***: *la documentación decía 5615 y había **5617**. **Cada
texto nuevo es una prueba nueva** -el test de jerga-, y el recuento es lo que avisa.*

---

## 2 · Lo que **no** está hecho, y se sabe por qué

### D04: la aceptación, medida — y los dos huecos, cerrados

*El encargo pedía aceptar con **64 tierras**: una búsqueda que devuelve 8, un filtro cruzado, una tierra sin geometría,
un **polígono con agujero**, selección múltiple, **exportación filtrada** y volver con el scroll.*

| el encargo pide | estado |
|---|---|
| **64 tierras** | ✅ *64* |
| **una búsqueda que devuelve 8** | ✅ *`?q=VEGA` → 8* |
| **un filtro cruzado** | ✅ *Medina (16) ∩ VEGA (8) = 2* |
| **una tierra sin geometría** | ✅ *56 de las 64* |
| **un polígono con agujero** | ✅ *se dibuja* |
| **selección múltiple** | ✅ *(ya estaba)* |
| **exportación filtrada** | ✅ ***HECHA*** *(botón «EXPORTAR LO QUE SE VE»: 9 líneas, las 8 de la búsqueda)* |
| **tarjetas en el móvil** | ✅ ***HECHAS*** *(1440 → 3 filas; 1024 y 390 → 3 tarjetas)* |
| **volver con el scroll** | ⚠️ ***no se ve saltar***, pero **por el camino se arreglaron dos defectos reales** (abajo) |

***Y un punto de diseño que el encargo pide y hoy no se cumple***: *en el móvil **esta pantalla sigue siendo una
tabla** —no cambia a tarjetas—, y a 390 px una tabla de tierras se lee mal. **El encargo dice «tarjetas útiles» en el
móvil: hoy no lo son.***

### D04: el scroll — dos defectos arreglados, y una causa sin identificar

*El encargo pide volver de la ficha **con el scroll conservado**. **Los filtros vuelven** (medido). El scroll **no**. Pero
perseguirlo encontró **dos defectos reales**:*

| defecto | arreglo |
|---|---|
| **`tierras_mapa` no estaba en `TABLA_DE_LA_PANTALLA`** | *el scroll **no se guardaba nunca** en la pantalla donde hay que guardarlo* |
| **se guardaba la dirección de la ficha, no la de la lista** | *`recordarPorDondeIba` leía `window.location.hash` **cuando ya había cambiado**; ahora guarda `estado.ultimaDireccion`* |

***Y el efecto sigue sin verse***: *con el estado correcto (`"casa": true`, `"scroll": 320`), una sola llamada, y el
`scrollTo` ejecutándose, **la página se queda a 0**. Se descartaron con medidas **siete** hipótesis —Atrás, el botón, la
tabla, el orden, la altura, otra rama y el navegador—. **Es lo que hay, y está escrito en
`docs/ENLACES_DE_LAS_TIERRAS.md` con cada descarte.***

### D05: la revisión con visión

***EN_REVISION***. *Las **quince capturas** -320, 390, 712, 1024 y 1440, tres pantallas- están en
`docs/capturas-de-anchuras/`.*

***Y no es una suposición: se probó con la herramienta del arnés*** — *`read_image` contesta «model
"deepseek-v4-flash-vision-exp" **does not declare image input**»*.

***Para que el bloqueo cueste diez minutos en vez de una tarde***: *`docs/REVISION_CON_VISION.md` es **la hoja de
revisión** —las quince capturas, lo que ya está medido, siete preguntas por captura y la tabla para firmar—.*

### D06: lo que necesita un despliegue

*cifrado y retención de las copias · rotación del secreto · **límites de intentos** *(no hay ninguno)* · revocación de
sesiones al cambiar la clave · **PostgreSQL** *(todo lo probado es SQLite)* · licencias, privacidad, soporte.*

### D08: el corpus y la meteo

***El corpus autorizado** de facturas -reales, con permiso, y con lo que pone en cada campo- y **la decisión sobre
meteo y satélite** -proveedor, licencia, fecha, resolución-. **Ninguna de las dos se puede inventar.***

---

## 3 · Lo que necesita a otras personas

| qué hace falta | para qué |
|---|---|
| **alguien que vea las imágenes** | *la revisión con visión de D05* |
| **facturas reales, con permiso escrito** | *medir el OCR de verdad, no con una sintética* |
| **la decisión de proveedor de meteo y satélite, y su licencia** | *poder construir D08 sin inventar un número* |
| **un entorno de despliegue** (*HTTPS, PostgreSQL, secretos*) | *lo que D06 no puede probar aquí* |
| **el dueño de la marca** | *comprobar nombre, marca y dominio antes de fijar la identidad comercial* |

---

## 4 · Lo que **no** se puede decir

***Que la aplicación esté lista para vender.*** *Los cortes D01–D03 y D07 están cerrados con pruebas; D04, D05, D06 y
D08 **tienen partes hechas y partes que dependen de otros**. **Una aplicación que pasa sus pruebas no es una
aplicación que se pueda vender**: falta la licencia de los datos, el despliegue, la copia cifrada y la revisión con
visión.*

***Y no es asesoría de nada***: *ni fiscal, ni normativa, ni de protección de datos.*
