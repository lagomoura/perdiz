# Plan: Chatbot RAG para CritiComida

## Context

El usuario quiere agregar un chatbot que responda preguntas sobre restaurantes y platos usando la base de datos como fuente de conocimiento. Si no hay contexto relevante, el bot debe decir que no tiene información suficiente. El chatbot será público (sin login), accesible como widget flotante desde cualquier página.

---

## Arquitectura

```
Usuario (pregunta)
    │
    ▼
[ChatWidget.tsx] ──POST /api/chat──▶ [FastAPI chat router]
                                           │
                                     1. Extrae keywords
                                     2. Busca en DB (restaurantes, platos)
                                     3. Construye contexto estructurado
                                     4. Llama Claude API (claude-haiku-4-5)
                                           │
                                     ◀─── Respuesta
```

---

## Fase 1 — Backend: nuevo endpoint `/api/chat`

### 1.1 Instalar dependencia
```
pip install litellm
```
Agregar `litellm` al `backend/requirements.txt`.

**¿Por qué LiteLLM?** Provee una interfaz unificada para 100+ proveedores (Anthropic, OpenAI, Google, Mistral, Ollama, etc.) usando el mismo código. Cambiar de modelo es solo cambiar variables de entorno.

### 1.2 `backend/app/services/chat_service.py` (NUEVO)
Lógica de recuperación de contexto + llamada al LLM via LiteLLM:

- Recibe el mensaje del usuario
- Extrae términos clave del mensaje
- Consulta directamente la DB via SQLAlchemy (sin HTTP interno)
- Para cada restaurante encontrado (máx. 3), carga nombre, descripción, rating, categoría, y top 3 platos con sus reviews
- Construye un `context_text` estructurado en español
- Si `context_text` está vacío → retorna respuesta estándar sin llamar al LLM
- Llama a `litellm.completion()` con configuración leída de env vars:
  ```python
  import litellm, os

  response = litellm.completion(
      model=os.getenv("CHAT_MODEL", "anthropic/claude-haiku-4-5-20251001"),
      api_key=os.getenv("CHAT_API_KEY"),   # opcional si ya hay key por proveedor
      messages=[
          {"role": "system", "content": SYSTEM_PROMPT},
          {"role": "user", "content": f"{context_text}\n\nPregunta: {message}"}
      ],
      max_tokens=512,
  )
  ```

### 1.3 `backend/app/routers/chat.py` (NUEVO)
```python
POST /api/chat
Body: { "message": str, "history": list[{"role": str, "content": str}] (optional) }
Response: { "response": str }
```
- Sin autenticación requerida
- Valida que `message` no esté vacío (max 500 chars)
- Delega a `chat_service`

### 1.4 `backend/app/main.py` (MODIFICAR)
Registrar el nuevo router:
```python
from app.routers import chat
app.include_router(chat.router, prefix="/api")
```

### 1.5 Variables de entorno (multi-modelo)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `CHAT_MODEL` | Modelo a usar (formato LiteLLM) | `anthropic/claude-haiku-4-5-20251001` |
| `CHAT_API_KEY` | API key del proveedor elegido | `sk-ant-...` / `sk-...` |

**Ejemplos de modelos compatibles sin cambiar código:**
```
# Anthropic Claude
CHAT_MODEL=anthropic/claude-haiku-4-5-20251001
CHAT_API_KEY=sk-ant-...

# OpenAI GPT-4o-mini
CHAT_MODEL=openai/gpt-4o-mini
CHAT_API_KEY=sk-...

# Google Gemini
CHAT_MODEL=gemini/gemini-1.5-flash
CHAT_API_KEY=AIza...

# Ollama (local, sin API key)
CHAT_MODEL=ollama/llama3
# (no CHAT_API_KEY necesaria)
```

LiteLLM resuelve el proveedor automáticamente a partir del prefijo del modelo.

---

## Fase 2 — Frontend: ChatWidget

### 2.1 `app/lib/api/chat.ts` (NUEVO)
```typescript
export async function sendChatMessage(message: string, history: Message[]): Promise<string>
```
Usa `fetchApi` con `skipAuth: true` para llamar `POST /api/chat`.

### 2.2 `app/components/ChatWidget.tsx` (NUEVO)
Widget flotante `'use client'` con:

**Estado:**
- `isOpen: boolean` — panel visible/oculto
- `messages: {role, content}[]` — historial
- `input: string` — texto del input
- `isLoading: boolean` — indicador de escritura

**UI:**
- Botón flotante fijo: `fixed bottom-6 right-6 z-[1100]`, `bg-main-pink`, icono de chat
- Panel: `fixed bottom-20 right-6 z-[1100] w-80 h-[480px]` con sombra y rounded-2xl
- Header: "CritiComida Bot" + botón cerrar
- Área de mensajes: scroll, burbujas user (derecha, pink) / bot (izquierda, neutral)
- Input + botón enviar (deshabilitado mientras carga)
- Typing indicator (3 puntos animados) durante `isLoading`
- Mensaje de bienvenida inicial del bot

### 2.3 `app/components/Providers.tsx` (MODIFICAR)
Importar y renderizar `<ChatWidget />` al final del JSX, fuera de los providers pero dentro del fragment raíz.

---

## Estrategia de contexto (chat_service)

```
Pregunta usuario: "¿Dónde comer buena pasta en Madrid?"

1. Keywords extraídos: ["pasta", "Madrid"]
2. Búsqueda DB: restaurants WHERE name ILIKE '%pasta%' OR location_name ILIKE '%pasta%'
                + restaurants WHERE name ILIKE '%Madrid%' OR location_name ILIKE '%Madrid%'
3. Merge deduplicado, máx 3 restaurantes
4. Para cada restaurante: load full detail + top 3 dishes (by computed_rating)
5. Context string:
   ---
   Restaurante: La Trattoria
   Categoría: Italiana | Rating: 4.2/5
   Descripción: Restaurante italiano en el centro de Madrid...
   Platos destacados:
   - Pasta Carbonara (4.5★): "Excelente, muy cremosa" - pros: sabor, porción
   - Fettuccine al pesto (4.1★): "Rica pasta fresca"
   ---
6. Si 0 resultados → sin llamada a Claude, respuesta estándar
```

---

## Archivos críticos a modificar/crear

| Archivo | Acción |
|---|---|
| `backend/app/services/chat_service.py` | CREAR |
| `backend/app/routers/chat.py` | CREAR |
| `backend/app/main.py` | MODIFICAR — registrar router |
| `backend/requirements.txt` | MODIFICAR — agregar `litellm` |
| `app/lib/api/chat.ts` | CREAR |
| `app/components/ChatWidget.tsx` | CREAR |
| `app/components/Providers.tsx` | MODIFICAR — añadir `<ChatWidget />` |

---

## Verificación

1. `pip install litellm` en entorno del backend
2. Configurar en `.env` del backend: `CHAT_MODEL=anthropic/claude-haiku-4-5-20251001` y `CHAT_API_KEY=sk-ant-...`
3. Reiniciar FastAPI: `uvicorn app.main:app --reload`
4. Test directo: `curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"message":"¿Qué restaurantes recomiendan?"}'`
5. `npm run dev` — verificar que el widget aparece en la esquina inferior derecha
6. Preguntar algo con contexto → debe responder con datos reales
7. Preguntar algo sin contexto (ej: "¿Cuál es la capital de Francia?") → debe responder que no tiene información suficiente
