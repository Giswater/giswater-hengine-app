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
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup with PostgreSQL
└── README.md               # This file
```

## 🗄️ Database

This application uses **PostgreSQL** with **SQLModel** for storing file metadata:

- **Database**: PostgreSQL 15
- **ORM**: SQLModel (built on SQLAlchemy)
- **Tables**: `inp_files` - stores file metadata (ID, filename, path, size, upload time)
- **Features**: Automatic table creation, connection pooling, session management

### Database Schema

```sql
CREATE TABLE inp_files (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR UNIQUE NOT NULL,
    filename VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    file_size INTEGER NOT NULL,
    upload_time TIMESTAMP NOT NULL
);
```

## 🚀 Quick Start

### 1️⃣ **Set Up Virtual Environment**

```bash
cd api-server/giswater-hengine-app
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2️⃣ **Database Setup**

**Option A: Using Docker Compose (Recommended)**
```bash
docker-compose up -d postgres  # Start only PostgreSQL
```

**Option B: Local PostgreSQL**
```bash
# Install PostgreSQL and create database
createdb giswater_hengine
```

### 3️⃣ **Environment Variables**

Set the following environment variables (or use defaults):

```bash
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_NAME=giswater_hengine
export DATABASE_USER=postgres
export DATABASE_PASSWORD=postgres
```

### 4️⃣ **Run Locally**

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

📌 API Docs available at: [**http://127.0.0.1:8000/docs**](http://127.0.0.1:8000/docs)

---

## 🐳 Running with Docker

### **Complete Setup with Docker Compose**

```bash
# Create the external network (if it doesn't exist)
docker network create --subnet=172.21.1.0/24 api-network

# Start all services (PostgreSQL + API)
docker-compose up --build
```

### **Individual Docker Commands**

```bash
# Build the application
docker build -t giswater-hengine-app .

# Run with external PostgreSQL
docker run -d -p 8000:8000 \
  -e DATABASE_HOST=your_postgres_host \
  -e DATABASE_PASSWORD=your_password \
  -v $(pwd)/uploads:/app/uploads \
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

### File Upload Limits
- **Allowed Extensions:** `.inp` only
- **Maximum File Size:** 10MB
- **Upload Directory:** `uploads/` (auto-created)

### Database Configuration
- **Host:** `DATABASE_HOST` (default: localhost)
- **Port:** `DATABASE_PORT` (default: 5432)
- **Database:** `DATABASE_NAME` (default: giswater_hengine)
- **User:** `DATABASE_USER` (default: postgres)
- **Password:** `DATABASE_PASSWORD` (default: postgres)

### File Storage
- Files are stored with UUID prefixes to prevent conflicts
- Metadata is stored in PostgreSQL `inp_files` table
- Original filenames are preserved in database
- Automatic cleanup of orphaned database records

---

## 🧪 Testing the API

### Using the Interactive API Documentation
1. Start the server (with database)
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
- **Database**: Metadata stored in PostgreSQL with referential integrity
- **Cleanup**: Automatic cleanup of orphaned records when files are missing
- **Concurrency**: Safe concurrent access with database sessions

---

## 🔗 Integration with Giswater

This API follows similar patterns to the main giswater-api:
- Consistent response formats with `status`, `message`, and data fields
- Similar project structure and organization
- Compatible Docker networking (API: 172.21.1.51, DB: 172.21.1.52)
- Database-first approach for reliability

---

## 🚨 Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps

# Check database logs
docker-compose logs postgres

# Test database connection
docker-compose exec postgres psql -U postgres -d giswater_hengine -c "\dt"
```

### Application Logs
```bash
# View application logs
docker-compose logs giswater-hengine-app
```

---

## 📌 License

This project is free software, licensed under the GNU General Public License (GPL) version 3 or later.
