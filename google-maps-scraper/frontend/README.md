# Google Maps Scraper - Frontend

A modern React + TypeScript frontend for the Google Maps Scraper backend API.

## Features

- 🎯 **Job Management**: Create, monitor, and manage scraping jobs
- 📊 **Real-time Updates**: Auto-refresh job status every 5 seconds
- 📥 **Results Download**: Export results as JSON
- 🔑 **API Key Management**: Secure API authentication
- 🎨 **Modern UI**: Built with Tailwind CSS
- ⚡ **Fast Development**: Vite for instant HMR

## Prerequisites

- Node.js 18+ or npm/yarn
- Google Maps Scraper backend running on `http://localhost:8080`

## Installation

```bash
# Install dependencies
npm install

# or with yarn
yarn install
```

## Development

```bash
# Start development server
npm run dev

# The app will be available at http://localhost:3000
```

The development server includes a proxy configuration that forwards `/api` requests to `http://localhost:8080`.

## Building for Production

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── lib/
│   │   └── api.ts          # API client and types
│   ├── pages/
│   │   ├── Dashboard.tsx   # Jobs list page
│   │   ├── NewJob.tsx      # Create new job form
│   │   ├── JobDetails.tsx  # Job details and results
│   │   └── ApiSettings.tsx # API key configuration
│   ├── App.tsx             # Main app component with routing
│   ├── main.tsx            # App entry point
│   └── index.css           # Global styles
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## Usage

### 1. Configure API Key

1. Navigate to **Settings** page
2. Enter your API key (generate one from the backend admin dashboard)
3. Click **Save API Key**

### 2. Create a Scraping Job

1. Click **New Job** in the navigation
2. Fill in the form:
   - **Keyword**: Search query (e.g., "restaurants in New York")
   - **Language**: Select language for results
   - **Max Depth**: How many times to scroll (1-100)
   - **Geo Coordinates**: Optional location (lat,lon format)
   - **Options**: Email extraction, extra reviews, fast mode
3. Click **Submit Job**

### 3. Monitor Jobs

- View all jobs on the **Dashboard**
- Filter by status (pending, running, completed, failed)
- Auto-refresh every 5 seconds
- Click on a job to view details

### 4. View Results

- Click the eye icon on any completed job
- View results in a table format
- Download full results as JSON

## API Integration

The frontend connects to the backend REST API:

- **Base URL**: `http://localhost:8080/api/v1`
- **Authentication**: API key via `X-API-Key` header
- **Endpoints**:
  - `POST /scrape` - Submit job
  - `GET /jobs` - List jobs
  - `GET /jobs/:id` - Get job details
  - `DELETE /jobs/:id` - Delete job

## Configuration

### Backend URL

To change the backend URL, edit `vite.config.ts`:

```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://your-backend-url:8080',
        changeOrigin: true,
      }
    }
  }
})
```

### Port

To change the frontend port, edit `vite.config.ts`:

```typescript
export default defineConfig({
  server: {
    port: 3000, // Change this
  }
})
```

## Technologies

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **Tailwind CSS** - Utility-first CSS
- **Lucide React** - Icon library
- **date-fns** - Date formatting

## Troubleshooting

### API Connection Issues

If you see connection errors:

1. Ensure the backend is running on `http://localhost:8080`
2. Check that your API key is correct
3. Verify CORS is enabled on the backend
4. Check browser console for detailed errors

### Build Errors

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
```

## License

MIT License - Same as the backend project
