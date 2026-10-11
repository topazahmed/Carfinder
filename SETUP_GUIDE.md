# 🚗 CarFinder Web API - Quick Setup Guide

## Integrated Browser, Database, and Scheduled Runs

Use the existing project, rather than creating a second scraper. Playwright renders
HTML for the existing parsers, the aggregator saves searches when `DATABASE_URL`
is configured, and the CLI can be run as a scheduled one-shot job.

### Local Setup (macOS/Linux)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
```

On Windows, activate with `venv\Scripts\Activate.ps1`. In VS Code, install the
Microsoft Python extension and use **Python: Select Interpreter** to select
`venv`. Do not reuse the repository's tracked `.venv` Windows environment on macOS.
The requirements currently cap Playwright below 1.56 for macOS 12
compatibility. Upgrade macOS and revalidate before lifting this cap; older
browser builds do not receive current security updates.

The template enables Playwright. Without it, the default remains `requests` for
existing deployments. `PLAYWRIGHT_HEADLESS=false` opens a visible browser for
debugging. Optional `SCRAPER_PROXY_SERVER`, `SCRAPER_PROXY_USERNAME`, and
`SCRAPER_PROXY_PASSWORD` configure a provider you are authorized to use; proxies
are not universally required and do not guarantee access. Credentials remain in
the ignored `.env` file, not source code.

### PostgreSQL

Install/start PostgreSQL locally or provision a managed instance, create a database
named `car_finder`, and set this in `.env` using your own credentials:

```dotenv
DATABASE_URL=postgresql://YOUR_USER:YOUR_PASSWORD@localhost:5432/car_finder
```

URL-encode special characters in credentials. For managed databases, follow the
provider's TLS configuration, commonly `?sslmode=require`. The connection uses
`psycopg2-binary` to avoid requiring a local compiler and PostgreSQL headers.

```bash
python conexion.py
python conexion.py --init
python carfinder.py Toyota Camry --sources autotrader kijiji --require-database
```

`conexion.py` checks connectivity; `--init` creates the table and vehicle index.
The CLI also initializes the schema when persistence is enabled. Listings use a
unique `(source, external_id)` key, extracting numeric IDs from listing paths
or hashing the canonical URL when an ID is unavailable. Re-scraping updates the
snapshot and `last_seen`, preserving `first_seen`. This is not a price-history
table and does not mark disappeared listings as sold or delete old snapshots.

### Website and Search API

```bash
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/app for the existing interface or
http://127.0.0.1:8000/docs for the API. Local pages use the local API; the existing
hosted frontend still defaults to Railway. An explicit frontend override is
available with `?api=http://127.0.0.1:8000`.

```bash
curl 'http://127.0.0.1:8000/api/search?make=Toyota&model=Camry&mode=stored&location=Toronto&limit=100'
```

`mode=live` scrapes and saves when PostgreSQL is configured. `mode=stored` reads
saved snapshots without contacting listing sites. Set `SEARCH_MODE=stored` and
restart the API to make stored search the website default. Initialize the schema
and run a scrape first. Stored search matches make/model case-insensitively and
filters location by substring; live location handling remains source-dependent
and the existing Kijiji/AutoTrader scrapers do not reliably constrain geography.
`total_count` counts the returned results, capped by `limit` in stored mode.
Blocking browser/database work runs in FastAPI's worker threads, not its event loop.

### Scheduling

The CLI exits after each run, so use cron, Task Scheduler, or a hosted scheduled
worker. It exits nonzero if every source fails or PostgreSQL is unavailable;
partial source failures are logged while successful results are saved. Logs
should be monitored, and frequency should respect each site's terms and limits.

Example daily cron entry at 07:00, replacing the absolute project path:

```cron
0 7 * * * cd /absolute/path/to/Carfinder && venv/bin/python carfinder.py Toyota Camry --sources autotrader kijiji --require-database --sequential >> scraper.log 2>&1
```

Cron runs only while the machine is awake. Use a hosted worker for unattended
uptime. Configure its working directory, database URL, and browser installation
in the job environment. Chromium requires system libraries on Linux; install with
`python -m playwright install --with-deps chromium` during image/build setup.
Do not run browser jobs in an ordinary Vercel request function. AWS Lambda requires
a compatible container image, Chromium dependencies, and an EventBridge schedule;
deploying only these Python files is insufficient. PythonAnywhere support depends
on account permissions, browser availability, and outbound-network restrictions.
No cloud job or recurring local task is created automatically by this setup.

### Validation and Limitations

```bash
python -m unittest test_integration -v
```

These offline tests cover rendering, cleanup, fixture parsing, deduplication,
parameterized database queries, aggregator persistence, API modes, and CLI flags.
They do not prove access to live marketplaces or a real PostgreSQL database.
Facebook remains best-effort: its parser is a placeholder and login/access may
be required. Browser rendering does not bypass authentication, CAPTCHAs, or site
restrictions. AutoTrader and Kijiji selectors must be checked against current,
permitted pages and maintained when sites change. A selector timeout is reported
as a source failure rather than silently returning a successful empty search.

## Step 1: Install Dependencies

Open PowerShell in this directory and run:

```powershell
pip install -r requirements.txt
```

This will install:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- Pydantic (data validation)
- Plus all existing dependencies

## Step 2: Start the API Server

Option A - Using the start script:
```powershell
python start_api.py
```

Option B - Using uvicorn directly:
```powershell
uvicorn api:app --reload
```

## Step 3: Access the Application

Once the server is running, you have several options:

### 1. Web Interface (Recommended for beginners)
- Open `index.html` in your web browser
- Enter car make and model
- Click "Search Cars"

### 2. Interactive API Documentation
- Visit: http://localhost:8000/docs
- Try the API directly from your browser
- See all available endpoints and parameters

### 3. Direct API Access
Open a new PowerShell window and test with curl:
```powershell
curl "http://localhost:8000/api/search?make=Honda&model=Civic"
```

Or use a tool like Postman, Insomnia, or your web browser.

## Example Usage

### From Web Browser
1. Go to http://localhost:8000/docs
2. Click on `/api/search` endpoint
3. Click "Try it out"
4. Fill in:
   - make: `Honda`
   - model: `Civic`
   - location: `Toronto` (optional)
5. Click "Execute"

### From JavaScript
```javascript
fetch('http://localhost:8000/api/search?make=Toyota&model=Camry')
  .then(response => response.json())
  .then(data => console.log(data));
```

### From Python
```python
import requests
response = requests.get('http://localhost:8000/api/search', 
                       params={'make': 'Ford', 'model': 'F-150'})
print(response.json())
```

## What You Get

The API returns JSON with:
- **total_count**: Number of listings found
- **by_source**: Count of listings per website (Kijiji, AutoTrader, Facebook)
- **listings**: Array of car listings with details:
  - title
  - price
  - year
  - make/model
  - mileage
  - location
  - url (link to the listing)
  - source (which website)

## Troubleshooting

### Port Already in Use
If port 8000 is busy, use a different port:
```powershell
uvicorn api:app --reload --port 8080
```

### CORS Errors in Browser
The API is configured to allow all origins. If you still get CORS errors, make sure:
1. The API server is running
2. You're using the correct URL (http://localhost:8000)

### Import Errors
Make sure you installed all requirements:
```powershell
pip install -r requirements.txt
```

## Next Steps

- Read the full documentation in `API_README.md`
- Customize the `index.html` frontend
- Deploy to a production server
- Add authentication if needed
- Implement caching for better performance

## Stopping the Server

Press `CTRL + C` in the terminal where the server is running.

---

For more details, see `API_README.md`
