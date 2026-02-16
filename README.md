# AI-Assisted Reliability & Error Budget Platform

A production-grade SRE platform for monitoring Service Level Objectives (SLOs), managing error budgets, calculating burn rates, and making AI-assisted release decisions.

## Features

### Core Capabilities
- **SLO Monitoring** - Track availability, latency, and error rate SLOs with multi-window analysis
- **Error Budget Management** - Real-time budget consumption tracking with predictive exhaustion forecasting
- **Multi-Window Burn Rate** - Calculate burn rates across 5m, 1h, and 24h windows with weighted averaging
- **Release Gate Controller** - Data-driven deployment decisions based on risk levels
- **AI-Generated Insights** - Natural language summaries of reliability status and recommendations
- **Alert Management** - Configurable alerting with cooldowns and simulated notifications

### Key Algorithms
- **Linear Regression Forecasting** - Predict budget exhaustion time from burn rate trends
- **Multi-Window Burn Rate** - Weighted average across time windows (5m: 40%, 1h: 35%, 24h: 25%)
- **Risk Classification** - SAFE → OBSERVE → DANGER → FREEZE based on burn rate thresholds

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      React Frontend                          │
│  (Dashboard, Service Detail, Charts, AI Insights)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │   Services  │ │    SLO      │ │     Burn Rate       │   │
│  │   Router    │ │    API      │ │       API           │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │  Forecast   │ │   Release   │ │      Alerts         │   │
│  │    API      │ │    Gate     │ │       API           │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────┐    ┌────────────────────┐
│    PostgreSQL     │    │       Redis        │
│   (Primary DB)    │    │   (Cache/Queue)    │
└───────────────────┘    └────────────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local development)
- Python 3.11+ (for local development)

### Using Docker Compose

```bash
# Clone the repository
git clone <repository-url>
cd resume_project

# Copy environment variables
cp .env.example .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

Access the application:
- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Local Development

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set environment variables
set DATABASE_URL=postgresql://user:pass@localhost:5432/sre_platform

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## API Endpoints

### Services
- `GET /api/services` - List all services
- `GET /api/services/{name}` - Get service details
- `POST /api/services` - Create new service
- `PUT /api/services/{name}` - Update service
- `DELETE /api/services/{name}` - Delete service

### SLO
- `GET /api/slo/{service_name}` - Get SLO status for service
- `GET /api/slo/{service_name}/targets` - Get SLO targets
- `POST /api/slo/{service_name}/targets` - Create SLO target
- `PUT /api/slo/targets/{id}` - Update SLO target

### Burn Rate
- `GET /api/burn` - Get all burn rates
- `GET /api/burn/{service_name}` - Get service burn rate history
- `POST /api/burn/compute` - Trigger burn rate computation

### Forecast
- `GET /api/forecast/{service_name}` - Get exhaustion forecast

### Release Gate
- `GET /api/release/{service_name}` - Get release decision
- `POST /api/release/{service_name}/override` - Override release gate

### Summary
- `GET /api/summary` - Get executive overview
- `GET /api/summary/{service_name}` - Get AI narrative for service
- `GET /api/summary/heatmap` - Get risk heatmap data

### Alerts
- `GET /api/alerts` - List all alerts
- `GET /api/alerts/{service_name}` - Get service alerts
- `PATCH /api/alerts/{id}/acknowledge` - Acknowledge alert

## Data Models

### Service
```typescript
{
  id: number;
  name: string;
  tier: number;  // 1=Critical, 2=Important, 3=Standard
  owner: string;
  description?: string;
  created_at: string;
  updated_at: string;
}
```

### BurnRateSnapshot
```typescript
{
  service_name: string;
  burn_rate_5m: number;
  burn_rate_1h: number;
  burn_rate_24h: number;
  composite_burn_rate: number;
  error_budget_consumed: number;
  error_budget_remaining: number;
  risk_level: "SAFE" | "OBSERVE" | "DANGER" | "FREEZE";
  timestamp: string;
}
```

### Forecast
```typescript
{
  service_name: string;
  time_to_exhaustion_hours: number | null;
  projected_exhaustion_time: string | null;
  burn_rate_trend: "increasing" | "decreasing" | "stable";
  confidence_level: "high" | "medium" | "low";
  forecast_message: string;
  data_points_used: number;
}
```

## Risk Levels

| Level | Burn Rate | Action |
|-------|-----------|--------|
| SAFE | < 1.0 | Normal operations |
| OBSERVE | 1.0 - 1.5 | Monitor closely |
| DANGER | 1.5 - 2.0 | Consider halting deploys |
| FREEZE | > 2.0 | Block all deployments |

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | required |
| `REDIS_URL` | Redis connection string | optional |
| `DEBUG` | Enable debug mode | false |
| `ENABLE_METRICS_SIMULATOR` | Enable demo data generator | true |

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation and settings
- **PostgreSQL** - Primary database
- **Redis** - Caching (optional)
- **NumPy** - Numerical computations for forecasting

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Utility-first styling
- **Recharts** - Data visualization
- **React Query** - Server state management
- **React Router** - Client-side routing

## License

MIT License
