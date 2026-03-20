LEARNING_EXTENSION = {
    "backend_import": "from family_logic import build_learning_progress, build_learning_readiness\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_learning_progress(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"courses": [], "progress": {"active": 0, "draft": 0, "average_progress": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    courses = []
    progress = {"active": 0, "draft": 0, "average_progress": 0}
    total_progress = 0
    for row in rows:
        payload = dict(row)
        status = str(payload.get("status") or "active").lower()
        if status in {"active", "draft"}:
            progress[status] += 1
        course_progress = int(payload.get("progress") or 0)
        total_progress += course_progress
        courses.append(
            {
                "id": payload.get("id"),
                "title": payload.get("title") or payload.get("name") or f"{primary_entity} #{payload.get('id')}",
                "status": status,
                "progress": course_progress,
            }
        )
    progress["average_progress"] = int(total_progress / len(courses)) if courses else 0
    return {"courses": courses, "progress": progress}


def build_learning_readiness(db_path: Path, primary_entity: str, primary_table: str):
    courses = build_learning_progress(db_path, primary_entity, primary_table)["courses"]
    return {"lessons": courses[:10]}
""",
    "backend_routes": """
@app.get('/api/learning/progress')
def get_learning_progress():
    db_path = SEED_FILE.with_name('app.db')
    return build_learning_progress(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.get('/api/learning/lessons')
def get_learning_readiness():
    db_path = SEED_FILE.with_name('app.db')
    return build_learning_readiness(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)
""",
    "frontend_import": "import { LearningFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function LearningFamilyPanel({ learningProgress, lessonReadiness }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>Learning Progress</h2>
        <span className=\"role-pill\">Course delivery</span>
      </div>
      <div className=\"stack\">
        <div className=\"section-row\">
          <strong>Progress Summary</strong>
          <p>Active {learningProgress.active} · Draft {learningProgress.draft} · Avg Progress {learningProgress.average_progress}%</p>
        </div>
        {lessonReadiness.map((course) => (
          <div className=\"section-row\" key={course.id}>
            <strong>{course.title}</strong>
            <p>{course.status} · {course.progress}% complete</p>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
    "frontend": {
        "state": (
            "  const [learningProgress, setLearningProgress] = useState({ active: 0, draft: 0, average_progress: 0 });\n"
            "  const [lessonReadiness, setLessonReadiness] = useState([]);\n"
        ),
        "loader": (
            "  async function loadLearningProgress() {\n"
            "    const [progressResponse, lessonsResponse] = await Promise.all([\n"
            "      fetch(`${API_BASE}/api/learning/progress`),\n"
            "      fetch(`${API_BASE}/api/learning/lessons`),\n"
            "    ]);\n"
            "    const progressData = await progressResponse.json();\n"
            "    const lessonsData = await lessonsResponse.json();\n"
            "    setLearningProgress(progressData.progress || { active: 0, draft: 0, average_progress: 0 });\n"
            "    setLessonReadiness(lessonsData.lessons || []);\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'learning_platform') {\n"
            "        await loadLearningProgress();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'learning_platform') {\n"
            "        await loadLearningProgress();\n"
            "      }\n"
        ),
        "after_integration": "",
        "panel": "        <LearningFamilyPanel learningProgress={learningProgress} lessonReadiness={lessonReadiness} />\n\n",
    },
}


LEARNING_VALIDATION = {
    "backend_markers": ("@app.get('/api/learning/progress')", "@app.get('/api/learning/lessons')"),
    "frontend_markers": ("LearningFamilyPanel", "loadLearningProgress", "lessonReadiness"),
}
