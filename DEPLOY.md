# Deployment Guide

This guide walks you through deploying the Playto Payout Engine to free hosting platforms. We'll cover deployment to **Railway**, **Render**, and **Fly.io**.

---

## Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment to Railway](#deployment-to-railway)
3. [Deployment to Render](#deployment-to-render)
4. [Deployment to Fly.io](#deployment-to-fly-io)
5. [Frontend Deployment (Vercel)](#frontend-deployment-vercel)
6. [Post-Deployment Steps](#post-deployment-steps)
7. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

Before deploying, make sure you have:

- [ ] GitHub repository with all code pushed
- [ ] Test account on chosen platform(s)
- [ ] Git installed locally
- [ ] All environment variables documented
- [ ] Database migrations tested locally
- [ ] Seed script tested locally

---

## Deployment to Railway

**Railway** is recommended for this project because it supports both Python and Node.js, has built-in PostgreSQL and Redis, and offers a generous free tier.

### Step 1: Prepare Your Repository

1. **Create `railway.yaml` in project root:**

```yaml
# Save this as: Kalyan/railway.yaml
build:
  backend:
    context: ./backend
    builder: HEROKU_BUILDPACK
    buildpacks:
      - heroku/python
  frontend:
    context: ./frontend
    builder: NIXPACKS
```

2. **Create `.railway/backend/.env.example`:**

```bash
# Copy from backend/.env.example
SECRET_KEY=your-production-secret-key-here
DEBUG=False
ALLOWED_HOSTS=.railway.app,railway.app
```

### Step 2: Deploy to Railway

1. **Go to [railway.app](https://railway.app/)**

2. **Click "Start a New Project"** → "Deploy from GitHub repo"

3. **Select your repository**

4. **Railway will auto-detect services**
   - It should find the backend (Python/Django)
   - It should find the frontend (Node.js/React)

5. **Configure Backend Service:**

   Click on the backend service, then:

   a. **Add Environment Variables:**
   - Click "Variables" tab
   - Add these variables:
     ```
     SECRET_KEY=generate-a-secure-random-key
     DEBUG=False
     ALLOWED_HOSTS=.railway.app,railway.app
     PYTHON_VERSION=3.9.18
     ```

   b. **Add PostgreSQL Database:**
   - Click "New" → "Database" → "Add PostgreSQL"
   - Railway will automatically set `DATABASE_URL`

   c. **Add Redis:**
   - Click "New" → "Database" → "Add Redis"
   - Railway will automatically set `REDIS_URL`

6. **Configure Frontend Service:**

   Click on the frontend service, then:

   a. **Add Environment Variables:**
     ```
     VITE_API_URL=https://your-backend.railway.app
     ```

7. **Update Django Settings (one-time setup):**

   Railway provides a **public URL**. You need to add it to `ALLOWED_HOSTS`:

   ```
   ALLOWED_HOSTS=.railway.app,*.railway.app,your-project-name.railway.app
   ```

8. **Run Database Migrations:**

   a. Click on backend service
   b. Click "Deployments" tab
   c. Click on latest deployment
   d. Click "View Logs"
   e. Click "Console" tab
   f. Run these commands:
      ```bash
      python manage.py migrate
      python manage.py createsuperuser
      python seed.py
      ```

9. **Deploy Celery Worker:**

   a. Click "New Service" → "Deploy from GitHub repo"
   b. Select same repository
   c. Set root directory to `backend`
   d. Add environment variables (same as backend)
   e. **Important:** Set command to:
      ```
      celery -A payout_engine worker -l info
      ```

10. **Get Your URLs:**

    - Frontend: Click frontend service → "Settings" → "Domains"
    - Backend API: Click backend service → "Settings" → "Domains"
    - Admin Panel: Backend URL + `/admin/`

### Step 3: Verify Deployment

1. **Visit frontend URL** → Should see merchant dashboard
2. **Visit backend URL** + `/api/v1/merchants/` → Should see JSON
3. **Visit admin panel** → Log in and check data

---

## Deployment to Render

**Render** is another great option with a simple interface and free PostgreSQL.

### Step 1: Prepare Your Repository

Create `render.yaml` in project root:

```yaml
# Save this as: Kalyan/render.yaml
services:
  - type: web
    name: playto-backend
    env: python
    buildCommand: cd backend && pip install -r requirements.txt
    startCommand: cd backend && python manage.py migrate && gunicorn payout_engine.wsgi:application
    envVars:
      - key: PYTHON_VERSION
        value: 3.9.18
      - key: DATABASE_URL
        fromDatabase:
          name: playto-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          type: redis
          name: playto-redis
          property: connectionString

  - type: web
    name: playto-frontend
    env: node
    buildCommand: cd frontend && npm install && npm run build
    startCommand: cd frontend && npm run preview
    envVars:
      - key: VITE_API_URL
        fromService:
          type: web
          name: playto-backend
          property: url

databases:
  - name: playto-db
    databaseName: playto_payout
    user: playto

services:
  - type: redis
    name: playto-redis
    maxmemoryPolicy: allkeys-lru
```

### Step 2: Deploy to Render

1. **Go to [render.com](https://render.com)**

2. **Click "New"** → "Blueprint New Instance"

3. **Connect your GitHub repository**

4. **Render will read `render.yaml`** and create all services

5. **Add Environment Variables:**

   For the backend service, add:
   ```
   SECRET_KEY=your-secret-key
   DEBUG=False
   ALLOWED_HOSTS=.onrender.com
   ```

6. **Deploy Celery Worker (separate service):**

   - Create a new "Worker" service
   - Set command to: `cd backend && celery -A payout_engine worker -l info`
   - Add same environment variables as backend

7. **Run Seed Script:**

   - Go to backend service → "Events" → "Deploy"
   - Click "Shell" button
   - Run: `python seed.py`

### Step 3: Access Your App

- Frontend: `https://playto-frontend.onrender.com`
- Backend API: `https://playto-backend.onrender.com/api/v1/`
- Admin: Backend URL + `/admin/`

---

## Deployment to Fly.io

**Fly.io** is great if you want your deployment close to your users in India.

### Step 1: Install Fly CLI

```bash
curl -L https://fly.io/install.sh | sh
```

### Step 2: Authenticate

```bash
fly auth login
```

### Step 3: Create `fly.toml` Files

**Backend (`backend/fly.toml`):**

```toml
app = "playto-backend"
primary_region = "sin"

[env]
  PORT = "8000"
  DEBUG = "False"

[[services]]
  protocol = "tcp"
  internal_port = 8000

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

[deploy]
  release_command = "python manage.py migrate && python seed.py"
```

**Frontend (`frontend/fly.toml`):**

```toml
app = "playto-frontend"
primary_region = "sin"

[build]
  [build.args]
    NODE_VERSION = "20"

[[services]]
  protocol = "tcp"
  internal_port = 3000

  [[services.ports]]
    port = 80
    handlers = ["http"]
```

### Step 4: Deploy Backend

```bash
cd backend

# Launch app
fly launch

# Add PostgreSQL
fly postgres create --name playto-db

# Add Redis
fly redis create --name playto-redis

# Attach to app
fly postgres attach --app playto-backend playto-db

# Set secrets
fly secrets set SECRET_KEY="your-secret-key"
fly secrets set DEBUG="False"
fly secrets set ALLOWED_HOSTS=".fly.dev"

# Deploy
fly deploy
```

### Step 5: Deploy Celery Worker

```bash
# Create separate app for worker
fly launch --name playto-worker --no-deploy

# Set same secrets
fly secrets set DATABASE_URL=$(fly secrets list -a playto-backend | grep DATABASE_URL)
fly secrets set REDIS_URL=$(fly secrets list -a playto-backend | grep REDIS_URL)

# Set command to run Celery
flyctl secrets set COMMAND="celery -A payout_engine worker -l info"

# Deploy
fly deploy
```

### Step 6: Deploy Frontend

```bash
cd frontend

# Build and deploy
fly launch
fly deploy
```

---

## Frontend Deployment (Vercel)

If you prefer to deploy only the frontend to Vercel:

### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

### Step 2: Deploy

```bash
cd frontend

# Deploy to Vercel
vercel

# When prompted:
# - Set up and deploy: Yes
# - Which scope: Your account
# - Link to existing project: No
# - Project name: playto-frontend
# - Directory: ./
# - Override settings: No
```

### Step 3: Add Environment Variable

```bash
vercel env add VITE_API_URL
# Enter your backend URL (e.g., https://playto-backend.railway.app)
```

---

## Post-Deployment Steps

### 1. Verify Everything Works

```bash
# Test API endpoint
curl https://your-backend-url.com/api/v1/merchants/

# Test frontend
open https://your-frontend-url.com
```

### 2. Seed Database

Most platforms have a "Shell" or "Console" feature:

```bash
# Access your backend service console
python manage.py migrate
python seed.py
```

### 3. Create Superuser

```bash
python manage.py createsuperuser
# Follow prompts to create admin user
```

### 4. Test Critical Paths

- [ ] Create a payout request
- [ ] Check if Celery worker processes it
- [ ] Verify status changes in admin panel
- [ ] Test idempotency (submit same request twice)
- [ ] Test concurrent payouts (use two browser tabs)

### 5. Set Up Monitoring

Most platforms have built-in logs:
- Check Celery worker logs
- Monitor PostgreSQL connections
- Track Redis queue size

---

## Troubleshooting

### Issue 1: Database Migration Failures

**Error:** `django.db.utils.OperationalError: no such table`

**Solution:**
```bash
# Run migrations manually
python manage.py migrate

# Or use the platform's shell/console
```

### Issue 2: CORS Errors

**Error:** `Access to fetch at 'http://backend' has been blocked by CORS policy`

**Solution:**
Add your frontend URL to `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` in Django settings.

### Issue 3: Celery Worker Not Processing Tasks

**Symptoms:** Payouts stuck in `PENDING` state

**Solution:**
```bash
# Check if Celery worker is running
# In your platform's logs, look for:
# "celery@xxx ready"

# If not running, check:
# 1. REDIS_URL is correct
# 2. Celery command is correct
# 3. Worker logs show errors
```

### Issue 4: Seed Script Fails

**Error:** `django.db.utils.IntegrityError: duplicate key value violates unique constraint`

**Solution:**
```bash
# Clear existing data first
python manage.py shell << EOF
from ledger.models import *
Merchant.objects.all().delete()
EOF

# Then run seed script
python seed.py
```

### Issue 5: Build Failures

**Error:** `Module not found` or `ImportError`

**Solution:**
- Check `requirements.txt` has all dependencies
- Verify Python/Node version matches
- Clear cache and redeploy

### Issue 6: Memory Issues on Free Tier

**Symptoms:** Service crashes or becomes unresponsive

**Solution:**
- Free tiers have limited RAM (usually 512MB)
- Consider:
  - Reducing Celery worker concurrency
  - Using database connection pooling
  - Optimizing queries

---

## Platform Comparison

| Platform | Free Tier | Best For | Limitations |
|----------|-----------|----------|-------------|
| **Railway** | $5 free/month | Full-stack apps | After free tier, min $5/month |
| **Render** | 750 hours/month | Simple deployment | Free tiers spin down with inactivity |
| **Fly.io** | 3 VMs x 512MB | Global deployment | More complex setup |
| **Vercel** | Unlimited | Frontend only | No backend support |

**My Recommendation:** Use **Railway** for this project. It has the best developer experience, reliable free tier, and supports both backend and frontend seamlessly.

---

## Cost Estimates (After Free Tier)

- **Railway:** ~$5-10/month (basic plan)
- **Render:** ~$7/month (starter plan)
- **Fly.io:** ~$2-5/month (pay-as-you-go)

All platforms offer free credits for new users!

---

## Security Checklist

Before going live:

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `DEBUG = False`
- [ ] Use environment variables for all sensitive data
- [ ] Enable HTTPS (most platforms do this automatically)
- [ ] Set up database backups
- [ ] Configure log retention
- [ ] Add rate limiting (production)
- [ ] Set up monitoring alerts

---

## Next Steps After Deployment

1. **Share Your URLs:**
   - Fill out the Playto submission form
   - Include both frontend and backend URLs

2. **Prepare for Demo:**
   - Test all flows before the interview
   - Have test merchant credentials ready
   - Prepare to walk through the code

3. **Monitor:**
   - Check logs daily
   - Track error rates
   - Monitor database size

4. **Iterate:**
   - Gather feedback from Playto team
   - Prioritize improvements
   - Keep commit history clean

---

## Getting Help

If you get stuck:

1. **Platform Documentation:**
   - [Railway Docs](https://docs.railway.app/)
   - [Render Docs](https://render.com/docs)
   - [Fly.io Docs](https://fly.io/docs/)

2. **Django Deployment:**
   - [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)

3. **Celery on Cloud:**
   - [Celery Deployment Guide](https://docs.celeryproject.org/en/stable/userguide/deploying.html)

4. **Community:**
   - Stack Overflow
   - Platform Discord servers
   - GitHub Discussions

---

**Good luck with your deployment! Remember, the goal is to get it working, not perfect. You can always optimize later.**
