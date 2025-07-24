# 🚀 Giswater Hydraulic Engine API

A FastAPI application for managing INP files for hydraulic modeling with EPANET. This API provides endpoints for uploading and retrieving INP files, with PostgreSQL database storage for metadata. Built using FastAPI with SQLModel for robust data management.

## 📂 Project Structure

```
giswater-hengine-app/
├── src/
│   └── api/
│       ├── main.py          # FastAPI application entry point
│       ├── routes.py        # API endpoints for INP file management
│       ├── models.py        # Pydantic models for data validation
│       ├── database.py      # SQLModel database models and connection
│       └── __init__.py
├── uploads/                 # Directory for uploaded INP files (auto-created)
├── pg_service.conf.template # PostgreSQL service configuration template
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup with PostgreSQL
├── start.sh                # Shell script to start the application
└── README.md               # This file
```

## 🗄️ Database

This application uses **PostgreSQL** with **SQLModel** and **pgservice** for database connection management:

- **Database**: PostgreSQL 15
- **ORM**: SQLModel (built on SQLAlchemy)
- **Connection**: PostgreSQL service files (pgservice)
- **Schemas**: Configurable schemas for WS, UD, and AUDIT data
- **Features**: Automatic table creation, connection pooling, session management

### Database Connection Architecture

The application uses PostgreSQL service files (pgservice) for database configuration:

- **pg_service.conf.template**: Template file with connection parameters
- **Runtime Configuration**: Template is processed to create `/etc/postgresql-common/pg_service.conf`
- **Connection String**: `postgresql:///?service={PGSERVICE}`
- **Schema Support**: Multiple schemas (WS, UD, AUDIT) for data organization

## 🚀 Quick Start

### 1️⃣ **Environment Configuration**

Copy the environment template and configure your settings:

```bash
cd api-server/giswater-hengine-app
cp .env.example .env
```

Edit `.env` file with your configuration:

```bash
# PostgreSQL Database Configuration
POSTGRES_PASSWORD=your_secure_password_here
```

### 2️⃣ **Set Up Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3️⃣ **Database Setup & Run**

**Option A: Using Docker Compose (Recommended)**
```bash
# Create network and start all services
./start.sh

# Or manually:
docker network create --subnet=172.21.1.0/24 api-network-2
docker-compose up --build
```

**Option B: Local PostgreSQL with pgservice**
```bash
# Install PostgreSQL and create database
createdb giswater_hengine

# Configure pgservice
sudo mkdir -p /etc/postgresql-common
envsubst < pg_service.conf.template | sudo tee /etc/postgresql-common/pg_service.conf

# Run application
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

📌 API Docs available at: [**http://127.0.0.1:8000/docs**](http://127.0.0.1:8000/docs)

---

## 🐳 Running with Docker

### **Complete Setup with Docker Compose**

```bash
# Make sure you have a .env file configured
cp .env.example .env
# Edit .env with your settings

# Use the start script (creates network automatically)
./start.sh
```

### **Individual Docker Commands**

```bash
# Build the application
docker build -t giswater-hengine-app .

# Run with external PostgreSQL
docker run -d -p 8000:8000 \
  -e PGSERVICE=giswater_hengine \
  -e POSTGRES_PASSWORD=your_password \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/pg_service.conf.template:/tmp/pg_service.conf.template:ro \
  giswater-hengine-app
```

---

## 🛠️ API Endpoints

| Endpoint              | Method | Description                                    |
|-----------------------|--------|-----------------------------------------------|
| `/`                   | GET    | Root endpoint - API information               |
| `/health`             | GET    | Health check endpoint                         |
| `/inp/upload`         | POST   | Upload an INP file (multipart/form-data)     |
| `/inp/files`          | GET    | Get all uploaded INP files with metadata     |
| `/inp/files/{file_id}`| GET    | Get specific INP file metadata by ID         |
| `/inp/files/{file_id}`| DELETE | Delete an INP file and its metadata          |

### 📤 Upload INP File

**POST** `/inp/upload`

Upload an INP file for hydraulic modeling. Metadata is stored in PostgreSQL database.

**Request:**
- Content-Type: `multipart/form-data`
- Body: File upload with key `file`

**Response:**
```json
{
  "status": "Accepted",
  "message": "File uploaded successfully",
  "filename": "model.inp",
  "file_id": "uuid-here",
  "upload_time": "2024-01-01T12:00:00",
  "file_size": 1024
}
```

### 📥 Get All INP Files

**GET** `/inp/files`

Retrieve information about all uploaded INP files from database.

**Response:**
```json
{
  "status": "Accepted",
  "message": "Retrieved INP files successfully",
  "total_files": 2,
  "files": [
    {
      "file_id": "uuid-1",
      "filename": "model1.inp",
      "upload_time": "2024-01-01T12:00:00",
      "file_size": 1024,
      "file_path": "uploads/uuid-1_model1.inp"
    }
  ]
}
```

### 📄 Get Specific File

**GET** `/inp/files/{file_id}`

Get metadata for a specific INP file by its unique ID.

### 🗑️ Delete File

**DELETE** `/inp/files/{file_id}`

Delete an INP file from both disk storage and database.

---

## 🔧 Configuration

### Environment Variables

The application uses a `.env` file for configuration:

```bash
# Database Configuration
POSTGRES_PASSWORD=your_secure_password  # Required: PostgreSQL password
```

### PostgreSQL Service Configuration

The `pg_service.conf.template` defines database connection parameters:

```ini
[giswater_hengine]
host=postgres
port=5432
dbname=giswater_hengine
user=postgres
password=${POSTGRES_PASSWORD}
```

**Note**: The template is processed at runtime to substitute environment variables.

### File Upload Limits
- **Allowed Extensions:** `.inp` only
- **Maximum File Size:** 250MB
- **Upload Directory:** `uploads/` (auto-created)

### Docker Networking
- **API Container**: 172.21.1.51:8000
- **PostgreSQL Container**: 172.21.1.52:5432
- **Network**: `api-network-2` (auto-created by start.sh)

---

## 🧪 Testing the API

### Using the Interactive API Documentation
1. Start the server: `./start.sh`
2. Navigate to `http://localhost:8000/docs`
3. Use the built-in Swagger UI to test endpoints

### Using curl

**Check API Status:**
```bash
curl http://localhost:8000/
```

**Upload a file:**
```bash
curl -X POST "http://localhost:8000/inp/upload" \
  -F "file=@example.inp"
```

**Get all files:**
```bash
curl http://localhost:8000/inp/files
```

**Get specific file:**
```bash
curl http://localhost:8000/inp/files/{file_id}
```

**Delete a file:**
```bash
curl -X DELETE http://localhost:8000/inp/files/{file_id}
```

---

## 🏗️ Technology Stack

- **Framework:** FastAPI 0.115.7
- **Database:** PostgreSQL 15
- **ORM:** SQLModel 0.0.16
- **Database Driver:** psycopg2-binary 2.9.10
- **Migration Tool:** Alembic 1.13.3
- **Validation:** Pydantic 2.10.6
- **Server:** Uvicorn 0.34.0
- **Connection Management:** PostgreSQL service files (pgservice)

## 🗄️ Database Schema Architecture

The application supports multiple schemas for data organization:

```sql
-- Schemas created automatically
CREATE SCHEMA IF NOT EXISTS ws_42;    -- Water supply data
CREATE SCHEMA IF NOT EXISTS ud_42;    -- Urban drainage data
CREATE SCHEMA IF NOT EXISTS audit;    -- Audit trail data

-- Example table structure
CREATE TABLE ws_42.inp_files (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR UNIQUE NOT NULL,
    filename VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    file_size INTEGER NOT NULL,
    upload_time TIMESTAMP NOT NULL
);
```

## 🔄 Database Migrations

For production deployments, you may want to use Alembic for database migrations:

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create a migration
alembic revision --autogenerate -m "Create inp_files table"

# Apply migrations
alembic upgrade head
```

---

## 📁 File Management

- **Storage**: Files stored in `uploads/` directory with UUID prefixes
- **Database**: Metadata stored in PostgreSQL with schema separation
- **Cleanup**: Automatic cleanup of orphaned records when files are missing
- **Concurrency**: Safe concurrent access with database sessions

---

## 🔗 Integration with Giswater

This API follows similar patterns to the main giswater-api:
- **pgservice Configuration**: Consistent database connection management
- **Schema Structure**: Multi-schema approach for data organization
- **Response Formats**: Consistent `status`, `message`, and data fields
- **Docker Networking**: Compatible networking (API: 172.21.1.51, DB: 172.21.1.52)
- **Environment Management**: `.env` file configuration approach

---

## 🚨 Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps

# Check database logs
docker-compose logs postgres

# Test database connection using pgservice
docker-compose exec giswater-hengine-app psql "service=giswater_hengine" -c "\dt"

# Verify pgservice configuration
docker-compose exec giswater-hengine-app cat /etc/postgresql-common/pg_service.conf
```

### Environment Configuration Issues
```bash
# Check environment variables
docker-compose exec giswater-hengine-app env | grep -E "(POSTGRES|PGSERVICE|SCHEMA)"

# Verify .env file
cat .env

# Test database connection from application
docker-compose exec giswater-hengine-app python src/api/test_db.py
```

### Application Logs
```bash
# View application logs
docker-compose logs giswater-hengine-app

# Follow logs in real-time
docker-compose logs -f giswater-hengine-app
```

### Network Issues
```bash
# Check if network exists
docker network ls | grep api-network-2

# Recreate network if needed
docker network rm api-network-2
./start.sh
```

---

## 📌 License

This project is free software, licensed under the GNU General Public License (GPL) version 3 or later.
