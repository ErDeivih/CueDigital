# Cuentas y accesos: qué hace falta para que el cuaderno esté en internet

**Qué es este documento.** La lista de **cuentas, planes y pasos exactos** que faltan para
poner CUE Digital en una URL pública, con los límites reales de cada plan gratuito y con lo
que hay que pegar de vuelta para poder montarlo. Se escribió el **09/11/2026** y **todo lo que
no se ha podido comprobar se marca «no verificado»**: no se rellena con un número que suene
bien.

**Qué NO es.** No hay ninguna cuenta creada. **No se ha abierto una URL pública**: sin cuenta
de proveedor no hay máquina, sin dominio no hay certificado, y eso no lo puede hacer un
programa. Lo que sí está hecho y probado es el despliegue **en local**: la imagen
`deploy/Dockerfile` se construye (669 MB) y el stack de producción (uvicorn + PostgreSQL 16,
sin Caddy) arranca y pasa el recorrido completo; el detalle está en el informe de la tarea y
en `docs/DESPLIEGUE.md`.

| Dato | Valor |
|---|---|
| Fecha de consulta de los planes | **09/11/2026** |
| Imagen construida | `cuedigital:prueba`, **669 MB** (`docker images`) |
| Stack probado en local | app en **8090**, PostgreSQL 16 en **5434**, datos en `%TEMP%` |
| Recomendación primaria | **máquina virtual gratuita (Oracle Cloud Always Free) con el `docker-compose` tal cual** |
| Alternativa sin tarjeta | PaaS gratuito (Render + Neon), **con disco efímero: se pierden las fotos** → exige S3 antes |

---

## 1. La recomendación, en una frase y en una tabla

**Primaria: una VM gratuita con Docker y el `deploy/docker-compose.yml` sin tocar una línea.**
Es la única opción que cumple las tres cosas que la aplicación necesita de verdad: **disco que
no se borra** (las fotos y los boletines del agricultor), **PostgreSQL de verdad al lado** (sin
límite de plan ni suspensión por inactividad) y **HTTPS con dominio propio** (Caddy lo saca
solo). No hay que cambiar código.

| Pieza | Opción gratuita | Límite que importa | ¿Cumple? |
|---|---|---|---|
| Máquina | **Oracle Cloud Always Free** (Ampere A1) | 2 OCPU + 12 GB y 200 GB de disco, en la región de casa | **Sí**, con avisos (§3.3) |
| Sistema y TLS | Ubuntu + Caddy + Let's Encrypt | 0 € | Sí |
| Base de datos | PostgreSQL 16 en la misma máquina | la que quepa en el disco | Sí |
| Fotos y papeles | disco de la VM | ~30 GB útiles del disco | Sí |
| Copia fuera | Cloudflare R2 (10 GB/mes gratis) | 10 GB-mes | Sí, para el arranque |
| Dominio | el que David ya tenga | **no verificado** si hay uno gratis fiable | Hace falta uno |

**Alternativa sin tarjeta: PaaS gratuito (Render + Neon).** Sirve para enseñar la aplicación,
**no para guardar los papeles de un agricultor**: el disco de Render se borra en cada reinicio,
despliegue o apagado por inactividad, y su PostgreSQL gratuito **caduca a los 30 días**. Para
usarla de verdad habría que implementar **almacenamiento S3** (las fotos fuera del disco) antes
de abrirla a nadie. **Eso NO se hace en esta tarea** y es, hoy, un trabajo pendiente.

---

## 2. Qué cuentas hacen falta, una por una

| # | Cuenta | Para qué | ¿Imprescindible? |
|---|---|---|---|
| 1 | **Oracle Cloud** (o el proveedor de VM que se elija) | la máquina donde corre el `docker-compose` | Sí |
| 2 | **Un dominio** con acceso al DNS | el nombre público y el certificado de Caddy | Sí (Caddy no saca certificado de una IP) |
| 3 | **Cloudflare** (cuenta gratuita) | copia de seguridad **fuera** de la máquina (R2) | Recomendada desde el primer día |
| 4 | UptimeRobot | avisar si el servidor se cae | Recomendada |
| 5 | Render + Neon | **solo** si se elige la alternativa sin tarjeta | Solo en la opción B |
| 6 | Supabase / Backblaze B2 / Koyeb | alternativas; ver límites y por qué no son la primera opción | No |

Las cuentas **3, 4 y 5 no hacen falta para arrancar**: se pueden dejar para el segundo día,
pero la copia fuera (3) debería estar **antes** de que haya datos de un agricultor de verdad.

---

## 3. Opción A (recomendada): una VM gratuita — Oracle Cloud Always Free

### 3.1. Qué da el plan Always Free, tal y como está publicado (consultado 09/11/2026)

Fuente: [Oracle Cloud Infrastructure Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)
y [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

| Recurso | Lo que da Always Free | ¿Llega para CUE Digital? |
|---|---|---|
| **Cómputo Ampere A1** (`VM.Standard.A1.Flex`, ARM) | **2 OCPU y 12 GB de memoria en total** (1.500 horas-OCPU y 9.000 horas-GB al mes) | **Sí, de sobra.** El despliegue recomienda 2 vCPU / 4 GB; con 2/12 hay margen para el OCR |
| **Cómputo AMD** (`VM.Standard.E2.1.Micro`) | **2 VM**, cada una **1/8 de OCPU y 1 GB de RAM** | Justo: 1 GB para app + PostgreSQL + Caddy va muy apretado y el OCR se queda sin aire |
| **Disco (Block Volume)** | **200 GB en total**, sumando volúmenes de arranque y de datos; el de arranque **mínimo 47 GB** (50 GB por defecto) | **Sí.** El despliegue pide 40 GB; con 50 GB de arranque + un volumen de datos hay sitio para la caché del SIGPAC (1,7 GB) y las fotos |
| **Almacenamiento de objetos** | 20 GB | No hace falta: los papeles van al disco de la VM |
| **Salida de datos** | **10 TB/mes** | Sí, muchísimo más de lo que gasta un cuaderno |
| **Región** | **solo la región de casa** (home region) | Elegir una **europea** al registrarse (el RGPD manda dónde están los datos) |
| **Tarjeta** | «most users need a mobile phone number and a **credit card** to create an account»; **no se cobra** mientras no se pase a cuenta de pago | Es el pero de esta opción: **pide tarjeta** (ver §3.3) |

### 3.2. Los pasos, numerados

1. **Crear la cuenta** en <https://signup.cloud.oracle.com/> con el correo de David.
   - Elegir como **home region una de la UE** (por ejemplo, Fráncfort o Madrid si aparece).
     **La región no se puede cambiar después** sin crear otra cuenta.
   - Verificar el correo y el móvil, y añadir la tarjeta cuando la pida (no se cobra).
2. **Crear la instancia de cómputo**: menú → *Compute* → *Instances* → *Create instance*.
   - **Imagen**: Ubuntu 24.04 (o la última 24.04 LTS que ofrezca).
   - **Shape**: `VM.Standard.A1.Flex` con **2 OCPU y 12 GB** (o `VM.Standard.E2.1.Micro` si no
     hay capacidad A1; entonces cuenta con 1 GB de RAM y menos margen).
   - **Boot volume**: 50 GB (o crear además un volumen de datos y montarlo en
     `/srv/cuedigital/datos`).
   - **Clave SSH**: descargar la clave privada y guardarla; **no se pega en ningún chat**.
3. **Abrir los puertos** en la red virtual (VCN): *Security List* → *Add ingress rule* para
   **22/tcp, 80/tcp y 443/tcp** desde `0.0.0.0/0` (solo esos tres; la base de datos **no** se
   publica).
4. **Entrar por SSH** y preparar la máquina: seguir `deploy/LEEME.md` desde el apartado 1
   (paquetes, `ufw`, Docker y el complemento `compose`).
5. **Traer el repositorio y la configuración**: `git clone`, `cp deploy/.env.example
   deploy/.env`, `chmod 600`, y rellenar `DOMINIO`, `POSTGRES_PASSWORD`,
   `CUEDIGITAL_DATABASE_URL`, `CUEDIGITAL_SECRETO`, `CARPETA_DATOS` y las dos de la
   observabilidad (`CUEDIGITAL_OBSERVABILIDAD` y `CUEDIGITAL_OBSERVABILIDAD_TOKEN`).
6. **El DNS antes que Caddy**: en el panel del dominio, un registro **A** del nombre elegido
   a la **IP pública** de la instancia. Comprobar con `dig +short <dominio>` desde otra
   máquina; **no seguir hasta que devuelva la IP**.
7. **Arrancar**: `docker compose -f deploy/docker-compose.yml up -d --build`.
8. **Comprobar**: `cd backend && python3 scripts/comprobar_despliegue.py https://<dominio>`
   (sale 0 si todo va bien) y mirar que `/api/observabilidad/resumen` contesta 200 con el
   token de `deploy/.env`.

**Comprobación de cada paso:** la del `deploy/LEEME.md` (los tres contenedores en marcha, 66
tablas en PostgreSQL, `curl -I https://<dominio>` con certificado de fiar, `/health` en 200).

### 3.3. Los tres avisos que no se pueden callar

1. **Pide tarjeta.** Es un requisito de Oracle para la mayoría de las cuentas («most users need
   a mobile phone number and a credit card»), no un cobro: **la tarjeta no se carga mientras no
   se pase a cuenta de pago**. Si David no quiere dar tarjeta, la opción es la B (§4).
2. **Oracle puede reclamar las instancias Always Free que estén ociosas.** Lo dice su
   documentación: si durante **7 días** la CPU (p95) está por debajo del **20 %**, la red por
   debajo del 20 % y —en las Ampere A1— la memoria por debajo del 20 %, **la instancia puede
   reclamarse**. Un cuaderno de campo con poco tráfico **parece ocioso**. Mitigaciones:
   - usar la forma **AMD** (la condición de memoria no se aplica a esas), a cambio de 1 GB de
     RAM;
   - o pasar la cuenta a **Pay As You Go** (Oracle dice que los recursos Always Free siguen
     siendo gratuitos; **no verificado** que eso quite la reclamación por inactividad);
   - y tener **copia de seguridad fuera** (R2) desde el primer día, que es la regla de la casa.
   **No verificado en la práctica**: no se ha podido comprobar si Oracle reclama de verdad una
   instancia con este patrón de uso. Es un riesgo, no una certeza.
3. **«Out of host capacity».** Es habitual al crear la instancia A1 en la región de casa: no hay
   hueco. Se prueba en otra zona de disponibilidad o se espera; **no es un fallo de la cuenta**.
   Si se agota la paciencia: forma AMD, u otro proveedor (Hetzner CX23, 5,99 €/mes sin IVA,
   ver `docs/DESPLIEGUE.md` §2.1).

### 3.4. Qué debe pegar David de vuelta (sin secretos)

- [ ] **IP pública** de la instancia y **región** (para comprobar que es la UE).
- [ ] **Forma y tamaño**: «A1, 2 OCPU / 12 GB» o «E2.1.Micro, 1 GB».
- [ ] **Usuario SSH** (normalmente `ubuntu`) y confirmación de que la clave la tiene él.
- [ ] **Dominio elegido** y confirmación de que el registro A ya devuelve la IP.
- [ ] El resultado de `docker compose -f deploy/docker-compose.yml ps` y del guion
      `comprobar_despliegue.py`.
- **NO pegar** en el chat: la clave privada SSH, `deploy/.env`, ni el token de la
  observabilidad.

---

## 4. Opción B (sin tarjeta): PaaS gratuito — Render + Neon

Sirve para **una demostración**, no para producción, y el motivo no es el precio: es que **el
disco se borra** y **la base caduca**. Está contado en `docs/DESPLIEGUE.md` §3.2.

### 4.1. Render (la aplicación)

Fuente: [Deploy for Free](https://render.com/docs/free) y [Regions](https://render.com/docs/regions)
(consultadas 09/11/2026).

| Límite | Valor publicado |
|---|---|
| Cómputo gratuito | **0,1 CPU / 512 MB de RAM** |
| Se apaga por inactividad | **a los 15 minutos** sin tráfico; tarda ~1 minuto en despertar |
| Horas | **750 horas de instancia al mes**; agotadas, suspende los servicios gratuitos hasta el mes siguiente |
| Disco | **efímero**: lo escrito se pierde en cada reinicio, despliegue **y apagado**; el plan gratuito **no** admite disco persistente |
| PostgreSQL gratuito | **1 GB** y **caduca a los 30 días** (14 días de gracia y se borra), sin copias |
| Región europea | sí: **Fráncfort (Alemania)** |
| Dominio y TLS | incluidos (certificado gestionado) |

**Consecuencia para CUE Digital:** las fotos, los boletines y los PDF subidos **se pierden**;
la base de datos **desaparece al mes**. Para usarlo en serio hay que (a) implementar
almacenamiento S3 para los adjuntos y (b) pagar un PostgreSQL o migrar a Neon. **Nada de eso
se hace en esta tarea.**

### 4.2. Neon (la base de datos)

Fuente: [Neon Free plan limits](https://neon.com/faqs/free-plan-limits-and-quotas)
(consultada 09/11/2026).

| Límite | Valor publicado |
|---|---|
| Almacenamiento | **1 GB por proyecto** (20 GB por cuenta) |
| Cómputo | **100 horas-CU por proyecto y mes** (≈ 400 h de una instancia de 0,25 CU) |
| Suspensión | **a los 5 minutos** de inactividad, **no se puede desactivar** |
| Transferencia | 5 GB por proyecto y mes |
| Proyectos | 100, con 10 ramas cada uno |
| Región europea | **no verificado en la consulta** (hay regiones en la UE, pero no se leyó el listado) |

**Consecuencia:** la primera petición del domingo por la mañana paga el desperezar de la base
(unos segundos). No es grave para una demo; para el campo, sí.

### 4.3. Los pasos, numerados (si se elige esta opción)

1. **Neon**: crear cuenta en <https://console.neon.tech/signup> → *Create project* → región
   europea si está disponible → copiar la **cadena de conexión** (`postgresql://…`), que se
   guarda en `deploy/.env` como `CUEDIGITAL_DATABASE_URL` (con el prefijo
   `postgresql+psycopg://`). **No se pega en el chat.**
2. **Render**: crear cuenta en <https://dashboard.render.com/register> → *New* → *Web Service*
   → conectar el repositorio → **Docker** → `deploy/Dockerfile` → región **Frankfurt** →
   plan **Free**.
   - Variables de entorno: `CUEDIGITAL_DATABASE_URL` (la de Neon), `CUEDIGITAL_SECRETO`,
     `CUEDIGITAL_ADJUNTOS=/tmp/adjuntos`, `CUEDIGITAL_SIGPAC_CACHE=/tmp/sigpac_cache`,
     `CUEDIGITAL_OBSERVABILIDAD` vacía, `CUEDIGITAL_OBSERVABILIDAD_TOKEN`.
   - **Ojo**: en Render el puerto lo marca `$PORT`; esta imagen escucha en **8000** fijo. Para
     la demo hay que mapear el puerto en el panel o cambiar el `CMD` en una copia del
     Dockerfile. **No verificado** cuál de las dos cosas admite el plan gratuito hoy.
3. **Supabase** (solo si se quiere Storage en vez de S3 propio): ver §5.3.
4. **Comprobar**: `python3 backend/scripts/comprobar_despliegue.py https://<servicio>.onrender.com`.
   La comprobación de los adjuntos **fallará a propósito** en cuanto el servicio se reinicie:
   es el límite del plan, no un fallo del programa.

### 4.4. Qué debe pegar David de vuelta

- [ ] La **URL** del servicio de Render (`https://<algo>.onrender.com`).
- [ ] El **host y el plan** de Neon (sin la contraseña).
- [ ] El resultado del guion de comprobación.
- **NO pegar**: la cadena de conexión con contraseña, ni `deploy/.env`.

---

## 5. Almacenamiento de las fotos (si algún día se separa del servidor)

Hoy los adjuntos se escriben **en el disco** (`backend/app/adjuntos.py`): no hay conector S3 y
**no se implementa en esta tarea**. Esta tabla es para decidir cuando toque; los precios y
límites son los publicados el 09/11/2026.

| Opción | Plan gratuito | Al superarlo | Fuente |
|---|---|---|---|
| **Cloudflare R2** | **10 GB-mes**, **1 millón** de operaciones A y **10 millones** B al mes; **salida gratis** | 0,015 $/GB-mes y 4,50 $/millón de operaciones A | <https://developers.cloudflare.com/r2/pricing/> (página actualizada el 30/10/2026) |
| **Backblaze B2** | **no verificado**: la tabla de precios de la página oficial no se pudo leer en la consulta (se sirve con JavaScript) | — | <https://www.backblaze.com/cloud-storage/pricing> |
| **Supabase Storage** | **1 GB** de ficheros, 5 GB de salida en caché, **subida máxima de 50 MB** por fichero, 2 proyectos activos | plan Pro desde **25 $/mes**: 100 GB de ficheros incluidos | <https://supabase.com/pricing> |

**Lo que se recomienda:** para el arranque, **los adjuntos en el disco de la VM** (es lo que la
aplicación ya sabe hacer) y **R2 para la copia de fuera** (10 GB gratis cubren la base y los
papeles de los primeros agricultores). R2 también es la opción natural para las fotos el día
que se separen del servidor, pero **eso exige tocar `adjuntos.py`**: es una tarea aparte.

---

## 6. Supabase y Koyeb: por qué no son la primera opción

### 6.1. Supabase

Fuente: <https://supabase.com/pricing> (consultada 09/11/2026).

| Límite del plan Free | Valor |
|---|---|
| Base de datos | **500 MB** (CPU compartida, 500 MB de RAM) |
| Ficheros | **1 GB** |
| Salida | 5 GB |
| Proyectos activos | **2** |
| **Se pausa** | **tras 1 semana de inactividad** |
| Copias automáticas | **no incluye** |

**Por qué no:** 500 MB de base y 1 GB de ficheros se quedan cortos para varios agricultores; y
una base que **se pausa sola a la semana** es justo lo contrario de lo que necesita un cuaderno
que se abre en el campo. Como **complemento** (solo Storage, o un proyecto de pruebas) sí vale.

### 6.2. Koyeb

Fuente: <https://www.koyeb.com/pricing> (consultada 09/11/2026).

- **No hay plan gratuito para quien se registra hoy**: el plan más barato es **Pro, 29 $/mes**
  más consumo (10 $ de cómputo incluidos). Antes había un plan Starter gratuito (512 MB, 0,1
  vCPU, 2 GB de SSD), pero está **cerrado a nuevos registros** y solo se mantiene a las
  organizaciones que ya lo tenían. La página de precios lo confirma al no listar ningún plan
  de 0 $; el detalle del cierre se leyó en una nota de un tercero
  (<https://dev.to/build996/koyebs-starter-plan-closed-to-new-signups-kept-for-existing-orgs-30mh>,
  no es fuente oficial: **no verificado** en la web de Koyeb).
- Su PostgreSQL «Free 5h» (0,25 vCPU / 1 GB / 1 GB de disco) es una prueba por horas; **no
  verificado** el detalle de esas 5 horas.

**Por qué no:** sin plan gratuito, no ahorra nada frente a una VM de 6 €/mes (Hetzner) y sigue
teniendo el problema del disco efímero para las fotos.

---

## 7. Lo que queda bloqueado, y por qué

| Bloqueo | Por qué | Quién lo desbloquea |
|---|---|---|
| **No hay URL pública** | hace falta una cuenta de proveedor (y una tarjeta, en el caso de Oracle) y un dominio con DNS | David (10–20 minutos, §3.2) |
| **No hay certificado HTTPS** | Caddy lo pide validando el dominio; sin DNS no hay certificado | David, después del paso 6 |
| **No hay copia fuera de la máquina** | necesita la cuenta de Cloudflare (R2) y un token de API | David, antes de meter datos reales |
| **El IUWS (volcado a la Junta)** | necesita el **alta del dominio del certificado** en el interfaz de la Junta; es gestión de David, no del servidor | David / la Junta |
| **Fotos fuera del disco (S3)** | hay que implementar el conector en `adjuntos.py`; **no está hecho** y no se hace aquí | trabajo aparte |
| **Nada más del programa** | la imagen se construye y el recorrido completo pasa en local contra PostgreSQL | hecho |

---

## 8. Fuentes consultadas (09/11/2026)

- Oracle: [Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm) ·
  [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) ·
  [alta](https://signup.cloud.oracle.com/)
- Render: [Deploy for Free](https://render.com/docs/free) · [Regions](https://render.com/docs/regions)
- Neon: [límites del plan Free](https://neon.com/faqs/free-plan-limits-and-quotas)
- Supabase: [precios](https://supabase.com/pricing)
- Koyeb: [precios](https://www.koyeb.com/pricing)
- Cloudflare R2: [precios](https://developers.cloudflare.com/r2/pricing/)
- Backblaze B2: [precios](https://www.backblaze.com/cloud-storage/pricing) (tabla **no verificada**)
- Precios y alternativas de servidores: `docs/DESPLIEGUE.md` §2.1 (Hetzner, OVH, Contabo)
- Let's Encrypt y Caddy: <https://letsencrypt.org/> · <https://caddyserver.com/docs/automatic-https>

**Lo que se ha quedado «no verificado» y no se inventa:** la cuota exacta del plan gratuito de
Sentry; los precios de Backblaze B2; las horas exactas del PostgreSQL «Free» de Koyeb; el
listado de regiones europeas de Neon; si Oracle deja de reclamar instancias ociosas al pasar a
Pay As You Go; y el coste de un dominio.
