He diseñado la pantalla inicial de acceso e inicio de sesión **«Mi cuaderno - CUE Digital»** adaptada rigurosamente a las condiciones de uso de un agricultor de 50 a 70 años en Castilla y León (al sol, con una mano, de pie en la parcela y sin cobertura).

### Decisiones de diseño y cumplimiento de reglas:
1. **Dos caminos claros sin pestañas ni menús**:
   - Por defecto muestra el camino rápido **«Si ya te has apuntado alguna vez»** (con «Tu correo», «Tu clave», botón de 72 px **«ENTRAR A MI CUADERNO»** y la opción complementaria **«ENTRAR CON MI CERTIFICADO»** con su pista «Sin teclear nada: usa el certificado que ya tienes en este teléfono o en la tarjeta»).
   - Abajo del todo se sitúa el botón claro de 68 px **«Es mi primera vez: quiero apuntarme»**. Al pulsarlo, conmuta dinámicamente al camino **«Si es la primera vez que entras»** mostrando: *«¿Cómo te llamas?»*, *«Tu NIF»* (con recuadro de ayuda que explica dónde se mira en el DNI y por qué hace falta para el SIGPAC), *«¿En qué pueblo está tu finca?»*, *«¿En qué provincia?»* (un desplegable nativo táctil con las 9 provincias de Castilla y León: Ávila, Burgos, León, Palencia, Salamanca, Segovia, Soria, Valladolid y Zamora), *«Tu correo»*, *«Tu clave»* y el botón verde **«CREAR MI CUADERNO»**. Al estar en este modo, el botón inferior pasa a decir **«Ya tengo cuenta: entrar con mi clave»**.
2. **Explicación normativa en cabecera**: Se incluye el texto íntegro solicitado en el panel superior: *«Puedes llevarlo en papel hasta el 31 de diciembre de 2026. A partir del 1 de enero de 2027 tiene que ser electrónico. Si lo llevas aquí, no se te pierde, te calcula solo los días de espera y te avisa de lo que falta»*.
3. **Ergonomía de campo**:
   - Tipografía base de 18 px (`system-ui`) con conmutador funcional **«A+ Letra»** (21 px) en la cabecera fija.
   - Campos de 64 px de alto y botones de 64 a 72 px, con bordes gruesos de 3 px de alto contraste para máxima visibilidad bajo la luz solar directa.
   - Cero sombras difusas, transparencias o degradados.
   - Todos los iconos son SVG vectoriales limpios (tractor, libro, credencial, intercambio, carné), sin emojis.
   - Aviso de tranquilidad: *«Funciona en el campo sin cobertura. Lo que apuntes se guarda en este teléfono aunque no tengas internet»*.