RECRUITING_EXTENSION = {
    "backend_import": "from family_logic import advance_candidate_stage, build_recruiting_interviews, build_recruiting_pipeline\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_recruiting_pipeline(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"pipeline": [], "summary": {"screen": 0, "interview": 0, "offer": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    summary = {"screen": 0, "interview": 0, "offer": 0}
    pipeline = []
    for row in rows:
        payload = dict(row)
        status = str(payload.get("status") or "screen").lower()
        if status in summary:
            summary[status] += 1
        pipeline.append(
            {
                "id": payload.get("id"),
                "name": payload.get("name") or payload.get("title") or f"{primary_entity} #{payload.get('id')}",
                "status": status,
                "recruiter": payload.get("recruiter") or "Unassigned",
                "score": payload.get("score") or 0,
            }
        )
    return {"pipeline": pipeline, "summary": summary}


def build_recruiting_interviews(db_path: Path):
    if not db_path.exists():
        return {"interviews": []}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        table_names = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "interviews" not in table_names:
            return {"interviews": []}
        rows = connection.execute("SELECT * FROM interviews ORDER BY id DESC LIMIT 25").fetchall()
    return {
        "interviews": [
            {
                "id": dict(row).get("id"),
                "title": dict(row).get("title") or f"Interview #{dict(row).get('id')}",
                "status": dict(row).get("status") or "scheduled",
                "scheduled_for": dict(row).get("scheduled_for") or "TBD",
            }
            for row in rows
        ]
    }


def advance_candidate_stage(db_path: Path, primary_table: str, item_id: int):
    if not db_path.exists():
        raise FileNotFoundError("Database not initialized")
    stages = ["screen", "interview", "offer", "hired"]
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(f"SELECT id, status FROM {primary_table} WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return None
        current = str(dict(row).get("status") or "screen").lower()
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
@app.get('/api/recruiting/pipeline')
def get_recruiting_pipeline():
    db_path = SEED_FILE.with_name('app.db')
    return build_recruiting_pipeline(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.get('/api/recruiting/interviews')
def get_recruiting_interviews():
    db_path = SEED_FILE.with_name('app.db')
    return build_recruiting_interviews(db_path)

@app.post('/api/recruiting/candidates/{item_id}/advance')
def advance_recruiting_candidate(item_id: int, user_email: str | None = None):
    _require_editor(user_email or _default_session()['email'])
    db_path = SEED_FILE.with_name('app.db')
    result = advance_candidate_stage(db_path, PRIMARY_TABLE, item_id)
    if result is None:
        raise HTTPException(status_code=404, detail='Candidate not found')
    session = SessionLocal()
    try:
        record_notification(session, PRIMARY_ENTITY, 'advanced', f"Candidate moved to {result['status']}", item_id)
        session.commit()
        return {'candidate': result}
    finally:
        session.close()
""",
    "frontend_import": "import { RecruitingFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function RecruitingFamilyPanel({ recruitingSummary, recruitingPipeline, recruitingInterviews }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>Recruiting Pipeline</h2>
        <span className=\"role-pill\">Hiring operations</span>
      </div>
      <div className=\"stack\">
        <div className=\"section-row\">
          <strong>Stage Mix</strong>
          <p>Screen {recruitingSummary.screen} · Interview {recruitingSummary.interview} · Offer {recruitingSummary.offer}</p>
        </div>
        {recruitingPipeline.map((entry) => (
          <div className=\"section-row\" key={entry.id}>
            <strong>{entry.name}</strong>
            <p>{entry.recruiter} · {entry.status} · Score {entry.score}</p>
          </div>
        ))}
        {recruitingInterviews.slice(0, 3).map((interview) => (
          <div className=\"section-row\" key={`interview-${interview.id}`}>
            <strong>{interview.title}</strong>
            <p>{interview.scheduled_for} · {interview.status}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
    "frontend": {
        "state": (
            "  const [recruitingSummary, setRecruitingSummary] = useState({ screen: 0, interview: 0, offer: 0 });\n"
            "  const [recruitingPipeline, setRecruitingPipeline] = useState([]);\n"
            "  const [recruitingInterviews, setRecruitingInterviews] = useState([]);\n"
        ),
        "loader": (
            "  async function loadRecruitingOperations() {\n"
            "    const [pipelineResponse, interviewsResponse] = await Promise.all([\n"
            "      fetch(`${API_BASE}/api/recruiting/pipeline`),\n"
            "      fetch(`${API_BASE}/api/recruiting/interviews`),\n"
            "    ]);\n"
            "    const pipelineData = await pipelineResponse.json();\n"
            "    const interviewsData = await interviewsResponse.json();\n"
            "    setRecruitingSummary(pipelineData.summary || { screen: 0, interview: 0, offer: 0 });\n"
            "    setRecruitingPipeline(pipelineData.pipeline || []);\n"
            "    setRecruitingInterviews(interviewsData.interviews || []);\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'recruiting_platform') {\n"
            "        await loadRecruitingOperations();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'recruiting_platform') {\n"
            "        await loadRecruitingOperations();\n"
            "      }\n"
        ),
        "after_integration": "",
        "panel": "        <RecruitingFamilyPanel recruitingSummary={recruitingSummary} recruitingPipeline={recruitingPipeline} recruitingInterviews={recruitingInterviews} />\n\n",
    },
}


RECRUITING_VALIDATION = {
    "backend_markers": ("@app.get('/api/recruiting/pipeline')", "@app.get('/api/recruiting/interviews')", "@app.post('/api/recruiting/candidates/{item_id}/advance')"),
    "frontend_markers": ("RecruitingFamilyPanel", "loadRecruitingOperations", "recruitingPipeline"),
}
