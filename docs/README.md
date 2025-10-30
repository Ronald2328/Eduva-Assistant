# Documentación Técnica - ScienceBot WhatsApp API

Documentación completa del sistema de asistencia virtual para la Universidad Nacional de Piura.

## Índice General

### 1. [Arquitectura General](./1-arquitectura/1-arquitectura-general.md)
Visión general del sistema, stack tecnológico y diagrama de alto nivel.

---

### 2. Componentes del Sistema

- **[2.1 Evolution API](./2-componentes/2.1-evolution-api.md)**
  Gateway de WhatsApp para envío y recepción de mensajes

- **[2.2 PostgreSQL](./2-componentes/2.2-postgresql.md)**
  Base de datos relacional para Evolution API (sesiones, instancias, configuraciones)

- **[2.3 Redis](./2-componentes/2.3-redis.md)**
  Cache en memoria para Evolution API (colas, sesiones temporales, rendimiento)

- **[2.4 FastAPI](./2-componentes/2.4-fastapi.md)**
  Framework web principal de la aplicación

- **[2.5 LangGraph](./2-componentes/2.5-langgraph.md)**
  Motor del agente conversacional con grafos de estado

- **[2.6 MongoDB Atlas](./2-componentes/2.6-mongodb-atlas.md)**
  Base de datos documental con búsqueda vectorial

- **[2.7 Railway](./2-componentes/2.7-railway.md)**
  Plataforma de deployment y hosting

---

### 3. Flujo de Datos

- **[3.1 Recepción de Mensaje](./3-flujo-de-datos/3.1-recepcion-mensaje.md)**
  WhatsApp → Evolution API → FastAPI Webhook

- **[3.2 Procesamiento del Agente](./3-flujo-de-datos/3.2-procesamiento-agente.md)**
  LangGraph + OpenAI: flujo del grafo conversacional

- **[3.3 Búsqueda de Documentos](./3-flujo-de-datos/3.3-busqueda-documentos.md)**
  Pipeline de búsqueda semántica en MongoDB

- **[3.4 Respuesta al Usuario](./3-flujo-de-datos/3.4-respuesta-usuario.md)**
  Generación y envío de respuesta via Evolution API

---

### 4. Servicios Externos

- **[4.1 OpenAI API](./4-servicios-externos/4.1-openai-api.md)**
  GPT-4o-mini para chat + text-embedding-3-small

- **[4.2 Evolution API - Integración](./4-servicios-externos/4.2-evolution-integracion.md)**
  Detalles técnicos de la integración con Evolution

- **[4.3 MongoDB - Búsqueda Vectorial](./4-servicios-externos/4.3-mongodb-vectores.md)**
  Vector Search y comparación semántica

---

### 5. Modelo del Agente

- **[5.1 Estructura del Grafo](./5-modelo-agente/5.1-estructura-grafo.md)**
  StateGraph de LangGraph: nodos, edges y estados

- **[5.2 Herramientas (Tools)](./5-modelo-agente/5.2-herramientas.md)**
  Tool `search_documents` y binding con OpenAI

- **[5.3 Prompts del Sistema](./5-modelo-agente/5.3-prompts.md)**
  System prompts y estrategias de prompting

- **[5.4 Contexto Conversacional](./5-modelo-agente/5.4-contexto-conversacion.md)**
  Manejo de estado y memoria entre interacciones

---

### 6. Base de Datos

- **[6.1 Colecciones MongoDB](./6-base-de-datos/6.1-colecciones-mongodb.md)**
  Estructura de Documents y Pages

- **[6.2 Embeddings](./6-base-de-datos/6.2-embeddings.md)**
  Generación de vectores con OpenAI Embeddings

- **[6.3 Búsqueda Semántica](./6-base-de-datos/6.3-busqueda-semantica.md)**
  Pipeline de Vector Search paso a paso

---

### 7. Deployment

- **[7.1 Railway Setup](./7-deployment/7.1-railway-setup.md)**
  Configuración del proyecto en Railway

- **[7.2 Variables de Entorno](./7-deployment/7.2-variables-entorno.md)**
  Variables necesarias y configuración de secretos

- **[7.3 Monitoreo](./7-deployment/7.3-monitoreo.md)**
  Logfire para observabilidad y debugging

---

### 8. Diagramas

- **[8.1 Arquitectura Completa](./8-diagramas/8.1-arquitectura-completa.md)**
  Diagrama Mermaid de todos los componentes

- **[8.2 Flujo de Mensaje](./8-diagramas/8.2-flujo-mensaje.md)**
  Diagrama de secuencia de un mensaje completo

- **[8.3 Grafo LangGraph](./8-diagramas/8.3-grafo-langgraph.md)**
  Visualización del agente conversacional

---

## Conceptos Clave

### ¿Qué hace este sistema?

ScienceBot es un **asistente virtual de WhatsApp** para la Universidad Nacional de Piura que:

1. Recibe consultas de estudiantes via WhatsApp
2. Busca información en documentos académicos (reglamentos, guías, etc.)
3. Genera respuestas contextualizadas usando IA
4. Responde automáticamente al usuario

### Stack Tecnológico

```
Frontend: WhatsApp (usuarios)
    ↓
Gateway: Evolution API (PostgreSQL + Redis)
    ↓
Backend: FastAPI + LangGraph
    ↓
IA: OpenAI (GPT-4o-mini + Embeddings)
    ↓
Datos: MongoDB Atlas (Vector Search)
    ↓
Hosting: Railway
```

---

## Prerequisitos

Para entender esta documentación es útil tener conocimientos básicos de:

- Python y FastAPI
- APIs REST y webhooks
- Conceptos de IA: LLMs, embeddings, RAG
- Bases de datos (SQL y NoSQL)
- Docker y deployment

---

## Inicio Rápido

1. **Arquitectura**: Empieza por [1-arquitectura-general.md](./1-arquitectura/1-arquitectura-general.md)
2. **Componentes**: Revisa cada tecnología en el capítulo 2
3. **Flujo**: Entiende cómo fluyen los datos en el capítulo 3
4. **Implementación**: Profundiza en capítulos 4-6
5. **Deployment**: Aprende sobre Railway en el capítulo 7

---

## Recursos Adicionales

- [Código fuente principal](../app/)
- [README del proyecto](../README.md)
- [Evolution API Docs](https://doc.evolution-api.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

---

**Última actualización**: 2025-10-30
