# NTR VIKASA FastAPI Backend — Phase 1 Foundation

Clean, scalable, and modular FastAPI backend architecture for the **NTR VIKASA Job Portal & District Employment Exchange System** (NTR District, Andhra Pradesh).

Phase 1 establishes the backend architecture and asynchronous MySQL database foundation using **SQLAlchemy 2.0 AsyncIO** and **asyncmy**.

---

## 🏛️ Directory Architecture

```text
NTR_Vikasa_Backend/
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # Primary FastAPI application entry point
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic BaseSettings (DB, CORS, JWT, uploads)
│   │   ├── security.py             # Bcrypt hashing & JWT utilities foundation
│   │   └── exceptions.py           # Custom exception definitions
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── session.py              # SQLAlchemy 2.0 async engine, async_sessionmaker, get_db
│   │   ├── base.py                 # Declarative Base
│   │   └── init_db.py              # Database initialization & async MySQL connection test
│   │
│   ├── models/
│   │   └── __init__.py             # ORM models (reserved for future phases)
│   │
│   ├── schemas/
│   │   └── __init__.py             # Pydantic schemas (reserved for future phases)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                 # Async database session dependency provider
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py           # Aggregated v1 API router (/api/v1)
│   │       └── endpoints/
│   │           └── __init__.py     # Business endpoints (reserved for future phases)
│   │
│   ├── services/
│   │   └── __init__.py             # Business logic layer (reserved for future phases)
│   │
│   ├── repositories/
│   │   └── __init__.py             # Data access layer (reserved for future phases)
│   │
│   └── utils/
│       └── __init__.py             # Common utilities (reserved for future phases)
│
├── scripts/
│   └── __init__.py
│
├── tests/
│   ├── __init__.py
│   └── test_main.py                # Health check & entry point verification test
│
├── uploads/
│   ├── resumes/                    # Candidate resumes directory
│   ├── documents/                  # Verification documents directory
│   └── logos/                      # Company logos directory
│
├── .env.example                    # Sample environment variables
├── .gitignore                      # Git ignore rules
├── requirements.txt                # Python package dependencies
└── README.md
```

---

## ⚙️ Technology Stack & Specifications

- **Backend**: http://127.0.0.1:8000
- **Swagger**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **Health**: http://127.0.0.1:8000/health
- **API**: http://127.0.0.1:8000/api/v1
- **Database**: MySQL
- **Database Driver**: asyncmy
- **ORM**: SQLAlchemy 2.0 Async (`create_async_engine`, `async_sessionmaker`, `AsyncSession`)

---

## 🚀 Running the Backend

`app/main.py` is the only application entry point.

### 1. Install Dependencies
```bash
cd NTR_Vikasa_Backend
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```
Ensure your MySQL connection URL is set in `.env`:
```env
DATABASE_URL=mysql+asyncmy://root:YOUR_PASSWORD@localhost:3306/ntr_vikasa
```

### 3. Start Development Server
```bash
uvicorn app.main:app --reload
```

---

## 🧪 Running Tests

```bash
pytest
```
