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

***Lo que NO está probado***: *que sean **idempotentes** —que pasarlas dos veces deje lo mismo— ni que la vuelta
atrás se haya ensayado sobre una copia real. **El encargo lo pide; aquí no está hecho.***

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
