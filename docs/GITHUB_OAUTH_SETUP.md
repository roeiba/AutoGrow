# GitHub OAuth Setup for Guided Setup

## Overview
This document explains how to set up GitHub OAuth for the guided setup flow in the GitHub Pages site.

## Prerequisites
You need to create a GitHub OAuth App to enable authentication.

## Step 1: Create GitHub OAuth App

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Click "New OAuth App"
3. Fill in the details:
   - **Application name**: `SeedGPT Guided Setup`
   - **Homepage URL**: `https://roeiba.github.io/SeedGPT`
   - **Authorization callback URL**: `https://roeiba.github.io/SeedGPT/oauth-callback.html`
   - **Description**: `Automated GitHub authentication and fork setup for SeedGPT`

4. Click "Register application"
5. Note down the **Client ID** (you'll need this)
6. Generate a new **Client Secret** (you'll need this for the backend)

## Step 2: Update GitHub Pages Configuration

Update the `CLIENT_ID` constant in `/docs/index.html` and `/docs/oauth-callback.html`:

```javascript
const GITHUB_CLIENT_ID = 'your_client_id_here';
```

## Step 3: Backend OAuth Proxy (Required)

Since GitHub Pages is static, you need a backend service to exchange the OAuth code for an access token.

### Option A: Use GitHub Actions + Secrets
Store the Client Secret in GitHub Secrets and use it in workflows.

### Option B: Deploy a Simple OAuth Proxy
Deploy a serverless function (e.g., Netlify Functions, Vercel, or Cloud Functions) that:
1. Receives the OAuth code
2. Exchanges it for an access token using the Client Secret
3. Returns the token to the frontend

Example endpoint: `https://your-oauth-proxy.com/github/token`

## Step 4: Security Considerations

- **Never expose Client Secret in frontend code**
- Use HTTPS only
- Implement CSRF protection with state parameter
- Set appropriate OAuth scopes (minimum: `public_repo` for forking)
- Consider token expiration and refresh logic

## OAuth Flow

1. User clicks "Guided Setup" button
2. Redirect to GitHub OAuth authorization URL
3. User authorizes the app
4. GitHub redirects back with authorization code
5. Frontend sends code to OAuth proxy
6. Proxy exchanges code for access token
7. Frontend uses token to fork repository via GitHub API
8. Display success message with fork URL

## Required OAuth Scopes

- `public_repo` - Required to fork public repositories
- `repo` - Required if forking private repositories (optional)
- `workflow` - Required to enable GitHub Actions in forked repo (optional)

## Testing

Test the OAuth flow in a development environment before deploying to production.

## Troubleshooting

- **Redirect URI mismatch**: Ensure callback URL matches exactly in OAuth app settings
- **Invalid client**: Check Client ID is correct
- **Access denied**: User may have cancelled authorization
- **CORS errors**: Ensure OAuth proxy has proper CORS headers
