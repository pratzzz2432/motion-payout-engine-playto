# Playto Payout Engine

A robust payment payout engine for Indian agencies, freelancers, and online businesses. Built for the Playto Founding Engineer Challenge 2026.

## Overview

This project implements a minimal version of Playto's payout engine that handles:
- Merchant ledger with balance tracking in paise
- Payout request API with idempotency
- Background payout processing with state machine
- Concurrency control to prevent overdrafts
- Automatic retry logic with exponential backoff
- Real-time dashboard for monitoring payouts

## Tech Stack

### Backend
- **Django 4.2** + **Django REST Framework**: Web framework and API
- **PostgreSQL**: Primary database (strongly preferred for financial data)
- **Celery**: Background task processing
- **Redis**: Celery broker and result backend

### Frontend
- **React 18**: UI library
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   React     │──────│  Django API  │──────│  PostgreSQL │
│  Frontend   │      │   (DRF)      │      │  Database   │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                     ┌──────┴──────┐
                     │   Celery    │
                     │  Workers    │
                     └─────────────┘
                            │
                     ┌──────┴──────┐
                     │    Redis    │
                     │    Queue    │
                     └─────────────┘
```

## Core Features

### 1. Merchant Ledger
- All amounts stored in **paise** as integers (BigIntegerField)
- Balance derived from credits and debits using database-level SQL
- **No floats, no DecimalField** for money storage
- Held balance tracking for pending payouts

### 2. Payout Request API
```
POST /api/v1/merchants/{merchant_id}/payouts/
Headers:
  Idempotency-Key: <UUID>

Body:
{
  "amount_paise": 5000,
  "bank_account_id": "<uuid>"
}
```

**Features:**
- Idempotency key prevents duplicate payouts
- Concurrent request handling with SELECT FOR UPDATE
- Atomic balance check and fund holding
- Returns cached response for duplicate keys

### 3. Payout Processor (Background Worker)
- Picks up pending payouts automatically
- Simulates bank settlement:
  - 70% succeed
  - 20% fail
  - 10% remain stuck (require retry)
- Moves payouts through state machine:
  - `PENDING → PROCESSING → COMPLETED` or `FAILED`
- Exponential backoff retry (1s, 2s, 4s, max 30s)
- Maximum 3 retry attempts
- Automatic fund return on failure

### 4. Merchant Dashboard
- **Available balance**: Funds ready for withdrawal
- **Held balance**: Funds held for pending payouts
- **Recent ledger entries**: Credit/debit history
- **Payout request form**: Create new payout requests
- **Payout history table**: Track all payouts with live status
- Auto-refresh every 5 seconds

## Technical Highlights

### Concurrency Control
Uses PostgreSQL's `SELECT FOR UPDATE` to prevent race conditions:

```python
with transaction.atomic():
    cursor.execute("""
        SELECT COALESCE(SUM(...), 0)
        FROM ledger_ledgerentry
        WHERE merchant_id = %s
        FOR UPDATE
    """, [merchant_id])
    # Check balance and create payout atomically
```

**Result:** If a merchant with ₹100 submits two ₹60 payout requests simultaneously, exactly one succeeds.

### Idempotency
- Keys scoped per merchant
- 24-hour expiration
- Response caching
- Database-backed storage

### State Machine
Strict validation prevents illegal state transitions:
- ✅ `PENDING → PROCESSING → COMPLETED`
- ✅ `PENDING → PROCESSING → FAILED`
- ❌ `COMPLETED → PENDING`
- ❌ `FAILED → COMPLETED`

### Money Integrity
- **Invariant**: `credits - debits = displayed balance`
- Database-level aggregation (no Python arithmetic)
- All amounts in paise (integers)
- Conversion to rupees only for display

## Project Structure

```
Kalyan/
├── backend/
│   ├── payout_engine/          # Django project settings
│   │   ├── settings.py
│   │   ├── celery.py           # Celery configuration
│   │   └── urls.py
│   ├── ledger/                 # Core app
│   │   ├── models.py           # Merchant, Payout, LedgerEntry models
│   │   ├── serializers.py      # DRF serializers
│   │   ├── views.py            # API views
│   │   ├── tasks.py            # Celery background tasks
│   │   ├── tests.py            # Concurrency & idempotency tests
│   │   └── admin.py            # Django admin config
│   ├── seed.py                 # Seed script for test data
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── PayoutForm.jsx
│   │   │   ├── PayoutHistory.jsx
│   │   │   ├── LedgerEntries.jsx
│   │   │   └── MerchantSelector.jsx
│   │   ├── services/
│   │   │   └── api.js          # API client
│   │   ├── App.jsx             # Main app component
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── docker-compose.yml          # Easy local setup
├── README.md                   # This file
├── EXPLAINER.md                # Technical deep-dive
├── GITHUB.md                   # Git commit strategy
└── DEPLOY.md                   # Deployment guide
```

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 20+
- PostgreSQL 13+
- Redis 6+

### Option 1: Docker Compose (Recommended)

```bash
# Clone and navigate to project
cd Kalyan

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend python manage.py migrate

# Seed test data
docker-compose exec backend python seed.py

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/api/v1/
# Django Admin: http://localhost:8000/admin/
```

### Option 2: Manual Setup

#### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Seed test data
python seed.py

# Start Django server
python manage.py runserver

# In another terminal, start Celery worker
celery -A payout_engine worker -l info
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

## Running Tests

```bash
cd backend

# Run all tests
python manage.py test

# Run specific test
python manage.py test ledger.tests.ConcurrencyTest
python manage.py test ledger.tests.IdempotencyTest
```

### Test Coverage
- ✅ **Concurrency Test**: Verifies only one of two concurrent payouts succeeds
- ✅ **Idempotency Test**: Ensures duplicate requests don't create duplicate payouts
- ✅ **State Machine Test**: Validates legal and illegal state transitions
- ✅ **Ledger Integrity Test**: Confirms balance calculation correctness

## API Endpoints

### Merchants
- `GET /api/v1/merchants/` - List all merchants
- `GET /api/v1/merchants/{id}/` - Get merchant details with balances

### Payouts
- `GET /api/v1/merchants/{merchant_id}/payouts/` - List merchant payouts
- `POST /api/v1/merchants/{merchant_id}/payouts/` - Create payout request

### Ledger
- `GET /api/v1/merchants/{merchant_id}/ledger/` - List ledger entries

## Usage Example

### Creating a Payout Request

```bash
curl -X POST http://localhost:8000/api/v1/merchants/{merchant_id}/payouts/ \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_paise": 5000,
    "bank_account_id": "bank-account-uuid"
  }'
```

**Response:**
```json
{
  "id": "payout-uuid",
  "merchant": "merchant-uuid",
  "merchant_name": "TechSolutions India Pvt Ltd",
  "amount_paise": 5000,
  "amount_rupees": 50.00,
  "status": "PENDING",
  "bank_account": {
    "id": "bank-account-uuid",
    "account_name": "TechSolutions India Pvt Ltd",
    "ifsc_code": "HDFC0001234"
  },
  "created_at": "2026-04-27T10:30:00Z"
}
```

## Monitoring

### Django Admin
Access at `http://localhost:8000/admin/` to view:
- All merchants and their balances
- Bank accounts
- Ledger entries (credits and debits)
- Payouts and their statuses
- Idempotency keys

### Celery Logs
```bash
# View Celery worker logs
docker-compose logs -f celery-worker

# Or if running manually
# Logs are printed to console where you ran: celery -A payout_engine worker -l info
```

## Database Schema

### Key Tables

**Merchant**
- `id`: UUID (PK)
- `name`: VARCHAR
- `email`: VARCHAR (unique)
- `created_at`, `updated_at`: TIMESTAMP

**LedgerEntry**
- `id`: UUID (PK)
- `merchant`: UUID (FK)
- `entry_type`: 'CREDIT' or 'DEBIT'
- `amount_paise`: BigIntegerField
- `is_held`: Boolean
- `description`: TEXT
- `payout`: UUID (FK, nullable)

**Payout**
- `id`: UUID (PK)
- `merchant`: UUID (FK)
- `bank_account`: UUID (FK)
- `amount_paise`: BigIntegerField
- `status`: 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
- `retry_count`: Integer
- `idempotency_key`: UUID (nullable)

**IdempotencyKey**
- `merchant`: UUID (FK)
- `key`: UUID (unique per merchant)
- `response_data`: JSON
- `created_at`: TIMESTAMP

## Configuration

### Environment Variables

**Backend (.env)**
```
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=playto_payout
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
IDEMPOTENCY_KEY_EXPIRY_HOURS=24
```

**Frontend**
Configured in `vite.config.js` - API proxy to `http://localhost:8000`

## Deployment

See [DEPLOY.md](DEPLOY.md) for detailed deployment instructions on:
- Railway
- Render
- Fly.io
- Vercel (frontend only)

## What I'm Proud Of

1. **Correct Concurrency Handling**: The `SELECT FOR UPDATE` lock ensures that even under high concurrency, no money can be lost or created.

2. **Clean Ledger Model**: Database-level balance calculation with held funds creates a clear audit trail and prevents inconsistencies.

3. **Robust Idempotency**: Database-backed idempotency with merchant-scoped keys and 24-hour expiration handles network retries gracefully.

4. **State Machine Validation**: Strict validation prevents illegal state transitions that could corrupt payout status.

5. **Comprehensive Testing**: Concurrency and idempotency tests prove the system handles real-world scenarios correctly.

## Known Limitations

1. **No authentication**: In a real system, merchants would need to authenticate with API keys or OAuth.
2. **Simplified bank simulation**: Real payout processing would integrate with actual banking APIs.
3. **Basic retry logic**: Production systems would need more sophisticated retry with dead letter queues.
4. **No webhook notifications**: Merchants aren't notified when payouts complete.
5. **Single-region deployment**: Production would need multi-region setup for high availability.

## Future Enhancements

If I were to continue building this:

1. **Event Sourcing**: Store all ledger events in an immutable log for perfect auditability
2. **Webhook Delivery**: Notify merchants of payout status changes with retry logic
3. **Audit Log**: Track every balance change with user, timestamp, and reason
4. **Payout Scheduling**: Allow merchants to schedule recurring payouts
5. **Multi-currency Support**: Handle payouts in multiple currencies
6. **Analytics Dashboard**: Charts for payout trends and merchant insights
7. **API Rate Limiting**: Prevent abuse with per-merchant rate limits
8. **Fraud Detection**: Flag suspicious payout patterns

## Learning Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [PostgreSQL SELECT FOR UPDATE](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)
- [React Documentation](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/)

## License

This project is for the Playto Founding Engineer Challenge 2026.

## Contact

For questions about this submission, please reach out through the challenge submission form.

---

**Built with ❤️ for the Playto Founding Engineer Challenge**
