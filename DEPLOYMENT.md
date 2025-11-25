# FixtureCast Deployment Guide

## Overview
- **ML API & Backend API**: Deploy to Railway
- **Frontend**: Deploy to Cloudflare Pages

---

## 1. Deploy ML API to Railway

### Option A: Using Railway CLI

1. **Install Railway CLI**:
```bash
npm install -g @railway/cli
```

2. **Login to Railway**:
```bash
railway login
```

3. **Create new project**:
```bash
railway init
```

4. **Deploy ML API**:
```bash
railway up
```

5. **Add environment variables in Railway dashboard**:
   - `PORT=8000`
   - `PYTHON_VERSION=3.11.6`
   - `API_FOOTBALL_KEY=your_api_key_here`

### Option B: Using Railway Dashboard

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your `fixturecast2` repository
4. Railway will auto-detect Python and use the Dockerfile
5. Set environment variables:
   - `PORT=8000`
   - `API_FOOTBALL_KEY=your_api_key_here`
6. Deploy!

### Railway Configuration Files
- `Dockerfile` - Container configuration
- `railway.json` - Railway-specific settings
- `nixpacks.toml` - Alternative to Dockerfile
- `Procfile` - Process definitions

---

## 2. Deploy Backend API to Railway (Optional Separate Service)

If you want ML API and Backend API on separate Railway services:

1. Create a second Railway service
2. Set start command to: `python backend/main.py`
3. Set environment variables:
   - `PORT=8001`
   - `API_FOOTBALL_KEY=your_api_key_here`

**OR** run both on one Railway service with a proxy (recommended for cost):
- Edit `backend/ml_api.py` and `backend/main.py` to use different ports
- Use Railway's internal networking

---

## 3. Deploy Frontend to Cloudflare Pages

### Option A: Using Cloudflare Dashboard

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com)
2. Navigate to **Pages** → **Create a project**
3. Connect your GitHub account and select `fixturecast2` repo
4. Configure build settings:
   - **Framework preset**: Vite
   - **Build command**: `cd frontend && npm install && npm run build`
   - **Build output directory**: `frontend/dist`
   - **Root directory**: `/`

5. Add environment variables:
   - `VITE_API_URL`: `https://your-railway-backend.railway.app`
   - `VITE_ML_API_URL`: `https://your-railway-ml.railway.app`

6. Click **Save and Deploy**

### Option B: Using Wrangler CLI

1. **Install Wrangler**:
```bash
npm install -g wrangler
```

2. **Login to Cloudflare**:
```bash
wrangler login
```

3. **Update API URLs in frontend code**:
Create `frontend/.env.production`:
```env
VITE_API_URL=https://your-railway-backend.railway.app
VITE_ML_API_URL=https://your-railway-ml.railway.app
```

4. **Deploy to Cloudflare Pages**:
```bash
cd frontend
npm run build
wrangler pages deploy dist --project-name=fixturecast
```

---

## 4. Update Frontend API URLs

After deploying to Railway, update the API URLs in your frontend:

### Create environment-specific files:

**frontend/.env.production**:
```env
VITE_API_URL=https://fixturecast-backend.railway.app
VITE_ML_API_URL=https://fixturecast-ml.railway.app
```

**frontend/.env.development** (for local):
```env
VITE_API_URL=http://localhost:8001
VITE_ML_API_URL=http://localhost:8000
```

### Update API client files to use env variables:

Create `frontend/src/config.js`:
```javascript
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';
export const ML_API_URL = import.meta.env.VITE_ML_API_URL || 'http://localhost:8000';
```

Then update all API calls to use these constants instead of hardcoded URLs.

---

## 5. CORS Configuration

Update your backend to allow Cloudflare Pages domain:

In `backend/ml_api.py` and `backend/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://fixturecast.pages.dev",  # Your Cloudflare Pages URL
        "https://your-custom-domain.com"  # If you add custom domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 6. Custom Domains (Optional)

### Railway Custom Domain:
1. Go to Railway project → Settings → Domains
2. Add your custom domain (e.g., `api.fixturecast.com`)
3. Add DNS records provided by Railway

### Cloudflare Pages Custom Domain:
1. Go to Pages project → Custom domains
2. Add your domain (e.g., `fixturecast.com`)
3. DNS records are automatically configured

---

## 7. Environment Variables Summary

### Railway (ML API):
```
PORT=8000
PYTHON_VERSION=3.11.6
API_FOOTBALL_KEY=your_api_key_here
```

### Railway (Backend API):
```
PORT=8001
API_FOOTBALL_KEY=your_api_key_here
```

### Cloudflare Pages:
```
VITE_API_URL=https://your-railway-backend.railway.app
VITE_ML_API_URL=https://your-railway-ml.railway.app
NODE_VERSION=18
```

---

## 8. Post-Deployment Checklist

- [ ] ML API is accessible and returns health check
- [ ] Backend API is accessible and returns health check
- [ ] Frontend loads without errors
- [ ] API calls from frontend to backend work
- [ ] CORS is configured correctly
- [ ] Environment variables are set
- [ ] SSL certificates are active (automatic on both platforms)
- [ ] Custom domains configured (if applicable)

---

## 9. Monitoring & Logs

### Railway:
- View logs in Railway dashboard under "Deployments"
- Set up usage alerts in Settings

### Cloudflare Pages:
- View build logs and function logs in dashboard
- Use Cloudflare Analytics for traffic insights

---

## 10. Cost Optimization

### Railway:
- **Hobby Plan**: $5/month for 512 MB RAM, $0.000231/min usage
- Use single service for both APIs to save costs
- Enable sleep mode for non-production environments

### Cloudflare Pages:
- **Free tier**: Unlimited requests, unlimited bandwidth
- Upgrade to Pro ($20/month) only if needed for advanced features

---

## Quick Start Commands

```bash
# 1. Deploy ML API to Railway
railway login
railway init
railway up

# 2. Deploy Frontend to Cloudflare Pages
cd frontend
npm run build
wrangler pages deploy dist --project-name=fixturecast

# 3. Check deployments
railway logs
wrangler pages deployment list
```

---

## Troubleshooting

### Railway Issues:
- Check logs: `railway logs`
- Verify environment variables in dashboard
- Ensure Dockerfile builds locally first: `docker build -t fixturecast .`

### Cloudflare Pages Issues:
- Check build logs in dashboard
- Verify environment variables are set
- Test build locally: `npm run build`

### API Connection Issues:
- Verify CORS settings
- Check API URLs in browser console
- Test API endpoints directly with curl/Postman
