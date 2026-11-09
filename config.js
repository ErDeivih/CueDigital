// La dirección del servidor de CueDigital, para la pantalla publicada aparte.
// Vacía = el mismo sitio (cuando la sirve el propio programa).
window.CUEDIGITAL_API = "https://attract-leeds-integer-asp.trycloudflare.com";

// Entrada automática en la cuenta de ejemplo (demo publicada, sin formulario de entrar).
// Las credenciales son de una finca de ejemplo: no hay datos de ningún agricultor real.
(function () {
  var CLAVE = "cuedigital.token";
  try {
    if (localStorage.getItem(CLAVE) || !window.CUEDIGITAL_API) return;
    fetch(window.CUEDIGITAL_API + "/api/cuenta/entrar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ correo: "demo@cuedigital.local", clave: "cuaderno-demo-2026" }),
    })
      .then(function (respuesta) { return respuesta.ok ? respuesta.json() : null; })
      .then(function (datos) {
        if (datos && datos.token) {
          localStorage.setItem(CLAVE, datos.token);
          location.reload();
        }
      })
      .catch(function () {});
  } catch (error) {}
})();
