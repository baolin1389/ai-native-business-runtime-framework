"""
Trade CRM Runtime — CLI Entry Point
=====================================
Usage:
    python app/main.py list_customers
    python app/main.py create_customer --company "Berlin GmbH" --email test@berlin.de --country Germany --name "Hans"
    python app/main.py get_customer --id CUST_xxx
    python app/main.py add_followup --customer CUST_xxx --content "Sent price list"
    python app/main.py list_followups --customer CUST_xxx
    python app/main.py update_customer --id CUST_xxx --status "已联系"
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.database import init_db
from app.runtime.engine import RuntimeEngine


def main():
    parser = argparse.ArgumentParser(description="Trade CRM Runtime CLI")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # list_customers
    p = sub.add_parser("list_customers", help="List all customers")
    p.add_argument("--status", help="Filter by contact status")
    p.add_argument("--country", help="Filter by country")
    p.add_argument("--limit", type=int, default=100, help="Max results (default: 100)")

    # create_customer
    p = sub.add_parser("create_customer", help="Create a new customer")
    p.add_argument("--company", required=True, help="Company name")
    p.add_argument("--name", required=True, help="Contact person name")
    p.add_argument("--email", required=True, help="Contact email")
    p.add_argument("--country", required=True, help="Country")
    p.add_argument("--type", dest="business_type", help="Business type")
    p.add_argument("--notes", help="Notes")

    # get_customer
    p = sub.add_parser("get_customer", help="Get customer by ID")
    p.add_argument("--id", required=True, help="Customer ID")

    # update_customer
    p = sub.add_parser("update_customer", help="Update customer")
    p.add_argument("--id", required=True, help="Customer ID")
    p.add_argument("--status", help="New contact status")
    p.add_argument("--notes", help="Updated notes")

    # add_followup
    p = sub.add_parser("add_followup", help="Add follow-up record")
    p.add_argument("--customer", required=True, help="Customer ID")
    p.add_argument("--content", required=True, help="Follow-up content")
    p.add_argument("--type", dest="followup_type", default="call", help="Follow-up type")

    # list_followups
    p = sub.add_parser("list_followups", help="List follow-ups for a customer")
    p.add_argument("--customer", required=True, help="Customer ID")
    p.add_argument("--limit", type=int, default=100, help="Max results")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize runtime
    import os
    os.chdir(Path(__file__).parent.parent)
    init_db()
    engine = RuntimeEngine("runtime.yaml")

    # Route command
    if args.command == "list_customers":
        result = engine.execute("list_customers", {
            "contact_status": args.status,
            "country": args.country,
            "limit": args.limit,
        })

    elif args.command == "create_customer":
        result = engine.execute("create_customer", {
            "company_name": args.company,
            "contact_name": args.name,
            "contact_email": args.email,
            "country": args.country,
            "business_type": args.business_type,
            "notes": args.notes,
        })

    elif args.command == "get_customer":
        result = engine.execute("get_customer", {"customer_id": args.id})

    elif args.command == "update_customer":
        params = {"customer_id": args.id}
        if args.status:
            params["contact_status"] = args.status
        if args.notes:
            params["notes"] = args.notes
        result = engine.execute("update_customer", params)

    elif args.command == "add_followup":
        result = engine.execute("add_followup", {
            "customer_id": args.customer,
            "content": args.content,
            "followup_type": args.followup_type,
        })

    elif args.command == "list_followups":
        result = engine.execute("list_followups", {
            "customer_id": args.customer,
            "limit": args.limit,
        })

    else:
        result = {"success": False, "error": f"Unknown command: {args.command}"}

    # Output
    if result.get("success"):
        import json
        print(json.dumps(result.get("result"), indent=2, ensure_ascii=False))
    else:
        print(f"ERROR: {result.get('error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()