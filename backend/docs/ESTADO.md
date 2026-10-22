# El estado del encargo, en un solo sitio

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

**La última pasada completa, sobre este mismo HEAD (22/10/2026)**:

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
| **volver con el scroll** | ⚠️ *el mecanismo está escrito en `app.js` (`recordarPorDondeIba` / `volverAdondeIba`); **la medición en el navegador no llegó a verlo saltar** — dicho, no disfrazado* |

***Y un punto de diseño que el encargo pide y hoy no se cumple***: *en el móvil **esta pantalla sigue siendo una
tabla** —no cambia a tarjetas—, y a 390 px una tabla de tierras se lee mal. **El encargo dice «tarjetas útiles» en el
móvil: hoy no lo son.***

### D05: la revisión con visión

***EN_REVISION***. *Las **quince capturas** -320, 390, 712, 1024 y 1440, tres pantallas- están en
`docs/capturas-de-anchuras/`. **El modelo de esta sesión no acepta imágenes**, y el encargo manda dejarlo así hasta que
lo mire quien sí puede.*

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
