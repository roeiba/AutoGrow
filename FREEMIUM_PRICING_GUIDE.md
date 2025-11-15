# Freemium Pricing Implementation Guide

This guide explains the freemium pricing system implemented for SeedGPT with usage-based metering and upgrade paths.

## Overview

SeedGPT now includes a 3-tier pricing model:

- **Free**: 100 AI operations/month - Perfect for trying out the platform
- **Pro**: $49/month - 1,000 AI operations/month - For serious developers
- **Enterprise**: Custom pricing - Unlimited operations - For organizations

## Key Features

### 1. Usage-Based Metering
- Tracks AI operations (projects, issues, PRs) per user
- Real-time usage monitoring
- Monthly quota resets
- Detailed usage breakdown

### 2. Upgrade Prompts
- Automatic warning at 80% quota usage
- Blocking prompt when quota is exceeded
- Self-service upgrade flow via Stripe Checkout

### 3. Conversion Tracking
- Free → Paid conversion rate
- Expansion revenue (upgrades)
- Churn tracking by tier
- Revenue impact metrics

## Architecture

### Backend Components

#### Database Models (`apps/seed-planter-api/src/db_models.py`)
- **User**: User account information
- **Subscription**: Tier, limits, Stripe integration
- **UsageMetric**: Monthly usage tracking
- **Payment**: Transaction records
- **ConversionEvent**: Analytics for tier changes
- **PricingConfig**: Dynamic pricing configuration

#### Services

**UsageMeteringService** (`apps/seed-planter-api/src/usage_metering.py`)
- `get_usage_stats()`: Current usage and limits
- `check_quota()`: Check if operation is allowed
- `enforce_quota()`: Raise exception if quota exceeded
- `increment_usage()`: Record usage
- `track_conversion_event()`: Log tier changes
- `get_conversion_metrics()`: Analytics dashboard data

**BillingService** (`apps/seed-planter-api/src/billing_service.py`)
- `create_free_subscription()`: Initialize new users
- `create_checkout_session()`: Stripe checkout for upgrades
- `handle_subscription_created()`: Process Stripe webhooks
- `cancel_subscription()`: Downgrade handling
- `get_subscription_info()`: Current subscription details

#### API Endpoints

**Authentication** (`/api/v1/auth`)
- `POST /register`: Create account (auto-assigns Free tier)
- `POST /login`: Authenticate and get JWT token
- `GET /me`: Get current user info

**Billing** (`/api/v1/billing`)
- `GET /usage`: Current usage statistics
- `GET /subscription`: Subscription details
- `POST /checkout`: Create Stripe checkout session
- `POST /cancel`: Cancel subscription
- `GET /pricing`: Pricing tier information
- `GET /metrics`: Conversion metrics (admin)
- `POST /webhooks/stripe`: Stripe webhook handler

### Frontend Components

#### React Components (`apps/seed-planter-frontend/src/components/`)

**UsageMeter.jsx**
- Visual progress bar for quota usage
- Color-coded warnings (blue < 80%, yellow ≥ 80%, red = exceeded)
- Detailed usage breakdown
- Enterprise unlimited display

**UpgradePrompt.jsx**
- Displays at 80% quota or when exceeded
- Shows benefits of target tier
- Pricing information
- One-click upgrade button

**PricingPlans.jsx**
- Full pricing comparison table
- Feature lists for each tier
- Upgrade/downgrade restrictions
- Call-to-action buttons

#### React Hooks (`apps/seed-planter-frontend/src/hooks/`)

**useAuth.js**
- User registration and login
- JWT token management
- Session persistence

**useBilling.js**
- Fetch usage and subscription data
- Create checkout sessions
- Cancel subscriptions
- Refresh billing data

## Setup Instructions

### 1. Environment Configuration

Update `.env` file in `apps/seed-planter-api/`:

```bash
# Database (use PostgreSQL in production)
DATABASE_URL=postgresql://user:password@localhost:5432/seedgpt
# Or SQLite for development:
# DATABASE_URL=sqlite:///./seedgpt.db

# Authentication
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...
```

### 2. Database Setup

Initialize the database:

```bash
cd apps/seed-planter-api
python -c "from src.database import init_db; init_db()"
```

For production, use Alembic migrations:

```bash
alembic init migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 3. Stripe Configuration

1. Create a Stripe account at https://stripe.com
2. Create products and prices:
   - **Pro**: $49/month recurring
   - **Enterprise**: Custom pricing
3. Configure webhook endpoint: `https://your-domain.com/api/v1/billing/webhooks/stripe`
4. Subscribe to events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `payment_intent.succeeded`

### 4. Install Dependencies

Backend:
```bash
cd apps/seed-planter-api
pip install -r requirements.txt
```

Frontend:
```bash
cd apps/seed-planter-frontend
npm install
```

### 5. Run the Application

Backend:
```bash
cd apps/seed-planter-api
python src/main.py
```

Frontend:
```bash
cd apps/seed-planter-frontend
npm run dev
```

## Usage Flow

### New User Registration

1. User visits the application
2. Clicks "Sign Up"
3. Enters email, password, and optional name
4. Account created with Free tier (100 AI ops/month)
5. JWT token issued, user logged in

### Creating a Project (Usage Metering)

1. User submits project creation request
2. Backend checks authentication
3. `UsageMeteringService.enforce_quota()` checks limits
4. If quota available:
   - Usage incremented
   - Project created
   - Success response
5. If quota exceeded:
   - 429 error returned
   - Frontend shows upgrade prompt

### Upgrade Flow

1. User clicks "Upgrade" button
2. Frontend calls `/api/v1/billing/checkout`
3. Backend creates Stripe Checkout session
4. User redirected to Stripe payment page
5. User completes payment
6. Stripe webhook notifies backend
7. `BillingService.handle_subscription_created()` processes:
   - Updates subscription tier
   - Sets new limits
   - Tracks conversion event
8. User redirected back to app with upgraded access

### Usage Monitoring

Users can view their usage anytime:
- Dashboard shows `UsageMeter` component
- Real-time quota percentage
- Detailed breakdown of operations
- Warning messages at 80%

## Conversion Metrics

### Tracked Events

- `free_signup`: New user registration
- `free_to_pro`: Upgrade from Free to Pro
- `pro_to_enterprise`: Upgrade from Pro to Enterprise
- `churn`: Downgrade or cancellation

### Analytics Dashboard

Access conversion metrics via `/api/v1/billing/metrics`:

```json
{
  "period_days": 30,
  "total_signups": 150,
  "free_to_paid_conversions": 15,
  "conversion_rate_percent": 10.0,
  "expansion_revenue_cents": 49000,
  "churn_by_tier": {
    "free": 5,
    "pro": 2,
    "enterprise": 0
  }
}
```

## Pricing Tiers Comparison

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| AI Operations/Month | 100 | 1,000 | Unlimited |
| Active Projects | 1 | 10 | Unlimited |
| Support | Community | Priority | Dedicated |
| Price | $0 | $49/mo | Custom |

## Security Considerations

1. **JWT Tokens**: Change `SECRET_KEY` in production
2. **HTTPS**: Use SSL/TLS for all API calls
3. **Stripe Webhooks**: Verify webhook signatures
4. **Database**: Use PostgreSQL in production, not SQLite
5. **Password Hashing**: Uses bcrypt via passlib
6. **Rate Limiting**: Implement additional rate limiting in production

## Testing

### Manual Testing

1. **Registration**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "password123"}'
   ```

2. **Check Usage**:
   ```bash
   curl http://localhost:8000/api/v1/billing/usage \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Create Project** (uses quota):
   ```bash
   curl -X POST http://localhost:8000/api/v1/projects \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"project_name": "test", "project_description": "A test project"}'
   ```

### Automated Testing

Run pytest suite:
```bash
cd apps/seed-planter-api
pytest tests/
```

## Monitoring & Operations

### Key Metrics to Monitor

1. **Conversion Rate**: Free → Paid percentage
2. **Expansion Revenue**: Upsells and upgrades
3. **Churn Rate**: Cancellations by tier
4. **Usage Patterns**: Average operations per tier
5. **Quota Warnings**: Users hitting 80% threshold

### Database Maintenance

- Monitor `usage_metrics` table growth
- Archive old metrics (>6 months)
- Index optimization on frequently queried columns

### Stripe Reconciliation

Regularly verify:
- Payment records match Stripe dashboard
- Subscription statuses are synchronized
- Webhook events are processed

## Troubleshooting

### Issue: Users can't upgrade

**Check**:
1. Stripe API keys configured correctly
2. Webhook endpoint accessible
3. Price IDs match Stripe dashboard

### Issue: Usage not tracking

**Check**:
1. Database connection working
2. `increment_usage()` called in project creation
3. User has valid subscription record

### Issue: Quota not enforcing

**Check**:
1. `enforce_quota()` called before operations
2. Subscription limits set correctly
3. Usage metrics being calculated properly

## Future Enhancements

1. **Annual Billing**: Discounted annual plans
2. **Usage Overage**: Pay-as-you-go for excess usage
3. **Team Plans**: Multi-user subscriptions
4. **API Credits**: Separate credit pool for API access
5. **Promotional Codes**: Discount codes and trials
6. **Referral Program**: Reward user referrals

## Support

For issues or questions:
- GitHub Issues: https://github.com/roeiba/SeedGPT/issues
- Email: support@seedgpt.com

## License

MIT License - See LICENSE file for details
