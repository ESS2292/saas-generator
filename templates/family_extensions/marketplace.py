MARKETPLACE_EXTENSION = {
    "backend_import": "from family_logic import build_marketplace_activity, moderate_marketplace_item_status\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_marketplace_activity(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"activity": [], "moderation": {"pending": 0, "active": 0, "archived": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    activity = []
    moderation = {"pending": 0, "active": 0, "archived": 0}
    for row in rows:
        payload = dict(row)
        status = str(payload.get("status") or "active").lower()
        if status in moderation:
            moderation[status] += 1
        activity.append(
            {
                "id": payload.get("id"),
                "title": payload.get("title") or payload.get("name") or f"{primary_entity} #{payload.get('id')}",
                "seller": payload.get("seller") or payload.get("owner") or payload.get("provider") or "Unknown seller",
                "status": status,
                "price": payload.get("price") or payload.get("amount") or payload.get("value") or "",
            }
        )
    return {"activity": activity, "moderation": moderation}


def moderate_marketplace_item_status(db_path: Path, primary_table: str, item_id: int, next_status: str):
    if not db_path.exists():
        raise FileNotFoundError("Database not initialized")
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(f"UPDATE {primary_table} SET status = ? WHERE id = ?", (next_status, item_id))
        connection.commit()
        return cursor.rowcount
""",
    "backend_routes": """
@app.get('/api/marketplace/activity')
def get_marketplace_activity():
    db_path = SEED_FILE.with_name('app.db')
    return build_marketplace_activity(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.post('/api/marketplace/moderation/{item_id}')
def moderate_marketplace_item(item_id: int, payload: dict, user_email: str | None = None):
    _require_editor(user_email or _default_session()['email'])
    next_status = str(payload.get('status') or 'active')
    db_path = SEED_FILE.with_name('app.db')
    if moderate_marketplace_item_status(db_path, PRIMARY_TABLE, item_id, next_status) == 0:
        raise HTTPException(status_code=404, detail='Item not found')
    session = SessionLocal()
    try:
        record_notification(session, PRIMARY_ENTITY, 'moderated', f"Marketplace item moved to {next_status}", item_id)
        session.commit()
        return {'item': {'id': item_id, 'status': next_status}}
    finally:
        session.close()
""",
    "frontend_import": "import { MarketplaceFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function MarketplaceFamilyPanel({ marketplaceActivity, marketplaceModeration }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>Marketplace Activity</h2>
        <span className=\"role-pill\">Buyer and seller flow</span>
      </div>
      <div className=\"stack\">
        <div className=\"section-row\">
          <strong>Moderation Queue</strong>
          <p>Pending {marketplaceModeration.pending} · Active {marketplaceModeration.active} · Archived {marketplaceModeration.archived}</p>
        </div>
        {marketplaceActivity.map((entry) => (
          <div className=\"section-row\" key={entry.id}>
            <strong>{entry.title}</strong>
            <p>{entry.seller} · {entry.status} · {entry.price || 'Price TBD'}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
    "frontend": {
        "state": (
            "  const [marketplaceActivity, setMarketplaceActivity] = useState([]);\n"
            "  const [marketplaceModeration, setMarketplaceModeration] = useState({ pending: 0, active: 0, archived: 0 });\n"
        ),
        "loader": (
            "  async function loadMarketplaceActivity() {\n"
            "    const response = await fetch(`${API_BASE}/api/marketplace/activity`);\n"
            "    const data = await response.json();\n"
            "    setMarketplaceActivity(data.activity || []);\n"
            "    setMarketplaceModeration(data.moderation || { pending: 0, active: 0, archived: 0 });\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'marketplace') {\n"
            "        await loadMarketplaceActivity();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'marketplace') {\n"
            "        await loadMarketplaceActivity();\n"
            "      }\n"
        ),
        "after_integration": (
            "      if (config.appType === 'marketplace') {\n"
            "        await loadMarketplaceActivity();\n"
            "      }\n"
        ),
        "panel": "        <MarketplaceFamilyPanel marketplaceActivity={marketplaceActivity} marketplaceModeration={marketplaceModeration} />\n\n",
    },
}


MARKETPLACE_VALIDATION = {
    "backend_markers": (
        "@app.get('/api/marketplace/activity')",
        "@app.post('/api/marketplace/moderation/{item_id}')",
    ),
    "frontend_markers": ("MarketplaceFamilyPanel", "loadMarketplaceActivity", "marketplaceModeration"),
}
