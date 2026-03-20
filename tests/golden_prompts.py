GOLDEN_PROMPTS = [
    {
        "name": "saas_analytics",
        "prompt": "Build a SaaS analytics dashboard for B2B revenue teams.",
        "expected": {
            "app_type": "saas_dashboard",
            "primary_entity": "Account",
            "page_names": ["Overview"],
            "route_path": "/accounts",
            "family_module": "dashboard_core",
        },
        "manifest_output": """
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
        """,
    },
    {
        "name": "crm",
        "prompt": "Build a CRM for account executives to manage leads, accounts, and deals.",
        "expected": {
            "app_type": "crm_platform",
            "primary_entity": "Deal",
            "page_names": ["Overview", "Deals", "Accounts"],
            "route_path": "/crm/pipeline",
            "family_module": "crm_platform_module",
        },
        "manifest_output": """
        {
          "app_name": "Pipeline Hub",
          "slug": "pipeline-hub",
          "app_type": "crm_platform",
          "tagline": "Run the pipeline",
          "summary": "CRM for account and deal management",
          "primary_entity": "Deal",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Sales pipeline command center",
            "subheadline": "Track deals and account health",
            "sections": [{"title": "Pipeline", "description": "Review active opportunities"}]
          },
          "pages": [{"name": "Overview", "purpose": "See pipeline health"}],
          "workflows": [{"name": "Advance deal", "steps": ["Qualify", "Propose", "Close"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "manager", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Deal", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/deals", "method": "GET", "summary": "List deals"}],
          "sample_records": [{"status": "qualified"}]
        }
        """,
    },
    {
        "name": "support",
        "prompt": "Build a support desk for customer issue triage and escalations.",
        "expected": {
            "app_type": "support_desk",
            "primary_entity": "Ticket",
            "page_names": ["Overview", "Tickets", "Escalations"],
            "route_path": "/support/queue",
            "family_module": "support_desk_module",
        },
        "manifest_output": """
        {
          "app_name": "Support Radar",
          "slug": "support-radar",
          "app_type": "support_desk",
          "tagline": "Handle support issues",
          "summary": "Support desk for tickets and escalations",
          "primary_entity": "Ticket",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Support queue control center",
            "subheadline": "Track tickets and SLA risk",
            "sections": [{"title": "Queue", "description": "Review urgent issues"}]
          },
          "pages": [{"name": "Overview", "purpose": "Track ticket health"}],
          "workflows": [{"name": "Resolve ticket", "steps": ["Intake", "Respond", "Resolve"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "agent", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Ticket", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/tickets", "method": "GET", "summary": "List tickets"}],
          "sample_records": [{"status": "open"}]
        }
        """,
    },
    {
        "name": "project_management",
        "prompt": "Build a project management app for milestones, tasks, and delivery tracking.",
        "expected": {
            "app_type": "project_management",
            "primary_entity": "Project",
            "page_names": ["Overview", "Projects", "Milestones"],
            "route_path": "/project-management/board",
            "family_module": "project_management_module",
        },
        "manifest_output": """
        {
          "app_name": "Milestone Flow",
          "slug": "milestone-flow",
          "app_type": "project_management",
          "tagline": "Run delivery plans",
          "summary": "Project management for milestones and delivery",
          "primary_entity": "Project",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Project delivery overview",
            "subheadline": "Track milestones and task progress",
            "sections": [{"title": "Projects", "description": "Review delivery posture"}]
          },
          "pages": [{"name": "Overview", "purpose": "See delivery health"}],
          "workflows": [{"name": "Ship milestone", "steps": ["Plan", "Execute", "Complete"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "manager", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Project", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/projects", "method": "GET", "summary": "List projects"}],
          "sample_records": [{"status": "active"}]
        }
        """,
    },
    {
        "name": "recruiting",
        "prompt": "Build a recruiting platform for hiring teams to manage candidates and interviews.",
        "expected": {
            "app_type": "recruiting_platform",
            "primary_entity": "Candidate",
            "page_names": ["Overview", "Candidates", "Interviews"],
            "route_path": "/recruiting/pipeline",
            "family_module": "recruiting_platform_module",
        },
        "manifest_output": """
        {
          "app_name": "Hiring Loop",
          "slug": "hiring-loop",
          "app_type": "recruiting_platform",
          "tagline": "Run the hiring process",
          "summary": "Recruiting workflow for candidates and interviews",
          "primary_entity": "Candidate",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Hiring pipeline overview",
            "subheadline": "Track candidates and interview load",
            "sections": [{"title": "Pipeline", "description": "Review active candidates"}]
          },
          "pages": [{"name": "Overview", "purpose": "See hiring health"}],
          "workflows": [{"name": "Advance candidate", "steps": ["Screen", "Interview", "Offer"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "recruiter", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Candidate", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/candidates", "method": "GET", "summary": "List candidates"}],
          "sample_records": [{"status": "screen"}]
        }
        """,
    },
    {
        "name": "inventory",
        "prompt": "Build an inventory management app for warehouse teams to monitor stock and reorders.",
        "expected": {
            "app_type": "inventory_management",
            "primary_entity": "Item",
            "page_names": ["Overview", "Inventory", "Reorders"],
            "route_path": "/inventory/stock",
            "family_module": "inventory_management_module",
        },
        "manifest_output": """
        {
          "app_name": "Stock Signal",
          "slug": "stock-signal",
          "app_type": "inventory_management",
          "tagline": "Control stock flow",
          "summary": "Inventory operations for stock and suppliers",
          "primary_entity": "Item",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Inventory control center",
            "subheadline": "Track low-stock items and suppliers",
            "sections": [{"title": "Stock", "description": "Review inventory health"}]
          },
          "pages": [{"name": "Overview", "purpose": "See stock posture"}],
          "workflows": [{"name": "Reorder stock", "steps": ["Detect", "Request", "Receive"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "manager", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Item", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/items", "method": "GET", "summary": "List items"}],
          "sample_records": [{"status": "in_stock"}]
        }
        """,
    },
    {
        "name": "finance",
        "prompt": "Build a finance ops app for invoice approvals and cashflow tracking.",
        "expected": {
            "app_type": "finance_ops",
            "primary_entity": "Invoice",
            "page_names": ["Overview", "Invoices", "Approvals"],
            "route_path": "/finance/cashflow",
            "family_module": "finance_ops_module",
        },
        "manifest_output": """
        {
          "app_name": "Cashflow Desk",
          "slug": "cashflow-desk",
          "app_type": "finance_ops",
          "tagline": "Run finance approvals",
          "summary": "Finance operations for invoices and approvals",
          "primary_entity": "Invoice",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Finance operations overview",
            "subheadline": "Track invoices and cashflow posture",
            "sections": [{"title": "Invoices", "description": "Review pending approvals"}]
          },
          "pages": [{"name": "Overview", "purpose": "See finance health"}],
          "workflows": [{"name": "Approve invoice", "steps": ["Review", "Approve", "Pay"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "manager", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Invoice", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/invoices", "method": "GET", "summary": "List invoices"}],
          "sample_records": [{"status": "pending"}]
        }
        """,
    },
    {
        "name": "internal_ops",
        "prompt": "Build an internal operations tool for handling escalations and approvals.",
        "expected": {
            "app_type": "internal_tool",
            "primary_entity": "Ticket",
            "page_names": ["Overview", "Queue", "Approvals"],
            "route_path": "/internal/queue",
            "family_module": "internal_tool_module",
        },
        "manifest_output": """
        {
          "app_name": "Ops Desk",
          "slug": "ops-desk",
          "app_type": "internal_tool",
          "tagline": "Handle internal ops",
          "summary": "Operational work routing for internal teams",
          "primary_entity": "Ticket",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Operations control center",
            "subheadline": "Route and resolve internal work",
            "sections": [{"title": "Queue", "description": "Review active tickets"}]
          },
          "pages": [{"name": "Overview", "purpose": "Track queue health"}],
          "workflows": [{"name": "Route ticket", "steps": ["Capture", "Assign", "Resolve"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "manager", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Ticket", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/tickets", "method": "GET", "summary": "List tickets"}],
          "sample_records": [{"status": "open"}]
        }
        """,
    },
    {
        "name": "marketplace",
        "prompt": "Build a marketplace for creators to sell digital packs.",
        "expected": {
            "app_type": "marketplace",
            "primary_entity": "Listing",
            "page_names": ["Overview", "Listings", "Sellers"],
            "route_path": "/marketplace/activity",
            "family_module": "marketplace_module",
        },
        "manifest_output": """
        {
          "app_name": "Creator Market",
          "slug": "creator-market",
          "app_type": "marketplace",
          "tagline": "Sell creator packs",
          "summary": "Marketplace for digital creator assets",
          "primary_entity": "Listing",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Marketplace activity hub",
            "subheadline": "Track listings and seller momentum",
            "sections": [{"title": "Listings", "description": "Review active inventory"}]
          },
          "pages": [{"name": "Overview", "purpose": "Track marketplace health"}],
          "workflows": [{"name": "Moderate listing", "steps": ["Submit", "Review", "Approve"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "manager", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Listing", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/listings", "method": "GET", "summary": "List listings"}],
          "sample_records": [{"status": "active"}]
        }
        """,
    },
    {
        "name": "booking",
        "prompt": "Build a booking platform for wellness studios.",
        "expected": {
            "app_type": "booking_platform",
            "primary_entity": "Booking",
            "page_names": ["Overview", "Bookings", "Resources"],
            "route_path": "/booking/availability",
            "family_module": "booking_platform_module",
        },
        "manifest_output": """
        {
          "app_name": "Studio Reserve",
          "slug": "studio-reserve",
          "app_type": "booking_platform",
          "tagline": "Book studio sessions",
          "summary": "Scheduling for wellness studios",
          "primary_entity": "Booking",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Availability and bookings",
            "subheadline": "Manage resources and reservations",
            "sections": [{"title": "Availability", "description": "Review open time slots"}]
          },
          "pages": [{"name": "Overview", "purpose": "Track availability"}],
          "workflows": [{"name": "Confirm reservation", "steps": ["Request", "Confirm", "Notify"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "manager", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Booking", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/bookings", "method": "GET", "summary": "List bookings"}],
          "sample_records": [{"status": "scheduled"}]
        }
        """,
    },
    {
        "name": "content",
        "prompt": "Build a content publishing platform for an editorial team.",
        "expected": {
            "app_type": "content_platform",
            "primary_entity": "Article",
            "page_names": ["Overview", "Content", "Calendar"],
            "route_path": "/content/pipeline",
            "family_module": "content_platform_module",
        },
        "manifest_output": """
        {
          "app_name": "Editorial Hub",
          "slug": "editorial-hub",
          "app_type": "content_platform",
          "tagline": "Run editorial ops",
          "summary": "Editorial workflow and scheduling",
          "primary_entity": "Article",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Publishing command center",
            "subheadline": "Track drafts and release schedule",
            "sections": [{"title": "Pipeline", "description": "Review publishing state"}]
          },
          "pages": [{"name": "Overview", "purpose": "View publishing status"}],
          "workflows": [{"name": "Publish content", "steps": ["Draft", "Review", "Publish"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "editor", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Article", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/articles", "method": "GET", "summary": "List articles"}],
          "sample_records": [{"status": "draft"}]
        }
        """,
    },
    {
        "name": "social",
        "prompt": "Build a social app for private communities and post moderation.",
        "expected": {
            "app_type": "social_app",
            "primary_entity": "Post",
            "page_names": ["Overview", "Feed", "Moderation"],
            "route_path": "/social/engagement",
            "family_module": "social_app_module",
        },
        "manifest_output": """
        {
          "app_name": "Community Loop",
          "slug": "community-loop",
          "app_type": "social_app",
          "tagline": "Run community spaces",
          "summary": "Community engagement and moderation",
          "primary_entity": "Post",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Community activity overview",
            "subheadline": "Track members and moderation",
            "sections": [{"title": "Communities", "description": "Review audience participation"}]
          },
          "pages": [{"name": "Overview", "purpose": "Track community health"}],
          "workflows": [{"name": "Moderate post", "steps": ["Detect", "Review", "Resolve"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "moderator", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Post", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/posts", "method": "GET", "summary": "List posts"}],
          "sample_records": [{"status": "active"}]
        }
        """,
    },
    {
        "name": "learning",
        "prompt": "Build a learning platform for onboarding and course progress.",
        "expected": {
            "app_type": "learning_platform",
            "primary_entity": "Course",
            "page_names": ["Overview", "Courses", "Progress"],
            "route_path": "/learning/progress",
            "family_module": "learning_platform_module",
        },
        "manifest_output": """
        {
          "app_name": "Skill Path",
          "slug": "skill-path",
          "app_type": "learning_platform",
          "tagline": "Guide learning paths",
          "summary": "Courses, lessons, and learner progress",
          "primary_entity": "Course",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Learning operations overview",
            "subheadline": "Track courses and progress",
            "sections": [{"title": "Courses", "description": "Review active programs"}]
          },
          "pages": [{"name": "Overview", "purpose": "See progress across courses"}],
          "workflows": [{"name": "Publish course", "steps": ["Draft", "Review", "Launch"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "instructor", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Course", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/courses", "method": "GET", "summary": "List courses"}],
          "sample_records": [{"status": "active"}]
        }
        """,
    },
    {
        "name": "ecommerce",
        "prompt": "Build an ecommerce app for order fulfillment and catalog management.",
        "expected": {
            "app_type": "ecommerce_app",
            "primary_entity": "Order",
            "page_names": ["Overview", "Orders", "Catalog"],
            "route_path": "/ecommerce/orders",
            "family_module": "ecommerce_app_module",
        },
        "manifest_output": """
        {
          "app_name": "Order Desk",
          "slug": "order-desk",
          "app_type": "ecommerce_app",
          "tagline": "Manage fulfillment",
          "summary": "Orders, catalog, and shipment flow",
          "primary_entity": "Order",
          "theme": {
            "primary_color": "#0f766e",
            "accent_color": "#f59e0b",
            "surface_color": "#ecfeff"
          },
          "dashboard": {
            "headline": "Commerce and fulfillment overview",
            "subheadline": "Track orders and catalog movement",
            "sections": [{"title": "Orders", "description": "Review fulfillment state"}]
          },
          "pages": [{"name": "Overview", "purpose": "See order health"}],
          "workflows": [{"name": "Fulfill order", "steps": ["Receive", "Pack", "Ship"]}],
          "auth": {
            "enabled": true,
            "roles": ["owner", "manager", "viewer"],
            "demo_users": [{"name": "Avery", "email": "avery@example.com", "role": "owner"}]
          },
          "capabilities": {"search": true, "notifications": true, "automation": true},
          "integrations": {"email": "sendgrid", "payments": "stripe", "storage": "s3", "webhook_topics": ["record.created"]},
          "data_model": [{"name": "Order", "fields": [{"name": "status", "type": "string"}]}],
          "api_routes": [{"path": "/orders", "method": "GET", "summary": "List orders"}],
          "sample_records": [{"status": "pending"}]
        }
        """,
    },
]
