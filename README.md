# 🚀 Giswater Hydraulic Engine API

A FastAPI application for managing INP files for hydraulic modeling with EPANET. This API provides endpoints for uploading and retrieving INP files, following similar patterns to the giswater-api for consistency.

## 📂 Project Structure

```
giswater-hengine-app/
├── src/
│   └── api/
│       ├── main.py          # FastAPI application entry point
│       ├── routes.py        # API endpoints for INP file management
│       ├── models.py        # Pydantic models for data validation
│       └── __init__.py
├── uploads/                 # Directory for uploaded INP files (auto-created)
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup
└── README.md               # This file
```

## 🚀 Quick Start

### 1️⃣ **Set Up Virtual Environment**

```bash
cd api-server/giswater-hengine-app
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2️⃣ **Run Locally**

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

📌 API Docs available at: [**http://127.0.0.1:8000/docs**](http://127.0.0.1:8000/docs)

---

## 🐳 Running with Docker

### **Build and Run with Docker Compose**

```bash
docker-compose up --build
```

### **Build and Run with Docker**

```bash
docker build -t giswater-hengine-app .
docker run -d -p 8000:8000 -v $(pwd)/uploads:/app/uploads giswater-hengine-app
```

---

## 🛠️ API Endpoints

| Endpoint          | Method | Description                                    |
|-------------------|--------|-----------------------------------------------|
| `/`               | GET    | Root endpoint - API information               |
| `/health`         | GET    | Health check endpoint                         |
| `/inp/upload`     | POST   | Upload an INP file (multipart/form-data)     |
| `/inp/files`      | GET    | Get all uploaded INP files with metadata     |

### 📤 Upload INP File

**POST** `/inp/upload`

Upload an INP file for hydraulic modeling.

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

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/inp/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/model.inp"
```

### 📥 Get All INP Files

**GET** `/inp/files`

Retrieve information about all uploaded INP files.

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
    },
    {
      "file_id": "uuid-2",
      "filename": "model2.inp",
      "upload_time": "2024-01-01T13:00:00",
      "file_size": 2048,
      "file_path": "uploads/uuid-2_model2.inp"
    }
  ]
}
```

---

## 🔧 Configuration

### File Upload Limits
- **Allowed Extensions:** `.inp` only
- **Maximum File Size:** 10MB
- **Upload Directory:** `uploads/` (auto-created)

### File Storage
- Files are stored with UUID prefixes to prevent conflicts
- Metadata is stored in `uploads/files_metadata.json`
- Original filenames are preserved in metadata

---

## 🧪 Testing the API

### Using the Interactive API Documentation
1. Start the server
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

---

## 📁 File Management

- Uploaded files are stored in the `uploads/` directory
- Each file gets a unique UUID prefix to prevent naming conflicts
- File metadata is tracked in JSON format
- The system automatically cleans up references to deleted files

---

## 🔗 Integration with Giswater

This API follows similar patterns to the main giswater-api:
- Consistent response formats with `status`, `message`, and data fields
- Similar project structure and organization
- Compatible Docker networking (uses different IP: 172.21.1.51)

---

## 📌 License

This project is licensed under the GPL-3.0 License. See the [LICENSE](LICENSE) file for details.
