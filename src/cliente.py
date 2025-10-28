import argparse
import json
import socket
import sys
import uuid

HOST_PREDETERMINADO = "127.0.0.1"
PUERTO_PREDETERMINADO = 9000

TIPOS_DISPONIBLES = [
    ("1", "Palabras en mayusculas", "Convertir a mayúsculas un texto"),
    ("2", "Invertir texto", "Invertir el texto recibido"),
    ("3", "Contar Palabras", "Contar palabras separadas por espacios"),
    ("4", "tiempo de espera", "Simular trabajo esperando N segundos"),
]

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


def construir_argumentos():
    """Configura y obtiene los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Cliente simple para enviar tareas al servidor PFO3."
    )
    parser.add_argument(
        "--host",
        "--servidor",
        dest="servidor",
        default=HOST_PREDETERMINADO,
        help="Host o IP del servidor (predeterminado 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        "--puerto",
        dest="puerto",
        type=int,
        default=PUERTO_PREDETERMINADO,
        help="Puerto del servidor (predeterminado 9000)",
    )
    parser.add_argument("--tipo", help="Tipo de tarea (1, uppercase, reverse, word_count, sleep, etc.)")
    parser.add_argument(
        "--contenido",
        help="Dato a procesar. Para sleep debe ser un número (segundos).",
    )
    parser.add_argument("--tarea-id", help="ID de tarea opcional (por defecto se genera un UUID).")
    return parser.parse_args()


def mostrar_menu():
    """Muestra las opciones disponibles para el usuario."""
    print("=== Selecciona el tipo de tarea ===")
    for opcion, clave, descripcion in TIPOS_DISPONIBLES:
        print(f"{opcion}. {clave} -> {descripcion}")
    print("===============================")


def normalizar_tipo(valor):
    """Convierte el valor ingresado a la clave de tarea estándar."""
    if not valor:
        return None
    clave = ALIAS_TIPO.get(valor.strip().lower())
    if not clave:
        raise ValueError(f"Tipo de tarea no soportado: {valor}")
    return clave


def solicitar_tipo_interactivo():
    """Pide al usuario que elija el tipo de tarea."""
    mostrar_menu()
    while True:
        opcion = input("Opción (ej. 1): ").strip()
        try:
            return normalizar_tipo(opcion)
        except ValueError as error:
            print(f"{error}. Intenta nuevamente.")


def solicitar_contenido_interactivo(tipo):
    """Solicita el contenido según el tipo."""
    if tipo == "sleep":
        while True:
            valor = input("Segundos a esperar: ").strip()
            try:
                return float(valor)
            except ValueError:
                print("Debes ingresar un número (puede ser decimal).")
    prompt = "Texto a procesar: "
    return input(prompt)


def construir_tarea(args):
    """Arma el diccionario con la tarea que se enviará al servidor."""
    identificador = args.tarea_id or str(uuid.uuid4())
    tipo = None
    if args.tipo:
        tipo = normalizar_tipo(args.tipo)
    else:
        tipo = solicitar_tipo_interactivo()

    contenido = args.contenido
    if contenido is None:
        contenido = solicitar_contenido_interactivo(tipo)
    elif tipo == "sleep":
        try:
            contenido = float(contenido)
        except ValueError as error:
            raise ValueError("El contenido de sleep debe ser numérico.") from error

    if tipo != "sleep" and contenido == "":
        raise ValueError("El contenido no puede estar vacío.")

    return {
        "tarea_id": identificador,
        "tipo": tipo,
        "contenido": contenido,
    }


def enviar_tarea(host, puerto, tarea):
    """Envía la tarea al servidor y devuelve la respuesta decodificada."""
    mensaje = json.dumps(tarea) + "\n"
    with socket.create_connection((host, puerto), timeout=10) as conexion:
        conexion.sendall(mensaje.encode("utf-8"))
        buffer = ""
        while "\n" not in buffer:
            datos = conexion.recv(4096)
            if not datos:
                raise ConnectionError("El servidor cerró la conexión sin responder.")
            buffer += datos.decode("utf-8")
        respuesta, _ = buffer.split("\n", 1)
    return json.loads(respuesta)


def main():
    args = construir_argumentos()
    try:
        tarea = construir_tarea(args)
    except ValueError as error:
        print("[ERROR] {}".format(error), file=sys.stderr)
        sys.exit(1)

    try:
        respuesta = enviar_tarea(args.servidor, args.puerto, tarea)
    except Exception as error:  # noqa: BLE001
        print("[ERROR] No se pudo enviar la tarea: {}".format(error), file=sys.stderr)
        sys.exit(1)

    salida = {
        "servidor": args.servidor,
        "puerto": args.puerto,
        "solicitud": tarea,
        "respuesta": respuesta,
    }
    print(json.dumps(salida, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
