import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import Boolean, Column, Integer, MetaData, String, Table, Text, create_engine, delete, desc, func, insert, select, update


DB_PATH = Path("memory/control_panel.db")
DEFAULT_PLAN = "free"
DEFAULT_RUN_LIMIT = 5


metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String, unique=True, nullable=False),
    Column("password_hash", Text, nullable=False),
    Column("name", String, nullable=False),
    Column("plan", String, nullable=False, default=DEFAULT_PLAN),
    Column("monthly_run_limit", Integer, nullable=False, default=DEFAULT_RUN_LIMIT),
    Column("monthly_run_usage", Integer, nullable=False, default=0),
    Column("usage_month", String, nullable=False),
    Column("created_at", String, nullable=False),
)

sessions = Table(
    "sessions",
    metadata,
    Column("token", String, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("created_at", String, nullable=False),
)

stored_secrets = Table(
    "secrets",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("value_encrypted", Text, nullable=False),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

runs = Table(
    "runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("prompt", Text, nullable=False),
    Column("app_root", Text, nullable=False),
    Column("run_verification", Boolean, nullable=False),
    Column("auto_deploy", Boolean, nullable=False),
    Column("status", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
    Column("result_json", Text),
    Column("error", Text, nullable=False, default=""),
)

jobs = Table(
    "jobs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", String, nullable=False, unique=True),
    Column("status", String, nullable=False),
    Column("worker_id", String),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

run_logs = Table(
    "run_logs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", String, nullable=False),
    Column("level", String, nullable=False),
    Column("message", Text, nullable=False),
    Column("created_at", String, nullable=False),
)

run_artifacts = Table(
    "run_artifacts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", String, nullable=False),
    Column("artifact_type", String, nullable=False),
    Column("label", String, nullable=False),
    Column("path", Text, nullable=False),
    Column("created_at", String, nullable=False),
)

worker_heartbeats = Table(
    "worker_heartbeats",
    metadata,
    Column("worker_id", String, primary_key=True),
    Column("status", String, nullable=False),
    Column("last_seen_at", String, nullable=False),
    Column("backend", String, nullable=False),
)


def _database_url():
    configured = os.getenv("CONTROL_PANEL_DATABASE_URL")
    if configured:
        return configured
    return f"sqlite:///{DB_PATH}"


def _engine():
    url = _database_url()
    if url.startswith("sqlite:///"):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, future=True)
    return create_engine(url, future=True, pool_pre_ping=True)


def init_db():
    metadata.create_all(_engine())


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _parse_utc(timestamp):
    if not timestamp:
        return None
    return datetime.fromisoformat(timestamp)


def _month_key():
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def _hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
    return f"{salt}${digest}"


def _verify_password(password, password_hash):
    salt, expected = password_hash.split("$", 1)
    candidate = _hash_password(password, salt=salt).split("$", 1)[1]
    return hmac.compare_digest(candidate, expected)


def _serialize_json(value):
    return json.dumps(value) if value is not None else None


def _row_to_dict(row):
    if row is None:
        return None
    return dict(row._mapping)


def _user_from_row(row):
    data = _row_to_dict(row)
    if data is None:
        return None
    return {
        "id": data["id"],
        "email": data["email"],
        "name": data["name"],
        "plan": data["plan"],
        "monthly_run_limit": data["monthly_run_limit"],
        "monthly_run_usage": data["monthly_run_usage"],
        "usage_month": data["usage_month"],
        "created_at": data["created_at"],
    }


def _deserialize_run(row):
    data = _row_to_dict(row)
    if data is None:
        return None
    return {
        "id": data["id"],
        "user_id": data["user_id"],
        "prompt": data["prompt"],
        "app_root": data["app_root"],
        "run_verification": bool(data["run_verification"]),
        "auto_deploy": bool(data["auto_deploy"]),
        "status": data["status"],
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
        "result": json.loads(data["result_json"]) if data.get("result_json") else None,
        "error": data["error"],
    }


def _master_secret():
    return os.getenv("CONTROL_PANEL_SECRET_KEY", "local-dev-secret-key-change-me").encode("utf-8")


def _stream_cipher(data, nonce):
    secret = _master_secret()
    output = bytearray()
    counter = 0
    while len(output) < len(data):
        block = hmac.new(secret, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        output.extend(block)
        counter += 1
    return bytes(a ^ b for a, b in zip(data, output[: len(data)]))


def encrypt_secret(value):
    nonce = secrets.token_bytes(16)
    plaintext = value.encode("utf-8")
    ciphertext = _stream_cipher(plaintext, nonce)
    digest = hmac.new(_master_secret(), nonce + ciphertext, hashlib.sha256).digest()
    return base64.b64encode(nonce + digest + ciphertext).decode("utf-8")


def decrypt_secret(encrypted):
    payload = base64.b64decode(encrypted.encode("utf-8"))
    nonce = payload[:16]
    digest = payload[16:48]
    ciphertext = payload[48:]
    expected = hmac.new(_master_secret(), nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(digest, expected):
        raise ValueError("Stored secret failed integrity verification.")
    return _stream_cipher(ciphertext, nonce).decode("utf-8")


def _reset_usage_if_needed(connection, user_id):
    row = connection.execute(select(users).where(users.c.id == user_id)).first()
    if row is None:
        return
    current_month = _month_key()
    if row._mapping["usage_month"] != current_month:
        connection.execute(
            update(users)
            .where(users.c.id == user_id)
            .values(usage_month=current_month, monthly_run_usage=0)
        )


def register_user(email, password, name):
    init_db()
    normalized_email = str(email or "").strip().lower()
    normalized_name = str(name or "").strip() or normalized_email.split("@", 1)[0]
    if not normalized_email or not password:
        raise ValueError("Email and password are required.")
    engine = _engine()
    with engine.begin() as connection:
        existing = connection.execute(select(users.c.id).where(users.c.email == normalized_email)).first()
        if existing is not None:
            raise ValueError("An account with this email already exists.")
        connection.execute(
            insert(users).values(
                email=normalized_email,
                password_hash=_hash_password(password),
                name=normalized_name,
                plan=DEFAULT_PLAN,
                monthly_run_limit=DEFAULT_RUN_LIMIT,
                monthly_run_usage=0,
                usage_month=_month_key(),
                created_at=_utc_now(),
            )
        )
        row = connection.execute(select(users).where(users.c.email == normalized_email)).first()
    return _user_from_row(row)


def authenticate_user(email, password):
    init_db()
    normalized_email = str(email or "").strip().lower()
    with _engine().begin() as connection:
        row = connection.execute(select(users).where(users.c.email == normalized_email)).first()
    if row is None or not _verify_password(password, row._mapping["password_hash"]):
        return None
    return _user_from_row(row)


def create_session(user_id):
    init_db()
    token = secrets.token_urlsafe(32)
    with _engine().begin() as connection:
        connection.execute(insert(sessions).values(token=token, user_id=user_id, created_at=_utc_now()))
    return token


def delete_session(token):
    init_db()
    with _engine().begin() as connection:
        connection.execute(delete(sessions).where(sessions.c.token == token))


def get_user_by_session(token):
    if not token:
        return None
    init_db()
    with _engine().begin() as connection:
        row = connection.execute(
            select(users)
            .join(sessions, users.c.id == sessions.c.user_id)
            .where(sessions.c.token == token)
        ).first()
    return _user_from_row(row)


def get_user(user_id):
    init_db()
    with _engine().begin() as connection:
        row = connection.execute(select(users).where(users.c.id == user_id)).first()
    return _user_from_row(row)


def get_usage_summary(user_id):
    user = get_user(user_id)
    if not user:
        return None
    return {
        "plan": user["plan"],
        "monthly_run_limit": user["monthly_run_limit"],
        "monthly_run_usage": user["monthly_run_usage"],
        "remaining_runs": max(user["monthly_run_limit"] - user["monthly_run_usage"], 0),
        "usage_month": user["usage_month"],
        "database_url": _database_url(),
    }


def store_secret(user_id, name, value):
    init_db()
    now = _utc_now()
    encrypted = encrypt_secret(value)
    name = str(name or "").strip()
    with _engine().begin() as connection:
        existing = connection.execute(
            select(stored_secrets).where(
                (stored_secrets.c.user_id == user_id) & (stored_secrets.c.name == name)
            )
        ).first()
        if existing is None:
            connection.execute(
                insert(stored_secrets).values(
                    user_id=user_id,
                    name=name,
                    value_encrypted=encrypted,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            connection.execute(
                update(stored_secrets)
                .where((stored_secrets.c.user_id == user_id) & (stored_secrets.c.name == name))
                .values(value_encrypted=encrypted, updated_at=now)
            )


def list_secrets(user_id):
    init_db()
    with _engine().begin() as connection:
        rows = connection.execute(
            select(stored_secrets.c.name, stored_secrets.c.created_at, stored_secrets.c.updated_at)
            .where(stored_secrets.c.user_id == user_id)
            .order_by(stored_secrets.c.name.asc())
        ).all()
    return [dict(row._mapping) for row in rows]


def get_secret_value(user_id, name):
    init_db()
    with _engine().begin() as connection:
        row = connection.execute(
            select(stored_secrets.c.value_encrypted).where(
                (stored_secrets.c.user_id == user_id) & (stored_secrets.c.name == name)
            )
        ).first()
    if row is None:
        return None
    return decrypt_secret(row._mapping["value_encrypted"])


def delete_secret(user_id, name):
    init_db()
    with _engine().begin() as connection:
        connection.execute(
            delete(stored_secrets).where((stored_secrets.c.user_id == user_id) & (stored_secrets.c.name == name))
        )


def create_run(user_id, prompt, app_root, run_verification=True, auto_deploy=False):
    init_db()
    run_id = secrets.token_hex(16)
    now = _utc_now()
    with _engine().begin() as connection:
        _reset_usage_if_needed(connection, user_id)
        user = connection.execute(select(users).where(users.c.id == user_id)).first()
        if user is None:
            raise ValueError("User not found.")
        user_data = user._mapping
        if user_data["monthly_run_usage"] >= user_data["monthly_run_limit"]:
            raise ValueError("Monthly run limit reached for this account.")
        connection.execute(
            insert(runs).values(
                id=run_id,
                user_id=user_id,
                prompt=prompt,
                app_root=app_root,
                run_verification=bool(run_verification),
                auto_deploy=bool(auto_deploy),
                status="queued",
                created_at=now,
                updated_at=now,
                result_json=None,
                error="",
            )
        )
        connection.execute(
            insert(jobs).values(
                run_id=run_id,
                status="queued",
                worker_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        connection.execute(
            update(users)
            .where(users.c.id == user_id)
            .values(monthly_run_usage=user_data["monthly_run_usage"] + 1)
        )
        row = connection.execute(select(runs).where(runs.c.id == run_id)).first()
    return _deserialize_run(row)


def list_runs(user_id, limit=20):
    init_db()
    with _engine().begin() as connection:
        rows = connection.execute(
            select(runs).where(runs.c.user_id == user_id).order_by(desc(runs.c.created_at)).limit(limit)
        ).all()
    return [_deserialize_run(row) for row in rows]


def get_run(user_id, run_id):
    init_db()
    with _engine().begin() as connection:
        row = connection.execute(
            select(runs).where((runs.c.user_id == user_id) & (runs.c.id == run_id))
        ).first()
    return _deserialize_run(row)


def get_run_by_id(run_id):
    init_db()
    with _engine().begin() as connection:
        row = connection.execute(select(runs).where(runs.c.id == run_id)).first()
    return _deserialize_run(row)


def update_run(run_id, **updates):
    init_db()
    values = {"updated_at": _utc_now()}
    if "status" in updates:
        values["status"] = updates["status"]
    if "result" in updates:
        values["result_json"] = _serialize_json(updates["result"])
    if "error" in updates:
        values["error"] = updates["error"]
    if "app_root" in updates:
        values["app_root"] = updates["app_root"]
    with _engine().begin() as connection:
        connection.execute(update(runs).where(runs.c.id == run_id).values(**values))
        row = connection.execute(select(runs).where(runs.c.id == run_id)).first()
    return _deserialize_run(row)


def list_run_logs(user_id, run_id, limit=200):
    init_db()
    if get_run(user_id, run_id) is None:
        return None
    with _engine().begin() as connection:
        rows = connection.execute(
            select(run_logs.c.level, run_logs.c.message, run_logs.c.created_at)
            .where(run_logs.c.run_id == run_id)
            .order_by(run_logs.c.id.asc())
            .limit(limit)
        ).all()
    return [dict(row._mapping) for row in rows]


def append_run_log(run_id, level, message):
    init_db()
    with _engine().begin() as connection:
        connection.execute(
            insert(run_logs).values(run_id=run_id, level=level, message=message, created_at=_utc_now())
        )


def list_run_artifacts(user_id, run_id):
    init_db()
    if get_run(user_id, run_id) is None:
        return None
    with _engine().begin() as connection:
        rows = connection.execute(
            select(
                run_artifacts.c.artifact_type,
                run_artifacts.c.label,
                run_artifacts.c.path,
                run_artifacts.c.created_at,
            )
            .where(run_artifacts.c.run_id == run_id)
            .order_by(run_artifacts.c.id.asc())
        ).all()
    return [dict(row._mapping) for row in rows]


def replace_run_artifacts(run_id, artifacts):
    init_db()
    with _engine().begin() as connection:
        connection.execute(delete(run_artifacts).where(run_artifacts.c.run_id == run_id))
        for artifact in artifacts:
            connection.execute(
                insert(run_artifacts).values(
                    run_id=run_id,
                    artifact_type=artifact["artifact_type"],
                    label=artifact["label"],
                    path=artifact["path"],
                    created_at=_utc_now(),
                )
            )


def claim_next_job(worker_id):
    init_db()
    with _engine().begin() as connection:
        row = connection.execute(
            select(jobs).where(jobs.c.status == "queued").order_by(jobs.c.created_at.asc()).limit(1)
        ).first()
        if row is None:
            return None
        job_id = row._mapping["id"]
        connection.execute(
            update(jobs)
            .where(jobs.c.id == job_id)
            .values(status="running", worker_id=worker_id, updated_at=_utc_now())
        )
        job = connection.execute(select(jobs).where(jobs.c.id == job_id)).first()
    return dict(job._mapping) if job else None


def update_job(run_id, status, worker_id=None):
    init_db()
    values = {"status": status, "updated_at": _utc_now()}
    if worker_id is not None:
        values["worker_id"] = worker_id
    with _engine().begin() as connection:
        connection.execute(update(jobs).where(jobs.c.run_id == run_id).values(**values))


def get_job_for_run(run_id):
    init_db()
    with _engine().begin() as connection:
        row = connection.execute(select(jobs).where(jobs.c.run_id == run_id)).first()
    return dict(row._mapping) if row else None


def list_jobs_by_status(status):
    init_db()
    with _engine().begin() as connection:
        rows = connection.execute(
            select(jobs).where(jobs.c.status == status).order_by(jobs.c.updated_at.asc())
        ).fetchall()
    return [dict(row._mapping) for row in rows]


def set_user_plan(user_id, plan, monthly_run_limit):
    init_db()
    with _engine().begin() as connection:
        connection.execute(
            update(users)
            .where(users.c.id == user_id)
            .values(plan=plan, monthly_run_limit=monthly_run_limit)
        )


def get_database_backend():
    url = _database_url()
    if url.startswith("postgresql"):
        return "postgresql"
    if url.startswith("sqlite"):
        return "sqlite"
    return "unknown"


def record_worker_heartbeat(worker_id, status="alive"):
    init_db()
    payload = {
        "worker_id": worker_id,
        "status": status,
        "last_seen_at": _utc_now(),
        "backend": get_database_backend(),
    }
    with _engine().begin() as connection:
        existing = connection.execute(
            select(worker_heartbeats.c.worker_id).where(worker_heartbeats.c.worker_id == worker_id)
        ).first()
        if existing is None:
            connection.execute(insert(worker_heartbeats).values(**payload))
        else:
            connection.execute(
                update(worker_heartbeats)
                .where(worker_heartbeats.c.worker_id == worker_id)
                .values(**payload)
            )


def list_recent_workers(limit=10):
    init_db()
    with _engine().begin() as connection:
        rows = connection.execute(
            select(worker_heartbeats).order_by(desc(worker_heartbeats.c.last_seen_at)).limit(limit)
        ).fetchall()
    return [dict(row._mapping) for row in rows]


def get_worker_heartbeat(worker_id):
    init_db()
    with _engine().begin() as connection:
        row = connection.execute(
            select(worker_heartbeats).where(worker_heartbeats.c.worker_id == worker_id)
        ).first()
    return dict(row._mapping) if row else None


def recover_stale_jobs(worker_timeout_seconds=90, lease_timeout_seconds=180):
    init_db()
    now = datetime.now(timezone.utc)
    stale_jobs = []
    with _engine().begin() as connection:
        running_rows = connection.execute(
            select(jobs).where(jobs.c.status == "running").order_by(jobs.c.updated_at.asc())
        ).fetchall()
        for row in running_rows:
            job = dict(row._mapping)
            updated_at = _parse_utc(job.get("updated_at"))
            if updated_at is None:
                continue
            worker_stale = False
            worker_id = job.get("worker_id")
            if worker_id:
                worker_row = connection.execute(
                    select(worker_heartbeats).where(worker_heartbeats.c.worker_id == worker_id)
                ).first()
                if worker_row is None:
                    worker_stale = True
                else:
                    last_seen = _parse_utc(worker_row._mapping["last_seen_at"])
                    worker_stale = last_seen is None or last_seen < now - timedelta(seconds=worker_timeout_seconds)
            lease_stale = updated_at < now - timedelta(seconds=lease_timeout_seconds)
            if worker_stale or lease_stale:
                connection.execute(
                    update(jobs)
                    .where(jobs.c.id == job["id"])
                    .values(status="queued", worker_id=None, updated_at=_utc_now())
                )
                stale_jobs.append(job["run_id"])
    return stale_jobs
