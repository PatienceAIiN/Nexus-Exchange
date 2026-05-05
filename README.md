# Nexus Exchange 🛡️

A premium, full-stack FBIL Reference Rate Management Platform built for high-performance financial data processing and administrative oversight.

![Nexus Exchange Dashboard](https://api.dicebear.com/8.x/shapes/svg?seed=nexus&backgroundColor=0f172a)

## 🚀 Overview

Nexus Exchange is designed to automate the lifecycle of FBIL (Financial Benchmarks India Pvt. Ltd.) exchange rates—from automated scraping and real-time WebSocket updates to bulk file processing and administrative approval workflows.

### Key Features:
- **Real-Time Rates**: Automated scraping of FBIL rates with instant WebSocket broadcasting to clients.
- **High-Speed Processing**: Bulk upload and processing of `.xlsx` and `.csv` files with a smooth, real-time percentage progress bar.
- **Admin Command Center**: Secure, separate administrative panel for managing user approvals, role assignments, and platform statistics.
- **Smart Security**: Token-versioning system for immediate session invalidation on role changes and automated "self-healing" admin credentials.
- **Modern UI**: Dark-mode first design with glassmorphic elements, smooth animations, and a premium aesthetic.

---

## 🛠️ Tech Stack

### Backend:
- **Framework**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL (via Neon DB) with SQLAlchemy (Asyncio)
- **Security**: JWT Authentication + Passlib (Bcrypt)
- **Task Scheduling**: APScheduler (for automated FBIL scraping)
- **Storage**: Cloudflare R2 (S3-compatible) for file storage
- **Email**: SMTP integration for automated approval notifications

### Frontend:
- **Framework**: Angular 17+ (Standalone Components)
- **Styling**: Vanilla SCSS (Custom Design System)
- **State**: RxJS Observables & BehaviorSubjects
- **Icons**: Lucide & Custom SVGs

---

## 💻 Local Development Setup

### Prerequisites:
- Python 3.10+
- Node.js 18+ & npm
- PostgreSQL database

### 1. Clone the Repository
```bash
git clone https://github.com/PatienceAIiN/Nexus-Exchange.git
cd Nexus-Exchange
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```
Create a `.env` file in the `backend/` directory:
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
JWT_SECRET_KEY=your_secret_key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=Admin@1233
# Add R2 and SMTP credentials here
```
Start the server:
```bash
uvicorn main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm start
```
The app will be available at `http://localhost:4200`.

---

## 🚀 Deployment (Render)

The project is pre-configured for one-click deployment on Render.

1. **Create Web Service**: Connect your repo.
2. **Build Command**: `./render-build.sh`
3. **Start Command**: `cd backend && gunicorn main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
4. **Environment Variables**: Copy all keys from your `.env` to the Render Dashboard.

---

## 📁 Project Structure

```text
Nexus-Exchange/
├── backend/                # FastAPI Application
│   ├── routes/             # API Endpoints
│   ├── services/           # Scrapers, Processors, R2
│   ├── models.py           # Database Schema
│   └── main.py             # App Entry & Lifespan
├── frontend/               # Angular 17 Application
│   ├── src/app/core/       # Services, Guards, Interceptors
│   ├── src/app/pages/      # UI Components
│   └── styles.scss         # Global Design System
├── render-build.sh         # Deployment Automation
└── Procfile                # Render Start Command
```

---

## 📝 License
Proprietary - Developed by [Patience AI](https://patienceai.in).

---
*Maintained with ❤️ by the Nexus Team.*
