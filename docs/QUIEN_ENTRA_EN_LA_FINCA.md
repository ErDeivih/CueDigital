# Varias cuentas en una misma finca (y en qué finca estás trabajando)

Este documento cuenta **cómo se le da acceso a otra persona a la misma finca**, en qué finca está
apuntando cada cuenta, y por qué se hizo así. Es lo que pidió David con estas palabras: «también quiero
que una explotación puedan acceder varias cuentas, no solo 1».

## 1. El caso de verdad, contado en una frase

David lleva el cuaderno de su finca. Su hijo le echa producto un día y quiere apuntarlo él mismo, desde
su móvil y con su cuenta. **Los dos apuntan en el mismo cuaderno**: no son dos cuadernos que luego haya
que juntar. Y el hijo, además, ayuda en la finca de su suegro, así que tiene que poder decir **en cuál
de las dos está apuntando** cuando abre la aplicación.

Eso son dos cosas distintas y las dos hacen falta:

| Lo que hace falta | Cómo se llama aquí |
|---|---|
| Que una finca tenga **varias cuentas** dentro | Quién entra en mi finca |
| Que una cuenta pueda estar en **varias fincas** | En qué finca estás trabajando |

## 2. Quién manda: el titular y los ayudantes

| Papel | Quién es | Qué puede hacer |
|---|---|---|
| **Titular** | Quien creó la finca. **Una finca tiene uno solo.** | Todo, y además **decidir quién entra**: añadir cuentas por su correo y quitarlas |
| **Ayudante** | A quien el titular le ha dado acceso | Trabajar igual que el titular (apuntar, mirar, sacar el cuaderno) y **quitarse a sí mismo** |

Tres decisiones que están en el código y no son casualidad:

1. **El titular no se puede quitar.** Una finca sin titular es una finca que nadie puede gestionar: no
   habría nadie que pudiera volver a dar acceso. El servidor contesta 409 y la pantalla **no pinta el
   botón**, porque un botón que lleva a un error es peor que no ponerlo.
2. **Nadie puede ponerle la clave a otro.** Se pide el **correo** de una cuenta **que ya existe**: la
   cuenta se crea antes, con su correo y su clave, y después el titular le da acceso a la finca. Si el
   correo no es de ninguna cuenta, se dice que esa persona se dé de alta primero.
3. **El correo es lo que identifica una cuenta**, y no se repite: por eso se pide el correo y no el
   nombre («María» hay muchas).

## 3. En qué finca estás: el vale dice la finca

Cada cuenta guarda **en qué finca está trabajando ahora mismo**, y eso es lo que decide qué datos ve.
Cambiar de finca es cambiar eso, y tiene dos consecuencias que hay que entender:

- **Se emite un vale nuevo.** El vale (el token) dice **en qué finca** se está. Si no se cambiara, un
  vale viejo seguiría mirando la finca en la que ya no se está: es lo que impide que alguien siga viendo
  datos de una finca de la que le han quitado el acceso.
- **Se vuelve a pedir todo.** Lo que hay en pantalla (las tierras, los apuntes, el cuaderno) es de la
  finca anterior, y enseñarlo después de cambiar sería enseñarle a un agricultor los datos de otra
  finca. Se olvida también el atajo «lo mismo que la última vez», que repetiría un apunte de la finca
  anterior con una tierra que aquí no existe.

## 4. Las cuatro puertas del servidor

| Camino | Qué hace | Quién puede |
|---|---|---|
| `GET /api/fincas` | Las fincas en las que puede entrar esta cuenta, con la que está usando marcada | Cualquiera con su cuenta |
| `GET /api/fincas/quien-entra` | Quién entra en la finca **en la que se está trabajando** | Cualquiera que entre en esa finca |
| `POST /api/fincas/quien-entra` | Da acceso a una cuenta, por su correo | **Solo el titular** |
| `DELETE /api/fincas/quien-entra/{id}` | Le quita el acceso | El titular a cualquiera; cada uno a sí mismo |
| `POST /api/fincas/cambiar` | Se pone a trabajar en otra finca de las suyas, y devuelve **un vale nuevo** | Cualquiera, en una finca en la que pueda entrar |

Los motivos por los que el servidor dice que no son **frases que lee el agricultor** y viven en
`textos.FINCAS` (`textos.py`): «Solo el titular de la finca puede decidir quién más entra», «Esa finca no
es tuya o ya no tienes acceso a ella», «El titular de la finca no se puede quitar»…

> **Un arreglo que salió de aquí.** Hasta la ronda 89, cuando el servidor decía que no con una frase
> suelta (`{"detail": "…"}`) la interfaz **la tiraba** y enseñaba «No se ha podido mandar». Se arregló en
> `nucleo.js` (`avisoDelServidor`): ahora se aprovecha la frase del servidor venga como venga, porque la
> regla del proyecto es que la interfaz **no compone frases, pero tampoco puede tirar la que le dan**.
> Se descubrió al escribir esta pantalla, donde **todos** los motivos son frases sueltas.

## 5. La pantalla

«Quién entra en mi finca» está en React (`backend/web/react/pantallas/quien_entra.js`) y se abre desde
**«mis datos»**, que es la pantalla de la finca (el titular, su NIF y el nombre de la explotación): es
donde el agricultor busca quién más entra en ella.

Enseña tres cosas, en este orden:

1. **En qué finca estás** («Estás en …»), que es lo primero que hace falta saber cuando se puede estar
   en dos.
2. **Quién entra**, con el papel de cada uno escrito de cuatro maneras distintas según quién mire: «Tú
   (titular)», «El titular de la finca», «Tu cuenta» y «Ayuda en la finca». El mismo dato se lee de una
   forma cuando es tuyo y de otra cuando es de otro —decirle «Tú (titular)» al titular cuando quien mira
   es el ayudante es mentirle—. Si eres el titular, además sale el campo del correo y el botón de añadir;
   si no, sale la frase que dice a quién hay que pedírselo.
3. **En qué finca estás trabajando**, pero **solo si hay más de una**: con una sola finca, un bloque que
   enseña una lista de uno es ruido. La finca en la que ya estás no lleva botón (no cambiaría nada) y la
   otra sí, con «PONME EN ESTA FINCA».

Quitar el acceso **se pregunta antes** (`window.confirm`, el mismo que usa el botón de salir): es lo
único de esta pantalla que no se deshace con otro toque, porque habría que volver a escribir el correo.

## 6. Cómo se comprueba

```powershell
cd backend
$env:CUEDIGITAL_ENTORNO="pruebas"; $env:CUEDIGITAL_ITERACIONES_PBKDF2="1000"
$env:PYTHONIOENCODING="utf-8"

# Lo del servidor: los papeles, los permisos y el aislamiento entre fincas (12 pruebas)
..\.venv\Scripts\python.exe -m pytest tests/test_varias_cuentas_en_una_finca.py -q

# Lo que se ve: el componente, sin navegador
node --test "tests_js/react.test.js"

# Y el recorrido desde app.js: que se pida la pantalla, que el correo llegue y que el vale cambie
node --test "tests_js/interfaz.test.js"
```

Lo que se comprueba, y por qué cada cosa:

| Comprobación | Dónde | Por qué importa |
|---|---|---|
| Dos cuentas en la misma finca ven **las mismas tierras** | `tests/test_varias_cuentas_en_una_finca.py` | Es lo que se pidió: un cuaderno, no dos |
| El ayudante trabaja pero **no decide** quién entra (403) | Lo mismo | El papel se respeta de verdad, no solo en la pantalla |
| Al quitarle el acceso, **su vale viejo deja de valer** (401) | Lo mismo | Si no, seguiría viendo la finca desde el móvil |
| El titular no se puede quitar (409) | Lo mismo | Una finca sin titular se queda sin quien la gestione |
| Un vale antiguo de una finca sin acceso **no entra** (401) | Lo mismo | Es la puerta que cierra el aislamiento |
| El correo escrito a mano **llega al servidor** | `tests_js/interfaz.test.js` | El campo lo dibuja React y lo lee `app.js` por su `id`: si el `id` cambia, se manda vacío y nadie se entera |
| Cambiar de finca **cambia el vale y vuelve a pedir todo** | Lo mismo | Enseñar los datos de la finca anterior es el peor fallo posible aquí |
| Los cuatro papeles se distinguen según quién mire | `tests_js/react.test.js` | El mismo dato dicho de dos formas distintas |
| Ninguna frase está escrita en el componente | Lo mismo | Las palabras viven en `textos.py`, y así pasan por la prueba de la jerga |

## 7. Lo que queda por hacer, y lo que no

- **Una cuenta de prueba con dos fincas**: en la finca de David solo entra él, así que el bloque de
  cambiar de finca **no se ve** hasta que haya una segunda finca (o hasta que le dé acceso a su hijo y
  el hijo entre en las dos). No es un fallo: es que el caso todavía no existe.
- **Avisar a la otra persona** de que ya puede entrar. Hoy se entera porque se lo dice el titular; no se
  le manda ningún correo (el programa no manda correos).
- **Papeles por finca**: hoy el papel de una cuenta dentro de una finca es titular o ayudante. Si algún
  día hace falta un papel de solo mirar (el técnico, la cooperativa), se añade un valor más en
  `AccesoAFinca.papel` y su frase en `textos.FINCAS`.
