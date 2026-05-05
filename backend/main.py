from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import select, text
import os, json, logging

from config import settings
from database import engine, AsyncSessionLocal
from models import Base, User, FBILRate, SignupStatus, UserRole
from auth import get_password_hash
from routes import auth_routes, admin_routes, rates_routes, processing_routes, profile_routes
from services.scheduler import setup_scheduler, scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WSManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

ws_manager = WSManager()
rates_routes.set_ws_manager(ws_manager)

async def daily_scrape_job():
    """Job that runs daily to scrape FBIL rates."""
    from services.fbil_scraper import scrape_latest_rates
    logger.info("Running scheduled FBIL scrape...")
    try:
        rows = await scrape_latest_rates()
        if rows:
            async with AsyncSessionLocal() as db:
                from models import FBILRate
                from sqlalchemy import and_
                for row in rows:
                    existing = await db.execute(
                        select(FBILRate).where(
                            and_(FBILRate.date == row["date"], FBILRate.currency_pair == row["currency_pair"])
                        )
                    )
                    ex = existing.scalar_one_or_none()
                    if ex:
                        ex.rate = row["rate"]
                    else:
                        db.add(FBILRate(**row))
                await db.commit()
            await ws_manager.broadcast({"event": "rates_updated", "count": len(rows)})
            logger.info(f"Scheduled scrape: updated {len(rows)} rates")
    except Exception as e:
        logger.error(f"Scheduled scrape failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (checkfirst=True prevents DuplicateTableError)
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))

    # Seed admin user
    async with AsyncSessionLocal() as db:
        # Sync Admin
        try:
            result = await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
            existing_admin = result.scalar_one_or_none()
            if not existing_admin:
                admin = User(
                    username=settings.ADMIN_USERNAME,
                    password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                    role=UserRole.ADMIN,
                    signup_status=SignupStatus.APPROVED,
                    avatar_seed="admin",
                )
                db.add(admin)
                await db.commit()
                logger.info(f"Admin user '{settings.ADMIN_USERNAME}' created")
            else:
                # Ensure admin always has correct role, status and password
                changed = False
                if existing_admin.role != UserRole.ADMIN:
                    existing_admin.role = UserRole.ADMIN
                    changed = True
                if existing_admin.signup_status != SignupStatus.APPROVED:
                    existing_admin.signup_status = SignupStatus.APPROVED
                    changed = True
                if not existing_admin.is_active:
                    existing_admin.is_active = True
                    changed = True
                # Always reset password to env value on startup
                existing_admin.password_hash = get_password_hash(settings.ADMIN_PASSWORD)
                changed = True
                if changed:
                    await db.commit()
                    logger.info(f"Admin user '{settings.ADMIN_USERNAME}' credentials & role synced")
        except Exception as e:
            logger.error(f"Failed to sync admin user: {e}")

        # Check if we need historical data backfill
        count_result = await db.execute(select(FBILRate).limit(1))
        has_data = count_result.scalar_one_or_none()

    if not has_data:
        logger.info("No FBIL data found. Starting historical backfill...")
        await backfill_historical()

    # Start scheduler
    setup_scheduler(daily_scrape_job)

    yield

    if scheduler.running:
        scheduler.shutdown()

async def backfill_historical():
    from services.fbil_scraper import scrape_historical_rates
    from sqlalchemy import text
    logger.info("Starting historical FBIL data backfill (2 years)...")
    try:
        rows = await scrape_historical_rates(days=730)
        if rows:
            async with AsyncSessionLocal() as db:
                # Bulk insert, skip on conflict (date+currency_pair duplicates)
                db.add_all([FBILRate(**r) for r in rows])
                await db.commit()
            logger.info(f"Historical backfill complete: {len(rows)} rows inserted")
        else:
            logger.warning("Historical backfill returned 0 rows")
    except Exception as e:
        logger.error(f"Historical backfill failed: {e}", exc_info=True)

app = FastAPI(title="Nexus Exchange API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(rates_routes.router)
app.include_router(processing_routes.router)
app.include_router(profile_routes.router)

@app.websocket("/ws/rates")
async def websocket_rates(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# Serve Angular static files if dist exists
static_path = settings.FRONTEND_DIST_PATH
if os.path.exists(static_path):
    # Mount static assets
    assets_path = f"{static_path}/assets"
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    # Mount full static dir for JS/CSS chunks
    app.mount("/static-files", StaticFiles(directory=static_path), name="static-files")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_angular(full_path: str):
        # Try serving the file directly
        file_path = os.path.join(static_path, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        index = f"{static_path}/index.html"
        if os.path.exists(index):
            return FileResponse(index)
        return JSONResponse({"message": "Nexus Exchange API is running. Frontend not built."})
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "Nexus Exchange API is running", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
