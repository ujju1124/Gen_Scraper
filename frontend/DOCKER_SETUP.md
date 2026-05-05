# Frontend Docker Production Setup

## Overview

The frontend uses a **multi-stage Docker build** to create an optimized production image:

1. **Stage 1 (Builder)**: Builds the React application using Node.js and Vite
2. **Stage 2 (Runtime)**: Serves the static files using Nginx

## Files

### 1. `Dockerfile`
Multi-stage build configuration:
- **Builder stage**: Uses `node:18-alpine` to build the React app
- **Runtime stage**: Uses `nginx:1.25-alpine` to serve static files
- Final image size: ~25MB (compared to ~1GB with Node.js)

### 2. `nginx.conf`
Nginx configuration with:
- **SPA fallback**: All routes serve `index.html` for client-side routing
- **API proxy**: Forwards `/api/*` requests to backend service
- **SSE support**: Disables buffering for Server-Sent Events
- **Static asset caching**: 1-year cache for JS/CSS/images
- **Security headers**: X-Frame-Options, X-Content-Type-Options, etc.
- **Gzip compression**: Reduces bandwidth usage
- **Health check endpoint**: `/health` for container health monitoring

### 3. `.env.production`
Production environment variables:
- `VITE_API_BASE_URL=""` - Empty string uses relative URLs (proxied by nginx)
- `VITE_ENV=production` - Sets environment to production

### 4. `.dockerignore`
Excludes unnecessary files from Docker build context:
- `node_modules` (reinstalled during build)
- Test files and coverage reports
- Development environment files
- Documentation files

## Build Process

### Local Build
```bash
cd frontend
docker build -t web-scraping-portal-frontend:latest .
```

### Docker Compose Build
```bash
# From project root
docker-compose build frontend
```

## Running

### With Docker Compose (Recommended)
```bash
# From project root
docker-compose up frontend
```

Access at: http://localhost:5173

### Standalone Container
```bash
docker run -p 5173:80 \
  --network scraper_network \
  --name frontend \
  web-scraping-portal-frontend:latest
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Container                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    Nginx (Port 80)                      │ │
│  │                                                          │ │
│  │  ┌──────────────┐         ┌──────────────────────────┐ │ │
│  │  │   /health    │         │    Static Files          │ │ │
│  │  │  (health     │         │    /usr/share/nginx/html │ │ │
│  │  │   check)     │         │    - index.html          │ │ │
│  │  └──────────────┘         │    - assets/             │ │ │
│  │                           │    - *.js, *.css         │ │ │
│  │  ┌──────────────┐         └──────────────────────────┘ │ │
│  │  │   /api/*     │                                       │ │
│  │  │  (proxy to   │───────────────────────────────────┐  │ │
│  │  │   backend)   │                                    │  │ │
│  │  └──────────────┘                                    │  │ │
│  │                                                       │  │ │
│  │  ┌──────────────┐                                    │  │ │
│  │  │   /*         │                                    │  │ │
│  │  │  (SPA        │                                    │  │ │
│  │  │   fallback)  │                                    │  │ │
│  │  └──────────────┘                                    │  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ Proxy /api/* requests
                              ▼
                    ┌──────────────────┐
                    │  Backend Service │
                    │  (Port 8000)     │
                    └──────────────────┘
```

## Environment Variables

### Build-time Variables (baked into build)
Set in `.env.production`:
- `VITE_API_BASE_URL` - API base URL (empty for relative URLs)
- `VITE_ENV` - Environment name

### Runtime Variables
Set in `docker-compose.yml`:
- `NGINX_HOST` - Nginx host (default: localhost)
- `NGINX_PORT` - Nginx port (default: 80)

## API Proxy Configuration

The nginx configuration proxies API requests to the backend:

```nginx
location /api/ {
    proxy_pass http://backend:8000;
    # ... proxy headers and SSE settings
}
```

This means:
- Frontend makes requests to `/api/v1/auth/login`
- Nginx forwards to `http://backend:8000/api/v1/auth/login`
- No CORS issues since requests are same-origin

## SPA Routing

All non-API routes serve `index.html`:

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

This enables client-side routing:
- `/dashboard` → serves `index.html` → React Router handles routing
- `/jobs/123` → serves `index.html` → React Router handles routing
- `/admin` → serves `index.html` → React Router handles routing

## Caching Strategy

### Static Assets (1 year)
- JavaScript files: `*.js`
- CSS files: `*.css`
- Images: `*.png`, `*.jpg`, `*.svg`
- Fonts: `*.woff`, `*.woff2`, `*.ttf`

### HTML (no cache)
- `index.html` - Always fetched fresh to get latest app version

## Health Check

Container includes health check:
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1
```

Also accessible via:
```bash
curl http://localhost:5173/health
# Response: healthy
```

## Security Headers

Nginx adds security headers to all responses:
- `X-Frame-Options: SAMEORIGIN` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
- `X-XSS-Protection: 1; mode=block` - XSS protection
- `Referrer-Policy: no-referrer-when-downgrade` - Referrer policy

## Troubleshooting

### Build fails with "npm ci" error
- Delete `node_modules` and `package-lock.json`
- Run `npm install` locally to regenerate lock file
- Rebuild Docker image

### API requests fail with 502 Bad Gateway
- Ensure backend service is running: `docker-compose ps backend`
- Check backend logs: `docker-compose logs backend`
- Verify network connectivity: `docker network inspect scraper_network`

### SPA routing doesn't work (404 on refresh)
- Verify nginx.conf has `try_files $uri $uri/ /index.html;`
- Check nginx logs: `docker-compose logs frontend`

### SSE connection fails
- Verify nginx.conf has `proxy_buffering off;` for `/api/` location
- Check backend SSE endpoint is working
- Inspect browser Network tab for SSE connection

## Production Deployment

For production deployment:

1. **Build optimized image**:
   ```bash
   docker build -t registry.example.com/frontend:v1.0.0 .
   ```

2. **Push to registry**:
   ```bash
   docker push registry.example.com/frontend:v1.0.0
   ```

3. **Deploy with environment-specific config**:
   ```bash
   docker run -p 80:80 \
     -e NGINX_HOST=app.example.com \
     registry.example.com/frontend:v1.0.0
   ```

## Performance

### Build Time
- First build: ~2-3 minutes (downloads dependencies)
- Subsequent builds: ~30-60 seconds (uses Docker cache)

### Image Size
- Builder stage: ~1.2GB (not included in final image)
- Final image: ~25MB (nginx + static files)

### Runtime Performance
- Nginx serves static files with minimal overhead
- Gzip compression reduces bandwidth by ~70%
- Static asset caching reduces server load
- Health checks ensure container availability

## Monitoring

### Container Health
```bash
docker inspect --format='{{.State.Health.Status}}' <container_id>
```

### Nginx Access Logs
```bash
docker-compose logs -f frontend
```

### Resource Usage
```bash
docker stats frontend
```
