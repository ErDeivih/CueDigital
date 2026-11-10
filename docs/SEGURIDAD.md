# Seguridad: qué está expuesto y qué no (10/11/2026)

> **El aviso que originó este documento.** Los dos coordinadores avisaron de que CueDigital estaba
> publicada en un túnel de Cloudflare abierto a internet (`attract-leeds-integer-asp.trycloudflare.com`),
> **sin cabeceras de seguridad, con el alta de cuentas abierta y con las parcelas reales de un
> cliente**. Eso no puede estar así. Este documento dice lo que se ha cerrado, lo que queda expuesto
> y con qué se comprueba.

---

## 1. Qué había, y qué hay ahora

| Antes (10/11/2026, mañana) | Ahora |
|---|---|
| Túnel `trycloudflare.com` público, sin autenticación de red | **Túnel eliminado**. El contenedor `cuedigital-tunnel` ya no existe |
| Cualquiera con la dirección veía la app y sus datos | Solo entra quien esté **en la red de Tailscale de David** (`servidor.tail4263a0.ts.net:8443`) |
| Alta de cuentas **abierta** a todo el mundo | **Cerrada**: `POST /api/cuenta/registro` contesta **403** |
| Sin cabeceras de seguridad | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `CSP` con `frame-ancestors 'none'` y **HSTS cuando va por HTTPS** |
| Demo pública con **las parcelas del cliente** | Demo pública con **cinco tierras ficticias** («El Llano», «La Fuente», «Los Olmos», «La Dehesa», «El Barbecho», en «Villa de Ejemplo») |

## 2. Lo que se expone ahora (y a quién)

| Superficie | Quién entra | Qué lleva |
|---|---|---|
| **App completa** en `https://servidor.tail4263a0.ts.net:8443` | Solo dispositivos de la red de Tailscale de David | Datos reales de la finca de ejemplo (cliente) y lo que se apunte |
| **Demo estática** en `https://erdeivih.github.io/cuedigital-demo/` | Cualquiera (es el enlace del portfolio) | **Solo datos ficticios**: cinco parcelas inventadas, sin nombre, NIF ni teléfono de nadie |
| **Repositorio** de la demo (`ErDeivih/cuedigital-demo`) | Público | Solo el front estático y los datos ficticios |

**Lo que ya NO está expuesto en ningún sitio público:** las referencias SIGPAC del cliente, sus
superficies, sus formas y sus coordenadas. Se han quitado del paquete de la demo (se rehizo con
`deploy/paginas_github/hacer_demo_ficticia.py`) y el túnel que las servía está apagado.

## 3. Cómo se comprueba (y cómo se repite)

```bash
# 1) Por la red de Tailscale tiene que contestar:
curl -s -o /dev/null -w '%{http_code}\n' https://servidor.tail4263a0.ts.net:8443/health   # 200

# 2) Por el ingress PÚBLICO de Tailscale (la IP pública, no la red interna) NO:
curl -s -o /dev/null -m 10 -w '%{http_code}\n' \
  --resolve servidor.tail4263a0.ts.net:8443:176.58.90.46 \
  https://servidor.tail4263a0.ts.net:8443/health                                        # 000 (no conecta)

# 3) El alta de cuentas está cerrada:
curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' \
  -d '{"nombre":"X","correo":"x@x.test","clave":"clave-larga-123","explotacion":{"nombre":"F","nif":"00000000T"}}' \
  https://servidor.tail4263a0.ts.net:8443/api/cuenta/registro                            # 403

# 4) Las cabeceras van puestas:
curl -sI https://servidor.tail4263a0.ts.net:8443/health | grep -iE 'content-security|x-frame|strict-transport'
```

Y en las pruebas, sin red: `tests/test_seguridad_web.py` (12 pruebas de cabeceras y del alta).

## 4. Cómo se pone en marcha y cómo se retira

**El acceso por Tailscale** (solo red privada, TLS con certificado de Tailscale):

```bash
# En el servidor. Solo la red de Tailscale (serve, NO funnel):
sudo tailscale serve --bg --https=8443 8090
# Dejarlo sin publicar:
sudo tailscale serve --https=8443 off
```

> **Ojo con `funnel`:** `tailscale funnel` hace lo contrario — lo publica en internet. Se usó el
> 10/11 por la mañana para enseñar la app y **por eso quedó expuesta**. Para lo privado se usa
> `serve`, y el puerto 8443 ya no tiene funnel (`tailscale funnel status` no lo lista).

**El alta de cuentas** (cerrada por defecto en producción):

```bash
CUEDIGITAL_REGISTRO=cerrado   # forzada a cerrada
CUEDIGITAL_REGISTRO=abierto   # solo si hay que dar de alta a alguien
```

Sin la variable, en producción (`CUEDIGITAL_ENTORNO` vacío) está **cerrada**; en pruebas y local
está abierta, que es donde hacen falta cuentas. La lógica está en `backend/app/seguridad.py`.

## 5. Lo que queda por revisar (dicho sin adornos)

1. **La cuenta de ejemplo** (`demo@cuedigital.local` / `cuaderno-demo-2026`) sigue existiendo en la
   app privada, con la finca real del cliente. No es pública (solo se entra por Tailscale), pero
   **sus credenciales están escritas en la documentación**: si el repositorio se hace público, hay
   que cambiar la clave o borrar la cuenta.
2. **Los datos del cliente siguen en la base del servidor de casa** (es su función), y en las
   copias de seguridad de `/srv/cuedigital/datos`. Fuera de casa no han salido.
3. **El firewall del router** no se ha tocado: el servidor no publica puertos, pero conviene revisar
   que 8090 y 5433/5434 no estén abiertos hacia internet.
4. **El token de Cloudflare** del 09/11 sigue guardado en la documentación de cuentas; no tiene
   permisos de despliegue, pero conviene revocarlo.
5. **CSP con `'unsafe-inline'` para estilos**: React y el CSS del proyecto lo necesitan hoy. Si se
   puede quitar en el futuro, mejor.
