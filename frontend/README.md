# Agent Builder Frontend

React frontend for the AI Agent Builder platform, built with React Router v7 and shadcn/ui.

## Features

- **Home Page**: Landing page with feature overview
- **Create Agent**: Conversational interface to design agents
- **Agent List**: View all created agents with metrics
- **Agent Details**: View and execute individual agents

## Tech Stack

- React Router v7
- TypeScript
- shadcn/ui (Tailwind CSS v4)
- Vite

## Setup

1. Install dependencies:
```bash
npm install
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Start dev server:
```bash
npm run dev
```

4. Build for production:
```bash
npm run build
```

## Routes

- `/` - Home page
- `/create-agent` - Chat interface for agent creation
- `/agents` - List of all agents
- `/agents/:id` - Agent details and execution

## Components

UI components from shadcn/ui located in `app/components/ui/`:
- Button
- Card
- Input
- ScrollArea

## API Client

The API client is located in `app/lib/api.ts` and provides typed methods for:
- `chatForAgentCreation()` - Chat with LLM to create agent
- `listAgents()` - Get all agents
- `getAgent()` - Get specific agent
- `executeAgent()` - Execute an agent

## Development

The app connects to the backend API at http://localhost:8000 by default. Make sure the backend is running before starting the frontend.

## Deployment

### Docker Deployment

To build and run using Docker:

```bash
docker build -t agent-builder-frontend .
docker run -p 3000:3000 agent-builder-frontend
```

### Environment Variables

- `VITE_API_URL` - Backend API URL (default: http://localhost:8000)
