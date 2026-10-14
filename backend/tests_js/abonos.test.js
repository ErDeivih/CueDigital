/**
 * El abono: **«no consta» no es 0** (CRM-07, 14/10/2026).
 *
 * POR QUE ESTA PRUEBA. El contrato del CRM-07 dice, con estas palabras: *«Abono: composicion con unidades,
 * producto aplicado y nutrientes calculados separados; **no asumir 0**»*. Y la casa tiene su propia regla,
 * escrita en el comentario de `composicionDelAbono` (`web/app.js:8270`): *«Un 0 y un "no lo se" no son lo
 * mismo —el 0 dice que el abono no lleva nada— y cuando falta alguno de los tres se dice con palabras»*.
 *
 * Y sin embargo **el formulario no dejaba hacerlo**: los tres campos eran `obligatorio: true` y las pistas
 * decian **«Si el saco no lo trae, pon 0»** ✗. O sea: **el codigo que ensena «no consta» estaba escrito para
 * unos huecos que la pantalla no dejaba hacer**. Se arreglo el 14/10/2026 y esto lo defiende.
 *
 * QUE SE MIDE, Y POR QUE ASI. Estas dos cosas **son** la pantalla: la tabla de campos del formulario y las
 * pistas que el agricultor lee. No hay una funcion pura que las reciba —las lee `app.js` de su propio
 * modulo—, asi que la prueba lee **los dos ficheros que deciden**, y no una copia que se quedaria vieja.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const APP_JS = readFileSync(new URL("../web/app.js", import.meta.url), "utf8");
const TEXTOS = readFileSync(new URL("../app/textos.py", import.meta.url), "utf8");


test("la composicion del abono se puede dejar en «no consta»", () => {
  // Los tres nutrientes tienen que poder quedarse en blanco: en blanco es **no consta**, y el calculo
  // devuelve `None` (no un cero). Si alguno volviera a ser obligatorio, la pantalla obligaria a escribir un
  // numero que el agricultor no sabe, y ese numero seria mentira.
  for (const nutriente of ["riqueza_n", "riqueza_p", "riqueza_k"]) {
    const linea = APP_JS.split("\n").find((una) => una.includes(`"abono.${nutriente}": {`));
    assert.ok(linea, `no encuentro «abono.${nutriente}» en los campos del formulario`);
    assert.doesNotMatch(
      linea,
      /obligatorio/,
      `«abono.${nutriente}» vuelve a ser obligatorio: el saco puede no traerlo y habria que inventarse un 0`,
    );
  }
});


test("ninguna pista manda escribir un 0 cuando no se sabe", () => {
  const mandanCero = TEXTOS.split("\n").filter((una) => /pista/.test(una) && /pon 0/.test(una));
  assert.deepEqual(
    mandanCero,
    [],
    `hay pistas que mandan escribir 0 cuando no se sabe: ${mandanCero.join(" | ")}`,
  );
});


test("la pantalla del abono sabe decir que la composicion no consta", () => {
  // Y el otro lado: que **habiendo** huecos, se diga con palabras. Es la mitad que ya existia (el comentario
  // de `composicionDelAbono` cuenta que antes salia «null-null-null»), y esta prueba la ata al arreglo: si
  // alguien quitara las palabras, los huecos volverian a salir como numeros raros.
  assert.match(
    APP_JS,
    /composicion_no_se/,
    "la pantalla tiene que decir «no consta» con palabras cuando falta algun nutriente",
  );
});
