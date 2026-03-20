SUPPORT_EXTENSION = {
    "backend_import": "from family_logic import build_support_escalations, build_support_queue, escalate_support_ticket\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_support_queue(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"queue": [], "summary": {"open": 0, "pending": 0, "high": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    queue = []
    summary = {"open": 0, "pending": 0, "high": 0}
    for row in rows:
        payload = dict(row)
        status = str(payload.get("status") or "open").lower()
        priority = str(payload.get("priority") or "medium").lower()
        if status in {"open", "pending"}:
            summary[status] += 1
        if priority == "high":
            summary["high"] += 1
        queue.append(
            {
                "id": payload.get("id"),
                "title": payload.get("title") or payload.get("name") or f"{primary_entity} #{payload.get('id')}",
                "priority": priority,
                "status": status,
                "assignee": payload.get("assignee") or "Unassigned",
            }
        )
    return {"queue": queue, "summary": summary}


def build_support_escalations(db_path: Path, primary_entity: str, primary_table: str):
    queue = build_support_queue(db_path, primary_entity, primary_table)["queue"]
    escalations = [item for item in queue if item["priority"] == "high" or item["status"] in {"pending", "escalated"}]
    return {"escalations": escalations[:10]}


def escalate_support_ticket(db_path: Path, primary_table: str, item_id: int):
    if not db_path.exists():
        raise FileNotFoundError("Database not initialized")
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            f"UPDATE {primary_table} SET status = ?, priority = ? WHERE id = ?",
            ("escalated", "high", item_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
    return {"id": item_id, "status": "escalated", "priority": "high"}
""",
    "backend_routes": """
@app.get('/api/support/queue')
def get_support_queue():
    db_path = SEED_FILE.with_name('app.db')
    return build_support_queue(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.get('/api/support/escalations')
def get_support_escalations():
    db_path = SEED_FILE.with_name('app.db')
    return build_support_escalations(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.post('/api/support/tickets/{item_id}/escalate')
def escalate_ticket(item_id: int, user_email: str | None = None):
    _require_editor(user_email or _default_session()['email'])
    db_path = SEED_FILE.with_name('app.db')
    result = escalate_support_ticket(db_path, PRIMARY_TABLE, item_id)
    if result is None:
        raise HTTPException(status_code=404, detail='Ticket not found')
    session = SessionLocal()
    try:
        record_notification(session, PRIMARY_ENTITY, 'escalated', "Support ticket escalated", item_id)
        session.commit()
        return {'ticket': result}
    finally:
        session.close()
""",
    "frontend_import": "import { SupportFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function SupportFamilyPanel({ supportSummary, supportEscalations }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>Support Escalations</h2>
        <span className=\"role-pill\">Customer operations</span>
      </div>
      <div className=\"stack\">
        <div className=\"section-row\">
          <strong>Queue Summary</strong>
          <p>Open {supportSummary.open} · Pending {supportSummary.pending} · High {supportSummary.high}</p>
        </div>
        {supportEscalations.map((item) => (
          <div className=\"section-row\" key={item.id}>
            <strong>{item.title}</strong>
            <p>{item.assignee} · {item.priority} · {item.status}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
    "frontend": {
        "state": (
            "  const [supportSummary, setSupportSummary] = useState({ open: 0, pending: 0, high: 0 });\n"
            "  const [supportEscalations, setSupportEscalations] = useState([]);\n"
        ),
        "loader": (
            "  async function loadSupportOperations() {\n"
            "    const [queueResponse, escalationsResponse] = await Promise.all([\n"
            "      fetch(`${API_BASE}/api/support/queue`),\n"
            "      fetch(`${API_BASE}/api/support/escalations`),\n"
            "    ]);\n"
            "    const queueData = await queueResponse.json();\n"
            "    const escalationsData = await escalationsResponse.json();\n"
            "    setSupportSummary(queueData.summary || { open: 0, pending: 0, high: 0 });\n"
            "    setSupportEscalations(escalationsData.escalations || []);\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'support_desk') {\n"
            "        await loadSupportOperations();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'support_desk') {\n"
            "        await loadSupportOperations();\n"
            "      }\n"
        ),
        "after_integration": "",
        "panel": "        <SupportFamilyPanel supportSummary={supportSummary} supportEscalations={supportEscalations} />\n\n",
    },
}


SUPPORT_VALIDATION = {
    "backend_markers": ("@app.get('/api/support/queue')", "@app.get('/api/support/escalations')", "@app.post('/api/support/tickets/{item_id}/escalate')"),
    "frontend_markers": ("SupportFamilyPanel", "loadSupportOperations", "supportEscalations"),
}
