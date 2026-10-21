"""***Un proxy que hace fallar UNA ruta*** (21/10/2026, D03).

*Para comprobar de verdad los estados de fallo hace falta **que una peticion falle**. Hasta hoy los recorridos usaban
un servidor de verdad, donde nada falla: por eso los arreglos de D03 se podian escribir pero **no verificar**.*

***Por que un proxy y no interceptar en el navegador***: *el instrumento (`NavegadorDeVerdad`) **descarta los eventos
de CDP** -busca su `id` y tira el resto-, asi que `Fetch.requestPaused` se quedaria sin contestar y **la pagina se
colgaria**. Arreglar eso es cambiar el instrumento; **un proxy son ochenta lineas, se prueba solo y no toca ni la
aplicacion ni el navegador**.*

***Y no toca la aplicacion***: *no hay ninguna variable de entorno de pruebas ni ningun campo en `/api/interfaz`. Lo
que se sirve por el proxy es **la aplicacion de verdad**, reenviada tal cual; solo la ruta elegida contesta 500.*

Uso:
    with el_proxy_que_falla("http://127.0.0.1:8010", "/api/parcelas") as direccion:
        ...  # `direccion` es por donde se entra: todo pasa, menos `/api/parcelas`, que da 500
"""

from __future__ import annotations

import http.client
import json
import threading
import time
import urllib.parse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class ElProxy(BaseHTTPRequestHandler):
    """*Reenvia todo al servidor de verdad, menos la ruta elegida.*"""

    protocol_version = "HTTP/1.1"
    servidor_de_verdad = ""
    la_ruta_que_falla = ""
    el_estado_que_da = 500
    el_mensaje = {"detail": "Fallo de prueba: esta ruta se ha hecho fallar a proposito."}

    def log_message(self, formato, *argumentos):
        # *Sin ruido: el proxy no tiene que llenar la salida de la prueba.*
        return

    def handle_one_request(self):
        # ***Y sin el ruido de las conexiones que el navegador corta al navegar*** (21/10/2026): *Chrome abre
        # conexiones que luego tira, y `BaseHTTPRequestHandler` escupe un `Traceback` por cada una. **Una prueba que
        # llena la pantalla de trazas esconde el fallo de verdad.***
        try:
            super().handle_one_request()
        except OSError:
            # *`BrokenPipe`, `ConnectionReset` y `ConnectionAborted` son **la misma cosa**: el navegador cerro la
            # conexion. Se atrapan como `OSError`, que es su madre comun, para que la prueba no se llene de trazas.*
            return

    def _la_peticion(self, cuerpo: bytes | None):
        if self.path.startswith(self.la_ruta_que_falla):
            el_cuerpo = json.dumps(self.el_mensaje).encode("utf-8")
            self.send_response(self.el_estado_que_da)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(el_cuerpo)))
            self.end_headers()
            self.wfile.write(el_cuerpo)
            return

        # ***Y lo demas, al servidor de verdad, tal cual.***
        el_destino = urllib.parse.urlsplit(self.servidor_de_verdad)
        el_camino = self.path
        las_cabeceras = {
            clave: valor
            for clave, valor in self.headers.items()
            if clave.lower() not in ("host", "connection", "content-length")
        }
        if cuerpo is not None:
            las_cabeceras["Content-Length"] = str(len(cuerpo))
        conexion = http.client.HTTPConnection(el_destino.hostname, el_destino.port, timeout=60)
        try:
            conexion.request(self.command, el_camino, body=cuerpo, headers=las_cabeceras)
            la_respuesta = conexion.getresponse()
            los_datos = la_respuesta.read()
            self.send_response(la_respuesta.status)
            for clave, valor in la_respuesta.getheaders():
                if clave.lower() in ("transfer-encoding", "connection", "content-length"):
                    continue
                self.send_header(clave, valor)
            self.send_header("Content-Length", str(len(los_datos)))
            self.end_headers()
            self.wfile.write(los_datos)
        finally:
            conexion.close()

    def do_GET(self):
        self._la_peticion(None)

    def do_HEAD(self):
        self._la_peticion(None)

    def do_POST(self):
        self._la_peticion(self._el_cuerpo())

    def do_PUT(self):
        self._la_peticion(self._el_cuerpo())

    def do_PATCH(self):
        self._la_peticion(self._el_cuerpo())

    def do_DELETE(self):
        self._la_peticion(self._el_cuerpo())

    def _el_cuerpo(self) -> bytes:
        el_largo = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(el_largo) if el_largo else b""


@contextmanager
def el_proxy_que_falla(servidor: str, la_ruta: str, estado: int = 500):
    """*Deja `la_ruta` contestando `estado` y todo lo demas pasando. Devuelve la direccion del proxy.*"""
    ElProxy.servidor_de_verdad = servidor.rstrip("/")
    ElProxy.la_ruta_que_falla = la_ruta
    ElProxy.el_estado_que_da = estado
    el_servidor = ThreadingHTTPServer(("127.0.0.1", 0), ElProxy)
    el_servidor.daemon_threads = True
    el_hilo = threading.Thread(target=el_servidor.serve_forever, daemon=True)
    el_hilo.start()
    la_direccion = f"http://127.0.0.1:{el_servidor.server_address[1]}"
    try:
        time.sleep(0.2)
        yield la_direccion
    finally:
        el_servidor.shutdown()
        el_servidor.server_close()
        el_hilo.join(timeout=5)
