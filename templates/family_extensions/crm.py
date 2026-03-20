CRM_EXTENSION = {
    "backend_import": "from family_logic import advance_crm_deal_status, build_crm_accounts, build_crm_pipeline\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_crm_pipeline(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"pipeline": [], "forecast": {"qualified": 0, "proposal": 0, "closed": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
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
            }
        )
    return {"pipeline": pipeline, "forecast": forecast}


def build_crm_accounts(db_path: Path):
    if not db_path.exists():
        return {"accounts": []}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        table_names = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        account_table = "accounts" if "accounts" in table_names else None
        if not account_table:
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


def advance_crm_deal_status(db_path: Path, primary_table: str, item_id: int):
    if not db_path.exists():
        raise FileNotFoundError("Database not initialized")
    stages = ["qualified", "proposal", "closed"]
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(f"SELECT id, status FROM {primary_table} WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return None
        current = str(dict(row).get("status") or "qualified").lower()
        try:
            index = stages.index(current)
        except ValueError:
            index = 0
        next_status = stages[min(index + 1, len(stages) - 1)]
        connection.execute(f"UPDATE {primary_table} SET status = ? WHERE id = ?", (next_status, item_id))
        connection.commit()
    return {"id": item_id, "status": next_status}
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

@app.post('/api/crm/deals/{item_id}/advance')
def advance_crm_deal(item_id: int, user_email: str | None = None):
    _require_editor(user_email or _default_session()['email'])
    db_path = SEED_FILE.with_name('app.db')
    result = advance_crm_deal_status(db_path, PRIMARY_TABLE, item_id)
    if result is None:
        raise HTTPException(status_code=404, detail='Deal not found')
    session = SessionLocal()
    try:
        record_notification(session, PRIMARY_ENTITY, 'advanced', f"CRM deal moved to {result['status']}", item_id)
        session.commit()
        return {'deal': result}
    finally:
        session.close()
""",
    "frontend_import": "import { CrmFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function CrmFamilyPanel({ crmPipeline, crmForecast, crmAccounts }) {
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
            <p>{entry.owner} · {entry.status} · ${entry.amount}</p>
          </div>
        ))}
        {crmAccounts.slice(0, 3).map((account) => (
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
        ),
        "loader": (
            "  async function loadCrmOperations() {\n"
            "    const [pipelineResponse, accountsResponse] = await Promise.all([\n"
            "      fetch(`${API_BASE}/api/crm/pipeline`),\n"
            "      fetch(`${API_BASE}/api/crm/accounts`),\n"
            "    ]);\n"
            "    const pipelineData = await pipelineResponse.json();\n"
            "    const accountsData = await accountsResponse.json();\n"
            "    setCrmPipeline(pipelineData.pipeline || []);\n"
            "    setCrmForecast(pipelineData.forecast || { qualified: 0, proposal: 0, closed: 0 });\n"
            "    setCrmAccounts(accountsData.accounts || []);\n"
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
        "panel": "        <CrmFamilyPanel crmPipeline={crmPipeline} crmForecast={crmForecast} crmAccounts={crmAccounts} />\n\n",
    },
}


CRM_VALIDATION = {
    "backend_markers": ("@app.get('/api/crm/pipeline')", "@app.get('/api/crm/accounts')", "@app.post('/api/crm/deals/{item_id}/advance')"),
    "frontend_markers": ("CrmFamilyPanel", "loadCrmOperations", "crmForecast"),
}
