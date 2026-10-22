# Operación: lo que está probado, y lo que no

> **Para qué es este documento.** D06 pide una puesta en producción: copias, actualizaciones, sesiones,
> configuración. Esto separa **lo que se ha probado en esta máquina** de **lo que necesita un despliegue de
> verdad**. *Una copia sin cifrar no es una copia cifrada, y decir «tenemos copias» sin decir cómo no vale.*

---

## 1 · Lo que sí está hecho, y probado

### La copia y la restauración — **probadas de verdad**

*`scripts/copiar_la_base.py` hace la copia; `scripts/verificar_la_copia_y_la_restauracion.py` **la usa**.*

| | |
|---|---|
| **la copia es coherente** | *`VACUUM INTO`, **no** un `copy` del fichero: copiar el `.db` a pelo puede dejar el WAL a medias* |
| **se lleva los adjuntos** | *la carpeta de ficheros, entera* |
| **deja un manifiesto** | *versión, fecha, integridad, tablas, adjuntos… y **`cifrado: false`*** |
| **la copia se comprueba** | *`PRAGMA integrity_check` **y se abre cada documento*** — no solo `quick_check`, como pide el encargo |
| **se restaura en un destino nuevo** | *otra carpeta, otro puerto, **otro servidor** |
| **y funciona** | *la cuenta entra, la tierra está y el papel está* |

    Comprobaciones: 5   Fallos: 0

***Y el detalle que casi se escapa***: *la comprobación de los documentos buscaba una columna que **no existe**
(`nombre_guardado`) y decía «documentos en la base: 0» **cuando había uno**. Se vio porque el número era cero
teniendo un papel subido. **Una comprobación que no encuentra nada que comprobar no está comprobando.***

### Las migraciones, con su vuelta atrás

*Hay migraciones concretas —`migrar_contactos.py`, `migrar_zona_de_nitratos.py`— **y cada una tiene su
`deshacer_la_migracion.py`**.*

***Lo que SÍ está probado***: *la suite `tests/test_aceptacion_copia_y_migracion.py` prueba **la mecánica** de la
copia -el WAL, la coherencia, la vuelta atrás restaurando la copia- y que **el esquema** se puede reconstruir dos veces
sin cambiar nada (`reconstruir_para_poder_decir_no_se` **es idempotente**, y hay una prueba que lo dice).*

***Y la idempotencia de la MIGRACIÓN DE DATOS, probada*** (22/10/2026):

*`tests/test_la_migracion_de_los_nitratos_es_idempotente.py` pasa `migrar_zona_de_nitratos.py` **dos veces** sobre una
base con el **esquema de una instalación vieja**, y comprueba que **la segunda no cambia nada**.*

***Reutiliza las herramientas de la suite de aceptación*** —`_motor_con_las_columnas_todavia_obligatorias` y
`_meter_una_finca_de_verdad`—, **no las copia**: *el esquema viejo se construye de verdad, con la columna `NOT NULL` y
los «no» inventados dentro.*

***Y hubo que entender el caso***: *con la tierra diciendo «no», el «no» del tratamiento **es legítimo** y la migración
**no lo toca** -se probó, y no movía ninguna fila-. **El defecto existía cuando el «no» lo puso el programa, no el
agricultor**: el caso es la tierra que **no lo sabe**.*

***Y se intentó, y no salió***: *la prueba se montó sobre una base **nueva**, y en una base nueva **la columna que la
migración arregla ya existe bien**: *la migración trabaja sobre una base **vieja**, con la columna `NOT NULL` y los
«no» inventados dentro.* **Para probarlo hay que construir el esquema viejo a mano** —que es exactamente lo que hace
`test_aceptacion_copia_y_migracion.py` con su `_el_esquema_de_las_26_tablas`—, **y no se reutilizó a tiempo**.

***La prueba se quitó en vez de dejarla saltando.*** *Una prueba que se salta siempre no prueba nada y da la falsa
sensación de que algo está cubierto.* **Queda como pendiente, con el camino escrito.**

---

## 2 · Lo que NO está hecho, y no se puede decir que sí

| lo que pide el encargo | estado |
|---|---|
| **cifrado y retención de las copias** | **no**. *El manifiesto lo dice: `cifrado: false`* |
| **secreto persistente y rotación** | *el secreto se lee de `CUEDIGITAL_SECRETO`; **rotarlo no está probado** y **no se invalida nada** al cambiarlo* |
| **HTTPS y proxy de certificados** | *fuera de esta máquina: es del despliegue* |
| **límites de intentos y de tamaños** | **no hay límite de intentos** en la puerta de entrada (*no se encontró ninguno*) |
| **sesiones: revocación al cambiar la clave** | *no probado* |
| **PostgreSQL** | **no**. *Todo lo probado es SQLite* — y el encargo dice: «si no se puede, dejar la promesa limitada a SQLite». **Aquí se deja limitada** |
| **licencias del código, vendor, datos y cartografía** | **no** |
| **prueba de tareas con usuarios** | **no** |
| **la revisión con visión** | **EN_REVISION**: *el modelo de esta sesión no acepta imágenes; las capturas están en `docs/capturas-de-anchuras/`* |

---

## 3 · Lo que este documento **no** es

***No es una promesa de que la aplicación esté lista para producción.*** *Es lo contrario: **la lista de lo que
falta**, para que nadie lea «hay copias» y entienda «hay copias cifradas y probadas de restaurar».*

***Y no es asesoría jurídica***: *ni fiscal, ni normativa, ni de protección de datos. Eso necesita a quien sepa de
eso.*

---

## 4 · Lo que sí se puede decir hoy

- *Los datos **se pueden copiar y restaurar en otra máquina**, y **los documentos se abren después**.*
- *La base **no se rompe** al copiarla con la aplicación escribiendo (`VACUUM INTO`).*
- *El despliegue **es SQLite**, y así está probado.*
- *Todo lo demás de D06 **está por hacer**, y está escrito arriba.*
