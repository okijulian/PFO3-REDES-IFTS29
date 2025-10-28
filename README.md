# PFO3 · Rediseño como Sistema Distribuido (Cliente-Servidor)

Este prototipo implementa la consigna del PFO3 para **Programación sobre Redes**: transformar el sistema en una arquitectura distribuida basada en sockets, con separación entre clientes, balanceo, cola de mensajes, workers y almacenamiento.

## Arquitectura propuesta

- **Clientes (web/móvil):** envían tareas a través de sockets TCP usando un protocolo JSON sencillo.
- **Balanceador de carga (Nginx/HAProxy):** distribuye conexiones entrantes entre múltiples instancias del servidor de orquestación. En desarrollo se usa una sola instancia, pero la configuración admite escalar horizontalmente.
- **Servidor orquestador:** recibe tareas, valida el contenido y las coloca en una cola de mensajes segura (simulada con `queue.Queue`, intercambiable por RabbitMQ/Kombu). Mantiene un pool de workers para procesar las tareas concurrentemente.
- **Workers:** cada worker se ejecuta en su propio hilo, obtiene tareas desde la cola, las procesa y retorna resultados al cliente mediante una `reply_queue`.
- **Cola de mensajes (RabbitMQ):** el prototipo usa una implementación en memoria, pero el flujo es compatible con usar RabbitMQ (o Redis Streams) para desacoplar el orquestador y los workers.
- **Almacenamiento distribuido:** los resultados podrían persistirse en PostgreSQL y archivos en S3; en este prototipo se deja preparado el punto de extensión en `procesar_tarea`.

Consulta el archivo [`docs/diagram.md`](docs/diagram.md) para un diagrama de alto nivel (formato Mermaid) y una descripción narrativa del flujo.  
Si prefieres editarlo en diagrams.net/draw.io, está disponible la versión editable en [`docs/diagram.drawio`](docs/diagram.drawio).

## Requisitos

- Python 3.9 o superior (solo se utilizan módulos estándar).

## Uso

1. Arrancar el servidor:

   ```bash
   python3 src/server.py
   ```

2. Enviar una tarea desde el cliente. Puedes pasar los parámetros por línea de comandos o dejar que el programa te guíe de forma interactiva (el menú se muestra en el cliente):

   ```bash
   # Ejemplo con argumentos
   python3 src/client.py --tipo uppercase --contenido "hola mundo"

   # Ejemplo interactivo (solo ejecuta el cliente y sigue el menú)
   python3 src/client.py
   ```

   Respuesta de ejemplo:

   ```json
   {
     "servidor": "127.0.0.1",
     "puerto": 9000,
     "solicitud": {
       "tarea_id": "4cbc8d09-aee0-48c1-96ef-3ccf2e6a2d28",
       "tipo": "uppercase",
       "contenido": "hola mundo"
     },
     "respuesta": {
       "estado": "ok",
       "resultado": "HOLA MUNDO",
       "tarea_id": "4cbc8d09-aee0-48c1-96ef-3ccf2e6a2d28",
       "worker": 2
     }
   }
   ```

## Tipos de tareas soportadas

| Código | Tipo         | Descripción                                          | Alias aceptados                      |
|--------|--------------|------------------------------------------------------|--------------------------------------|
| `1`    | `uppercase`  | Convierte texto a mayúsculas.                        | `uppercase`, `mayus`, `upper`        |
| `2`    | `reverse`    | Invierte la cadena recibida.                         | `reverse`, `invertir`, `reversa`     |
| `3`    | `word_count` | Cuenta palabras separadas por espacios.              | `word_count`, `contar`, `palabras`   |
| `4`    | `sleep`      | Simula un trabajo pesado esperando N segundos.       | `sleep`, `espera`, `delay`           |

Para agregar nuevas tareas basta con extender la función `procesar_tarea` en `src/server.py`.

## Escalamiento y mejoras sugeridas

1. **Balanceo real:** frente a múltiples instancias del servidor, configurar Nginx/HAProxy en modo TCP con health-checks.
2. **Cola externa:** reemplazar la cola en memoria por RabbitMQ usando `pika` o `kombu`, lo que permitiría distribuir workers en nodos distintos.
3. **Persistencia:** registrar los resultados de cada tarea (ej. en PostgreSQL) y publicar archivos a S3 cuando el contenido lo amerite.
4. **Seguridad:** agregar autenticación JWT y TLS a los sockets para productivo, reutilizando los componentes del PFO2.
