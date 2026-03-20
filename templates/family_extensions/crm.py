CRM_EXTENSION = {
    "backend_import": (
        "from family_logic import "
        "advance_crm_deal_status, build_crm_account_health, build_crm_accounts, "
        "build_crm_activity, build_crm_deal_snapshot, build_crm_pipeline, "
        "reassign_crm_deal_owner\n"
    ),
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _table_names(connection):
    return {
        row["name"]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }


def _ensure_crm_events_table(connection):
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS crm_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            account_id INTEGER,
            event_type TEXT NOT NULL,
            actor TEXT,
            summary TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        '''
    )
    connection.commit()


def _account_name_map(connection):
    table_names = _table_names(connection)
    if "accounts" not in table_names:
        return {}
    rows = connection.execute("SELECT id, name FROM accounts").fetchall()
    return {dict(row).get("id"): dict(row).get("name") for row in rows}


def build_crm_pipeline(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"pipeline": [], "forecast": {"qualified": 0, "proposal": 0, "closed": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        account_names = _account_name_map(connection)
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    pipeline = []
    forecast = {"qualified": 0, "proposal": 0, "closed": 0}
    for row in rows:
        payload = dict(row)
        status = str(payload.get("status") or "qualified").lower()
        if status in forecast:
            forecast[status] += 1
        pipeline.append(
            {
                "id": payload.get("id"),
                "title": payload.get("title") or payload.get("name") or f"{primary_entity} #{payload.get('id')}",
                "owner": payload.get("owner") or "Unassigned",
                "status": status,
                "amount": payload.get("amount") or payload.get("value") or 0,
                "account": account_names.get(payload.get("account_id")) or "Unassigned account",
            }
        )
    return {"pipeline": pipeline, "forecast": forecast}


def build_crm_accounts(db_path: Path):
    if not db_path.exists():
        return {"accounts": []}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        table_names = _table_names(connection)
        if "accounts" not in table_names:
            return {"accounts": []}
        rows = connection.execute("SELECT * FROM accounts ORDER BY id DESC LIMIT 25").fetchall()
    return {
        "accounts": [
            {
                "id": dict(row).get("id"),
                "name": dict(row).get("name") or f"Account #{dict(row).get('id')}",
                "status": dict(row).get("status") or "active",
                "segment": dict(row).get("segment") or "general",
            }
            for row in rows
        ]
    }


def build_crm_account_health(db_path: Path, primary_table: str):
    if not db_path.exists():
        return {"accounts": []}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        table_names = _table_names(connection)
        if "accounts" not in table_names:
            return {"accounts": []}
        account_rows = connection.execute(
            "SELECT id, name, segment, status FROM accounts ORDER BY id ASC"
        ).fetchall()
        deal_rows = connection.execute(
            f"SELECT id, account_id, amount, status FROM {primary_table} ORDER BY id ASC"
        ).fetchall()
    health = []
    deals_by_account = {}
    for row in deal_rows:
        payload = dict(row)
        account_id = payload.get("account_id")
        if not account_id:
            continue
        deals_by_account.setdefault(account_id, []).append(payload)
    for row in account_rows:
        payload = dict(row)
        related_deals = deals_by_account.get(payload.get("id"), [])
        pipeline_value = sum((deal.get("amount") or 0) for deal in related_deals)
        health.append(
            {
                "id": payload.get("id"),
                "name": payload.get("name") or f"Account #{payload.get('id')}",
                "segment": payload.get("segment") or "general",
                "status": payload.get("status") or "active",
                "openDeals": len(related_deals),
                "pipelineValue": pipeline_value,
            }
        )
    health.sort(key=lambda account: (-account["pipelineValue"], -account["openDeals"], account["id"] or 0))
    return {"accounts": health[:20]}


def record_crm_event(db_path: Path, event_type: str, item_id: int | None, account_id: int | None, actor: str | None, summary: str):
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        _ensure_crm_events_table(connection)
        connection.execute(
            '''
            INSERT INTO crm_events (item_id, account_id, event_type, actor, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (item_id, account_id, event_type, actor or "system", summary, _utc_now()),
        )
        connection.commit()


def build_crm_activity(db_path: Path, primary_table: str):
    if not db_path.exists():
        return {"activity": []}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        _ensure_crm_events_table(connection)
        events = connection.execute(
            "SELECT * FROM crm_events ORDER BY id DESC LIMIT 20"
        ).fetchall()
        if not events:
            deal_rows = connection.execute(
                f"SELECT id, title, name, account_id, owner FROM {primary_table} ORDER BY id DESC LIMIT 10"
            ).fetchall()
            account_names = _account_name_map(connection)
            for row in deal_rows:
                payload = dict(row)
                connection.execute(
                    '''
                    INSERT INTO crm_events (item_id, account_id, event_type, actor, summary, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        payload.get("id"),
                        payload.get("account_id"),
                        "seeded",
                        payload.get("owner") or "system",
                        f"Added {payload.get('title') or payload.get('name') or 'deal'} for {account_names.get(payload.get('account_id')) or 'an account'}",
                        _utc_now(),
                    ),
                )
            connection.commit()
            events = connection.execute(
                "SELECT * FROM crm_events ORDER BY id DESC LIMIT 20"
            ).fetchall()
    return {
        "activity": [
            {
                "id": dict(row).get("id"),
                "itemId": dict(row).get("item_id"),
                "accountId": dict(row).get("account_id"),
                "eventType": dict(row).get("event_type"),
                "actor": dict(row).get("actor") or "system",
                "summary": dict(row).get("summary"),
                "createdAt": dict(row).get("created_at"),
            }
            for row in events
        ]
    }


def build_crm_deal_snapshot(db_path: Path, primary_table: str, item_id: int):
    if not db_path.exists():
        return None
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        _ensure_crm_events_table(connection)
        deal_row = connection.execute(
            f"SELECT * FROM {primary_table} WHERE id = ?",
            (item_id,),
        ).fetchone()
        if not deal_row:
            return None
        deal = dict(deal_row)
        account_name = None
        if deal.get("account_id") and "accounts" in _table_names(connection):
            account_row = connection.execute(
                "SELECT name, segment, status FROM accounts WHERE id = ?",
                (deal.get("account_id"),),
            ).fetchone()
            if account_row:
                account_name = dict(account_row)
        events = connection.execute(
            "SELECT event_type, actor, summary, created_at FROM crm_events WHERE item_id = ? ORDER BY id DESC LIMIT 10",
            (item_id,),
        ).fetchall()
    return {
        "deal": {
            "id": deal.get("id"),
            "title": deal.get("title") or deal.get("name"),
            "status": deal.get("status") or "qualified",
            "owner": deal.get("owner") or "Unassigned",
            "amount": deal.get("amount") or deal.get("value") or 0,
        },
        "account": account_name,
        "activity": [dict(row) for row in events],
    }


def advance_crm_deal_status(db_path: Path, primary_table: str, item_id: int, actor: str = "system"):
    if not db_path.exists():
        raise FileNotFoundError("Database not initialized")
    stages = ["qualified", "proposal", "closed"]
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        _ensure_crm_events_table(connection)
        row = connection.execute(
            f"SELECT id, status, account_id FROM {primary_table} WHERE id = ?",
            (item_id,),
        ).fetchone()
        if not row:
            return None
        current = str(dict(row).get("status") or "qualified").lower()
        try:
            index = stages.index(current)
        except ValueError:
            index = 0
        next_status = stages[min(index + 1, len(stages) - 1)]
        account_id = dict(row).get("account_id")
        connection.execute(f"UPDATE {primary_table} SET status = ? WHERE id = ?", (next_status, item_id))
        connection.commit()
    record_crm_event(db_path, "stage_advanced", item_id, account_id, actor, f"Moved deal to {next_status}")
    return {"id": item_id, "status": next_status}


def reassign_crm_deal_owner(db_path: Path, primary_table: str, item_id: int, owner: str, actor: str = "system"):
    if not db_path.exists():
        raise FileNotFoundError("Database not initialized")
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        _ensure_crm_events_table(connection)
        row = connection.execute(
            f"SELECT id, owner, account_id FROM {primary_table} WHERE id = ?",
            (item_id,),
        ).fetchone()
        if not row:
            return None
        account_id = dict(row).get("account_id")
        connection.execute(f"UPDATE {primary_table} SET owner = ? WHERE id = ?", (owner, item_id))
        connection.commit()
    record_crm_event(db_path, "owner_reassigned", item_id, account_id, actor, f"Reassigned deal to {owner}")
    return {"id": item_id, "owner": owner}
""",
    "backend_routes": """
@app.get('/api/crm/pipeline')
def get_crm_pipeline():
    db_path = SEED_FILE.with_name('app.db')
    return build_crm_pipeline(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.get('/api/crm/accounts')
def get_crm_accounts():
    db_path = SEED_FILE.with_name('app.db')
    return build_crm_accounts(db_path)

@app.get('/api/crm/account-health')
def get_crm_account_health():
    db_path = SEED_FILE.with_name('app.db')
    return build_crm_account_health(db_path, PRIMARY_TABLE)

@app.get('/api/crm/activity')
def get_crm_activity():
    db_path = SEED_FILE.with_name('app.db')
    return build_crm_activity(db_path, PRIMARY_TABLE)

@app.get('/api/crm/deals/{item_id}/snapshot')
def get_crm_deal_snapshot(item_id: int):
    db_path = SEED_FILE.with_name('app.db')
    snapshot = build_crm_deal_snapshot(db_path, PRIMARY_TABLE, item_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail='Deal not found')
    return snapshot

@app.post('/api/crm/deals/{item_id}/advance')
def advance_crm_deal(item_id: int, user_email: str | None = None):
    actor = user_email or _default_session()['email']
    _require_editor(actor)
    db_path = SEED_FILE.with_name('app.db')
    result = advance_crm_deal_status(db_path, PRIMARY_TABLE, item_id, actor=actor)
    if result is None:
        raise HTTPException(status_code=404, detail='Deal not found')
    session = SessionLocal()
    try:
        record_notification(session, PRIMARY_ENTITY, 'advanced', f"CRM deal moved to {result['status']}", item_id)
        session.commit()
        return {'deal': result}
    finally:
        session.close()

@app.post('/api/crm/deals/{item_id}/reassign')
def reassign_crm_deal(item_id: int, owner: str, user_email: str | None = None):
    actor = user_email or _default_session()['email']
    _require_editor(actor)
    db_path = SEED_FILE.with_name('app.db')
    result = reassign_crm_deal_owner(db_path, PRIMARY_TABLE, item_id, owner, actor=actor)
    if result is None:
        raise HTTPException(status_code=404, detail='Deal not found')
    session = SessionLocal()
    try:
        record_notification(session, PRIMARY_ENTITY, 'updated', f"CRM deal reassigned to {result['owner']}", item_id)
        session.commit()
        return {'deal': result}
    finally:
        session.close()
""",
    "frontend_import": "import { CrmFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function CrmFamilyPanel({ crmPipeline, crmForecast, crmAccounts, crmAccountHealth, crmActivity }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>CRM Pipeline</h2>
        <span className=\"role-pill\">Revenue operations</span>
      </div>
      <div className=\"stack\">
        <div className=\"section-row\">
          <strong>Forecast</strong>
          <p>Qualified {crmForecast.qualified} · Proposal {crmForecast.proposal} · Closed {crmForecast.closed}</p>
        </div>
        {crmPipeline.map((entry) => (
          <div className=\"section-row\" key={entry.id}>
            <strong>{entry.title}</strong>
            <p>{entry.account} · {entry.owner} · {entry.status} · ${entry.amount}</p>
          </div>
        ))}
        {crmAccountHealth.slice(0, 3).map((account) => (
          <div className=\"section-row\" key={`health-${account.id}`}>
            <strong>{account.name}</strong>
            <p>{account.segment} · {account.openDeals} open deals · ${account.pipelineValue}</p>
          </div>
        ))}
        {crmActivity.slice(0, 4).map((activity) => (
          <div className=\"section-row\" key={`activity-${activity.id}`}>
            <strong>{activity.summary}</strong>
            <p>{activity.actor} · {activity.eventType}</p>
          </div>
        ))}
        {crmAccounts.slice(0, 2).map((account) => (
          <div className=\"section-row\" key={`account-${account.id}`}>
            <strong>{account.name}</strong>
            <p>{account.segment} · {account.status}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
    "frontend": {
        "state": (
            "  const [crmPipeline, setCrmPipeline] = useState([]);\n"
            "  const [crmForecast, setCrmForecast] = useState({ qualified: 0, proposal: 0, closed: 0 });\n"
            "  const [crmAccounts, setCrmAccounts] = useState([]);\n"
            "  const [crmAccountHealth, setCrmAccountHealth] = useState([]);\n"
            "  const [crmActivity, setCrmActivity] = useState([]);\n"
        ),
        "loader": (
            "  async function loadCrmOperations() {\n"
            "    const [pipelineResponse, accountsResponse, accountHealthResponse, activityResponse] = await Promise.all([\n"
            "      fetch(`${API_BASE}/api/crm/pipeline`),\n"
            "      fetch(`${API_BASE}/api/crm/accounts`),\n"
            "      fetch(`${API_BASE}/api/crm/account-health`),\n"
            "      fetch(`${API_BASE}/api/crm/activity`),\n"
            "    ]);\n"
            "    const pipelineData = await pipelineResponse.json();\n"
            "    const accountsData = await accountsResponse.json();\n"
            "    const accountHealthData = await accountHealthResponse.json();\n"
            "    const activityData = await activityResponse.json();\n"
            "    setCrmPipeline(pipelineData.pipeline || []);\n"
            "    setCrmForecast(pipelineData.forecast || { qualified: 0, proposal: 0, closed: 0 });\n"
            "    setCrmAccounts(accountsData.accounts || []);\n"
            "    setCrmAccountHealth(accountHealthData.accounts || []);\n"
            "    setCrmActivity(activityData.activity || []);\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'crm_platform') {\n"
            "        await loadCrmOperations();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'crm_platform') {\n"
            "        await loadCrmOperations();\n"
            "      }\n"
        ),
        "after_integration": (
            "      if (config.appType === 'crm_platform') {\n"
            "        await loadCrmOperations();\n"
            "      }\n"
        ),
        "panel": "        <CrmFamilyPanel crmPipeline={crmPipeline} crmForecast={crmForecast} crmAccounts={crmAccounts} crmAccountHealth={crmAccountHealth} crmActivity={crmActivity} />\n\n",
    },
}


CRM_VALIDATION = {
    "backend_markers": (
        "@app.get('/api/crm/pipeline')",
        "@app.get('/api/crm/accounts')",
        "@app.get('/api/crm/account-health')",
        "@app.get('/api/crm/activity')",
        "@app.get('/api/crm/deals/{item_id}/snapshot')",
        "@app.post('/api/crm/deals/{item_id}/advance')",
        "@app.post('/api/crm/deals/{item_id}/reassign')",
    ),
    "frontend_markers": (
        "CrmFamilyPanel",
        "loadCrmOperations",
        "crmForecast",
        "crmAccountHealth",
        "crmActivity",
    ),
}
