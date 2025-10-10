# Solar Verify Backend - Magic Link Authentication

Professional solar quote analysis API with magic link email verification and PDF delivery.

## Features

- **Quote Analysis API** - Grade solar quotes A-F based on real UK market data
- **Magic Link Authentication** - Secure, one-click email verification (no OTP typing)
- **JWT-based Security** - 10-minute expiration, single-use tokens
- **PDF Delivery** - Automatic Solar Buyer's Guide delivery after verification
- **SendGrid Integration** - Professional email delivery

## API Endpoints

### POST /api/analyze-quote
Analyze a solar quote and return A-F grade

### POST /api/send-magic-link
Send magic link verification email

### POST /api/verify-token
Verify JWT token and send PDF

### GET /api/health
Health check endpoint

## Environment Variables

- `SENDGRID_API_KEY` - SendGrid API key
- `JWT_SECRET` - JWT signing secret
- `FRONTEND_URL` - Frontend URL (e.g., https://solarverify.co.uk )
- `PORT` - Server port (default: 5000)

## Deployment

Configured for Railway deployment with SendGrid email integration.
