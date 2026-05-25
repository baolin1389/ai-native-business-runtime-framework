# Trade CRM Runtime — Reference Implementation

> **What is this?**
> This is the **Reference Runtime** for the AI Business Runtime Framework.
> It serves as: Demo · Tutorial · Benchmark · Template for new runtimes.

## Purpose

```
AI ──▶ Runtime.execute("create_customer", {...})
                    │
                    ▼
              ┌─────────────────┐
              │  Trade CRM      │
              │  Reference      │
              │  Runtime        │
              └─────────────────┘
```

AI agents can learn from this runtime to understand:
- How domain YAMLs define business entities and constraints
- How the runtime engine executes actions
- How database models map to domain definitions
- What a well-structured runtime looks like

## Architecture

```
runtime.yaml          ← Runtime Manifest (THE key file)
                       Defines: name, version, entities, actions, infrastructure

app/
├── domain/           ← Domain DSL definitions (YAML)
│   ├── customer.yaml # Customer entity: fields, constraints, state_machine, actions
│   └── followup.yaml # Followup entity
│
├── runtime/
│   ├── engine.py      ← RuntimeEngine.execute(action, params)
│   └── actions/
│       ├── customer_actions.py
│       └── followup_actions.py
│
├── infrastructure/
│   ├── database.py    ← SQLite + SQLModel (Customer, Followup models)
│   └── repositories/
│       ├── customer_repo.py
│       └── followup_repo.py
│
└── main.py           ← CLI entry point

data/
└── crm.db            ← SQLite database (gitignored)
```

## Quick Start

```bash
cd examples/trade_crm_runtime
pip install -r requirements.txt

# List all customers
python app/main.py list_customers

# Create a customer
python app/main.py create_customer \
  --company "Berlin Ingredients GmbH" \
  --email "hans@berlin.de" \
  --country "Germany" \
  --name "Hans Mueller"

# Update customer status
python app/main.py update_customer --id CUST_xxx --status "已联系"

# Add a follow-up record
python app/main.py add_followup --customer CUST_xxx --content "Sent price list"

# List follow-ups
python app/main.py list_followups --customer CUST_xxx

# Get customer details
python app/main.py get_customer --id CUST_xxx
```

## Entity: Customer

**Fields:**
- `customer_id` — Unique ID (auto-generated)
- `company_name` — Company name (required)
- `contact_name` — Primary contact (required)
- `contact_email` — Email (required, validated)
- `contact_phone` — Phone number
- `country` — Country (required)
- `business_type` — distributor / manufacturer / agent
- `contact_status` — new / 未联系 / 已联系 / 已报价 / 已打样 / 成交 / closed_won / closed_lost
- `notes` — Free-form notes
- `follow_up_count` — Auto-incremented on each status change
- `created_at` — Creation timestamp
- `updated_at` — Last update timestamp

**State Machine:**
```
new → 未联系 → 已联系 → 已报价 → 已打样 → 成交 → closed_won
                                    ↘         ↙
                                    closed_lost
```

**Constraints:**
- email must match valid email format
- contact_status must be one of the valid values

## Entity: Followup

**Fields:**
- `followup_id` — Unique ID
- `customer_id` — Foreign key to Customer
- `content` — Follow-up content (required)
- `followup_type` — call / email / meeting / wechat
- `followup_date` — Timestamp (auto-set)
- `next_followup_date` — Scheduled next follow-up
- `created_by` — Creator identifier

## All Actions

| Action | Description |
|--------|-------------|
| `create_customer` | Create new customer |
| `list_customers` | List customers (filter by status/country) |
| `get_customer` | Get customer by ID |
| `update_customer` | Update customer fields (contact_status, notes) |
| `add_followup` | Add follow-up record for customer |
| `list_followups` | List follow-ups for a customer |

## runtime.yaml Structure

```yaml
name: trade_crm_runtime        # Runtime identity
version: "1.0"                # Semantic version
description: "Reference CRM runtime for foreign trade business"

entry: app.main:CLI           # Entry point

directories:                   # Standard layout (AI-readable)
  app/domain/: "Entity DSL definitions (YAML)"
  app/runtime/actions/: "Business action implementations"
  app/infrastructure/: "Database models and repositories"
  data/: "SQLite database files"

entities:                      # Entity registry
  - Customer
  - Followup

infrastructure:
  database:
    type: sqlite
    path: data/crm.db
    models:
      - Customer
      - Followup

actions:                      # Available actions
  - create_customer
  - list_customers
  - get_customer
  - update_customer
  - add_followup
  - list_followups

constraints:                  # Cross-entity business rules
  - name: followup_requires_customer
    condition: "customer_id is not null"
    error_message: "Follow-up must belong to a customer"
```

## How to Extend

1. **Add new entity**: Create `app/domain/your_entity.yaml`, add model to `database.py`, add actions
2. **Add new action**: Add method to appropriate actions file, register in engine
3. **Add constraint**: Add to entity's `constraints:` section in domain YAML

## Framework Alignment

This reference runtime demonstrates the patterns described in:
- `docs/guides/domain-dsl.md` — Domain YAML DSL specification
- `runtime.schema.yaml` — Runtime manifest schema
- `docs/architecture/runtime.md` — Runtime engine architecture