import pytest

from engine.file_writer import GeneratedProjectError
from engine.manifest import parse_manifest
from templates.families import render_family_prompt_guide, render_product_boundary_guide


def test_parse_manifest_accepts_valid_json():
    manifest = parse_manifest(
        """
        {
          "app_name": "Revenue Radar",
          "slug": "revenue-radar",
          "app_type": "saas_dashboard",
          "tagline": "Track growth",
          "summary": "Revenue analytics for SaaS teams",
          "primary_entity": "Account",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Revenue command center",
            "subheadline": "Watch the pipeline move",
            "sections": [{"title": "MRR", "description": "Track recurring revenue"}]
          },
          "pages": [{"name": "Overview", "purpose": "See metrics"}],
          "workflows": [{"name": "Review pipeline", "steps": ["Inspect", "Assign", "Close"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Account", "fields": [{"name": "name", "type": "string"}]}],
          "api_routes": [{"path": "/accounts", "method": "GET", "summary": "List accounts"}],
          "sample_records": [{"title": "Acme", "status": "active"}]
        }
        """
    )

    assert manifest["slug"] == "revenue-radar"
    assert manifest["dashboard"]["sections"][0]["title"] == "MRR"
    assert manifest["app_type"] == "saas_dashboard"
    assert manifest["scaffold_family"]["app_type"] == "saas_dashboard"
    assert manifest["scaffold_family"]["template_key"] == "dashboard_shell"
    assert manifest["auth"]["demo_users"][0]["role"] == "owner"
    assert manifest["capabilities"]["search"] is True
    assert manifest["integrations"]["payments"] == "stripe"
    assert manifest["generator_boundary"]["mode"] == "family_based_generator"
    assert manifest["support_tier"] == "supported"
    assert manifest["closest_family"] == "saas_dashboard"
    assert manifest["refinement_steps"]
    assert manifest["spec_brief"]["closest_family"] == "saas_dashboard"
    assert manifest["spec_brief"]["goal"]
    assert manifest["pages"][0]["layout"] == "dashboard"
    assert manifest["workflows"][0]["owner_role"] == "owner"
    assert manifest["permissions"][0]["resource"] == "Account"
    assert manifest["layout"]["navigation_style"] == "tabs"
    assert "dashboard_core" in manifest["family_modules"]


def test_parse_manifest_applies_family_defaults_for_marketplace():
    manifest = parse_manifest(
        """
        {
          "app_name": "Seller Hub",
          "slug": "seller-hub",
          "app_type": "marketplace",
          "tagline": "Marketplace shell",
          "summary": "Marketplace shell",
          "primary_entity": "Listing",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
              "auth": {
                "enabled": true,
                "roles": ["owner"],
                "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
              },
              "capabilities": {"search": true, "notifications": true, "automation": true},
              "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
              "data_model": [{"name": "Listing", "fields": [{"name": "name", "type": "string"}, {"name": "status", "type": "string"}, {"name": "seller", "type": "string"}, {"name": "price", "type": "number"}]}],
              "api_routes": [{"path": "/listings", "method": "GET", "summary": "List listings"}],
              "sample_records": [{"name": "Acme", "status": "active", "seller": "Avery", "price": 42}]
            }
            """
        )

    assert manifest["dashboard"]["headline"] == "Marketplace activity hub"
    assert manifest["pages"][1]["name"] == "Listings"
    assert manifest["workflows"][0]["name"] == "Moderate listing"
    assert manifest["layout"]["navigation_style"] == "tabs"
    assert "marketplace_module" in manifest["family_modules"]


def test_parse_manifest_accepts_richer_dsl_fields():
    manifest = parse_manifest(
        """
        {
          "app_name": "Studio Flow",
          "slug": "studio-flow",
          "app_type": "content_platform",
          "tagline": "Editorial ops",
          "summary": "Editorial planning and publishing",
          "primary_entity": "Article",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Editorial pipeline",
            "subheadline": "Manage drafts and releases",
            "sections": [{"title": "Pipeline", "description": "Track publishing state"}]
          },
          "pages": [{"name": "Overview", "purpose": "View editorial KPIs", "layout": "dashboard", "widgets": ["summary_cards", "calendar"]}],
          "workflows": [{"name": "Publish article", "steps": ["Draft", "Review", "Publish"], "trigger": "manual", "owner_role": "editor", "states": ["draft", "review", "published"]}],
          "auth": {
            "enabled": true,
            "roles": ["editor", "writer", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "editor"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "permissions": [{"resource": "Article", "actions": ["read", "publish"], "roles": ["editor", "writer"]}],
          "layout": {"navigation_style": "sidebar", "density": "compact", "panels": ["search", "calendar", "records"]},
          "family_modules": ["editorial_calendar", "asset_pipeline"],
          "data_model": [{"name": "Article", "fields": [{"name": "title", "type": "string"}, {"name": "status", "type": "string"}, {"name": "author", "type": "string"}, {"name": "publish_date", "type": "string"}]}],
          "api_routes": [{"path": "/articles", "method": "GET", "summary": "List articles"}],
          "sample_records": [{"title": "Launch note", "status": "draft", "author": "Avery", "publish_date": "2026-04-05"}]
        }
        """
    )

    assert manifest["pages"][0]["widgets"] == ["summary_cards", "calendar"]
    assert manifest["workflows"][0]["trigger"] == "manual"
    assert manifest["workflows"][0]["owner_role"] == "editor"
    assert manifest["permissions"][0]["actions"] == ["read", "publish"]
    assert manifest["layout"]["navigation_style"] == "sidebar"
    assert manifest["family_modules"][0] == "dashboard_core"
    assert "asset_pipeline" in manifest["family_modules"]


def test_parse_manifest_expands_booking_family_entities_when_underspecified():
    manifest = parse_manifest(
        """
        {
          "app_name": "Reserve Now",
          "slug": "reserve-now",
          "app_type": "booking_platform",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
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
        """
    )

    entity_names = [entity["name"] for entity in manifest["data_model"]]
    booking_fields = {field["name"] for field in manifest["data_model"][0]["fields"]}

    assert "Resource" in entity_names
    assert "Customer" in entity_names
    assert {"start_date", "resource_id", "customer_id"}.issubset(booking_fields)
    assert [page["name"] for page in manifest["pages"]] == ["Overview", "Bookings", "Resources"]
    assert any(route["path"] == "/booking/availability" for route in manifest["api_routes"])
    assert manifest["sample_records"][0]["start_date"] == "2026-04-01"


def test_parse_manifest_expands_internal_tool_family_entities_when_underspecified():
    manifest = parse_manifest(
        """
        {
          "app_name": "Ops Desk",
          "slug": "ops-desk",
          "app_type": "internal_tool",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "auth": {
            "enabled": true,
            "roles": ["owner"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Ticket", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/tickets", "method": "GET", "summary": "List tickets"}],
          "sample_records": [{"status": "open"}]
        }
        """
    )

    entity_names = [entity["name"] for entity in manifest["data_model"]]
    ticket_fields = {field["name"] for field in manifest["data_model"][0]["fields"]}

    assert "Team" in entity_names
    assert "Incident" in entity_names
    assert {"priority", "assignee", "team_id"}.issubset(ticket_fields)
    assert [page["name"] for page in manifest["pages"]] == ["Overview", "Queue", "Approvals"]
    assert any(route["path"] == "/internal/queue" for route in manifest["api_routes"])
    assert manifest["sample_records"][0]["priority"] == "high"


def test_parse_manifest_expands_ecommerce_family_entities_when_underspecified():
    manifest = parse_manifest(
        """
        {
          "app_name": "Order Desk",
          "slug": "order-desk",
          "app_type": "ecommerce_app",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "auth": {
            "enabled": true,
            "roles": ["owner"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Order", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/orders", "method": "GET", "summary": "List orders"}],
          "sample_records": [{"status": "pending"}]
        }
        """
    )

    entity_names = [entity["name"] for entity in manifest["data_model"]]
    order_fields = {field["name"] for field in manifest["data_model"][0]["fields"]}

    assert "Product" in entity_names
    assert "Customer" in entity_names
    assert {"amount", "customer_id"}.issubset(order_fields)
    assert [page["name"] for page in manifest["pages"]] == ["Overview", "Orders", "Catalog"]
    assert any(route["path"] == "/ecommerce/orders" for route in manifest["api_routes"])
    assert manifest["sample_records"][0]["amount"] == 99


def test_parse_manifest_expands_content_family_entities_when_underspecified():
    manifest = parse_manifest(
        """
        {
          "app_name": "Editorial Hub",
          "slug": "editorial-hub",
          "app_type": "content_platform",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "auth": {
            "enabled": true,
            "roles": ["owner"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Article", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/articles", "method": "GET", "summary": "List articles"}],
          "sample_records": [{"status": "draft"}]
        }
        """
    )

    entity_names = [entity["name"] for entity in manifest["data_model"]]
    article_fields = {field["name"] for field in manifest["data_model"][0]["fields"]}

    assert "Collection" in entity_names
    assert "Asset" in entity_names
    assert {"author", "publish_date", "collection_id"}.issubset(article_fields)
    assert [page["name"] for page in manifest["pages"]] == ["Overview", "Content", "Calendar"]
    assert any(route["path"] == "/content/pipeline" for route in manifest["api_routes"])
    assert manifest["sample_records"][0]["publish_date"] == "2026-04-05"


def test_parse_manifest_expands_social_family_entities_when_underspecified():
    manifest = parse_manifest(
        """
        {
          "app_name": "Community Loop",
          "slug": "community-loop",
          "app_type": "social_app",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "auth": {
            "enabled": true,
            "roles": ["owner"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Post", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/posts", "method": "GET", "summary": "List posts"}],
          "sample_records": [{"status": "active"}]
        }
        """
    )

    entity_names = [entity["name"] for entity in manifest["data_model"]]
    post_fields = {field["name"] for field in manifest["data_model"][0]["fields"]}

    assert "Community" in entity_names
    assert "Member" in entity_names
    assert {"content", "author", "community_id"}.issubset(post_fields)
    assert [page["name"] for page in manifest["pages"]] == ["Overview", "Feed", "Moderation"]
    assert any(route["path"] == "/social/engagement" for route in manifest["api_routes"])
    assert manifest["sample_records"][1]["status"] == "flagged"


def test_parse_manifest_expands_learning_family_entities_when_underspecified():
    manifest = parse_manifest(
        """
        {
          "app_name": "Skill Path",
          "slug": "skill-path",
          "app_type": "learning_platform",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "auth": {
            "enabled": true,
            "roles": ["owner"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Course", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/courses", "method": "GET", "summary": "List courses"}],
          "sample_records": [{"status": "active"}]
        }
        """
    )

    entity_names = [entity["name"] for entity in manifest["data_model"]]
    course_fields = {field["name"] for field in manifest["data_model"][0]["fields"]}

    assert "Lesson" in entity_names
    assert "Learner" in entity_names
    assert {"progress", "lesson_id", "learner_id"}.issubset(course_fields)
    assert [page["name"] for page in manifest["pages"]] == ["Overview", "Courses", "Progress"]
    assert any(route["path"] == "/learning/progress" for route in manifest["api_routes"])
    assert manifest["sample_records"][0]["progress"] == 72


def test_parse_manifest_expands_marketplace_family_entities_when_underspecified():
    manifest = parse_manifest(
        """
        {
          "app_name": "Seller Hub",
          "slug": "seller-hub",
          "app_type": "marketplace",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "auth": {
            "enabled": true,
            "roles": ["owner"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Listing", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/listings", "method": "GET", "summary": "List listings"}],
          "sample_records": [{"status": "active"}]
        }
        """
    )

    entity_names = [entity["name"] for entity in manifest["data_model"]]
    listing_fields = {field["name"] for field in manifest["data_model"][0]["fields"]}

    assert "Seller" in entity_names
    assert "Buyer" in entity_names
    assert {"seller", "price"}.issubset(listing_fields)
    assert [page["name"] for page in manifest["pages"]] == ["Overview", "Listings", "Sellers"]
    assert any(route["path"] == "/marketplace/activity" for route in manifest["api_routes"])
    assert manifest["sample_records"][0]["seller"] == "Avery"


def test_render_family_prompt_guide_lists_marketplace_guidance():
    guide = render_family_prompt_guide()

    assert "marketplace (Marketplace)" in guide
    assert "buyers, sellers, moderation" in guide


def test_render_product_boundary_guide_lists_supported_and_unsupported_scope():
    guide = render_product_boundary_guide()

    assert "Mode: family_based_generator" in guide
    assert "Supported:" in guide
    assert "Starter-only:" in guide
    assert "Unsupported:" in guide


def test_parse_manifest_rejects_invalid_theme():
    with pytest.raises(GeneratedProjectError, match="primary_color"):
        parse_manifest(
            """
            {
              "app_name": "Bad Theme",
              "slug": "bad-theme",
              "app_type": "saas_dashboard",
              "tagline": "x",
              "summary": "y",
              "primary_entity": "Thing",
              "theme": {
                "primary_color": "teal",
                "accent_color": "#f59e0b",
                "surface_color": "#ecfeff"
              },
              "dashboard": {
                "headline": "Head",
                "subheadline": "Sub",
                "sections": [{"title": "One", "description": "Desc"}]
              },
              "pages": [{"name": "Home", "purpose": "Landing"}],
              "workflows": [{"name": "Route work", "steps": ["Create", "Route"]}],
              "auth": {
                "enabled": true,
                "roles": ["owner"],
                "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
              },
              "capabilities": {"search": true, "notifications": true, "automation": true},
              "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
              "data_model": [{"name": "Thing", "fields": [{"name": "name", "type": "string"}]}],
              "api_routes": [{"path": "/things", "method": "GET", "summary": "List things"}],
              "sample_records": [{"title": "Sample", "status": "active"}]
            }
            """
        )


def test_parse_manifest_rejects_unknown_app_type():
    with pytest.raises(GeneratedProjectError, match="app_type"):
        parse_manifest(
            """
            {
              "app_name": "Bad Type",
              "slug": "bad-type",
              "app_type": "robot_brain",
              "tagline": "x",
              "summary": "y",
              "primary_entity": "Thing",
              "theme": {
                "primary_color": "#0f766e",
                "accent_color": "#f59e0b",
                "surface_color": "#ecfeff"
              },
              "dashboard": {
                "headline": "Head",
                "subheadline": "Sub",
                "sections": [{"title": "One", "description": "Desc"}]
              },
              "pages": [{"name": "Home", "purpose": "Landing"}],
              "workflows": [{"name": "Route work", "steps": ["Create", "Route"]}],
              "auth": {
                "enabled": true,
                "roles": ["owner"],
                "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
              },
              "capabilities": {"search": true, "notifications": true, "automation": true},
              "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
              "data_model": [{"name": "Thing", "fields": [{"name": "name", "type": "string"}]}],
              "api_routes": [{"path": "/things", "method": "GET", "summary": "List things"}],
              "sample_records": [{"title": "Sample", "status": "active"}]
            }
            """
        )


def test_parse_manifest_rejects_demo_user_role_not_in_roles():
    with pytest.raises(GeneratedProjectError, match="demo_user role"):
        parse_manifest(
            """
            {
              "app_name": "Bad Auth",
              "slug": "bad-auth",
              "app_type": "saas_dashboard",
              "tagline": "x",
              "summary": "y",
              "primary_entity": "Thing",
              "theme": {
                "primary_color": "#0f766e",
                "accent_color": "#f59e0b",
                "surface_color": "#ecfeff"
              },
              "dashboard": {
                "headline": "Head",
                "subheadline": "Sub",
                "sections": [{"title": "One", "description": "Desc"}]
              },
              "pages": [{"name": "Home", "purpose": "Landing"}],
              "workflows": [{"name": "Route work", "steps": ["Create", "Route"]}],
              "auth": {
                "enabled": true,
                "roles": ["viewer"],
                "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
              },
              "capabilities": {"search": true, "notifications": true, "automation": true},
              "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
              "data_model": [{"name": "Thing", "fields": [{"name": "name", "type": "string"}]}],
              "api_routes": [{"path": "/things", "method": "GET", "summary": "List things"}],
              "sample_records": [{"title": "Sample", "status": "active"}]
            }
            """
        )
