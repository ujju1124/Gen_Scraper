# Docker Explained - For Complete Beginners

This document explains **what Docker is** and **how we use it** in this project. Written assuming you have zero knowledge about Docker.

---

## Table of Contents

1. [What is Docker?](#what-is-docker)
2. [Why Do We Need Docker?](#why-do-we-need-docker)
3. [Docker Concepts Explained](#docker-concepts-explained)
4. [How We Use Docker in This Project](#how-we-use-docker-in-this-project)
5. [Docker Commands Explained](#docker-commands-explained)
6. [Troubleshooting](#troubleshooting)

---

## What is Docker?

### The Simple Explanation

**Docker is like a shipping container for software.**

Imagine you're moving to a new house. You could:
- **Option A**: Carry each item individually (tedious, things might break)
- **Option B**: Pack everything in a container (organized, protected, easy to move)

Docker does Option B for software.

### The Technical Explanation

Docker is a tool that packages software and everything it needs to run (code, libraries, settings) into a **container**. This container can run on any computer that has Docker installed, and it will work exactly the same way.

### Real-World Analogy

Think of Docker like a **food delivery box**:

```
┌─────────────────────────────────────┐
│  Food Delivery Box (Docker)         │
│  ┌───────────────────────────────┐  │
│  │ Meal (Your Application)       │  │
│  │ - Main dish (Code)            │  │
│  │ - Utensils (Dependencies)     │  │
│  │ - Instructions (Config)       │  │
│  └───────────────────────────────┘  │
│                                     │
│  Everything you need in one box!    │
└─────────────────────────────────────┘
```

No matter where you open this box (your house, office, friend's place), you have everything you need to eat the meal.

Similarly, a Docker container has everything your application needs to run, no matter which computer it's on.

---

## Why Do We Need Docker?

### The Problem Docker Solves

**"It works on my computer!"** - Every developer ever

Here's a common scenario:

1. **Developer A** writes code on their laptop (Windows)
   - Has PostgreSQL version 15 installed
   - Has Go version 1.21
   - Everything works perfectly

2. **Developer B** tries to run the same code (Mac)
   - Has PostgreSQL version 14 installed
   - Has Go version 1.20
   - **Code doesn't work!** 😱

3. **Production server** (Linux)
   - Different versions of everything
   - **Code breaks again!** 😱😱

### How Docker Fixes This

With Docker:

1. **Developer A** creates a Docker container
   - Specifies: "Use PostgreSQL 15, Go 1.21"
   - Packages everything together

2. **Developer B** runs the same container
   - Gets exact same PostgreSQL 15, Go 1.21
   - **Works perfectly!** ✅

3. **Production server** runs the same container
   - Gets exact same environment
   - **Works perfectly!** ✅

**Key benefit**: "If it works in Docker on your laptop, it will work in Docker anywhere."

---

## Docker Concepts Explained

### 1. Docker Image

**What it is**: A blueprint or recipe for creating a container

**Analogy**: Like a recipe for baking a cake
- Lists all ingredients (dependencies)
- Specifies steps to make it (instructions)
- Can be shared with others

**Example**: `postgres:18-alpine`
- This is an image for PostgreSQL version 18
- `alpine` means it's a lightweight version

**In our project**: We use the `postgres:18-alpine` image to run our database.

---

### 2. Docker Container

**What it is**: A running instance of an image

**Analogy**: The actual cake you baked from the recipe
- The recipe (image) can make many cakes (containers)
- Each cake is independent
- You can eat one without affecting others

**Example**: When you run `docker compose up`, it creates a container from the PostgreSQL image.

**In our project**: We have a PostgreSQL container running that stores all our job data.

---

### 3. Docker Volume

**What it is**: Persistent storage for containers

**The Problem**: Containers are temporary. If you delete a container, all data inside is lost!

**The Solution**: Volumes are like external hard drives
- Data is stored outside the container
- Even if container is deleted, data remains
- Can be attached to new containers

**Analogy**: 
- Container = Laptop (temporary)
- Volume = External hard drive (permanent)
- You can replace the laptop, but your files on the hard drive remain

**In our project**: We use a volume called `saas_pgdata` to store PostgreSQL data permanently.

```yaml
volumes:
  saas_pgdata:  # This is our "external hard drive"
```

---

### 4. Docker Compose

**What it is**: A tool to run multiple containers together

**Why we need it**: Most applications need multiple services
- Our app needs: PostgreSQL database
- Maybe later: Redis cache, Nginx web server, etc.

**Analogy**: Like a restaurant kitchen
- One chef (container) makes pasta
- Another chef (container) makes desserts
- Docker Compose is the head chef coordinating everyone

**In our project**: `docker-compose.saas.yaml` defines our PostgreSQL container.

---

### 5. Docker Network

**What it is**: Allows containers to talk to each other

**Analogy**: Like a phone network
- Each container has a "phone number" (IP address)
- They can call each other
- Isolated from the outside world (secure)

**In our project**: Our backend can connect to PostgreSQL using `localhost:5432` because they're on the same Docker network.

---

## How We Use Docker in This Project

### What We're Running in Docker

In this project, we only run **PostgreSQL** in Docker. Everything else runs directly on your computer:

```
┌─────────────────────────────────────────┐
│  Your Computer                          │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Docker Container               │   │
│  │  ┌───────────────────────────┐  │   │
│  │  │  PostgreSQL Database      │  │   │
│  │  │  - Port: 5432             │  │   │
│  │  │  - User: postgres         │  │   │
│  │  │  - Password: postgres     │  │   │
│  │  │  - Database: gmapssaas    │  │   │
│  │  └───────────────────────────┘  │   │
│  └─────────────────────────────────┘   │
│                                         │
│  Running Directly (Not in Docker):     │
│  - Backend Server (Go)                 │
│  - Worker Process (Go)                 │
│  - Frontend (React)                    │
└─────────────────────────────────────────┘
```

### Why Only PostgreSQL in Docker?

**Advantages**:
1. **Easy setup**: No need to install PostgreSQL manually
2. **Consistent**: Everyone gets the same PostgreSQL version
3. **Isolated**: Won't conflict with other PostgreSQL installations
4. **Easy cleanup**: Delete container = PostgreSQL is gone

**Why not everything in Docker?**
- Easier to develop and debug when running directly
- Faster to restart and test changes
- Can use your local Go and Node.js installations

---

### The Docker Compose File

Let's break down `docker-compose.saas.yaml`:

```yaml
services:
  postgres:                          # Name of our service
    image: postgres:18-alpine        # Use PostgreSQL 18 (lightweight version)
    environment:                     # Configuration settings
      POSTGRES_USER: postgres        # Username: postgres
      POSTGRES_PASSWORD: postgres    # Password: postgres
      POSTGRES_DB: gmapssaas         # Database name: gmapssaas
    ports:
      - "5432:5432"                  # Expose port 5432 to your computer
    volumes:
      - saas_pgdata:/var/lib/postgresql/data  # Store data permanently
    healthcheck:                     # Check if PostgreSQL is ready
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s                   # Check every 5 seconds
      timeout: 5s
      retries: 5

volumes:
  saas_pgdata:                       # Define the volume for data storage
```

**What each part means**:

1. **`image: postgres:18-alpine`**
   - Download PostgreSQL version 18
   - `alpine` = small, lightweight version

2. **`environment`**
   - Sets up username, password, and database name
   - Like filling out a registration form

3. **`ports: "5432:5432"`**
   - Makes PostgreSQL accessible on port 5432
   - Format: `host_port:container_port`
   - Your computer's port 5432 → Container's port 5432

4. **`volumes`**
   - Saves data to `saas_pgdata` volume
   - Data survives even if container is deleted

5. **`healthcheck`**
   - Checks if PostgreSQL is ready to accept connections
   - Runs `pg_isready` command every 5 seconds

---

## Docker Commands Explained

### Starting PostgreSQL

```bash
docker compose -f docker-compose.saas.yaml up -d postgres
```

**Breaking it down**:
- `docker compose`: Use Docker Compose tool
- `-f docker-compose.saas.yaml`: Use this specific file
- `up`: Start the services
- `-d`: Run in background (detached mode)
- `postgres`: Only start the postgres service

**What happens**:
1. Docker reads `docker-compose.saas.yaml`
2. Downloads `postgres:18-alpine` image (if not already downloaded)
3. Creates a container named `google-maps-scraper-copy-postgres-1`
4. Starts PostgreSQL inside the container
5. Returns control to you (because of `-d`)

**Output you'll see**:
```
[+] Running 2/2
✔ Network google-maps-scraper-copy_default      Created
✔ Container google-maps-scraper-copy-postgres-1 Started
```

---

### Stopping PostgreSQL

```bash
docker compose -f docker-compose.saas.yaml down
```

**What happens**:
1. Stops the PostgreSQL container
2. Removes the container
3. Removes the network
4. **Data is NOT deleted** (it's in the volume)

**Output**:
```
[+] Running 2/2
✔ Container google-maps-scraper-copy-postgres-1 Removed
✔ Network google-maps-scraper-copy_default      Removed
```

---

### Checking Running Containers

```bash
docker ps
```

**What it shows**: List of all running containers

**Example output**:
```
CONTAINER ID   IMAGE                  STATUS         PORTS                    NAMES
a1b2c3d4e5f6   postgres:18-alpine     Up 5 minutes   0.0.0.0:5432->5432/tcp   google-maps-scraper-copy-postgres-1
```

**What each column means**:
- **CONTAINER ID**: Unique identifier (like a serial number)
- **IMAGE**: Which image was used
- **STATUS**: How long it's been running
- **PORTS**: Which ports are exposed
- **NAMES**: Container name

---

### Viewing Container Logs

```bash
docker logs google-maps-scraper-copy-postgres-1
```

**What it shows**: Everything PostgreSQL has printed (logs, errors, etc.)

**Example output**:
```
PostgreSQL init process complete; ready for start up.

2026-04-13 17:00:52.654 UTC [1] LOG:  starting PostgreSQL 18.0
2026-04-13 17:00:52.661 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
2026-04-13 17:00:52.662 UTC [1] LOG:  database system is ready to accept connections
```

**Useful for**: Debugging if PostgreSQL isn't working

---

### Executing Commands Inside Container

```bash
docker exec -it google-maps-scraper-copy-postgres-1 psql -U postgres
```

**Breaking it down**:
- `docker exec`: Run a command inside a container
- `-it`: Interactive mode (you can type commands)
- `google-maps-scraper-copy-postgres-1`: Container name
- `psql -U postgres`: Command to run (PostgreSQL client)

**What happens**: Opens a PostgreSQL command prompt inside the container

**Example session**:
```sql
postgres=# \l                          -- List databases
postgres=# \c gmapssaas                -- Connect to gmapssaas database
gmapssaas=# SELECT * FROM jobs;       -- Query jobs table
gmapssaas=# \q                         -- Quit
```

---

### Removing Everything (Including Data)

```bash
docker compose -f docker-compose.saas.yaml down -v
```

**What happens**:
1. Stops containers
2. Removes containers
3. Removes networks
4. **Removes volumes** (deletes all data!)

**⚠️ WARNING**: This deletes all your scraped data! Only use when you want to start fresh.

---

### Checking Disk Usage

```bash
docker system df
```

**What it shows**: How much disk space Docker is using

**Example output**:
```
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          5         1         2.5GB     2GB (80%)
Containers      1         1         100MB     0B (0%)
Local Volumes   1         1         500MB     0B (0%)
```

---

## Common Docker Scenarios

### Scenario 1: PostgreSQL Won't Start

**Problem**: Container keeps restarting

**Check logs**:
```bash
docker logs google-maps-scraper-copy-postgres-1
```

**Common causes**:
1. Port 5432 already in use
   - **Solution**: Stop other PostgreSQL instances
   - Check: `netstat -an | findstr 5432` (Windows)

2. Corrupted data
   - **Solution**: Remove volume and start fresh
   ```bash
   docker compose -f docker-compose.saas.yaml down -v
   docker compose -f docker-compose.saas.yaml up -d postgres
   ```

---

### Scenario 2: Can't Connect to PostgreSQL

**Problem**: Backend says "connection refused"

**Check if container is running**:
```bash
docker ps
```

**Check if PostgreSQL is ready**:
```bash
docker exec google-maps-scraper-copy-postgres-1 pg_isready -U postgres
```

**Expected output**: `postgres:5432 - accepting connections`

**If not ready**: Wait a few seconds and try again

---

### Scenario 3: Out of Disk Space

**Problem**: Docker says "no space left on device"

**Check usage**:
```bash
docker system df
```

**Clean up unused data**:
```bash
docker system prune -a
```

**What it removes**:
- Stopped containers
- Unused images
- Unused networks
- Build cache

**⚠️ WARNING**: This will remove ALL unused Docker data, not just this project!

---

## Docker vs. Traditional Installation

### Traditional Way (Without Docker)

**To install PostgreSQL**:
1. Download installer for your OS
2. Run installer
3. Configure settings
4. Set up user accounts
5. Create database
6. Hope it doesn't conflict with existing installations

**Problems**:
- Different steps for Windows/Mac/Linux
- Might conflict with other PostgreSQL versions
- Hard to uninstall completely
- Settings might differ between computers

---

### Docker Way

**To install PostgreSQL**:
1. Run: `docker compose up -d postgres`

**That's it!** ✅

**Advantages**:
- Same command on all operating systems
- Isolated from other installations
- Easy to remove: `docker compose down -v`
- Guaranteed same version everywhere

---

## How Docker Fits in Our Project

### The Full Picture

```
┌─────────────────────────────────────────────────────────┐
│  Your Computer (Windows)                                │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │  Docker Desktop                                 │   │
│  │                                                 │   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │  Container: postgres                     │  │   │
│  │  │  - Image: postgres:18-alpine             │  │   │
│  │  │  - Port: 5432                            │  │   │
│  │  │  - Volume: saas_pgdata                   │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────┘   │
│                          ▲                             │
│                          │ Port 5432                   │
│                          │                             │
│  ┌───────────────────────┴──────────────────────────┐ │
│  │  Backend Server (Go)                             │ │
│  │  - Connects to: localhost:5432                   │ │
│  │  - Database: gmapssaas                           │ │
│  │  - User: postgres                                │ │
│  └──────────────────────────────────────────────────┘ │
│                          ▲                             │
│                          │ HTTP (Port 8080)            │
│                          │                             │
│  ┌───────────────────────┴──────────────────────────┐ │
│  │  Frontend (React)                                │ │
│  │  - Runs on: localhost:3000                       │ │
│  │  - Calls API: localhost:8080                     │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Frontend** (React) sends job request to **Backend** (Go)
2. **Backend** saves job to **PostgreSQL** (in Docker)
3. **Worker** (Go) reads job from **PostgreSQL** (in Docker)
4. **Worker** scrapes Google Maps
5. **Worker** saves results to **PostgreSQL** (in Docker)
6. **Frontend** fetches results from **Backend**
7. **Backend** reads results from **PostgreSQL** (in Docker)
8. **Frontend** displays results to you

**Key point**: Only PostgreSQL runs in Docker. Everything else runs normally on your computer.

---

## Summary

### What is Docker?
A tool that packages software in containers that run the same way everywhere.

### Why do we use it?
To run PostgreSQL easily without manual installation and configuration.

### What's in our Docker setup?
- **1 container**: PostgreSQL database
- **1 volume**: Persistent storage for database data
- **1 network**: Allows backend to connect to PostgreSQL

### Key commands:
```bash
# Start PostgreSQL
docker compose -f docker-compose.saas.yaml up -d postgres

# Stop PostgreSQL
docker compose -f docker-compose.saas.yaml down

# View logs
docker logs google-maps-scraper-copy-postgres-1

# Check if running
docker ps

# Remove everything including data
docker compose -f docker-compose.saas.yaml down -v
```

### Remember:
- Containers are temporary (can be deleted and recreated)
- Volumes are permanent (data survives container deletion)
- Our backend connects to PostgreSQL at `localhost:5432`
- Database name: `gmapssaas`, User: `postgres`, Password: `postgres`

That's Docker in a nutshell! 🐳
