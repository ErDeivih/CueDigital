# Ficheros de prueba para comprobar la firma del cuaderno

Aquí no hay ningún secreto: **solo está la parte pública**. Son ficheros de usar y tirar, hechos
para que los tests puedan comprobar de verdad una firma CAdES sin salir a internet y sin
depender de que AutoFirma esté instalado.

## De dónde salen

Se generaron con **OpenSSL 3.5.6**, que produce estructuras CMS iguales a las que produce
AutoFirma (un CAdES es un CMS con los atributos firmados obligatorios, y esto los tiene:
`contentType`, `messageDigest`, `signingTime` y las capacidades S/MIME).

```bash
# Un certificado autofirmado de mentira (no vale para nada, es para probar)
openssl req -x509 -newkey rsa:2048 -keyout clave.pem -out cert.pem -days 3650 -nodes \
  -subj "/C=ES/O=EXPLOTACION DE PRUEBA/CN=PEREZ VELASCO DAVID/serialNumber=70922320A"

# La firma, en las dos formas posibles
openssl cms -sign -binary -in cuaderno_de_prueba.txt -signer cert.pem -inkey clave.pem \
  -outform DER -out firma_destacada.p7s -md sha256
openssl cms -sign -binary -nodetach -in cuaderno_de_prueba.txt -signer cert.pem -inkey clave.pem \
  -outform DER -out firma_adjunta.p7s -md sha256
```

**`-binary` no es un detalle: es lo que hace que se firme el fichero byte a byte.** Sin ese
parámetro, OpenSSL convierte los saltos de línea al formato del correo y la huella que firma no
es la del fichero. Un CAdES es binario.

## Las claves privadas NO están aquí

Se borraron en cuanto se generaron las firmas, y no hacen falta: **comprobar una firma solo
necesita la parte pública**. Por eso este directorio se puede tener en el repositorio sin
romper la regla de que aquí no entra ningún secreto.

Significa también que **estas firmas no se pueden volver a generar cambiando el contenido**: si
algún día hay que añadir un caso nuevo, se generan otra vez con OpenSSL y se borran las claves.

## Qué hay, y para qué sirve cada cosa

| Fichero | Para qué |
|---|---|
| `certificado.pem` | El certificado con el que están firmados casi todos |
| `certificado_de_otro.pem` | Otro agricultor distinto, para el caso de la firma ajena |
| `cuaderno_de_prueba.txt` | El contenido que se firmó, byte a byte |
| `cuaderno_cambiado.txt` | El mismo cuaderno con la fecha y la dosis cambiadas, para probar que **una firma válida deja de valer si el contenido no es el mismo** |
| `firma_destacada.p7s` | **La firma tal y como la produce AutoFirma**: el fichero de firma no lleva el cuaderno dentro |
| `firma_adjunta.p7s` | La firma llevando el cuaderno dentro (la otra forma posible) |
| `firma_de_otro.p7s` | Firmada por el otro certificado, sobre el mismo contenido |
| `firma_curva.p7s` + `certificado_curva.pem` | Firmada con **curva elíptica**, para probar que de lo que no se sabe comprobar se dice «no se pudo», **no** «no vale» |
| `firma_sha1.p7s` | Firmada con SHA-1, un algoritmo viejo que ya no se admite |

Los casos de firma manipulada (cambiar un byte de la firma) **no están como fichero**: se hacen
en el test a partir de una buena, porque así queda claro en el propio test qué se está
rompiendo.

## Lo que estas firmas NO valen

No valen para nada real. El certificado es autofirmado, o sea que **no lo respalda ninguna
autoridad de certificación**, y aquí no hay cadena de confianza que comprobar. Eso es
precisamente lo que el programa dice en voz alta: comprueba que **la firma corresponde al
contenido**, y no dice que el certificado sea de fiar, porque para eso haría falta una lista de
autoridades en la que confiar.
