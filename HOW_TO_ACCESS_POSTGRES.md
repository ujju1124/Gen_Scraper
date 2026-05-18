# 🗄️ How to Access PostgreSQL Database

## Understanding the Setup

### What PostgreSQL Service Is Used?

**PostgreSQL 15** running inside a **Docker container** (not installed on your machine).

### Credentials (from `.env` file):
```
Database Name: scraper_db
Username: scraper
Password: scraper_pass
Port: 5433 (on your machine) → 5432 (inside container)
```

### How It Was Created:

1. **Docker Compose** automatically:
   - Downloaded PostgreSQL 15 image
   - Created a container named `gen_scraper-postgres-1`
   - Set up the database with credentials from `.env`
   - Created a persistent volume `postgres_data` to store data

2. **Alembic Migrations** automatically:
   - Created all tables (users, categories, sources, jobs, results, etc.)
   - Set up relationships and indexes

3. **Seed Script** automatically:
   - Added 30 categories
   - Added 32 sources
   - Created admin user

4. **Scrapers** automatically:
   - Collected 4,790 business records
   - Stored in `cleaned_results` table

---

## 🔍 How to View Your Data

### Method 1: Using pgAdmin (GUI - Recommended)

#### Step 1: Download pgAdmin
- Download from: https://www.pgadmin.org/download/
- Install pgAdmin 4

#### Step 2: Connect to Database
1. Open pgAdmin
2. Right-click "Servers" → "Register" → "Server"
3. **General Tab**:
   - Name: `Gen_Scraper`
4. **Connection Tab**:
   - Host: `localhost`
   - Port: `5433` ⚠️ (not 5432!)
   - Database: `scraper_db`
   - Username: `scraper`
   - Password: `scraper_pass`
5. Click "Save"

#### Step 3: Browse Data
1. Expand: Servers → Gen_Scraper → Databases → scraper_db → Schemas → public → Tables
2. Right-click `cleaned_results` → "View/Edit Data" → "All Rows"
3. You'll see all 4,790 records!

---

### Method 2: Using Command Line (Quick)

#### View All Records:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT * FROM cleaned_results LIMIT 10;"
```

#### Count Records:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) FROM cleaned_results;"
```

#### View by City:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT city, COUNT(*) FROM cleaned_results GROUP BY city ORDER BY COUNT(*) DESC;"
```

#### View by Category:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT c.name, COUNT(*) FROM cleaned_results cr JOIN categories c ON cr.category_id = c.id GROUP BY c.name ORDER BY COUNT(*) DESC;"
```

#### View Specific Business:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT name, address, phone, city FROM cleaned_results WHERE city='Kathmandu' LIMIT 5;"
```

---

### Method 3: Using DBeaver (GUI - Alternative)

#### Step 1: Download DBeaver
- Download from: https://dbeaver.io/download/
- Install DBeaver Community Edition

#### Step 2: Connect
1. Click "New Database Connection"
2. Select "PostgreSQL"
3. Enter:
   - Host: `localhost`
   - Port: `5433`
   - Database: `scraper_db`
   - Username: `scraper`
   - Password: `scraper_pass`
4. Test Connection → Finish

#### Step 3: Browse
1. Expand: scraper_db → Schemas → public → Tables
2. Double-click `cleaned_results`
3. Click "Data" tab to see all records

---

### Method 4: Using psql Interactive Shell

#### Enter PostgreSQL Shell:
```powershell
docker exec -it gen_scraper-postgres-1 psql -U scraper -d scraper_db
```

#### Once Inside, Run SQL:
```sql
-- See all tables
\dt

-- Count records
SELECT COUNT(*) FROM cleaned_results;

-- View sample data
SELECT * FROM cleaned_results LIMIT 5;

-- View by city
SELECT city, COUNT(*) FROM cleaned_results GROUP BY city;

-- Exit
\q
```

---

## 📊 Database Schema

### Main Tables:

1. **cleaned_results** (4,790 records)
   - Your business data
   - Columns: id, name, address, phone, email, website, city, latitude, longitude, category_id, source_id, etc.

2. **categories** (30 records)
   - Hotels, Restaurants, Clinics, etc.

3. **sources** (32 records)
   - Google Maps, Booking.com, Agoda, etc.

4. **scrape_jobs** (214 records)
   - Job history (55 done, 158 cancelled, 1 running)

5. **users** (1 record)
   - Admin user

6. **raw_results** (scraped data before cleaning)

7. **validated_results** (validated data)

8. **geocoding_cache** (cached coordinates)

---

## 💾 Export Your Data

### Export to CSV:
```powershell
# Export all data
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "\COPY (SELECT * FROM cleaned_results) TO '/tmp/export.csv' WITH CSV HEADER;"

# Copy to your machine
docker cp gen_scraper-postgres-1:/tmp/export.csv ./my_data.csv
```

### Export to JSON:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -t -c "SELECT json_agg(row_to_json(cleaned_results)) FROM cleaned_results;" > my_data.json
```

### Export Specific City:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "\COPY (SELECT * FROM cleaned_results WHERE city='Kathmandu') TO '/tmp/kathmandu.csv' WITH CSV HEADER;"
docker cp gen_scraper-postgres-1:/tmp/kathmandu.csv ./kathmandu.csv
```

---

## 🔒 Security Notes

### Current Setup (Development):
- ⚠️ Simple password: `scraper_pass`
- ⚠️ Exposed port: 5433
- ⚠️ No SSL

### For Production:
- ✅ Use strong password
- ✅ Don't expose port publicly
- ✅ Enable SSL
- ✅ Use environment variables
- ✅ Restrict network access

---

## 📍 Where Is Data Stored?

### Docker Volume:
- **Volume Name**: `postgres_data`
- **Location**: Managed by Docker (usually in Docker's data directory)
- **Persistence**: Data survives container restarts
- **Size**: ~500MB (with 4,790 records)

### View Volume:
```powershell
docker volume inspect postgres_data
```

### Backup Volume:
```powershell
# Backup database
docker exec gen_scraper-postgres-1 pg_dump -U scraper scraper_db > backup.sql

# Restore database
docker exec -i gen_scraper-postgres-1 psql -U scraper -d scraper_db < backup.sql
```

---

## 🔄 Common Operations

### View All Tables:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "\dt"
```

### View Table Structure:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "\d cleaned_results"
```

### Count Records in All Tables:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "
SELECT 
  'cleaned_results' as table_name, COUNT(*) FROM cleaned_results
UNION ALL
SELECT 'categories', COUNT(*) FROM categories
UNION ALL
SELECT 'sources', COUNT(*) FROM sources
UNION ALL
SELECT 'scrape_jobs', COUNT(*) FROM scrape_jobs
UNION ALL
SELECT 'users', COUNT(*) FROM users;
"
```

### Search for Specific Business:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT name, address, phone FROM cleaned_results WHERE name ILIKE '%hotel%' LIMIT 10;"
```

---

## ❓ FAQ

### Q: Do I need PostgreSQL installed on my machine?
**A**: No! It runs inside Docker. You don't need to install PostgreSQL separately.

### Q: Will my data be lost if I stop Docker?
**A**: No! Data is stored in a Docker volume (`postgres_data`) which persists even when containers stop.

### Q: Can I access this database from other tools?
**A**: Yes! Use any PostgreSQL client (pgAdmin, DBeaver, DataGrip, etc.) with:
- Host: `localhost`
- Port: `5433`
- Database: `scraper_db`
- User: `scraper`
- Password: `scraper_pass`

### Q: How do I delete all data?
**A**: 
```powershell
# Delete all records (keeps tables)
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "TRUNCATE cleaned_results CASCADE;"

# Or delete entire volume (removes everything)
docker-compose down -v
```

### Q: Can I use my own PostgreSQL server?
**A**: Yes! Update `.env`:
```
DATABASE_URL=postgresql://your_user:your_pass@your_host:5432/your_db
```

### Q: How do I see what's happening in real-time?
**A**: Watch logs:
```powershell
docker-compose logs -f postgres
```

---

## 🎯 Quick Reference

### Connection Details:
```
Host: localhost
Port: 5433
Database: scraper_db
Username: scraper
Password: scraper_pass
```

### Quick Commands:
```powershell
# View data
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT * FROM cleaned_results LIMIT 10;"

# Count records
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) FROM cleaned_results;"

# Export to CSV
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "\COPY (SELECT * FROM cleaned_results) TO '/tmp/export.csv' WITH CSV HEADER;"
docker cp gen_scraper-postgres-1:/tmp/export.csv ./my_data.csv

# Backup
docker exec gen_scraper-postgres-1 pg_dump -U scraper scraper_db > backup.sql
```

---

## 🚀 Try It Now!

### Step 1: Check if PostgreSQL is running:
```powershell
docker ps | findstr postgres
```

### Step 2: Count your records:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) FROM cleaned_results;"
```

### Step 3: View sample data:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT name, city, phone FROM cleaned_results LIMIT 5;"
```

**You should see your 4,790 business records!** 🎉

---

**Need help?** Just ask! I can help you query or export your data in any format you need.
