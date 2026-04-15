# Agent Builder

**Build AI Agents Through Conversation** - A conversational interface for designing and deploying LangGraph AI agents without writing code.

## What We're Building

Agent Builder lets users create custom AI agents by simply describing what they want in natural language. Instead of manually constructing LangGraph workflows and writing Python code, users chat with an AI that asks clarifying questions and generates agents based on requirements.

### The Vision

Complex AI automation should be accessible to everyone, not just experienced developers. Users describe their automation needs (e.g., "Monitor competitor websites and notify me of price changes"), and the system generates a LangGraph agent that handles the workflow.

### Current Pain Points Being Solved

1. **High Barrier to Entry**: LangGraph is powerful but requires understanding graphs, nodes, edges, and state management. Most users just want results.

2. **Repetitive Boilerplate**: Every agent requires similar setup code, error handling, and integration patterns. We abstract this away.

3. **No Streaming UX**: Most AI tools don't provide real-time feedback. We built ChatGPT-style streaming for immediate responsiveness.

4. **Vendor Lock-in**: Many platforms lock you into one LLM provider. We support multiple (OpenAI, xAI Grok) with easy switching.

5. **Lack of Agent Templates**: Building agents from scratch is tedious. Our conversational approach guides users through best practices.

## Architecture

### Tech Stack

**Frontend** (React Router v7 + TypeScript)
- Modern React with React Router for routing and SSR
- TailwindCSS + shadcn/ui for beautiful, accessible components
- Server-Sent Events (SSE) for real-time streaming
- Markdown rendering with syntax highlighting

**Backend** (FastAPI + Python)
- LangChain for LLM interactions
- LangGraph for agent workflow construction
- Multi-provider LLM support (OpenAI, xAI Grok)
- In-memory caching to reduce token usage
- SSE streaming for real-time responses

### Project Structure

```
blacklight_website/
├── frontend/                 # React Router application
│   ├── app/
│   │   ├── components/      # Reusable UI components
│   │   │   ├── chat-*.tsx  # Chat interface components
│   │   │   ├── code-block.tsx
│   │   │   ├── markdown-renderer.tsx
│   │   │   └── ui/         # shadcn/ui components
│   │   ├── routes/         # Route components (pages)
│   │   │   ├── home.tsx
│   │   │   ├── create-agent.tsx
│   │   │   └── agents.tsx
│   │   ├── lib/
│   │   │   ├── api.ts      # API client with SSE streaming
│   │   │   └── utils.ts
│   │   └── root.tsx        # App layout with sidebar
│   └── package.json
│
└── backend/                 # FastAPI application
    ├── src/agent_builder_api/
    │   ├── config/         # Configuration
    │   │   └── llm_config.py  # Multi-provider LLM setup
    │   ├── models/         # Pydantic models
    │   ├── routes/         # API endpoints
    │   │   └── agents.py   # Agent CRUD + streaming chat
    │   ├── services/       # Business logic
    │   │   └── agent_builder.py  # Core agent creation
    │   └── main.py         # FastAPI app entry
    ├── .env                # Environment configuration
    └── pyproject.toml      # Python dependencies
```

## Key Features Implemented

### 1. Conversational Agent Design
Users chat with an AI to design agents. The AI asks clarifying questions about:
- What triggers the agent
- What data sources it needs
- What actions it should take
- Expected outputs

### 2. Real-Time Streaming
Token-by-token streaming like ChatGPT using Server-Sent Events:
- Immediate feedback as responses generate
- No waiting for complete responses
- Smooth, responsive UX

### 3. ChatGPT-Style UI
Modern chat interface with:
- User messages in boxes (right-aligned)
- AI messages full-width with markdown
- Code syntax highlighting with copy buttons
- Responsive design

### 4. Multi-Provider LLM Support
Switch between providers via environment variables:
```bash
LLM_PROVIDER=xai_grok    # or openai
LLM_MODEL=grok-4-fast-non-reasoning
```

Currently supported:
- **OpenAI**: gpt-4o-mini, gpt-4o
- **xAI Grok**: grok-4-fast-non-reasoning, grok-3

### 5. OAuth2 Social Login
Secure authentication with social login providers:
- **Google OAuth2** - Login with Google accounts
- **GitHub OAuth2** - Login with GitHub accounts
- **Microsoft OAuth2** - Login with Microsoft/Azure AD accounts
- **Generic OIDC** - Support for Auth0, Okta, Keycloak, and other OIDC providers

Environment-driven configuration allows enabling/disabling providers without code changes. OAuth buttons automatically appear on the login page when enabled.

**See [OAUTH_SETUP.md](OAUTH_SETUP.md) for complete setup instructions.**

### 6. Response Caching
LangChain's InMemoryCache reduces costs by caching LLM responses for identical queries.

## Getting Started

### Prerequisites

- **Node.js** 18+ (for frontend)
- **Python** 3.10+ (for backend)
- **Docker & Docker Compose** (for database)
- **uv** (Python package manager) - Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- API key for OpenAI or xAI Grok

### Setup

**1. Clone the repository**
```bash
git clone <repo-url>
cd blacklight_website
```

**2. Database Setup (PostgreSQL via Docker)**
```bash
# Start PostgreSQL container
docker compose up -d postgres

# Or use the automated setup script
cd backend
./scripts/setup-db.sh
```

The database will be available at:
- Host: `localhost:5432`
- Database: `agent_builder`
- User: `agent_builder`
- Password: `agent_builder_dev`

**3. Backend Setup**
```bash
cd backend

# Copy .env.example to .env
cp .env.example .env

# Edit .env and add your API keys:
# - LLM_PROVIDER (xai_grok or openai)
# - LLM_MODEL (grok-4-fast-non-reasoning or gpt-4o-mini)
# - GROK_API_KEY or OPENAI_API_KEY
# - DATABASE_URL is already configured for Docker

# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start server
uv run uvicorn src.agent_builder_api.main:app --reload --host 0.0.0.0 --port 8000
```

**4. Frontend Setup**
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

**5. Open browser**
Navigate to `http://localhost:5173`

## Development

### Adding New Components

Frontend components follow shadcn/ui patterns:
```bash
cd frontend
npx shadcn@latest add <component-name>
```

### Adding New API Endpoints

1. Add route in `backend/src/agent_builder_api/routes/`
2. Add business logic in `backend/src/agent_builder_api/services/`
3. Update frontend `app/lib/api.ts` client

### Environment Variables

**Backend (.env)**
```bash
# LLM Configuration
LLM_PROVIDER=xai_grok  # or openai
LLM_MODEL=grok-4-fast-non-reasoning  # or gpt-4o-mini

# API Keys
OPENAI_API_KEY=sk-...
GROK_API_KEY=xai-...

# Server
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:5173
```

**Frontend (.env)**
```bash
VITE_API_URL=http://localhost:8000
```

## Pain Points & Solutions

### Problem: Slow Traditional Request/Response
**Solution**: Implemented SSE streaming for real-time token delivery

**Backend**:
```python
async def chat_for_agent_creation_stream():
    callback = StreamingCallbackHandler()
    streaming_llm = LLMConfig.get_llm(streaming=True, callbacks=[callback])

    async for token in callback.aiter():
        yield {"type": "token", "content": token}
```

**Frontend**:
```typescript
const reader = response.body?.getReader();
while (true) {
    const { done, value } = await reader.read();
    // Parse SSE events and update UI in real-time
}
```

### Problem: Complex State Management
**Solution**: Simplified state with React hooks, clear separation of concerns

### Problem: Poor Markdown Rendering
**Solution**: `react-markdown` + `remark-gfm` + `react-syntax-highlighter`

Supports:
- Code blocks with syntax highlighting
- Tables, lists, quotes
- Links with auto-open in new tab
- GFM features (strikethrough, task lists)

### Problem: Provider Lock-in
**Solution**: Abstracted LLM configuration

```python
# Easy provider switching
LLMConfig.get_llm(
    provider="xai_grok",  # or "openai"
    model="grok-4-fast-non-reasoning",
    streaming=True
)
```

### Problem: Token Costs
**Solution**: LangChain InMemoryCache automatically caches responses

## API Reference

### Streaming Chat Endpoint

**POST** `/api/agents/chat/stream`

Stream agent creation conversation with real-time responses.

**Request**:
```json
{
  "message": "I want to create a greeting agent",
  "conversation_history": [],
  "agent_id": null
}
```

**Response** (SSE):
```
event: message
data: {"type": "agent_id", "agent_id": "uuid"}

event: message
data: {"type": "token", "content": "That's"}

event: message
data: {"type": "token", "content": " a great"}

event: message
data: {"type": "done"}
```

**Event Types**:
- `agent_id`: New conversation started
- `token`: Text chunk
- `agent_ready`: Agent creation complete
- `agent_details`: Agent specification
- `done`: Stream finished
- `error`: Error occurred

### Agent Management

**GET** `/api/agents/` - List all agents
**GET** `/api/agents/{agent_id}` - Get agent details
**POST** `/api/agents/execute` - Execute agent

## Production Considerations

### Implemented Features ✅

1. **PostgreSQL Database**: Persistent storage for agents, users, conversations
   - SQLAlchemy 2.0 with async support
   - Alembic migrations for schema version control

2. **Authentication & Authorization**: Complete user management system
   - Cookie-based sessions with FastAPI-Users
   - OAuth2 social login (Google, GitHub, Microsoft, OIDC)
   - Role-Based Access Control (RBAC)
   - Audit logging for security events
   - User settings and preferences

3. **User Experience**: Personalized interface
   - Dark/light theme with system detection
   - Custom prompts and preferences
   - Persistent settings across sessions

### Current Limitations (Development Phase)

1. **No Rate Limiting**: Susceptible to abuse
   - **TODO**: Implement rate limiting middleware

2. **Basic Error Handling**: Needs more robust error recovery
   - **TODO**: Add retry logic, circuit breakers for LLM calls

3. **Single Instance**: Can't scale horizontally with current session approach
   - **TODO**: Use Redis for session/cache management

### Production Deployment Checklist

- [x] Replace in-memory storage with PostgreSQL
- [x] Add authentication (FastAPI-Users + OAuth2)
- [x] Add database migrations (Alembic)
- [x] Configure CORS for production domains
- [ ] Implement rate limiting
- [ ] Add structured logging (JSON logs with correlation IDs)
- [ ] Set up monitoring (Sentry/Datadog)
- [ ] Configure production LLM keys in secure vault
- [ ] Set up CDN for frontend assets
- [ ] Enable HTTPS/TLS
- [ ] Implement database backup strategy
- [ ] Set up CI/CD pipeline
- [ ] Add health check endpoints (/health, /ready)

## Code Architecture

### Streaming Implementation

**Backend Flow**:
1. User sends message via POST request
2. `StreamingCallbackHandler` captures tokens from LLM
3. Tokens buffered in `asyncio.Queue`
4. `EventSourceResponse` sends SSE events to client
5. Frontend parses events and updates UI in real-time

**Key Files**:
- `backend/src/agent_builder_api/services/agent_builder.py` - StreamingCallbackHandler
- `backend/src/agent_builder_api/routes/agents.py` - SSE endpoint
- `frontend/app/lib/api.ts` - SSE client
- `frontend/app/routes/create-agent.tsx` - UI state management

### Multi-Provider Architecture

The `LLMConfig` class abstracts provider differences:
```python
class LLMConfig:
    @staticmethod
    def get_llm(provider=None, model=None, streaming=False):
        # Returns configured ChatOpenAI instance
        # Works for both OpenAI and xAI Grok (OpenAI-compatible)
```

This allows swapping providers without code changes - just update `.env`.

## Troubleshooting

### Issue: Backend won't start - "GROK_API_KEY required"
**Solution**: Ensure `.env` file exists in `backend/` directory with valid key

### Issue: CORS errors in browser
**Solution**: Check `CORS_ORIGINS` in backend `.env` includes frontend URL

### Issue: Streaming not working
**Solution**: Ensure browser supports EventSource/SSE. Check network tab for SSE events.

### Issue: Port 8000 already in use
**Solution**: Kill existing process: `lsof -ti:8000 | xargs kill -9`

### Issue: Frontend shows "API error: 500"
**Solution**: Check backend logs for Python errors. Common issues:
- Missing API key in `.env`
- Invalid model name
- LangChain version mismatch

## Contributing

### Code Style

**TypeScript**: Follow React Router conventions, use TypeScript strict mode
**Python**: Follow PEP 8, use type hints, docstrings for public APIs

### Commit Messages

Use conventional commits:
```
feat: add streaming support
fix: resolve token parsing issue
docs: update API reference
refactor: simplify state management
```

## License

MIT

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Built with LangChain, LangGraph, FastAPI, and React Router**
