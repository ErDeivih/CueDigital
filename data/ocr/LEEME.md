# Idiomas del lector de fotos (Tesseract) — no se tocan

Estos ficheros son **datos de un programa de terceros**, no material del proyecto. Se guardan tal y
como los publica su repositorio oficial, para poder decir de dónde sale cada uno y para que la
lectura de facturas funcione **sin tocar la instalación del ordenador**.

## Qué hay aquí

| Fichero | Qué es | Bytes | SHA-256 |
|---|---|---|---|
| `tessdata/spa.traineddata` | El idioma **español** para el lector de letras (Tesseract) | 2.294.433 | `6f2e04d02774a18f01bed44b1111f2cd7f3ba7ac9dc4373cd3f898a40ea6b464` |

## De dónde sale

Del repositorio oficial de Tesseract, que es de donde salen los idiomas:

```
https://github.com/tesseract-ocr/tessdata_fast
https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/spa.traineddata
```

Se usa `tessdata_fast` y no `tessdata_best` porque es la que el propio proyecto recomienda para
documentos normales: 2,3 MB frente a 13,6 MB, con una diferencia de precisión pequeña.

## Por qué hace falta

El lector de letras **no sabe español de fábrica**: hay que darle el idioma. En el ordenador donde se
probó esto, Tesseract estaba instalado pero solo con el inglés, y eso se nota en las facturas: los
números se leen bien (los dígitos no son de ningún idioma) pero las palabras con tilde o con eñe
salen cambiadas. Con el español, la misma foto se lee entera y bien: se comprobó con una factura de
ejemplo (membrete, NIF, número, fecha, totales y tres líneas) y el resultado fue exacto.

## Cómo se usa (y por qué así)

`backend/app/ocr.py` pone `TESSDATA_PREFIX` apuntando a esta carpeta cuando hay idiomas aquí dentro.
Así el español se puede instalar **sin permisos de administrador** y sin cambiar nada del ordenador
de nadie: la carpeta del sistema no se toca.

## Cómo se vuelve a descargar

```bash
cd backend
../.venv/Scripts/python.exe scripts/bajar_idioma_ocr.py
```

El guion comprueba la huella SHA-256: si el fichero que hay no coincide con la que está apuntada, se
para y lo dice, en vez de seguir con un idioma cambiado sin que nadie se entere de por qué las
lecturas salen raras.
