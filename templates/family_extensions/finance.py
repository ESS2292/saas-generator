FINANCE_EXTENSION = {
    "backend_import": "from family_logic import approve_finance_invoice, build_finance_approvals, build_finance_cashflow\n",
    "backend_module_path": "backend/family_logic.py",
    "backend_module_source": """from pathlib import Path
import sqlite3


def build_finance_cashflow(db_path: Path, primary_entity: str, primary_table: str):
    if not db_path.exists():
        return {"invoices": [], "summary": {"pending": 0, "approved": 0, "total_amount": 0}}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f"SELECT * FROM {primary_table} ORDER BY id DESC LIMIT 25").fetchall()
    invoices = []
    summary = {"pending": 0, "approved": 0, "total_amount": 0}
    for row in rows:
        payload = dict(row)
        status = str(payload.get("status") or "pending").lower()
        amount = float(payload.get("amount") or 0)
        if status in {"pending", "approved"}:
            summary[status] += 1
        summary["total_amount"] += amount
        invoices.append(
            {
                "id": payload.get("id"),
                "title": payload.get("title") or payload.get("name") or f"{primary_entity} #{payload.get('id')}",
                "status": status,
                "amount": amount,
                "due_date": payload.get("due_date") or "TBD",
            }
        )
    return {"invoices": invoices, "summary": summary}


def build_finance_approvals(db_path: Path, primary_entity: str, primary_table: str):
    cashflow = build_finance_cashflow(db_path, primary_entity, primary_table)["invoices"]
    approvals = [invoice for invoice in cashflow if invoice["status"] == "pending"]
    return {"approvals": approvals[:10]}


def approve_finance_invoice(db_path: Path, primary_table: str, item_id: int):
    if not db_path.exists():
        raise FileNotFoundError("Database not initialized")
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            f"UPDATE {primary_table} SET status = ? WHERE id = ?",
            ("approved", item_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
    return {"id": item_id, "status": "approved"}
""",
    "backend_routes": """
@app.get('/api/finance/cashflow')
def get_finance_cashflow():
    db_path = SEED_FILE.with_name('app.db')
    return build_finance_cashflow(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.get('/api/finance/approvals')
def get_finance_approvals():
    db_path = SEED_FILE.with_name('app.db')
    return build_finance_approvals(db_path, APP_CONFIG['primaryEntity'], PRIMARY_TABLE)

@app.post('/api/finance/invoices/{item_id}/approve')
def approve_invoice(item_id: int, user_email: str | None = None):
    _require_editor(user_email or _default_session()['email'])
    db_path = SEED_FILE.with_name('app.db')
    result = approve_finance_invoice(db_path, PRIMARY_TABLE, item_id)
    if result is None:
        raise HTTPException(status_code=404, detail='Invoice not found')
    session = SessionLocal()
    try:
        record_notification(session, PRIMARY_ENTITY, 'approved', "Finance invoice approved", item_id)
        session.commit()
        return {'invoice': result}
    finally:
        session.close()
""",
    "frontend_import": "import { FinanceFamilyPanel } from './familyPanel.jsx';\n",
    "frontend_module_path": "frontend/src/familyPanel.jsx",
    "frontend_module_source": """export function FinanceFamilyPanel({ financeSummary, financeInvoices, financeApprovals }) {
  return (
    <div className=\"panel\">
      <div className=\"panel-header\">
        <h2>Finance Operations</h2>
        <span className=\"role-pill\">Cashflow control</span>
      </div>
      <div className=\"stack\">
        <div className=\"section-row\">
          <strong>Cashflow Summary</strong>
          <p>Pending {financeSummary.pending} · Approved {financeSummary.approved} · Total ${financeSummary.total_amount}</p>
        </div>
        {financeInvoices.slice(0, 3).map((invoice) => (
          <div className=\"section-row\" key={invoice.id}>
            <strong>{invoice.title}</strong>
            <p>{invoice.status} · ${invoice.amount} · Due {invoice.due_date}</p>
          </div>
        ))}
        {financeApprovals.slice(0, 3).map((invoice) => (
          <div className=\"section-row\" key={`approval-${invoice.id}`}>
            <strong>Awaiting approval: {invoice.title}</strong>
            <p>${invoice.amount} · Due {invoice.due_date}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
    "frontend": {
        "state": (
            "  const [financeSummary, setFinanceSummary] = useState({ pending: 0, approved: 0, total_amount: 0 });\n"
            "  const [financeInvoices, setFinanceInvoices] = useState([]);\n"
            "  const [financeApprovals, setFinanceApprovals] = useState([]);\n"
        ),
        "loader": (
            "  async function loadFinanceOperations() {\n"
            "    const [cashflowResponse, approvalsResponse] = await Promise.all([\n"
            "      fetch(`${API_BASE}/api/finance/cashflow`),\n"
            "      fetch(`${API_BASE}/api/finance/approvals`),\n"
            "    ]);\n"
            "    const cashflowData = await cashflowResponse.json();\n"
            "    const approvalsData = await approvalsResponse.json();\n"
            "    setFinanceSummary(cashflowData.summary || { pending: 0, approved: 0, total_amount: 0 });\n"
            "    setFinanceInvoices(cashflowData.invoices || []);\n"
            "    setFinanceApprovals(approvalsData.approvals || []);\n"
            "  }\n\n"
        ),
        "load_data": (
            "      if (configData.appType === 'finance_ops') {\n"
            "        await loadFinanceOperations();\n"
            "      }\n"
        ),
        "after_notification": (
            "      if (config.appType === 'finance_ops') {\n"
            "        await loadFinanceOperations();\n"
            "      }\n"
        ),
        "after_integration": "",
        "panel": "        <FinanceFamilyPanel financeSummary={financeSummary} financeInvoices={financeInvoices} financeApprovals={financeApprovals} />\n\n",
    },
}


FINANCE_VALIDATION = {
    "backend_markers": ("@app.get('/api/finance/cashflow')", "@app.get('/api/finance/approvals')", "@app.post('/api/finance/invoices/{item_id}/approve')"),
    "frontend_markers": ("FinanceFamilyPanel", "loadFinanceOperations", "financeApprovals"),
}
