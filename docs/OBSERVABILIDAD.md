# Observabilidad del propio programa

Saber **qué falla, qué pantallas se usan y dónde se cae la gente** sin añadir nada que instalar
y sin que la herramienta pueda romper la aplicación ni molestar al agricultor.

Esto no es un servicio de terceros ni una plataforma de medidas: es código del propio programa
(`backend/app/observabilidad.py`) midiéndose a sí mismo **dentro del mismo proceso**. Coste:
**0 €**, ni una dependencia nueva, ni una cuenta que contratar.

## Qué se mide

| Qué | Dónde queda | Cuánto se guarda |
|---|---|---|
| **Errores** (5xx o excepción): marca de tiempo, tipo, método, ruta normalizada, código y mensaje corto | memoria (búfer circular) y, opcionalmente, JSONL | los **40** más recientes |
| **Uso por pantalla y día**: cuántas veces se abre cada vista de la app nueva | memoria y, opcionalmente, JSONL | **14 días**; **500** claves como mucho |
| **Duración por plantilla de ruta**: peticiones, cuenta por código de estado, p50 y p95 | memoria | **200** rutas; **64** duraciones por ruta |
| **Embudo**: cuentas → fincas → fincas con tierra → con algún apunte → con cuaderno firmado o exportado | se calcula **al pedir el resumen**, con SQL sobre las tablas que ya existen | no se guarda: se cuenta en el momento |

La ruta se guarda **por su plantilla, sin identificadores**: `/api/parcelas/17` y
`/api/parcelas/2031` son la misma fila (`/api/parcelas/{id}`). Es lo que hace que el resumen
hable de la aplicación y no de cada tierra de cada finca.

El embudo **no se inventa ni se instrumenta de más**: se apoya en `parcelas`, `labores`,
`tratamientos`, `fertilizaciones`, `siembras`, `firmas` y en el rastro de `auditoria`
(`sacar_el_cuaderno_de_la_junta`, que ya escribe la descarga del cuaderno de la Junta). Si a la
base le falta una tabla, esa etapa se queda en **«no se sabe»** y se dice por qué; nunca en un
cero que parezca un dato.

## Qué **no** se mide, y por qué

El cuaderno de un agricultor son datos suyos y de nadie más. Una herramienta de medida no es una
excusa para sacarlos de la explotación, así que **no se guarda**:

- **cuerpos de petición ni de respuesta** (pueden llevar su NIF, su correo, su nombre, una foto
  del cuaderno o su clave);
- **quién**: ni la cuenta, ni la IP, ni el vale;
- **datos del cuaderno** (tierras, tratamientos, importes, albaranes): no son métricas;
- **qué finca**: el embudo cuenta **fincas distintas por etapa**, nunca cuáles;
- **texto de pantalla nuevo**: aquí no hay ni una palabra visible para el agricultor; todo lo
  que lee sigue viviendo en `backend/app/textos.py`.

De un mensaje de error se tapan además correos, NIF/NIE y teléfonos antes de recortarlo, por si
el propio texto del fallo los llevara dentro.

## Cómo se enciende (y qué pasa si no se enciende)

Por defecto **no escribe nada en disco**. Ni ficheros, ni carpetas: las medidas viven en la
memoria del proceso y se pierden al reiniciar. Es lo que necesita una instalación normal y lo
que impide que la suite de pruebas ensucie el ordenador de quien la ejecuta.

Para conservar los errores y los avisos de pantalla entre reinicios se pone la variable
`CUEDIGITAL_OBSERVABILIDAD` con una carpeta o con un fichero:

```powershell
# Una carpeta: dentro se escribe observabilidad.jsonl
$env:CUEDIGITAL_OBSERVABILIDAD = "C:\CUE Digital\registro"

# O un fichero con su nombre
$env:CUEDIGITAL_OBSERVABILIDAD = "C:\CUE Digital\registro\observabilidad.jsonl"
```

El JSONL **gira** al llegar a **2 MB**, conservando **2 copias** (`observabilidad.jsonl.1` y
`.2`): un fichero que solo crece acaba llenando el disco de la instalación. Cada línea es un
error o un aviso de pantalla, en JSON, una por línea.

## Cómo se lee el resumen

El resumen está en `GET /api/observabilidad/resumen` y se protege con una cabecera, **no con la
sesión del agricultor**. Se configura su token:

```powershell
$env:CUEDIGITAL_OBSERVABILIDAD_TOKEN = "una-cadena-larga-y-propia"
```

Y se pide:

```bash
curl -H "X-Observabilidad: una-cadena-larga-y-propia" \
     http://127.0.0.1:8000/api/observabilidad/resumen
```

En PowerShell:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/observabilidad/resumen" `
  -Headers @{ "X-Observabilidad" = "una-cadena-larga-y-propia" }
```

Tres respuestas posibles y qué significa cada una:

- **404** — no hay `CUEDIGITAL_OBSERVABILIDAD_TOKEN` configurado: la puerta **no existe**, que es
  lo que se quiere por defecto. No está «abierta para cerrarla luego».
- **403** — hay token configurado y la cabecera falta o no coincide. La comparación se hace en
  tiempo constante (`hmac.compare_digest`), no con `==`.
- **200** — lo medido:
  - `errores_recientes`: de más nuevo a más viejo.
  - `pantallas`: `día`, `pantalla` y `veces`.
  - `rutas`: peticiones, cuenta por código, `muestras`, `p50_ms` y `p95_ms`.
  - `embudo`: una entrada por etapa con su `cuenta` (o `null` si no se ha podido medir) y la
    lista de `fallos` con el motivo.
  - `memoria` y `desde_el_arranque`: para no confundir «no hay nada» con «no se ha mirado».

El aviso de pantalla (`POST /api/observabilidad/pantalla`) es la otra puerta. La manda la app
nueva al cambiar de vista con `navigator.sendBeacon` (o `fetch` con `keepalive`, con su
`.catch(() => {})`) y **contesta siempre 204**, incluso con un cuerpo roto o vacío: un aviso del
móvil no puede convertirse en un error que el agricultor no ha provocado.

## Retención y límites

- **En memoria** (siempre): 40 errores, 500 claves de pantalla de 14 días, 200 rutas y 64
  duraciones por ruta. Los días viejos se purgan solos.
- **En disco** (solo si `CUEDIGITAL_OBSERVABILIDAD` está puesta): errores y avisos de pantalla,
  con 2 MB + 2 copias por fichero. Las **duraciones de las rutas no se escriben**: viven solo en
  memoria, porque son las que más cambian y las que menos aportan en un papel.
- **Si el proceso se reinicia**, se pierde todo lo que estaba en memoria: los contadores de
  pantalla, las duraciones y los errores que no se hubieran escrito. Con la variable puesta, los
  errores y los avisos de pantalla anteriores siguen en el JSONL; el embudo **no se pierde
  nunca**, porque se recalcula de la base cada vez que se pide.
- Un fallo de la observabilidad (disco lleno, carpeta sin permiso, un contador roto) **se traga
  y no llega al agricultor**: se pierde la métrica y la petición sigue. Está probado en
  `backend/tests/test_observabilidad.py`.
