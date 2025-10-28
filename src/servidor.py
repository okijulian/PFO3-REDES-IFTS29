import json
import queue
import socket
import threading
import time
import uuid

# --- CONFIGURACIÓN BÁSICA ---

HOST_SERVIDOR = "0.0.0.0"
PUERTO_SERVIDOR = 9000
CANTIDAD_WORKERS = 4
TIEMPO_MAXIMO_RESPUESTA = 30  # segundos

ALIAS_TIPO = {
    "1": "uppercase",
    "uppercase": "uppercase",
    "mayus": "uppercase",
    "mayusculas": "uppercase",
    "upper": "uppercase",
    "2": "reverse",
    "reverse": "reverse",
    "reversa": "reverse",
    "invertir": "reverse",
    "3": "word_count",
    "word_count": "word_count",
    "contar": "word_count",
    "palabras": "word_count",
    "4": "sleep",
    "sleep": "sleep",
    "espera": "sleep",
    "delay": "sleep",
}

# Cola compartida donde se encolan las tareas junto con la cola de respuesta
cola_tareas = queue.Queue()


def normalizar_tipo(tipo_bruto):
    """Valida y normaliza el tipo recibido."""
    if isinstance(tipo_bruto, str):
        clave = ALIAS_TIPO.get(tipo_bruto.strip().lower())
        if clave:
            return clave
    raise ValueError(f"Tipo de tarea no soportado: {tipo_bruto}")


def procesar_tarea(tarea):
    """Ejecuta la tarea solicitada por el cliente."""
    tipo = normalizar_tipo(tarea.get("tipo"))
    contenido = tarea.get("contenido")

    if tipo == "uppercase":
        if not isinstance(contenido, str):
            raise ValueError("El contenido debe ser texto para uppercase.")
        resultado = contenido.upper()
    elif tipo == "reverse":
        if not isinstance(contenido, str):
            raise ValueError("El contenido debe ser texto para reverse.")
        resultado = contenido[::-1]
    elif tipo == "word_count":
        if not isinstance(contenido, str):
            raise ValueError("El contenido debe ser texto para word_count.")
        resultado = len(contenido.split())
    elif tipo == "sleep":
        # Simula un trabajo pesado esperando N segundos.
        duracion = float(contenido)
        time.sleep(max(0.0, duracion))
        resultado = f"Trabajo simulado durante {duracion:.2f}s"
    else:
        raise ValueError("Tipo de tarea no soportado: {}".format(tipo))

    return {"estado": "ok", "resultado": resultado}


class Worker(threading.Thread):
    """Consume tareas de la cola y publica los resultados."""

    def __init__(self, identificador, cola_trabajo):
        super().__init__(daemon=True)
        self.identificador = identificador
        self.cola_trabajo = cola_trabajo
        self._activo = True

    def detener(self):
        """Marca al worker como detenido."""
        self._activo = False

    def run(self):
        while self._activo:
            try:
                tarea, cola_respuesta = self.cola_trabajo.get(timeout=0.5)
            except queue.Empty:
                continue

            if tarea is None:
                # Señal para que el worker finalice.
                self.cola_trabajo.task_done()
                break

            try:
                print("Worker {} procesando tarea {}".format(self.identificador, tarea["tarea_id"]))
                respuesta = procesar_tarea(tarea)
            except Exception as error:
                respuesta = {"estado": "error", "mensaje": str(error)}
            finally:
                self.cola_trabajo.task_done()

            respuesta.setdefault("tarea_id", tarea.get("tarea_id"))
            respuesta.setdefault("worker", self.identificador)
            cola_respuesta.put(respuesta)


def inicializar_pool(cantidad):
    """Crea y arranca los workers."""
    workers = []
    for numero in range(1, cantidad + 1):
        worker = Worker(numero, cola_tareas)
        worker.start()
        workers.append(worker)
        print("Worker {} inicializado".format(numero))
    return workers


def detener_pool(workers):
    """Detiene todos los workers en orden."""
    for _ in workers:
        cola_tareas.put((None, None))
    for worker in workers:
        worker.detener()
    for worker in workers:
        worker.join(timeout=1.0)
        print("Worker {} detenido".format(worker.identificador))


def atender_cliente(conexion, direccion):
    """Recibe tareas del cliente, espera la respuesta y la reenvía."""
    print("Cliente conectado desde {}:{}".format(direccion[0], direccion[1]))
    buffer = ""
    try:
        while True:
            datos = conexion.recv(4096)
            if not datos:
                print("Cliente {}:{} desconectado".format(direccion[0], direccion[1]))
                break

            buffer += datos.decode("utf-8")

            while "\n" in buffer:
                mensaje, buffer = buffer.split("\n", 1)
                if not mensaje.strip():
                    continue

                try:
                    tarea = json.loads(mensaje)
                except json.JSONDecodeError:
                    respuesta = {"estado": "error", "mensaje": "Formato JSON inválido"}
                    conexion.sendall((json.dumps(respuesta) + "\n").encode("utf-8"))
                    continue

                if "tarea_id" not in tarea:
                    tarea["tarea_id"] = str(uuid.uuid4())
                cola_respuesta = queue.Queue()
                cola_tareas.put((tarea, cola_respuesta))

                try:
                    respuesta = cola_respuesta.get(timeout=TIEMPO_MAXIMO_RESPUESTA)
                except queue.Empty:
                    respuesta = {
                        "estado": "error",
                        "mensaje": "Se agotó el tiempo procesando la tarea",
                        "tarea_id": tarea["tarea_id"],
                    }

                conexion.sendall((json.dumps(respuesta) + "\n").encode("utf-8"))
    finally:
        conexion.close()


def iniciar_servidor(host=HOST_SERVIDOR, puerto=PUERTO_SERVIDOR, cantidad_workers=CANTIDAD_WORKERS):
    """Punto de entrada del servidor de sockets."""
    workers = inicializar_pool(cantidad_workers)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((host, puerto))
        servidor.listen()
        print("Servidor escuchando en {}:{}".format(host, puerto))

        try:
            while True:
                conexion, direccion = servidor.accept()
                hilo = threading.Thread(target=atender_cliente, args=(conexion, direccion), daemon=True)
                hilo.start()
        except KeyboardInterrupt:
            print("Cerrando servidor (Ctrl+C)")
        finally:
            detener_pool(workers)


if __name__ == "__main__":
    iniciar_servidor()
