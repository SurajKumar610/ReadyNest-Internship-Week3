# India Business Intelligence & Transformation Dashboard

An India-focused digital opportunity analysis platform that processes Google Maps business listings, cleans data quality anomalies, calculates growth opportunity scores, generates AI insights, and compiles PDF/PPTX transformation reports.

---

## 📂 Project Structure

The project has been restructured into clean `backend`, `frontend`, and `docs` directories to facilitate clean local development and containerized or cloud deployments:

```text
ReadyNest Intership Week3/
├── backend/                  # FastAPI Backend Server & Engines
│   ├── config/               # Opportunity Weights Configuration
│   │   └── scoring.json      # Customizable scoring rules
│   ├── data/                 # Raw and processed datasets (CSV)
│   ├── src/                  # Python source code
│   │   ├── analyzer.py       # Scoring Engine & Insight Generator
│   │   ├── cleaner.py        # Data Ingestion & Preprocessing Pipeline
│   │   ├── exporter.py       # PDF/PPTX Document Generators
│   │   ├── generator.py      # Indian Business Listing Demo Generator
│   │   └── server.py         # FastAPI API Routing Setup
│   ├── tests/                # Integration test suites
│   │   └── run_tests.py      # Automated pipeline tests
│   ├── main.py               # Backend main server entrypoint
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # Static Frontend Dashboard
│   ├── css/
│   │   └── style.css         # Modern visual styles
│   ├── js/
│   │   └── app.js            # Leaflet Map, Charts.js & API connector
│   └── index.html            # Dashboard Main HTML page
│
├── docs/                     # Project Specifications & Documentation
│   ├── prd.pdf               # Product Requirements Document
│   ├── uiux.pdf              # UI/UX Specification
│   ├── trd.pdf               # Technical Requirements Document
│   └── impplan.pdf           # Implementation Plan
│
├── Dockerfile                # Containerized deployment settings
└── README.md                 # Project guide (this file)
```

---

## 🌐 Live Production Links

The application is deployed and accessible globally at the following links:
- **Frontend Dashboard (Vercel)**: [https://ready-nest-internship-week3.vercel.app/](https://ready-nest-internship-week3.vercel.app/)
- **Backend API Server (Render)**: [https://readynest-internship-week3.onrender.com/](https://readynest-internship-week3.onrender.com/)
- **Swagger API Interactive Docs**: [https://readynest-internship-week3.onrender.com/docs](https://readynest-internship-week3.onrender.com/docs)

---

## 🚀 Local Development Setup

### Option 1: Local Server (FastAPI Unified Mode)

In unified mode, the FastAPI backend serves both the API endpoints and the static HTML frontend.

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the server**:
   ```bash
   python main.py
   ```

4. **Access the local dashboard**:
   Open your browser and navigate to `http://127.0.0.1:8000`.

---

### Option 2: Docker Container Deployment (Local)

You can build and deploy the entire application using the root `Dockerfile`.

1. **Build the Docker image**:
   ```bash
   docker build -t business-bi-dashboard .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8000:8000 business-bi-dashboard
   ```

3. **Access the local dashboard**:
   Navigate to `http://localhost:8000`.

---

### Option 3: Decoupled Deployment (Independent Backend & Frontend)

If you wish to host the frontend (e.g., on Vercel/Netlify) and the backend (e.g., on Render/Heroku) separately:

#### 1. Backend Hosting (Render/Heroku/AWS)
- Deploy the `backend/` folder to your Python hosting service.
- Ensure the port binds using the `PORT` and `HOST` environment variables (FastAPI has been made environment-ready).
- Enable CORS if needed (enabled by default to allow `*`).

#### 2. Frontend Connection
- Open [frontend/js/app.js](file:///e:/ReadyNest%20Intership%20Week3/frontend/js/app.js) and locate `API_BASE_URL` on line 2:
  ```javascript
  const API_BASE_URL = "https://your-deployed-backend-api.com";
  ```
- Change `""` to your live backend base URL.
- Deploy the `frontend/` folder directly to any static site hosting provider.

---

## 🧪 Verification & Testing

To run the automated integration tests that check the data generator, cleaner, analyzer scoring, and report exporters:

1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Run the integration test suite:
   ```bash
   python tests/run_tests.py
   ```
