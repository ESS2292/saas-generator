CONTENT_EXTENSION = {
    "backend_import": "from family_logic import build_content_calendar, build_content_pipeline\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_content_pipeline(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"pipeline": [], "status_breakdown": {"draft": 0, "scheduled": 0, "published": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    pipeline = []
    status_breakdown = {"draft": 0, "scheduled": 0, "published": 0}
    for row in rows:
        payload = dict(row)
        status = str(payload.get("status") or "draft").lower()
        if status in status_breakdown:
            status_breakdown[status] += 1
        pipeline.append(
            {
                "id": payload.get("id"),
                "title": payload.get("title") or payload.get("headline") or f"{primary_entity} #{payload.get('id')}",
                "author": payload.get("author") or payload.get("owner") or "Unknown author",
                "publish_date": payload.get("publish_date") or payload.get("scheduled_for") or "TBD",
                "status": status,
            }
        )
    return {"pipeline": pipeline, "status_breakdown": status_breakdown}


def build_content_calendar(db_path: Path, primary_entity: str, primary_table: str):
    pipeline = build_content_pipeline(db_path, primary_entity, primary_table)["pipeline"]
    return {"calendar": [item for item in pipeline if item["publish_date"] != "TBD"][:10]}
""",
    "backend_routes": """
@app.get('/api/content/pipeline')
def get_content_pipeline():
    db_path = SEED_FILE.with_name('app.db')
    return build_content_pipeline(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.get('/api/content/calendar')
def get_content_calendar():
    db_path = SEED_FILE.with_name('app.db')
    return build_content_calendar(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)
""",
    "frontend_import": "import { ContentFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function ContentFamilyPanel({ publishingBreakdown, publishingCalendar }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>Publishing Pipeline</h2>
        <span className=\"role-pill\">Editorial flow</span>
      </div>
      <div className=\"stack\">
        <div className=\"section-row\">
          <strong>Pipeline Status</strong>
          <p>Draft {publishingBreakdown.draft} · Scheduled {publishingBreakdown.scheduled} · Published {publishingBreakdown.published}</p>
        </div>
        {publishingCalendar.map((item) => (
          <div className=\"section-row\" key={item.id}>
            <strong>{item.title}</strong>
            <p>{item.author} · {item.publish_date} · {item.status}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
    "frontend": {
        "state": (
            "  const [publishingBreakdown, setPublishingBreakdown] = useState({ draft: 0, scheduled: 0, published: 0 });\n"
            "  const [publishingCalendar, setPublishingCalendar] = useState([]);\n"
        ),
        "loader": (
            "  async function loadContentOperations() {\n"
            "    const [pipelineResponse, calendarResponse] = await Promise.all([\n"
            "      fetch(`${API_BASE}/api/content/pipeline`),\n"
            "      fetch(`${API_BASE}/api/content/calendar`),\n"
            "    ]);\n"
            "    const pipelineData = await pipelineResponse.json();\n"
            "    const calendarData = await calendarResponse.json();\n"
            "    setPublishingBreakdown(pipelineData.status_breakdown || { draft: 0, scheduled: 0, published: 0 });\n"
            "    setPublishingCalendar(calendarData.calendar || []);\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'content_platform') {\n"
            "        await loadContentOperations();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'content_platform') {\n"
            "        await loadContentOperations();\n"
            "      }\n"
        ),
        "after_integration": "",
        "panel": "        <ContentFamilyPanel publishingBreakdown={publishingBreakdown} publishingCalendar={publishingCalendar} />\n\n",
    },
}


CONTENT_VALIDATION = {
    "backend_markers": ("@app.get('/api/content/pipeline')", "@app.get('/api/content/calendar')"),
    "frontend_markers": ("ContentFamilyPanel", "loadContentOperations", "publishingBreakdown"),
}
