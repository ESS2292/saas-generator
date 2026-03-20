INVENTORY_EXTENSION = {
    "backend_import": "from family_logic import build_inventory_reorders, build_inventory_stock, create_reorder_request\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_inventory_stock(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"items": [], "summary": {"in_stock": 0, "low_stock": 0, "out_of_stock": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    items = []
    summary = {"in_stock": 0, "low_stock": 0, "out_of_stock": 0}
    for row in rows:
        payload = dict(row)
        status = str(payload.get("status") or "in_stock").lower()
        if status in summary:
            summary[status] += 1
        items.append(
            {
                "id": payload.get("id"),
                "title": payload.get("title") or payload.get("name") or f"{primary_entity} #{payload.get('id')}",
                "sku": payload.get("sku") or "SKU",
                "stock_level": payload.get("stock_level") or 0,
                "status": status,
            }
        )
    return {"items": items, "summary": summary}


def build_inventory_reorders(db_path: Path, primary_entity: str, primary_table: str):
    stock = build_inventory_stock(db_path, primary_entity, primary_table)["items"]
    reorders = [item for item in stock if item["status"] in {"low_stock", "out_of_stock"} or float(item["stock_level"]) <= 5]
    return {"reorders": reorders[:10]}


def create_reorder_request(db_path: Path, primary_table: str, item_id: int):
    if not db_path.exists():
        raise FileNotFoundError("Database not initialized")
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            f"UPDATE {primary_table} SET status = ? WHERE id = ?",
            ("reorder_pending", item_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
    return {"id": item_id, "status": "reorder_pending"}
""",
    "backend_routes": """
@app.get('/api/inventory/stock')
def get_inventory_stock():
    db_path = SEED_FILE.with_name('app.db')
    return build_inventory_stock(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.get('/api/inventory/reorders')
def get_inventory_reorders():
    db_path = SEED_FILE.with_name('app.db')
    return build_inventory_reorders(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.post('/api/inventory/items/{item_id}/reorder')
def reorder_inventory_item(item_id: int, user_email: str | None = None):
    _require_editor(user_email or _default_session()['email'])
    db_path = SEED_FILE.with_name('app.db')
    result = create_reorder_request(db_path, PRIMARY_TABLE, item_id)
    if result is None:
        raise HTTPException(status_code=404, detail='Inventory item not found')
    session = SessionLocal()
    try:
        record_notification(session, PRIMARY_ENTITY, 'reordered', "Inventory reorder requested", item_id)
        session.commit()
        return {'item': result}
    finally:
        session.close()
""",
    "frontend_import": "import { InventoryFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function InventoryFamilyPanel({ inventorySummary, inventoryItems, inventoryReorders }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>Inventory Watch</h2>
        <span className=\"role-pill\">Supply operations</span>
      </div>
      <div className=\"stack\">
        <div className=\"section-row\">
          <strong>Stock Summary</strong>
          <p>In stock {inventorySummary.in_stock} · Low stock {inventorySummary.low_stock} · Out {inventorySummary.out_of_stock}</p>
        </div>
        {inventoryItems.slice(0, 3).map((item) => (
          <div className=\"section-row\" key={item.id}>
            <strong>{item.title}</strong>
            <p>{item.sku} · {item.stock_level} units · {item.status}</p>
          </div>
        ))}
        {inventoryReorders.slice(0, 3).map((item) => (
          <div className=\"section-row\" key={`reorder-${item.id}`}>
            <strong>Reorder {item.title}</strong>
            <p>{item.sku} · {item.stock_level} units remaining</p>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
    "frontend": {
        "state": (
            "  const [inventorySummary, setInventorySummary] = useState({ in_stock: 0, low_stock: 0, out_of_stock: 0 });\n"
            "  const [inventoryItems, setInventoryItems] = useState([]);\n"
            "  const [inventoryReorders, setInventoryReorders] = useState([]);\n"
        ),
        "loader": (
            "  async function loadInventoryOperations() {\n"
            "    const [stockResponse, reorderResponse] = await Promise.all([\n"
            "      fetch(`${API_BASE}/api/inventory/stock`),\n"
            "      fetch(`${API_BASE}/api/inventory/reorders`),\n"
            "    ]);\n"
            "    const stockData = await stockResponse.json();\n"
            "    const reorderData = await reorderResponse.json();\n"
            "    setInventorySummary(stockData.summary || { in_stock: 0, low_stock: 0, out_of_stock: 0 });\n"
            "    setInventoryItems(stockData.items || []);\n"
            "    setInventoryReorders(reorderData.reorders || []);\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'inventory_management') {\n"
            "        await loadInventoryOperations();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'inventory_management') {\n"
            "        await loadInventoryOperations();\n"
            "      }\n"
        ),
        "after_integration": "",
        "panel": "        <InventoryFamilyPanel inventorySummary={inventorySummary} inventoryItems={inventoryItems} inventoryReorders={inventoryReorders} />\n\n",
    },
}


INVENTORY_VALIDATION = {
    "backend_markers": ("@app.get('/api/inventory/stock')", "@app.get('/api/inventory/reorders')", "@app.post('/api/inventory/items/{item_id}/reorder')"),
    "frontend_markers": ("InventoryFamilyPanel", "loadInventoryOperations", "inventoryReorders"),
}
