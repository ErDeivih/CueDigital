titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: **Las tres cosas, comprobadas en la demo pública** (https://erdeivih.github.io/cuedigital-demo/). **Pestañas con hash**: se pulsaron **ocho** y **cada una cambia el contenido y el `#`** de la URL — `#tierras`, `#calendario`, `#apuntar`, `#hoy`, `#trabajos`, `#productos`, `#facturas`, `#cuaderno` (con su pantalla: Mis tierras, Calendario, Apuntar un trabajo, Hoy, Trabajos, Productos y abonos, Facturas, Cuaderno). En la demo se **esconden** los enlaces a la app de siempre (PAC, Documentos, Ajustes, el chip de cuenta) y la tarjeta de descargar el PDF: una pestaña que no lleva a ninguna parte es peor que no tenerla. **Consola limpia**: se instaló antes de cargar un registrador de errores, promesas rechazadas y respuestas 4xx/5xx; tras abrir la pantalla y pulsar las ocho pestañas, **0 entradas** — hay **captura de la consola** (`consola-limpia-390.png`, el registro pintado por la propia página) y la evidencia en `docs/capturas-despliegue/consola-limpia-demo.json`. **Caso**: `docs/CASO-CUEDIGITAL.md` tiene sus siete secciones, con **SIGPAC** (§2), **modelo de datos** (§3) y **validación de geometrías** (§4: WKT sin romperse, sin forma no hay área —nunca cero—, el área cuadra con la del SIGPAC, solapes `si`/`puede`/`no`/`no_se`, el punto dentro del recinto y el límite de la caja del mapa).
estado: en-curso
tarea: pestañas con hash y contenido propio, consola limpia con captura, y caso con SIGPAC y validación de geometrías; todo comprobado en la demo pública
nivel: 2
siguiente: seguir con los textos de P5/P7/P8 del informe de interfaz y revisar el firewall del router; la cartera y el caso están listos para el panel
bloqueado: el aviso de seguridad está atendido (túnel fuera, cabeceras, alta cerrada, demo ficticia); siguen abiertos tres puntos que no son míos: la clave de la cuenta demo está en la documentación, el token de Cloudflare del 09/11 sigue guardado y conviene revocarlo, y el firewall del router lo tiene que mirar David; PSD2 parado por presupuesto; el alta del dominio en el IUWS y los formatos del expediente dependen de la Junta/FEGA
fecha: 2026-11-11

## Bloqueo

**(a) Dónde me quedé.** La tanda está cerrada: URL del funnel verificada en **móvil (390) y
escritorio (1024)** —parcelas con contorno y alta por los seis números, con capturas `final-alta-1024`
y `final-alta-ficha-1024`—, layouts medidos y `PORTFOLIO.md` con la prueba visual. Lo que queda **no es
de esta tanda**.

**(b) Qué falta revisar.** Los textos de **P5** (barra de acciones fija al apuntar), **P7** (la
cabecera del grupo sigue diciendo «N tierras · no consta» sin decir de qué) y **P8** (ayuda de
«Agregado» y «Zona» y la fecha del mapa); y **confirmar que el chat del panel** ha metido la URL en la
tarjeta («Abre desde cualquier sitio»).

**(c) Qué necesito de David o de otro chat.**
- **De David**: decidir si el **443** pasa a CueDigital (hoy lo tiene `lyfta`, en el 8010). No es
  bloqueante —el 8443 funciona y está comprobado—, pero la dirección corta no se puede tener sin
  decidir de quién es el puerto. Los dos comandos están en `docs/DESPLIEGUE.md` §10.1 bis.
- **Del chat del panel** (sesión del portfolio): que procese el mensaje con la URL buena
  (`https://servidor.tail4263a0.ts.net:8443`) y confirme la tarjeta.

**(d) Siguiente paso concreto.** Implementar **P7** (texto de la cabecera del grupo en `textos.py`,
con su prueba) y **P8** (ayuda de «Agregado» y «Zona»), volver a medir con `deploy/medir_publica.py`
y actualizar `docs/revision-interfaz.md` §6.4.

## Lo que se ha hecho en esta ronda (10/11/2026, sexta: cierre del túnel y endurecimiento)

1. **Fuera el túnel público.** El contenedor `cuedigital-tunnel` se ha eliminado (no solo parado) y
   el dominio `trycloudflare.com` contesta 530. Se ha quitado el *funnel* del puerto 8443 y se ha
   dejado **`serve`**: la app se abre **solo desde la red de Tailscale**, en
   `https://servidor.tail4263a0.ts.net:8443`.
   Comprobado: por la red de Tailscale, 200; **por el ingress público de Tailscale (la IP pública),
   000** (no conecta).
2. **Cabeceras de seguridad** en todas las respuestas (`app/seguridad.py` + middleware en
   `main.py`): `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`,
   `CSP` con `frame-ancestors 'none'` y **HSTS solo por HTTPS**. Comprobadas en el servidor.
3. **Alta de cuentas cerrada**: `registro_abierto()` la cierra en producción y la deja abierta en
   pruebas/local; `POST /api/cuenta/registro` contesta **403** con el mensaje de qué hacer. La
   variable `CUEDIGITAL_REGISTRO=abierto` la enciende si hace falta.
4. **Demo pública con datos ficticios**: se ha rehecho `deploy/paginas_github/demo/datos.json` sin
   nada del cliente (cinco tierras inventadas en «Villa de Ejemplo», referencias 47-99…, formas
   rectangulares nuevas) y se ha vuelto a publicar. Comprobado contra la URL de Pages: el alta por
   referencia y el contorno siguen funcionando con los datos inventados.
5. **`docs/SEGURIDAD.md`**: qué había, qué hay, qué se expone y a quién, cómo se comprueba y lo que
   queda por revisar (clave de la cuenta demo, token de Cloudflare, firewall del router, CSP con
   `unsafe-inline`).
6. **Aviso al chat del panel**: que **no enlace** la URL de la app (privada) y que use la demo
   estática, y que no publique capturas con datos de la finca.
## Lo que se ha hecho en esta ronda (10/11/2026, quinta: contenido real y cuaderno guiado)

1. **Contenido real en la finca de ejemplo**: las cinco parcelas del cliente **ya tienen sus datos
   del SIGPAC** (superficie y uso, sacados del recinto de su referencia) y sus apuntes de cuaderno
   (8 en total: tratamientos con plazo de seguridad y reentrada, abonos y labores). Sin datos
   personales: la finca no lleva nombre, NIF ni teléfono de nadie. Deja **3 tierras con
   tratamientos** (El Alto, El Prado y La Vega) y **2 sin ellos** (El Visor y Las Eras): así se ve
   la diferencia entre una tierra con plazos que mirar y una que aún no tiene nada apuntado.
2. **Cuaderno guiado** (`backend/app/guia.py`, función pura, 22 pruebas): la ficha de cada tierra
   dice **qué toca hacer y a partir de cuándo** — «ya se puede volver a entrar», «podrás cosechar a
   partir del 22/11/2026», «quedan 3 días: no coseches antes del…» con la etiqueta «Corre prisa» —
   y «di qué hay sembrado» cuando falta el cultivo, **sin fecha inventada**. Un plazo **vencido**
   no se marca como prisa: se dice y ya está. El texto vive en la pantalla (`textos.guia`); el
   servidor manda códigos y fechas.
3. **Desplegado y comprobado**: imagen nueva en el servidor (contenedor recreado, `/health` 200) y
   el bloque visto con Chrome de verdad a 390 y 1024 (`guia-ficha-390/1024.png`); las filas del
   aviso miden entre 78 y 138 px de alto.
4. **`PORTFOLIO.md`**: nueva fila «Cuaderno guiado, con fecha» y la prueba visual del aviso.
## Lo que se ha hecho en esta ronda (10/11/2026, cuarta: cierre para portfolio)

1. **URL publicada y comprobada**: el 443 del equipo estaba ocupado por `lyfta` (servido en el
   8010) cuando se fue a publicar, así que CueDigital sale por **https://servidor.tail4263a0.ts.net:8443**
   (Tailscale Funnel). La petición al **ingress público** de Tailscale (176.58.90.46, no la red
   interna) devuelve 200; no se ha pisado el servicio del otro proyecto y queda documentado cómo
   devolver el 443 si algún día se decide (`docs/DESPLIEGUE.md` §10.1 bis).
2. **Comprobado en móvil y escritorio**: parcelas con contorno y alta con los seis números, con
   capturas `final-tierras-360/1024`, `final-ficha-360/1024`, `final-modal-sigpac-360/1024` y
   `estable-ficha-nueva-390`. La finca vuelve a sus cinco parcelas (las de prueba se borran por la
   API al terminar).
3. **Medido lo que pide el encargo** (`deploy/medir_publica.py`): todas las pantallas del menú a
   360 y 1024, más la ficha y la ventana del SIGPAC. Resultado: **0 desbordes, 0 controles por
   debajo de 44 px, 0 tablas rotas**; el modal **cabe entero** (360×844 en el móvil, 1009×768 en el
   escritorio) con «Cerrar» de 48×48. La única «falta» que salió eran ayudantes ocultos para el
   lector de pantalla (1 px) y la casilla de un interruptor cuyo blanco de toque es su etiqueta: se
   afina la medida, no la aplicación.
4. **`PORTFOLIO.md`** con la URL, qué demuestra (SIGPAC, **geodatos**, **app de campo**), los
   números y la **prueba visual** (seis capturas). Aviso enviado al chat del panel con la URL
   buena (la primera que mandé no llevaba el puerto).

## Lo que se ha hecho en esta ronda (10/11/2026, tercera: URL estable publicada)

1. **Funnel de Tailscale en marcha**: `https://servidor.tail4263a0.ts.net` → `127.0.0.1:8090`.
   La primera llamada sin `sudo` da `Access denied: serve config denied`: el mando del cliente lo
   tiene root, así que se publica con `sudo tailscale funnel --bg 8090` (o se da el mando una vez
   con `sudo tailscale set --operator=david`).
2. **Comprobado desde fuera, no desde casa**: el DNS público del nombre resuelve a las direcciones
   de entrada de Tailscale (176.58.90.46/.63/.145) y una petición externa a `/health` devuelve el
   estado del servidor. Con Chrome de verdad: las cinco parcelas del cliente con su contorno
   (`deploy/comprobar_publica.py`), el alta por los seis números (`deploy/comprobar_alta_publica.py`)
   y el layout a 360/390/768/1024 sin desbordes ni controles pequeños. Capturas `estable-*.png`.
3. **El alta que funciona es la de las seis casillas** (provincia, municipio, agregado, zona,
   polígono y parcela); pegar la referencia sirve para el trozo (siete números). Se apunta en el
   guion y en la documentación, porque el mensaje del servidor ya lo dice al pegar una parcela.
4. **La finca queda como estaba**: las parcelas de la prueba se borran por la API al terminar
   (`DELETE /api/parcelas/{id}`) y se comprueba que vuelven a ser cinco.
5. **`PORTFOLIO.md`** en la raíz, con la URL como «Abre desde cualquier sitio», la evidencia medida
   y lo que falta dicho sin adornos. Y **aviso al chat del panel** (sesión del portfolio) para que
   actualice la tarjeta de `cue-digital`, que decía que no había demo pública.
6. **`docs/DESPLIEGUE.md` §10.1 bis**: estado del funnel, qué pasa si se cae (`tailscale funnel
   status` → `sudo tailscale funnel --bg 8090`), por qué no caduca y qué haría cambiar la dirección.

## Lo que se ha hecho en esta ronda (10/11/2026, segunda: URL estable y comprobaciones de la demo)

1. **Demo pública, comprobada otra vez y con el alta completa** (https://erdeivih.github.io/cuedigital-demo/):
   - **Alta por referencia de seis números**: `37-2-0-0-502-1` → «Añadir tierras» → «O pega las
     referencias» → «Traer las pegadas». La tierra nueva entra en la lista (**6 tierras**) y queda
     guardada en el navegador.
   - **Y se ve su contorno**: la ficha de la tierra nueva dibuja el anillo (SVG con su trazo),
     comprobado en el DOM y en la captura `docs/capturas-despliegue/demo-alta-contorno-390.png`.
   - Se arregló de paso un detalle feo: la ortofoto de la demo (`/api/mapa/imagen`) devolvía 404 y
     el navegador pintaba el **icono de imagen rota encima del contorno**. Ahora responde una
     imagen válida y el mapa queda limpio.
2. **Layouts de móvil y tableta medidos en la demo publicada** (`deploy/medir_demo.py`): a **360,
   390, 768 y 1024 px**, **0 desbordes horizontales, 0 controles por debajo de 44 px y 0 huecos
   por debajo de 8 px** (los «antes» están en `docs/revision-interfaz.md` §6.2: 30 controles y 135
   huecos). Capturas `demo-medida-*.png` y `medidas-demo.json`.
3. **URL estable preparada** (`docs/DESPLIEGUE.md` §10): Tailscale Funnel es la vía recomendada
   (gratis, sin cuentas nuevas; el servidor ya está en la red de Tailscale). **Solo falta un clic de
   David** en <https://login.tailscale.com/f/funnel?node=nN87axQZiT11CNTRL>; después,
   `deploy/url_estable.sh 8090` deja la app completa en **https://servidor.tail4263a0.ts.net/**.
   El guion no se queda colgado (eso pasó con la llamada directa): saca el enlace y el sufijo de la
   red. Alternativas documentadas: dominio propio con Caddy (≈10 €/año) y túnel con nombre de
   Cloudflare (`deploy/cloudflared/config.yml`, bloqueado por permisos del token del 09/11).

## Lo que se ha hecho en esta ronda (10/11/2026: la demo que no depende de nadie)

1. **Demo pública en GitHub Pages**: **https://erdeivih.github.io/cuedigital-demo/**. Es la misma
   pantalla de `/nuevo/` con **los datos dentro** (copia literal de lo que contestó el servidor el
   10/11/2026): las cinco parcelas del cliente de Salamanca con sus anillos, su ficha, el resumen,
   lo que falta del cuaderno, el calendario y los trabajos. **No pide nada a ningún servidor.**
   - **Aviso de demo siempre visible** arriba: «DEMO · Datos de ejemplo (cinco parcelas de
     Salamanca). Lo que apuntes se queda en este navegador, no en un servidor.»
   - **Alta por referencia de seis números funciona en la demo** (`37-2-0-0-502-1`): «Añadir
     tierras» → «O pega las referencias» → «Traer las pegadas»; la tierra aparece en la lista y se
     guarda en el `localStorage` del visitante.
   - **Verificado contra la URL real**: `GET /` → **200**, y con Chrome de verdad la app pinta, se
     ven las cinco parcelas, el aviso está y el alta se completa. Capturas a **360 y 1024** en
     `docs/capturas-despliegue/` (`demo-tierras-360/1024`, `demo-alta-referencia-390`,
     `demo-tierras-con-alta-390`). Se repite con `python deploy/comprobar_demo.py <url>`.
   - **Por qué un repositorio aparte**: Pages no se puede activar en el repositorio principal
     (privado + plan gratuito, `422`). La demo vive en el repositorio **público** `cuedigital-demo`,
     que **solo** lleva el front y los datos de ejemplo: ni backend, ni cuaderno, ni datos de
     ningún agricultor real.
2. **La demo también se prueba en el ordenador**: `deploy/paginas_github/servir_demo.py` sirve el
   paquete con los tipos de fichero declarados a mano. **`python -m http.server` no vale**: en
   Windows sirve los `.js` como `text/plain` y el navegador rechaza el módulo (la pantalla se queda
   en blanco sin decir por qué). Es la trampa de `AGENTS.md`, encontrada otra vez aquí.
3. **Cómo se rehace**: `sacar_datos_demo.py` (con el servidor encendido) → `preparar.py --demo` →
   publicar `build/pages-demo` en la rama `gh-pages` del repositorio de la demo. Todo en
   `docs/DESPLIEGUE.md` §9.5.

## Lo que se ha hecho en esta ronda (09/11/2026, cuarta: URL pública de verdad)

1. **Backend completo en el servidor propio** (`192.168.1.139`, Docker): contenedores
   `cuedigital-db` (PostgreSQL 16) y `cuedigital-app` (la imagen `cuedigital:servidor`, construida
   aquí y cargada con `docker load`, puerto `127.0.0.1:8090`), datos en
   `/srv/cuedigital/datos`. Arranca en PostgreSQL con las 67 tablas y `/health` contesta 200.
   La base y los secretos viven en `/srv/cuedigital/env` (600, fuera del repositorio).
2. **URL pública por túnel de Cloudflare** (`cloudflared` en un contenedor con `--restart`):
   **https://attract-leeds-integer-asp.trycloudflare.com**. Es un *quick tunnel*: HTTPS de verdad,
   sin cuenta, pero **la dirección cambia** si se recrea. Estable requiere dominio o túnel con nombre.
3. **Finca de ejemplo con las cinco parcelas del cliente**, dadas de alta **solo con su referencia**
   (cuatro con recinto y «El Visor» con seis números) y con la forma traída del **GeoPackage real de
   Salamanca** que se copió a la caché del servidor: **5 de 5 con contorno**, PNG 800×600. Cuenta:
   `demo@cuedigital.local` / `cuaderno-demo-2026`.
4. **Comprobado en la URL pública** (`deploy/comprobar_publica.py`, Chrome de verdad): entra la
   cuenta, la pantalla carga, se ven las cinco parcelas y **el mapa con su contorno**
   (`naturalWidth > 0`), y la ficha enseña la ortofoto con el contorno. Capturas a **360 y 1024** en
   `docs/capturas-despliegue/` (`tierras-360/1024`, `ficha-360/1024`).
5. **El front para publicarlo aparte**: `deploy/paginas_github/preparar.py` genera el paquete
   estático (rutas relativas, `config.js` con `window.CUEDIGITAL_API`, `.nojekyll` y entrada
   automática en la cuenta de ejemplo) y `urlDeLaApi()` (`web/nuevo/modelo.js`) es lo que hace que
   las llamadas lleven el dominio del servidor solo cuando se publica aparte. En el backend, los
   orígenes de fuera se autorizan con **`CUEDIGITAL_CORS_ORIGENES`** (con su prueba), y `*` se
   ignora a propósito. La rama **`gh-pages` está subida**, pero **Pages no se puede activar**:
   `422 · Your current plan does not support GitHub Pages for this repository` (repo privado,
   cuenta gratuita). Se activa en dos clics si el repo se hace público o la cuenta pasa a Pro.
6. **`docs/DESPLIEGUE.md` §9**: la URL, la cuenta, cómo se levanta y se apaga, cómo se conecta la
   pantalla con el backend (variables, CORS), el bloqueo de Pages y la comprobación que se repite.

## Lo que se ha hecho en esta ronda (09/11/2026, tercera: móvil, tableta y despliegue)

1. **Layouts revisados y arreglados a 360, 390, 768 y 1024 px** (14 pantallas × 4 anchos, 112
   capturas en `docs/capturas-revision/despues-*` y `antes-*`, más `mediciones-antes.json` y
   `mediciones-despues.json`). Antes → después, medido en el DOM:
   - **controles por debajo de 44 px: 30 → 0** en 360 y 390 (eran las celdas del calendario,
     38,6 px de ancho) y **huecos por debajo de 8 px: 135 → 0** en 768 y 1024 (eran los
     renglones del menú lateral y el calendario);
   - **mapas sin zona de toque: 1 → 0** (el mapa de «Mis tierras» tenía anillos de 2 px de trazo
     y no había detrás los 60 px del SIGPAC: ahora cada recinto es tocable);
   - **letra mínima: 10 → 15,2 px** (el suelo del contrato, la pista de 0,95 rem; los datos
     heredan el cuerpo) y **la opción elegida pasa de 2,48:1 a fondo de marca con texto blanco**,
     como el `boton-elegido` del contrato;
   - **0 desbordes horizontales** antes y después en los cuatro anchos, **0 acciones principales
     por debajo de 48 px** y **0 ventanas que no caben** (las dos del SIGPAC ya cabían).
   - Además: buscador de tierras en «Apuntar» (se acaba la caja de 64 tierras con scroll propio),
     tabla de «otros años» que se desplaza dentro de su caja, calendario a sangre en el móvil
     (44,3 px por celda a 360), y **teclado numérico** (`type="tel"` + `inputmode="numeric"`/
     `"decimal"` + `enterkeyhint`) en hectáreas, dosis, cantidades, superficie y referencia.
   - **Guardianes nuevos**: `backend/tests/test_revision_movil.py` (29 pruebas: leen el CSS, el
     JS y `mediciones-despues.json` y exigen 0 desbordes y 0 controles < 44 px) y el guion
     `backend/scripts/capturar_la_revision_movil.py`. **No se ha tocado `DESIGN.md`**: todo lo
     usado ya estaba en el contrato.
2. **Despliegue: todo listo, publicación bloqueada por cuentas** (probado con las credenciales
   del 09/11, sin copiar ningún secreto a ningún sitio):
   - **Cloudflare no sirve**: el token está activo, pero `GET /accounts` da **403** y
     `GET /memberships` da **401** (no deja leer la cuenta: falta el Account ID). Y aunque se
     añadiera, **Pages/Functions corren JavaScript/TypeScript**, no un backend Python con
     PostgreSQL.
   - **Supabase** (el token funciona) da base y fotos, pero **no ejecuta Python**; el proyecto
     que hay es de otro trabajo y no se ha tocado.
   - **Lo que queda es una cuenta**: Render (2 minutos con GitHub) aplicando
     `deploy/render.yaml`, que ya está escrito y validado (Docker + PostgreSQL gratis, variables
     generadas, `/health`), o la VM gratuita del apartado 3 de `docs/CUENTAS-Y-ACCESOS.md`.
   - **Arreglo de código que hacía falta para cualquier proveedor**: `app/database.py` pone el
     driver a las direcciones `postgres://`/`postgresql://` que dan Render, Neon y Supabase
     (SQLAlchemy 2 no las acepta tal cual). Probado con la **imagen real** levantada contra
     PostgreSQL 16 usando `postgres://` sin driver: arranca y `comprobar_despliegue.py` pasa
     entero (contornos incluidos). 9 pruebas nuevas en `tests/test_url_de_la_base.py`.

## Lo que se ha hecho en esta ronda (09/11/2026, segunda: despliegue real)

1. **Estado del repo, comprobado**: árbol limpio en `4ca5107`, **85 ficheros** en el último commit y
   **0/0** con `origin`. **No había 18 ficheros sin comitear**: se revisó y no había ninguno pendiente.
2. **La imagen se construye y el stack arranca contra PostgreSQL 16 de verdad**
   (`cuedigital:prueba`, 669 MB). El recorrido de `backend/scripts/comprobar_despliegue.py` contra
   `127.0.0.1:8090` sale **todo en verde**: `/health`, estáticos con su tipo MIME, alta de cuenta,
   **tierra por referencia de seis números** (`37-70-0-0-503-51` → códigos 37070/503/51 y recinto en
   «no lo sé»), **tierra con recinto**, **contornos desde el GeoPackage real** (2 con forma, PNG de
   800×600) y la observabilidad. La base se crea con **67 tablas** (66 del modelo + `grupo_parcela`).
   - **Bloqueo de producción nº 1 (cerrado)**: `acciones_a_fincas.puede_modificar` y
     `puede_ver_lo_economico` tenían `server_default=text("1")`. En PostgreSQL un `boolean` no admite
     `DEFAULT 1`: **la base nueva no se creaba y la app moría al arrancar**. Ahora `text("true")`.
   - **Bloqueo nº 2 (cerrado)**: `database._valor_por_defecto` devolvía `1`/`0` para booleanos al
     añadir una columna a una tabla existente; en PostgreSQL el `ALTER` fallaba **en silencio** (la
     columna quedaba en «imposibles» y habría reventado después). Ahora `TRUE`/`FALSE`.
   - **Prueba que impide que vuelva**: `backend/tests/test_booleans_en_postgresql.py` (6 pruebas) compila
     el DDL con el dialecto de PostgreSQL **sin servidor** y recorre todas las tablas del modelo.
3. **No hay URL pública, y es un bloqueo de cuenta, no de código**: `docs/CUENTAS-Y-ACCESOS.md` deja
   el paso exacto. Recomendación: **VM gratuita (Oracle Cloud Always Free)** con el `deploy/docker-compose.yml`
   tal cual — disco que no se borra, PostgreSQL al lado y HTTPS con dominio. Alternativa sin tarjeta:
   Render + Neon, pero **con disco efímero se pierden las fotos** (exigiría S3 antes de abrirla a nadie).
   Hace falta: cuenta de proveedor, un dominio con DNS y (recomendado) Cloudflare R2 para la copia fuera.
4. **Observabilidad verificada en vivo** (no solo escrita): 7 avisos de pantalla contados por vista y día,
   rutas medidas por **plantilla** (`/api/parcelas/{id}`, sin ids), códigos por ruta, **embudo de 5 etapas
   medido contra PostgreSQL** (cuentas 1 · fincas 1 · con tierra 1 · con apunte 0 · con cuaderno 0) y la
   puerta del resumen con su token: **200 con cabecera buena, 403 sin cabecera, 403 con cabecera mala,
   404 sin token configurado**. En el compose se añaden `CUEDIGITAL_OBSERVABILIDAD` y su token.
5. **Revisión de interfaz** (`docs/revision-interfaz.md`, 33 capturas en `docs/capturas-revision/`):
   inventario de **14 entradas** (13 pantallas + estado vacío) a 390 y 1024, y **10 problemas concretos
   con medición**: contraste **2,48:1** del elemento seleccionado en modo oscuro (mínimo 4,5:1), 35–68 %
   del texto por debajo de 16 px cuando `DESIGN.md` fija 18 px y solo permite bajar en la «pista»,
   apuntar empieza por una caja con **64 tierras y 9.426 px de scroll propio** (pestañas y «Guardar» fuera
   de pantalla), textos de programador en pantalla, 66 × «sin mapa» con un recuadro que el contrato
   prohíbe, «Arreglar» que no lleva a donde se arregla, y el resumen de trabajos sumando dosis/ha como
   si fuera un total. A favor, medido: 0 desborde horizontal y 0 controles por debajo de 44 px.

## Lo que se ha hecho en esta ronda (09/11/2026, primera: despliegue preparado)

1. **El despliegue está preparado, no hecho** (`docs/DESPLIEGUE.md`, 879 líneas, + `deploy/`):
   diagnóstico punto por punto con fichero y línea (SQLite por defecto, el driver de PostgreSQL
   **no** estaba en `requirements.txt`, adjuntos en disco, tokens de 30 días sin revocación, CORS a
   localhost, `/health` superficial, caché del SIGPAC de gigas, OCR aparte, IUWS con certificado,
   copias solo para SQLite); opciones y **precios con URL y fecha** (Hetzner CX23 5,99 €/mes y CAX11
   6,49 €, comprobados hoy en su página; R2 gratis hasta 10 GB; Let's Encrypt y UptimeRobot, 0 €);
   arquitectura recomendada (una máquina: Caddy + uvicorn + PostgreSQL + carpeta de adjuntos, copia
   diaria fuera) con el **por qué** frente a PaaS y PostgreSQL gestionado; **plan de 14 pasos** con la
   comprobación después de cada uno; RGPD (NIF, hosting en la UE, encargado del tratamiento, plazos) y
   **20 decisiones** para David con su coste y lo que pasa si no se decide. Artefactos:
   `deploy/Dockerfile` (Python 3.12, sin root, con Tesseract y HEALTHCHECK), `docker-compose.yml`
   (Caddy + app + PostgreSQL, **sin publicar** los puertos de app y base, datos en carpetas del
   servidor), `Caddyfile` (HTTPS solo, tope de subida 15 MB), `.env.example`, `copia.sh`, `restaurar.sh`
   y `LEEME.md`. `backend/requirements-produccion.txt` añade `psycopg[binary]==3.3.8`, que era el
   hueco que impedía arrancar en PostgreSQL.
   - **Comprobado**: `docker compose config` válido; `bash -n` de los dos guiones; precios cotejados
     contra las páginas oficiales (Hetzner y R2, 09/11/2026). **No comprobado y se dice**: no se ha
     construido la imagen ni levantado el servidor, no hay PostgreSQL en la máquina, y el precio del
     dominio queda «no verificado».
   - **Tres cifras**: ≈ **7,25 €/mes con IVA**; **150–200 agricultores** de alta (el límite es el disco
     de las fotos) y **10 a la vez**; **10–12 horas** de puesta en marcha y ensayo (estimación).
2. **Observabilidad dentro del programa** (`backend/app/observabilidad.py` +
   `routers/observabilidad_api.py` + `docs/OBSERVABILIDAD.md`): **errores** (5xx o excepción, con
   tipo, plantilla de ruta, código y mensaje corto **saneado**: correos, NIF y teléfonos tapados),
   **uso por pantalla y día** (lista blanca de las 11 vistas sacada de `app.js`, lo desconocido a
   `otra`, retención 14 días) y **duración por plantilla de ruta** (p50/p95 acotados). **El embudo se
   calcula con SQL sobre lo que ya existe** (cuentas → fincas → con tierra → con apunte → con cuaderno
   firmado o exportado), sin instrumentar nada de más; una etapa que falla queda en `null`, nunca en 0.
   - **Por defecto no escribe ni un byte en disco** (probado con espía): el JSONL giratorio de 2 MB +
     2 copias solo se escribe si se pone `CUEDIGITAL_OBSERVABILIDAD`. El resumen exige
     `X-Observabilidad` comparada en tiempo constante con `CUEDIGITAL_OBSERVABILIDAD_TOKEN`: **404 sin
     token configurado** (la puerta no existe) y **403 con cabecera mala**. El aviso de pantalla es
     `sendBeacon` y **contesta siempre 204**, incluso con basura (probado con 10 cuerpos, uno de 100 KB).
     El middleware **no cambia ninguna respuesta** y si falla, la petición sigue. **No se mide** cuerpo,
     token, IP, cuenta ni dato del cuaderno.
   - **46 pruebas nuevas** y el guardián de rutas públicas puesto al día (24 → 26, con el motivo de
     cada una escrito).
3. **La carga está medida, no estimada** (`backend/scripts/prueba_de_carga.py` +
   `docs/PRUEBAS_DE_CARGA.md` + `backend/tests/test_prueba_de_carga.py`, 35 pruebas): levanta su propio
   uvicorn con base y adjuntos **temporales**, siembra agricultores por la API pública, repite el
   recorrido real (entrar con PBKDF2, tierras, ficha, apuntar tratamiento, cuaderno) y sube la
   concurrencia por escalones. **Medido en esta máquina (Ryzen 5 3600, con la CPU al 100 % por otros
   procesos, así que conservador)**: 1 y 5 usuarios sin errores (p95 130 y 171 ms), **10 usuarios con
   holgura (p95 286 ms, 0 errores)**, **la rodilla a 25** (p95 630–895 ms), 50 lento y sin errores
   (p95 1.784 ms) y **100 atascados** (las entradas agotan los 20 s; el servidor no se cae).
   **Con la clave de producción (240.000 iteraciones) entrar cuesta 2,9 veces más** (280 ms de CPU) y
   el p95 a 1 usuario pasa de 130 a 234 ms. Cuellos medidos: **SQLite con un solo escritor** y un único
   proceso (15 conexiones de base, 40 hilos), arranque 5,3 s y `crear_tablas` en cada arranque. El
   número defendible hoy es **10 concurrentes**; con PostgreSQL y 2–3 procesos se estima ×2–3, **sin
   medir**.
4. **El hueco del SIGPAC, cerrado** (hallado por la verificación y arreglado el mismo día): cuando una
   tierra no casaba con el GeoPackage, el servidor mandaba el **motivo** y la ventana **no lo pintaba**
   (solo contaba «1 tierra sin códigos»). Ahora `lineasDeLosContornos` **no pierde el motivo** (agrupado
   para no repetir frases), hay una fila por tierra con **su motivo tal cual** y un botón **«Elegir el
   recinto en el SIGPAC»** que **abre la misma ventana ya rellena con esa tierra** (no otra ventana y no
   la tierra anterior: hay guardián). Textos nuevos en `textos.py` (`CONTORNOS_DEL_SIGPAC`) y en
   `textos_visibles()`, con su copia servida y guardián de que las dos digan lo mismo.
   - **Verificado en Chrome** con el GeoPackage real: arnés del armazón **Fallos: 0**; la línea «11
     tierras sin códigos del SIGPAC · le falta el polígono, la parcela o el recinto» pintada; 11 botones
     en el DOM; el botón de la fila abre la ventana con `37-2-0-0-502-1` y trae sus 2 recintos.
   - **Y destapó un desborde de 10 px a 390** (el panel de resultado es `display:flex` en fila): se
     envolvió el contenido en un solo `<div>` en `app.js`, sin tocar CSS, y quedó en **0 px a 390, 360,
     1024 y 1440**, con los botones «Ver las tierras» y «Cerrar» enteros y alcanzables.
5. **Limpieza y verificación**: informe de los dos frentes en
   `docs/VERIFICACION_SIGPAC_Y_CUADERNO_2026-11-09.md` (266 pruebas de Python y 88 de JS ejecutadas,
   y la prueba **en vivo** con el `.gpkg` real: contornos en 498 ms, PNG de 800×600 con ortofoto y
   contorno, y el caso de 2 recintos que pide elegir); 10 capturas nuevas indexadas en
   `docs/capturas-nuevo/LEEME.md`; ningún servidor ni Chrome queda encendido.

## Lo que se ha hecho en esta ronda (08/11/2026)

1. **GeoPackage real con un cliente de verdad**: cuatro parcelas de Salamanca con referencias sacadas
   del fichero real (El Prado, El Alto, La Vega y **Las Eras**, esta última dada de alta **solo con la
   referencia**). `POST /api/sigpac/cache/37/contornos` → **4/4 actualizadas, 0 sin códigos**, geometría
   **idéntica** al WKT del lector, y **cuatro mapas** con ortofoto del IGN (0,6–1,3 s por mapa) en
   `docs/capturas-nuevo/cliente-contornos.png`; variante sin red con el contorno dibujado por el
   programa. El contorno de las cuatro se genera en **0,046 s**. **Y dentro de la app, en móvil**: el
   mapa real aplicado a una tierra se ve en su ficha con ortofoto y contorno
   **el GeoPackage real**: la ventana abierta desde la ficha de una tierra **ya viene rellena con su
   referencia, pueblo y códigos, busca sola una vez y deja elegido el recinto de la tierra**; desde
   el alta sigue vacía. La ficha del mapa real se ve en `cliente-real-ficha-390/360.png` y la ventana
   con el recinto en `cliente-real-sigpac-390.png`, con la imagen cargada comprobada. Y **las cinco parcelas del
   cliente** (cuatro con el recinto en la referencia y **una con la referencia del visor, seis
   números**), dadas de alta solo con su referencia, se ven una a una con su contorno y su ortofoto
   (`cliente-real-1..5-390.png`); el índice de capturas está en `docs/capturas-nuevo/LEEME.md`.
   Si la referencia no dice el recinto y la parcela tiene **uno solo**, se coge; si tiene **varios**,
   se dice y se pide elegir, sin adivinar (IMP-27, 3 pruebas nuevas).
2. **Fallo cerrado (hallado por esa prueba)**: una tierra creada con **solo `ref_sigpac`** guardaba los
   códigos en blanco y el GeoPackage no la reconocía. Ahora:
   - al guardar, `_completar_los_codigos_con_la_referencia` rellena `codigo_ine`, polígono, parcela y
     recinto **solo si faltan** y no bloquea si la referencia no se entiende;
   - al leer, `codigos_de_una_parcela` usa la referencia **también para las tierras ya guardadas**, sin
     migración.
   Antes: `sin_codigos`; ahora: `actualizadas` y WKT idéntico. **7 pruebas nuevas** del alta por
   referencia y 3 del geopackage.
3. **Cuaderno guiado con avisos claros**: el aviso distingue **lo que bloquea el envío** (lo resuelve
   la aplicación, la Junta o FEGA) de **lo que el agricultor puede rellenar**. Arriba dice «Lo primero
   que puedes rellenar: …» con la pantalla donde se arregla, avisa de que lo técnico «no depende de
   ti» y **no manda a la app vieja a arreglar lo que no puede**; las secciones con pantalla van antes
   y, dentro, lo bloqueante primero. Medido en Chrome: 16 secciones con pantalla antes de las
   técnicas, 0 desbordes y botón alcanzable. El resumen dice además **cuántas faltas son suyas**
   («Puedes rellenar N de ellas aquí»). En el SIGPAC, la lista de tierras pintadas dice cuáles
   son, no solo cuántas.
4. **Móvil auditado y con capturas limpias**: 10 vistas a 390×844 y 360×640, **0 px de desborde, 0
   botones <44 px y 0 centros tapados** (cada control se lleva al centro y se comprueba con
   `elementFromPoint`); **20 capturas** de todas las vistas y **3 más** del contorno real dentro de la
   app en `docs/capturas-nuevo/` (`movil-*.png` y `cliente-real-*.png`), con Hoy, Tierras, ficha,
   apuntar, calendario, trabajos, productos, cuaderno, facturas y la ventana del SIGPAC. Al cambiar de
   pantalla el scroll vuelve arriba (antes una vista heredaba el scroll de la anterior y los primeros
   botones quedaban bajo la cabecera fija).
5. **PSD2 documentado para decidir, sin contratar nada** (`docs/PSD2-AGREGADORES.md`, revisión
   08/11/2026):
   - **Ningún agregador grande publica precio de producción** (Enable Banking, Powens, Tink,
     GoCardless, TrueLayer, Salt Edge: presupuesto).
   - **Lo único publicado**: sandbox de BBVA **0 €** y **openbanking.io 3 €/mes con 1 cuenta + 1 €/mes
     por cuenta** (2 cuentas = 48 €/año antes de IVA), pero **su licencia y cobertura española no están
     verificadas**: no se usa sin DPA y por escrito.
   - **Licencia propia (AISP) descartada**: **50.000 € de capital inicial** (art. 7 PSD2) más
     certificados eIDAS (2.000–10.000 €/año, estimación de tercero) y auditoría.
   - **Tres caminos**: seguir con el extracto por fichero (0 €), agregador AISP (presupuesto) o
     licencia propia (descartada). **Criterio de parada**: si el anual supera el coste de seguir a mano
     (0 €), no se contrata. **David decide**; no hay código de PSD2.
6. **Limpieza**: solo se levanta el uvicorn temporal de las verificaciones y se apaga; no queda ningún
   proceso de CueDigital escuchando.

## La última pasada, sobre este mismo HEAD (09/11/2026)

    Python       6108 recogidas · 0 fallos (RESULTADO=PASA, código de salida 0)
    JavaScript   1319 superadas, 0 fallos
    móvil y tableta, 14 pantallas × 4 anchos  0 desbordes · 0 controles < 44 px · 0 huecos < 8 px
    letra mínima                          10 px → 15,2 px (el suelo del contrato)
    opción elegida en oscuro              2,48:1 → fondo de marca con texto blanco
    mapa de «Mis tierras»                 1 sin zona de toque → 0
    imagen de producción + PostgreSQL 16 con dirección `postgres://` sin driver
                                                   comprobar_despliegue.py: todo lo comprobado bien
    base nueva en PostgreSQL                                     67 tablas, arranque sin error
    prueba de humo contra un uvicorn de verdad                    RESULTADO: todo correcto
    armazón nuevo en Chrome con el GeoPackage real de Salamanca            Fallos: 0
    carga (docs/PRUEBAS_DE_CARGA.md)                  10 concurrentes con holgura, rodilla a 25

**Y la puerta encontró un fallo que no era del código:** al añadir 104 pruebas de Python y 3 de JS,
el guardián `test_lista_de_la_junta` se puso rojo porque `README.md`, `AGENTS.md` y
`docs/LO_QUE_PIDE_LA_JUNTA.md` seguían diciendo 5938 y 1316. Se actualizaron los tres al número
medido (6042 y 1319) y la suite volvió a verde. Es exactamente para lo que existe ese test.

## Lo que sigue abierto

- **La URL pública (lo primero)**: crear la cuenta y el dominio con el paso exacto de
  `docs/CUENTAS-Y-ACCESOS.md`, desplegar y correr `backend/scripts/comprobar_despliegue.py <url>`.
  Hasta entonces, el despliegue está **probado en local**, no publicado.
- **Los 10 problemas de interfaz** de `docs/revision-interfaz.md`, por gravedad: primero el contraste
  del elemento seleccionado (2,48:1), el tamaño del texto (18 px de contrato frente a 13 px reales)
  y «apuntar» entre 64 tierras.
- **Límite de intentos y revocación de vales**: hoy un vale robado vale 30 días y no se puede echar
  a nadie sin cambiar la clave a todos (decisión 6 y 7 de `docs/DESPLIEGUE.md`; 1–2 días cada una).
- **Re-medir la carga con PostgreSQL y 2–3 procesos**: la prueba actual es con SQLite y un proceso
  (10 concurrentes; rodilla entre 10 y 25). PostgreSQL **no se ha medido** en esta máquina.
- **Política de limpieza de la caché** del GeoPackage (ZIP 600 MB + `.gpkg` 1.070 MB por provincia;
  no basta con borrar el ZIP porque `ficha_guardada` lo necesita).
- **Separar las dependencias** de producción de las de test (hoy la imagen instala `pytest` y `ruff`).
- **Migraciones de verdad** (Alembic o similar) antes del primer cambio de esquema en PostgreSQL.
- **RGPD antes del primer agricultor**: aviso de privacidad, registro de actividades, contrato de
  encargado y política de conservación de adjuntos (apartado 5 de `docs/DESPLIEGUE.md`).
- **Cola sin cobertura** del apunte y **cosecha comercializada** en la app nueva.
- **PAC de años anteriores** y recintos por campaña de la Junta; pantallas propias de PAC y gastos.
- **PSD2**: esperar los presupuestos y la decisión de David; sin código hasta contrato.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
