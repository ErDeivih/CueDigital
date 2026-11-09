# Cómo se levanta CUE Digital en un servidor

Esto es la guía corta y ejecutable. Las decisiones, los precios, las alternativas y el
porqué de cada cosa están en [`../docs/DESPLIEGUE.md`](../docs/DESPLIEGUE.md); aquí
solo se dice **qué se teclea y qué se comprueba después**.

Lo que se levanta: **Caddy** (HTTPS y proxy) + **la aplicación** + **PostgreSQL**, todo
en una máquina pequeña. Los ficheros del agricultor y la base de datos viven en carpetas
del servidor, fuera de Docker, para que una copia de seguridad sea un `pg_dump` y un
`tar`.

> **Nada de esto se ha podido probar en un servidor**: se escribió en el ordenador de
> desarrollo, donde hay Docker 27.4 pero no hay servidor ni dominio. `docker compose
> config` sí se ha pasado (valida el fichero). Lo demás está dicho como se debe hacer y
> **hay que probarlo de verdad** antes de dar el despliegue por bueno.

---

## 0. Antes de empezar

- Un servidor con Linux (probado a escribir para Ubuntu 24.04), **2 vCPU, 4 GB de RAM y
  40 GB de disco** como mínimo, en la UE.
- Un dominio (o un subdominio) que puedas apuntar a la IP del servidor.
- Acceso por SSH con clave (contraseña, no).
- Docker y el complemento `compose` en el servidor.
- El repositorio en el servidor. **Sin GitHub Actions**: el proyecto tiene prohibido
  usarlas (cuota agotada; ver `PROTOCOLO-AUTONOMIA.md`), así que aquí no hay integración
  continua: se actualiza a mano con `git pull`.

## 1. Preparar la máquina

```bash
# Paquetes y usuario
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl git ufw

# Cortafuegos: solo SSH, HTTP y HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status

# Docker (el método oficial; el "docker.io" de Ubuntu suele ir atrasado)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"   # y vuelve a entrar por SSH
docker --version && docker compose version
```

**Comprobación:** `sudo ufw status` enseña 22, 80 y 443 permitidos; `docker compose
version` contesta (v2, no el `docker-compose` de antes).

## 2. Traer el repositorio y la configuración

```bash
sudo mkdir -p /srv/cuedigital
sudo chown "$USER":"$USER" /srv/cuedigital
cd /srv/cuedigital
git clone <la-dirección-del-repositorio> CueDigital
cd CueDigital

# La configuración de ESTE servidor
cp deploy/.env.example deploy/.env
chmod 600 deploy/.env
nano deploy/.env
```

En `deploy/.env` hay que cambiar, como mínimo:

| Variable | Qué poner |
|---|---|
| `DOMINIO` | el dominio de verdad (hoy es `cuaderno.ejemplo.invalid`) |
| `POSTGRES_PASSWORD` | una clave larga y aleatoria |
| `CUEDIGITAL_DATABASE_URL` | la misma clave, dentro de la dirección |
| `CUEDIGITAL_SECRETO` | `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CARPETA_DATOS` | `/srv/cuedigital/datos` |

> **El `.env` no se sube al repositorio ni se envía por correo.**
> Y ojo con el `.gitignore` de este proyecto: su regla `.env.*` también ignora
> `deploy/.env.example`. Para que el ejemplo viaje con el código hay que hacer
> `git add -f deploy/.env.example` (o añadir `!.env.example` al `.gitignore`, que es una
> decisión aparte y no se ha tocado).

**Comprobación:** `docker compose -f deploy/docker-compose.yml config --quiet` no dice
nada (si faltara una variable obligatoria, se queja aquí y no al arrancar).

## 3. Las carpetas de datos (permisos)

```bash
sudo mkdir -p /srv/cuedigital/datos/{adjuntos,sigpac_cache,postgresql,observabilidad}
sudo chown -R 10001:10001 /srv/cuedigital/datos
sudo chmod 700 /srv/cuedigital/datos
```

El usuario `10001` es el de dentro del contenedor (`deploy/Dockerfile`). Si esta carpeta
no es suya, la primera foto que suba un agricultor fallará con un error de permisos que
no dice nada útil.

**Comprobación:** `ls -ln /srv/cuedigital/datos` enseña `10001 10001` en las cuatro. La de
`observabilidad` es opcional: si `CUEDIGITAL_OBSERVABILIDAD` va vacía no se usa, y si no es
del usuario 10001, el programa sigue funcionando pero **no apunta nada en disco** (se lo traga
a propósito: la observabilidad no puede romper la aplicación).

## 4. El DNS antes que el certificado

En el panel del dominio, un registro **A**:

```
cuaderno.tu-dominio.es.   A   <la IP del servidor>
```

**Comprobación:** desde otra máquina, `dig +short cuaderno.tu-dominio.es` devuelve la
IP. **No sigas hasta que lo devuelva**: Caddy pide el certificado validando el dominio y,
si el DNS no está, falla y reintenta con espera creciente.

## 5. Arrancar

```bash
cd /srv/cuedigital/CueDigital
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs -f app
```

La primera vez se construye la imagen (varios minutos) y **la aplicación crea sola las
tablas al arrancar** (`crear_tablas()`, en `backend/app/main.py`). En el registro de
`app` se ven las líneas de puesta al día del esquema.

**Comprobación, una por una:**

```bash
# 1. Los tres contenedores en marcha y "healthy"
docker compose -f deploy/docker-compose.yml ps

# 2. La aplicación atiende (por dentro)
curl -fsS http://127.0.0.1:8000/health        # si se publica; si no, desde el contenedor:
docker compose -f deploy/docker-compose.yml exec app \
    python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health').read())"

# 3. HTTPS de verdad, desde fuera
curl -I https://cuaderno.tu-dominio.es
curl -fsS https://cuaderno.tu-dominio.es/health

# 4. HTTP redirige a HTTPS
curl -I http://cuaderno.tu-dominio.es
```

Lo que tiene que salir de `/health`:

```json
{"estado":"ok","zonas_vulnerables_cargadas":true}
```

> **`/health` no lo demuestra todo.** Solo dice que el programa atiende: **no consulta la
> base de datos**. Para comprobar la base, cuenta las tablas:

```bash
docker compose -f deploy/docker-compose.yml exec -T db \
    psql -U cuedigital -d cuedigital -tAc \
    "select count(*) from information_schema.tables where table_schema='public' and table_type='BASE TABLE';"
```

Tiene que contestar **67**: las **66** que declara `backend/app/models.py` con
`__tablename__`, más `grupo_parcela`, que es la tabla de unión de los grupos de parcelas y no
tiene modelo (se declara como `Table`). Comprobado en una base PostgreSQL 16 nueva el
09/11/2026. Si contesta 0, la aplicación arrancó pero no habló con PostgreSQL: mira
`logs app`.

## 6. El primer agricultor

Se da de alta como cualquier otro, desde la aplicación (`/`, botón de registrarse) o con
la API:

```bash
curl -fsS -X POST https://cuaderno.tu-dominio.es/api/cuenta/registro \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Prueba","correo":"prueba@example.com","clave":"una-clave-larga",
       "explotacion":{"nombre":"La prueba","nif":"00000000T"}}'
```

Devuelve un vale (`token`). **Comprobación:** entra en la pantalla con ese correo y esa
clave; y el vale sirve:

```bash
curl -fsS https://cuaderno.tu-dominio.es/api/cuenta/yo \
  -H "Authorization: Bearer <el token>"
```

> Para un agricultor de verdad, el NIF tiene que ser **el suyo**: es lo que después se
> compara con su certificado digital al entrar. No se cambia a mano: se da de alta bien.

## 7. Subir una foto y comprobar el tope de tamaño

Con la cuenta de prueba, sube un papel desde la pantalla (por ejemplo, un boletín de
análisis) y descárgalo.

**Comprobación en el disco:**

```bash
sudo ls -l /srv/cuedigital/datos/adjuntos/
```

Tiene que aparecer una carpeta con el número de la finca y, dentro, el fichero con un
nombre puesto por el programa (`...-<10 caracteres>.pdf`), **no** el nombre que mandó el
navegador.

**Comprobación del tope (dos puertas):**

- El programa corta en **12 MiB** y contesta `413` con una frase en castellano
  (`backend/app/adjuntos.py`, `MAXIMO_BYTES`).
- Caddy corta en **15 MB** antes de llegar (`deploy/Caddyfile`, `request_body`).

Se prueba con un fichero de 20 MB: tiene que llegar un `413`, no un corte raro.

## 8. Copia de seguridad y restauración

```bash
# Una copia a mano, y que se pueda leer
./deploy/copia.sh

# ENSAYO: restaurar en un destino NUEVO y abrirlo
./deploy/restaurar.sh /srv/cuedigital/copias/<la-marca>
```

El de restauración **no toca la base de producción**: crea una base nueva, restaura ahí,
descomprime los adjuntos en otra carpeta y te dice cómo levantar una segunda instancia en
`127.0.0.1:8001` para entrar y descargar un papel. Eso es lo que hay que hacer: **usar la
copia**, no solo mirar que el fichero existe.

Copia automática, una vez al día (de madrugada):

```bash
crontab -e
# añadir:
15 3 * * * /srv/cuedigital/CueDigital/deploy/copia.sh >> /var/log/cuedigital-copia.log 2>&1
```

Y **fuera de la máquina**, que es lo que de verdad protege. Con `rclone` y un
almacenamiento compatible con S3 (por ejemplo, el plan gratuito de Cloudflare R2, 10 GB):

```bash
# una vez
rclone config            # crea un remoto llamado, por ejemplo, "r2"
# en deploy/.env
COPIA_REMOTA=r2:cuedigital-copias
```

`copia.sh` avisa en voz alta si no hay copia remota: una copia en el mismo disco que los
datos no sirve para lo que más pasa.

## 9. Actualizar el programa

```bash
cd /srv/cuedigital/CueDigital
git pull
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml logs -f app
```

**Antes de actualizar, siempre:** `./deploy/copia.sh`.

> **Si la versión nueva cambia ficheros de la pantalla** (`backend/web/`), en el mismo
> cambio se sube el nombre de la caché del service worker
> (`backend/web/service-worker.js`, la línea `const CACHE = "cuedigital-…"`). Si no, un
> móvil que abra la aplicación en el campo **sin cobertura** se queda con los ficheros
> viejos. Es una regla del proyecto, no un detalle.

## 10. Mirar qué pasa

```bash
docker compose -f deploy/docker-compose.yml logs --tail=100 app
docker compose -f deploy/docker-compose.yml logs --tail=50 caddy
docker compose -f deploy/docker-compose.yml exec -T db pg_isready -U cuedigital
```

Y desde fuera, un vigilante gratuito que avise si el servidor se cae: UptimeRobot (plan
gratuito, 50 monitores cada 5 minutos) apuntando a `https://<dominio>/health`. Está en
`docs/DESPLIEGUE.md` con su límite y su precio.

La **observabilidad propia** (0 €) se lee con el token de `deploy/.env`:

```bash
curl -fsS -H "X-Observabilidad: <CUEDIGITAL_OBSERVABILIDAD_TOKEN>" \
    https://<dominio>/api/observabilidad/resumen
```

Y el recorrido de comprobación completo (salud, cuenta, tierras, foto del mapa y
observabilidad), que vale también contra la URL pública y devuelve 0 o 1:

```bash
cd backend && python3 scripts/comprobar_despliegue.py https://<dominio>
```

## 11. Parar, y lo que NO hay que hacer

```bash
docker compose -f deploy/docker-compose.yml stop       # se puede volver a arrancar
docker compose -f deploy/docker-compose.yml down       # los datos siguen en /srv/cuedigital/datos
docker compose -f deploy/docker-compose.yml down -v    # ¡OJO! borra los volúmenes de Caddy
```

**Lo que no se hace nunca:**

- Editar ficheros dentro del contenedor: se pierden en el siguiente arranque. Se cambia
  en el repositorio y se vuelve a construir.
- Restaurar una copia encima de la base de producción para "probar". Para eso está
  `restaurar.sh`, que restaura en otro sitio.
- Poner `CUEDIGITAL_ENTORNO=pruebas` en el servidor: permite bajar las iteraciones de la
  clave (ver `backend/app/security.py`).
- Copiar el `.env` a un chat, a un correo o al repositorio.

## 12. Si algo no arranca

| Lo que se ve | Dónde mirar |
|---|---|
| `app` reiniciándose en bucle | `logs app`. Si dice «no module named psycopg», falta `requirements-produccion.txt` en la imagen. Si dice que no puede preparar la base, el mensaje ya explica si es SQLite o PostgreSQL |
| Caddy no saca el certificado | el DNS (`dig +short`) y que los puertos 80/443 estén abiertos. Prueba con el entorno de pruebas de Let's Encrypt (está comentado en `deploy/Caddyfile`) |
| `502 Bad Gateway` | `app` no está sano: `docker compose ps` y `logs app` |
| No se puede subir un papel | permisos de `/srv/cuedigital/datos/adjuntos` (tiene que ser de `10001`) y el tope de 12 MiB |
| La pantalla sale en blanco | `logs caddy` y la consola del navegador. Si es tras una actualización, la caché del service worker (ver paso 9) |
