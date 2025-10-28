# Diagrama de arquitectura distribuida

```mermaid
graph TD
    subgraph Clientes
        C1[Cliente Web]
        C2[Cliente Móvil]
    end
    LB[Balanceador TCP<br/>Nginx/HAProxy]
    ORQ[Servidor Orquestador<br/>Sockets + Cola]
    subgraph Workers
        W1[Worker 1<br/>Pool de hilos]
        W2[Worker 2<br/>Pool de hilos]
        W3[Worker N<br/>Pool de hilos]
    end
    MQ[(RabbitMQ<br/>Cola de tareas)]
    DB[(PostgreSQL<br/>Resultados)]
    S3[(S3 / MinIO<br/>Artefactos)]

    C1 --> LB
    C2 --> LB
    LB --> ORQ
    ORQ --> MQ
    MQ --> W1
    MQ --> W2
    MQ --> W3
    W1 --> MQ
    W2 --> MQ
    W3 --> MQ
    MQ --> ORQ
    ORQ --> DB
    ORQ --> S3
```

## Flujo operacional

1. **Clientes** web o móviles establecen una conexión TCP (idealmente TLS) contra el balanceador de carga. En desarrollo se puede apuntar directamente al servidor orquestador.
2. El **balanceador (Nginx/HAProxy)** distribuye las conexiones entrantes entre varias réplicas del orquestador, asegurando alta disponibilidad.
3. El **servidor orquestador** valida el mensaje, lo publica en la cola de tareas (RabbitMQ) y espera la respuesta usando una cola de retorno (reply-to).
4. Los **workers** consumen tareas desde la cola, las procesan utilizando pools de hilos locales y publican los resultados en la cola de respuestas.
5. El **orquestador** recoge la respuesta y la devuelve al cliente. Opcionalmente persiste el resultado estructurado en **PostgreSQL** y archivos o reportes binarios en **S3/MinIO**.

El prototipo incluido en `src/` trabaja completamente en memoria (cola `queue.Queue`) para facilitar las pruebas locales, pero respeta el mismo flujo, por lo que la migración a RabbitMQ es directa.
