BOOKING_EXTENSION = {
    "backend_import": "from family_logic import build_booking_availability\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_booking_availability(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"slots": [], "resourceLabel": primary_entity}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    slots = []
    for row in rows:
        payload = dict(row)
        slots.append(
            {
                "id": payload.get("id"),
                "label": payload.get("title") or payload.get("name") or f"{primary_entity} #{payload.get('id')}",
                "status": payload.get("status") or "scheduled",
                "start": payload.get("start_date") or payload.get("start_time") or payload.get("date") or "",
                "resource": payload.get("resource") or payload.get("resource_name") or payload.get("provider") or payload.get("staff") or payload.get("room") or primary_entity,
            }
        )
    return {"slots": slots, "resourceLabel": primary_entity}
""",
    "backend_routes": """
@app.get('/api/booking/availability')
def get_booking_availability():
    db_path = SEED_FILE.with_name('app.db')
    return build_booking_availability(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)
""",
    "frontend_import": "import { BookingFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function BookingFamilyPanel({ availability }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>Availability Board</h2>
        <span className=\"role-pill\">Booking specific</span>
      </div>
      <div className=\"stack\">
        {availability.map((slot) => (
          <div className=\"section-row\" key={slot.id}>
            <strong>{slot.label}</strong>
            <p>{slot.start || 'Time TBD'} · {slot.resource} · {slot.status}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
    "frontend": {
        "state": "  const [availability, setAvailability] = useState([]);\n",
        "loader": (
            "  async function loadBookingAvailability() {\n"
            "    const response = await fetch(`${API_BASE}/api/booking/availability`);\n"
            "    const data = await response.json();\n"
            "    setAvailability(data.slots || []);\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'booking_platform') {\n"
            "        await loadBookingAvailability();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'booking_platform') {\n"
            "        await loadBookingAvailability();\n"
            "      }\n"
        ),
        "after_integration": (
            "      if (config.appType === 'booking_platform') {\n"
            "        await loadBookingAvailability();\n"
            "      }\n"
        ),
        "panel": "        <BookingFamilyPanel availability={availability} />\n\n",
    },
}


BOOKING_VALIDATION = {
    "backend_markers": ("@app.get('/api/booking/availability')",),
    "frontend_markers": ("BookingFamilyPanel", "loadBookingAvailability"),
}
