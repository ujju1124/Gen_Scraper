# Quick Start Guide - Frontend + Backend

This guide will help you get both the backend and frontend running locally.

## Option 1: Using Make (Recommended - Easiest)

This automatically sets up PostgreSQL, runs migrations, and creates an admin user.

### Prerequisites
- Docker installed and running
- Go 1.21+ installed
- Node.js 18+ installed

### Steps

1. **Start the backend development environment**:
   ```bash
   make saas-dev
   ```
   
   This will:
   - Start PostgreSQL in Docker
   - Run database migrations
   - Create default admin user (username: `admin`, password: `1234#abcd`)
   - Start the backend server on `http://localhost:8080`

2. **Access the admin dashboard**:
   - Open `http://localhost:8080/admin`
   - Login with: `admin` / `1234#abcd`
   - Navigate to "API Keys" and generate a new API key

3. **Install frontend dependencies**:
   ```bash
   cd frontend
   npm install
   ```

4. **Start the frontend**:
   ```bash
   npm run dev
   ```
   
   The frontend will be available at `http://localhost:5173`

5. **Configure the frontend**:
   - Open the frontend in your browser
   - Go to "Settings" page
   - Paste your API key from step 2
   - Click "Save API Key"

6. **Start scraping**:
   - Click "New Job"
   - Enter a keyword (e.g., "restaurants in New York")
   - Submit the job
   - View results on the Dashboard

### Stop the backend
```bash
make saas-dev-stop
```

### Reset all data (if needed)
```bash
make saas-dev-reset
```

---

## Option 2: Manual Setup (If you don't have Make)

### Prerequisites
- PostgreSQL running locally or in Docker
- Go 1.21+ installed
- Node.js 18+ installed

### Steps

1. **Start PostgreSQL** (if using Docker):
   ```bash
   docker run -d \
     --name gmaps-postgres \
     -e POSTGRES_USER=postgres \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=gmaps_pro \
     -p 5432:5432 \
     postgres:15
   ```

2. **Generate an encryption key**:
   ```bash
   # On Windows (PowerShell)
   $key = -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })
   echo $key
   
   # On Linux/Mac
   openssl rand -hex 32
   ```
   
   Copy the generated key (64 hex characters).

3. **Create a .env file** in the project root:
   ```bash
   # Windows PowerShell
   @"
   DATABASE_URL=postgres://postgres:postgres@localhost:5432/gmaps_pro?sslmode=disable
   ENCRYPTION_KEY=your_generated_key_here
   ADDR=:8080
   "@ | Out-File -FilePath .env -Encoding utf8
   ```

4. **Run database migrations**:
   ```bash
   # Install migrate tool first (if not installed)
   go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest
   
   # Run migrations
   migrate -path migrations -database "postgres://postgres:postgres@localhost:5432/gmaps_pro?sslmode=disable" up
   ```

5. **Create an admin user**:
   ```bash
   go run cmd/gmapssaas/main.go admin create-user \
     --database-url "postgres://postgres:postgres@localhost:5432/gmaps_pro?sslmode=disable" \
     --encryption-key "your_generated_key_here" \
     --username admin \
     --password "1234#abcd"
   ```

6. **Start the backend server**:
   ```bash
   go run cmd/gmapssaas/main.go serve \
     --database-url "postgres://postgres:postgres@localhost:5432/gmaps_pro?sslmode=disable" \
     --encryption-key "your_generated_key_here" \
     --addr ":8080"
   ```

7. **Follow steps 2-6 from Option 1** to set up the frontend.

---

## Troubleshooting

### Backend won't start
- **Error: "Required flag encryption-key not set"**
  - Generate a key: `openssl rand -hex 32` (Linux/Mac) or use PowerShell command above
  - Pass it with `--encryption-key` flag or set `ENCRYPTION_KEY` environment variable

- **Error: "connection refused" to PostgreSQL**
  - Ensure PostgreSQL is running: `docker ps` (should see postgres container)
  - Check connection string matches your PostgreSQL setup

### Frontend can't connect to backend
- Ensure backend is running on `http://localhost:8080`
- Check browser console for errors
- Verify API key is correct
- Check that CORS is enabled (it should be by default)

### Port already in use
- Backend (8080): Change with `--addr ":8081"` flag
- Frontend (5173): Change in `frontend/vite.config.ts`

---

## What's Next?

Once everything is running:

1. **Create your first scraping job** from the frontend
2. **Monitor job progress** on the Dashboard (auto-refreshes every 5 seconds)
3. **View and download results** when the job completes
4. **Explore the admin dashboard** at `http://localhost:8080/admin` for advanced features

## Production Deployment

For production deployment, see:
- `docs/saas.md` - Full deployment guide with Docker
- Use the provision script for automated cloud deployment
