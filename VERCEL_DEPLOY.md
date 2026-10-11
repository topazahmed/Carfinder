# Vercel Deployment Guide for CarFinder Frontend

## Current Deployment

Production frontend: https://carfinder-phi.vercel.app

Project settings: https://vercel.com/topazahmeds-projects/carfinder/settings

The frontend and video asset were verified with public HTTP 200 responses.
The configured Railway API at `https://carfinder-production-6990.up.railway.app`
currently returns HTTP 404, "Application not found". The page is deployed, but
live searches are not operational until a hosted backend is connected.

### Deployment Architecture

Vercel serves only the HTML and assets. `node build_frontend.cjs` copies these
into `public/`, which is the configured output directory. `.vercelignore`
excludes Python code, environments, and local credentials from CLI uploads.
Do not publish the repository root as the static output directory.

The Python API and Playwright jobs need a separate browser-capable host such as
Railway or a container service. Deploy the current backend changes there,
install Chromium and its Linux dependencies, and verify `/api/health` and an
actual search. Vercel does not run this project's scraper or schedule its CLI.

### Remaining Setup

1. Provision or restore the hosted Python API. Use `uvicorn api:app --host 0.0.0.0 --port $PORT`.
2. Set `SCRAPER_BACKEND=playwright` on that host and install Chromium during its build. On Linux use `python -m playwright install --with-deps chromium`; the image needs permission to install system libraries.
3. In Vercel Settings -> Environment Variables, set `API_BASE_URL` to the working API's HTTPS base URL, without `/api/search`. Select Production and Preview as appropriate, then redeploy. This value is public configuration, not a secret.
4. Configure backend CORS for `https://carfinder-phi.vercel.app` and approved preview/local origins. The backend currently permits all origins; narrow this before a production launch.
5. For persistence, provision PostgreSQL, set `DATABASE_URL` on the backend/job host only, and run `python conexion.py --init`. Verify a real save/search round-trip.
6. For scheduled inventory, create a hosted cron job using `python carfinder.py Toyota Camry --sources kijiji --require-database --sequential`. Set `SEARCH_MODE=stored` on the API after the first successful saved run.
7. AutoTrader access remains unverified, Facebook parsing is incomplete, and dealership feeds require provider access and licensing. Do not assume deploying fixes these source limitations.

Keep database passwords, proxy credentials, and inventory API keys off Vercel's
static frontend. For this architecture they belong on the backend/job host.
Vercel preview deployments may require authentication; production returned public
HTTP 200 during verification. Review Deployment Protection if access differs.

### Redeploy From This Workspace

```bash
node build_frontend.cjs
vercel --prod --yes
```

Vercel CLI is linked to `topazahmeds-projects/carfinder`. This deployment uploaded
the local working tree; no Git commit or push was made. Connect the GitHub
repository in Vercel and commit/push the intended changes to enable Git-based
automatic deployments. Do not commit generated `public/`, `.vercel/`, or `.env` files.

The older walkthrough below is general background. Use the build settings and
environment-variable configuration above instead of editing a hard-coded API URL.

## 🔷 Deploy Frontend to Vercel

### Prerequisites
- GitHub account
- Vercel account (sign up at https://vercel.com)
- Railway API deployed (see RAILWAY_DEPLOY.md)

### Step 1: Update API URL

Before deploying, update `index.html` with your Railway API URL:

```javascript
// Change this line in index.html:
const API_BASE_URL = 'http://localhost:8000';

// To your Railway URL (get from Railway dashboard):
const API_BASE_URL = 'https://your-app-name.railway.app';
```

### Step 2: Create vercel.json

This file is already created for you. It configures Vercel to serve your HTML file.

### Step 3: Deploy to Vercel

#### Option A: Using Vercel Dashboard (Easiest)

1. Go to https://vercel.com/dashboard
2. Click **"Add New..."** → **"Project"**
3. Import your GitHub repository
4. Vercel will auto-detect the project
5. Click **"Deploy"**

#### Option B: Using Vercel CLI

```powershell
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy
vercel
```

### Step 4: Configure CORS

Update `api.py` on Railway to allow your Vercel domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app.vercel.app",  # Your Vercel domain
        "http://localhost:8000"  # Keep for local testing
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Commit and push - Railway will auto-deploy the update.

### Step 5: Test Your Live Site

Visit your Vercel URL (e.g., `your-app.vercel.app`)
- Search for cars
- Check that it connects to your Railway API
- Verify results appear correctly

## 🎉 You're Live!

Your website: `https://your-app.vercel.app`
Your API: `https://your-app.railway.app`

## 💰 Pricing

Vercel Free Tier includes:
- **Unlimited deployments**
- **100 GB bandwidth/month**
- **Custom domains**
- **Automatic HTTPS**

## 🔧 Troubleshooting

### CORS Errors
Make sure your Railway API allows your Vercel domain in CORS settings

### API Not Connecting
1. Check Railway API is running: `https://your-app.railway.app/api/health`
2. Verify API_BASE_URL in `index.html` is correct
3. Check browser console for errors

### Changes Not Showing
Vercel caches aggressively:
1. Hard refresh: `Ctrl + Shift + R` (Windows) or `Cmd + Shift + R` (Mac)
2. Or redeploy from Vercel dashboard

## 🚀 Custom Domain (Optional)

1. Go to your project in Vercel
2. Click **"Settings"** → **"Domains"**
3. Add your custom domain
4. Update DNS settings as instructed
5. Vercel handles HTTPS automatically

## 📝 Environment Variables (If Needed)

If you need to make API_BASE_URL configurable:

1. In Vercel Dashboard → **"Settings"** → **"Environment Variables"**
2. Add: `API_BASE_URL` = `https://your-app.railway.app`
3. Update `index.html` to use it (requires build step)

## 🔄 Automatic Deployments

Vercel automatically deploys when you push to GitHub:
- **main branch** → Production
- **other branches** → Preview deployments

## 🔗 Useful Links

- Vercel Dashboard: https://vercel.com/dashboard
- Vercel Docs: https://vercel.com/docs
- Your Site: Check Vercel dashboard for URL

---

Happy deploying! 🚀
