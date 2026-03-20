from copy import deepcopy
import re


APP_TYPE_LABELS = {
    "saas_dashboard": "SaaS Dashboard",
    "crm_platform": "CRM Platform",
    "support_desk": "Support Desk",
    "project_management": "Project Management",
    "recruiting_platform": "Recruiting Platform",
    "inventory_management": "Inventory Management",
    "finance_ops": "Finance Ops",
    "internal_tool": "Internal Tool",
    "marketplace": "Marketplace",
    "booking_platform": "Booking Platform",
    "content_platform": "Content Platform",
    "social_app": "Social App",
    "learning_platform": "Learning Platform",
    "ecommerce_app": "Ecommerce App",
}


PRODUCT_BOUNDARY = {
    "mode": "family_based_generator",
    "supported": [
        "dashboard and CRUD-heavy business apps",
        "workflow-driven internal tools",
        "family-based SaaS starters with auth, entities, integrations, and deployment scaffolds",
    ],
    "starter_only": [
        "consumer apps with custom interaction models",
        "apps requiring deep domain-specific logic beyond scaffold families",
        "products that need bespoke multi-service architectures",
    ],
    "unsupported": [
        "claims of fully custom production systems from one vague prompt",
        "arbitrary infra-heavy, realtime-heavy, or algorithm-heavy products with no narrowing",
    ],
}


FAMILY_SPECS = {
    "saas_dashboard": {
        "prompt_guidance": "Use recurring metrics, account health, team workflows, and operational dashboards.",
        "manifest_defaults": {},
        "schema_requirements": {},
    },
    "crm_platform": {
        "prompt_guidance": "Bias toward leads, accounts, deals, pipeline stages, revenue forecasting, and sales follow-up.",
        "manifest_defaults": {
            "tagline": "A CRM for pipeline and account management",
            "summary": "A CRM starter focused on leads, deals, account relationships, and forecast visibility.",
            "primary_entity": "Deal",
            "dashboard": {
                "headline": "Sales pipeline command center",
                "subheadline": "Track deals, account health, and forecast movement.",
                "sections": [
                    {"title": "Pipeline", "description": "Monitor active opportunities and stage movement."},
                    {"title": "Accounts", "description": "Review customers, ownership, and engagement health."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "See forecast and pipeline health."},
                {"name": "Deals", "purpose": "Manage opportunities and stage movement."},
            ],
            "workflows": [{"name": "Advance deal", "steps": ["Qualify", "Propose", "Close"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "stage"),
                ("amount", "value", "price"),
                ("customer", "account", "owner", "lead"),
            ),
        },
    },
    "support_desk": {
        "prompt_guidance": "Bias toward tickets, customers, SLAs, queues, agents, escalations, and response workflows.",
        "manifest_defaults": {
            "tagline": "A support desk for customer operations",
            "summary": "A support starter focused on ticket queues, SLAs, customer issues, and escalations.",
            "primary_entity": "Ticket",
            "dashboard": {
                "headline": "Support queue control center",
                "subheadline": "Track ticket volume, escalations, and response posture.",
                "sections": [
                    {"title": "Queue", "description": "Monitor open, pending, and escalated tickets."},
                    {"title": "Customers", "description": "Review affected accounts and communication health."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "Track support queue health."},
                {"name": "Tickets", "purpose": "Manage support tickets and escalations."},
            ],
            "workflows": [{"name": "Resolve ticket", "steps": ["Intake", "Respond", "Resolve"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "state"),
                ("priority", "severity", "sla"),
                ("customer", "requester", "assignee", "agent"),
            ),
        },
    },
    "project_management": {
        "prompt_guidance": "Bias toward projects, tasks, milestones, owners, delivery status, and planning cadence.",
        "manifest_defaults": {
            "tagline": "A project management workspace",
            "summary": "A project planning starter focused on milestones, tasks, owners, and delivery status.",
            "primary_entity": "Project",
            "dashboard": {
                "headline": "Project delivery overview",
                "subheadline": "Track milestones, task flow, and delivery risks.",
                "sections": [
                    {"title": "Projects", "description": "Review active projects and milestone posture."},
                    {"title": "Tasks", "description": "Monitor work items, owners, and progress."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "See project health and delivery posture."},
                {"name": "Projects", "purpose": "Manage projects, milestones, and priorities."},
            ],
            "workflows": [{"name": "Ship milestone", "steps": ["Plan", "Execute", "Complete"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "state"),
                ("owner", "assignee", "manager"),
                ("milestone", "due_date", "progress", "task"),
            ),
        },
    },
    "recruiting_platform": {
        "prompt_guidance": "Bias toward candidates, jobs, interview stages, recruiters, and hiring pipeline movement.",
        "manifest_defaults": {
            "tagline": "A recruiting platform for hiring teams",
            "summary": "A recruiting starter focused on candidates, interview scheduling, and stage progression.",
            "primary_entity": "Candidate",
            "dashboard": {
                "headline": "Hiring pipeline overview",
                "subheadline": "Track candidates, interview load, and stage movement.",
                "sections": [
                    {"title": "Pipeline", "description": "Review active candidates and hiring stages."},
                    {"title": "Interviews", "description": "Track upcoming loops and recruiter coordination."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "See hiring health and stage distribution."},
                {"name": "Candidates", "purpose": "Manage candidate records and hiring stages."},
            ],
            "workflows": [{"name": "Advance candidate", "steps": ["Screen", "Interview", "Offer"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "stage"),
                ("candidate", "applicant", "name"),
                ("recruiter", "owner", "job", "role"),
            ),
        },
    },
    "inventory_management": {
        "prompt_guidance": "Bias toward inventory items, stock levels, suppliers, reorder triggers, and warehouse visibility.",
        "manifest_defaults": {
            "tagline": "An inventory workspace for stock operations",
            "summary": "An inventory starter focused on stock monitoring, reorders, and supplier coordination.",
            "primary_entity": "Item",
            "dashboard": {
                "headline": "Inventory control center",
                "subheadline": "Track stock posture, supplier risk, and reorder demand.",
                "sections": [
                    {"title": "Stock", "description": "Review on-hand inventory and low-stock items."},
                    {"title": "Suppliers", "description": "Monitor supplier response and replenishment flow."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "See inventory health and stock risk."},
                {"name": "Inventory", "purpose": "Manage items and stock levels."},
            ],
            "workflows": [{"name": "Reorder stock", "steps": ["Detect", "Request", "Receive"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "state"),
                ("stock", "stock_level", "quantity"),
                ("supplier", "supplier_id", "sku", "warehouse"),
            ),
        },
    },
    "finance_ops": {
        "prompt_guidance": "Bias toward invoices, approvals, due dates, cashflow visibility, and finance operations workflows.",
        "manifest_defaults": {
            "tagline": "A finance operations workspace",
            "summary": "A finance ops starter focused on invoices, approvals, and cashflow visibility.",
            "primary_entity": "Invoice",
            "dashboard": {
                "headline": "Finance operations overview",
                "subheadline": "Track invoices, approvals, and cashflow posture.",
                "sections": [
                    {"title": "Invoices", "description": "Review pending and approved invoices."},
                    {"title": "Cashflow", "description": "Monitor due amounts and approval throughput."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "See cashflow and approvals health."},
                {"name": "Invoices", "purpose": "Manage invoices and billing operations."},
            ],
            "workflows": [{"name": "Approve invoice", "steps": ["Review", "Approve", "Pay"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "state"),
                ("amount", "value", "total"),
                ("customer", "vendor", "due_date", "invoice"),
            ),
        },
    },
    "internal_tool": {
        "prompt_guidance": "Bias toward queues, operators, approvals, incidents, and internal team workflows.",
        "manifest_defaults": {
            "tagline": "An internal operations workspace",
            "summary": "An internal tool for teams to manage operational work and approvals.",
            "primary_entity": "Ticket",
            "dashboard": {
                "headline": "Operations control center",
                "subheadline": "Route, resolve, and review internal work.",
                "sections": [
                    {"title": "Queue", "description": "Monitor incoming operational requests and their urgency."},
                    {"title": "Teams", "description": "Track ownership, handoffs, and team workload."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "Track operational health and queues."},
                {"name": "Queue", "purpose": "Triage and manage active tickets."},
            ],
            "workflows": [{"name": "Route ticket", "steps": ["Capture", "Assign", "Resolve"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "priority"),
                ("owner", "assignee", "operator"),
            ),
        },
    },
    "marketplace": {
        "prompt_guidance": "Bias toward listings, buyers, sellers, moderation, inventory/value, and transaction lifecycle.",
        "manifest_defaults": {
            "tagline": "A marketplace for buyers and sellers",
            "summary": "A marketplace starter focused on listings, seller activity, and moderation flow.",
            "primary_entity": "Listing",
            "dashboard": {
                "headline": "Marketplace activity hub",
                "subheadline": "Track listings, seller momentum, and moderation queue.",
                "sections": [
                    {"title": "Listings", "description": "Review active and pending marketplace inventory."},
                    {"title": "Sellers", "description": "Monitor seller participation and transaction flow."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "See marketplace activity and health."},
                {"name": "Listings", "purpose": "Browse and manage listings."},
            ],
            "workflows": [{"name": "Moderate listing", "steps": ["Submit", "Review", "Approve"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "state"),
                ("seller", "owner", "provider"),
                ("price", "amount", "value"),
            ),
        },
    },
    "booking_platform": {
        "prompt_guidance": "Bias toward bookings, resources, calendars, guest/customer communication, and time slots.",
        "manifest_defaults": {
            "tagline": "A booking platform for scheduling resources",
            "summary": "A booking app starter focused on availability, reservations, and guest communication.",
            "primary_entity": "Booking",
            "dashboard": {
                "headline": "Availability and bookings",
                "subheadline": "Manage resources, reservations, and guest follow-up.",
                "sections": [
                    {"title": "Availability", "description": "Review open and reserved time slots."},
                    {"title": "Guests", "description": "Keep track of guests and confirmations."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "See availability and upcoming reservations."},
                {"name": "Bookings", "purpose": "Manage bookings and assigned resources."},
            ],
            "workflows": [{"name": "Confirm reservation", "steps": ["Request", "Confirm", "Notify"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "state"),
                ("start_date", "start_time", "date"),
                ("resource", "resource_name", "resource_id", "provider", "staff", "room"),
            ),
        },
    },
    "content_platform": {
        "prompt_guidance": "Bias toward authors, publishing pipeline, collections, scheduling, and asset management.",
        "manifest_defaults": {
            "tagline": "A platform for publishing and managing content",
            "summary": "A content platform starter for editorial workflows and publishing operations.",
            "primary_entity": "Article",
            "dashboard": {
                "headline": "Publishing command center",
                "subheadline": "Track drafts, schedules, and content performance.",
                "sections": [
                    {"title": "Pipeline", "description": "Track drafts, reviews, and published content."},
                    {"title": "Collections", "description": "Manage series, categories, and assets."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "View publishing status and schedules."},
                {"name": "Content", "purpose": "Manage articles and assets."},
            ],
            "workflows": [{"name": "Publish content", "steps": ["Draft", "Review", "Publish"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "state"),
                ("title", "headline", "name"),
                ("author", "owner", "publish_date", "scheduled_for"),
            ),
        },
    },
    "social_app": {
        "prompt_guidance": "Bias toward communities, members, posts, moderation, and engagement loops.",
        "manifest_defaults": {
            "tagline": "A community-driven social application",
            "summary": "A social app starter for communities, posts, and member engagement.",
            "primary_entity": "Post",
            "dashboard": {
                "headline": "Community activity overview",
                "subheadline": "Track members, posts, and moderation activity.",
                "sections": [
                    {"title": "Communities", "description": "Review groups and audience participation."},
                    {"title": "Moderation", "description": "Manage flagged content and community safety."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "Track community health and participation."},
                {"name": "Feed", "purpose": "Browse and manage posts."},
            ],
            "workflows": [{"name": "Moderate post", "steps": ["Detect", "Review", "Resolve"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "state"),
                ("title", "content", "body"),
                ("author", "member", "user"),
            ),
        },
    },
    "learning_platform": {
        "prompt_guidance": "Bias toward courses, lessons, learners, progress tracking, and publishing learning content.",
        "manifest_defaults": {
            "tagline": "A platform for structured learning",
            "summary": "A learning platform starter focused on courses, lessons, and learner progress.",
            "primary_entity": "Course",
            "dashboard": {
                "headline": "Learning operations overview",
                "subheadline": "Track courses, lessons, and learner progress.",
                "sections": [
                    {"title": "Courses", "description": "Review active courses and lesson readiness."},
                    {"title": "Learners", "description": "Track enrollment and completion progress."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "See course performance and learner progress."},
                {"name": "Courses", "purpose": "Manage courses and lessons."},
            ],
            "workflows": [{"name": "Publish course", "steps": ["Draft", "Review", "Launch"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "state"),
                ("title", "name"),
                ("progress", "lesson", "course", "module"),
            ),
        },
    },
    "ecommerce_app": {
        "prompt_guidance": "Bias toward catalog, orders, fulfillment, customers, inventory, and post-purchase flow.",
        "manifest_defaults": {
            "tagline": "An ecommerce operations workspace",
            "summary": "An ecommerce starter focused on catalog, orders, and fulfillment flow.",
            "primary_entity": "Order",
            "dashboard": {
                "headline": "Commerce and fulfillment overview",
                "subheadline": "Track orders, catalog movement, and shipment progress.",
                "sections": [
                    {"title": "Orders", "description": "Review incoming orders and their fulfillment status."},
                    {"title": "Catalog", "description": "Monitor products, pricing, and inventory posture."},
                ],
            },
            "pages": [
                {"name": "Overview", "purpose": "See order and fulfillment health."},
                {"name": "Orders", "purpose": "Manage orders and shipment state."},
            ],
            "workflows": [{"name": "Fulfill order", "steps": ["Receive", "Pack", "Ship"]}],
        },
        "schema_requirements": {
            "required_field_groups": (
                ("status", "state"),
                ("amount", "price", "value"),
                ("customer", "customer_id", "buyer", "email"),
            ),
        },
    },
}


FAMILY_ENTITY_PLANS = {
    "crm_platform": {
        "primary_fields": [
            {"name": "title", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "amount", "type": "number"},
            {"name": "account_id", "type": "number"},
            {"name": "owner", "type": "string"},
        ],
        "related_entities": [
            {
                "name": "Account",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "segment", "type": "string"},
                ],
            },
            {
                "name": "Lead",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "email", "type": "string"},
                ],
            },
        ],
    },
    "support_desk": {
        "primary_fields": [
            {"name": "title", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "priority", "type": "string"},
            {"name": "customer_id", "type": "number"},
            {"name": "assignee", "type": "string"},
        ],
        "related_entities": [
            {
                "name": "Customer",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "email", "type": "string"},
                ],
            },
            {
                "name": "SLA",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "target_hours", "type": "number"},
                ],
            },
        ],
    },
    "project_management": {
        "primary_fields": [
            {"name": "title", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "owner", "type": "string"},
            {"name": "progress", "type": "number"},
            {"name": "milestone_id", "type": "number"},
        ],
        "related_entities": [
            {
                "name": "Task",
                "fields": [
                    {"name": "title", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "assignee", "type": "string"},
                ],
            },
            {
                "name": "Milestone",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "due_date", "type": "string"},
                ],
            },
        ],
    },
    "recruiting_platform": {
        "primary_fields": [
            {"name": "name", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "job_id", "type": "number"},
            {"name": "recruiter", "type": "string"},
            {"name": "score", "type": "number"},
        ],
        "related_entities": [
            {
                "name": "Job",
                "fields": [
                    {"name": "title", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "department", "type": "string"},
                ],
            },
            {
                "name": "Interview",
                "fields": [
                    {"name": "title", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "scheduled_for", "type": "string"},
                ],
            },
        ],
    },
    "inventory_management": {
        "primary_fields": [
            {"name": "title", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "sku", "type": "string"},
            {"name": "stock_level", "type": "number"},
            {"name": "supplier_id", "type": "number"},
        ],
        "related_entities": [
            {
                "name": "Supplier",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "lead_time_days", "type": "number"},
                ],
            },
            {
                "name": "Warehouse",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "capacity", "type": "number"},
                ],
            },
        ],
    },
    "finance_ops": {
        "primary_fields": [
            {"name": "title", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "amount", "type": "number"},
            {"name": "customer_id", "type": "number"},
            {"name": "due_date", "type": "string"},
        ],
        "related_entities": [
            {
                "name": "Customer",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "email", "type": "string"},
                ],
            },
            {
                "name": "Budget",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "allocated_amount", "type": "number"},
                ],
            },
        ],
    },
    "internal_tool": {
        "primary_fields": [
            {"name": "title", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "priority", "type": "string"},
            {"name": "assignee", "type": "string"},
            {"name": "team_id", "type": "number"},
        ],
        "related_entities": [
            {
                "name": "Team",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "owner", "type": "string"},
                ],
            },
            {
                "name": "Incident",
                "fields": [
                    {"name": "title", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "severity", "type": "string"},
                ],
            },
        ],
    },
    "marketplace": {
        "primary_fields": [
            {"name": "title", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "seller", "type": "string"},
            {"name": "price", "type": "number"},
        ],
        "related_entities": [
            {
                "name": "Seller",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "rating", "type": "number"},
                ],
            },
            {
                "name": "Buyer",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "email", "type": "string"},
                ],
            },
        ],
    },
    "booking_platform": {
        "primary_fields": [
            {"name": "title", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "start_date", "type": "string"},
            {"name": "resource_id", "type": "number"},
            {"name": "customer_id", "type": "number"},
        ],
        "related_entities": [
            {
                "name": "Resource",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "capacity", "type": "number"},
                ],
            },
            {
                "name": "Customer",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "email", "type": "string"},
                ],
            },
        ],
    },
    "content_platform": {
        "primary_fields": [
            {"name": "title", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "author", "type": "string"},
            {"name": "publish_date", "type": "string"},
            {"name": "collection_id", "type": "number"},
        ],
        "related_entities": [
            {
                "name": "Collection",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "owner", "type": "string"},
                ],
            },
            {
                "name": "Asset",
                "fields": [
                    {"name": "title", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "asset_type", "type": "string"},
                ],
            },
        ],
    },
    "social_app": {
        "primary_fields": [
            {"name": "title", "type": "string"},
            {"name": "content", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "author", "type": "string"},
            {"name": "community_id", "type": "number"},
        ],
        "related_entities": [
            {
                "name": "Community",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "member_count", "type": "number"},
                ],
            },
            {
                "name": "Member",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "role", "type": "string"},
                ],
            },
        ],
    },
    "learning_platform": {
        "primary_fields": [
            {"name": "title", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "progress", "type": "number"},
            {"name": "lesson_id", "type": "number"},
            {"name": "learner_id", "type": "number"},
        ],
        "related_entities": [
            {
                "name": "Lesson",
                "fields": [
                    {"name": "title", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "duration_minutes", "type": "number"},
                ],
            },
            {
                "name": "Learner",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "email", "type": "string"},
                ],
            },
        ],
    },
    "ecommerce_app": {
        "primary_fields": [
            {"name": "title", "type": "string"},
            {"name": "status", "type": "string"},
            {"name": "amount", "type": "number"},
            {"name": "customer_id", "type": "number"},
        ],
        "related_entities": [
            {
                "name": "Product",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "price", "type": "number"},
                ],
            },
            {
                "name": "Customer",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "status", "type": "string"},
                    {"name": "email", "type": "string"},
                ],
            },
        ],
    },
}


FAMILY_APP_PLANS = {
    "crm_platform": {
        "pages": [
            {"name": "Overview", "purpose": "See sales pipeline and account health."},
            {"name": "Deals", "purpose": "Manage active opportunities and stage movement."},
            {"name": "Accounts", "purpose": "Review customers, segments, and owners."},
        ],
        "api_routes": [
            {"path": "/deals", "method": "GET", "summary": "List deals"},
            {"path": "/crm/pipeline", "method": "GET", "summary": "Get CRM pipeline summary"},
            {"path": "/crm/accounts", "method": "GET", "summary": "Get CRM account health"},
        ],
        "sample_records": [
            {"title": "Enterprise expansion", "status": "proposal", "amount": 24000, "account_id": 1, "owner": "Avery"},
            {"title": "Renewal motion", "status": "negotiation", "amount": 12000, "account_id": 1, "owner": "Morgan"},
        ],
    },
    "support_desk": {
        "pages": [
            {"name": "Overview", "purpose": "Track support queue and SLA health."},
            {"name": "Tickets", "purpose": "Manage open tickets and escalations."},
            {"name": "Escalations", "purpose": "Review urgent customer issues and SLA risk."},
        ],
        "api_routes": [
            {"path": "/tickets", "method": "GET", "summary": "List support tickets"},
            {"path": "/support/queue", "method": "GET", "summary": "Get support queue summary"},
            {"path": "/support/escalations", "method": "GET", "summary": "Get escalation backlog"},
        ],
        "sample_records": [
            {"title": "Billing issue", "status": "open", "priority": "high", "customer_id": 1, "assignee": "Avery"},
            {"title": "Login problem", "status": "pending", "priority": "medium", "customer_id": 1, "assignee": "Morgan"},
        ],
    },
    "project_management": {
        "pages": [
            {"name": "Overview", "purpose": "Track project delivery posture and milestone risk."},
            {"name": "Projects", "purpose": "Manage active projects and owners."},
            {"name": "Milestones", "purpose": "Review milestone readiness and due dates."},
        ],
        "api_routes": [
            {"path": "/projects", "method": "GET", "summary": "List projects"},
            {"path": "/project-management/board", "method": "GET", "summary": "Get project delivery board"},
            {"path": "/project-management/milestones", "method": "GET", "summary": "Get milestone readiness"},
        ],
        "sample_records": [
            {"title": "Q2 launch", "status": "active", "owner": "Avery", "progress": 68, "milestone_id": 1},
            {"title": "Platform migration", "status": "planning", "owner": "Morgan", "progress": 25, "milestone_id": 1},
        ],
    },
    "recruiting_platform": {
        "pages": [
            {"name": "Overview", "purpose": "Track hiring pipeline and interview load."},
            {"name": "Candidates", "purpose": "Manage candidates and stage movement."},
            {"name": "Interviews", "purpose": "Review scheduled interviews and recruiter activity."},
        ],
        "api_routes": [
            {"path": "/candidates", "method": "GET", "summary": "List candidates"},
            {"path": "/recruiting/pipeline", "method": "GET", "summary": "Get recruiting pipeline summary"},
            {"path": "/recruiting/interviews", "method": "GET", "summary": "Get scheduled interviews"},
        ],
        "sample_records": [
            {"name": "Taylor Reed", "status": "screen", "job_id": 1, "recruiter": "Avery", "score": 82},
            {"name": "Jordan Park", "status": "interview", "job_id": 1, "recruiter": "Morgan", "score": 91},
        ],
    },
    "inventory_management": {
        "pages": [
            {"name": "Overview", "purpose": "Track stock health and replenishment risk."},
            {"name": "Inventory", "purpose": "Manage items, suppliers, and stock levels."},
            {"name": "Reorders", "purpose": "Review low-stock items and supplier actions."},
        ],
        "api_routes": [
            {"path": "/items", "method": "GET", "summary": "List inventory items"},
            {"path": "/inventory/stock", "method": "GET", "summary": "Get inventory stock summary"},
            {"path": "/inventory/reorders", "method": "GET", "summary": "Get reorder recommendations"},
        ],
        "sample_records": [
            {"title": "Starter Kit", "status": "in_stock", "sku": "KIT-100", "stock_level": 24, "supplier_id": 1},
            {"title": "Refill Pack", "status": "low_stock", "sku": "RF-210", "stock_level": 4, "supplier_id": 1},
        ],
    },
    "finance_ops": {
        "pages": [
            {"name": "Overview", "purpose": "Track cashflow and approvals posture."},
            {"name": "Invoices", "purpose": "Manage invoices and payment readiness."},
            {"name": "Approvals", "purpose": "Review invoices awaiting finance approval."},
        ],
        "api_routes": [
            {"path": "/invoices", "method": "GET", "summary": "List invoices"},
            {"path": "/finance/cashflow", "method": "GET", "summary": "Get finance cashflow summary"},
            {"path": "/finance/approvals", "method": "GET", "summary": "Get pending finance approvals"},
        ],
        "sample_records": [
            {"title": "April Retainer", "status": "pending", "amount": 4200, "customer_id": 1, "due_date": "2026-04-12"},
            {"title": "Implementation Invoice", "status": "approved", "amount": 8500, "customer_id": 1, "due_date": "2026-04-18"},
        ],
    },
    "internal_tool": {
        "pages": [
            {"name": "Overview", "purpose": "Track operational health and queues."},
            {"name": "Queue", "purpose": "Triage and manage active tickets."},
            {"name": "Approvals", "purpose": "Review items waiting for action."},
        ],
        "api_routes": [
            {"path": "/tickets", "method": "GET", "summary": "List internal tickets"},
            {"path": "/internal/queue", "method": "GET", "summary": "Get queue summary"},
            {"path": "/internal/approvals", "method": "GET", "summary": "Get approval backlog"},
        ],
        "sample_records": [
            {"title": "Warehouse handoff", "status": "open", "priority": "high", "assignee": "Avery", "team_id": 1},
            {"title": "Ops escalation", "status": "pending", "priority": "medium", "assignee": "Morgan", "team_id": 1},
        ],
    },
    "marketplace": {
        "pages": [
            {"name": "Overview", "purpose": "See marketplace activity and health."},
            {"name": "Listings", "purpose": "Browse and manage listings."},
            {"name": "Sellers", "purpose": "Track sellers and marketplace participation."},
        ],
        "api_routes": [
            {"path": "/listings", "method": "GET", "summary": "List marketplace listings"},
            {"path": "/marketplace/activity", "method": "GET", "summary": "Get marketplace activity"},
            {"path": "/marketplace/moderation/{item_id}", "method": "POST", "summary": "Moderate a marketplace item"},
        ],
        "sample_records": [
            {"title": "Founding Seller Listing", "status": "active", "seller": "Avery", "price": 42},
            {"title": "Pending Featured Listing", "status": "pending", "seller": "Morgan", "price": 79},
        ],
    },
    "booking_platform": {
        "pages": [
            {"name": "Overview", "purpose": "See availability and upcoming reservations."},
            {"name": "Bookings", "purpose": "Manage bookings and assigned resources."},
            {"name": "Resources", "purpose": "Review resource availability and capacity."},
        ],
        "api_routes": [
            {"path": "/bookings", "method": "GET", "summary": "List bookings"},
            {"path": "/booking/availability", "method": "GET", "summary": "Get booking availability"},
            {"path": "/resources", "method": "GET", "summary": "List bookable resources"},
        ],
        "sample_records": [
            {"title": "Morning Consultation", "status": "scheduled", "start_date": "2026-04-01", "resource_id": 1, "customer_id": 1},
            {"title": "Follow-up Session", "status": "pending", "start_date": "2026-04-02", "resource_id": 1, "customer_id": 1},
        ],
    },
    "content_platform": {
        "pages": [
            {"name": "Overview", "purpose": "View publishing status and schedules."},
            {"name": "Content", "purpose": "Manage articles and assets."},
            {"name": "Calendar", "purpose": "Track scheduled content and deadlines."},
        ],
        "api_routes": [
            {"path": "/articles", "method": "GET", "summary": "List articles"},
            {"path": "/content/pipeline", "method": "GET", "summary": "Get publishing pipeline"},
            {"path": "/content/calendar", "method": "GET", "summary": "Get publishing calendar"},
        ],
        "sample_records": [
            {"title": "Launch announcement", "status": "draft", "author": "Avery", "publish_date": "2026-04-05", "collection_id": 1},
            {"title": "Editorial feature", "status": "scheduled", "author": "Morgan", "publish_date": "2026-04-07", "collection_id": 1},
        ],
    },
    "social_app": {
        "pages": [
            {"name": "Overview", "purpose": "Track community health and participation."},
            {"name": "Feed", "purpose": "Browse and manage posts."},
            {"name": "Moderation", "purpose": "Review flagged content and member safety."},
        ],
        "api_routes": [
            {"path": "/posts", "method": "GET", "summary": "List posts"},
            {"path": "/social/engagement", "method": "GET", "summary": "Get social engagement summary"},
            {"path": "/social/moderation", "method": "GET", "summary": "Get moderation queue"},
        ],
        "sample_records": [
            {"title": "Welcome thread", "content": "Introduce yourself to the community.", "status": "active", "author": "Avery", "community_id": 1},
            {"title": "Feature request", "content": "Vote on what the team should build next.", "status": "flagged", "author": "Morgan", "community_id": 1},
        ],
    },
    "learning_platform": {
        "pages": [
            {"name": "Overview", "purpose": "See course performance and learner progress."},
            {"name": "Courses", "purpose": "Manage courses and lessons."},
            {"name": "Progress", "purpose": "Track learner completion and readiness."},
        ],
        "api_routes": [
            {"path": "/courses", "method": "GET", "summary": "List courses"},
            {"path": "/learning/progress", "method": "GET", "summary": "Get learning progress summary"},
            {"path": "/learning/lessons", "method": "GET", "summary": "Get lesson readiness"},
        ],
        "sample_records": [
            {"title": "Onboarding Academy", "status": "active", "progress": 72, "lesson_id": 1, "learner_id": 1},
            {"title": "Manager Essentials", "status": "draft", "progress": 35, "lesson_id": 1, "learner_id": 1},
        ],
    },
    "ecommerce_app": {
        "pages": [
            {"name": "Overview", "purpose": "See order and fulfillment health."},
            {"name": "Orders", "purpose": "Manage orders and shipment state."},
            {"name": "Catalog", "purpose": "Monitor products and pricing."},
        ],
        "api_routes": [
            {"path": "/orders", "method": "GET", "summary": "List ecommerce orders"},
            {"path": "/ecommerce/orders", "method": "GET", "summary": "Get order pipeline"},
            {"path": "/ecommerce/orders/{item_id}/advance", "method": "POST", "summary": "Advance an order"},
        ],
        "sample_records": [
            {"title": "Starter Order", "status": "pending", "amount": 99, "customer_id": 1},
            {"title": "Priority Order", "status": "processing", "amount": 149, "customer_id": 1},
        ],
    },
}


DEFAULT_FAMILY = {
    "template_key": "dashboard_shell",
    "navigation_style": "tabs",
    "summary_cards": ["Active Pipelines", "Primary Route", "Entities"],
    "automation_actions": [
        {"action": "sync-status", "label": "Sync Status"},
        {"action": "notify-team", "label": "Notify Team"},
    ],
    "record_label": "Records",
    "search_placeholder": "Search records, statuses, and links",
}


SCAFFOLD_FAMILIES = {
    "saas_dashboard": {},
    "crm_platform": {
        "summary_cards": ["Pipeline Value", "Primary Route", "Accounts"],
        "automation_actions": [
            {"action": "sync-forecast", "label": "Sync Forecast"},
            {"action": "notify-reps", "label": "Notify Reps"},
        ],
        "record_label": "Deals",
        "search_placeholder": "Search deals, accounts, and pipeline stages",
    },
    "support_desk": {
        "summary_cards": ["Open Tickets", "Primary Route", "Escalations"],
        "automation_actions": [
            {"action": "triage-tickets", "label": "Triage Tickets"},
            {"action": "notify-customers", "label": "Notify Customers"},
        ],
        "record_label": "Tickets",
        "search_placeholder": "Search tickets, customers, and priorities",
    },
    "project_management": {
        "summary_cards": ["Projects", "Primary Route", "Milestones"],
        "automation_actions": [
            {"action": "update-status", "label": "Update Status"},
            {"action": "notify-owners", "label": "Notify Owners"},
        ],
        "record_label": "Projects",
        "search_placeholder": "Search projects, milestones, and owners",
    },
    "recruiting_platform": {
        "summary_cards": ["Candidates", "Primary Route", "Interview Stages"],
        "automation_actions": [
            {"action": "schedule-interviews", "label": "Schedule Interviews"},
            {"action": "notify-hiring-team", "label": "Notify Hiring Team"},
        ],
        "record_label": "Candidates",
        "search_placeholder": "Search candidates, jobs, and recruiters",
    },
    "inventory_management": {
        "summary_cards": ["Stock Items", "Primary Route", "Suppliers"],
        "automation_actions": [
            {"action": "reorder-stock", "label": "Reorder Stock"},
            {"action": "notify-suppliers", "label": "Notify Suppliers"},
        ],
        "record_label": "Inventory",
        "search_placeholder": "Search items, SKUs, and suppliers",
    },
    "finance_ops": {
        "summary_cards": ["Pending Invoices", "Primary Route", "Approvals"],
        "automation_actions": [
            {"action": "sync-cashflow", "label": "Sync Cashflow"},
            {"action": "notify-approvers", "label": "Notify Approvers"},
        ],
        "record_label": "Invoices",
        "search_placeholder": "Search invoices, customers, and due dates",
    },
    "internal_tool": {
        "summary_cards": ["Ops Queue", "Primary Route", "Teams"],
        "automation_actions": [
            {"action": "triage-queue", "label": "Triage Queue"},
            {"action": "notify-operator", "label": "Notify Operator"},
        ],
        "record_label": "Work Queue",
        "search_placeholder": "Search tickets, owners, and statuses",
    },
    "marketplace": {
        "summary_cards": ["Listings", "Primary Route", "Participants"],
        "automation_actions": [
            {"action": "review-listings", "label": "Review Listings"},
            {"action": "message-sellers", "label": "Message Sellers"},
        ],
        "record_label": "Listings",
        "search_placeholder": "Search listings, sellers, and statuses",
    },
    "booking_platform": {
        "summary_cards": ["Upcoming Bookings", "Primary Route", "Resources"],
        "automation_actions": [
            {"action": "confirm-bookings", "label": "Confirm Bookings"},
            {"action": "notify-guests", "label": "Notify Guests"},
        ],
        "record_label": "Bookings",
        "search_placeholder": "Search bookings, guests, and resources",
    },
    "content_platform": {
        "summary_cards": ["Published Assets", "Primary Route", "Collections"],
        "automation_actions": [
            {"action": "schedule-content", "label": "Schedule Content"},
            {"action": "notify-editors", "label": "Notify Editors"},
        ],
        "record_label": "Content",
        "search_placeholder": "Search content, authors, and tags",
    },
    "social_app": {
        "summary_cards": ["Communities", "Primary Route", "Member Types"],
        "automation_actions": [
            {"action": "moderate-feed", "label": "Moderate Feed"},
            {"action": "notify-members", "label": "Notify Members"},
        ],
        "record_label": "Communities",
        "search_placeholder": "Search posts, members, and groups",
    },
    "learning_platform": {
        "summary_cards": ["Courses", "Primary Route", "Learning Tracks"],
        "automation_actions": [
            {"action": "publish-lessons", "label": "Publish Lessons"},
            {"action": "notify-learners", "label": "Notify Learners"},
        ],
        "record_label": "Courses",
        "search_placeholder": "Search lessons, learners, and courses",
    },
    "ecommerce_app": {
        "summary_cards": ["Catalog Items", "Primary Route", "Order Types"],
        "automation_actions": [
            {"action": "sync-inventory", "label": "Sync Inventory"},
            {"action": "notify-buyers", "label": "Notify Buyers"},
        ],
        "record_label": "Catalog",
        "search_placeholder": "Search products, orders, and customers",
    },
}


def get_scaffold_family(app_type):
    family = deepcopy(DEFAULT_FAMILY)
    family.update(deepcopy(SCAFFOLD_FAMILIES.get(app_type, {})))
    family["app_type"] = app_type
    family["app_type_label"] = APP_TYPE_LABELS.get(app_type, "Application")
    return family


def get_family_manifest_defaults(app_type):
    return deepcopy(FAMILY_SPECS.get(app_type, {}).get("manifest_defaults", {}))


def get_family_schema_requirements(app_type):
    return deepcopy(FAMILY_SPECS.get(app_type, {}).get("schema_requirements", {}))


def _entity_key(name):
    return re.sub(r"[^a-z0-9]+", "", str(name).lower())


def apply_family_entity_plan(app_type, data_model, primary_entity):
    plan = FAMILY_ENTITY_PLANS.get(app_type)
    if not plan:
        return deepcopy(data_model)

    planned = deepcopy(data_model)
    if not planned:
        planned = [{"name": primary_entity or "Record", "fields": []}]

    primary_key = _entity_key(primary_entity or planned[0].get("name", "Record"))
    first_entity = None
    for entity in planned:
        if _entity_key(entity.get("name")) == primary_key:
            first_entity = entity
            break
    if first_entity is None:
        first_entity = planned[0]
        if primary_entity:
            first_entity["name"] = primary_entity

    existing_primary_fields = {
        str(field.get("name", "")).strip().lower()
        for field in first_entity.get("fields", [])
        if isinstance(field, dict)
    }
    first_entity.setdefault("fields", [])
    for field in plan["primary_fields"]:
        if field["name"].lower() not in existing_primary_fields:
            first_entity["fields"].append(deepcopy(field))

    existing_entities = {_entity_key(entity.get("name")) for entity in planned}
    for related in plan["related_entities"]:
        related_key = _entity_key(related["name"])
        if related_key in existing_entities:
            continue
        planned.append(deepcopy(related))

    return planned


def apply_family_pages_plan(app_type, pages):
    plan = FAMILY_APP_PLANS.get(app_type, {})
    existing = deepcopy(pages) if isinstance(pages, list) else []
    merged = existing[:]
    existing_names = {str(page.get("name", "")).strip().lower() for page in merged if isinstance(page, dict)}
    for page in plan.get("pages", ()):
        if page["name"].strip().lower() not in existing_names:
            merged.append(deepcopy(page))
    return merged


def apply_family_routes_plan(app_type, api_routes):
    plan = FAMILY_APP_PLANS.get(app_type, {})
    existing = deepcopy(api_routes) if isinstance(api_routes, list) else []
    merged = existing[:]
    existing_keys = {
        (
            str(route.get("path", "")).strip().lower(),
            str(route.get("method", "")).strip().upper(),
        )
        for route in merged
        if isinstance(route, dict)
    }
    for route in plan.get("api_routes", ()):
        key = (route["path"].strip().lower(), route["method"].strip().upper())
        if key not in existing_keys:
            merged.append(deepcopy(route))
    return merged


def apply_family_samples_plan(app_type, sample_records):
    plan = FAMILY_APP_PLANS.get(app_type, {})
    existing = deepcopy(sample_records) if isinstance(sample_records, list) else []
    planned_samples = deepcopy(plan.get("sample_records", ()))
    if not planned_samples:
        return existing

    merged = []
    for index, sample in enumerate(existing):
        template = planned_samples[index] if index < len(planned_samples) else {}
        if isinstance(sample, dict):
            hydrated = deepcopy(template)
            hydrated.update(sample)
            merged.append(hydrated)
        else:
            merged.append(sample)

    if not merged:
        return planned_samples

    for template in planned_samples[len(merged):]:
        merged.append(deepcopy(template))

    return merged


def render_family_prompt_guide():
    lines = []
    for app_type in (
        "saas_dashboard",
        "crm_platform",
        "support_desk",
        "project_management",
        "recruiting_platform",
        "inventory_management",
        "finance_ops",
        "internal_tool",
        "marketplace",
        "booking_platform",
        "content_platform",
        "social_app",
        "learning_platform",
        "ecommerce_app",
    ):
        label = APP_TYPE_LABELS[app_type]
        guidance = FAMILY_SPECS.get(app_type, {}).get("prompt_guidance", "")
        lines.append(f"- {app_type} ({label}): {guidance}")
    return "\n".join(lines)


def get_product_boundary():
    return deepcopy(PRODUCT_BOUNDARY)


def render_product_boundary_guide():
    boundary = get_product_boundary()
    lines = [
        f"Mode: {boundary['mode']}",
        "Supported:",
        *[f"- {item}" for item in boundary["supported"]],
        "Starter-only:",
        *[f"- {item}" for item in boundary["starter_only"]],
        "Unsupported:",
        *[f"- {item}" for item in boundary["unsupported"]],
    ]
    return "\n".join(lines)
