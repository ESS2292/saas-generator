PROJECT_MANAGEMENT_EXTENSION = {
    "backend_import": "from family_logic import advance_project_status, build_project_board, build_project_milestones\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_project_board(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"board": [], "summary": {"planning": 0, "active": 0, "complete": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    board = []
    summary = {"planning": 0, "active": 0, "complete": 0}
    for row in rows:
        payload = dict(row)
        status = str(payload.get("status") or "planning").lower()
        if status in summary:
            summary[status] += 1
        board.append(
            {
                "id": payload.get("id"),
                "title": payload.get("title") or payload.get("name") or f"{primary_entity} #{payload.get('id')}",
                "owner": payload.get("owner") or "Unassigned",
                "status": status,
                "progress": payload.get("progress") or 0,
            }
        )
    return {"board": board, "summary": summary}


def build_project_milestones(db_path: Path):
    if not db_path.exists():
        return {"milestones": []}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        table_names = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "milestones" not in table_names:
            return {"milestones": []}
        rows = connection.execute("SELECT * FROM milestones ORDER BY id DESC LIMIT 25").fetchall()
    return {
        "milestones": [
            {
                "id": dict(row).get("id"),
                "name": dict(row).get("name") or f"Milestone #{dict(row).get('id')}",
                "status": dict(row).get("status") or "planning",
                "due_date": dict(row).get("due_date") or "TBD",
            }
            for row in rows
        ]
    }


def advance_project_status(db_path: Path, primary_table: str, item_id: int):
    if not db_path.exists():
        raise FileNotFoundError("Database not initialized")
    stages = [("planning", 25), ("active", 70), ("complete", 100)]
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(f"SELECT id, status FROM {primary_table} WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return None
        current = str(dict(row).get("status") or "planning").lower()
        statuses = [status for status, _progress in stages]
        try:
            index = statuses.index(current)
        except ValueError:
            index = 0
        next_status, next_progress = stages[min(index + 1, len(stages) - 1)]
        connection.execute(
            f"UPDATE {primary_table} SET status = ?, progress = ? WHERE id = ?",
            (next_status, next_progress, item_id),
        )
        connection.commit()
    return {"id": item_id, "status": next_status, "progress": next_progress}
""",
    "backend_routes": """
@app.get('/api/project-management/board')
def get_project_board():
    db_path = SEED_FILE.with_name('app.db')
    return build_project_board(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.get('/api/project-management/milestones')
def get_project_milestones():
    db_path = SEED_FILE.with_name('app.db')
    return build_project_milestones(db_path)

@app.post('/api/project-management/projects/{item_id}/advance')
def advance_project(item_id: int, user_email: str | None = None):
    _require_editor(user_email or _default_session()['email'])
    db_path = SEED_FILE.with_name('app.db')
    result = advance_project_status(db_path, PRIMARY_TABLE, item_id)
    if result is None:
        raise HTTPException(status_code=404, detail='Project not found')
    session = SessionLocal()
    try:
        record_notification(session, PRIMARY_ENTITY, 'advanced', f"Project moved to {result['status']}", item_id)
        session.commit()
        return {'project': result}
    finally:
        session.close()
""",
    "frontend_import": "import { ProjectManagementFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function ProjectManagementFamilyPanel({ projectBoard, projectSummary, projectMilestones }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>Project Delivery Board</h2>
        <span className=\"role-pill\">Delivery planning</span>
      </div>
      <div className=\"stack\">
        <div className=\"section-row\">
          <strong>Delivery Summary</strong>
          <p>Planning {projectSummary.planning} · Active {projectSummary.active} · Complete {projectSummary.complete}</p>
        </div>
        {projectBoard.map((item) => (
          <div className=\"section-row\" key={item.id}>
            <strong>{item.title}</strong>
            <p>{item.owner} · {item.status} · {item.progress}%</p>
          </div>
        ))}
        {projectMilestones.slice(0, 3).map((item) => (
          <div className=\"section-row\" key={`milestone-${item.id}`}>
            <strong>{item.name}</strong>
            <p>{item.status} · due {item.due_date}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
    "frontend": {
        "state": (
            "  const [projectBoard, setProjectBoard] = useState([]);\n"
            "  const [projectSummary, setProjectSummary] = useState({ planning: 0, active: 0, complete: 0 });\n"
            "  const [projectMilestones, setProjectMilestones] = useState([]);\n"
        ),
        "loader": (
            "  async function loadProjectOperations() {\n"
            "    const [boardResponse, milestonesResponse] = await Promise.all([\n"
            "      fetch(`${API_BASE}/api/project-management/board`),\n"
            "      fetch(`${API_BASE}/api/project-management/milestones`),\n"
            "    ]);\n"
            "    const boardData = await boardResponse.json();\n"
            "    const milestonesData = await milestonesResponse.json();\n"
            "    setProjectBoard(boardData.board || []);\n"
            "    setProjectSummary(boardData.summary || { planning: 0, active: 0, complete: 0 });\n"
            "    setProjectMilestones(milestonesData.milestones || []);\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'project_management') {\n"
            "        await loadProjectOperations();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'project_management') {\n"
            "        await loadProjectOperations();\n"
            "      }\n"
        ),
        "after_integration": "",
        "panel": "        <ProjectManagementFamilyPanel projectBoard={projectBoard} projectSummary={projectSummary} projectMilestones={projectMilestones} />\n\n",
    },
}


PROJECT_MANAGEMENT_VALIDATION = {
    "backend_markers": ("@app.get('/api/project-management/board')", "@app.get('/api/project-management/milestones')", "@app.post('/api/project-management/projects/{item_id}/advance')"),
    "frontend_markers": ("ProjectManagementFamilyPanel", "loadProjectOperations", "projectSummary"),
}
