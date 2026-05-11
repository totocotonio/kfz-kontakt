from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import uvicorn
import os
import shutil
import asyncio
import threading
import time
import secrets
from zoneinfo import ZoneInfo

# ===== PUSH NOTIFICATIONS =====
def send_push_to_admins(db, title, body, url='/admin'):
    try:
        import json as _j
        from pywebpush import webpush, WebPushException
        keys = _j.load(open('/opt/ticketsystem/vapid_keys.json'))
        subs = db.query(PushSubscription).all()
        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh, "auth": sub.auth}
                    },
                    data=_j.dumps({"title": title, "body": body, "url": url}),
                    vapid_private_key=keys['private_pem'],
                    vapid_claims={"sub": "mailto:" + keys['email']}
                )
            except WebPushException as ex:
                if ex.response and ex.response.status_code in (404, 410):
                    db.delete(sub)
                    db.commit()
            except Exception:
                pass
    except Exception:
        pass

BERLIN = ZoneInfo("Europe/Berlin")

def now_berlin():
    from datetime import timezone
    return datetime.now(timezone.utc).astimezone(BERLIN).replace(tzinfo=None)

from database import get_db, engine, Base
from models import User, Ticket, Comment, TicketAttachment, TicketStatus, TicketPriority, AdminNote, TicketHistory, PasswordResetToken, TicketSequence, AdminTask, TaskHistory, ReplyTemplate, AuditLog, UserTemplate, UserLogin, PushSubscription
from auth import (
    authenticate_user, create_access_token, get_current_user,
    get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
)
from email_utils import (send_ticket_created_email, send_ticket_updated_email,
                         send_new_registration_email, send_new_ticket_admin_email,
                         send_registration_confirmation_email, send_reminder_email,
                         send_user_comment_admin_email, send_password_reset_email,
                         send_verification_email, send_task_reminder_email,
                         send_daily_summary_email, send_sla_warning_email,
                         send_2fa_code_email, send_weekly_report_email, send_auto_close_email,
                         send_user_closed_ticket_email, send_user_reopened_ticket_email)
import schemas

Base.metadata.create_all(bind=engine)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="MP-Feuer-Ticketsystem")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    print(f"[ERROR] Unbehandelte Ausnahme: {exc}")
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ─── ERINNERUNGSMAIL HINTERGRUNDTASK ────────────────────────────
def reminder_task():
    """Läuft alle 24h, sendet Erinnerungen bei Tickets älter als 5 Tage."""
    while True:
        time.sleep(86400)  # 24 Stunden
        try:
            from database import SessionLocal
            db = SessionLocal()
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=5)
            old_tickets = db.query(Ticket).filter(
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress]),
                Ticket.updated_at < cutoff
            ).all()
            for ticket in old_tickets:
                user = db.query(User).filter(User.id == ticket.user_id).first()
                if user:
                    send_reminder_email(user.email, user.name, ticket)
            db.close()
            print(f"[REMINDER] {len(old_tickets)} Erinnerungen gesendet")
        except Exception as e:
            print(f"[REMINDER FEHLER] {e}")

def task_reminder_task():
    """Läuft täglich um 7 Uhr und sendet Erinnerungen für fällige Aufgaben."""
    while True:
        now = now_berlin()
        # Warte bis 7 Uhr morgens
        target = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if now >= target:
            target = target + timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        time.sleep(wait_seconds)
        try:
            from database import SessionLocal
            db = SessionLocal()
            today_start = now_berlin().replace(hour=0, minute=0, second=0)
            today_end = now_berlin().replace(hour=23, minute=59, second=59)
            due_tasks = db.query(AdminTask).filter(
                AdminTask.is_done == False,
                AdminTask.due_date >= today_start,
                AdminTask.due_date <= today_end
            ).all()
            if due_tasks:
                admins = db.query(User).filter(User.is_admin == True).all()
                for admin in admins:
                    send_task_reminder_email(admin.email, admin.name, due_tasks)
                print(f"[TASK REMINDER] {len(due_tasks)} fällige Aufgaben gesendet")
            db.close()
        except Exception as e:
            print(f"[TASK REMINDER FEHLER] {e}")

def daily_summary_task():
    """Sendet täglich um 7:30 Uhr eine Zusammenfassung an alle Admins."""
    while True:
        now = now_berlin()
        target = now.replace(hour=7, minute=30, second=0, microsecond=0)
        if now >= target:
            target = target + timedelta(days=1)
        time.sleep((target - now).total_seconds())
        try:
            from database import SessionLocal
            db = SessionLocal()
            today_start = now_berlin().replace(hour=0, minute=0, second=0)
            total = db.query(Ticket).count()
            open_t = db.query(Ticket).filter(Ticket.status == TicketStatus.open).count()
            in_progress = db.query(Ticket).filter(Ticket.status == TicketStatus.in_progress).count()
            resolved_today = db.query(Ticket).filter(
                Ticket.resolved_at >= today_start).count()
            open_tasks = db.query(AdminTask).filter(AdminTask.is_done == False).count()
            # Unbeantwortet zählen
            tickets_active = db.query(Ticket).filter(
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])).all()
            unanswered = 0
            for t in tickets_active:
                comments = db.query(Comment).filter(Comment.ticket_id == t.id)\
                             .order_by(Comment.created_at.desc()).first()
                if not comments or not comments.is_admin:
                    unanswered += 1
            stats = {
                "date": now_berlin().strftime('%d.%m.%Y'),
                "total": total, "open": open_t, "in_progress": in_progress,
                "unanswered": unanswered, "resolved_today": resolved_today,
                "open_tasks": open_tasks
            }
            admins = db.query(User).filter(User.is_admin == True).all()
            for admin in admins:
                send_daily_summary_email(admin.email, admin.name, stats)
            db.close()
            print(f"[DAILY SUMMARY] Gesendet an {len(admins)} Admin(s)")
        except Exception as e:
            print(f"[DAILY SUMMARY FEHLER] {e}")

def sla_check_task():
    """Prüft stündlich ob Tickets die SLA-Zeit überschritten haben."""
    time.sleep(300)
    last_sent = {}
    while True:
        try:
            from database import SessionLocal
            db = SessionLocal()
            settings = load_settings()
            sla_hours = settings.get("sla_hours", {
                "critical": 2, "high": 8, "medium": 24, "low": 72
            })
            email_enabled = sla_hours.get("email_enabled", True)
            email_interval = sla_hours.get("email_interval", 1)
            now = now_berlin()

            active_tickets = db.query(Ticket).filter(
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])
            ).all()

            overdue = []
            for t in active_tickets:
                prio = t.priority.value
                sla_h = sla_hours.get(prio, 24)
                age_hours = (now - t.created_at).total_seconds() / 3600
                last_comment = db.query(Comment).filter(
                    Comment.ticket_id == t.id
                ).order_by(Comment.created_at.desc()).first()
                if not last_comment or not last_comment.is_admin:
                    if age_hours > sla_h:
                        # Automatische Prioritätserhöhung
                        if prio == "low" and age_hours > sla_hours.get("low", 72) * 1.5:
                            t.priority = TicketPriority.medium
                            db.add(TicketHistory(ticket_id=t.id, changed_by_id=None,
                                field="Priorität", old_value="low",
                                new_value="medium"))
                            db.commit()
                            print(f"[SLA] Ticket {t.ticket_number} auf Mittel erhöht")
                        elif prio == "medium" and age_hours > sla_hours.get("medium", 24) * 1.5:
                            t.priority = TicketPriority.high
                            db.add(TicketHistory(ticket_id=t.id, changed_by_id=None,
                                field="Priorität", old_value="medium",
                                new_value="high"))
                            db.commit()
                            print(f"[SLA] Ticket {t.ticket_number} auf Hoch erhöht")
                        elif prio == "high" and age_hours > sla_hours.get("high", 8) * 1.5:
                            t.priority = TicketPriority.critical
                            db.add(TicketHistory(ticket_id=t.id, changed_by_id=None,
                                field="Priorität", old_value="high",
                                new_value="critical"))
                            db.commit()
                            print(f"[SLA] Ticket {t.ticket_number} auf Kritisch erhöht")

                        if email_enabled:
                            last = last_sent.get(t.id)
                            if not last or (now - last).total_seconds() / 3600 >= email_interval:
                                overdue.append({
                                    "number": t.ticket_number,
                                    "title": t.title,
                                    "priority": t.priority.value,
                                    "overdue_hours": round(age_hours - sla_h, 1),
                                    "customer": t.user.name if t.user else "–"
                                })
                                last_sent[t.id] = now

            if overdue and email_enabled:
                admins = db.query(User).filter(User.is_admin == True).all()
                for admin in admins:
                    send_sla_warning_email(admin.email, admin.name, overdue)
                print(f"[SLA] {len(overdue)} überfällige Tickets gemeldet")
            db.close()
        except Exception as e:
            print(f"[SLA FEHLER] {e}")
        time.sleep(3600)

def weekly_report_task():
    """Sendet jeden Montag um 8:00 Uhr einen Wochenbericht."""
    while True:
        now = now_berlin()
        # Nächsten Montag 8 Uhr berechnen
        days_until_monday = (7 - now.weekday()) % 7 or 7
        target = (now + timedelta(days=days_until_monday)).replace(
            hour=8, minute=0, second=0, microsecond=0)
        time.sleep((target - now).total_seconds())
        try:
            from database import SessionLocal
            db = SessionLocal()
            week_start = now_berlin() - timedelta(days=7)
            new_tickets = db.query(Ticket).filter(Ticket.created_at >= week_start).count()
            resolved = db.query(Ticket).filter(
                Ticket.resolved_at >= week_start).count()
            still_open = db.query(Ticket).filter(
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])).count()
            users = db.query(User).count()
            # Unbeantwortet zählen
            active = db.query(Ticket).filter(
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])).all()
            unanswered = sum(1 for t in active if not db.query(Comment).filter(
                Comment.ticket_id == t.id, Comment.is_admin == True).first())
            stats = {
                "kw": now_berlin().isocalendar()[1],
                "from_date": week_start.strftime('%d.%m.%Y'),
                "to_date": now_berlin().strftime('%d.%m.%Y'),
                "new_tickets": new_tickets, "resolved": resolved,
                "still_open": still_open, "unanswered": unanswered, "users": users
            }
            admins = db.query(User).filter(User.is_admin == True).all()
            for admin in admins:
                send_weekly_report_email(admin.email, admin.name, stats)
            db.close()
            print(f"[WEEKLY] Wochenbericht gesendet")
        except Exception as e:
            print(f"[WEEKLY FEHLER] {e}")

def auto_escalation_task():
    """Erhöht automatisch die Priorität von Tickets die zu lange offen sind."""
    time.sleep(600)
    while True:
        try:
            from database import SessionLocal
            db = SessionLocal()
            settings = load_settings()
            sla_hours = settings.get("sla_hours", {
                "critical": 2, "high": 8, "medium": 24, "low": 72
            })
            now = now_berlin()
            escalation_map = {"low": "medium", "medium": "high", "high": "critical"}
            active = db.query(Ticket).filter(
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])
            ).all()
            for t in active:
                prio = t.priority.value
                if prio == "critical":
                    continue
                sla_h = sla_hours.get(prio, 24)
                age_h = (now - t.created_at).total_seconds() / 3600
                last_c = db.query(Comment).filter(Comment.ticket_id == t.id)\
                           .order_by(Comment.created_at.desc()).first()
                if last_c and last_c.is_admin:
                    continue
                if age_h > sla_h * 2:
                    new_prio = escalation_map.get(prio)
                    if new_prio:
                        t.priority = TicketPriority(new_prio)
                        db.add(TicketHistory(
                            ticket_id=t.id, changed_by_id=None,
                            field="Priorität (Auto-Eskalation)",
                            old_value=prio, new_value=new_prio
                        ))
                        db.commit()
            db.close()
        except Exception as e:
            print(f"[ESKALATION FEHLER] {e}")
        time.sleep(3600)

def auto_close_task():
    """Schließt Tickets automatisch wenn Nutzer 3 Wochen nicht geantwortet hat
    nachdem ein Admin geantwortet hat."""
    time.sleep(3600)  # 1 Stunde nach Start warten
    while True:
        try:
            from database import SessionLocal
            db = SessionLocal()
            cutoff = now_berlin() - timedelta(weeks=3)
            # Aktive Tickets finden
            tickets = db.query(Ticket).filter(
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])
            ).all()
            closed_count = 0
            for ticket in tickets:
                if not ticket.comments:
                    continue
                # Letzten Kommentar prüfen
                comments_sorted = sorted(ticket.comments, key=lambda c: c.created_at)
                last_comment = comments_sorted[-1]
                # Nur wenn letzter Kommentar vom Admin ist UND älter als 3 Wochen
                if not last_comment.is_admin:
                    continue
                if last_comment.created_at > cutoff:
                    continue
                # Ticket automatisch schließen
                old_status = ticket.status.value
                ticket.status = TicketStatus.closed
                ticket.updated_at = now_berlin()
                db.add(TicketHistory(
                    ticket_id=ticket.id,
                    changed_by_id=None,
                    field="Status (Auto)",
                    old_value=old_status,
                    new_value="closed"
                ))
                # Kommentar im Ticket hinterlassen
                auto_comment = Comment(
                    ticket_id=ticket.id,
                    user_id=ticket.user_id,
                    content="⚙️ Dieses Ticket wurde automatisch geschlossen, da seit 3 Wochen "
                            "keine Rückmeldung eingegangen ist. Falls dein Problem noch besteht, "
                            "kannst du das Ticket jederzeit wieder öffnen.",
                    is_admin=True
                )
                db.add(auto_comment)
                db.commit()
                # E-Mail an Nutzer senden
                if ticket.user:
                    try:
                        send_auto_close_email(ticket.user.email, ticket.user.name, ticket)
                    except Exception:
                        pass
                closed_count += 1
                print(f"[AUTO-CLOSE] Ticket {ticket.ticket_number} automatisch geschlossen")
            db.close()
            if closed_count:
                print(f"[AUTO-CLOSE] {closed_count} Ticket(s) geschlossen")
        except Exception as e:
            print(f"[AUTO-CLOSE FEHLER] {e}")
        time.sleep(86400)  # Täglich prüfen



@app.on_event("startup")
async def startup_event():
    # Prioritätsfarben als Jinja-Global setzen
    settings = load_settings()
    colors = settings.get("priority_colors", {
        "critical": "#ef4444", "high": "#f59e0b",
        "medium": "#3b82f6", "low": "#6b7280"
    })
    templates.env.globals["priority_colors"] = colors

    def wappen_filename(gemeinde):
        if not gemeinde:
            return ""
        return gemeinde.replace("Ü","Ue").replace("ü","ue").replace("Ö","Oe").replace("ö","oe").replace("Ä","Ae").replace("ä","ae")
    templates.env.globals["wappen_filename"] = wappen_filename

    def highlight(text, query):
        if not query or not text:
            return text
        import re
        from markupsafe import Markup, escape
        escaped_text = str(escape(text))
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        result = pattern.sub(
            lambda m: f'<mark style="background:#fef08a;color:#1a1a2e;border-radius:2px;padding:0 2px;">{m.group()}</mark>',
            escaped_text
        )
        return Markup(result)
    templates.env.globals["highlight"] = highlight

    # Sitzungs-Timeout aus Settings laden
    import auth
    auth.SESSION_TIMEOUT_MINUTES = settings.get("session_timeout", 60)
    print(f"[STARTUP] Sitzungs-Timeout: {auth.SESSION_TIMEOUT_MINUTES} Minuten")

    t = threading.Thread(target=reminder_task, daemon=True)
    t.start()
    t2 = threading.Thread(target=task_reminder_task, daemon=True)
    t2.start()
    t3 = threading.Thread(target=daily_summary_task, daemon=True)
    t3.start()
    t4 = threading.Thread(target=sla_check_task, daemon=True)
    t4.start()
    t5 = threading.Thread(target=weekly_report_task, daemon=True)
    t5.start()
    t6 = threading.Thread(target=auto_escalation_task, daemon=True)
    t6.start()
    t7 = threading.Thread(target=auto_close_task, daemon=True)
    t7.start()
    print("[STARTUP] Erinnerungs-Tasks gestartet")

@app.middleware("http")
async def update_last_seen(request: Request, call_next):
    response = await call_next(request)
    try:
        token = request.cookies.get("access_token")
        if token:
            from database import SessionLocal
            from auth import jwt, SECRET_KEY, ALGORITHM
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                db = SessionLocal()
                user = db.query(User).filter(User.id == int(user_id)).first()
                if user:
                    user.last_seen = now_berlin()
                    db.commit()
                db.close()
    except:
        pass
    return response

# ─── AUTH ROUTES ────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, db: Session = Depends(get_db),
                email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Ungültige E-Mail oder Passwort"
        })
    if not user.is_verified and not user.is_admin:
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Bitte bestätigen Sie zuerst Ihre E-Mail-Adresse."
        })
    if hasattr(user, 'is_active') and user.is_active == False:
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Ihr Konto wurde deaktiviert. Bitte wenden Sie sich an den Administrator."
        })
    # 2FA prüfen für Admins
    if user.is_admin:
        if getattr(user, 'totp_enabled', False):
            # TOTP aktiv → zur 2FA-Seite weiterleiten
            import secrets as sec
            tmp_token = sec.token_urlsafe(32)
            response = RedirectResponse(url=f"/2fa/verify?method=totp&tmp={tmp_token}", status_code=302)
            response.set_cookie("tmp_user_id", str(user.id), httponly=True, max_age=300)
            return response
        elif getattr(user, 'email_2fa_enabled', False):
            # E-Mail 2FA aktiv → Code senden und zur Eingabe weiterleiten
            import random, secrets as sec
            code = str(random.randint(100000, 999999))
            user.two_fa_code = code
            user.two_fa_code_expires = now_berlin() + timedelta(minutes=10)
            db.commit()
            threading.Thread(target=send_2fa_code_email,
                           args=(user.email, user.name, code), daemon=True).start()
            response = RedirectResponse(url="/2fa/verify?method=email", status_code=302)
            response.set_cookie("tmp_user_id", str(user.id), httponly=True, max_age=300)
            return response
    access_token = create_access_token(data={"sub": str(user.id)})
    log_action(db, user.id, "LOGIN", f"Anmeldung: {user.email}",
               get_real_ip(request))
    # Login aufzeichnen
    ua = request.headers.get("user-agent", "")[:200]
    db.add(UserLogin(
        user_id=user.id,
        ip_address=get_real_ip(request),
        user_agent=ua
    ))
    db.commit()
    if user.is_admin:
        response = RedirectResponse(url="/admin", status_code=302)
    else:
        response = RedirectResponse(url="/portal", status_code=302)
    response.set_cookie("access_token", access_token, httponly=True)
    return response

@app.get("/2fa/verify", response_class=HTMLResponse)
async def twofa_verify_page(request: Request, method: str = "email"):
    return templates.TemplateResponse("2fa_verify.html", {
        "request": request, "method": method
    })

@app.post("/2fa/verify")
async def twofa_verify(request: Request, db: Session = Depends(get_db),
                       code: str = Form(...), method: str = Form(default="email")):
    tmp_user_id = request.cookies.get("tmp_user_id")
    if not tmp_user_id:
        return RedirectResponse(url="/login?error=session", status_code=302)
    user = db.query(User).filter(User.id == int(tmp_user_id)).first()
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    valid = False
    if method == "totp":
        import pyotp
        totp = pyotp.TOTP(user.totp_secret)
        valid = totp.verify(code.strip())
    elif method == "email":
        if (user.two_fa_code and user.two_fa_code == code.strip() and
                user.two_fa_code_expires and user.two_fa_code_expires > now_berlin()):
            valid = True
            user.two_fa_code = None
            user.two_fa_code_expires = None
            db.commit()

    if not valid:
        return templates.TemplateResponse("2fa_verify.html", {
            "request": request, "method": method,
            "error": "Ungültiger Code. Bitte versuchen Sie es erneut."
        })

    access_token = create_access_token(data={"sub": str(user.id)})
    log_action(db, user.id, "LOGIN_2FA", f"2FA-Login: {user.email} ({method})")
    # Login aufzeichnen
    ua = request.headers.get("user-agent", "")[:200]
    db.add(UserLogin(
        user_id=user.id,
        ip_address=get_real_ip(request),
        user_agent=ua
    ))
    db.commit()
    response = RedirectResponse(url="/admin", status_code=302)
    response.set_cookie("access_token", access_token, httponly=True)
    response.delete_cookie("tmp_user_id")
    return response

@app.get("/admin/2fa", response_class=HTMLResponse)
async def admin_2fa_page(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    qr_data = None
    if not getattr(user, 'totp_secret', None):
        import pyotp
        user.totp_secret = pyotp.random_base32()
        db.commit()
    import pyotp
    totp_uri = pyotp.totp.TOTP(user.totp_secret).provisioning_uri(
        name=user.email, issuer_name="MP-Feuer-Ticketsystem"
    )
    return templates.TemplateResponse("admin_2fa.html", {
        "request": request, "user": user, "totp_uri": totp_uri
    })

@app.post("/admin/2fa/enable-totp")
async def enable_totp(request: Request, db: Session = Depends(get_db),
                      code: str = Form(...)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    import pyotp
    totp = pyotp.TOTP(user.totp_secret)
    if totp.verify(code.strip()):
        user.totp_enabled = True
        user.email_2fa_enabled = False
        db.commit()
        log_action(db, user.id, "2FA_ENABLE", "TOTP 2FA aktiviert")
        return templates.TemplateResponse("admin_2fa.html", {
            "request": request, "user": user,
            "totp_uri": pyotp.totp.TOTP(user.totp_secret).provisioning_uri(
                name=user.email, issuer_name="MP-Feuer-Ticketsystem"),
            "success": "TOTP 2FA erfolgreich aktiviert!"
        })
    import pyotp
    return templates.TemplateResponse("admin_2fa.html", {
        "request": request, "user": user,
        "totp_uri": pyotp.totp.TOTP(user.totp_secret).provisioning_uri(
            name=user.email, issuer_name="MP-Feuer-Ticketsystem"),
        "error": "Ungültiger Code – bitte erneut versuchen."
    })

@app.post("/admin/2fa/enable-email")
async def enable_email_2fa(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    user.email_2fa_enabled = True
    user.totp_enabled = False
    db.commit()
    log_action(db, user.id, "2FA_ENABLE", "E-Mail 2FA aktiviert")
    return RedirectResponse(url="/admin/2fa?success=email", status_code=302)

@app.post("/admin/2fa/disable")
async def disable_2fa(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    user.totp_enabled = False
    user.email_2fa_enabled = False
    db.commit()
    log_action(db, user.id, "2FA_DISABLE", "2FA deaktiviert")
    return RedirectResponse(url="/admin/2fa?success=disabled", status_code=302)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, db: Session = Depends(get_db),
                   name: str = Form(...), email: str = Form(...),
                   password: str = Form(...), password2: str = Form(...),
                   feuerwehr: str = Form(...),
                   loeschbezirk: str = Form(...), telefon: str = Form(...),
                   funktion: str = Form(...)):
    if password != password2:
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "Die Passwörter stimmen nicht überein."
        })
    if len(password) < 8:
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "Das Passwort muss mindestens 8 Zeichen lang sein."
        })
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "E-Mail bereits registriert"
        })
    user = User(name=name, email=email,
                hashed_password=get_password_hash(password),
                feuerwehr=feuerwehr, loeschbezirk=loeschbezirk,
                telefon=telefon, funktion=funktion,
                is_verified=False,
                verification_token=secrets.token_urlsafe(32))
    db.add(user)
    db.commit()
    db.refresh(user)
    send_new_registration_email(user)
    send_verification_email(user, user.verification_token)
    return RedirectResponse(url="/login?verify=1", status_code=302)

# ─── CUSTOMER PORTAL ────────────────────────────────────────────
@app.get("/portal", response_class=HTMLResponse)
async def portal(request: Request, db: Session = Depends(get_db),
                 sort: Optional[str] = "created_at",
                 order: Optional[str] = "desc",
                 search: Optional[str] = None):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    sort_map = {
        "created_at": Ticket.created_at,
        "updated_at": Ticket.updated_at,
        "title": Ticket.title,
        "status": Ticket.status,
        "priority": Ticket.priority,
    }
    sort_col = sort_map.get(sort, Ticket.created_at)
    query = db.query(Ticket).filter(Ticket.user_id == user.id)
    if search:
        query = query.filter(
            Ticket.title.ilike(f"%{search}%") |
            Ticket.description.ilike(f"%{search}%") |
            Ticket.tags.ilike(f"%{search}%")
        )
    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())
    tickets = query.all()
    return templates.TemplateResponse("portal.html", {
        "request": request, "user": user, "tickets": tickets,
        "sort": sort, "order": order, "search": search or ""
    })

@app.get("/portal/new", response_class=HTMLResponse)
async def new_ticket_page(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    templates_list = db.query(UserTemplate).filter(
        UserTemplate.is_active == True
    ).order_by(UserTemplate.title).all()
    return templates.TemplateResponse("new_ticket.html", {
        "request": request, "user": user,
        "priorities": TicketPriority, "statuses": TicketStatus,
        "user_templates": templates_list
    })

@app.post("/portal/new")
async def create_ticket(request: Request, db: Session = Depends(get_db),
                        title: str = Form(...), description: str = Form(...),
                        priority: str = Form(...),
                        files: List[UploadFile] = File(default=[])):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    # Fortlaufende Ticket-Nummer vergeben
    seq = db.query(TicketSequence).first()
    if not seq:
        seq = TicketSequence(last_number=0)
        db.add(seq)
        db.flush()
    seq.last_number += 1
    ticket = Ticket(
        title=title, description=description,
        priority=TicketPriority(priority),
        user_id=user.id,
        ticket_number_seq=seq.last_number
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    # Dateien speichern
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', '.txt', '.zip'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    for file in files:
        if file.filename:
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue  # Unerlaubte Dateitypen überspringen
            contents = await file.read()
            if len(contents) > MAX_FILE_SIZE:
                continue  # Zu große Dateien überspringen
            import re
            safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', file.filename)
            filename = f"ticket_{ticket.id}_{int(time.time())}_{safe_filename}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(contents)
            attachment = TicketAttachment(
                filename=file.filename,
                filepath=filename,
                ticket_id=ticket.id
            )
            db.add(attachment)
    db.commit()
    send_ticket_created_email(user.email, user.name, ticket)
    send_new_ticket_admin_email(user, ticket)
    send_push_to_admins(db,
        title=f"Neues Ticket #{ticket.ticket_number}",
        body=f"{user.name} ({user.feuerwehr}): {ticket.title}",
        url=f"/admin/ticket/{ticket.id}"
    )
    return RedirectResponse(url=f"/portal/ticket/{ticket.id}", status_code=302)

@app.get("/portal/ticket/{ticket_id}", response_class=HTMLResponse)
async def view_ticket(request: Request, ticket_id: int,
                      db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id, Ticket.user_id == user.id
    ).first()
    if not ticket:
        raise HTTPException(status_code=404)
    # Als gelesen markieren wenn Nutzer Ticket öffnet
    if not ticket.last_admin_reply_read:
        ticket.last_admin_reply_read = True
        db.commit()
    comments = db.query(Comment).filter(Comment.ticket_id == ticket_id)\
                 .order_by(Comment.created_at.desc()).all()
    return templates.TemplateResponse("ticket_detail.html", {
        "request": request, "user": user,
        "ticket": ticket, "comments": comments
    })

@app.post("/portal/ticket/{ticket_id}/reopen")
async def reopen_ticket(request: Request, ticket_id: int,
                        db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id, Ticket.user_id == user.id
    ).first()
    if not ticket:
        raise HTTPException(status_code=404)
    old_status = ticket.status.value
    ticket.status = TicketStatus.open
    ticket.updated_at = now_berlin()
    ticket.last_user_activity = now_berlin()
    db.add(TicketHistory(ticket_id=ticket_id, changed_by_id=user.id,
                         field="Status", old_value=old_status,
                         new_value="open"))
    db.commit()
    try:
        send_user_reopened_ticket_email(ticket, user)
    except Exception:
        pass
    return RedirectResponse(url=f"/portal/ticket/{ticket_id}", status_code=302)
async def close_ticket_customer(request: Request, ticket_id: int,
                                db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id, Ticket.user_id == user.id
    ).first()
    if not ticket:
        raise HTTPException(status_code=404)
    old_status = ticket.status.value
    ticket.status = TicketStatus.closed
    ticket.updated_at = now_berlin()
    db.add(TicketHistory(ticket_id=ticket_id, changed_by_id=user.id,
                         field="Status", old_value=old_status,
                         new_value="closed"))
    db.commit()
    # Admin benachrichtigen
    try:
        send_user_closed_ticket_email(ticket, user)
    except Exception:
        pass
    return RedirectResponse(url=f"/portal/ticket/{ticket_id}", status_code=302)

@app.post("/portal/ticket/{ticket_id}/comment")
async def add_comment_customer(request: Request, ticket_id: int,
                               db: Session = Depends(get_db),
                               content: str = Form(...)):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id, Ticket.user_id == user.id
    ).first()
    if not ticket:
        raise HTTPException(status_code=404)
    comment = Comment(content=content, ticket_id=ticket_id,
                      user_id=user.id, is_admin=False)
    db.add(comment)
    ticket.last_user_activity = now_berlin()
    ticket.updated_at = now_berlin()
    db.commit()
    send_user_comment_admin_email(user, ticket, content)
    send_push_to_admins(db,
        title=f"Neue Antwort: Ticket #{ticket.ticket_number}",
        body=f"{user.name} ({user.feuerwehr}): {content[:80]}",
        url=f"/admin/ticket/{ticket.id}"
    )
    return RedirectResponse(url=f"/portal/ticket/{ticket_id}", status_code=302)

# ─── ADMIN PANEL ─────────────────────────────────────────────────
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db),
                          status_filter: Optional[str] = None,
                          priority_filter: Optional[str] = None,
                          sort: Optional[str] = "status",
                          order: Optional[str] = "asc",
                          search: Optional[str] = None,
                          tag_filter: Optional[str] = None):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    query = db.query(Ticket)
    if status_filter:
        query = query.filter(Ticket.status == TicketStatus(status_filter))
    if priority_filter:
        query = query.filter(Ticket.priority == TicketPriority(priority_filter))
    if search:
        query = query.join(User).filter(
            Ticket.title.ilike(f"%{search}%") |
            Ticket.description.ilike(f"%{search}%") |
            User.name.ilike(f"%{search}%") |
            User.feuerwehr.ilike(f"%{search}%")
        )
    if tag_filter:
        # Exakte Tag-Suche: sucht nur in Tags-Feld nach exaktem Match
        query = query.filter(
            Ticket.tags.ilike(f"%{tag_filter}%")
        )
    # Sortierung
    sort_map = {
        "created_at": Ticket.created_at,
        "updated_at": Ticket.updated_at,
        "title": Ticket.title,
        "status": Ticket.status,
        "priority": Ticket.priority,
    }
    sort_col = sort_map.get(sort, Ticket.created_at)
    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())
    tickets = query.all()
    tickets = query.order_by(Ticket.created_at.desc()).all()

    # Unbeantwortet: letzter Kommentar ist vom Nutzer (nicht Admin)
    all_tickets = db.query(Ticket).filter(
        Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])
    ).all()
    unanswered = []
    for t in all_tickets:
        if t.comments:
            last_comment = sorted(t.comments, key=lambda c: c.created_at)[-1]
            if not last_comment.is_admin:
                unanswered.append(t)
        else:
            # Neues Ticket ohne Kommentare = immer unbeantwortet
            unanswered.append(t)

    # Online-Nutzer (aktiv in den letzten 15 Minuten)
    online_cutoff = now_berlin() - timedelta(minutes=15)
    online_users = db.query(User).filter(
        User.last_seen >= online_cutoff,
        User.is_admin == False
    ).order_by(User.last_seen.desc()).all()

    stats = {
        "total": db.query(Ticket).count(),
        "open": db.query(Ticket).filter(Ticket.status == TicketStatus.open).count(),
        "in_progress": db.query(Ticket).filter(Ticket.status == TicketStatus.in_progress).count(),
        "resolved": db.query(Ticket).filter(Ticket.status == TicketStatus.resolved).count(),
        "unanswered": len(unanswered),
    }
    # Offene Aufgaben
    open_tasks = db.query(AdminTask).filter(AdminTask.is_done == False)\
                   .order_by(AdminTask.due_date.asc().nullslast()).limit(5).all()
    overdue_tasks_count = db.query(AdminTask).filter(
        AdminTask.is_done == False,
        AdminTask.due_date < now_berlin()
    ).count()

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, "user": user, "tickets": tickets,
        "stats": stats, "statuses": TicketStatus, "priorities": TicketPriority,
        "status_filter": status_filter, "priority_filter": priority_filter,
        "unanswered_tickets": unanswered,
        "online_users": online_users,
        "sort": sort, "order": order,
        "open_tasks": open_tasks,
        "overdue_tasks_count": overdue_tasks_count,
        "now_berlin": now_berlin(),
        "search": search or "",
        "tag_filter": tag_filter or ""
    })

@app.get("/sw.js")
async def service_worker():
    return FileResponse("/opt/ticketsystem/static/sw.js", media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/"})

@app.get("/push/vapid-public-key")
async def vapid_public_key():
    import json as _j
    from fastapi.responses import JSONResponse
    keys = _j.load(open('/opt/ticketsystem/vapid_keys.json'))
    return JSONResponse({"public_key": keys['public_key']})

@app.post("/push/subscribe")
async def push_subscribe(request: Request, db: Session = Depends(get_db)):
    from fastapi.responses import JSONResponse
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"ok": False}, status_code=401)
    data = await request.json()
    endpoint = data.get("endpoint", "")
    p256dh = data.get("keys", {}).get("p256dh", "")
    auth = data.get("keys", {}).get("auth", "")
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    if existing:
        existing.p256dh = p256dh
        existing.auth = auth
    else:
        db.add(PushSubscription(user_id=user.id, endpoint=endpoint, p256dh=p256dh, auth=auth))
    db.commit()
    return JSONResponse({"ok": True})

@app.post("/push/unsubscribe")
async def push_unsubscribe(request: Request, db: Session = Depends(get_db)):
    from fastapi.responses import JSONResponse
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"ok": False}, status_code=401)
    data = await request.json()
    sub = db.query(PushSubscription).filter(PushSubscription.endpoint == data.get("endpoint", "")).first()
    if sub:
        db.delete(sub)
        db.commit()
    return JSONResponse({"ok": True})

@app.get("/admin/stats-live")
async def admin_stats_live(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        from fastapi.responses import Response
        return Response(status_code=403)

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                total = db.query(Ticket).count()
                open_c = db.query(Ticket).filter(Ticket.status == TicketStatus.open).count()
                in_prog = db.query(Ticket).filter(Ticket.status == TicketStatus.in_progress).count()
                resolved = db.query(Ticket).filter(Ticket.status == TicketStatus.resolved).count()
                active_tickets = db.query(Ticket).filter(
                    Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])
                ).all()
                unanswered = 0
                for t in active_tickets:
                    if t.comments:
                        last = sorted(t.comments, key=lambda c: c.created_at)[-1]
                        if not last.is_admin:
                            unanswered += 1
                    else:
                        unanswered += 1
                import json
                data = json.dumps({
                    "total": total, "open": open_c,
                    "in_progress": in_prog, "resolved": resolved,
                    "unanswered": unanswered
                })
                yield ("data: " + data + chr(10) + chr(10))
            except Exception:
                break
            await asyncio.sleep(15)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.get("/admin/ticket/{ticket_id}", response_class=HTMLResponse)
async def admin_view_ticket(request: Request, ticket_id: int,
                            db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404)
    comments = db.query(Comment).filter(Comment.ticket_id == ticket_id)\
                 .order_by(Comment.created_at.desc()).all()
    reply_templates = db.query(ReplyTemplate).order_by(ReplyTemplate.title).all()
    all_tickets = db.query(Ticket).filter(Ticket.id != ticket_id)\
                    .order_by(Ticket.created_at.desc()).all()
    return templates.TemplateResponse("admin_ticket.html", {
        "request": request, "user": user, "ticket": ticket,
        "comments": comments, "statuses": TicketStatus, "priorities": TicketPriority,
        "reply_templates": reply_templates, "edit_comment": None,
        "all_tickets": all_tickets
    })

@app.post("/admin/ticket/{ticket_id}/comment/{comment_id}/delete")
async def admin_delete_comment(request: Request, ticket_id: int, comment_id: int,
                               db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    comment = db.query(Comment).filter(
        Comment.id == comment_id, Comment.ticket_id == ticket_id
    ).first()
    if comment:
        log_action(db, user.id, "COMMENT_DELETE",
                   f"Kommentar gelöscht in Ticket {ticket_id}")
        db.delete(comment)
        db.commit()
    return RedirectResponse(url=f"/admin/ticket/{ticket_id}", status_code=302)

@app.get("/admin/ticket/{ticket_id}/comment/{comment_id}/edit", response_class=HTMLResponse)
async def admin_edit_comment_page(request: Request, ticket_id: int, comment_id: int,
                                  db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    comment = db.query(Comment).filter(
        Comment.id == comment_id, Comment.ticket_id == ticket_id
    ).first()
    if not ticket or not comment:
        raise HTTPException(status_code=404)
    comments = db.query(Comment).filter(Comment.ticket_id == ticket_id)\
                 .order_by(Comment.created_at.desc()).all()
    reply_templates = db.query(ReplyTemplate).order_by(ReplyTemplate.title).all()
    all_tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).all()
    return templates.TemplateResponse("admin_ticket.html", {
        "request": request, "user": user, "ticket": ticket,
        "comments": comments, "statuses": TicketStatus, "priorities": TicketPriority,
        "reply_templates": reply_templates, "edit_comment": comment,
        "all_tickets": all_tickets
    })

@app.post("/admin/ticket/{ticket_id}/comment/{comment_id}/edit")
async def admin_edit_comment(request: Request, ticket_id: int, comment_id: int,
                             db: Session = Depends(get_db),
                             content: str = Form(...)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    comment = db.query(Comment).filter(
        Comment.id == comment_id, Comment.ticket_id == ticket_id
    ).first()
    if comment:
        comment.content = content
        db.commit()
        log_action(db, user.id, "COMMENT_EDIT",
                   f"Kommentar bearbeitet in Ticket {ticket_id}")
    return RedirectResponse(url=f"/admin/ticket/{ticket_id}", status_code=302)

@app.post("/admin/ticket/{ticket_id}/link")
async def admin_link_ticket(request: Request, ticket_id: int,
                            db: Session = Depends(get_db),
                            related_id: str = Form(default="")):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket:
        ticket.related_ticket_id = int(related_id) if related_id else None
        db.commit()
        log_action(db, user.id, "TICKET_LINK",
                   f"Ticket {ticket.ticket_number} verknüpft mit ID {related_id}")
    return RedirectResponse(url=f"/admin/ticket/{ticket_id}", status_code=302)

@app.post("/admin/ticket/{ticket_id}/attachment/{attachment_id}/delete")
async def admin_delete_attachment(request: Request, ticket_id: int, attachment_id: int,
                                  db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    attachment = db.query(TicketAttachment).filter(
        TicketAttachment.id == attachment_id,
        TicketAttachment.ticket_id == ticket_id
    ).first()
    if attachment:
        import os
        filepath = os.path.join(UPLOAD_DIR, attachment.filepath) if not attachment.filepath.startswith('/') else attachment.filepath
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
        log_action(db, user.id, "ATTACHMENT_DELETE",
                   f"Anhang '{attachment.filename}' aus Ticket {ticket_id} gelöscht")
        db.delete(attachment)
        db.commit()
    return RedirectResponse(url=f"/admin/ticket/{ticket_id}", status_code=302)

@app.post("/admin/ticket/{ticket_id}/create-task")
async def create_task_from_ticket(request: Request, ticket_id: int,
                                  db: Session = Depends(get_db),
                                  title: str = Form(...),
                                  description: str = Form(default=""),
                                  priority: str = Form(default="medium")):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404)
    task = AdminTask(
        title=title,
        description=description,
        priority=TicketPriority(priority),
        created_by_id=user.id
    )
    db.add(task)
    db.commit()
    log_action(db, user.id, "TASK_CREATE_FROM_TICKET",
               f"Aufgabe '{title}' aus Ticket {ticket.ticket_number} erstellt")
    return RedirectResponse(url=f"/admin/ticket/{ticket_id}?success=task", status_code=302)

@app.post("/admin/ticket/{ticket_id}/star")
async def toggle_star(request: Request, ticket_id: int, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket:
        ticket.is_starred = not ticket.is_starred
        db.commit()
    return RedirectResponse(url=f"/admin/ticket/{ticket_id}", status_code=302)

@app.post("/admin/ticket/{ticket_id}/tags")
async def update_tags(request: Request, ticket_id: int, db: Session = Depends(get_db),
                      tags: str = Form(default="")):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket:
        ticket.tags = tags.strip()
        db.commit()
    return RedirectResponse(url=f"/admin/ticket/{ticket_id}", status_code=302)

@app.post("/portal/profil/avatar")
async def upload_avatar(request: Request, db: Session = Depends(get_db),
                        avatar: UploadFile = File(...)):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if avatar.filename:
        ext = os.path.splitext(avatar.filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            contents = await avatar.read()
            if len(contents) <= 2 * 1024 * 1024:  # Max 2MB
                import re
                filename = f"avatar_{user.id}{ext}"
                filepath = os.path.join(UPLOAD_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(contents)
                user.avatar = filename
                db.commit()
    return RedirectResponse(url="/portal/profil?success=1", status_code=302)

@app.post("/admin/ticket/{ticket_id}/delete")
async def admin_delete_ticket(request: Request, ticket_id: int,
                              db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404)
    db.query(Comment).filter(Comment.ticket_id == ticket_id).delete()
    db.query(TicketHistory).filter(TicketHistory.ticket_id == ticket_id).delete()
    db.query(AdminNote).filter(AdminNote.ticket_id == ticket_id).delete()
    db.query(TicketAttachment).filter(TicketAttachment.ticket_id == ticket_id).delete()
    db.delete(ticket)
    db.commit()
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/ticket/{ticket_id}/update")
async def admin_update_ticket(request: Request, ticket_id: int,
                              db: Session = Depends(get_db),
                              status: str = Form(...),
                              priority: str = Form(...)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404)
    old_status = ticket.status
    old_priority = ticket.priority
    ticket.status = TicketStatus(status)
    ticket.priority = TicketPriority(priority)
    ticket.updated_at = now_berlin()
    ticket.last_user_activity = now_berlin()  # Zeitstempel in Aktivität-Spalte
    # Lösungszeit erfassen
    if ticket.status == TicketStatus.resolved and old_status != TicketStatus.resolved:
        ticket.resolved_at = now_berlin()
        if not ticket.first_response_at:
            ticket.first_response_at = now_berlin()  # Falls noch keine Antwort
    # History aufzeichnen
    if old_status != ticket.status:
        db.add(TicketHistory(ticket_id=ticket_id, changed_by_id=user.id,
                             field="Status", old_value=old_status.value,
                             new_value=ticket.status.value))
    if old_priority != ticket.priority:
        db.add(TicketHistory(ticket_id=ticket_id, changed_by_id=user.id,
                             field="Priorität", old_value=old_priority.value,
                             new_value=ticket.priority.value))
    db.commit()
    log_action(db, user.id, "TICKET_UPDATE", 
               f"Ticket {ticket.ticket_number}: Status={status}, Priorität={priority}")
    if old_status != ticket.status:
        customer = db.query(User).filter(User.id == ticket.user_id).first()
        if customer:
            send_ticket_updated_email(customer.email, customer.name, ticket)
    return RedirectResponse(url=f"/admin/ticket/{ticket_id}", status_code=302)

@app.post("/admin/ticket/{ticket_id}/comment")
async def admin_add_comment(request: Request, ticket_id: int,
                            db: Session = Depends(get_db),
                            content: str = Form(...)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404)
    comment = Comment(content=content, ticket_id=ticket_id,
                      user_id=user.id, is_admin=True)
    db.add(comment)
    # Erste Reaktionszeit erfassen
    if not ticket.first_response_at:
        ticket.first_response_at = now_berlin()
    ticket.updated_at = now_berlin()
    ticket.last_admin_reply_read = False  # Nutzer hat noch nicht gelesen
    db.commit()
    customer = db.query(User).filter(User.id == ticket.user_id).first()
    if customer:
        send_ticket_updated_email(customer.email, customer.name, ticket,
                                  comment_added=True, comment_content=content,
                                  sachbearbeiter=user.name)
    log_action(db, user.id, "TICKET_COMMENT", f"Kommentar zu Ticket {ticket.ticket_number}")
    return RedirectResponse(url=f"/admin/ticket/{ticket_id}", status_code=302)

@app.get("/admin/users/{user_id}/edit", response_class=HTMLResponse)
async def admin_edit_user_page(request: Request, user_id: int,
                               db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    edit_user = db.query(User).filter(User.id == user_id).first()
    if not edit_user:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("admin_edit_user.html", {
        "request": request, "user": user, "edit_user": edit_user
    })

@app.post("/admin/users/{user_id}/edit")
async def admin_edit_user(request: Request, user_id: int,
                          db: Session = Depends(get_db),
                          name: str = Form(...), email: str = Form(...),
                          telefon: str = Form(default=""),
                          feuerwehr: str = Form(default=""),
                          loeschbezirk: str = Form(default=""),
                          funktion: str = Form(default=""),
                          is_admin: str = Form(default=""),
                          is_verified: str = Form(default=""),
                          password: str = Form(default=""),
                          admin_note: str = Form(default="")):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    edit_user = db.query(User).filter(User.id == user_id).first()
    if not edit_user:
        raise HTTPException(status_code=404)
    edit_user.name = name
    edit_user.email = email
    edit_user.telefon = telefon
    edit_user.feuerwehr = feuerwehr
    edit_user.loeschbezirk = loeschbezirk
    edit_user.funktion = funktion
    edit_user.is_admin = bool(is_admin)
    edit_user.is_verified = bool(is_verified)
    edit_user.admin_note = admin_note
    if password:
        edit_user.hashed_password = get_password_hash(password)
    db.commit()
    return templates.TemplateResponse("admin_edit_user.html", {
        "request": request, "user": user, "edit_user": edit_user,
        "success": "Nutzer erfolgreich gespeichert!"
    })

@app.get("/admin/users/{user_id}/activity", response_class=HTMLResponse)
async def admin_user_activity(request: Request, user_id: int,
                              db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404)
    logins = db.query(UserLogin).filter(UserLogin.user_id == user_id)\
               .order_by(UserLogin.logged_in_at.desc()).limit(50).all()
    total_logins = db.query(UserLogin).filter(UserLogin.user_id == user_id).count()
    tickets = db.query(Ticket).filter(Ticket.user_id == user_id)\
                .order_by(Ticket.created_at.desc()).all()
    comments = db.query(Comment).filter(Comment.user_id == user_id).count()
    # Online-Zeit schätzen: last_seen - letzter Login
    online_minutes = None
    if target.last_seen and logins:
        last_login = logins[0].logged_in_at
        diff = (target.last_seen - last_login).total_seconds() / 60
        if 0 < diff < 480:  # Max 8 Stunden
            online_minutes = round(diff)
    return templates.TemplateResponse("admin_user_activity.html", {
        "request": request, "user": user, "target": target,
        "logins": logins, "total_logins": total_logins,
        "tickets": tickets, "comments": comments,
        "online_minutes": online_minutes
    })

@app.post("/admin/users/{user_id}/reset-password")
async def admin_reset_password(request: Request, user_id: int,
                               db: Session = Depends(get_db),
                               new_password: str = Form(...)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404)
    if len(new_password) < 8:
        return RedirectResponse(url=f"/admin/users/{user_id}/edit?error=Passwort+zu+kurz", status_code=302)
    target.hashed_password = get_password_hash(new_password)
    db.commit()
    log_action(db, user.id, "ADMIN_RESET_PASSWORD",
               f"Passwort von {target.name} ({target.email}) zurückgesetzt")
    return RedirectResponse(url=f"/admin/users/{user_id}/edit?success=Passwort+gesetzt", status_code=302)

@app.post("/admin/users/{user_id}/toggle-active")
async def admin_toggle_active(request: Request, user_id: int,
                              db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    target = db.query(User).filter(User.id == user_id).first()
    if target and not target.is_admin:
        target.is_active = not getattr(target, 'is_active', True)
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)

@app.get("/admin/bulk-mail", response_class=HTMLResponse)
async def admin_bulk_mail_page(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    users = db.query(User).filter(User.is_verified == True).all()
    return templates.TemplateResponse("admin_bulk_mail.html", {
        "request": request, "user": user, "users": users
    })

@app.post("/admin/bulk-mail")
async def admin_bulk_mail_send(request: Request, db: Session = Depends(get_db),
                               subject: str = Form(...),
                               message: str = Form(...),
                               user_ids: List[str] = Form(default=[])):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    if user_ids:
        id_list = [int(i) for i in user_ids if i.isdigit()]
        users = db.query(User).filter(User.id.in_(id_list), User.is_verified == True).all()
    else:
        users = db.query(User).filter(User.is_verified == True, User.is_admin == False).all()
    sent = 0
    for u in users:
        try:
            from email_utils import _send, APP_URL
            html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
              <h2 style="color:#3b82f6;">📢 Mitteilung vom Admin</h2>
              <p>Hallo {u.name},</p>
              <div style="background:#f1f5f9;padding:16px;border-radius:8px;margin:16px 0;white-space:pre-line;">{message}</div>
              <p style="font-size:0.85rem;color:#666;">Gesendet von: {user.name} · MP-Feuer-Ticketsystem</p>
              <a href="{APP_URL}/portal" style="display:inline-block;padding:10px 20px;background:#3b82f6;color:#fff;text-decoration:none;border-radius:6px;">Portal öffnen</a>
            </div>"""
            _send(u.email, subject, html)
            sent += 1
        except:
            pass
    return templates.TemplateResponse("admin_bulk_mail.html", {
        "request": request, "user": user,
        "users": db.query(User).filter(User.is_verified == True).all(),
        "success": f"E-Mail erfolgreich an {sent} Nutzer gesendet!"
    })

@app.post("/admin/users/{user_id}/verify")
async def admin_verify_user(request: Request, user_id: int,
                            db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404)
    target.is_verified = True
    target.verification_token = None
    db.commit()
    send_registration_confirmation_email(target)
    return RedirectResponse(url="/admin/users", status_code=302)

@app.post("/admin/users/{user_id}/delete")
async def admin_delete_user(request: Request, user_id: int,
                            db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    target = db.query(User).filter(User.id == user_id).first()
    if not target or target.is_admin:
        raise HTTPException(status_code=403, detail="Nicht erlaubt")
    # Kommentare und Tickets des Nutzers auch löschen
    for ticket in target.tickets:
        db.query(Comment).filter(Comment.ticket_id == ticket.id).delete()
    db.query(Ticket).filter(Ticket.user_id == user_id).delete()
    db.query(Comment).filter(Comment.user_id == user_id).delete()
    db.delete(target)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(get_db),
                      sort: Optional[str] = "created_at",
                      order: Optional[str] = "desc"):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    sort_map = {
        "name": User.name,
        "email": User.email,
        "feuerwehr": User.feuerwehr,
        "created_at": User.created_at,
    }
    sort_col = sort_map.get(sort, User.created_at)
    if order == "asc":
        users = db.query(User).order_by(sort_col.asc()).all()
    else:
        users = db.query(User).order_by(sort_col.desc()).all()
    return templates.TemplateResponse("admin_users.html", {
        "request": request, "user": user, "users": users,
        "sort": sort, "order": order
    })

@app.get("/admin/stats", response_class=HTMLResponse)
async def admin_stats(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    from sqlalchemy import func
    # Tickets pro Status
    status_counts = {s.value: db.query(Ticket).filter(Ticket.status == s).count() for s in TicketStatus}
    # Tickets pro Priorität
    priority_counts = {p.value: db.query(Ticket).filter(Ticket.priority == p).count() for p in TicketPriority}
    # Tickets pro Tag (letzte 30 Tage)
    tickets_per_day = []
    for i in range(29, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59)
        count = db.query(Ticket).filter(
            Ticket.created_at >= day_start,
            Ticket.created_at <= day_end
        ).count()
        tickets_per_day.append({"date": day.strftime("%d.%m"), "count": count})
    # Überfällige Tickets (älter als 5 Tage, noch offen)
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=5)
    overdue = db.query(Ticket).filter(
        Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress]),
        Ticket.updated_at < cutoff
    ).count()
    total = db.query(Ticket).count()
    users_count = db.query(User).filter(User.is_admin == False).count()

    # Reaktionszeiten berechnen
    tickets_with_response = db.query(Ticket).filter(
        Ticket.first_response_at != None
    ).all()
    tickets_resolved = db.query(Ticket).filter(
        Ticket.resolved_at != None
    ).all()

    avg_response_hours = None
    avg_resolve_hours = None
    if tickets_with_response:
        total_hours = sum(
            (t.first_response_at - t.created_at).total_seconds() / 3600
            for t in tickets_with_response
            if t.first_response_at and t.created_at and t.first_response_at > t.created_at
        )
        count = len([t for t in tickets_with_response if t.first_response_at and t.created_at and t.first_response_at > t.created_at])
        if count > 0:
            avg_response_hours = round(total_hours / count, 1)
    if tickets_resolved:
        total_hours = sum(
            (t.resolved_at - t.created_at).total_seconds() / 3600
            for t in tickets_resolved
            if t.resolved_at and t.created_at and t.resolved_at > t.created_at
        )
        count = len([t for t in tickets_resolved if t.resolved_at and t.created_at and t.resolved_at > t.created_at])
        if count > 0:
            avg_resolve_hours = round(total_hours / count, 1)

    # Reaktionszeiten pro Monat (letzte 6 Monate)
    monthly_stats = []
    for i in range(5, -1, -1):
        month_start = (datetime.now() - timedelta(days=i*30)).replace(day=1, hour=0, minute=0, second=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        month_tickets = db.query(Ticket).filter(
            Ticket.created_at >= month_start,
            Ticket.created_at < month_end,
            Ticket.first_response_at != None
        ).all()
        if month_tickets:
            avg = sum((t.first_response_at - t.created_at).total_seconds() / 3600 for t in month_tickets) / len(month_tickets)
        else:
            avg = 0
        monthly_stats.append({
            "month": month_start.strftime("%b %Y"),
            "avg_hours": round(avg, 1),
            "count": len(month_tickets)
        })
    # Tickets pro Gemeinde
    gemeinden = ['Dillingen','Lebach','Saarlouis','Bous','Ensdorf','Nalbach',
                 'Rehlingen-Siersburg','Saarwellingen','Schmelz','Schwalbach',
                 'Wadgassen','Wallerfangen','Überherrn']
    gemeinde_stats = []
    for g in gemeinden:
        count = db.query(Ticket).join(User).filter(User.feuerwehr == g).count()
        if count > 0:
            gemeinde_stats.append({"name": g, "count": count})
    gemeinde_stats.sort(key=lambda x: x["count"], reverse=True)

    # Statistik pro Nutzer
    all_users = db.query(User).filter(User.is_admin == False, User.is_active == True).all()
    user_stats = []
    for u in all_users:
        total_u = db.query(Ticket).filter(Ticket.user_id == u.id).count()
        if total_u == 0:
            continue
        open_u = db.query(Ticket).filter(Ticket.user_id == u.id,
            Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])).count()
        resolved_u = db.query(Ticket).filter(Ticket.user_id == u.id,
            Ticket.status.in_([TicketStatus.resolved, TicketStatus.closed])).count()
        logins_u = db.query(UserLogin).filter(UserLogin.user_id == u.id).count()
        last_login_u = db.query(UserLogin).filter(UserLogin.user_id == u.id)\
                         .order_by(UserLogin.logged_in_at.desc()).first()
        user_stats.append({
            "id": u.id,
            "name": u.name, "feuerwehr": u.feuerwehr or "–",
            "total": total_u, "open": open_u, "resolved": resolved_u,
            "logins": logins_u,
            "last_login": last_login_u.logged_in_at.strftime('%d.%m.%Y %H:%M') if last_login_u else "–",
            "last_seen": u.last_seen.strftime('%d.%m. %H:%M') if u.last_seen else "–"
        })
    user_stats.sort(key=lambda x: x["total"], reverse=True)

    return templates.TemplateResponse("admin_stats.html", {
        "request": request, "user": user,
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "tickets_per_day": tickets_per_day,
        "overdue": overdue, "total": total,
        "users_count": users_count,
        "avg_response_hours": avg_response_hours,
        "avg_resolve_hours": avg_resolve_hours,
        "monthly_stats": monthly_stats,
        "gemeinde_stats": gemeinde_stats,
        "user_stats": user_stats,
    })

# ─── PASSWORT VERGESSEN ──────────────────────────────────────────
@app.get("/impressum", response_class=HTMLResponse)
async def impressum(request: Request):
    user = None
    try:
        from database import SessionLocal
        db = SessionLocal()
        user = await get_current_user(request, db)
        db.close()
    except:
        pass
    return templates.TemplateResponse("impressum.html", {"request": request, "user": user})

@app.get("/datenschutz", response_class=HTMLResponse)
async def datenschutz(request: Request):
    user = None
    try:
        from database import SessionLocal
        db = SessionLocal()
        user = await get_current_user(request, db)
        db.close()
    except:
        pass
    return templates.TemplateResponse("datenschutz.html", {"request": request, "user": user})

# ─── E-MAIL VERIFIKATION ────────────────────────────────────────
@app.get("/verify-email/{token}", response_class=HTMLResponse)
async def verify_email(request: Request, token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Ungültiger oder abgelaufener Bestätigungslink."
        })
    user.is_verified = True
    user.verification_token = None
    db.commit()
    send_registration_confirmation_email(user)
    return RedirectResponse(url="/login?registered=1", status_code=302)

@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@app.post("/forgot-password")
async def forgot_password(request: Request, db: Session = Depends(get_db),
                          email: str = Form(...)):
    user = db.query(User).filter(User.email == email).first()
    if user:
        token = secrets.token_urlsafe(32)
        reset = PasswordResetToken(
            token=token, user_id=user.id,
            expires_at=now_berlin() + timedelta(hours=2)
        )
        db.add(reset)
        db.commit()
        send_password_reset_email(user.email, user.name, token)
    return templates.TemplateResponse("forgot_password.html", {
        "request": request,
        "success": "Falls die E-Mail registriert ist, wurde ein Reset-Link gesendet."
    })

@app.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str, db: Session = Depends(get_db)):
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > now_berlin()
    ).first()
    if not reset:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, "error": "Link ungültig oder abgelaufen."
        })
    return templates.TemplateResponse("reset_password.html", {
        "request": request, "token": token
    })

@app.post("/reset-password/{token}")
async def reset_password(request: Request, token: str, db: Session = Depends(get_db),
                         password: str = Form(...)):
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > now_berlin()
    ).first()
    if not reset:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, "error": "Link ungültig oder abgelaufen."
        })
    user = db.query(User).filter(User.id == reset.user_id).first()
    user.hashed_password = get_password_hash(password)
    reset.used = True
    db.commit()
    return RedirectResponse(url="/login?reset=1", status_code=302)

# ─── PROFIL BEARBEITEN ───────────────────────────────────────────
@app.get("/portal/profil", response_class=HTMLResponse)
async def profil_page(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    # Nutzer-Statistiken
    total_tickets = db.query(Ticket).filter(Ticket.user_id == user.id).count()
    open_tickets = db.query(Ticket).filter(
        Ticket.user_id == user.id,
        Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])
    ).count()
    resolved_tickets = db.query(Ticket).filter(
        Ticket.user_id == user.id,
        Ticket.status == TicketStatus.resolved
    ).count()
    return templates.TemplateResponse("profil.html", {
        "request": request, "user": user,
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "resolved_tickets": resolved_tickets
    })

@app.post("/portal/profil")
async def profil_update(request: Request, db: Session = Depends(get_db),
                        name: str = Form(...), telefon: str = Form(...),
                        funktion: str = Form(...), feuerwehr: str = Form(...),
                        loeschbezirk: str = Form(...),
                        new_email: str = Form(default=""),
                        password: str = Form(default=""),
                        password2: str = Form(default="")):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    user.name = name
    user.telefon = telefon
    user.funktion = funktion
    user.feuerwehr = feuerwehr
    user.loeschbezirk = loeschbezirk
    # E-Mail ändern
    if new_email and new_email != user.email:
        existing = db.query(User).filter(User.email == new_email, User.id != user.id).first()
        if existing:
            total_tickets = db.query(Ticket).filter(Ticket.user_id == user.id).count()
            open_tickets = db.query(Ticket).filter(Ticket.user_id == user.id,
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])).count()
            resolved_tickets = db.query(Ticket).filter(Ticket.user_id == user.id,
                Ticket.status == TicketStatus.resolved).count()
            return templates.TemplateResponse("profil.html", {
                "request": request, "user": user,
                "error": "Diese E-Mail-Adresse wird bereits verwendet.",
                "total_tickets": total_tickets, "open_tickets": open_tickets,
                "resolved_tickets": resolved_tickets
            })
        user.email = new_email
    # Passwort ändern
    if password:
        if password != password2:
            total_tickets = db.query(Ticket).filter(Ticket.user_id == user.id).count()
            open_tickets = db.query(Ticket).filter(Ticket.user_id == user.id,
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])).count()
            resolved_tickets = db.query(Ticket).filter(Ticket.user_id == user.id,
                Ticket.status == TicketStatus.resolved).count()
            return templates.TemplateResponse("profil.html", {
                "request": request, "user": user,
                "error": "Die Passwörter stimmen nicht überein.",
                "total_tickets": total_tickets, "open_tickets": open_tickets,
                "resolved_tickets": resolved_tickets
            })
        user.hashed_password = get_password_hash(password)
    db.commit()
    total_tickets = db.query(Ticket).filter(Ticket.user_id == user.id).count()
    open_tickets = db.query(Ticket).filter(Ticket.user_id == user.id,
        Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])).count()
    resolved_tickets = db.query(Ticket).filter(Ticket.user_id == user.id,
        Ticket.status == TicketStatus.resolved).count()
    return templates.TemplateResponse("profil.html", {
        "request": request, "user": user,
        "success": "Profil erfolgreich gespeichert!",
        "total_tickets": total_tickets, "open_tickets": open_tickets,
        "resolved_tickets": resolved_tickets
    })

# ─── ADMIN NOTIZEN ───────────────────────────────────────────────
@app.post("/admin/ticket/{ticket_id}/note")
async def admin_add_note(request: Request, ticket_id: int,
                         db: Session = Depends(get_db),
                         content: str = Form(...)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    note = AdminNote(content=content, ticket_id=ticket_id, admin_id=user.id)
    db.add(note)
    db.commit()
    return RedirectResponse(url=f"/admin/ticket/{ticket_id}", status_code=302)

# ─── PDF EXPORT ─────────────────────────────────────────────────
@app.get("/portal/ticket/{ticket_id}/pdf")
async def ticket_pdf_customer(request: Request, ticket_id: int,
                               db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id, Ticket.user_id == user.id
    ).first()
    if not ticket:
        raise HTTPException(status_code=404)
    comments = db.query(Comment).filter(Comment.ticket_id == ticket_id)\
                 .order_by(Comment.created_at.asc()).all()
    return _generate_ticket_pdf(ticket, comments)

@app.get("/admin/ticket/{ticket_id}/pdf")
async def ticket_pdf_admin(request: Request, ticket_id: int,
                            db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404)
    comments = db.query(Comment).filter(Comment.ticket_id == ticket_id)\
                 .order_by(Comment.created_at.asc()).all()
    return _generate_ticket_pdf(ticket, comments)

def _generate_ticket_pdf(ticket, comments):
    from fastapi.responses import Response
    comments_html = ""
    for c in comments:
        bg = "#e8f0fe" if c.is_admin else "#f5f5f5"
        author = f"Support-Team ({c.user.name})" if c.is_admin else f"{c.user.name}"
        comments_html += f"""
        <div style="background:{bg};border-left:4px solid {'#2563eb' if c.is_admin else '#ccc'};
                    padding:10px;margin:8px 0;border-radius:4px;">
          <div style="font-size:11px;color:#666;margin-bottom:4px;">
            {author} &middot; {c.created_at.strftime('%d.%m.%Y %H:%M')}
          </div>
          <p style="margin:0;">{c.content}</p>
        </div>"""
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; font-size: 13px; color: #333; margin: 40px; }}
  h1 {{ color: #2563eb; font-size: 20px; margin:0; }}
  .header {{ border-bottom: 2px solid #2563eb; padding-bottom: 10px; margin-bottom: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  td {{ padding: 8px; border-bottom: 1px solid #eee; }}
  td:first-child {{ font-weight: bold; width: 150px; background: #f8f9fa; }}
  .description {{ background: #f8f9fa; padding: 12px; border-radius: 4px; margin: 16px 0; white-space: pre-wrap; }}
  .footer {{ margin-top: 30px; font-size: 11px; color: #999; border-top: 1px solid #eee; padding-top: 10px; }}
</style>
</head><body>
<div class="header">
  <h1>MP-Feuer-Ticketsystem - Landkreis Saarlouis</h1>
  <h2 style="margin:4px 0;font-size:16px;">{ticket.ticket_number}: {ticket.title}</h2>
</div>
<table>
  <tr><td>Ticket-Nr.</td><td>{ticket.ticket_number}</td></tr>
  <tr><td>Status</td><td>{ticket.status_label}</td></tr>
  <tr><td>Prioritaet</td><td>{ticket.priority_label}</td></tr>
  <tr><td>Erstellt von</td><td>{ticket.user.name} ({ticket.user.email})</td></tr>
  <tr><td>Feuerwehr</td><td>{ticket.user.feuerwehr or '-'}</td></tr>
  <tr><td>Loeschbezirk</td><td>{ticket.user.loeschbezirk or '-'}</td></tr>
  <tr><td>Funktion</td><td>{ticket.user.funktion or '-'}</td></tr>
  <tr><td>Erstellt am</td><td>{ticket.created_at.strftime('%d.%m.%Y %H:%M')}</td></tr>
  <tr><td>Zuletzt geaendert</td><td>{ticket.updated_at.strftime('%d.%m.%Y %H:%M')}</td></tr>
</table>
<h3>Beschreibung</h3>
<div class="description">{ticket.description}</div>
<h3>Kommunikation ({len(comments)} Nachrichten)</h3>
{comments_html}
<div class="footer">Gedruckt am {datetime.now().strftime('%d.%m.%Y %H:%M')} - MP-Feuer-Ticketsystem des Landkreises Saarlouis</div>
</body></html>"""
    try:
        import weasyprint
        pdf = weasyprint.HTML(string=html).write_pdf()
        from fastapi.responses import Response
        return Response(content=pdf, media_type="application/pdf",
                       headers={"Content-Disposition": f"attachment; filename={ticket.ticket_number}.pdf"})
    except ImportError:
        from fastapi.responses import Response
        return Response(content=html + "<script>window.print()</script>",
                       media_type="text/html")

# ─── OEFFENTLICHE STATUSSEITE ────────────────────────────────────
@app.get("/status", response_class=HTMLResponse)
async def public_status(request: Request, db: Session = Depends(get_db)):
    """Öffentliche Statusseite – nur zeigt ob System online ist."""
    return templates.TemplateResponse("public_status.html", {
        "request": request,
        "now": now_berlin(),
    })

@app.get("/admin/search", response_class=HTMLResponse)
async def admin_global_search(request: Request, db: Session = Depends(get_db),
                              q: Optional[str] = None):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    results = {"tickets": [], "users": [], "tasks": []}
    if q and len(q.strip()) >= 2:
        q = q.strip()
        # Tickets
        results["tickets"] = db.query(Ticket).join(User).filter(
            Ticket.title.ilike(f"%{q}%") |
            Ticket.description.ilike(f"%{q}%") |
            Ticket.tags.ilike(f"%{q}%") |
            User.name.ilike(f"%{q}%") |
            User.feuerwehr.ilike(f"%{q}%")
        ).order_by(Ticket.created_at.desc()).limit(10).all()
        # Nutzer
        results["users"] = db.query(User).filter(
            User.name.ilike(f"%{q}%") |
            User.email.ilike(f"%{q}%") |
            User.feuerwehr.ilike(f"%{q}%") |
            User.funktion.ilike(f"%{q}%")
        ).limit(10).all()
        # Aufgaben
        results["tasks"] = db.query(AdminTask).filter(
            AdminTask.title.ilike(f"%{q}%") |
            AdminTask.description.ilike(f"%{q}%")
        ).order_by(AdminTask.created_at.desc()).limit(10).all()
    return templates.TemplateResponse("admin_search.html", {
        "request": request, "user": user, "q": q or "",
        "results": results,
        "total": len(results["tickets"]) + len(results["users"]) + len(results["tasks"])
    })

@app.get("/admin/status", response_class=HTMLResponse)
async def admin_status(request: Request, db: Session = Depends(get_db)):
    """Detaillierte Systeminfo – nur für Admins."""
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    import os, time, glob
    stats = {
        "open": db.query(Ticket).filter(Ticket.status == TicketStatus.open).count(),
        "in_progress": db.query(Ticket).filter(Ticket.status == TicketStatus.in_progress).count(),
        "resolved": db.query(Ticket).filter(Ticket.status == TicketStatus.resolved).count(),
        "total": db.query(Ticket).count(),
        "users": db.query(User).filter(User.is_active == True).count(),
    }
    db_path = "/opt/ticketsystem/tickets.db"
    db_size_kb = round(os.path.getsize(db_path) / 1024, 1) if os.path.exists(db_path) else 0
    uploads_size = 0
    uploads_dir = "/opt/ticketsystem/uploads"
    if os.path.exists(uploads_dir):
        for f in os.listdir(uploads_dir):
            fp = os.path.join(uploads_dir, f)
            if os.path.isfile(fp):
                uploads_size += os.path.getsize(fp)
    uploads_size_mb = round(uploads_size / 1024 / 1024, 1)
    try:
        with open("/proc/uptime") as f:
            uptime_sec = float(f.read().split()[0])
        uptime_days = int(uptime_sec // 86400)
        uptime_hours = int((uptime_sec % 86400) // 3600)
        uptime_str = f"{uptime_days}d {uptime_hours}h"
    except Exception:
        uptime_str = "–"
    last_ticket = db.query(Ticket).order_by(Ticket.created_at.desc()).first()
    last_comment = db.query(Comment).order_by(Comment.created_at.desc()).first()
    backup_files = sorted(glob.glob("/opt/ticketsystem/backups/*.db"), reverse=True)
    last_backup = None
    backup_ok = False
    if backup_files:
        mtime = os.path.getmtime(backup_files[0])
        last_backup = datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M')
        backup_ok = (time.time() - mtime) / 3600 < 26
    return templates.TemplateResponse("admin_status.html", {
        "request": request, "user": user, "stats": stats,
        "db_size_kb": db_size_kb, "uploads_size_mb": uploads_size_mb,
        "uptime_str": uptime_str, "last_ticket": last_ticket,
        "last_comment": last_comment, "last_backup": last_backup,
        "backup_ok": backup_ok, "backup_count": len(backup_files),
        "now": now_berlin(),
    })


@app.get("/admin/changelog", response_class=HTMLResponse)
async def admin_changelog(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    versions = [
        {"version": "v3.9.0", "date": "15.04.2026", "title": "Browser Push-Notifications", "changes": ["Push-Benachrichtigung bei neuem Ticket (auch bei geschlossenem Tab)", "Push-Benachrichtigung bei neuer Nutzer-Antwort", "Service Worker + VAPID-Keys eingerichtet", "Automatische Registrierung fuer Admin-Konten"]},
        {"version": "v3.8.0", "date": "14.04.2026", "title": "Live-Dashboard", "changes": ["Live-Dashboard mit SSE - Kacheln aktualisieren automatisch alle 15s", "Massenmail: Einzelne Empfaenger per Klick waehlbar", "Fix: Statistik timezone-Fehler", "Fix: Jinja2 Block-Struktur"]},
        {"version": "v3.7.0", "date": "04.04.2026", "title": "Nutzer-Aktivität",
         "changes": ["📊 Login-Verlauf pro Nutzer – Datum, Uhrzeit, IP, Browser",
                     "🔐 Jeder Login wird automatisch aufgezeichnet",
                     "👤 Aktivitäts-Seite mit Logins, Tickets, Kommentaren",
                     "🏛️ Wappen im Ticket-Detail und Profil-Seite"]},
        {"version": "v3.6.0", "date": "03.04.2026", "title": "Globale Suche & Anhänge",
         "changes": ["🔍 Globale Suche – durchsucht Tickets, Nutzer und Aufgaben gleichzeitig",
                     "🗑️ Dateianhänge im Admin-Ticket löschen (mit ✕ Button)",
                     "⚡ Admin-Systemstatus unter /admin/status",
                     "🌐 Öffentliche /status Seite zeigt nur Online-Status"]},
        {"version": "v3.5.0", "date": "03.04.2026", "title": "Status, Avatar & Sicherheit",
         "changes": ["⚡ Systemstatus-Seite mit Uptime, DB-Größe, Backup-Status und letzter Aktivität",
                     "👤 Avatar und Initialen-Badge bei Kommentaren im Admin-Ticket sichtbar",
                     "🔑 Admin kann Nutzer-Passwort direkt setzen (ohne E-Mail, mit Audit-Log)",
                     "✅ Sortierung im Nutzer-Portal war bereits vorhanden"]},
        {"version": "v3.4.0", "date": "03.04.2026", "title": "Nutzer & Statistiken",
         "changes": ["🌙 Dark Mode wird dauerhaft gespeichert (Cookie + localStorage)",
                     "📧 Nutzer kann E-Mail-Adresse selbst im Profil ändern",
                     "🔄 Admin-Benachrichtigung wenn Nutzer Ticket wieder öffnet",
                     "👤 Statistik pro Nutzer in der Statistik-Seite",
                     "🏷️ Browser-Tab zeigt Ticket-Nummer und Seitenname"]},
        {"version": "v3.3.0", "date": "03.04.2026", "title": "Sicherheit & Benachrichtigungen",
         "changes": ["💾 Backup-Status auf Sicherheitsseite – zeigt letztes Backup, Anzahl und Warnung bei Ausfall",
                     "📧 Admin-Benachrichtigung wenn Nutzer Ticket schließt",
                     "⚙️ Professionelle 500-Fehlerseite statt Standard-Browser-Fehler",
                     "🔍 Suchbegriff wird in Tickets und Aufgaben gelb hervorgehoben"]},
        {"version": "v3.2.0", "date": "03.04.2026", "title": "Ticket-Vorlagen & Sicherheit",
         "changes": ["💡 Ticket-Vorlagen für Nutzer – Admin erstellt, Nutzer wählt beim neuen Ticket aus",
                     "🔐 Sitzungs-Timeout – einstellbar unter Einstellungen (Standard: 60 Min)",
                     "🔑 Passwort-Stärke beim Profil ändern",
                     "⚙️ Auto-Close nach 3 Wochen ohne Nutzer-Antwort (mit E-Mail-Benachrichtigung)",
                     "📋 Aufgabe direkt aus Ticket erstellen",
                     "🔍 Volltextsuche in Aufgaben bereits integriert"]},
        {"version": "v3.1.0", "date": "03.04.2026", "title": "UX & Bugfixes",
         "changes": ["🏛️ Gemeinde-Wappen im Portal-Banner und Nutzerliste (12 von 13)",
                     "🏷️ Tag-Suche getrennt von Textsuche – klickbare Tags im Dashboard",
                     "💬 Nachrichten-Status im Nutzer-Portal (Neu / Wartet / Beantwortet)",
                     "✅ Elegante Modal-Dialoge statt Browser-Popups",
                     "📋 Aufgaben-Historie vollständig mit Ausklapp-Funktion",
                     "🔧 SLA-Warnung verschwindet nach Admin-Antwort",
                     "📊 Statistik-Seite Breite korrigiert",
                     "🗒️ Nutzer schließt/öffnet Ticket wird in Änderungshistorie dokumentiert",
                     "✏️ Kommentare im Ticket-Verlauf bearbeiten und löschen"]},
        {"version": "v3.0.0", "date": "02.04.2026", "title": "Große Erweiterung",
         "changes": ["🔗 Ticket-Verknüpfung in der Sidebar",
                     "🔺 Automatische Prioritätserhöhung bei überfälligen Tickets",
                     "📥 CSV-Export aller Tickets in Statistiken",
                     "🔒 Admin-Notiz pro Nutzer",
                     "📧 Wöchentlicher Bericht jeden Montag 8:00 Uhr"]},
        {"version": "v2.9.0", "date": "02.04.2026", "title": "Bugfixes & Verbesserungen",
         "changes": ["🔧 SLA-Warnung verschwindet nach Admin-Antwort",
                     "✏ Kommentare im Verlauf bearbeiten und löschen",
                     "📋 Dashboard merkt sich Sortierung (Standard: Status aufsteigend)",
                     "Gelöste Tickets immer unten, aktive oben"]},
        {"version": "v2.8.0", "date": "01.04.2026", "title": "Zwei-Faktor-Authentifizierung",
         "changes": ["🔐 2FA nur für Admin-Accounts",
                     "📱 TOTP (Authenticator App) – empfohlen",
                     "📧 E-Mail-Code als Alternative",
                     "QR-Code zum einfachen Einrichten",
                     "2FA unter ⚙ Mehr → 2FA aktivierbar"]},
        {"version": "v2.7.0", "date": "31.03.2026", "title": "SLA & Eskalation",
         "changes": ["⏱️ SLA-Zeiten pro Priorität definierbar",
                     "⚠️ SLA-Warnung direkt im Dashboard",
                     "📧 Automatische E-Mail-Warnung stündlich",
                     "Standard: Kritisch=2h, Hoch=8h, Mittel=24h, Niedrig=72h"]},
        {"version": "v2.6.0", "date": "31.03.2026", "title": "Antwortvorlagen & Audit-Log",
         "changes": ["📝 Antwortvorlagen erstellen und verwalten",
                     "Vorlagen per Dropdown ins Antwortfeld einfügen",
                     "🔍 Audit-Log mit allen Admin-Aktionen",
                     "IP-Adresse und Zeitstempel bei jeder Aktion"]},
        {"version": "v2.5.0", "date": "31.03.2026", "title": "Antwort-Status verbessert",
         "changes": ["🔴 'Wartet auf dich' – Nutzer hat zuletzt geschrieben",
                     "🔵 'Wartet auf Nutzer' – Admin hat zuletzt geantwortet",
                     "Klare Unterscheidung wer als nächstes handeln muss"]},
        {"version": "v2.4.0", "date": "30.03.2026", "title": "Portal Redesign",
         "changes": ["🎉 Willkommens-Banner mit Avatar, Name und Feuerwehr",
                     "📊 Mini-Statistiken im Banner (Gesamt, Offen, Neue Antworten)",
                     "🟢 Grüner Punkt bei Tickets mit neuer Antwort",
                     "Zeile wird grün hinterlegt bei ungelesener Antwort",
                     "Bessere Empty-State Anzeige"]},
        {"version": "v2.3.0", "date": "30.03.2026", "title": "Startseite & Einstellungen",
         "changes": ["🏠 Attraktive neue Startseite mit Hero-Design",
                     "🎨 Prioritätsfarben individuell anpassbar",
                     "⚙️ Einstellungsseite im Admin-Panel",
                     "Einstellungen im ⚙ Mehr Dropdown"]},
        {"version": "v2.2.0", "date": "30.03.2026", "title": "E-Mail-Vorschau & Druckansicht",
         "changes": ["👁 E-Mail-Vorschau vor dem Senden",
                     "🖨 Drucken-Button im Ticket-Detail",
                     "Optimierte Druckansicht (Navigation ausgeblendet)",
                     "Saubere Darstellung beim Drucken"]},
        {"version": "v2.1.0", "date": "30.03.2026", "title": "Nutzer & Kommunikation",
         "changes": ["💬 Neue Antwort als gelesen markieren",
                     "📊 Tägliche Zusammenfassung per E-Mail um 7:30 Uhr",
                     "🚒 Statistik Tickets pro Gemeinde",
                     "📢 Massenmail an alle oder einzelne Gemeinden",
                     "⏸ Nutzer deaktivieren/sperren statt nur löschen"]},
        {"version": "v2.0.0", "date": "30.03.2026", "title": "Versionierung & Antwort-Anzeige",
         "changes": ["Versionshistorie im Admin-Panel",
                     "CHANGELOG.md im Projektordner",
                     "💬 Neue Antwort! Anzeige im Nutzer-Portal",
                     "Changelog wird bei jeder Änderung aktualisiert"]},
        {"version": "v1.9.0", "date": "30.03.2026", "title": "Profil & Registrierung",
         "changes": ["Avatar-Upload (JPG/PNG/GIF, max. 2MB)", "Avatar in Navigation angezeigt",
                     "Passwort 2x eingeben bei Registrierung", "Passwort-Stärke-Anzeige (live)",
                     "Gemeinden-Dropdown bei Registrierung", "Funktion: Hauptamtlicher Gerätewart",
                     "© Footer mit Torsten Michaely"]},
        {"version": "v1.8.0", "date": "30.03.2026", "title": "Ticket-Features",
         "changes": ["★ Stern-Markierung für wichtige Tickets", "🏷️ Tags als farbige Badges",
                     "Ticket löschen mit Bestätigung", "Ticket-Zusammenfassung bei gelösten Tickets",
                     "🔴 Wartet auf Antwort / ✓ Beantwortet Status im Dashboard",
                     "Abgrenzung aktive / gelöste Tickets im Dashboard"]},
        {"version": "v1.7.0", "date": "29.03.2026", "title": "Statistiken & Charts",
         "changes": ["Reaktionszeit-Chart pro Monat", "Donut-Charts nach Status und Priorität",
                     "Zahlen + Prozent in Charts", "Reaktionszeit-Fix (keine 0-Werte)"]},
        {"version": "v1.6.0", "date": "29.03.2026", "title": "Aufgabenverwaltung",
         "changes": ["Admin-Aufgabenliste (intern)", "Aufgaben erstellen, bearbeiten, erledigen",
                     "Fälligkeitsdatum mit Überfällig-Warnung", "Änderungshistorie für Aufgaben",
                     "Erinnerungs-E-Mail täglich um 7 Uhr", "Aufgaben-Widget im Dashboard"]},
        {"version": "v1.5.0", "date": "29.03.2026", "title": "Sicherheit & Nutzerverwaltung",
         "changes": ["Online-Nutzer Anzeige (letzte 15 Min)", "Fail2Ban Integration",
                     "Admin-Sicherheitsseite mit Ban/Unban", "Nutzer bearbeiten + Admin-Rechte"]},
        {"version": "v1.4.0", "date": "29.03.2026", "title": "Sortierung & Suche",
         "changes": ["Klickbare Spalten-Sortierung überall", "Suchfunktion im Dashboard",
                     "Suchfunktion in Aufgaben und Portal", "Suchbegriff-Highlighting"]},
        {"version": "v1.3.0", "date": "29.03.2026", "title": "UX & Design",
         "changes": ["Mobile-Optimierung", "Favicon + Barrierefreiheit",
                     "Ladeindikator + Zeichen-Counter", "Dark/Light Mode verbessert"]},
        {"version": "v1.0.0", "date": "28.03.2026", "title": "Grundsystem",
         "changes": ["FastAPI + SQLite + Jinja2", "Registrierung mit E-Mail-Verifikation",
                     "Admin-Panel + E-Mail-Benachrichtigungen", "HTTPS + Systemd-Service + Backups"]},
    ]
    return templates.TemplateResponse("admin_changelog.html", {
        "request": request, "user": user, "versions": versions
    })

import json

SETTINGS_FILE = "/opt/ticketsystem/settings.json"

def get_real_ip(request: Request) -> str:
    """Liest die echte Client-IP auch hinter nginx/Proxy."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "–"

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_settings(data: dict):
    try:
        current = load_settings()
        current.update(data)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(current, f)
    except:
        pass

def log_action(db, user_id: int, action: str, details: str = None, ip: str = None):
    """Schreibt einen Eintrag ins Audit-Log."""
    try:
        entry = AuditLog(user_id=user_id, action=action, details=details, ip_address=ip)
        db.add(entry)
        db.commit()
    except:
        pass

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings_page(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    settings = load_settings()
    colors = settings.get("priority_colors", {})
    sla = settings.get("sla_hours", {"critical": 2, "high": 8, "medium": 24, "low": 72})
    return templates.TemplateResponse("admin_settings.html", {
        "request": request, "user": user, "colors": colors, "sla": sla,
        "settings": settings
    })

@app.post("/admin/settings/timeout")
async def admin_settings_timeout(request: Request, db: Session = Depends(get_db),
                                 timeout_minutes: int = Form(default=60)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    settings = load_settings()
    timeout_minutes = max(5, min(480, timeout_minutes))
    settings["session_timeout"] = timeout_minutes
    save_settings(settings)
    # Auth-Modul aktualisieren
    import auth
    auth.SESSION_TIMEOUT_MINUTES = timeout_minutes
    log_action(db, user.id, "SETTINGS_TIMEOUT",
               f"Sitzungs-Timeout auf {timeout_minutes} Minuten gesetzt")
    return RedirectResponse(url="/admin/settings?success=timeout", status_code=302)

@app.post("/admin/settings/sla")
async def admin_settings_sla(request: Request, db: Session = Depends(get_db),
                             sla_critical: int = Form(default=2),
                             sla_high: int = Form(default=8),
                             sla_medium: int = Form(default=24),
                             sla_low: int = Form(default=72),
                             sla_email_enabled: str = Form(default=""),
                             sla_email_interval: int = Form(default=1)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    sla = {
        "critical": sla_critical, "high": sla_high,
        "medium": sla_medium, "low": sla_low,
        "email_enabled": bool(sla_email_enabled),
        "email_interval": max(1, min(24, sla_email_interval))
    }
    save_settings({"sla_hours": sla})
    log_action(db, user.id, "SLA_UPDATE",
               f"SLA: kritisch={sla_critical}h, hoch={sla_high}h, mittel={sla_medium}h, "
               f"niedrig={sla_low}h, E-Mail={'An' if sla_email_enabled else 'Aus'}, "
               f"Intervall={sla_email_interval}h")
    settings = load_settings()
    return templates.TemplateResponse("admin_settings.html", {
        "request": request, "user": user,
        "colors": settings.get("priority_colors", {}),
        "sla": sla,
        "success": "SLA-Zeiten gespeichert!"
    })

@app.post("/admin/settings/colors")
async def admin_settings_colors(request: Request, db: Session = Depends(get_db),
                                color_critical: str = Form(default="#ef4444"),
                                color_high: str = Form(default="#f59e0b"),
                                color_medium: str = Form(default="#3b82f6"),
                                color_low: str = Form(default="#6b7280"),
                                color_critical_hex: str = Form(default=""),
                                color_high_hex: str = Form(default=""),
                                color_medium_hex: str = Form(default=""),
                                color_low_hex: str = Form(default="")):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    colors = {
        "critical": color_critical_hex or color_critical,
        "high": color_high_hex or color_high,
        "medium": color_medium_hex or color_medium,
        "low": color_low_hex or color_low,
    }
    save_settings({"priority_colors": colors})
    templates.env.globals["priority_colors"] = colors
    return templates.TemplateResponse("admin_settings.html", {
        "request": request, "user": user,
        "colors": colors, "success": "Farben gespeichert!"
    })

@app.get("/admin/export/csv")
async def export_csv(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    import csv, io
    tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Ticket-Nr', 'Betreff', 'Status', 'Priorität', 'Nutzer',
                     'Feuerwehr', 'Erstellt', 'Aktualisiert', 'Gelöst am', 'Tags'])
    for t in tickets:
        writer.writerow([
            t.ticket_number, t.title, t.status.value, t.priority.value,
            t.user.name if t.user else '–',
            t.user.feuerwehr if t.user else '–',
            t.created_at.strftime('%d.%m.%Y %H:%M'),
            t.updated_at.strftime('%d.%m.%Y %H:%M'),
            t.resolved_at.strftime('%d.%m.%Y %H:%M') if t.resolved_at else '–',
            t.tags or '–'
        ])
    log_action(db, user.id, "EXPORT_CSV", f"{len(tickets)} Tickets exportiert")
    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue().encode('utf-8-sig')]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tickets_{now_berlin().strftime('%Y%m%d')}.csv"}
    )

# ─── ADMIN AUFGABEN ─────────────────────────────────────────────
@app.get("/admin/tasks", response_class=HTMLResponse)
async def admin_tasks(request: Request, db: Session = Depends(get_db),
                      search: Optional[str] = None):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    query_open = db.query(AdminTask).filter(AdminTask.is_done == False)
    query_done = db.query(AdminTask).filter(AdminTask.is_done == True)
    if search:
        query_open = query_open.filter(
            AdminTask.title.ilike(f"%{search}%") |
            AdminTask.description.ilike(f"%{search}%")
        )
        query_done = query_done.filter(
            AdminTask.title.ilike(f"%{search}%") |
            AdminTask.description.ilike(f"%{search}%")
        )
    tasks_open = query_open.order_by(AdminTask.due_date.asc().nullslast(), AdminTask.created_at.desc()).all()
    tasks_done = query_done.order_by(AdminTask.done_at.desc()).limit(10).all()
    tasks_done_count = db.query(AdminTask).filter(AdminTask.is_done == True).count()
    return templates.TemplateResponse("admin_tasks.html", {
        "request": request, "user": user,
        "tasks_open": tasks_open, "tasks_done": tasks_done,
        "tasks_done_count": tasks_done_count,
        "priorities": TicketPriority, "now": now_berlin(),
        "search": search or ""
    })

@app.get("/admin/tasks/{task_id}/edit", response_class=HTMLResponse)
async def admin_task_edit_page(request: Request, task_id: int,
                               db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    task = db.query(AdminTask).filter(AdminTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("admin_task_edit.html", {
        "request": request, "user": user, "task": task
    })

@app.post("/admin/tasks/{task_id}/edit")
async def admin_task_edit(request: Request, task_id: int,
                          db: Session = Depends(get_db),
                          title: str = Form(...),
                          description: str = Form(default=""),
                          priority: str = Form(...),
                          due_date: str = Form(default="")):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    task = db.query(AdminTask).filter(AdminTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404)

    # Alte Werte VOR der Änderung speichern
    old_title = task.title
    old_desc = task.description or ""
    old_prio = task.priority.value
    old_due = task.due_date.strftime('%d.%m.%Y') if task.due_date else "–"

    task.title = title
    task.description = description
    task.priority = TicketPriority(priority)
    task.updated_at = now_berlin()
    task.updated_by_id = user.id

    # Änderungen aufzeichnen
    changes = []
    if old_title != title:
        db.add(TaskHistory(task_id=task_id, changed_by_id=user.id,
                           field="Titel", old_value=old_title, new_value=title))
        changes.append(f"Titel: {old_title} → {title}")
    if old_desc != (description or ""):
        db.add(TaskHistory(task_id=task_id, changed_by_id=user.id,
                           field="Beschreibung", old_value=old_desc, new_value=(description or "")))
        changes.append("Beschreibung geändert")
    if old_prio != priority:
        db.add(TaskHistory(task_id=task_id, changed_by_id=user.id,
                           field="Priorität", old_value=old_prio, new_value=priority))
        changes.append(f"Priorität: {old_prio} → {priority}")
    new_due = datetime.strptime(due_date, "%Y-%m-%d").strftime('%d.%m.%Y') if due_date else "–"
    if old_due != new_due:
        db.add(TaskHistory(task_id=task_id, changed_by_id=user.id,
                           field="Fälligkeitsdatum", old_value=old_due, new_value=new_due))
        changes.append(f"Fälligkeit: {old_due} → {new_due}")
    if changes:
        log_action(db, user.id, "TASK_EDIT",
                   f"Aufgabe #{task_id} '{task.title}' geändert: {', '.join(changes)}")

    if due_date:
        try:
            task.due_date = datetime.strptime(due_date, "%Y-%m-%d")
        except:
            pass
    else:
        task.due_date = None
    db.commit()
    return RedirectResponse(url="/admin/tasks", status_code=302)

@app.post("/admin/tasks/new")
async def admin_task_new(request: Request, db: Session = Depends(get_db),
                         title: str = Form(...), description: str = Form(default=""),
                         priority: str = Form(...), due_date: str = Form(default="")):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    due = None
    if due_date:
        try:
            from datetime import datetime
            due = datetime.strptime(due_date, "%Y-%m-%d")
        except:
            pass
    task = AdminTask(title=title, description=description,
                     priority=TicketPriority(priority),
                     due_date=due, created_by_id=user.id)
    db.add(task)
    db.commit()
    return RedirectResponse(url="/admin/tasks", status_code=302)

@app.post("/admin/tasks/{task_id}/done")
async def admin_task_done(request: Request, task_id: int,
                          db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    task = db.query(AdminTask).filter(AdminTask.id == task_id).first()
    if task:
        task.is_done = True
        task.done_at = now_berlin()
        db.add(TaskHistory(task_id=task.id, changed_by_id=user.id,
                           field="Status", old_value="Offen", new_value="Erledigt"))
        db.commit()
    return RedirectResponse(url="/admin/tasks", status_code=302)

@app.post("/admin/tasks/{task_id}/reopen")
async def admin_task_reopen(request: Request, task_id: int,
                            db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    task = db.query(AdminTask).filter(AdminTask.id == task_id).first()
    if task:
        task.is_done = False
        task.done_at = None
        db.add(TaskHistory(task_id=task.id, changed_by_id=user.id,
                           field="Status", old_value="Erledigt", new_value="Wieder geöffnet"))
        db.commit()
    return RedirectResponse(url="/admin/tasks", status_code=302)

@app.post("/admin/tasks/{task_id}/delete")
async def admin_task_delete(request: Request, task_id: int,
                            db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    task = db.query(AdminTask).filter(AdminTask.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()
    return RedirectResponse(url="/admin/tasks", status_code=302)

@app.get("/admin/export/csv")
async def export_csv(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    import csv, io
    tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Ticket-Nr", "Betreff", "Status", "Priorität", "Nutzer",
                     "Feuerwehr", "Erstellt", "Aktualisiert", "Gelöst am", "Tags"])
    for t in tickets:
        writer.writerow([
            t.ticket_number, t.title, t.status.value, t.priority.value,
            t.user.name if t.user else "–",
            t.user.feuerwehr if t.user else "–",
            t.created_at.strftime('%d.%m.%Y %H:%M'),
            t.updated_at.strftime('%d.%m.%Y %H:%M'),
            t.resolved_at.strftime('%d.%m.%Y %H:%M') if t.resolved_at else "–",
            t.tags or "–"
        ])
    log_action(db, user.id, "EXPORT_CSV", f"{len(tickets)} Tickets exportiert")
    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tickets_export.csv"}
    )

# ─── ANTWORTVORLAGEN ────────────────────────────────────────────
# ─── NUTZER-VORLAGEN (Admin) ────────────────────────────────────────────────
@app.get("/admin/user-templates", response_class=HTMLResponse)
async def admin_user_templates(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    tmpl_list = db.query(UserTemplate).order_by(UserTemplate.title).all()
    return templates.TemplateResponse("admin_user_templates.html", {
        "request": request, "user": user, "templates_list": tmpl_list,
        "priorities": TicketPriority
    })

@app.post("/admin/user-templates/new")
async def admin_user_template_new(request: Request, db: Session = Depends(get_db),
                                  title: str = Form(...),
                                  subject: str = Form(...),
                                  description: str = Form(...),
                                  priority: str = Form(default="medium")):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    tmpl = UserTemplate(title=title, subject=subject, description=description,
                        priority=TicketPriority(priority), created_by_id=user.id)
    db.add(tmpl)
    db.commit()
    log_action(db, user.id, "USER_TEMPLATE_CREATE", f"Vorlage '{title}' erstellt")
    return RedirectResponse(url="/admin/user-templates", status_code=302)

@app.post("/admin/user-templates/{tmpl_id}/edit")
async def admin_user_template_edit(request: Request, tmpl_id: int,
                                   db: Session = Depends(get_db),
                                   title: str = Form(...),
                                   subject: str = Form(...),
                                   description: str = Form(...),
                                   priority: str = Form(default="medium")):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    tmpl = db.query(UserTemplate).filter(UserTemplate.id == tmpl_id).first()
    if tmpl:
        tmpl.title = title
        tmpl.subject = subject
        tmpl.description = description
        tmpl.priority = TicketPriority(priority)
        db.commit()
        log_action(db, user.id, "USER_TEMPLATE_EDIT", f"Vorlage '{title}' bearbeitet")
    return RedirectResponse(url="/admin/user-templates", status_code=302)

@app.post("/admin/user-templates/{tmpl_id}/delete")
async def admin_user_template_delete(request: Request, tmpl_id: int,
                                     db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    tmpl = db.query(UserTemplate).filter(UserTemplate.id == tmpl_id).first()
    if tmpl:
        log_action(db, user.id, "USER_TEMPLATE_DELETE", f"Vorlage '{tmpl.title}' gelöscht")
        db.delete(tmpl)
        db.commit()
    return RedirectResponse(url="/admin/user-templates", status_code=302)

@app.post("/admin/user-templates/{tmpl_id}/toggle")
async def admin_user_template_toggle(request: Request, tmpl_id: int,
                                     db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    tmpl = db.query(UserTemplate).filter(UserTemplate.id == tmpl_id).first()
    if tmpl:
        tmpl.is_active = not tmpl.is_active
        db.commit()
    return RedirectResponse(url="/admin/user-templates", status_code=302)

@app.get("/admin/templates", response_class=HTMLResponse)
async def admin_templates(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    templates_list = db.query(ReplyTemplate).order_by(ReplyTemplate.created_at.desc()).all()
    return templates.TemplateResponse("admin_templates.html", {
        "request": request, "user": user, "templates_list": templates_list
    })

@app.post("/admin/templates/new")
async def admin_template_new(request: Request, db: Session = Depends(get_db),
                             title: str = Form(...), content: str = Form(...)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    t = ReplyTemplate(title=title, content=content, created_by_id=user.id)
    db.add(t)
    db.commit()
    log_action(db, user.id, "TEMPLATE_CREATE", f"Vorlage erstellt: {title}")
    return RedirectResponse(url="/admin/templates", status_code=302)

@app.get("/admin/templates/{template_id}/edit", response_class=HTMLResponse)
async def admin_template_edit_page(request: Request, template_id: int,
                                   db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    t = db.query(ReplyTemplate).filter(ReplyTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404)
    templates_list = db.query(ReplyTemplate).order_by(ReplyTemplate.created_at.desc()).all()
    return templates.TemplateResponse("admin_templates.html", {
        "request": request, "user": user,
        "templates_list": templates_list, "edit_template": t
    })

@app.post("/admin/templates/{template_id}/edit")
async def admin_template_edit(request: Request, template_id: int,
                              db: Session = Depends(get_db),
                              title: str = Form(...), content: str = Form(...)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    t = db.query(ReplyTemplate).filter(ReplyTemplate.id == template_id).first()
    if t:
        t.title = title
        t.content = content
        db.commit()
        log_action(db, user.id, "TEMPLATE_EDIT", f"Vorlage bearbeitet: {title}")
    return RedirectResponse(url="/admin/templates", status_code=302)

@app.post("/admin/templates/{template_id}/delete")
async def admin_template_delete(request: Request, template_id: int,
                                db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    t = db.query(ReplyTemplate).filter(ReplyTemplate.id == template_id).first()
    if t:
        log_action(db, user.id, "TEMPLATE_DELETE", f"Vorlage gelöscht: {t.title}")
        db.delete(t)
        db.commit()
    return RedirectResponse(url="/admin/templates", status_code=302)

# ─── AUDIT LOG ──────────────────────────────────────────────────
@app.get("/admin/audit", response_class=HTMLResponse)
async def admin_audit(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    return templates.TemplateResponse("admin_audit.html", {
        "request": request, "user": user, "logs": logs
    })

# ─── SICHERHEIT / FAIL2BAN ──────────────────────────────────────
def _f2b_command(args: list):
    import subprocess
    try:
        result = subprocess.run(
            ["fail2ban-client"] + args,
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        return str(e), False

def _get_banned_ips():
    banned = []
    for jail in ["sshd", "ticketsystem"]:
        output, ok = _f2b_command(["status", jail])
        if ok and "Banned IP list:" in output:
            for line in output.split("\n"):
                if "Banned IP list:" in line:
                    ips = line.split("Banned IP list:")[1].strip().split()
                    for ip in ips:
                        if ip:
                            banned.append({"ip": ip, "jail": jail, "time": "–"})
    return banned

@app.get("/admin/security", response_class=HTMLResponse)
async def admin_security(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    banned_ips = _get_banned_ips()
    ssh_bans = sum(1 for b in banned_ips if b["jail"] == "sshd")
    _, f2b_running = _f2b_command(["ping"])
    # Backup-Status ermitteln
    import glob
    backup_dir = "/opt/ticketsystem/backups"
    backup_files = sorted(glob.glob(f"{backup_dir}/*.db"), reverse=True)
    last_backup = None
    backup_size = None
    backup_count = len(backup_files)
    if backup_files:
        import os
        last_backup_path = backup_files[0]
        last_backup_stat = os.stat(last_backup_path)
        last_backup = datetime.fromtimestamp(last_backup_stat.st_mtime).strftime('%d.%m.%Y %H:%M')
        backup_size = round(last_backup_stat.st_size / 1024, 1)
        # Alter des letzten Backups in Stunden
        age_hours = (datetime.now().timestamp() - last_backup_stat.st_mtime) / 3600
        backup_ok = age_hours < 26  # OK wenn jünger als 26 Stunden
    else:
        backup_ok = False
        age_hours = None
    return templates.TemplateResponse("admin_security.html", {
        "request": request, "user": user,
        "banned_ips": banned_ips,
        "ssh_bans": ssh_bans,
        "f2b_running": f2b_running,
        "last_backup": last_backup,
        "backup_size": backup_size,
        "backup_count": backup_count,
        "backup_ok": backup_ok,
        "backup_age_hours": round(age_hours, 1) if age_hours else None
    })

@app.post("/admin/security/unban")
async def admin_unban(request: Request, db: Session = Depends(get_db),
                      ip: str = Form(...), jail: str = Form(...)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    _f2b_command(["set", jail, "unbanip", ip])
    return RedirectResponse(url="/admin/security?success=1", status_code=302)

@app.post("/admin/security/unban-all")
async def admin_unban_all(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    for ban in _get_banned_ips():
        _f2b_command(["set", ban["jail"], "unbanip", ban["ip"]])
    return RedirectResponse(url="/admin/security?success=1", status_code=302)

@app.post("/admin/security/ban")
async def admin_ban(request: Request, db: Session = Depends(get_db),
                    ip: str = Form(...), jail: str = Form(...)):
    user = await get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    _f2b_command(["set", jail, "banip", ip])
    return RedirectResponse(url="/admin/security?success=1", status_code=302)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
