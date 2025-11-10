import secrets

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_settings_dependency
from app.models.api_key import APIKey
from app.models.daily_usage import DailyUsage
from app.models.send_log import SendLog
from app.services.auth import AuthService

templates = Jinja2Templates(directory="templates")
security = HTTPBasic()


async def admin_auth(
    credentials: HTTPBasicCredentials = Depends(security),
    x_admin_key: str | None = Header(None, alias="X-ADMIN-KEY"),
    settings=Depends(get_settings_dependency),
):
    """Simple admin auth: prefer BasicAuth (ADMIN_USERNAME/ADMIN_PASSWORD). If not set,
    accept X-ADMIN-KEY header matching ADMIN_API_KEY. In debug mode, allow if no creds are set.
    """
    # If explicit admin API key is provided and header matches, allow
    if settings.admin_api_key and x_admin_key:
        if secrets.compare_digest(x_admin_key, settings.admin_api_key):
            return True

    # If username/password set, validate BasicAuth
    if settings.admin_username and settings.admin_password:
        # Validate provided credentials
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        if secrets.compare_digest(credentials.username, settings.admin_username) and secrets.compare_digest(
            credentials.password, settings.admin_password
        ):
            return True
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    # Fallback: if debug, allow; otherwise deny
    if settings.debug:
        return True

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access is disabled")


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_auth)])


@router.get("/", include_in_schema=False)
async def admin_index():
    return RedirectResponse(url="/admin/api-keys")


@router.get("/api-keys")
async def list_api_keys(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    per_page: int = 25,
):
    # sanitize paging
    if per_page <= 0:
        per_page = 25
    per_page = min(per_page, 200)
    page = max(1, page)

    # total count
    total_res = await db.execute(select(func.count()).select_from(APIKey))
    total = total_res.scalar_one()

    stmt = select(APIKey).limit(per_page).offset((page - 1) * per_page)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return templates.TemplateResponse(
        "admin_list.html",
        {
            "request": request,
            "title": "API Keys",
            "items": items,
            "type": "api_keys",
            "page": page,
            "per_page": per_page,
            "total": total,
        },
    )


@router.get("/api-keys/create")
async def create_api_key_form(request: Request):
    return templates.TemplateResponse("admin_create_api_key.html", {"request": request})


@router.post("/api-keys/create")
async def create_api_key(
    request: Request,
    name: str = Form(...),
    daily_limit: int | None = Form(None),
    allowed: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    settings=Depends(get_settings_dependency),
):
    auth = AuthService(db, settings)
    # parse allowed recipients from comma-separated form field
    allowed_list = None
    if allowed:
        allowed_list = [e.strip().lower() for e in allowed.split(",") if e.strip()]

    key_obj, plain_key = await auth.create_api_key(
        name=name,
        daily_limit=daily_limit,
        allowed_recipients=allowed_list,
    )

    # Render a page with the plain key (only shown once)
    return templates.TemplateResponse(
        "admin_create_api_key.html",
        {
            "request": request,
            "created": True,
            "plain_key": plain_key,
            "key_obj": key_obj,
        },
    )


@router.post("/api-keys/{api_key_id}/deactivate")
async def deactivate_api_key(api_key_id: str, db: AsyncSession = Depends(get_db)):
    # Deactivate by id
    try:
        import uuid as _uuid

        uid = _uuid.UUID(api_key_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    stmt = select(APIKey).where(APIKey.id == uid)
    res = await db.execute(stmt)
    key_obj = res.scalar_one_or_none()
    if not key_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    key_obj.is_active = False
    await db.flush()
    return RedirectResponse(url="/admin/api-keys", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/api-keys/{api_key_id}/activate")
async def activate_api_key(api_key_id: str, db: AsyncSession = Depends(get_db)):
    try:
        import uuid as _uuid

        uid = _uuid.UUID(api_key_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    stmt = select(APIKey).where(APIKey.id == uid)
    res = await db.execute(stmt)
    key_obj = res.scalar_one_or_none()
    if not key_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    key_obj.is_active = True
    await db.flush()
    return RedirectResponse(url="/admin/api-keys", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/daily-usage")
async def list_daily_usage(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    per_page: int = 25,
):
    if per_page <= 0:
        per_page = 25
    per_page = min(per_page, 200)
    page = max(1, page)

    total_res = await db.execute(select(func.count()).select_from(DailyUsage))
    total = total_res.scalar_one()

    stmt = select(DailyUsage).limit(per_page).offset((page - 1) * per_page)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return templates.TemplateResponse(
        "admin_list.html",
        {
            "request": request,
            "title": "Daily Usage",
            "items": items,
            "type": "daily_usage",
            "page": page,
            "per_page": per_page,
            "total": total,
        },
    )


@router.get("/send-logs")
async def list_send_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    per_page: int = 25,
):
    if per_page <= 0:
        per_page = 25
    per_page = min(per_page, 200)
    page = max(1, page)

    total_res = await db.execute(select(func.count()).select_from(SendLog))
    total = total_res.scalar_one()

    stmt = select(SendLog).limit(per_page).offset((page - 1) * per_page)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return templates.TemplateResponse(
        "admin_list.html",
        {
            "request": request,
            "title": "Send Logs",
            "items": items,
            "type": "send_logs",
            "page": page,
            "per_page": per_page,
            "total": total,
        },
    )
