INTERNAL_TOOL_EXTENSION = {
    "backend_import": "from family_logic import build_internal_approvals, build_internal_queue\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_internal_queue(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"queue": [], "summary": {"open": 0, "pending": 0, "high_priority": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    queue = []
    summary = {"open": 0, "pending": 0, "high_priority": 0}
    for row in rows:
        payload = dict(row)
        status = str(payload.get("status") or "open").lower()
        priority = str(payload.get("priority") or "medium").lower()
        if status in {"open", "pending"}:
            summary[status] += 1
        if priority == "high":
            summary["high_priority"] += 1
        queue.append(
            {
                "id": payload.get("id"),
                "title": payload.get("title") or payload.get("name") or f"{primary_entity} #{payload.get('id')}",
                "status": status,
                "priority": priority,
                "assignee": payload.get("assignee") or payload.get("owner") or payload.get("operator") or "Unassigned",
            }
        )
    return {"queue": queue, "summary": summary}


def build_internal_approvals(db_path: Path, primary_entity: str, primary_table: str):
    queue = build_internal_queue(db_path, primary_entity, primary_table)["queue"]
    approvals = [item for item in queue if item["status"] in {"pending", "review"}]
    return {"approvals": approvals[:10]}
""",
    "backend_routes": """
@app.get('/api/internal/queue')
def get_internal_queue():
    db_path = SEED_FILE.with_name('app.db')
    return build_internal_queue(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.get('/api/internal/approvals')
def get_internal_approvals():
    db_path = SEED_FILE.with_name('app.db')
    return build_internal_approvals(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)
""",
    "frontend_import": "import { InternalToolFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function InternalToolFamilyPanel({ queueSummary, approvals }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>Operations Queue</h2>
        <span className=\"role-pill\">Internal ops flow</span>
      </div>
      <div className=\"stack\">
        <div className=\"section-row\">
          <strong>Queue Summary</strong>
          <p>Open {queueSummary.open} · Pending {queueSummary.pending} · High Priority {queueSummary.high_priority}</p>
        </div>
        {approvals.map((item) => (
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
            "  const [queueSummary, setQueueSummary] = useState({ open: 0, pending: 0, high_priority: 0 });\n"
            "  const [approvals, setApprovals] = useState([]);\n"
        ),
        "loader": (
            "  async function loadInternalOperations() {\n"
            "    const [queueResponse, approvalsResponse] = await Promise.all([\n"
            "      fetch(`${API_BASE}/api/internal/queue`),\n"
            "      fetch(`${API_BASE}/api/internal/approvals`),\n"
            "    ]);\n"
            "    const queueData = await queueResponse.json();\n"
            "    const approvalsData = await approvalsResponse.json();\n"
            "    setQueueSummary(queueData.summary || { open: 0, pending: 0, high_priority: 0 });\n"
            "    setApprovals(approvalsData.approvals || []);\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'internal_tool') {\n"
            "        await loadInternalOperations();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'internal_tool') {\n"
            "        await loadInternalOperations();\n"
            "      }\n"
        ),
        "after_integration": "",
        "panel": "        <InternalToolFamilyPanel queueSummary={queueSummary} approvals={approvals} />\n\n",
    },
}


INTERNAL_TOOL_VALIDATION = {
    "backend_markers": ("@app.get('/api/internal/queue')", "@app.get('/api/internal/approvals')"),
    "frontend_markers": ("InternalToolFamilyPanel", "loadInternalOperations", "queueSummary"),
}
