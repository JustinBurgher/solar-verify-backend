# Solar Verify Backend

Professional solar quote analysis API with real component database.

## Features

- **Quote Analysis API** - Grade solar quotes A-F based on real market data
- **Component Database** - Real solar panels, batteries, and inverters
- **Email Tracking** - User management and usage limits
- **Pricing Benchmarks** - Current UK market rates

## API Endpoints

### Quote Analysis
- `POST /api/analyze-quote` - Analyze a solar quote
- `GET /api/components/panels` - Search solar panels
- `GET /api/components/batteries` - Search batteries
- `GET /api/pricing-benchmarks` - Get pricing benchmarks

### User Management
- `POST /api/register-email` - Register user email
- `POST /api/track-usage` - Track usage limits
- `POST /api/check-email-status` - Check user status

## Database

Contains real data for:
- 8 Solar panel models (including 515W Longi)
- 8 Battery models (including Fox ESS EP11)
- 6 Inverter models
- UK pricing benchmarks

## Deployment

Configured for Railway deployment with PostgreSQL database.

## Environment Variables

- `DATABASE_URL` - PostgreSQL connection string (auto-provided by Railway)
- `SECRET_KEY` - Flask secret key (optional)
- `PORT` - Server port (auto-provided by Railway)

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python src/main.py
```

Server runs on http://localhost:5000

