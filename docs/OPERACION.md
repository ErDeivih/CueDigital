# Operar CUE Digital (D06)

> **Para quién es esto:** para quien instala, copia, restaura o retira un acceso en un
> servidor donde corre CUE Digital. No es documentación para el agricultor. Todo lo que
> aquí se escribe está comprobado contra el código de este repositorio; lo que **no** está
> hecho se dice en el último apartado y no se rellena con una suposición.

Este documento existe porque `backend/scripts/copiar_la_base.py` lo cita: la copia que
genera **no cifra** y **no decide la retención**, y esas dos cosas son decisiones de
despliegue, no del programa. Aquí se dice cuáles están tomadas y cuáles no.

---

## 1. Arrancar el programa

```bash
cd backend
# Windows
../.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
# Linux
../.venv/bin/python -m uvicorn app.main:app --port 8000
```

Si no existe el entorno:

```bash
cd backend && python -m venv ../.venv && ../.venv/Scripts/python.exe -m pip install -r requirements.txt
```

- La pantalla se sirve como ficheros estáticos desde el mismo servidor: **no hay compilación
  de producción** ni hace falta Node para atender a nadie (`AGENTS.md` §3.7).
- **Comprobación de que está vivo:** `GET /health` responde
  `{"estado": "ok", "zonas_vulnerables_cargadas": <true|false>}`. Es lo que debe usar el
  vigilante del despliegue. `GET /api` devuelve el nombre del programa y la dirección de la
  documentación de la API.
- El estado de «zonas vulnerables cargadas» es informativo: si es `false`, el programa
  funciona, pero no puede decir si una parcela está en zona vulnerable. **No se rellena a
  mano**: el listado se carga de la fuente oficial.

## 2. Variables de entorno

Todas son opcionales en local. En un servidor expuesto, las marcadas como obligatorias lo son.

| Variable | Por defecto | Para qué |
|---|---|---|
| `CUEDIGITAL_DATABASE_URL` | `sqlite:///./cuedigital.db` | Dónde vive la base. SQLite en local; PostgreSQL/PostGIS en producción (misma capa de SQLAlchemy). |
| `CUEDIGITAL_ADJUNTOS` | `datos/adjuntos` junto al proyecto | Carpeta de los ficheros que sube el agricultor (boletines, facturas). **Fuera del repositorio** y en el `.gitignore`: llevan su NIF. |
| `CUEDIGITAL_ENTORNO` | vacío (local) | `produccion` (también valen `producción`, `prod`, `production`). Activa las comprobaciones que no pueden fallar en producción, empezando por el secreto. |
| `CUEDIGITAL_SECRETO` | se genera al azar en local | **Obligatoria en producción.** Firma los vales de sesión. Si falta o es más corta que el mínimo, el programa **no arranca** (es a propósito: arrancar con un secreto de mentira da sesiones que cualquiera puede fabricar). |
| `CUEDIGITAL_SECRETO_ANTERIOR` | vacío | El secreto que se acaba de sustituir. Se usa **solo para comprobar** vales ya emitidos, de modo que rotar el secreto no expulsa a todo el mundo. Se puede retirar cuando hayan caducado los vales viejos (30 días, ver §4). |
| `CUEDIGITAL_CONFIAR_EN_CABECERAS` | desactivado | `1`, `true`, `si` o `sí`. Solo se pone cuando hay **delante** un proxy que él mismo pone y quita las cabeceras del certificado. Si se activa sin ese proxy, cualquiera puede mandar la cabecera y decir que es otro. |
| `CUEDIGITAL_CABECERA_CERTIFICADO` | `X-SSL-Client-Subject` | La cabecera donde el proxy deja el certificado del cliente. |
| `CUEDIGITAL_CABECERA_VERIFICACION` | `X-SSL-Client-Verify` | La cabecera donde el proxy deja si el certificado se verificó (`SUCCESS`). |

> **El secreto se genera fuera del repositorio y no se copia a ningún fichero que se suba.**
> Rotarlo: se pone el valor actual en `CUEDIGITAL_SECRETO_ANTERIOR`, se pone el nuevo en
> `CUEDIGITAL_SECRETO` y se reinicia. Cuando hayan pasado 30 días, se vacía el anterior.

## 3. Límites de intentos

Los números viven en un solo sitio (`backend/app/limites.py`) y no se tocan desde la
configuración:

| Qué se limita | Máximo | Ventana |
|---|---|---|
| Fallos al entrar con clave | 10 | 15 minutos |
| Altas de cuenta | 10 | 1 hora |
| Intentos con certificado | 30 | 1 hora |

- Se cuentan **a la vez por la dirección y por el correo** (o el NIF, en el certificado), para
  que ni una sola dirección ni una sola cuenta se puedan probar en bucle.
- **El contador vive en memoria y por proceso.** Al reiniciar se perdona; con varios procesos
  cada uno lleva el suyo. Esto es suficiente para el piloto y **no** sustituye a un cortafuegos
  ni a un limitador del proxy (ver §7).
- El programa **no lee `X-Forwarded-For`**: detrás de un proxy que no lo ponga, todas las
  peticiones parecen venir de la misma dirección y el límite por dirección se agota antes. Si
  se despliega detrás de un proxy, hay que saberlo y limitar también allí.

## 4. Sesiones: cuánto duran y cómo se cierran

- Un vale de sesión dura **30 días** y viaja en la cabecera de cada petición. Cada vale lleva
  la **versión de sesión** (`token_version`) de la cuenta.
- **Cambiar la clave cierra todas las sesiones abiertas de esa cuenta**: el script sube la
  versión y los vales antiguos dejan de valer en la siguiente petición.
- **Retirar el acceso a una persona:** poner `activo = False` en su fila de `usuario` de la
  base. En la siguiente petición se le contesta que la cuenta no está activa. **No hay todavía
  ni pantalla ni script para esto** (§7): es una operación sobre la base, con el programa
  parado o con cuidado, y queda anotada como pendiente.
- Para cambiar una clave desde el servidor (no hay «he olvidado mi clave»: el programa no manda
  correos, así que la salida es entrar en la máquina donde está la base):

```bash
cd backend
../.venv/Scripts/python.exe scripts/cambiar_la_clave.py --listar
../.venv/Scripts/python.exe scripts/cambiar_la_clave.py --correo <correo>     # la pide por teclado
```

Si se pasa `--clave "<nueva>"` queda en el historial de la consola: por eso no es la forma
recomendada. El mínimo son 8 caracteres, la misma regla que en el alta.

## 5. Copia de seguridad

**Cada cuánto:** no lo decide el programa. Para el piloto, como mínimo **una vez al día** y
**antes de cada actualización**. La copia no cifrada no se deja en un sitio del que se pueda
descargar sin permiso (§7).

```bash
cd backend
../.venv/Scripts/python.exe scripts/copiar_la_base.py --origen <carpeta-de-datos> --destino <carpeta-de-la-copia>
```

Qué deja en la carpeta de la copia:

- `cuedigital.db`, hecha con **`VACUUM INTO`**, no copiando el fichero: así la copia es
  coherente **aunque haya escrituras abiertas**, y no se pilla el `-wal` a medias. La base se
  busca por nombre (`cuedigital.db`, y si no `prueba.db`, `humo.db`, o el primer `*.db`), que es
  lo que dice `database.py`.
- `adjuntos/`, tal cual, con los ficheros que subió el agricultor.
- `manifiesto.json` con la versión del programa, la fecha, la integridad, el número de tablas
  y de adjuntos, y **`"cifrado": false`** con su nota. El manifiesto no miente: si algún día se
  cifra, se cambia ahí y en este documento.

**Comprobar una copia sin restaurarla** (abre la base, mira la integridad y **abre cada
documento** que la base referencia, comprobando que existe y que no está vacío):

```bash
../.venv/Scripts/python.exe scripts/copiar_la_base.py --comprobar <carpeta-de-la-copia>
```

**El ensayo completo, de punta a punta** (levanta un servidor con datos, copia, levanta otro
servidor en otro puerto sobre la copia y comprueba que se entra y que los datos están):

```bash
../.venv/Scripts/python.exe scripts/verificar_la_copia_y_la_restauracion.py
```

No lleva argumentos: usa una base y una carpeta temporales, y no toca los datos de nadie.

## 6. Restaurar y deshacer una migración

**Restaurar en un destino nuevo** es copiar la carpeta de la copia al sitio de datos y apuntar
`CUEDIGITAL_DATABASE_URL` / `CUEDIGITAL_ADJUNTOS` ahí. **Con el programa parado.** Después,
`GET /health` y entrar con una cuenta real.

**Volver atrás una migración** (o una actualización) tiene un guion propio, porque copiar la
copia encima **no basta**:

```bash
cd backend
../.venv/Scripts/python.exe scripts/deshacer_la_migracion.py --base <fichero-de-la-base>              # la copia más nueva de al lado
../.venv/Scripts/python.exe scripts/deshacer_la_migracion.py --base <fichero> --copia <otra>          # una copia concreta
../.venv/Scripts/python.exe scripts/deshacer_la_migracion.py --base <fichero> --mirar                 # solo enseña qué haría
```

Por qué no basta con copiar: si al lado de la base hay un `-wal` (cambios confirmados que aún
no han bajado al fichero principal), SQLite **reaplica el `-wal`** al abrir y lo escrito después
de la copia vuelve a estar ahí. El guion, en este orden y sin saltarse pasos:

1. Comprueba que la copia abre y está entera (`PRAGMA quick_check`). Si no, **no toca nada**.
2. Guarda el estado de ahora en `<base>.antes-de-deshacer-<marca>` (deshacer un deshacer también
   tiene que ser posible).
3. Pone la copia encima y **borra el `-wal` y el `-shm`** que hubiera al lado.
4. Comprueba el resultado: que abre, que está entera y que tiene **las mismas filas** que la copia.

Prefiere la copia **byte a byte** que deja la migración (`.antes-de-migrar-…-byte-a-byte`) si
existe; si solo está la coherente, también sirve. **Con el programa parado.**

El detalle medido de esta mecánica, con lo que falló y cómo se comprobó, está en
[`ACEPTACION_COPIA_Y_MIGRACION.md`](ACEPTACION_COPIA_Y_MIGRACION.md).

## 7. Lo que este documento deja pendiente, dicho

Estas cosas **no están resueltas** y no se pueden dar por hechas al desplegar:

1. **Cifrado de las copias.** Hoy la copia va sin cifrar (`manifiesto.json` lo dice). Hay que
   decidir el mecanismo (cifrado en reposo del destino, `age`/GPG con la clave fuera del
   servidor, o disco cifrado) y **dónde** se guarda.
2. **Retención y sitio de las copias.** No hay rotación automática ni copia fuera de la máquina.
   Hay que decidir cuántas se guardan, durante cuánto tiempo, y a qué destino (otra máquina,
   almacenamiento del proveedor). Una copia en el mismo disco que la base no protege de un
   disco roto.
3. **TLS.** El programa no termina TLS: delante tiene que haber un proxy (o el proveedor) con
   certificado. Sin TLS, la clave y el vale de sesión viajan legibles.
4. **Certificados de cliente.** Para usar el certificado del agricultor hay que activar
   `CUEDIGITAL_CONFIAR_EN_CABECERAS` **solo** cuando el proxy esté puesto y verificado.
5. **Limitador compartido.** El de `limites.py` es por proceso y en memoria: con varios
   procesos o con un proxy delante, el límite efectivo no es el de la tabla de §3. Hace falta
   limitar también en el proxy o mover el contador a la base.
6. **Script para retirar un acceso.** Hoy se hace poniendo `activo = False` a mano (§4). Debería
   ser un guion como `cambiar_la_clave.py`, con su prueba.
7. **Nada de esto se ha ensayado en el servidor definitivo**, porque no hay hosting elegido. Los
   ensayos de copia y restauración se han hecho en local, en un entorno temporal y **sin datos
   reales de ningún agricultor**.
