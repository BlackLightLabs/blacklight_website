# Docker Setup Guide

This guide covers the Docker Compose setup for Agent Builder's PostgreSQL database.

## Quick Start

```bash
# From project root
docker compose up -d postgres

# Run migrations
cd backend
uv run alembic upgrade head
```

Or use the automated setup script:
```bash
cd backend
./scripts/setup-db.sh
```

## Docker Compose Services

### PostgreSQL Database
- **Image**: postgres:16-alpine
- **Container Name**: agent_builder_db
- **Port**: 5432 (mapped to localhost:5432)
- **Credentials**:
  - User: `agent_builder`
  - Password: `agent_builder_dev`
  - Database: `agent_builder`

### Database URL
```
postgresql://agent_builder:agent_builder_dev@localhost:5432/agent_builder
```

## Common Commands

### Starting Services
```bash
# Start only the database
docker compose up -d postgres

# Start all services (when backend Dockerfile is added)
docker compose up -d

# Start with logs visible
docker compose up postgres
```

### Stopping Services
```bash
# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes all data)
docker compose down -v
```

### Managing the Database

#### View Logs
```bash
docker compose logs -f postgres
```

#### Check Database Status
```bash
# Check if container is running
docker compose ps

# Check database health
docker compose exec postgres pg_isready -U agent_builder -d agent_builder
```

#### Access PostgreSQL CLI
```bash
# Connect to psql
docker compose exec postgres psql -U agent_builder -d agent_builder

# Common psql commands:
# \dt              - List all tables
# \d table_name    - Describe table structure
# \l               - List all databases
# \q               - Quit psql
```

#### Database Backup and Restore
```bash
# Backup
docker compose exec -T postgres pg_dump -U agent_builder agent_builder > backup.sql

# Restore
docker compose exec -T postgres psql -U agent_builder agent_builder < backup.sql
```

#### Reset Database
```bash
# Stop and remove volumes
docker compose down -v

# Start fresh
docker compose up -d postgres

# Run migrations
cd backend
uv run alembic upgrade head
```

## Database Migrations with Alembic

### Running Migrations
```bash
cd backend

# Apply all pending migrations
uv run alembic upgrade head

# Apply one migration at a time
uv run alembic upgrade +1

# Rollback one migration
uv run alembic downgrade -1

# Rollback all migrations
uv run alembic downgrade base
```

### Creating Migrations
```bash
cd backend

# Auto-generate migration from model changes
uv run alembic revision --autogenerate -m "description of changes"

# Create empty migration (for manual SQL)
uv run alembic revision -m "description"

# Always review generated migrations before applying!
```

### Migration History
```bash
# View current migration version
uv run alembic current

# View migration history
uv run alembic history

# View history with details
uv run alembic history --verbose
```

## Environment Variables

The database connection is configured via the `DATABASE_URL` environment variable in `backend/.env`:

```bash
# Docker Compose (default)
DATABASE_URL=postgresql://agent_builder:agent_builder_dev@localhost:5432/agent_builder

# For production, use a secure password
DATABASE_URL=postgresql://user:secure_password@host:5432/dbname
```

## Troubleshooting

### Port 5432 Already in Use
If you have a local PostgreSQL instance running:
```bash
# Option 1: Stop local PostgreSQL
# macOS (Homebrew):
brew services stop postgresql

# Linux (systemd):
sudo systemctl stop postgresql

# Option 2: Change Docker port in docker-compose.yml
ports:
  - "5433:5432"  # Use 5433 on host

# Then update DATABASE_URL:
DATABASE_URL=postgresql://agent_builder:agent_builder_dev@localhost:5433/agent_builder
```

### Container Won't Start
```bash
# Check Docker logs
docker compose logs postgres

# Remove old container and volume
docker compose down -v
docker compose up -d postgres
```

### Connection Refused Errors
```bash
# Wait for database to be ready
docker compose exec postgres pg_isready -U agent_builder

# Check if container is healthy
docker compose ps

# Verify network connectivity
docker compose exec postgres ping postgres
```

### Migration Failures
```bash
# Check current migration state
cd backend
uv run alembic current

# Check database connection
docker compose exec postgres psql -U agent_builder -d agent_builder -c "SELECT version();"

# If migrations are corrupted, you may need to reset:
# WARNING: This deletes all data
docker compose down -v
docker compose up -d postgres
uv run alembic upgrade head
```

## Production Considerations

### Security
1. **Change default password**: Never use `agent_builder_dev` in production
2. **Use secrets management**: Store credentials in a secure vault
3. **Restrict network access**: Use Docker networks, don't expose port 5432 publicly
4. **Enable SSL**: Configure PostgreSQL to require SSL connections

### Persistence
- Database data is stored in Docker volume `postgres_data`
- Backup volumes regularly in production
- Consider using managed database services (AWS RDS, GCP Cloud SQL, etc.)

### Performance
```yaml
# Add to docker-compose.yml postgres service for production:
environment:
  POSTGRES_SHARED_BUFFERS: 256MB
  POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
  POSTGRES_MAX_CONNECTIONS: 100
command:
  - "postgres"
  - "-c"
  - "shared_buffers=256MB"
  - "-c"
  - "max_connections=100"
```

## Additional Resources

- [PostgreSQL Docker Official Image](https://hub.docker.com/_/postgres)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
