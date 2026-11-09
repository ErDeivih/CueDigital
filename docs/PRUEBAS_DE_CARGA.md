# Cuántos agricultores aguanta CUE Digital hoy

> **La respuesta corta, medida el 09/11/2026 en el ordenador de David**
> (Ryzen 5 3600, 6 núcleos / 12 hilos, 31,9 GB de RAM, Windows 11, con la máquina al
> 100 % de CPU por otros procesos):
>
> - **10 agricultores a la vez, cada uno haciendo el recorrido completo, van con holgura**
>   (p95 de 240–286 ms en el servidor, 0 errores).
> - **La rodilla está entre 10 y 25 usuarios**: a 25 el p95 se dobla o triplica en cada
>   pasada (630–1.027 ms) y las peticiones por segundo dejan de subir.
> - **A 50 usuarios ya va lento** (p95 1.620–1.784 ms) aunque **no da ni un error**; el
>   problema es la espera, no un fallo.
> - **A 100 usuarios se atasca**: las 100 peticiones de entrada agotaron los 20 s de espera
>   sin recibir respuesta. **No se cayó el servidor**; dejó de contestar a tiempo.
> - Con la **configuración de producción de verdad** (PBKDF2 de 240.000 iteraciones en vez
>   de las 100.000 de la prueba) **entrar cuesta 2,9 veces más** (280 ms de CPU por clave):
>   a 1 usuario el p95 pasa de 130 a 234 ms, a 10 de 286 a 455 ms y a 25 de 630–895 a
>   775–821 ms. **A 50 se pasa del segundo y medio (p95 1.621 ms).**
>
> **El número que hay que defender hoy es 10 usuarios concurrentes.** Con uso normal de
> campo (cada agricultor hace unas pocas peticiones y se va), eso permite **del orden de
> 150–300 agricultores activos al día** (estimación razonada en el apartado 7), siempre que
> no abran todos en el mismo par de minutos. El umbral que obliga a escalar es claro:
> **20–25 usuarios a la vez, o un p95 de entrada por encima de 1 s en producción**.

Este documento es la prueba de que se puede decir eso. Todo lo **medido** lleva el comando
que lo produce y la fecha. Todo lo **estimado** va marcado como **ESTIMACIÓN**, con las
cuentas a la vista. Lo que no se ha medido, se dice en el apartado 8 y no se rellena.

- Guion de la prueba: [`backend/scripts/prueba_de_carga.py`](../backend/scripts/prueba_de_carga.py)
- Sus pruebas automáticas: [`backend/tests/test_prueba_de_carga.py`](../backend/tests/test_prueba_de_carga.py)

---

## 1. Cómo se lanza

Desde `backend/`:

```powershell
# La pasada normal: levanta su propio uvicorn con una base temporal, mide los cinco
# escalones por defecto y borra todo al terminar.
..\.venv\Scripts\python.exe scripts\prueba_de_carga.py

# La pasada que se usó para el documento (más muestras por escalón, más estable).
..\.venv\Scripts\python.exe scripts\prueba_de_carga.py --escalones 1,5,10,25,50 --peticiones-por-usuario 2

# Medir con el coste real de producción (PBKDF2 240.000, no 100.000).
..\.venv\Scripts\python.exe scripts\prueba_de_carga.py --escalones 1,5,10,25 --iteraciones-pbkdf2 240000

# Fincas del tamaño de la de ejemplo (64 tierras) en vez de 10.
..\.venv\Scripts\python.exe scripts\prueba_de_carga.py --escalones 1,5,10,25 --tierras-por-usuario 64 --peticiones-por-usuario 4

# Resultado para máquina, sin la tabla (JSON a la salida estándar; la tabla, a la de error).
..\.venv\Scripts\python.exe scripts\prueba_de_carga.py --escalones 1,5 --json

# Un servidor que ya está en marcha: no arranca nada y no toca ninguna base.
..\.venv\Scripts\python.exe scripts\prueba_de_carga.py --base http://127.0.0.1:8010 --sin-servidor
```

### Argumentos

| Argumento | Qué hace | Por defecto |
|---|---|---|
| `--base URL` | Usa un servidor ya levantado; **no arranca uvicorn**. | arranca su propio servidor temporal |
| `--escalones 1,5,10,25` | Usuarios concurrentes de cada escalón, de menos a más. Hay que subir, no repetir. | `1,5,10,25,50` |
| `--peticiones-por-usuario N` | Recorridos completos por usuario en cada escalón. Con 2 o más, los percentiles son menos ruidosos. | `1` |
| `--tierras-por-usuario N` | Tierras de cada agricultor de prueba. | `10` |
| `--iteraciones-pbkdf2 N` | Iteraciones con las que arranca **el servidor propio**. Para medir producción: `240000`. | `100000` |
| `--json` | Saca el resultado en JSON (para guardarlo o pintarlo). | tabla en castellano |
| `--sin-servidor` | No arranca uvicorn: usa `--base` o `http://127.0.0.1:8000`. | arranca servidor temporal |

### Códigos de salida

| Código | Significado |
|---|---|
| `0` | Aguanta todos los escalones pedidos: sin errores y sin rodilla. |
| `1` | No aguanta: ha aparecido la rodilla (errores o p95 disparado) o no se llegaron a probar todos los escalones. |
| `2` | **No se ha podido medir**: no hay servidor al que preguntar, o no se han podido preparar los agricultores. Se dice qué pasa y no se rompe. |

### Lo que garantiza el guion

- Si no se le pasa `--base`, levanta **su propio uvicorn** en un puerto libre con
  `CUEDIGITAL_DATABASE_URL` en una **carpeta temporal**, y al terminar apaga el servidor,
  comprueba que el puerto quedó cerrado y **borra la carpeta entera** (base, adjuntos,
  registro del servidor).
- Los agricultores de prueba se dan de alta **por la API pública** (registro real, finca,
  campaña, producto y tierras), no retocando la base por detrás.
- **No sale a internet** y **no toca la base de desarrollo** (`backend/cuedigital.db`) ni
  datos reales.
- Si se le da `--base`, **no arranca nada y no borra nada**: usa el servidor que le digan.
  Ojo: ese servidor usará **su** base; para probar no se le debe apuntar nunca a una base
  con datos de agricultores, porque el guion crea cuentas y apuntes de prueba en ella.

---

## 2. Qué mide exactamente

Cada «recorrido» es lo que hace de verdad un agricultor cuando abre el cuaderno, y son
**cinco peticiones**:

1. **entrar** — `POST /api/cuenta/entrar` (PBKDF2 de la clave, el coste más caro de todos);
2. **listar las tierras** — `GET /api/parcelas/vista` (la llamada de la pantalla de Tierras);
3. **abrir una ficha** — `GET /api/parcelas/{id}`;
4. **apuntar un tratamiento** — `POST /api/tratamientos` (con su validación y su rastro de
   auditoría, como en el uso real);
5. **consultar el cuaderno** — `GET /api/cuaderno/resumen`.

Cada escalón lanza N de esos recorridos **a la vez**, cada uno con **su propia cuenta**
(hasta 100 agricultores preparados), y mide **cada petición por separado**:

- **Peticiones**: cuántas se han hecho de verdad (si alguien no puede entrar, su recorrido
  se corta y se apunta el fallo, no se cuentan las que no han ocurrido).
- **Errores**: peticiones que no han devuelto 2xx (incluye las que ni siquiera obtuvieron
  respuesta, que se apuntan como estado `0`).
- **p50 / p95 / p99**: la latencia de cada petición, en milisegundos. El p95 quiere decir
  «95 de cada 100 peticiones han tardado esto o menos»; es el número que se mira para saber
  si la espera molesta de verdad.
- **Peticiones/s**: peticiones totales divididas por lo que ha durado el escalón.
- **La rodilla**: el primer escalón en el que ocurre una de estas tres cosas (la primera
  que salte manda):
  1. hay **errores**;
  2. el **p95 pasa de 1.000 ms** (un segundo de servidor, antes de sumar la red móvil);
  3. el **p95 se multiplica por 2,5** respecto del escalón anterior y ya pasa de 300 ms
     (para no llamar rodilla al ruido de una máquina ociosa).

Cuando aparece la rodilla, el guion **deja de subir**: los escalones de arriba ya no dicen
nada nuevo y solo calentarían la máquina. (Para ver qué pasa más allá, se lanza el escalón
suelto, como se hizo con 50 y con 100.)

El guion no mide el «tiempo de un recorrido»: mide **cada petición**, que es lo que se
puede comparar entre escalones y lo que se parece a lo que espera una persona en cada
pantalla.

---

## 3. La máquina y las condiciones de la medida

```
AMD Ryzen 5 3600 6-Core Processor · 6 núcleos / 12 hilos · 31,9 GB de RAM
Windows 11 (10.0.26200) · Python 3.12.10 · SQLite 3.49.1
```

Sacado por el propio guion, que lo imprime en su cabecera
(`plataforma`, `os.cpu_count()`, el registro de Windows y `GlobalMemoryStatusEx`).

**Condición importante y honesta**: durante toda la tanda de medidas la máquina estaba
**al 100 % de CPU por otros procesos**, incluida **la suite completa de pytest de otro
compañero** (proceso `python -m pytest -q` lanzado a las 16:53 y aún vivo) y otros
proyectos del ordenador. Comprobado antes y después con:

```powershell
Get-CimInstance Win32_Processor | Select-Object LoadPercentage   # 100, 100, 100, 100, 100
```

Eso hace que **los números sean conservadores**: en una máquina quieta saldrían mejores.
También es verdad que el cliente de carga y el servidor comparten los mismos 6 núcleos, así
que en producción (con los móviles en otro sitio) el servidor tendría un poco más de CPU;
pero el orden de magnitud no cambia, porque el cuello es del propio servidor (apartado 6).

La prueba usa **100.000 iteraciones de PBKDF2** por defecto para que el alta de 50 cuentas
no tarde una eternidad. Por eso, además, se midió aparte **con las 240.000 de producción**
(apartado 4.5), que es lo que hay que mirar para decidir.

Las medidas se hicieron sobre el árbol de trabajo del 09/11/2026 a las 17:12, que ya
incluía el middleware de observabilidad de otro compañero (mide cada petición y no cambia
ninguna respuesta; su coste es una lectura de reloj por petición).

---

## 4. Resultados medidos

Los comandos y las fechas están en el anexo (apartado 10). Todo lo de este apartado está
medido el **09/11/2026** en la máquina descrita.

### 4.1. La pasada de referencia (100.000 iteraciones, 10 tierras por finca)

Comando:

```powershell
..\.venv\Scripts\python.exe scripts\prueba_de_carga.py --escalones 1,5,10,25,50 --peticiones-por-usuario 2
```

Salida real (17:27):

```text
== Prueba de carga de CUE Digital ==
Preparando 50 agricultores de prueba (por la API pública)…
Fecha: 2026-11-09 17:27:36
Servidor: http://127.0.0.1:61596 (uvicorn temporal propio, base de datos temporal)
Clave (PBKDF2): 100.000 iteraciones en el servidor de pruebas; en producción son 240.000
Máquina: AMD Ryzen 5 3600 6-Core Processor · 12 hilos · 31.9 GB · Windows-11-10.0.26200-SP0
Agricultores de prueba: 50 (con 10 tierras cada uno); preparados por la API en 16.4 s

Calentando el servidor con un recorrido que no se mide…
Escalón de 1 usuarios concurrentes…
Escalón de 5 usuarios concurrentes…
Escalón de 10 usuarios concurrentes…
Escalón de 25 usuarios concurrentes…
  Ha aparecido la rodilla: no se sube más, porque lo de arriba ya no dice nada.

  Usuarios  Peticiones  Errores    p50 ms    p95 ms    p99 ms   Peticiones/s
  --------  ----------  -------    ------    ------    ------   ------------
         1          10        0      16.6     130.0     131.3          25.6
         5          50        0      56.9     170.7     261.8          59.8
        10         100        0     120.5     286.0     364.8          65.5
        25         250        0     269.6     895.0    1397.4          59.2   <-- rodilla

Rodilla: a partir de 25 usuarios (en 25 usuarios el p95 (895 ms) se multiplica por 3.1 respecto de los 10 usuarios (286 ms)).
Veredicto: NO aguanta. En 25 usuarios el p95 (895 ms) se multiplica por 3.1 respecto de los 10 usuarios (286 ms).

Código de salida: 1 (0 aguanta · 1 no aguanta · 2 no se pudo medir)
```

Lo que dice, en palabras:

- **1 usuario**: el p95 es de 130 ms y la petición más lenta es la de entrar (PBKDF2).
  El recorrido entero se hace en un suspiro, pero **entrar cuesta ~100 ms de CPU**.
- **5–10 usuarios a la vez**: el p95 sube a 171–286 ms y las peticiones por segundo suben
  hasta ~60–65. El servidor aún tiene aire: la latencia crece poco y el rendimiento sube.
- **25 usuarios a la vez**: el p95 se va a **895 ms** (3,1 veces el de 10), el p50 se
  duplica y las peticiones por segundo **dejan de subir** (59). Eso es la rodilla: se ha
  llegado al techo y lo que se gana en usuarios se paga en espera.
- **No hubo ni un error en ningún escalón**: el servidor no falla, se atasca. Es peor de
  detectar, porque la pantalla no da error, se queda cargando.

### 4.2. ¿Es reproducible? Sí, la rodilla sale en el mismo sitio

Cuatro pasadas con el mismo comando (una con 1 petición por usuario y tres con 2). Se
comparan los dos escalones que importan:

| Hora | p95 con 10 usuarios | p95 con 25 usuarios | Factor | Rodilla |
|---|---|---|---|---|
| 17:14 | 263 ms | 722 ms | ×2,7 | 25 |
| 17:15 | 307 ms | 778 ms | ×2,5 | 25 |
| 17:21 | 240 ms | 630 ms | ×2,6 | 25 |
| 17:27 | 286 ms | 895 ms | ×3,1 | 25 |

Las cifras bailan (la máquina estaba compartida), pero **el escalón de la rodilla no**:
siempre 25. La lectura útil no es «aguanta exactamente 10», sino:

> **con 10 se va bien y con 25 se paga el doble o el triple por petición.**

### 4.3. Hasta dónde llega: 50 y 100 usuarios

Para ver qué hay más allá de la rodilla se lanzan escalones sueltos.

**50 usuarios** (17:22, 1 petición por usuario, 100.000 iteraciones):

```text
  Usuarios  Peticiones  Errores    p50 ms    p95 ms    p99 ms   Peticiones/s
  --------  ----------  -------    ------    ------    ------   ------------
        50         250        0     780.3    1783.5    2243.9          49.0   <-- rodilla
```

**Cero errores, pero el p95 es de 1,8 segundos y el p99 de 2,2**: con 50 agricultores
haciendo cosas a la vez, uno de cada veinte espera casi dos segundos a cada pantalla.

**100 usuarios** (17:23 y 17:25, con `--json` para ver los códigos):

```text
  Usuarios  Peticiones  Errores    p50 ms    p95 ms    p99 ms   Peticiones/s
  --------  ----------  -------    ------    ------    ------   ------------
       100         100      100   20362.9   20502.1   20522.5           4.9   <-- rodilla

  "codigos": { "0": 100 }     # 0 = ni siquiera hubo respuesta
```

Las 100 peticiones de entrar **agotaron los 20 s de espera del cliente**. El servidor
**no se cayó** (se apagó limpio al terminar), pero dejó de contestar a tiempo. A partir de
ahí, para el agricultor la aplicación «no funciona» aunque el proceso siga vivo.

### 4.4. Fincas de verdad: 64 tierras en vez de 10

La finca de ejemplo del proyecto tiene 64 tierras. El listado de tierras
(`/api/parcelas/vista`) devuelve más datos y cuesta más. Se midió con
`--tierras-por-usuario 64 --peticiones-por-usuario 4` (17:26):

```text
  Usuarios  Peticiones  Errores    p50 ms    p95 ms    p99 ms   Peticiones/s
  --------  ----------  -------    ------    ------    ------   ------------
         1          20        0      24.6     150.6     155.1          21.6
         5         100        0      50.5     186.9     297.2          58.4
        10         200        0     153.8     356.5     443.8          57.0
        25         500        0     423.3     885.6    1220.0          51.2
```

Con 64 tierras **la latencia es más alta en todos los escalones** (a 10 usuarios, p50 154 ms
frente a 121 ms; a 25, p50 423 ms frente a 270 ms), que es lo esperable: se pinta más. La
regla no marcó rodilla porque el crecimiento de 10 a 25 fue de ×2,48, **justo por debajo del
factor ×2,5**: está **en el filo**. En otra pasada del mismo día, con la misma
configuración, el crecimiento fue ×2,7 y sí marcó rodilla. Es exactamente lo que significa
una rodilla: el punto a partir del cual el resultado depende del ruido.

**Conclusión de las dos pruebas de tamaño:** el número de tierras no mueve el punto de la
rodilla en este rango (10–25), pero **sí sube la latencia de todas las peticiones**. Una
finca de 64 tierras es más lenta que una de 10.

### 4.5. Con la configuración de producción: PBKDF2 de 240.000

Esto es lo que hay que mirar para decidir. El servidor de pruebas usa 100.000 iteraciones
para que el alta no tarde; **en producción son 240.000** (`backend/app/security.py`,
`ITERACIONES_PBKDF2 = 240_000`). Con `--iteraciones-pbkdf2 240000` se mide ese coste real.

**1, 5, 10 y 25 usuarios** (17:33, 2 peticiones por usuario):

```text
  Usuarios  Peticiones  Errores    p50 ms    p95 ms    p99 ms   Peticiones/s
  --------  ----------  -------    ------    ------    ------   ------------
         1          10        0      15.0     234.2     237.9          16.8
         5          50        0      36.4     348.8     381.6          49.2
        10         100        0      79.0     454.7     502.2          59.8
        25         250        0     331.3     774.9    1037.7          63.0
```

**25 y 50 usuarios** (17:34, 2 peticiones por usuario):

```text
  Usuarios  Peticiones  Errores    p50 ms    p95 ms    p99 ms   Peticiones/s
  --------  ----------  -------    ------    ------    ------   ------------
        25         250        0     231.9     820.6    1026.4          68.8
        50         500        0     776.9    1620.6    1967.9          55.0   <-- rodilla
```

Lo que cambia respecto de la prueba con 100.000:

- **Entrar es mucho más caro**: a 1 usuario el p95 pasa de ~130 a **234 ms**; a 10, de 286
  a **455 ms**; a 25, de 630–895 a **775–821 ms**. Es el mismo ~2,9× que cuesta la clave.
- **El techo de peticiones por segundo no baja** (sigue en 55–69): el límite no es el
  PBKDF2 sino la arquitectura del servidor (apartado 6); el PBKDF2 **lo que hace es que
  cada persona espere más**.
- **A 50, el p95 pasa de 1,6 segundos**: por encima del umbral del segundo, la aplicación
  ya no se siente ágil ni en el mejor de los casos.

**Respuesta para producción: con 10 usuarios a la vez va bien; a 25 se va a ~0,8 s por
petición (p95); a 50 se pasa de 1,6 s.** Por eso el número que se puede defender hoy es
**10 concurrentes**, y el aviso de escalar salta a **20–25**.

---

## 5. Cómo se lee la tabla

| Columna | Qué significa | Cuándo es un problema |
|---|---|---|
| **Usuarios** | Agricultores haciendo el recorrido **a la vez**. | — |
| **Peticiones** | Peticiones HTTP reales de ese escalón. | Si baja mucho sin bajar los usuarios, es que los recorridos se cortan (fallos). |
| **Errores** | Peticiones sin respuesta 2xx (incluye los cortes de conexión). | **Cualquier error ya es rodilla.** En el uso real, un error es un agricultor que no puede apuntar. |
| **p50** | La petición típica. | Si pasa de ~0,5 s, la aplicación «va lenta» para todos. |
| **p95** | La petición que sufre uno de cada veinte. **Es el número que manda.** | Más de 1.000 ms en el servidor ya es demasiado (la red móvil suma). |
| **p99** | El caso malo (cobertura, una tierra grande, un pico). | Si se dispara respecto a p95, hay peticiones que se atascan. |
| **Peticiones/s** | Cuántas peticiones por segundo aguanta el servidor. | Si deja de subir al subir usuarios, se ha llegado al techo. |

**Regla de oro:** cuando al subir usuarios la latencia se dobla o triplica y las
peticiones/s se quedan planas, **se ha llegado**. No hace falta que haya errores: a partir
de ahí, cada agricultor nuevo se paga con la espera de los demás.

**No confundir «usuarios concurrentes» con «agricultores registrados».** Los 10 usuarios
de la prueba están **pulsando sin parar** durante toda la pasada. Un agricultor de verdad
hace unas pocas peticiones y se va. La relación entre las dos cosas está estimada en el
apartado 7.

---

## 6. Los cuellos de botella, comprobados en el código

Esto no es una suposición: es lo que hay en el repositorio, con su fichero y su línea.

### 6.1. Un solo proceso de uvicorn

El arranque documentado (`README.md`, «Arrancar») es **un** proceso:

```bash
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

En el repositorio **no hay ninguna configuración de `--workers`** (buscado en `backend/`):
el servidor de producción tal y como está pensado hoy es **un proceso**, con lo que toda
la CPU disponible se reparte entre sus hilos, pero **no se multiplica por núcleos**.

### 6.2. 40 hilos para las peticiones (endpoints síncronos)

Los routers de este programa son funciones síncronas con `Session` de SQLAlchemy. FastAPI
las ejecuta en el pool de hilos de AnyIO, que por defecto tiene **40 hilos** (comprobado en
el entorno del proyecto). Con más de 40 peticiones a la vez, las demás **esperan turno**:

```powershell
..\.venv\Scripts\python.exe -c "import asyncio, anyio.to_thread; async def m(): print(anyio.to_thread.current_default_thread_limiter().total_tokens); asyncio.run(m())"
# 40
```

### 6.3. 15 conexiones a la base por proceso (y 30 s de espera)

`app/database.py` crea el motor con `create_engine` y los valores por defecto de
SQLAlchemy. Comprobado en el entorno del proyecto:

```powershell
..\.venv\Scripts\python.exe -c "from app.database import engine; p=engine.pool; print(type(p).__name__, p.size(), p._max_overflow, p._timeout)"
# QueuePool 5 10 30.0
```

Es decir: **como mucho 15 operaciones de base de datos a la vez por proceso** (5 + 10 de
más), y una petición que no encuentra hueco **espera hasta 30 segundos** antes de fallar.
Con 25 usuarios a la vez, ya hay peticiones haciendo cola para una conexión; con 100, la
cola es la que explica los 20 s de espera de la prueba.

No es un fallo: son los valores por defecto, prudentes para no abrir cien conexiones a
una base pequeña. Pero **explica el techo** y es lo primero que se ajusta al escalar.

### 6.4. SQLite: un solo escritor y sin WAL

La base por defecto es SQLite (`sqlite:///./cuedigital.db`, en `app/database.py`), y
SQLite **solo admite un escritor a la vez**. En el código **no se activa el modo WAL**
(buscado `journal_mode` en `app/`: no aparece; solo se toca `PRAGMA foreign_keys`). Con el
diario por defecto, cada apunte que se guarda bloquea a los demás escritores mientras
dura su transacción. En la prueba no se vio ningún «database is locked», pero cada
tratamiento de los que se apuntan es una escritura que se pone en fila.

**Esto es lo que cambia de verdad al pasar a PostgreSQL**: deja de haber un único
escritor.

### 6.5. PBKDF2 de 240.000 iteraciones en el registro y en la entrada

`app/security.py` deriva la clave con PBKDF2-SHA256 y `ITERACIONES_PBKDF2 = 240_000`. Se
hace en **cada registro y cada entrada** (`hash_clave` / `verificar_clave`). Medido en esta
máquina (09/11/2026), solo la derivación, sin red ni base:

```powershell
..\.venv\Scripts\python.exe -c @"
import hashlib, time
for iteraciones in (100_000, 240_000):
    tiempos = []
    for _ in range(5):
        inicio = time.perf_counter()
        hashlib.pbkdf2_hmac('sha256', b'carga-2026-segura', b'0123456789abcdef', iteraciones)
        tiempos.append((time.perf_counter() - inicio) * 1000)
    tiempos.sort()
    print(f'{iteraciones:>7} iteraciones: mediana {tiempos[2]:.1f} ms  min {tiempos[0]:.1f}  max {tiempos[-1]:.1f}')
"@
#  100000 iteraciones: mediana 98.3 ms  min 97.1  max 116.0
#  240000 iteraciones: mediana 280.4 ms  min 270.5  max 335.0
```

Es una decisión de seguridad y está bien que cueste: **280 ms de CPU por cada entrada**, y
no se puede bajar. Lo que sí se puede es **no hacer que todo el sistema dependa de eso**:
hoy cada recorrido vuelve a entrar, y la entrada es la petición más lenta de todas. En la
práctica, el token dura 30 días (`security.DURACION_TOKEN_SEGUNDOS`), así que el agricultor
**no entra en cada pantalla**; la prueba entra en cada recorrido a propósito, para medir el
peor caso.

**Riesgo añadido**: no hay límite de intentos de entrada (`security.py` lo dice: «límite
de intentos y doble factor» están pendientes). Un agricultor con el móvil reintentando, o
alguien haciendo peticiones a la entrada, **quema CPU a 280 ms por intento**. Eso es un
amplificador de carga de manual y hay que tenerlo en cuenta antes de abrir al público.

### 6.6. Fotos y adjuntos: hasta 12 MB por fichero, en memoria y a disco

En `app/adjuntos.py`:

- el máximo por fichero es **12 MB** (`MAXIMO_BYTES = 12 * 1024 * 1024`);
- **el fichero se lee entero en memoria antes de escribirlo a disco** (`leer_el_fichero`
  acumula trozos y `guardar_en_disco` hace `write_bytes`): una foto de 12 MB = 12 MB de
  RAM mientras dura la subida, por cada subida a la vez;
- el fichero **va a disco**, no a la base (`CUEDIGITAL_ADJUNTOS`, por defecto
  `datos/adjuntos`), y en la base solo queda la referencia.

En esta prueba **no se subió ninguna foto**: la medición de ancho de banda y de disco está
en el apartado 8. Lo medido aquí es solo que el código lo hace así.

### 6.7. El PDF del cuaderno

`app/routers/cuaderno.py` genera el PDF con **reportlab** en la misma petición
(`GET /api/cuaderno/pdf`, `SimpleDocTemplate`). Es trabajo de CPU y memoria del mismo
proceso y del mismo pool de hilos que atiende a todos los demás. **No se ha medido** su
coste (depende de cuántos apuntes tenga el año). Es la siguiente prueba que habría que
hacer si se quiere saber cuánto aguanta la exportación.

### 6.8. Arranque: 5 s por proceso y crea las tablas

Al arrancar, el ciclo de vida de `app/main.py` llama a `crear_tablas()`, que crea el
esquema y pone al día columnas e índices. Medido sobre una base nueva (09/11/2026, con la
máquina cargada):

```powershell
..\.venv\Scripts\python.exe -c @"
import time, os
os.environ['CUEDIGITAL_DATABASE_URL'] = 'sqlite:///C:/Users/David/AppData/Local/Temp/arranque.db'
inicio = time.perf_counter()
import app.models
from app.database import crear_tablas
fin_import = time.perf_counter()
crear_tablas()
fin = time.perf_counter()
print(f'importar app.models: {(fin_import-inicio)*1000:.0f} ms')
print(f'crear_tablas: {(fin-fin_import)*1000:.0f} ms')
"@
# importar app.models: 2252 ms
# crear_tablas sobre base nueva: 3061 ms
# total: ~5,3 s
```

Esto importa para dos cosas: el arranque no es instantáneo (~5 s), y **si se ponen varios
workers, todos ejecutan `crear_tablas` a la vez** sobre la misma base. Eso es una carrera
que hay que evitar (arrancar un worker, esperar, y luego los demás; o sacar la preparación
del arranque). Con SQLite, además, varios workers son varios escritores: peor.

### 6.9. Consumo de memoria: ~142 MB por proceso

Medido con `Get-Process` sobre el proceso real de uvicorn (el `.venv` lanza un proceso hijo;
el que atiende es el hijo), en reposo, después de arrancar:

```
WorkingSetMB : 141.5    PrivateMB : 124.7    Threads : 8
```

(El lanzador del `.venv` son 4 MB aparte.) Ese número es el que manda al dimensionar: cada
worker que se añada cuesta **~150–200 MB** (lo medido en reposo, más lo que crezca con las
peticiones), y PostgreSQL y Caddy también piden su parte. **ESTIMACIÓN**: con 4 GB de RAM y
PostgreSQL en la misma máquina caben 2–3 workers con holgura; con 4 ya es apretar.

---

## 7. Modelo de capacidad y cuántos agricultores aguanta hoy

### 7.1. El techo del servidor, medido

| Concurrencia (a la vez) | p95 con 100.000 | p95 con 240.000 (producción) | Veredicto |
|---|---|---|---|
| 1 | 130 ms | 234 ms | Bien |
| 5 | 171 ms | 349 ms | Bien |
| 10 | 286 ms | 455 ms | **Bien** (el número que se defiende) |
| 25 | 630–895 ms | 775–821 ms | **Rodilla**: se dobla o triplica |
| 50 | 1.783 ms | 1.621 ms | Mal: más de segundo y medio |
| 100 | — | — | **Se atasca**: todas las peticiones agotan 20 s |

A esto se suma:

- **Un solo proceso uvicorn** (apartado 6.1).
- **40 hilos** para las peticiones y **15 conexiones de base por proceso** (6.2 y 6.3):
  con 25 usuarios ya hay cola para una conexión.
- **SQLite con un solo escritor y sin WAL** (6.4): cada apunte se pone en fila.
- **280 ms de CPU por entrada** (6.5): el que más pesa en cada recorrido.
- **~142 MB por proceso** (6.9).
- **Fincas de 64 tierras son más lentas** en todos los escalones (4.4).

### 7.2. Cuántos agricultores de verdad: **ESTIMACIÓN**

Esto **no está medido** (haría falta gente de verdad usándolo y observabilidad en
producción). Se puede acotar con lo medido y con hipótesis que se dicen:

- Un agricultor hace, como mucho, **un recorrido de 5 peticiones por visita** y abre el
  cuaderno **3–4 veces al día** → **15–20 peticiones al día**.
- **Techo del servidor**: ~50 peticiones/s con p95 aceptable (a 10 usuarios se midieron
  65 peticiones/s con p95 286 ms; a 50, 49 peticiones/s con p95 1,8 s). Tomamos **50/s**
  como cifra prudente.
- **Uso repartido**: si 200 agricultores hacen 20 peticiones al día son 4.000 peticiones
  al día; puestas en una hora punta que concentre el 25 % son 1.000 peticiones/hora =
  **0,28 peticiones/s**. El servidor, a 50/s, ni se entera.
- **El problema no es el total, son las coincidencias.** Si 250 agricultores abren el
  cuaderno en el mismo par de minutos (aviso de lluvia, primer día de plazo, cierre de
  campaña), son ~1.250 peticiones en un par de minutos ≈ 10 peticiones/s, con picos de
  decenas de peticiones simultáneas: **ahí ya se llega a la rodilla**.

**Conclusión, marcada como ESTIMACIÓN**:

> Con este servidor (un proceso uvicorn + SQLite + 6 núcleos), **del orden de 150–300
> agricultores activos al día** con uso repartido deberían ir bien. La cifra que hay que
> vigilar no es la de cuentas: es **20–25 agricultores usándolo en el mismo par de
> minutos**, que es donde está la rodilla. Si la campaña concentra las visitas (todos
> abren a la misma hora), el primero que nota la lentitud es el número ~25, no el ~250.

Hipótesis que, si cambian, cambian la estimación: 3–4 visitas al día por agricultor, 5
peticiones por visita, 25 % del tráfico en la hora punta, y una máquina como la medida
(6 núcleos) **sin otros procesos** (la medida se hizo con la máquina al 100 % por otros
programas, así que la cifra real podría ser algo mejor). La prueba con agricultores de
verdad es la que falta (apartado 9).

### 7.3. Qué cambia con PostgreSQL

- **Desaparece el único escritor**: apuntar tratamiento deja de hacer cola detrás de los
  demás. Es el cambio que más ayuda con muchos agricultores a la vez.
- **Se puede ajustar el pool** (hoy 5+10 por proceso). Con PostgreSQL tiene sentido subirlo,
  pero **cada worker tiene su propio pool**: 4 workers × 20 conexiones = 80 conexiones a
  la base; hay que contarlas y, si hace falta, poner PgBouncer delante.
- **Cada worker ejecuta `crear_tablas` al arrancar** (6.8): con varios workers hay que
  sacar la preparación del arranque o arrancarlos de uno en uno, o se pisan.
- **La latencia por consulta no mejora sola**: las consultas son sencillas y en local
  SQLite es rapidísimo. La ganancia es de **concurrencia**, no de velocidad por petición.

**No medido**: no hay PostgreSQL instalado en esta máquina, así que no se ha medido esta
prueba contra él. Se dice, no se inventa.

### 7.4. Qué cambia con más workers (`--workers`)

- **2–4 workers multiplican los hilos (40 cada uno) y las conexiones (15 cada uno)**, y el
  PBKDF2 se reparte entre procesos: con 6 núcleos, **2–4 workers es lo razonable**.
- **Con SQLite, no se debe**: cada worker es un escritor más y los bloqueos empeoran. Los
  workers van **con PostgreSQL**.
- La ganancia no es lineal: a partir de 3–4 workers, el cuello pasa a la base de datos y a
  la CPU total de la máquina.
- **ESTIMACIÓN**: pasar de 1 a 3 workers con PostgreSQL debería multiplicar por ~2–3 la
  capacidad de usuarios concurrentes (de ~10 a ~20–30), no por 3 exacto. Se comprobará con
  esta misma prueba cuando haya PostgreSQL.

### 7.5. El umbral que obliga a escalar

Señales de que **hay que escalar ya** (cualquiera de ellas):

1. **20–25 usuarios a la vez** en el servidor (peticiones simultáneas), aunque no haya
   errores.
2. **p95 de entrada (login) por encima de 1.000 ms** medido en el servidor en una hora
   punta (sin contar la red móvil). Hoy, con producción configurada, a 25 usuarios ya está
   en ~0,8 s: se llega antes de lo que parece.
3. **Cualquier error 5xx o «base de datos bloqueada»** en el registro.
4. **CPU del servidor por encima del 70 % de forma sostenida** en la hora punta.
5. **Cola de subidas de fotos o de PDF** que haga esperar a las pantallas normales.

Qué hacer en ese momento, por orden:

1. **PostgreSQL** (el cambio que más alivia: quita el único escritor) y **2–4 workers**
   detrás de Caddy/nginx, arrancando la preparación una sola vez.
2. **Ajustar el pool** de conexiones por worker y contar el total.
3. **Sacar los estáticos** (React, CSS, imágenes) al proxy, que hoy los sirve el mismo
   proceso de uvicorn.
4. **Separar el PDF y los adjuntos** si empiezan a molestar: el PDF, a un worker aparte o
   a una cola; los adjuntos, a un volumen aparte (hoy ya van a disco, no a la base).
5. **Límite de intentos de entrada** (y, si se puede, caché de la clave derivada mientras
   el token vive): hoy cada entrada son 280 ms de CPU y no hay tope.

### 7.6. El coste, en recursos

- **CPU**: ~142 MB de RAM por proceso (6.9) y el servidor se satura con 25 usuarios en
  una máquina de 6 núcleos compartida. Con PostgreSQL y 3 workers, la misma máquina
  debería aguantar 2–3 veces más (estimación de 7.4).
- **Disco**: la base no guarda los adjuntos (van a disco, hasta 12 MB por foto). La prueba
  no ha medido el disco; ver lo que falta en el apartado 8.
- **Dinero**: no es objeto de esta prueba (el documento de despliegue pone servidores y
  precios con su fuente). Aquí queda medido **cuánto consume** para poder dimensionar.
  **ESTIMACIÓN**: un servidor de 2 vCPU/4 GB es el mínimo razonable para empezar; con 6
  núcleos se llega a los 10–25 usuarios concurrentes medidos en esta aplicación.

---

## 8. Qué NO mide esta prueba (y no hay que creerse que lo mide)

- **La red móvil de verdad**: cobertura, pérdida de paquetes, latencia de 4G, el móvil de
  gama baja del agricultor. La prueba es toda en `127.0.0.1`: lo medido es **el servidor**.
- **El SIGPAC y el IGN**: el mapa, la ortofoto y las consultas oficiales salen a internet
  y no están en el recorrido. Una parcela traída desde el SIGPAC o una foto del mapa
  cuestan mucho más que lo medido aquí.
- **El disco**: escritura de adjuntos, `fsync` de SQLite, tamaño de la base con años de
  apuntes, copias de seguridad y restauración.
- **El OCR** (Tesseract) y la lectura de facturas (pdfplumber): son trabajo de CPU que no
  se ha tocado.
- **El PDF del cuaderno** (reportlab): no se ha medido. Con un año de apuntes es la
  petición más pesada que puede pedir un agricultor.
- **La subida de fotos**: no se ha subido ningún fichero. 12 MB por foto, en memoria y a
  disco, es lo que dicen el código y los límites.
- **TLS, Caddy/nginx y el proxy**: no hay proxy en la prueba; en producción añade su coste
  (pequeño, pero no medido aquí).
- **El navegador**: descargar el React, pintar, el JavaScript del móvil. Aquí solo se mide
  la API.
- **Datos de verdad acumulados**: la prueba usa fincas nuevas con 10 o 64 tierras y pocos
  apuntes; una finca con años de tratamientos, abonos y análisis tendrá listados y cuadernos
  más pesados.
- **Varios workers y PostgreSQL**: no medido (no hay PostgreSQL en esta máquina).
- **Ataques y abusos**: no se prueba el límite de intentos (no existe) ni el agotamiento
  de CPU por peticiones de entrada.

---

## 9. El plan sencillo para David

1. **Ahora no hay que comprar nada**: con 10 usuarios a la vez va bien, y los primeros
   agricultores no van a coincidir.
2. **Antes de abrir a un grupo de verdad, medir otra vez con la máquina quieta**:
   ```powershell
   ..\.venv\Scripts\python.exe scripts\prueba_de_carga.py --escalones 1,5,10,25,50 --peticiones-por-usuario 2
   ..\.venv\Scripts\python.exe scripts\prueba_de_carga.py --escalones 1,5,10,25 --iteraciones-pbkdf2 240000
   ```
   Apuntar la tabla en este documento, con fecha y máquina. Si la rodilla sigue en 10–25,
   no se toca nada.
3. **Piloto con 5–10 agricultores de verdad** (los del cliente de Salamanca sirven), con
   la observabilidad puesta (otro entregable) y alguien mirando el p95 de entrada. Es la
   única prueba que mide la red móvil y el uso real.
4. **Elegir el disparador**: cuando en el piloto se vea **20–25 usuarios a la vez** o el
   **p95 de entrada pase de 1 s**, se pasa a PostgreSQL + 2–3 workers (apartado 7.5) y se
   repite esta misma prueba para comprobar la mejora.
5. **Probar aparte, antes de abrir**: la subida de una foto de 12 MB, la generación del PDF
   del año y una finca de 64 tierras con datos. No están medidos aquí.

---

## 10. Anexo: todo lo medido, con su comando y su fecha

Máquina: AMD Ryzen 5 3600 (6 núcleos / 12 hilos), 31,9 GB, Windows 11, Python 3.12.10,
SQLite 3.49.1. CPU al 100 % por otros procesos durante toda la tanda. Todo el 09/11/2026.

| Qué | Cómo se produce | Resultado |
|---|---|---|
| Rodilla con 10 tierras, 100.000 iteraciones | `python scripts/prueba_de_carga.py --escalones 1,5,10,25,50 --peticiones-por-usuario 2` | Rodilla a 25 usuarios (p95 630–895 ms, ×2,5–3,1). Ver 4.1 y 4.2. |
| 50 usuarios | `... --escalones 25,50` o `--escalones 50` | p95 1.783 ms, 0 errores, 49 peticiones/s. |
| 100 usuarios | `... --escalones 100` | 100 errores (timeout de 20 s), p50 20,4 s. El servidor no se cae. |
| Finca de 64 tierras | `... --escalones 1,5,10,25 --tierras-por-usuario 64 --peticiones-por-usuario 4` | p95 a 25 = 886 ms, ×2,48 (en el filo). Ver 4.4. |
| Configuración de producción | `... --escalones 1,5,10,25 --iteraciones-pbkdf2 240000 --peticiones-por-usuario 2` | p95 a 10 = 455 ms; a 25 = 775–821 ms. Ver 4.5. |
| Producción a 25 y 50 | `... --escalones 25,50 --iteraciones-pbkdf2 240000 --peticiones-por-usuario 2` | 25: 821 ms; 50: 1.621 ms (rodilla). |
| Coste de PBKDF2 | one-liner de 6.5 | 100.000: 98,3 ms; 240.000: 280,4 ms (mediana). |
| Pool de la base | one-liner de 6.3 | QueuePool, 5 + 10, espera 30 s. |
| Hilos para peticiones | one-liner de 6.2 | 40. |
| Arranque y esquema | one-liner de 6.8 | ~5,3 s en base nueva. |
| Memoria por proceso | `Get-Process` sobre el uvicorn real (6.9) | ~142 MB de memoria de trabajo, 8 hilos. |
| Pruebas del guion | `..\.venv\Scripts\python.exe -m pytest tests/test_prueba_de_carga.py -q` | **35 superadas, 0 fallos**. |

Para comprobar que no queda ningún servidor de la prueba escuchando:

```powershell
Get-NetTCPConnection -LocalPort <el-puerto-que-salga> -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
    Where-Object { $_.CommandLine -like '*app.main:app*' -and $_.CommandLine -notlike '*runner.js*' }
```

En todas las pasadas de este documento, el guion apagó su uvicorn, comprobó que el puerto
quedaba cerrado y borró su carpeta temporal. No quedó ningún proceso escuchando.
