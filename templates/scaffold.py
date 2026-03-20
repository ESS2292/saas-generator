import json
import re
from textwrap import dedent

from templates.families import APP_TYPE_LABELS


# Basic JSON rendering helper used whenever generated files need pretty printed
# embedded data.
def _json(value):
    return json.dumps(value, indent=2)


# ---------------------------------------------------------------------------
# Manifest-to-identifier helpers
# ---------------------------------------------------------------------------

# Infer stable Python/SQL identifiers from loose manifest names.
def _slug(value):
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "entity"


# Convert an entity name into the table/route form used by the generated app.
# This stays intentionally naive because the scaffold only needs predictable
# plural paths, not full natural-language inflection.
def _plural_path(name):
    slug = _slug(name)
    return slug if slug.endswith("s") else f"{slug}s"


# If a field looks like a foreign key (for example `client_id`), map it to the
# target table name if that entity exists in the manifest.
def _relation_target(field_name, entity_names):
    if not field_name.endswith("_id"):
        return None
    base_name = _slug(field_name[:-3])
    for entity_name in entity_names:
        singular = _slug(entity_name)
        plural = _plural_path(entity_name)
        if base_name in {singular, plural}:
            return _plural_path(entity_name)
    return None


# Same relation inference as `_relation_target`, but returning the source entity
# name so the generated ORM relationship can reference the Python model class.
def _relation_entity(field_name, entity_names):
    if not field_name.endswith("_id"):
        return None
    base_name = _slug(field_name[:-3])
    for entity_name in entity_names:
        singular = _slug(entity_name)
        plural = _plural_path(entity_name)
        if base_name in {singular, plural}:
            return entity_name
    return None


# Map a manifest field definition to a SQLAlchemy column declaration snippet.
# This centralizes the backend type policy used for all generated entities.
def _field_column(field, entity_names):
    field_type = field.get("type", "string")
    relation_target = _relation_target(field["name"], entity_names)
    if relation_target:
        return f"Integer, ForeignKey('{relation_target}.id'), nullable=True"
    if field["name"].endswith("_id"):
        return "Integer, nullable=True"
    mapping = {
        "number": "Float, default=0",
        "boolean": "Boolean, default=False",
    }
    return mapping.get(field_type, "String, default=''")


# Map a manifest field to the matching HTML form input type used in the React UI.
def _field_input_type(field):
    field_type = field.get("type", "string")
    if field["name"].endswith("_id"):
        return "number"
    if field_type == "number":
        return "number"
    if field_type == "boolean":
        return "boolean"
    return "text"


# Build the runtime coercion expression inserted into generated create/update
# handlers so payloads are normalized before they reach the ORM.
def _coerce_expr(field, source_expr):
    field_type = field.get("type", "string")
    name = field["name"]
    if field["name"].endswith("_id"):
        return f"int({source_expr}.get('{name}') or 0) if {source_expr}.get('{name}') not in (None, '') else None"
    if field_type == "number":
        return f"float({source_expr}.get('{name}') or 0)"
    if field_type == "boolean":
        return (
            f"({source_expr}.get('{name}') if isinstance({source_expr}.get('{name}'), bool) "
            f"else str({source_expr}.get('{name}', '')).strip().lower() in {{'true', '1', 'yes', 'on'}})"
        )
    return f"str({source_expr}.get('{name}', '') or '')"


# ---------------------------------------------------------------------------
# Manifest normalization for generated runtime config and seed data
# ---------------------------------------------------------------------------

# This becomes the runtime config blob embedded into generated backend/frontend code.
def _build_backend_config(manifest):
    return {
        "appName": manifest["app_name"],
        "appType": manifest["app_type"],
        "appTypeLabel": APP_TYPE_LABELS.get(manifest["app_type"], "Application"),
        "tagline": manifest["tagline"],
        "summary": manifest["summary"],
        "primaryEntity": manifest["primary_entity"],
        "scaffoldFamily": manifest["scaffold_family"],
        "theme": manifest["theme"],
        "headline": manifest["dashboard"]["headline"],
        "subheadline": manifest["dashboard"]["subheadline"],
        "sections": manifest["dashboard"]["sections"],
        "pages": manifest["pages"],
        "workflows": manifest["workflows"],
        "auth": manifest["auth"],
        "capabilities": manifest["capabilities"],
        "integrations": manifest["integrations"],
        "permissions": manifest.get("permissions", []),
        "layout": manifest.get("layout", {"navigation_style": "tabs", "density": "comfortable", "panels": ["search", "automation", "records"]}),
        "familyModules": manifest.get("family_modules", ["dashboard_core"]),
        "generatorBoundary": manifest.get("generator_boundary", {}),
        "supportTier": manifest.get("support_tier", "supported"),
        "closestFamily": manifest.get("closest_family", manifest["app_type"]),
        "refinementSteps": manifest.get("refinement_steps", []),
        "handoffNotes": manifest.get("handoff_notes", []),
        "specBrief": manifest.get("spec_brief", {}),
        "routes": manifest["api_routes"],
        "entities": manifest["data_model"],
    }


# Seed records are grouped by entity so the generated DB bootstrap can populate multiple tables.
def _seed_records_by_entity(manifest):
    entity_map = {entity["name"]: [] for entity in manifest["data_model"]}
    primary_entity = manifest["data_model"][0]["name"] if manifest["data_model"] else "Record"
    entity_map[primary_entity] = manifest["sample_records"]
    return entity_map


# ---------------------------------------------------------------------------
# Backend file generation
# ---------------------------------------------------------------------------

# Emit a SQL migration snapshot alongside ORM models so the scaffold has a schema artifact on disk.
def _render_create_table_statement(entity, entity_names):
    table_name = _plural_path(entity["name"])
    columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    foreign_keys = []
    for field in entity.get("fields", []):
        relation_target = _relation_target(field["name"], entity_names)
        if relation_target:
            columns.append(f"{field['name']} INTEGER")
            foreign_keys.append(f"FOREIGN KEY ({field['name']}) REFERENCES {relation_target}(id)")
        elif field.get("type") == "number":
            columns.append(f"{field['name']} REAL")
        elif field.get("type") == "boolean":
            columns.append(f"{field['name']} BOOLEAN")
        else:
            columns.append(f"{field['name']} TEXT")
    all_parts = columns + foreign_keys
    return (
        "CREATE TABLE IF NOT EXISTS "
        f"{table_name} (\n  " + ",\n  ".join(all_parts) + "\n);\n"
    )


def render_backend_initial_migration(manifest):
    statements = []
    entity_names = [entity["name"] for entity in manifest["data_model"]]
    for entity in manifest["data_model"]:
        statements.append(_render_create_table_statement(entity, entity_names))
    return "\n".join(statements)


def _schema_snapshot(manifest):
    entity_names = [entity["name"] for entity in manifest["data_model"]]
    return {
        "app_name": manifest["app_name"],
        "app_type": manifest["app_type"],
        "slug": manifest["slug"],
        "entities": [
            {
                "name": entity["name"],
                "table": _plural_path(entity["name"]),
                "fields": [
                    {
                        "name": field["name"],
                        "type": field.get("type", "string"),
                        "relation_table": _relation_target(field["name"], entity_names),
                    }
                    for field in entity.get("fields", [])
                ],
            }
            for entity in manifest["data_model"]
        ],
    }


def render_backend_schema_snapshot(manifest):
    return json.dumps(_schema_snapshot(manifest), indent=2) + "\n"


def _column_sql(field, entity_names):
    relation_target = _relation_target(field["name"], entity_names)
    if relation_target:
        return f"{field['name']} INTEGER REFERENCES {relation_target}(id)"
    if field.get("type") == "number":
        return f"{field['name']} REAL"
    if field.get("type") == "boolean":
        return f"{field['name']} BOOLEAN"
    return f"{field['name']} TEXT"


def _build_schema_maps(manifest):
    entity_names = [entity["name"] for entity in manifest["data_model"]]
    table_map = {}
    for entity in manifest["data_model"]:
        table_name = _plural_path(entity["name"])
        table_map[table_name] = {
            "entity": entity,
            "fields": {field["name"]: field for field in entity.get("fields", [])},
            "entity_names": entity_names,
        }
    return table_map


def render_backend_incremental_migration(previous_manifest, manifest, version):
    previous_tables = _build_schema_maps(previous_manifest)
    current_tables = _build_schema_maps(manifest)
    statements = []
    manual_actions = []

    for table_name, current_entry in current_tables.items():
        if table_name not in previous_tables:
            statements.append(_render_create_table_statement(current_entry["entity"], current_entry["entity_names"]).strip())
            continue

        previous_fields = previous_tables[table_name]["fields"]
        current_fields = current_entry["fields"]
        for field_name, field in current_fields.items():
            if field_name not in previous_fields:
                statements.append(f"ALTER TABLE {table_name} ADD COLUMN {_column_sql(field, current_entry['entity_names'])};")
                continue
            previous_field = previous_fields[field_name]
            previous_signature = (previous_field.get("type", "string"), _relation_target(previous_field["name"], previous_tables[table_name]["entity_names"]))
            current_signature = (field.get("type", "string"), _relation_target(field["name"], current_entry["entity_names"]))
            if previous_signature != current_signature:
                manual_actions.append(
                    f"-- Manual action required: review type or relation change for {table_name}.{field_name} "
                    f"({previous_signature[0]} -> {current_signature[0]})."
                )

        for field_name in previous_fields:
            if field_name not in current_fields:
                manual_actions.append(f"-- Manual action required: dropped column detected for {table_name}.{field_name}.")

    for table_name in previous_tables:
        if table_name not in current_tables:
            manual_actions.append(f"-- Manual action required: dropped table detected for {table_name}.")

    heading = [
        f"-- Migration {version:04d}: schema update for {manifest['app_name']}",
        f"-- Previous app type: {previous_manifest['app_type']}",
        f"-- Current app type: {manifest['app_type']}",
        "",
    ]
    body = statements + manual_actions
    if not body:
        body = ["-- No schema changes detected."]
    return "\n".join(heading + body).rstrip() + "\n"


def render_backend_migration_history(existing_versions=None, next_version=None):
    versions = sorted(set(existing_versions or [1]))
    if next_version:
        versions = sorted(set(versions + [next_version]))
    migrations = []
    for version in versions:
        migrations.append(
            {
                "version": version,
                "name": "initial" if version == 1 else "schema_update",
                "file": f"{version:04d}_{'initial' if version == 1 else 'schema_update'}.sql",
            }
        )
    return json.dumps(
        {
            "current_version": migrations[-1]["version"] if migrations else 1,
            "migrations": migrations,
        },
        indent=2,
    ) + "\n"


def render_backend_migrations_readme():
    return dedent(
        """
        # Schema Migrations

        This generated app includes:
        - `0001_initial.sql` for the first schema snapshot
        - `schema_snapshot.json` for the latest normalized schema view
        - `history.json` for migration version tracking

        When the generator rebuilds an existing app root with a changed manifest,
        it emits a new `NNNN_schema_update.sql` migration containing additive SQL
        changes plus manual-review comments for destructive or type-changing diffs.
        """
    ).strip() + "\n"


# Render the shared FastAPI application core as one source file. This function does most
# of the heavy lifting: it expands a validated manifest into SQLAlchemy models,
# serializers, CRUD routes, search, automation, notifications, and integrations.
def render_backend_app_core(manifest):
    config_json = _json(_build_backend_config(manifest))
    demo_users_json = _json(manifest["auth"]["demo_users"])
    entity_defs = []
    serializer_defs = []
    default_defs = []
    create_payload_defs = []
    update_payload_defs = []
    route_defs = []
    search_blocks = []

    primary_entity = manifest["data_model"][0]["name"] if manifest["data_model"] else "Record"
    entity_names = [entity["name"] for entity in manifest["data_model"]]

    # Build per-entity model/serializer/CRUD code fragments, then stitch them into one backend file.
    for entity in manifest["data_model"]:
        entity_name = entity["name"]
        class_name = re.sub(r"[^A-Za-z0-9]", "", entity_name) or "Entity"
        table_name = f"{_plural_path(entity_name)}"
        fields = [field for field in entity.get("fields", []) if field.get("name")]
        relation_fields = [
            (field, _relation_entity(field["name"], entity_names))
            for field in fields
            if _relation_entity(field["name"], entity_names)
        ]

        # ORM field declarations for the generated model class.
        field_columns = "\n".join(
            f"    {field['name']} = Column({_field_column(field, entity_names)})" for field in fields
        ) or "    placeholder = Column(String, default='')"
        # Relationship declarations inferred from `*_id` fields.
        relationship_lines = "\n".join(
            f"    {field['name'][:-3]} = relationship('{re.sub(r'[^A-Za-z0-9]', '', related_entity) or 'Entity'}')"
            for field, related_entity in relation_fields
        )
        # Base field serialization included in API responses.
        serializer_lines = "\n".join(
            f"        '{field['name']}': item.{field['name']}," for field in fields
        ) or "        'placeholder': item.placeholder,"
        # Inline nested relation summaries so the frontend can display links
        # without doing extra joins client-side.
        relation_serializer_lines = "\n".join(
            f"        '{field['name'][:-3]}': "
            f"{{'id': item.{field['name'][:-3]}.id, 'label': getattr(item.{field['name'][:-3]}, 'name', None) or getattr(item.{field['name'][:-3]}, 'title', None) or item.{field['name'][:-3]}.id}} "
            f"if item.{field['name'][:-3]} else None,"
            for field, _ in relation_fields
        )
        # Default frontend form state for this entity.
        default_lines = "\n".join(
            f"        '{field['name']}': {_coerce_expr(field, '{}') if False else _field_default_js(field)}," for field in fields
        )
        # Payload-to-model mapping for create handlers.
        create_lines = "\n".join(
            f"            {field['name']}={_coerce_expr(field, 'values')}," for field in fields
        ) or "            placeholder='record',"
        # In-place update assignments for edit handlers.
        update_lines = "\n".join(
            f"    item.{field['name']} = {_coerce_expr(field, 'values')}" for field in fields
        ) or "        item.placeholder = str(values.get('placeholder', 'record'))"

        # Prefer a real `status` field in summary cards when present; otherwise
        # fall back to the table name so every entity can still be counted.
        status_expr = (
            "payload.get('status', 'unknown')"
            if any(field["name"] == "status" for field in fields)
            else f"'{table_name}'"
        )

        # ORM class body.
        entity_defs.append(
            f"class {class_name}(Base):\n"
            f"    __tablename__ = '{table_name}'\n"
            f"    id = Column(Integer, primary_key=True, index=True)\n"
            f"{field_columns}\n"
            f"{relationship_lines + chr(10) if relationship_lines else ''}"
        )
        # Serializer helper used by list/detail/search routes.
        serializer_defs.append(
            f"def serialize_{table_name}(item):\n"
            f"    return {{\n"
            f"        'id': item.id,\n"
            f"{serializer_lines}\n"
            f"{relation_serializer_lines + chr(10) if relation_serializer_lines else ''}"
            f"    }}\n"
        )
        default_payload = {
            field["name"]: (0 if _field_input_type(field) == "number" else False if _field_input_type(field) == "boolean" else "")
            for field in fields
        }
        # Frontend default form values keyed by manifest entity name.
        default_defs.append(f"    '{entity_name}': {json.dumps(default_payload)},")
        # Entity-specific factory helper.
        create_payload_defs.append(
            f"def create_{table_name}(values):\n"
            f"    return {class_name}(\n"
            f"{create_lines}\n"
            f"    )\n"
        )
        # Entity-specific mutation helper.
        update_payload_defs.append(
            f"def update_{table_name}(item, values):\n"
            f"{update_lines}\n"
            f"    return item\n"
        )
        # CRUD and per-entity summary helpers for the generated API.
        route_defs.append(
            f"@app.get('/api/{table_name}')\n"
            f"def list_{table_name}():\n"
            f"    session = SessionLocal()\n"
            f"    try:\n"
            f"        items = session.query({class_name}).order_by({class_name}.id.desc()).all()\n"
            f"        return {{'items': [serialize_{table_name}(item) for item in items]}}\n"
            f"    finally:\n"
            f"        session.close()\n\n"
            f"@app.get('/api/{table_name}' + '/{{item_id}}')\n"
            f"def detail_{table_name}(item_id: int):\n"
            f"    session = SessionLocal()\n"
            f"    try:\n"
            f"        item = session.get({class_name}, item_id)\n"
            f"        if not item:\n"
            f"            raise HTTPException(status_code=404, detail='Item not found')\n"
            f"        return {{'item': serialize_{table_name}(item)}}\n"
            f"    finally:\n"
            f"        session.close()\n\n"
            f"@app.post('/api/{table_name}')\n"
            f"def create_{table_name}_route(payload: ItemPayload, user_email: str | None = None):\n"
            f"    _require_editor(user_email or _default_session()['email'])\n"
            f"    session = SessionLocal()\n"
            f"    try:\n"
            f"        item = create_{table_name}(payload.values or {{}})\n"
            f"        session.add(item)\n"
            f"        session.commit()\n"
            f"        session.refresh(item)\n"
            f"        record_notification(session, '{entity_name}', 'created', 'Created {entity_name} record', item.id)\n"
            f"        session.commit()\n"
            f"        return {{'item': serialize_{table_name}(item)}}\n"
            f"    finally:\n"
            f"        session.close()\n\n"
                f"@app.put('/api/{table_name}' + '/{{item_id}}')\n"
            f"def update_{table_name}_route(item_id: int, payload: ItemPayload, user_email: str | None = None):\n"
            f"    _require_editor(user_email or _default_session()['email'])\n"
            f"    session = SessionLocal()\n"
            f"    try:\n"
            f"        item = session.get({class_name}, item_id)\n"
            f"        if not item:\n"
            f"            raise HTTPException(status_code=404, detail='Item not found')\n"
            f"        update_{table_name}(item, payload.values or {{}})\n"
            f"        session.commit()\n"
            f"        session.refresh(item)\n"
            f"        record_notification(session, '{entity_name}', 'updated', 'Updated {entity_name} record', item.id)\n"
            f"        session.commit()\n"
            f"        return {{'item': serialize_{table_name}(item)}}\n"
            f"    finally:\n"
            f"        session.close()\n\n"
                f"@app.delete('/api/{table_name}' + '/{{item_id}}')\n"
            f"def delete_{table_name}_route(item_id: int, user_email: str | None = None):\n"
            f"    _require_editor(user_email or _default_session()['email'])\n"
            f"    session = SessionLocal()\n"
            f"    try:\n"
            f"        item = session.get({class_name}, item_id)\n"
            f"        if not item:\n"
            f"            raise HTTPException(status_code=404, detail='Item not found')\n"
            f"        session.delete(item)\n"
            f"        record_notification(session, '{entity_name}', 'deleted', 'Deleted {entity_name} record', item_id)\n"
            f"        session.commit()\n"
            f"        return {{'deleted': item_id}}\n"
            f"    finally:\n"
            f"        session.close()\n\n"
            f"def summary_source_{table_name}(payloads):\n"
            f"    statuses = {{}}\n"
            f"    for payload in payloads:\n"
            f"        status = str({status_expr})\n"
            f"        statuses[status] = statuses.get(status, 0) + 1\n"
            f"    return statuses\n"
        )
        # Search fan-out block appended into the shared `/api/search` route.
        search_blocks.append(
            f"        {table_name}_items = session.query({class_name}).limit(25).all()\n"
            f"        for item in {table_name}_items:\n"
            f"            payload = serialize_{table_name}(item)\n"
            f"            haystack = json.dumps(payload).lower()\n"
            f"            if query in haystack:\n"
            f"                results.append({{'entity': '{entity_name}', 'table': '{table_name}', 'item': payload}})\n"
        )

    primary_table = _plural_path(primary_entity)
    entity_map = {
        entity["name"]: {
            "path": _plural_path(entity["name"]),
            "fields": entity.get("fields", []),
        }
        for entity in manifest["data_model"]
    }

    # The backend is rendered as one assembled source file so the generator stays template-driven
    # instead of asking the model to handwrite application code.
    return (
        "from contextlib import asynccontextmanager\n"
        "import json\n"
        "from datetime import datetime\n"
        "\n"
        "from fastapi import FastAPI, HTTPException\n"
        "from fastapi.middleware.cors import CORSMiddleware\n"
        "from pydantic import BaseModel\n"
        "from app_config import APP_CONFIG, DATABASE_URL, DEFAULT_FORM_VALUES, DEMO_USERS, ENTITY_MAP, PRIMARY_ENTITY, PRIMARY_TABLE, SEED_FILE\n"
        "from database import Base, SessionLocal, engine\n"
        "from providers import build_checkout_session, send_email_message, build_storage_upload\n"
        "__FAMILY_BACKEND_IMPORTS__"
        "from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String\n"
        "from sqlalchemy.orm import relationship\n\n\n"
        + "\n\n".join(entity_defs)
        + "\n\n"
        # Shared support tables used across every generated app.
        "class Notification(Base):\n"
        "    __tablename__ = 'notifications'\n"
        "    id = Column(Integer, primary_key=True, index=True)\n"
        "    entity = Column(String, default='')\n"
        "    action = Column(String, default='')\n"
        "    message = Column(String, default='')\n"
        "    record_id = Column(Integer, nullable=True)\n"
        "    created_at = Column(String, default='')\n\n\n"
        "class AutomationJob(Base):\n"
        "    __tablename__ = 'automation_jobs'\n"
        "    id = Column(Integer, primary_key=True, index=True)\n"
        "    entity = Column(String, default='')\n"
        "    table_name = Column(String, default='')\n"
        "    action = Column(String, default='')\n"
        "    status = Column(String, default='queued')\n"
        "    record_id = Column(Integer, nullable=True)\n"
        "    created_at = Column(String, default='')\n\n\n"
        "class IntegrationEvent(Base):\n"
        "    __tablename__ = 'integration_events'\n"
        "    id = Column(Integer, primary_key=True, index=True)\n"
        "    provider = Column(String, default='')\n"
        "    direction = Column(String, default='')\n"
        "    event_type = Column(String, default='')\n"
        "    payload = Column(String, default='')\n"
        "    created_at = Column(String, default='')\n\n\n"
        # Request payload schemas for the generated routes.
        "class ItemPayload(BaseModel):\n"
        "    values: dict\n\n\n"
        "class SessionPayload(BaseModel):\n"
        "    email: str\n\n\n"
        "class AutomationPayload(BaseModel):\n"
        "    entity: str\n"
        "    table_name: str\n"
        "    action: str\n"
        "    record_id: int | None = None\n\n\n"
        "class IntegrationPayload(BaseModel):\n"
        "    provider: str\n"
        "    event_type: str\n"
        "    payload: dict | None = None\n\n\n"
        "class CheckoutPayload(BaseModel):\n"
        "    amount: float\n"
        "    currency: str = 'usd'\n"
        "    description: str = 'Generated checkout'\n\n\n"
        "class EmailPayload(BaseModel):\n"
        "    to_email: str\n"
        "    subject: str\n"
        "    body: str\n\n\n"
        "class StoragePayload(BaseModel):\n"
        "    file_name: str\n"
        "    content_type: str = 'application/octet-stream'\n\n\n"
        + "\n\n".join(serializer_defs)
        + "\n\n"
        + "\n\n".join(create_payload_defs)
        + "\n\n"
        + "\n\n".join(update_payload_defs)
        + "\n\n"
        # Small auth/recording helpers used by multiple generated routes.
        "def _default_session():\n"
        "    return DEMO_USERS[0]\n\n\n"
        "def _require_editor(user_email=None):\n"
        "    user = next((candidate for candidate in DEMO_USERS if candidate['email'] == user_email), None)\n"
        "    if not user:\n"
        "        raise HTTPException(status_code=401, detail='Unknown demo user')\n"
        "    if user.get('role') not in {'owner', 'manager', 'member'}:\n"
        "        raise HTTPException(status_code=403, detail='User does not have edit access')\n"
        "    return user\n\n\n"
        "def record_notification(session, entity, action, message, record_id=None):\n"
        "    session.add(Notification(entity=entity, action=action, message=message, record_id=record_id, created_at=datetime.utcnow().isoformat()))\n\n\n"
        "def record_integration_event(session, provider, direction, event_type, payload):\n"
        "    session.add(IntegrationEvent(provider=provider, direction=direction, event_type=event_type, payload=json.dumps(payload), created_at=datetime.utcnow().isoformat()))\n\n\n"
        "def _load_seed_records():\n"
        "    if SEED_FILE.exists():\n"
        "        return json.loads(SEED_FILE.read_text(encoding='utf-8'))\n"
        "    return {}\n\n\n"
        # Seed the database once on first startup using manifest-provided sample data.
        "def _seed_database():\n"
        "    seeded = _load_seed_records()\n"
        "    session = SessionLocal()\n"
        "    try:\n"
        + "".join(
            f"        if session.query({re.sub(r'[^A-Za-z0-9]', '', entity['name']) or 'Entity'}).count() == 0:\n"
            f"            for values in seeded.get('{entity['name']}', []):\n"
            f"                record = create_{_plural_path(entity['name'])}(values)\n"
            f"                session.add(record)\n"
            for entity in manifest["data_model"]
        )
        + "        session.commit()\n"
        "    finally:\n"
        "        session.close()\n\n\n"
        "@asynccontextmanager\n"
        "async def app_lifespan(app):\n"
        "    Base.metadata.create_all(bind=engine)\n"
        "    _seed_database()\n"
        "    yield\n\n\n"
        # Global application routes: health/config/session/integrations.
        f"app = FastAPI(title={manifest['app_name']!r}, description={manifest['summary']!r}, version='1.0.0', lifespan=app_lifespan)\n"
        "app.add_middleware(\n"
        "    CORSMiddleware,\n"
        "    allow_origins=['*'],\n"
        "    allow_credentials=True,\n"
        "    allow_methods=['*'],\n"
        "    allow_headers=['*'],\n"
        ")\n\n\n"
        # Global application routes: health/config/session/integrations.
        "@app.get('/health')\n"
        "def health_check():\n"
        "    return {'status': 'ok', 'app': APP_CONFIG['appName']}\n\n\n"
        "@app.get('/api/config')\n"
        "def get_config():\n"
        "    return {**APP_CONFIG, 'defaultFormValues': DEFAULT_FORM_VALUES, 'primaryTable': PRIMARY_TABLE}\n\n\n"
        "@app.get('/api/auth/session')\n"
        "def get_session():\n"
        "    return {'user': _default_session(), 'availableUsers': DEMO_USERS}\n\n\n"
        "@app.post('/api/auth/session')\n"
        "def set_session(payload: SessionPayload):\n"
        "    user = next((candidate for candidate in DEMO_USERS if candidate['email'] == payload.email), None)\n"
        "    if not user:\n"
        "        raise HTTPException(status_code=404, detail='Demo user not found')\n"
        "    return {'user': user, 'availableUsers': DEMO_USERS}\n\n\n"
        "@app.get('/api/entities')\n"
        "def list_entities():\n"
        "    return {'entities': APP_CONFIG['entities'], 'primaryTable': PRIMARY_TABLE}\n\n\n"
        "@app.get('/api/integrations')\n"
        "def list_integrations():\n"
        "    return {'integrations': APP_CONFIG['integrations']}\n\n\n"
        "@app.post('/api/integrations/payment/checkout')\n"
        "def create_checkout(payload: CheckoutPayload, user_email: str | None = None):\n"
        "    _require_editor(user_email or _default_session()['email'])\n"
        "    session = SessionLocal()\n"
        "    try:\n"
        "        checkout = build_checkout_session(APP_CONFIG['integrations']['payments'], payload.amount, payload.currency, payload.description)\n"
        "        record_integration_event(session, APP_CONFIG['integrations']['payments'], 'outbound', 'checkout.session.created', checkout)\n"
        "        record_notification(session, 'integration', 'payment', f\"Checkout created via {APP_CONFIG['integrations']['payments']}\")\n"
        "        session.commit()\n"
        "        return checkout\n"
        "    finally:\n"
        "        session.close()\n\n\n"
        "@app.post('/api/integrations/email/send')\n"
        "def send_email(payload: EmailPayload, user_email: str | None = None):\n"
        "    _require_editor(user_email or _default_session()['email'])\n"
        "    session = SessionLocal()\n"
        "    try:\n"
        "        message = send_email_message(APP_CONFIG['integrations']['email'], payload.to_email, payload.subject, payload.body)\n"
        "        record_integration_event(session, APP_CONFIG['integrations']['email'], 'outbound', 'email.sent', message)\n"
        "        record_notification(session, 'integration', 'email', f\"Email queued via {APP_CONFIG['integrations']['email']}\")\n"
        "        session.commit()\n"
        "        return message\n"
        "    finally:\n"
        "        session.close()\n\n\n"
        "@app.post('/api/integrations/storage/presign')\n"
        "def create_upload(payload: StoragePayload, user_email: str | None = None):\n"
        "    _require_editor(user_email or _default_session()['email'])\n"
        "    session = SessionLocal()\n"
        "    try:\n"
        "        upload = build_storage_upload(APP_CONFIG['integrations']['storage'], payload.file_name, payload.content_type)\n"
        "        record_integration_event(session, APP_CONFIG['integrations']['storage'], 'outbound', 'storage.upload.prepared', upload)\n"
        "        record_notification(session, 'integration', 'storage', f\"Upload prepared via {APP_CONFIG['integrations']['storage']}\")\n"
        "        session.commit()\n"
        "        return upload\n"
        "    finally:\n"
        "        session.close()\n\n\n"
        # Cross-entity behavior routes layered on top of CRUD.
        "@app.get('/api/search')\n"
        "def search_records(q: str = ''):\n"
        "    query = q.strip().lower()\n"
        "    if not query:\n"
        "        return {'results': []}\n"
        "    session = SessionLocal()\n"
        "    try:\n"
        "        results = []\n"
        + "".join(search_blocks)
        + "        return {'results': results[:25]}\n"
        "    finally:\n"
        "        session.close()\n\n\n"
        "@app.get('/api/notifications')\n"
        "def list_notifications():\n"
        "    session = SessionLocal()\n"
        "    try:\n"
        "        notifications = session.query(Notification).order_by(Notification.id.desc()).limit(25).all()\n"
        "        return {'notifications': [\n"
        "            {'id': note.id, 'entity': note.entity, 'action': note.action, 'message': note.message, 'record_id': note.record_id, 'created_at': note.created_at}\n"
        "            for note in notifications\n"
        "        ]}\n"
        "    finally:\n"
        "        session.close()\n\n\n"
        "@app.post('/api/automation/run')\n"
        "def run_automation(payload: AutomationPayload, user_email: str | None = None):\n"
        "    _require_editor(user_email or _default_session()['email'])\n"
        "    session = SessionLocal()\n"
        "    try:\n"
        "        job = AutomationJob(entity=payload.entity, table_name=payload.table_name, action=payload.action, status='completed', record_id=payload.record_id, created_at=datetime.utcnow().isoformat())\n"
        "        session.add(job)\n"
        "        record_notification(session, payload.entity, 'automation', f\"Automation '{payload.action}' completed\", payload.record_id)\n"
        "        session.commit()\n"
        "        session.refresh(job)\n"
        "        return {'job': {'id': job.id, 'entity': job.entity, 'table_name': job.table_name, 'action': job.action, 'status': job.status, 'record_id': job.record_id}}\n"
        "    finally:\n"
        "        session.close()\n\n\n"
        "@app.get('/api/integration-events')\n"
        "def list_integration_events():\n"
        "    session = SessionLocal()\n"
        "    try:\n"
        "        events = session.query(IntegrationEvent).order_by(IntegrationEvent.id.desc()).limit(25).all()\n"
        "        return {'events': [\n"
        "            {'id': event.id, 'provider': event.provider, 'direction': event.direction, 'event_type': event.event_type, 'payload': event.payload, 'created_at': event.created_at}\n"
        "            for event in events\n"
        "        ]}\n"
        "    finally:\n"
        "        session.close()\n\n\n"
        "@app.post('/api/integrations/test')\n"
        "def run_integration_test(payload: IntegrationPayload, user_email: str | None = None):\n"
        "    _require_editor(user_email or _default_session()['email'])\n"
        "    session = SessionLocal()\n"
        "    try:\n"
        "        sample_payload = payload.payload or {'status': 'ok', 'provider': payload.provider}\n"
        "        record_integration_event(session, payload.provider, 'outbound', payload.event_type, sample_payload)\n"
        "        record_notification(session, 'integration', 'test', f\"Integration test sent via {payload.provider}\")\n"
        "        session.commit()\n"
        "        return {'provider': payload.provider, 'event_type': payload.event_type, 'status': 'sent'}\n"
        "    finally:\n"
        "        session.close()\n\n\n"
        "@app.post('/api/webhooks/{provider}')\n"
        "def receive_webhook(provider: str, payload: dict):\n"
        "    session = SessionLocal()\n"
        "    try:\n"
        "        event_type = str(payload.get('event_type', 'webhook.received'))\n"
        "        record_integration_event(session, provider, 'inbound', event_type, payload)\n"
        "        record_notification(session, 'integration', 'webhook', f\"Webhook received from {provider}\")\n"
        "        session.commit()\n"
        "        return {'provider': provider, 'event_type': event_type, 'status': 'received'}\n"
        "    finally:\n"
        "        session.close()\n\n\n"
        # Finally append all entity-specific CRUD/detail routes.
        + "\n\n".join(route_defs)
        + "\n\n"
        "__FAMILY_BACKEND_ROUTES__"
        "@app.get('/api/summary')\n"
        "def get_summary():\n"
        "    session = SessionLocal()\n"
        "    try:\n"
        f"        items = session.query({re.sub(r'[^A-Za-z0-9]', '', primary_entity) or 'Entity'}).all()\n"
        f"        payloads = [serialize_{primary_table}(item) for item in items]\n"
        f"        statuses = summary_source_{primary_table}(payloads)\n"
        "        return {\n"
        "            'totalItems': len(payloads),\n"
        "            'statusBreakdown': statuses,\n"
        "            'primaryRoute': APP_CONFIG['routes'][0]['path'] if APP_CONFIG['routes'] else f'/api/{PRIMARY_TABLE}',\n"
        "            'appType': APP_CONFIG['appType'],\n"
        "            'recordLabel': APP_CONFIG['primaryEntity'],\n"
        "        }\n"
        "    finally:\n"
        "        session.close()\n"
    )


# Minimal backend entrypoint that imports the generated shared app module.
def render_backend_main():
    return "from app_core import app\n"


# Shared backend configuration module. This keeps manifest-derived constants
# separate from the route/model assembly so the generated app has a clearer
# layout and smaller entry modules.
def render_backend_config_module(manifest):
    config_json = _json(_build_backend_config(manifest))
    demo_users_json = _json(manifest["auth"]["demo_users"])
    primary_entity = manifest["data_model"][0]["name"] if manifest["data_model"] else "Record"
    primary_table = _plural_path(primary_entity)
    entity_map = {
        entity["name"]: {
            "path": _plural_path(entity["name"]),
            "fields": entity.get("fields", []),
        }
        for entity in manifest["data_model"]
    }
    default_payloads = {
        entity["name"]: {
            field["name"]: (
                0
                if _field_input_type(field) == "number"
                else False
                if _field_input_type(field) == "boolean"
                else ""
            )
            for field in entity.get("fields", [])
            if field.get("name")
        }
        for entity in manifest["data_model"]
    }
    return (
        "import json\n"
        "from pathlib import Path\n\n"
        f"APP_CONFIG = json.loads('''{config_json}''')\n"
        f"DEMO_USERS = json.loads('''{demo_users_json}''')\n"
        f"ENTITY_MAP = json.loads('''{json.dumps(entity_map)}''')\n"
        f"PRIMARY_ENTITY = {primary_entity!r}\n"
        f"PRIMARY_TABLE = {primary_table!r}\n"
        f"DEFAULT_FORM_VALUES = json.loads('''{json.dumps(default_payloads)}''')\n"
        "DATABASE_URL = 'sqlite:///./app.db'\n"
        "SEED_FILE = Path(__file__).with_name('seed_data.json')\n"
    ).rstrip() + "\n"


# Shared SQLAlchemy bootstrap module. Keeping the engine/session/base here lets
# app_core focus on generated models and routes.
def render_backend_database_module():
    return dedent(
        """
        from sqlalchemy import create_engine
        from sqlalchemy.orm import declarative_base, sessionmaker

        from app_config import DATABASE_URL

        engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        Base = declarative_base()
        """
    ).strip() + "\n"


# Convert a manifest field into the JavaScript literal used for empty form state.
def _field_default_js(field):
    input_type = _field_input_type(field)
    if input_type == "number":
        return 0
    if input_type == "boolean":
        return False
    return ""


def _page_slug(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "page"


def _page_component_name(page):
    return f"{re.sub(r'[^A-Za-z0-9]', '', page['name'].title()) or 'Generated'}Page"


def _page_component_filename(page):
    return f"{_page_component_name(page)}.jsx"


def _page_route_path(page, index):
    return "/" if index == 0 else f"/{_page_slug(page['name'])}"


def _page_mode(page):
    layout = str(page.get("layout", "workspace")).strip().lower()
    widgets = set(page.get("widgets", []))
    if layout == "dashboard" or "summary_cards" in widgets:
        return "dashboard"
    if layout in {"table", "workspace"} or {"record_grid", "entity_form"} & widgets:
        return "records"
    return "operations"


# Dependency set for the generated FastAPI/SQLAlchemy backend.
def render_backend_requirements():
    return "fastapi==0.111.1\nuvicorn==0.24.0\npydantic==2.11.0\nsqlalchemy==2.0.21\n"


# Docker image for local backend runs inside the generated project.
def render_backend_dockerfile():
    return dedent(
        """
        FROM python:3.11-slim
        WORKDIR /app
        COPY backend/requirements.txt /app/requirements.txt
        RUN pip install --no-cache-dir -r requirements.txt
        COPY backend /app
        CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
        """
    ).strip() + "\n"


# Seed data file consumed by `_seed_database` in the generated backend.
def render_backend_seed_data(manifest):
    return _json(_seed_records_by_entity(manifest)) + "\n"


# Provider adapters stay isolated here so real SDK integrations can replace these stubs later.
def render_backend_providers():
    return dedent(
        """
        import hashlib
        import hmac
        import json
        import os
        import urllib.error
        import urllib.parse
        import urllib.request
        from datetime import datetime, timezone
        from uuid import uuid4


        def _utc_timestamp():
            now = datetime.now(timezone.utc)
            return now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")


        def _provider_response(provider, mode, payload):
            return {
                "provider": provider,
                "mode": mode,
                **payload,
                "created_at": datetime.utcnow().isoformat(),
            }


        def _missing_credentials(provider, required):
            return _provider_response(
                provider,
                "config_required",
                {
                    "required_env": list(required),
                    "configured": {name: bool(os.getenv(name)) for name in required},
                },
            )


        def _http_json(method, url, headers=None, payload=None):
            body = None
            request_headers = headers or {}
            if payload is not None:
                body = json.dumps(payload).encode("utf-8")
                request_headers = {"Content-Type": "application/json", **request_headers}
            request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    content = response.read().decode("utf-8")
                    return json.loads(content) if content else {}
            except urllib.error.HTTPError as exc:
                details = exc.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"HTTP {exc.code}: {details[:400]}") from exc


        def _http_form(method, url, headers=None, payload=None):
            data = None
            request_headers = headers or {}
            if payload is not None:
                data = urllib.parse.urlencode(payload).encode("utf-8")
                request_headers = {"Content-Type": "application/x-www-form-urlencoded", **request_headers}
            request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    content = response.read().decode("utf-8")
                    return json.loads(content) if content and content.startswith("{") else {"raw": content}
            except urllib.error.HTTPError as exc:
                details = exc.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"HTTP {exc.code}: {details[:400]}") from exc


        def build_checkout_session(provider, amount, currency, description):
            normalized = str(provider or "demo").strip().lower()
            if normalized == "stripe":
                required = ("PAYMENTS_SECRET_KEY", "APP_BASE_URL")
                if not all(os.getenv(name) for name in required):
                    return _missing_credentials(normalized, required)
                response = _http_form(
                    "POST",
                    "https://api.stripe.com/v1/checkout/sessions",
                    headers={"Authorization": f"Bearer {os.getenv('PAYMENTS_SECRET_KEY')}"},
                    payload={
                        "mode": "payment",
                        "success_url": f"{os.getenv('APP_BASE_URL').rstrip('/')}/success",
                        "cancel_url": f"{os.getenv('APP_BASE_URL').rstrip('/')}/cancel",
                        "line_items[0][price_data][currency]": currency,
                        "line_items[0][price_data][product_data][name]": description,
                        "line_items[0][price_data][unit_amount]": int(float(amount) * 100),
                        "line_items[0][quantity]": 1,
                    },
                )
                return _provider_response(
                    normalized,
                    "live",
                    {
                        "session_id": response.get("id"),
                        "checkout_url": response.get("url"),
                        "amount": amount,
                        "currency": currency,
                        "description": description,
                        "publishable_key": os.getenv("PAYMENTS_PUBLIC_KEY", ""),
                    },
                )
            if normalized == "paddle":
                required = ("PAYMENTS_SECRET_KEY",)
                if not all(os.getenv(name) for name in required):
                    return _missing_credentials(normalized, required)
                return _provider_response(
                    normalized,
                    "template",
                    {
                        "session_id": f"paddle_{uuid4().hex[:12]}",
                        "amount": amount,
                        "currency": currency,
                        "description": description,
                        "message": "Paddle selected. Wire this template to your Paddle transaction flow.",
                    },
                )
            return _provider_response(
                normalized,
                "demo",
                {
                    "session_id": f"{normalized}_{uuid4().hex[:12]}",
                    "amount": amount,
                    "currency": currency,
                    "description": description,
                    "publishable_key": os.getenv("PAYMENTS_PUBLIC_KEY", "demo_public_key"),
                },
            )


        def send_email_message(provider, to_email, subject, body):
            normalized = str(provider or "demo").strip().lower()
            if normalized == "sendgrid":
                required = ("EMAIL_API_KEY", "EMAIL_FROM_EMAIL")
                if not all(os.getenv(name) for name in required):
                    return _missing_credentials(normalized, required)
                _http_json(
                    "POST",
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={"Authorization": f"Bearer {os.getenv('EMAIL_API_KEY')}"},
                    payload={
                        "personalizations": [{"to": [{"email": to_email}]}],
                        "from": {"email": os.getenv("EMAIL_FROM_EMAIL")},
                        "subject": subject,
                        "content": [{"type": "text/plain", "value": body}],
                    },
                )
                return _provider_response(
                    normalized,
                    "live",
                    {
                        "message_id": f"sendgrid_{uuid4().hex[:12]}",
                        "to_email": to_email,
                        "subject": subject,
                    },
                )
            if normalized == "resend":
                required = ("EMAIL_API_KEY", "EMAIL_FROM_EMAIL")
                if not all(os.getenv(name) for name in required):
                    return _missing_credentials(normalized, required)
                response = _http_json(
                    "POST",
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {os.getenv('EMAIL_API_KEY')}"},
                    payload={
                        "from": os.getenv("EMAIL_FROM_EMAIL"),
                        "to": [to_email],
                        "subject": subject,
                        "text": body,
                    },
                )
                return _provider_response(
                    normalized,
                    "live",
                    {
                        "message_id": response.get("id"),
                        "to_email": to_email,
                        "subject": subject,
                    },
                )
            return _provider_response(
                normalized,
                "demo",
                {
                    "message_id": f"{normalized}_{uuid4().hex[:12]}",
                    "to_email": to_email,
                    "subject": subject,
                    "body_preview": body[:80],
                    "api_key_present": bool(os.getenv("EMAIL_API_KEY")),
                },
            )


        def _aws_sign(key, message):
            return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


        def _aws_signing_key(secret_key, datestamp, region, service):
            date_key = _aws_sign(("AWS4" + secret_key).encode("utf-8"), datestamp)
            region_key = _aws_sign(date_key, region)
            service_key = _aws_sign(region_key, service)
            return _aws_sign(service_key, "aws4_request")


        def build_storage_upload(provider, file_name, content_type):
            normalized = str(provider or "demo").strip().lower()
            if normalized == "s3":
                required = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "STORAGE_BUCKET")
                if not all(os.getenv(name) for name in required):
                    return _missing_credentials(normalized, required)
                region = os.getenv("AWS_REGION")
                bucket = os.getenv("STORAGE_BUCKET")
                access_key = os.getenv("AWS_ACCESS_KEY_ID")
                secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
                timestamp, datestamp = _utc_timestamp()
                host = f"{bucket}.s3.{region}.amazonaws.com"
                credential_scope = f"{datestamp}/{region}/s3/aws4_request"
                query = {
                    "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
                    "X-Amz-Credential": f"{access_key}/{credential_scope}",
                    "X-Amz-Date": timestamp,
                    "X-Amz-Expires": "900",
                    "X-Amz-SignedHeaders": "host",
                }
                canonical_query = "&".join(
                    f"{urllib.parse.quote(name, safe='')}={urllib.parse.quote(value, safe='~')}"
                    for name, value in sorted(query.items())
                )
                object_key = f"uploads/{uuid4().hex}/{file_name}"
                canonical_request = "\\n".join(
                    [
                        "PUT",
                        f"/{object_key}",
                        canonical_query,
                        f"host:{host}\\n",
                        "host",
                        "UNSIGNED-PAYLOAD",
                    ]
                )
                string_to_sign = "\\n".join(
                    [
                        "AWS4-HMAC-SHA256",
                        timestamp,
                        credential_scope,
                        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
                    ]
                )
                signing_key = _aws_signing_key(secret_key, datestamp, region, "s3")
                signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
                upload_url = f"https://{host}/{object_key}?{canonical_query}&X-Amz-Signature={signature}"
                return _provider_response(
                    normalized,
                    "live",
                    {
                        "file_name": file_name,
                        "content_type": content_type,
                        "upload_url": upload_url,
                        "bucket": bucket,
                        "object_key": object_key,
                    },
                )
            if normalized == "cloudinary":
                required = ("STORAGE_API_KEY", "STORAGE_API_SECRET", "STORAGE_CLOUD_NAME")
                if not all(os.getenv(name) for name in required):
                    return _missing_credentials(normalized, required)
                timestamp = str(int(datetime.utcnow().timestamp()))
                signature_base = f"timestamp={timestamp}{os.getenv('STORAGE_API_SECRET')}"
                signature = hashlib.sha1(signature_base.encode("utf-8")).hexdigest()
                return _provider_response(
                    normalized,
                    "live",
                    {
                        "file_name": file_name,
                        "content_type": content_type,
                        "upload_url": f"https://api.cloudinary.com/v1_1/{os.getenv('STORAGE_CLOUD_NAME')}/auto/upload",
                        "timestamp": timestamp,
                        "api_key": os.getenv("STORAGE_API_KEY"),
                        "signature": signature,
                    },
                )
            return _provider_response(
                normalized,
                "demo",
                {
                    "file_name": file_name,
                    "content_type": content_type,
                    "upload_url": f"https://uploads.example.com/{normalized}/{uuid4().hex}/{file_name}",
                    "bucket": os.getenv("STORAGE_BUCKET", "generated-app-assets"),
                },
            )
        """
    ).strip() + "\n"


# Environment template for real provider credentials in the generated backend.
def render_backend_env_example(manifest):
    return (
        f"EMAIL_PROVIDER={manifest['integrations']['email']}\n"
        "EMAIL_API_KEY=demo-email-key\n"
        "EMAIL_FROM_EMAIL=noreply@example.com\n"
        f"PAYMENTS_PROVIDER={manifest['integrations']['payments']}\n"
        "APP_BASE_URL=http://localhost:3000\n"
        "PAYMENTS_PUBLIC_KEY=pk_test_demo\n"
        "PAYMENTS_SECRET_KEY=sk_test_demo\n"
        f"STORAGE_PROVIDER={manifest['integrations']['storage']}\n"
        "STORAGE_BUCKET=generated-app-assets\n"
        "AWS_ACCESS_KEY_ID=demo-access-key\n"
        "AWS_SECRET_ACCESS_KEY=demo-secret-key\n"
        "AWS_REGION=us-east-1\n"
        "STORAGE_API_KEY=demo-storage-key\n"
        "STORAGE_API_SECRET=demo-storage-secret\n"
        "STORAGE_CLOUD_NAME=demo-cloud\n"
    )


# ---------------------------------------------------------------------------
# Frontend file generation
# ---------------------------------------------------------------------------

# Minimal React/Vite package definition for the generated UI.
def render_frontend_package_json(manifest):
    package = {
        "name": manifest["slug"],
        "private": True,
        "version": "0.1.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview --host 0.0.0.0 --port 3000",
        },
        "dependencies": {
            "react": "^18.3.1",
            "react-dom": "^18.3.1",
            "react-router-dom": "^6.28.0",
        },
        "devDependencies": {
            "@vitejs/plugin-react": "^4.3.1",
            "vite": "^5.4.2",
        },
    }
    return _json(package) + "\n"


# Vite dev server config used by the generated frontend container and local runs.
def render_frontend_vite_config():
    return dedent(
        """
        import { defineConfig } from 'vite';
        import react from '@vitejs/plugin-react';

        export default defineConfig({
          plugins: [react()],
          server: {
            host: '0.0.0.0',
            port: 3000,
          },
        });
        """
    ).strip() + "\n"


# HTML shell that mounts the generated React application.
def render_frontend_index_html(manifest):
    return dedent(
        f"""
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>{manifest["app_name"]}</title>
            <script type="module" src="/src/main.jsx"></script>
          </head>
          <body>
            <div id="root"></div>
          </body>
        </html>
        """
    ).strip() + "\n"


# React entrypoint that mounts the generated `App` component.
def render_frontend_main_jsx():
    return dedent(
        """
        import React from 'react';
        import ReactDOM from 'react-dom/client';
        import App from './App.jsx';
        import './styles.css';

        ReactDOM.createRoot(document.getElementById('root')).render(
          <React.StrictMode>
            <App />
          </React.StrictMode>
        );
        """
    ).strip() + "\n"


# Shared frontend API helper. This gives the generated shell and future family
# modules one import path for backend requests.
def render_frontend_api_js():
    return dedent(
        """
        export const API_BASE = 'http://localhost:8000';

        export async function requestJson(path, options = {}) {
          const response = await fetch(`${API_BASE}${path}`, options);
          const data = await response.json();
          if (!response.ok) {
            throw new Error(data.detail || `Request failed (${response.status})`);
          }
          return data;
        }
        """
    ).strip() + "\n"


# Shared frontend entity helpers used by the dashboard shell and family panels.
def render_frontend_entity_utils_js():
    return dedent(
        """
        export function entityToTableName(entityName) {
          const slug = String(entityName || '')
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/_$/, '');
          return slug.endsWith('s') ? slug : `${slug}s`;
        }

        export function formatRecordValue(value) {
          if (typeof value === 'object' && value !== null) {
            return value.label || value.id || JSON.stringify(value);
          }
          return String(value);
        }
        """
    ).strip() + "\n"


# Shared generated form component for entity create/edit flows.
def render_frontend_entity_form_jsx():
    return dedent(
        """
        export default function EntityForm({
          activeEntity,
          fields,
          formValues,
          editingItemId,
          selectedUser,
          saving,
          canEdit,
          onFieldChange,
          onReset,
          onSubmit,
        }) {
          return (
            <form className="panel" onSubmit={onSubmit}>
              <div className="panel-header">
                <h2>{editingItemId ? `Edit ${activeEntity.name}` : `Create ${activeEntity.name}`}</h2>
                <span className="role-pill">{selectedUser ? `${selectedUser.name} · ${selectedUser.role}` : 'Loading user...'}</span>
              </div>
              <div className="form-grid">
                {fields.map((field) => {
                  const isBoolean = field.type === 'boolean';
                  const inputType = field.name.endsWith('_id') || field.type === 'number' ? 'number' : 'text';
                  return (
                    <label className="field" key={field.name}>
                      <span>{field.name}</span>
                      {isBoolean ? (
                        <input type="checkbox" checked={Boolean(formValues[field.name])} onChange={(event) => onFieldChange(field, event.target.checked)} />
                      ) : (
                        <input
                          type={inputType}
                          value={formValues[field.name] ?? ''}
                          onChange={(event) => onFieldChange(field, event.target.value)}
                          placeholder={`Enter ${field.name}`}
                        />
                      )}
                    </label>
                  );
                })}
              </div>
              <div className="button-row">
                <button className="primary-button" type="submit" disabled={saving || !canEdit}>
                  {saving ? 'Saving...' : editingItemId ? `Save ${activeEntity.name}` : `Create ${activeEntity.name}`}
                </button>
                <button className="ghost-button" type="button" onClick={onReset}>
                  Reset
                </button>
              </div>
            </form>
          );
        }
        """
    ).strip() + "\n"


# Shared generated grid component for entity list/edit/delete actions.
def render_frontend_record_grid_jsx():
    return dedent(
        """
        import { formatRecordValue } from '../entityUtils.js';

        export default function RecordGrid({ activeEntity, displayItems, recordLabel, onEdit, onDelete }) {
          return (
            <section className="panel">
              <h2>{activeEntity.name} {recordLabel || 'Records'}</h2>
              <div className="record-grid">
                {displayItems.map((item, index) => (
                  <article className="record-card" key={`${item.id || 'item'}-${index}`}>
                    <div className="record-actions">
                      <span className="record-id">#{item.id ?? index + 1}</span>
                      <div className="inline-actions">
                        <button className="ghost-button" type="button" onClick={() => onEdit(item)}>
                          Edit
                        </button>
                        <button className="ghost-button" type="button" onClick={() => onDelete(item.id)}>
                          Delete
                        </button>
                      </div>
                    </div>
                    {Object.entries(item).map(([key, value]) => (
                      key === 'id' ? null : (
                        <div className="record-line" key={key}>
                          <span>{key}</span>
                          <strong>{formatRecordValue(value)}</strong>
                        </div>
                      )
                    ))}
                  </article>
                ))}
              </div>
            </section>
          );
        }
        """
    ).strip() + "\n"


def render_frontend_summary_cards_jsx():
    return dedent(
        """
        export default function SummaryCards({ summaryCards, summary, selectedTable, entityCount }) {
          return (
            <section className="metrics-grid">
              <article className="metric-card">
                <span>{summaryCards[0]}</span>
                <strong>{summary.totalItems || 0}</strong>
              </article>
              <article className="metric-card">
                <span>{summaryCards[1]}</span>
                <strong>{summary.primaryRoute || `/api/${selectedTable}`}</strong>
              </article>
              <article className="metric-card">
                <span>{summaryCards[2]}</span>
                <strong>{entityCount}</strong>
              </article>
            </section>
          );
        }
        """
    ).strip() + "\n"


def render_frontend_search_panel_jsx():
    return dedent(
        """
        export default function SearchPanel({ searchQuery, setSearchQuery, handleSearch, scaffoldFamily, searchResults }) {
          return (
            <div className="panel">
              <div className="panel-header">
                <h2>Search</h2>
                <span className="role-pill">Cross-entity lookup</span>
              </div>
              <form className="search-row" onSubmit={handleSearch}>
                <input
                  className="search-input"
                  type="text"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder={scaffoldFamily.search_placeholder || 'Search records, statuses, and links'}
                />
                <button className="primary-button" type="submit">Search</button>
              </form>
              <div className="stack">
                {searchResults.map((result, index) => (
                  <div className="section-row" key={`${result.table}-${result.item.id}-${index}`}>
                    <strong>{result.entity}</strong>
                    <p>{Object.values(result.item).filter(Boolean).slice(0, 3).join(' · ')}</p>
                  </div>
                ))}
              </div>
            </div>
          );
        }
        """
    ).strip() + "\n"


def render_frontend_automation_panel_jsx():
    return dedent(
        """
        export default function AutomationPanel({ automationActions, canEdit, handleAutomation }) {
          return (
            <div className="panel">
              <div className="panel-header">
                <h2>Automation</h2>
                <span className="role-pill">{canEdit ? 'Runnable' : 'Read only'}</span>
              </div>
              <div className="button-row">
                {automationActions.map((action) => (
                  <button className="ghost-button" type="button" onClick={() => handleAutomation(action.action)} key={action.action}>
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          );
        }
        """
    ).strip() + "\n"


def render_frontend_sections_panel_jsx():
    return dedent(
        """
        export default function SectionsPanel({ sections }) {
          return (
            <div className="panel">
              <h2>Dashboard Sections</h2>
              <div className="stack">
                {(sections || []).map((section) => (
                  <div className="section-row" key={section.title}>
                    <strong>{section.title}</strong>
                    <p>{section.description}</p>
                  </div>
                ))}
              </div>
            </div>
          );
        }
        """
    ).strip() + "\n"


def render_frontend_workflow_panel_jsx():
    return dedent(
        """
        export default function WorkflowPanel({ activeEntity, workflows, statusEntries }) {
          return (
            <div className="panel">
              <h2>{activeEntity.name} Workflow</h2>
              <div className="stack">
                {(workflows || []).map((workflow) => (
                  <div className="workflow-card" key={workflow.name}>
                    <strong>{workflow.name}</strong>
                    <div className="workflow-steps">
                      {(workflow.steps || []).map((step) => (
                        <span className="status-chip" key={step}>{step}</span>
                      ))}
                    </div>
                  </div>
                ))}
                {!workflows?.length && statusEntries.map(([status, count]) => (
                  <div className="status-chip status-row" key={status}>
                    <span>{status}</span>
                    <strong>{count}</strong>
                  </div>
                ))}
              </div>
            </div>
          );
        }
        """
    ).strip() + "\n"


def render_frontend_integrations_panel_jsx():
    return dedent(
        """
        export default function IntegrationsPanel({ integrations, handleIntegrationTest, handleProviderAction }) {
          return (
            <div className="panel">
              <div className="panel-header">
                <h2>Integrations</h2>
                <span className="role-pill">Provider layer</span>
              </div>
              <div className="stack">
                {Object.entries(integrations || {}).filter(([key]) => key !== 'webhook_topics').map(([key, value]) => (
                  <div className="section-row" key={key}>
                    <strong>{key}</strong>
                    <p>{String(value)}</p>
                    <button className="ghost-button" type="button" onClick={() => handleIntegrationTest(key)}>
                      Send Test Event
                    </button>
                  </div>
                ))}
              </div>
              <div className="button-row">
                <button className="ghost-button" type="button" onClick={() => handleProviderAction('payment')}>
                  Create Checkout
                </button>
                <button className="ghost-button" type="button" onClick={() => handleProviderAction('email')}>
                  Send Email
                </button>
                <button className="ghost-button" type="button" onClick={() => handleProviderAction('storage')}>
                  Prepare Upload
                </button>
              </div>
            </div>
          );
        }
        """
    ).strip() + "\n"


def render_frontend_feed_panels_jsx():
    return dedent(
        """
        export function IntegrationEventsPanel({ integrationEvents }) {
          return (
            <div className="panel">
              <h2>Integration Events</h2>
              <div className="stack">
                {integrationEvents.map((event) => (
                  <div className="section-row" key={event.id}>
                    <strong>{event.provider} · {event.direction}</strong>
                    <p>{event.event_type}</p>
                  </div>
                ))}
              </div>
            </div>
          );
        }

        export function ProviderResponsesPanel({ providerResponses }) {
          return (
            <section className="panel">
              <h2>Provider Responses</h2>
              <div className="stack">
                {providerResponses.map((entry, index) => (
                  <div className="section-row" key={`${entry.kind}-${index}`}>
                    <strong>{entry.kind}</strong>
                    <p>{JSON.stringify(entry.data).slice(0, 180)}</p>
                  </div>
                ))}
              </div>
            </section>
          );
        }

        export function NotificationsPanel({ notifications }) {
          return (
            <section className="panel">
              <h2>Notifications</h2>
              <div className="stack">
                {notifications.map((notification) => (
                  <div className="section-row" key={notification.id}>
                    <strong>{notification.entity} · {notification.action}</strong>
                    <p>{notification.message}</p>
                  </div>
                ))}
              </div>
            </section>
          );
        }

        export function EntityMapPanel({ entities }) {
          return (
            <div className="panel">
              <h2>Entity Map</h2>
              <div className="stack">
                {(entities || []).map((entity) => (
                  <div className="section-row" key={entity.name}>
                    <strong>{entity.name}</strong>
                    <p>{(entity.fields || []).map((field) => `${field.name}:${field.type}`).join(', ')}</p>
                  </div>
                ))}
              </div>
            </div>
          );
        }
        """
    ).strip() + "\n"


def render_frontend_routes_js(manifest):
    routes = [
        {
            "name": page["name"],
            "purpose": page["purpose"],
            "layout": page.get("layout", "workspace"),
            "widgets": page.get("widgets", []),
            "path": _page_route_path(page, index),
            "component": _page_component_name(page),
            "mode": _page_mode(page),
        }
        for index, page in enumerate(manifest["pages"])
    ]
    return f"export const APP_ROUTES = {_json(routes)};\n"


def render_frontend_page_helpers_jsx():
    return dedent(
        """
        import SummaryCards from '../components/SummaryCards.jsx';
        import SearchPanel from '../components/SearchPanel.jsx';
        import AutomationPanel from '../components/AutomationPanel.jsx';
        import EntityForm from '../components/EntityForm.jsx';
        import SectionsPanel from '../components/SectionsPanel.jsx';
        import WorkflowPanel from '../components/WorkflowPanel.jsx';
        import IntegrationsPanel from '../components/IntegrationsPanel.jsx';
        import { EntityMapPanel, IntegrationEventsPanel, NotificationsPanel, ProviderResponsesPanel } from '../components/FeedPanels.jsx';
        import RecordGrid from '../components/RecordGrid.jsx';

        function PageHero({ page, config, error }) {
          return (
            <>
              <header className="hero">
                <span className="eyebrow">{page.layout || 'workspace'}</span>
                <h1>{page.name}</h1>
                <p className="lead">{page.purpose || config.subheadline || config.summary}</p>
              </header>
              {error ? <div className="error-banner">Backend unavailable: {error}</div> : null}
            </>
          );
        }

        export default function GeneratedPageLayout({ page, mode, appState }) {
          const {
            config,
            error,
            summaryCards,
            summary,
            selectedTable,
            statusEntries,
            scaffoldFamily,
            searchQuery,
            setSearchQuery,
            searchResults,
            handleSearch,
            automationActions,
            canEdit,
            handleAutomation,
            activeEntity,
            fields,
            formValues,
            editingItemId,
            selectedUser,
            saving,
            updateField,
            resetComposer,
            handleSaveRecord,
            displayItems,
            beginEdit,
            handleDeleteRecord,
            handleIntegrationTest,
            handleProviderAction,
            integrationEvents,
            providerResponses,
            notifications,
            familyPanel,
          } = appState;

          return (
            <>
              <PageHero page={page} config={config} error={error} />

              {mode === 'dashboard' ? (
                <>
                  <SummaryCards
                    summaryCards={summaryCards}
                    summary={summary}
                    selectedTable={selectedTable}
                    entityCount={(config.entities || []).length}
                  />

                  <section className="content-grid">
                    <SearchPanel
                      searchQuery={searchQuery}
                      setSearchQuery={setSearchQuery}
                      handleSearch={handleSearch}
                      scaffoldFamily={scaffoldFamily}
                      searchResults={searchResults}
                    />
                    <AutomationPanel
                      automationActions={automationActions}
                      canEdit={canEdit}
                      handleAutomation={handleAutomation}
                    />
                  </section>

                  <section className="content-grid">
                    {familyPanel}
                    <SectionsPanel sections={config.sections} />
                    <WorkflowPanel activeEntity={activeEntity} workflows={config.workflows} statusEntries={statusEntries} />
                  </section>
                </>
              ) : null}

              {mode === 'operations' ? (
                <>
                  <section className="content-grid">
                    {familyPanel}
                    <IntegrationsPanel
                      integrations={config.integrations}
                      handleIntegrationTest={handleIntegrationTest}
                      handleProviderAction={handleProviderAction}
                    />
                    <IntegrationEventsPanel integrationEvents={integrationEvents} />
                  </section>

                  <ProviderResponsesPanel providerResponses={providerResponses} />
                  <NotificationsPanel notifications={notifications} />
                </>
              ) : null}

              {mode === 'records' ? (
                <>
                  <section className="content-grid">
                    <EntityForm
                      activeEntity={activeEntity}
                      fields={fields}
                      formValues={formValues}
                      editingItemId={editingItemId}
                      selectedUser={selectedUser}
                      saving={saving}
                      canEdit={canEdit}
                      onFieldChange={updateField}
                      onReset={() => resetComposer()}
                      onSubmit={handleSaveRecord}
                    />

                    <EntityMapPanel entities={config.entities} />
                  </section>

                  <RecordGrid
                    activeEntity={activeEntity}
                    displayItems={displayItems}
                    recordLabel={scaffoldFamily.record_label}
                    onEdit={beginEdit}
                    onDelete={handleDeleteRecord}
                  />
                </>
              ) : null}
            </>
          );
        }
        """
    ).strip() + "\n"


def render_frontend_page_module(page, index):
    page_json = _json(
        {
            "name": page["name"],
            "purpose": page["purpose"],
            "layout": page.get("layout", "workspace"),
            "widgets": page.get("widgets", []),
            "path": _page_route_path(page, index),
        }
    )
    mode = _page_mode(page)
    component_name = _page_component_name(page)
    return dedent(
        f"""
        import GeneratedPageLayout from './pageHelpers.jsx';

        const page = {page_json};

        export default function {component_name}({{ appState }}) {{
          return <GeneratedPageLayout page={{page}} mode={mode!r} appState={{appState}} />;
        }}
        """
    ).strip() + "\n"


def render_frontend_pages_index_js(manifest):
    imports = []
    mappings = []
    for page in manifest["pages"]:
        component_name = _page_component_name(page)
        imports.append(f"import {component_name} from './{_page_component_filename(page)}';")
        mappings.append(f"  {component_name},")
    return "\n".join(imports + ["", "export const PAGE_COMPONENTS = {", *mappings, "};", ""]) 


# Render the shared dashboard application shell. It now owns data/state and
# route composition while page modules render the actual screen content.
def render_frontend_app_shell_jsx():
    summary_cards = _json(["Active Pipelines", "Primary Route", "Entities"])
    # The frontend template mirrors backend capabilities: multi-entity CRUD, search, automation,
    # notifications, and provider actions are all exposed through one generated dashboard shell.
    return (
        dedent(
            """
            import { useEffect, useMemo, useState } from 'react';
            import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
            __FAMILY_FRONTEND_IMPORTS__
            import { API_BASE } from './api.js';
            import { entityToTableName } from './entityUtils.js';
            import { APP_ROUTES } from './routes.js';
            import { PAGE_COMPONENTS } from './pages/index.js';

            const defaultSummaryCards = __SUMMARY_CARDS__;
            const emptyConfig = {
              appName: 'Generated SaaS',
              appType: 'saas_dashboard',
              appTypeLabel: 'SaaS Dashboard',
              tagline: '',
              summary: '',
              primaryEntity: 'Work Item',
              scaffoldFamily: {
                template_key: 'dashboard_shell',
                navigation_style: 'tabs',
                summary_cards: defaultSummaryCards,
                automation_actions: [
                  { action: 'sync-status', label: 'Sync Status' },
                  { action: 'notify-team', label: 'Notify Team' },
                ],
                record_label: 'Records',
                search_placeholder: 'Search records, statuses, and links',
              },
              headline: '',
              subheadline: '',
              theme: {
                primary_color: '#0f766e',
                accent_color: '#f59e0b',
                surface_color: '#ecfeff',
              },
              sections: [],
              pages: [],
              workflows: [],
              auth: { enabled: true, roles: [], demo_users: [] },
              routes: [],
              entities: [],
              defaultFormValues: {},
              primaryTable: '',
            };

            export default function App() {
              // App-wide state mirrors the backend surface area so the generated
              // UI can exercise every major capability immediately.
              const [config, setConfig] = useState(emptyConfig);
              const [items, setItems] = useState([]);
              const [summary, setSummary] = useState({ totalItems: 0, statusBreakdown: {}, recordLabel: 'Work Item' });
              const [selectedTable, setSelectedTable] = useState('');
              const [formValues, setFormValues] = useState({});
              const [editingItemId, setEditingItemId] = useState(null);
              const [selectedUser, setSelectedUser] = useState(null);
              const [searchQuery, setSearchQuery] = useState('');
              const [searchResults, setSearchResults] = useState([]);
              const [notifications, setNotifications] = useState([]);
              const [integrationEvents, setIntegrationEvents] = useState([]);
              const [providerResponses, setProviderResponses] = useState([]);
            __FAMILY_FRONTEND_STATE__
              const [error, setError] = useState('');
              const [saving, setSaving] = useState(false);

              // Initial bootstrap request bundle: config, summary, auth state,
              // notifications, and integration history.
              async function loadConfigAndSession() {
                const [configResponse, summaryResponse, sessionResponse, notificationResponse, integrationResponse] = await Promise.all([
                  fetch(`${API_BASE}/api/config`),
                  fetch(`${API_BASE}/api/summary`),
                  fetch(`${API_BASE}/api/auth/session`),
                  fetch(`${API_BASE}/api/notifications`),
                  fetch(`${API_BASE}/api/integration-events`),
                ]);
                const configData = await configResponse.json();
                const summaryData = await summaryResponse.json();
                const sessionData = await sessionResponse.json();
                const notificationData = await notificationResponse.json();
                const integrationData = await integrationResponse.json();
                setConfig(configData);
                setSummary(summaryData);
                setSelectedUser(sessionData.user);
                setNotifications(notificationData.notifications || []);
                setIntegrationEvents(integrationData.events || []);
                setSelectedTable((current) => current || configData.primaryTable);
                setFormValues((current) => Object.keys(current).length ? current : (configData.defaultFormValues[configData.primaryEntity] || {}));
                return configData;
              }

            __FAMILY_FRONTEND_LOADERS__
              // Fetch records for the currently selected entity/table.
              async function loadEntityItems(tableName) {
                const response = await fetch(`${API_BASE}/api/${tableName}`);
                const data = await response.json();
                setItems(data.items || []);
              }

              // First-load orchestrator that decides which table should populate
              // the dashboard once config is available.
              async function loadData() {
                try {
                  const configData = await loadConfigAndSession();
                  const tableName = selectedTable || configData.primaryTable;
                  if (tableName) {
                    await loadEntityItems(tableName);
                  }
            __FAMILY_FRONTEND_LOAD_DATA__
                } catch (loadError) {
                  setError(loadError.message);
                }
              }

              useEffect(() => {
                loadData();
              }, []);

              useEffect(() => {
                if (selectedTable) {
                  loadEntityItems(selectedTable).catch((loadError) => setError(loadError.message));
                }
              }, [selectedTable]);

              // Derived display state used throughout the dashboard.
              const theme = config.theme || emptyConfig.theme;
              const scaffoldFamily = config.scaffoldFamily || emptyConfig.scaffoldFamily;
              const summaryCards = scaffoldFamily.summary_cards || defaultSummaryCards;
              const automationActions = scaffoldFamily.automation_actions || emptyConfig.scaffoldFamily.automation_actions;
              const statusEntries = Object.entries(summary.statusBreakdown || {});
              const displayItems = useMemo(() => items.slice(0, 12), [items]);
              const canEdit = ['owner', 'manager', 'member'].includes(selectedUser?.role);
              const activeEntity = (config.entities || []).find((entity) => {
                return entityToTableName(entity.name) === selectedTable;
              }) || (config.entities || [])[0] || { name: config.primaryEntity, fields: [] };
              const fields = activeEntity.fields || [];

              // Form helpers for create/edit state.
              function resetComposer(entityName = activeEntity.name) {
                setEditingItemId(null);
                setFormValues(config.defaultFormValues?.[entityName] || {});
              }

              function updateField(field, nextValue) {
                setFormValues((current) => ({ ...current, [field.name]: nextValue }));
              }

              function beginEdit(item) {
                const values = {};
                for (const field of fields) {
                  values[field.name] = item[field.name] ?? '';
                }
                setEditingItemId(item.id);
                setFormValues(values);
              }

              // Session switching is demo-only, but it exercises generated role
              // gates and read/write behavior in the scaffold.
              async function handleUserChange(email) {
                try {
                  const response = await fetch(`${API_BASE}/api/auth/session`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email }),
                  });
                  const sessionData = await response.json();
                  setSelectedUser(sessionData.user);
                } catch (sessionError) {
                  setError(sessionError.message);
                }
              }

              // Changing entities swaps both the record list and the active form schema.
              async function handleEntityChange(tableName) {
                setSelectedTable(tableName);
                const nextEntity = (config.entities || []).find((entity) => entityToTableName(entity.name) === tableName);
                resetComposer(nextEntity?.name);
              }

              // Create or update the active entity based on edit mode.
              async function handleSaveRecord(event) {
                event.preventDefault();
                if (!canEdit) {
                  setError('This role has read-only access.');
                  return;
                }
                setSaving(true);
                setError('');
                try {
                  const response = await fetch(`${API_BASE}/api/${selectedTable}${editingItemId ? `/${editingItemId}` : ''}?user_email=${encodeURIComponent(selectedUser?.email || '')}`, {
                    method: editingItemId ? 'PUT' : 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ values: formValues }),
                  });
                  if (!response.ok) {
                    throw new Error(`Failed to save record (${response.status})`);
                  }
                  resetComposer();
                  await loadEntityItems(selectedTable);
                  const summaryResponse = await fetch(`${API_BASE}/api/summary`);
                  setSummary(await summaryResponse.json());
                  const notificationResponse = await fetch(`${API_BASE}/api/notifications`);
                  setNotifications((await notificationResponse.json()).notifications || []);
            __FAMILY_FRONTEND_AFTER_NOTIFICATION__
                } catch (saveError) {
                  setError(saveError.message);
                } finally {
                  setSaving(false);
                }
              }

              // Delete a record, then refresh the side panels affected by that mutation.
              async function handleDeleteRecord(itemId) {
                if (!canEdit) {
                  setError('This role has read-only access.');
                  return;
                }
                setError('');
                try {
                  const response = await fetch(`${API_BASE}/api/${selectedTable}/${itemId}?user_email=${encodeURIComponent(selectedUser?.email || '')}`, {
                    method: 'DELETE',
                  });
                  if (!response.ok) {
                    throw new Error(`Failed to delete record (${response.status})`);
                  }
                  await loadEntityItems(selectedTable);
                  const summaryResponse = await fetch(`${API_BASE}/api/summary`);
                  setSummary(await summaryResponse.json());
                  const notificationResponse = await fetch(`${API_BASE}/api/notifications`);
                  setNotifications((await notificationResponse.json()).notifications || []);
            __FAMILY_FRONTEND_AFTER_NOTIFICATION__
                  const integrationResponse = await fetch(`${API_BASE}/api/integration-events`);
                  setIntegrationEvents((await integrationResponse.json()).events || []);
            __FAMILY_FRONTEND_AFTER_INTEGRATION__
                } catch (deleteError) {
                  setError(deleteError.message);
                }
              }

              // Cross-entity search uses the backend aggregation route.
              async function handleSearch(event) {
                event.preventDefault();
                try {
                  const response = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(searchQuery)}`);
                  const data = await response.json();
                  setSearchResults(data.results || []);
                } catch (searchError) {
                  setError(searchError.message);
                }
              }

              // Automation is intentionally generic here; the manifest decides the
              // app family and the generated backend records the invocation.
              async function handleAutomation(action) {
                if (!selectedTable || !canEdit) {
                  return;
                }
                try {
                  const response = await fetch(`${API_BASE}/api/automation/run?user_email=${encodeURIComponent(selectedUser?.email || '')}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ entity: activeEntity.name, table_name: selectedTable, action, record_id: editingItemId }),
                  });
                  if (!response.ok) {
                    throw new Error(`Failed to run automation (${response.status})`);
                  }
                  const notificationResponse = await fetch(`${API_BASE}/api/notifications`);
                  setNotifications((await notificationResponse.json()).notifications || []);
                } catch (automationError) {
                  setError(automationError.message);
                }
              }

              // Send a synthetic integration event through the provider layer.
              async function handleIntegrationTest(providerKey) {
                if (!canEdit) {
                  setError('This role has read-only access.');
                  return;
                }
                try {
                  const providerName = config.integrations?.[providerKey];
                  const response = await fetch(`${API_BASE}/api/integrations/test?user_email=${encodeURIComponent(selectedUser?.email || '')}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      provider: providerName,
                      event_type: `${providerKey}.test`,
                      payload: { entity: activeEntity.name, table: selectedTable },
                    }),
                  });
                  if (!response.ok) {
                    throw new Error(`Failed integration test (${response.status})`);
                  }
                  const [notificationResponse, integrationResponse] = await Promise.all([
                    fetch(`${API_BASE}/api/notifications`),
                    fetch(`${API_BASE}/api/integration-events`),
                  ]);
                  setNotifications((await notificationResponse.json()).notifications || []);
                  setIntegrationEvents((await integrationResponse.json()).events || []);
                } catch (integrationError) {
                  setError(integrationError.message);
                }
              }

              // Trigger one of the concrete provider-shaped endpoints exposed by the backend.
              async function handleProviderAction(kind) {
                if (!canEdit) {
                  setError('This role has read-only access.');
                  return;
                }
                try {
                  const routeMap = {
                    payment: {
                      path: '/api/integrations/payment/checkout',
                      payload: { amount: 49, currency: 'usd', description: `${activeEntity.name} checkout` },
                    },
                    email: {
                      path: '/api/integrations/email/send',
                      payload: { to_email: selectedUser?.email || 'demo@example.com', subject: `${config.appName} update`, body: `Update triggered for ${activeEntity.name}` },
                    },
                    storage: {
                      path: '/api/integrations/storage/presign',
                      payload: { file_name: `${selectedTable || 'record'}.json`, content_type: 'application/json' },
                    },
                  };
                  const spec = routeMap[kind];
                  const response = await fetch(`${API_BASE}${spec.path}?user_email=${encodeURIComponent(selectedUser?.email || '')}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(spec.payload),
                  });
                  if (!response.ok) {
                    throw new Error(`Provider action failed (${response.status})`);
                  }
                  const data = await response.json();
                  setProviderResponses((current) => [{ kind, data }, ...current].slice(0, 6));
                  const [notificationResponse, integrationResponse] = await Promise.all([
                    fetch(`${API_BASE}/api/notifications`),
                    fetch(`${API_BASE}/api/integration-events`),
                  ]);
                  setNotifications((await notificationResponse.json()).notifications || []);
                  setIntegrationEvents((await integrationResponse.json()).events || []);
                } catch (providerError) {
                  setError(providerError.message);
                }
              }

              const familyPanel = (
                <>
            __FAMILY_FRONTEND_PANEL__
                </>
              );
              const routeFallback = APP_ROUTES[0]?.path || '/';
              const appState = {
                config,
                items,
                summary,
                selectedTable,
                formValues,
                editingItemId,
                selectedUser,
                searchQuery,
                setSearchQuery,
                searchResults,
                notifications,
                integrationEvents,
                providerResponses,
                error,
                saving,
                theme,
                scaffoldFamily,
                summaryCards,
                automationActions,
                statusEntries,
                displayItems,
                canEdit,
                activeEntity,
                fields,
                resetComposer,
                updateField,
                beginEdit,
                handleUserChange,
                handleEntityChange,
                handleSaveRecord,
                handleDeleteRecord,
                handleSearch,
                handleAutomation,
                handleIntegrationTest,
                handleProviderAction,
                familyPanel,
              };

              // The rendered layout is now route-driven: the shell owns shared
              // state and navigation while generated page modules render the
              // actual screens from manifest.pages.
              return (
                <div
                  className="page-shell"
                  style={{
                    '--primary': theme.primary_color,
                    '--accent': theme.accent_color,
                    '--surface': theme.surface_color,
                  }}
                >
                  <nav className="top-nav">
                    <div className="brand-lockup">
                      <span className="eyebrow">{config.appTypeLabel}</span>
                      <strong>{config.appName}</strong>
                    </div>
                    <div className="nav-links nav-tools">
                      {selectedUser ? (
                        <select className="user-select" value={selectedUser.email} onChange={(event) => handleUserChange(event.target.value)}>
                          {(config.auth?.demo_users || []).map((user) => (
                            <option value={user.email} key={user.email}>
                              {user.name} ({user.role})
                            </option>
                          ))}
                        </select>
                      ) : null}
                      <select className="user-select" value={selectedTable} onChange={(event) => handleEntityChange(event.target.value)}>
                        {(config.entities || []).map((entity) => {
                          const tableName = entityToTableName(entity.name);
                          return <option value={tableName} key={entity.name}>{entity.name}</option>;
                        })}
                      </select>
                      {APP_ROUTES.map((page) => (
                        <NavLink className="nav-pill" to={page.path} key={page.name}>
                          {page.name}
                        </NavLink>
                      ))}
                    </div>
                  </nav>

                  <Routes>
                    {APP_ROUTES.map((page) => {
                      const PageComponent = PAGE_COMPONENTS[page.component];
                      return (
                        <Route
                          key={page.path}
                          path={page.path}
                          element={<PageComponent appState={appState} />}
                        />
                      );
                    })}
                    <Route path="*" element={<Navigate to={routeFallback} replace />} />
                  </Routes>
                </div>
              );
            }
            """
        ).strip().replace("__SUMMARY_CARDS__", summary_cards) + "\n"
    )


# Thin frontend entrypoint that keeps the top-level app file stable while the
# shared dashboard shell lives in its own generated module.
def render_frontend_app_jsx():
    return dedent(
        """
        import { BrowserRouter } from 'react-router-dom';
        import AppShell from './appShell.jsx';

        export default function App() {
          return (
            <BrowserRouter>
              <AppShell />
            </BrowserRouter>
          );
        }
        """
    ).strip() + "\n"


# Styling for the generated frontend. This stays in one file so the scaffold is
# easy to inspect and copy forward into a real app.
def render_frontend_styles():
    return dedent(
        """
        :root {
          font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
          color: #0f172a;
          background: #f8fafc;
        }

        * {
          box-sizing: border-box;
        }

        body {
          margin: 0;
        }

        button,
        input,
        select {
          font: inherit;
        }

        .page-shell {
          min-height: 100vh;
          padding: 32px;
          background:
            radial-gradient(circle at top left, var(--surface), transparent 40%),
            linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        }

        .hero {
          max-width: 760px;
          margin-bottom: 24px;
        }

        .top-nav {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 16px;
          margin-bottom: 24px;
          flex-wrap: wrap;
        }

        .brand-lockup {
          display: grid;
          gap: 4px;
        }

        .nav-links {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }

        .nav-tools {
          align-items: center;
        }

        .nav-pill {
          padding: 10px 14px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.72);
          border: 1px solid rgba(148, 163, 184, 0.3);
          font-size: 0.9rem;
        }

        .user-select {
          border: 1px solid rgba(148, 163, 184, 0.35);
          border-radius: 999px;
          padding: 10px 14px;
          background: rgba(255, 255, 255, 0.82);
        }

        .eyebrow {
          text-transform: uppercase;
          letter-spacing: 0.18em;
          color: var(--primary);
          font-size: 12px;
          font-weight: 700;
        }

        h1 {
          margin: 0 0 12px;
          font-size: clamp(2.2rem, 5vw, 4.8rem);
          line-height: 0.95;
        }

        h2 {
          margin-top: 0;
        }

        .lead {
          margin: 0;
          font-size: 1.05rem;
          color: #334155;
        }

        .metrics-grid,
        .content-grid,
        .record-grid,
        .form-grid {
          display: grid;
          gap: 16px;
        }

        .metrics-grid {
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          margin-bottom: 16px;
        }

        .content-grid {
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          margin-bottom: 16px;
        }

        .form-grid {
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          margin-bottom: 16px;
        }

        .panel,
        .metric-card,
        .record-card {
          background: rgba(255, 255, 255, 0.82);
          border: 1px solid rgba(148, 163, 184, 0.25);
          border-radius: 20px;
          padding: 20px;
          box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
          backdrop-filter: blur(10px);
        }

        .field {
          display: grid;
          gap: 8px;
        }

        .field input[type='text'],
        .field input[type='number'] {
          width: 100%;
          border: 1px solid rgba(148, 163, 184, 0.35);
          border-radius: 12px;
          padding: 12px 14px;
          background: rgba(255, 255, 255, 0.9);
        }

        .search-row {
          display: flex;
          gap: 10px;
          margin-bottom: 16px;
          flex-wrap: wrap;
        }

        .search-input {
          flex: 1;
          min-width: 220px;
          border: 1px solid rgba(148, 163, 184, 0.35);
          border-radius: 12px;
          padding: 12px 14px;
          background: rgba(255, 255, 255, 0.9);
        }

        .field input[type='checkbox'] {
          width: 20px;
          height: 20px;
        }

        .primary-button,
        .ghost-button {
          border: none;
          border-radius: 999px;
          padding: 12px 16px;
          cursor: pointer;
        }

        .primary-button {
          background: var(--primary);
          color: white;
          font-weight: 700;
        }

        .ghost-button {
          background: rgba(255, 255, 255, 0.75);
          color: #0f172a;
          border: 1px solid rgba(148, 163, 184, 0.35);
        }

        .button-row,
        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }

        .role-pill {
          padding: 8px 12px;
          border-radius: 999px;
          background: color-mix(in srgb, var(--surface) 75%, white);
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }

        .metric-card span,
        .record-line span,
        .status-chip span,
        .field span,
        .record-id {
          display: block;
          color: #475569;
          font-size: 0.8rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }

        .metric-card strong,
        .record-line strong,
        .status-chip strong {
          display: block;
          margin-top: 6px;
          font-size: 1.2rem;
        }

        .stack {
          display: grid;
          gap: 12px;
        }

        .section-row p {
          margin: 4px 0 0;
          color: #334155;
        }

        .status-chip {
          display: inline-flex;
          justify-content: center;
          align-items: center;
          padding: 10px 12px;
          background: color-mix(in srgb, var(--surface) 70%, white);
          border-radius: 14px;
        }

        .status-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .workflow-card {
          padding: 14px;
          border-radius: 16px;
          background: color-mix(in srgb, white 80%, var(--surface));
          border: 1px solid rgba(148, 163, 184, 0.25);
        }

        .workflow-steps {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin-top: 10px;
        }

        .record-grid {
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        }

        .record-actions {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }

        .inline-actions {
          display: flex;
          gap: 8px;
        }

        .record-line + .record-line {
          margin-top: 12px;
        }

        .error-banner {
          margin-bottom: 16px;
          padding: 14px 16px;
          border-radius: 14px;
          background: #fee2e2;
          color: #991b1b;
        }

        @media (max-width: 640px) {
          .page-shell {
            padding: 20px;
          }
        }
        """
    ).strip() + "\n"


# Docker image for serving the generated React app through `vite preview`.
def render_frontend_dockerfile():
    return dedent(
        """
        FROM node:20-alpine
        WORKDIR /app
        COPY package*.json /app/
        RUN npm install
        COPY . /app
        CMD ["npm", "run", "preview"]
        """
    ).strip() + "\n"


def render_root_env_example(manifest):
    slug = manifest["slug"].upper().replace("-", "_")
    return dedent(
        f"""
        APP_NAME="{manifest['app_name']}"
        APP_SLUG="{manifest['slug']}"
        {slug}_BACKEND_URL=http://localhost:8000
        {slug}_FRONTEND_URL=http://localhost:4173
        EMAIL_API_KEY=
        PAYMENTS_SECRET_KEY=
        PAYMENTS_PUBLIC_KEY=
        STORAGE_ACCESS_KEY=
        STORAGE_SECRET_KEY=
        """
    ).strip() + "\n"


def render_deploy_docker_compose(manifest):
    return dedent(
        f"""
        version: "3.9"

        services:
          backend:
            build:
              context: ..
              dockerfile: backend/Dockerfile
            container_name: {manifest['slug']}_backend
            ports:
              - "8000:8000"
            env_file:
              - ../.env.example

          frontend:
            build:
              context: ../frontend
              dockerfile: Dockerfile
            container_name: {manifest['slug']}_frontend
            ports:
              - "4173:4173"
            environment:
              VITE_API_BASE_URL: http://backend:8000
            depends_on:
              - backend
        """
    ).strip() + "\n"


def render_deploy_render_yaml(manifest):
    return dedent(
        f"""
        services:
          - type: web
            name: {manifest['slug']}-backend
            env: docker
            dockerfilePath: backend/Dockerfile
            rootDir: .
            plan: starter
            envVars:
              - key: DATABASE_URL
                value: sqlite:///./app.db

          - type: web
            name: {manifest['slug']}-frontend
            env: docker
            dockerfilePath: frontend/Dockerfile
            rootDir: frontend
            plan: starter
        """
    ).strip() + "\n"


def render_deploy_railway_json(manifest):
    return json.dumps(
        {
            "$schema": "https://railway.app/railway.schema.json",
            "build": {"builder": "DOCKERFILE"},
            "deploy": {
                "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
                "restartPolicyType": "ON_FAILURE",
                "restartPolicyMaxRetries": 10,
            },
            "metadata": {"appName": manifest["app_name"], "slug": manifest["slug"]},
        },
        indent=2,
    ) + "\n"


def render_deploy_readme(manifest):
    return dedent(
        f"""
        # Deployment Artifacts

        This generated app includes deployment outputs for:
        - Local Docker Compose: `deploy/docker-compose.yml`
        - Render: `deploy/render.yaml`
        - Railway: `deploy/railway.json`
        - Shared environment template: `.env.example`

        Suggested deploy split:
        - Backend service: FastAPI container from `backend/Dockerfile`
        - Frontend service: Vite preview container from `frontend/Dockerfile`

        App family: `{manifest['app_type']}`
        Primary entity: `{manifest['primary_entity']}`
        """
    ).strip() + "\n"


# ---------------------------------------------------------------------------
# Shared project assembly
# ---------------------------------------------------------------------------

# The shared dashboard shell remains the default implementation used by the
# current family renderers. Family-specific modules can fork from this function
# over time without changing the rest of the generation pipeline.
def build_dashboard_shell_project_files(manifest, previous_manifest=None, existing_migration_versions=None):
    files = [
        (".env.example", render_root_env_example(manifest)),
        ("backend/main.py", render_backend_main()),
        ("backend/app_config.py", render_backend_config_module(manifest)),
        ("backend/app_core.py", render_backend_app_core(manifest)),
        ("backend/database.py", render_backend_database_module()),
        ("backend/providers.py", render_backend_providers()),
        ("backend/requirements.txt", render_backend_requirements()),
        ("backend/Dockerfile", render_backend_dockerfile()),
        ("backend/seed_data.json", render_backend_seed_data(manifest)),
        ("backend/.env.example", render_backend_env_example(manifest)),
        ("backend/migrations/0001_initial.sql", render_backend_initial_migration(manifest)),
        ("backend/migrations/schema_snapshot.json", render_backend_schema_snapshot(manifest)),
        ("backend/migrations/history.json", render_backend_migration_history(existing_migration_versions)),
        ("backend/migrations/README.md", render_backend_migrations_readme()),
        ("frontend/package.json", render_frontend_package_json(manifest)),
        ("frontend/vite.config.js", render_frontend_vite_config()),
        ("frontend/index.html", render_frontend_index_html(manifest)),
        ("frontend/src/main.jsx", render_frontend_main_jsx()),
        ("frontend/src/api.js", render_frontend_api_js()),
        ("frontend/src/entityUtils.js", render_frontend_entity_utils_js()),
        ("frontend/src/routes.js", render_frontend_routes_js(manifest)),
        ("frontend/src/App.jsx", render_frontend_app_jsx()),
        ("frontend/src/appShell.jsx", render_frontend_app_shell_jsx()),
        ("frontend/src/pages/pageHelpers.jsx", render_frontend_page_helpers_jsx()),
        ("frontend/src/pages/index.js", render_frontend_pages_index_js(manifest)),
        ("frontend/src/components/SummaryCards.jsx", render_frontend_summary_cards_jsx()),
        ("frontend/src/components/SearchPanel.jsx", render_frontend_search_panel_jsx()),
        ("frontend/src/components/AutomationPanel.jsx", render_frontend_automation_panel_jsx()),
        ("frontend/src/components/EntityForm.jsx", render_frontend_entity_form_jsx()),
        ("frontend/src/components/SectionsPanel.jsx", render_frontend_sections_panel_jsx()),
        ("frontend/src/components/WorkflowPanel.jsx", render_frontend_workflow_panel_jsx()),
        ("frontend/src/components/IntegrationsPanel.jsx", render_frontend_integrations_panel_jsx()),
        ("frontend/src/components/FeedPanels.jsx", render_frontend_feed_panels_jsx()),
        ("frontend/src/components/RecordGrid.jsx", render_frontend_record_grid_jsx()),
        ("frontend/src/styles.css", render_frontend_styles()),
        ("frontend/Dockerfile", render_frontend_dockerfile()),
        ("deploy/docker-compose.yml", render_deploy_docker_compose(manifest)),
        ("deploy/render.yaml", render_deploy_render_yaml(manifest)),
        ("deploy/railway.json", render_deploy_railway_json(manifest)),
        ("deploy/README.md", render_deploy_readme(manifest)),
    ]
    if previous_manifest:
        next_version = max(existing_migration_versions or [1]) + 1
        incremental_source = render_backend_incremental_migration(previous_manifest, manifest, next_version)
        if "-- No schema changes detected." not in incremental_source:
            files.append((f"backend/migrations/{next_version:04d}_schema_update.sql", incremental_source))
            files = [
                (path, render_backend_migration_history(existing_migration_versions, next_version))
                if path == "backend/migrations/history.json"
                else (path, content)
                for path, content in files
            ]
    for index, page in enumerate(manifest["pages"]):
        files.append((f"frontend/src/pages/{_page_component_filename(page)}", render_frontend_page_module(page, index)))
    return files
