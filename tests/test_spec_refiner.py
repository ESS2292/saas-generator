from engine.intake import analyze_product_request
from engine.manifest import parse_manifest
from engine.spec_refiner import refine_product_spec


def test_refine_product_spec_extracts_structured_brief():
    intake = analyze_product_request("Build a marketplace for creators to sell digital products and manage orders.")
    brief = refine_product_spec(
        "Build a marketplace for creators to sell digital products and manage orders.",
        intake,
    )

    assert brief["closest_family"] == "marketplace"
    assert "seller" in brief["primary_users"]
    assert "listing" in brief["core_entities"]
    assert brief["core_workflows"]
    assert brief["clarification_prompts"]


def test_parse_manifest_uses_spec_brief_override():
    intake = analyze_product_request("Build a booking platform for photography studios.")
    spec_brief = refine_product_spec("Build a booking platform for photography studios.", intake)
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
        spec_brief=spec_brief,
    )

    assert manifest["spec_brief"]["closest_family"] == "booking_platform"
    assert manifest["spec_brief"]["support_tier"] == "supported"
    assert "booking" in manifest["spec_brief"]["core_entities"]
