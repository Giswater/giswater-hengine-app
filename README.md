# 🌊 Giswater HEngine Server

This repository contains a series of scripts to process INP files for calibration, solving, comparison, and other tasks. It also includes a basic API to communicate with the main Giswater API and is packaged as a Docker container.

## ✨ Features

- Process INP files for various tasks
- Basic API to communicate with the [Giswater API](https://github.com/Giswater/giswater_api_server)
- Dockerized for easy deployment

## 🚀 Quick Start

### 1️⃣ **Clone the Repository**

```sh
git clone https://github.com/yourusername/giswater_hengine_server.git
cd giswater_hengine_server
```

### 2️⃣ **Build the Docker Image**

```sh
docker build -t giswater_hengine_server .
```

### 3️⃣ **Run the Docker Container**

```sh
docker run -d -p 8000:8000 giswater_hengine_server
```

## 📂 Project Structure

The project directory structure is as follows:

```
giswater_hengine_server/
├── src/
│   ├── api/               # API to communicate with the Giswater API
│   │   ├── main.py        # API creation
│   │   ├── routes.py      # Endpoints
│   │
│   ├── core/              # Hydraulic engine algorithms
│   │   ├── calibrator.py  # Calibration functions
│   │   ├── comparer.py    # Comparer functions
│   │   ├── solver.py      # Solver functions
│   │   ├── utils.py       # Common utility functions
│
├── tests/                 # Unit and integration tests
├── docker-compose.yml     # Docker compose configuration
├── Dockerfile             # Docker definition and configuration
├── requirements.txt       # Required Python packages
```

## 📌 Usage

1. Access the API at `http://localhost:8000`.
2. Use the provided endpoints to process INP files and interact with the Giswater API.

## 📜 License

This project is licensed under the GPL-3.0 License. See the [LICENSE](LICENSE) file for details.
