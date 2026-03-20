from engine.intake import analyze_product_request
from engine.manifest import parse_manifest


def test_analyze_product_request_marks_supported_business_app():
    intake = analyze_product_request("Build an internal operations dashboard for approvals and incidents.")

    assert intake["support_tier"] == "supported"
    assert intake["closest_family"] == "internal_tool"
    assert intake["handoff_mode"] == "full_family_generation"


def test_analyze_product_request_detects_crm_family():
    intake = analyze_product_request("Build a CRM for account executives to manage leads and deals.")

    assert intake["support_tier"] == "supported"
    assert intake["closest_family"] == "crm_platform"


def test_analyze_product_request_marks_starter_only_broad_app():
    intake = analyze_product_request("Build a realtime chat and live video social app.")

    assert intake["support_tier"] == "starter_only"
    assert intake["handoff_mode"] == "starter_scaffold_with_limitations"


def test_analyze_product_request_marks_out_of_scope_system():
    intake = analyze_product_request("Build a new browser and operating system with a game engine.")

    assert intake["support_tier"] == "out_of_scope"
    assert intake["handoff_mode"] == "starter_scaffold_with_gap_report"


def test_parse_manifest_accepts_intake_context_override():
    intake = analyze_product_request("Build a booking platform for studios.")
    manifest = parse_manifest(
        """
        {
          "app_name": "Studio Reserve",
          "slug": "studio-reserve",
          "app_type": "booking_platform",
          "tagline": "Bookings",
          "summary": "Studio scheduling",
          "primary_entity": "Booking",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Bookings",
            "subheadline": "Manage reservations",
            "sections": [{"title": "Availability", "description": "Track slots"}]
          },
          "pages": [{"name": "Overview", "purpose": "See availability"}],
          "workflows": [{"name": "Confirm reservation", "steps": ["Request", "Confirm"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Booking", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/bookings", "method": "GET", "summary": "List bookings"}],
          "sample_records": [{"status": "scheduled"}]
        }
        """,
        intake_context=intake,
    )

    assert manifest["support_tier"] == "supported"
    assert manifest["closest_family"] == "booking_platform"
    assert manifest["refinement_steps"]
