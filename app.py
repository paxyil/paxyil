import os
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from db import init_db, get_conn
from auth import parse_dev_user

load_dotenv()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Mini App CRM")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/api/me")
async def get_me(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data")
    user = parse_dev_user(init_data)
    return user


@app.get("/api/applications")
async def get_applications(request: Request, status: str | None = None):
    user = parse_dev_user(request.headers.get("X-Telegram-Init-Data"))

    conn = get_conn()
    cur = conn.cursor()

    if user["is_admin"]:
        if status:
            cur.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY id DESC",
                (status,)
            )
        else:
            cur.execute("SELECT * FROM applications ORDER BY id DESC")
    else:
        if status:
            cur.execute(
                "SELECT * FROM applications WHERE user_id = ? AND status = ? ORDER BY id DESC",
                (user["id"], status)
            )
        else:
            cur.execute(
                "SELECT * FROM applications WHERE user_id = ? ORDER BY id DESC",
                (user["id"],)
            )

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/applications/{application_id}")
async def get_application(application_id: int, request: Request):
    user = parse_dev_user(request.headers.get("X-Telegram-Init-Data"))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE id = ?", (application_id,))
    app_row = cur.fetchone()

    if not app_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    app_dict = dict(app_row)

    if not user["is_admin"] and app_dict["user_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Нет доступа")

    cur.execute(
        "SELECT * FROM messages WHERE application_id = ? ORDER BY id ASC",
        (application_id,)
    )
    messages = [dict(row) for row in cur.fetchall()]
    conn.close()

    return {
        "application": app_dict,
        "messages": messages
    }


@app.post("/api/applications")
async def create_application(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    service: str = Form(...),
    desired_date: str = Form(""),
    desired_time: str = Form(""),
    comment: str = Form(...),
    photo: UploadFile | None = File(None),
):
    user = parse_dev_user(request.headers.get("X-Telegram-Init-Data"))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    photo_path = None
    if photo:
        filename = f"{int(datetime.now().timestamp())}_{photo.filename}"
        target = UPLOAD_DIR / filename
        with open(target, "wb") as f:
            f.write(await photo.read())
        photo_path = f"/uploads/{filename}"

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO applications
        (user_id, user_name, username, phone, service, desired_date, desired_time, comment, photo_path, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)
    """, (
        user["id"],
        name,
        user["username"],
        phone,
        service,
        desired_date,
        desired_time,
        comment,
        photo_path,
        now,
        now
    ))
    application_id = cur.lastrowid

    cur.execute("""
        INSERT INTO messages (application_id, sender_id, sender_role, text, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        application_id,
        user["id"],
        "user",
        f"Создана заявка: {comment}",
        now
    ))

    conn.commit()
    conn.close()

    return {"ok": True, "application_id": application_id}


@app.post("/api/applications/{application_id}/messages")
async def send_message(application_id: int, request: Request, text: str = Form(...)):
    user = parse_dev_user(request.headers.get("X-Telegram-Init-Data"))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE id = ?", (application_id,))
    app_row = cur.fetchone()

    if not app_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    app_dict = dict(app_row)
    if not user["is_admin"] and app_dict["user_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Нет доступа")

    if app_dict["status"] == "closed":
        conn.close()
        raise HTTPException(status_code=400, detail="Заявка закрыта")

    role = "admin" if user["is_admin"] else "user"

    cur.execute("""
        INSERT INTO messages (application_id, sender_id, sender_role, text, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (application_id, user["id"], role, text, now))

    if app_dict["status"] == "new" and user["is_admin"]:
        cur.execute("""
            UPDATE applications
            SET status = 'in_progress', updated_at = ?
            WHERE id = ?
        """, (now, application_id))

    conn.commit()
    conn.close()

    return {"ok": True}


@app.post("/api/applications/{application_id}/status")
async def set_status(application_id: int, request: Request, status: str = Form(...)):
    user = parse_dev_user(request.headers.get("X-Telegram-Init-Data"))
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Только админ")

    if status not in {"new", "in_progress", "closed"}:
        raise HTTPException(status_code=400, detail="Некорректный статус")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE applications
        SET status = ?, updated_at = ?
        WHERE id = ?
    """, (status, now, application_id))
    conn.commit()
    conn.close()

    return {"ok": True}