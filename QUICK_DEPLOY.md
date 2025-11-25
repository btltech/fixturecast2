# 🚀 Quick Deployment Guide

## Deploy to Railway + Cloudflare in 5 Minutes

### Step 1: Deploy ML API to Railway (2 min)

1. **Go to [railway.app](https://railway.app)** and sign in
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select **`fixturecast2`** repository
4. Railway will auto-detect and deploy using the Dockerfile
5. **Add environment variables** in Railway dashboard:
   ```
   PORT=8000
   API_FOOTBALL_KEY=your_api_key_here
   ```
6. Copy your Railway URL (e.g., `https://fixturecast-ml.railway.app`)

### Step 2: Deploy Frontend to Cloudflare Pages (3 min)

1. **Go to [dash.cloudflare.com](https://dash.cloudflare.com)** → **Pages**
2. Click **"Create a project"** → **"Connect to Git"**
3. Select **`fixturecast2`** repository
4. **Configure build settings**:
   - **Build command**: `cd frontend && npm install && npm run build`
   - **Build output directory**: `frontend/dist`
   - **Root directory**: `/`

5. **Add environment variables**:
   ```
   VITE_API_URL=https://your-railway-backend.railway.app
   VITE_ML_API_URL=https://your-railway-ml.railway.app
   NODE_VERSION=18
   ```
6. Click **"Save and Deploy"**

### Step 3: Update CORS (1 min)

Update `backend/ml_api.py` and `backend/main.py` to allow your Cloudflare domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://fixturecast.pages.dev",  # Add your Cloudflare URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Commit and push → Railway will auto-deploy.

---

## ✅ You're Done!

Your app is now live:
- **ML API**: `https://your-project.railway.app`
- **Frontend**: `https://your-project.pages.dev`

---

## 📖 Full Documentation

See [DEPLOYMENT.md](./DEPLOYMENT.md) for:
- Detailed deployment options
- Custom domain setup
- Monitoring and logs
- Troubleshooting
- Cost optimization

---

## 💰 Cost Breakdown

- **Railway**: ~$5/month (Hobby plan)
- **Cloudflare Pages**: Free (unlimited bandwidth)
- **Total**: ~$5/month

---

## 🔧 Local Development

```bash
# Backend
source .venv/bin/activate
python backend/main.py        # Port 8001
python backend/ml_api.py      # Port 8000

# Frontend
cd frontend
npm run dev                   # Port 5173
```
