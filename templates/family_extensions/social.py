SOCIAL_EXTENSION = {
    "backend_import": "from family_logic import build_social_engagement, build_social_moderation\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_social_engagement(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"posts": [], "engagement": {"active": 0, "flagged": 0, "members": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    posts = []
    engagement = {"active": 0, "flagged": 0, "members": 0}
    for row in rows:
        payload = dict(row)
        status = str(payload.get("status") or "active").lower()
        if status in {"active", "flagged"}:
            engagement[status] += 1
        engagement["members"] += 1
        posts.append(
            {
                "id": payload.get("id"),
                "title": payload.get("title") or payload.get("name") or f"{primary_entity} #{payload.get('id')}",
                "author": payload.get("author") or payload.get("member") or payload.get("user") or "Unknown member",
                "status": status,
                "content": payload.get("content") or payload.get("body") or "",
            }
        )
    return {"posts": posts, "engagement": engagement}


def build_social_moderation(db_path: Path, primary_entity: str, primary_table: str):
    posts = build_social_engagement(db_path, primary_entity, primary_table)["posts"]
    return {"flagged": [post for post in posts if post["status"] == "flagged"][:10]}
""",
    "backend_routes": """
@app.get('/api/social/engagement')
def get_social_engagement():
    db_path = SEED_FILE.with_name('app.db')
    return build_social_engagement(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.get('/api/social/moderation')
def get_social_moderation():
    db_path = SEED_FILE.with_name('app.db')
    return build_social_moderation(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)
""",
    "frontend_import": "import { SocialFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function SocialFamilyPanel({ engagementSummary, flaggedPosts }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>Community Pulse</h2>
        <span className=\"role-pill\">Engagement and moderation</span>
      </div>
      <div className=\"stack\">
        <div className=\"section-row\">
          <strong>Engagement</strong>
          <p>Active {engagementSummary.active} · Flagged {engagementSummary.flagged} · Member Touchpoints {engagementSummary.members}</p>
        </div>
        {flaggedPosts.map((post) => (
          <div className=\"section-row\" key={post.id}>
            <strong>{post.title}</strong>
            <p>{post.author} · {post.status}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
    "frontend": {
        "state": (
            "  const [engagementSummary, setEngagementSummary] = useState({ active: 0, flagged: 0, members: 0 });\n"
            "  const [flaggedPosts, setFlaggedPosts] = useState([]);\n"
        ),
        "loader": (
            "  async function loadSocialActivity() {\n"
            "    const [engagementResponse, moderationResponse] = await Promise.all([\n"
            "      fetch(`${API_BASE}/api/social/engagement`),\n"
            "      fetch(`${API_BASE}/api/social/moderation`),\n"
            "    ]);\n"
            "    const engagementData = await engagementResponse.json();\n"
            "    const moderationData = await moderationResponse.json();\n"
            "    setEngagementSummary(engagementData.engagement || { active: 0, flagged: 0, members: 0 });\n"
            "    setFlaggedPosts(moderationData.flagged || []);\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'social_app') {\n"
            "        await loadSocialActivity();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'social_app') {\n"
            "        await loadSocialActivity();\n"
            "      }\n"
        ),
        "after_integration": "",
        "panel": "        <SocialFamilyPanel engagementSummary={engagementSummary} flaggedPosts={flaggedPosts} />\n\n",
    },
}


SOCIAL_VALIDATION = {
    "backend_markers": ("@app.get('/api/social/engagement')", "@app.get('/api/social/moderation')"),
    "frontend_markers": ("SocialFamilyPanel", "loadSocialActivity", "engagementSummary"),
}
