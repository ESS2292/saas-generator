ECOMMERCE_EXTENSION = {
    "backend_import": "from family_logic import advance_order_status, build_order_pipeline\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_order_pipeline(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"orders": [], "fulfillment": {"pending": 0, "processing": 0, "shipped": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    orders = []
    fulfillment = {"pending": 0, "processing": 0, "shipped": 0}
    for row in rows:
        payload = dict(row)
        status = str(payload.get("status") or "pending").lower()
        if status in fulfillment:
            fulfillment[status] += 1
        orders.append(
            {
                "id": payload.get("id"),
                "label": payload.get("title") or payload.get("name") or f"{primary_entity} #{payload.get('id')}",
                "customer": payload.get("customer") or payload.get("buyer") or payload.get("email") or "Unknown customer",
                "status": status,
                "amount": payload.get("amount") or payload.get("price") or payload.get("value") or "",
            }
        )
    return {"orders": orders, "fulfillment": fulfillment}


def advance_order_status(db_path: Path, primary_table: str, item_id: int, next_status: str):
    if not db_path.exists():
        raise FileNotFoundError("Database not initialized")
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(f"UPDATE {primary_table} SET status = ? WHERE id = ?", (next_status, item_id))
        connection.commit()
        return cursor.rowcount
""",
    "backend_routes": """
@app.get('/api/ecommerce/orders')
def get_order_pipeline():
    db_path = SEED_FILE.with_name('app.db')
    return build_order_pipeline(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.post('/api/ecommerce/orders/{item_id}/advance')
def advance_order(item_id: int, payload: dict | None = None, user_email: str | None = None):
    _require_editor(user_email or _default_session()['email'])
    payload = payload or {}
    next_status = str(payload.get('status') or 'processing')
    db_path = SEED_FILE.with_name('app.db')
    if advance_order_status(db_path, PRIMARY_TABLE, item_id, next_status) == 0:
        raise HTTPException(status_code=404, detail='Order not found')
    session = SessionLocal()
    try:
        record_notification(session, PRIMARY_ENTITY, 'fulfillment', f"Order advanced to {next_status}", item_id)
        session.commit()
        return {'order': {'id': item_id, 'status': next_status}}
    finally:
        session.close()
""",
    "frontend_import": "import { EcommerceFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function EcommerceFamilyPanel({ fulfillmentSummary, orderPipeline }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>Fulfillment Board</h2>
        <span className=\"role-pill\">Order pipeline</span>
      </div>
      <div className=\"stack\">
        <div className=\"section-row\">
          <strong>Fulfillment Status</strong>
          <p>Pending {fulfillmentSummary.pending} · Processing {fulfillmentSummary.processing} · Shipped {fulfillmentSummary.shipped}</p>
        </div>
        {orderPipeline.map((order) => (
          <div className=\"section-row\" key={order.id}>
            <strong>{order.label}</strong>
            <p>{order.customer} · {order.status} · {order.amount || 'Amount TBD'}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
    "frontend": {
        "state": (
            "  const [orderPipeline, setOrderPipeline] = useState([]);\n"
            "  const [fulfillmentSummary, setFulfillmentSummary] = useState({ pending: 0, processing: 0, shipped: 0 });\n"
        ),
        "loader": (
            "  async function loadOrderPipeline() {\n"
            "    const response = await fetch(`${API_BASE}/api/ecommerce/orders`);\n"
            "    const data = await response.json();\n"
            "    setOrderPipeline(data.orders || []);\n"
            "    setFulfillmentSummary(data.fulfillment || { pending: 0, processing: 0, shipped: 0 });\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'ecommerce_app') {\n"
            "        await loadOrderPipeline();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'ecommerce_app') {\n"
            "        await loadOrderPipeline();\n"
            "      }\n"
        ),
        "after_integration": (
            "      if (config.appType === 'ecommerce_app') {\n"
            "        await loadOrderPipeline();\n"
            "      }\n"
        ),
        "panel": "        <EcommerceFamilyPanel fulfillmentSummary={fulfillmentSummary} orderPipeline={orderPipeline} />\n\n",
    },
}


ECOMMERCE_VALIDATION = {
    "backend_markers": (
        "@app.get('/api/ecommerce/orders')",
        "@app.post('/api/ecommerce/orders/{item_id}/advance')",
    ),
    "frontend_markers": ("EcommerceFamilyPanel", "loadOrderPipeline", "fulfillmentSummary"),
}
