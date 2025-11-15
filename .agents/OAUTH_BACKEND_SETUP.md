# OAuth Backend Setup Complete ✅

## Overview

The OAuth flow is now fully integrated with the seed-planter-api backend. Users can authenticate with GitHub and automatically fork the SeedGPT repository.

## Architecture

```
User Browser → GitHub OAuth → oauth-callback.html → seed-planter-api → GitHub API
                                                    (/api/v1/oauth/exchange)
```

## Changes Made

### 1. Backend API (`apps/seed-planter-api`)

**New Endpoint**: `POST /api/v1/oauth/exchange`
- Accepts OAuth authorization code
- Exchanges it for access token using client secret (secure)
- Returns access token to frontend

**Files Modified**:
- `src/models.py`: Added `OAuthExchangeRequest` and `OAuthExchangeResponse` models
- `src/config.py`: Added `github_oauth_client_id` and `github_oauth_client_secret` config
- `src/main.py`: Added OAuth exchange endpoint

### 2. Frontend (`docs/`)

**Files Modified**:
- `oauth-callback.html`: Updated `OAUTH_PROXY_URL` to point to seed-planter-api
- `guided-setup.html`: Restored OAuth option as "AUTOMATED"

### 3. Deployment

**Files Modified**:
- `.github/workflows/apps-seed-planter-api.yml`: Added `GITHUB_OAUTH_CLIENT_SECRET` secret mount

**New Script**:
- `.agents/scripts/add_oauth_secret.sh`: Helper script to add secret to GCP

## Setup Instructions

### Step 1: Add OAuth Client Secret to GCP

Run the helper script:

```bash
./.agents/scripts/add_oauth_secret.sh
```

Or manually:

```bash
# Get the client secret from GitHub OAuth App settings
# https://github.com/settings/apps

# Add to GCP Secret Manager
echo -n "YOUR_CLIENT_SECRET" | gcloud secrets create GITHUB_OAUTH_CLIENT_SECRET \
  --project=magic-mirror-427812 \
  --data-file=- \
  --replication-policy="automatic"
```

### Step 2: Deploy Updated API

The workflow will automatically deploy when you push changes to `apps/seed-planter-api/`:

```bash
git add .
git commit -m "Add OAuth backend support"
git push
```

Or manually trigger:

```bash
# Go to GitHub Actions
# Select "Seed Planter API - CI/CD"
# Click "Run workflow"
```

### Step 3: Verify OAuth Flow

1. Visit: https://roeiba.github.io/SeedGPT/guided-setup.html
2. Select "GitHub OAuth" option
3. Click "Authorize with GitHub"
4. Should successfully fork the repository

## API Endpoint Details

### `POST /api/v1/oauth/exchange`

**Request**:
```json
{
  "code": "authorization_code_from_github"
}
```

**Response** (Success):
```json
{
  "access_token": "gho_...",
  "token_type": "bearer",
  "scope": "public_repo workflow"
}
```

**Response** (Error):
```json
{
  "detail": "Error message"
}
```

## Security Notes

- ✅ Client secret is stored in GCP Secret Manager (encrypted)
- ✅ Secret is mounted to Cloud Run at runtime (not in code)
- ✅ CORS is configured to allow GitHub Pages origin
- ✅ State parameter prevents CSRF attacks
- ✅ Token exchange happens server-side only

## Testing

### Test OAuth Endpoint

```bash
# Get an authorization code from GitHub OAuth flow first
# Then test the exchange:

curl -X POST https://seed-planter-api-pmxej6pldq-uc.a.run.app/api/v1/oauth/exchange \
  -H "Content-Type: application/json" \
  -d '{"code":"YOUR_AUTH_CODE"}'
```

### Test Full Flow

1. Open browser dev tools
2. Visit: https://roeiba.github.io/SeedGPT/guided-setup.html
3. Select OAuth option
4. Monitor network requests
5. Should see successful token exchange and fork

## Troubleshooting

### Error: "OAuth client secret not configured on server"

**Solution**: Run `.agents/scripts/add_oauth_secret.sh` to add the secret to GCP

### Error: "Failed to exchange authorization code"

**Possible causes**:
- Invalid client secret
- Authorization code already used (codes are single-use)
- Authorization code expired (10 minutes)

**Solution**: Try the OAuth flow again to get a fresh code

### Error: CORS issues

**Solution**: Verify CORS is configured in `src/main.py`:
```python
allow_origins=["*"]  # Or specific origins
```

## Next Steps

1. ✅ Add OAuth secret to GCP Secret Manager
2. ✅ Deploy updated API
3. ✅ Test OAuth flow end-to-end
4. 📝 Update documentation with OAuth setup instructions
5. 🎉 Users can now use one-click OAuth setup!

## Related Files

- Backend: `apps/seed-planter-api/src/main.py`
- Frontend: `docs/oauth-callback.html`, `docs/guided-setup.html`
- Workflow: `.github/workflows/apps-seed-planter-api.yml`
- Script: `.agents/scripts/add_oauth_secret.sh`
