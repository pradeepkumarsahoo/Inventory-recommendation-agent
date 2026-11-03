"""Thin CLI wrapper for the GuardrailService.

Reads JSON from stdin, dispatches to the named method, and writes the
JSON verdict to stdout. Used by the C# API as a subprocess bridge.

Usage:
    echo '{"store_id": "S101", "intent": "daily_game_plan"}' | python guardrail_cli.py validate_input
"""
from __future__ import annotations

import json
import sys

from guardrail_service import GuardrailService  # noqa: F401


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"allowed": False, "reason": "missing_method"}))
        sys.exit(1)
    method = sys.argv[1]
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"allowed": False, "reason": "invalid_json"}))
        sys.exit(1)

    svc = GuardrailService()
    try:
        if method == "validate_input":
            print(json.dumps(svc.validate_input(payload)))
        elif method == "validate_recommendation":
            print(json.dumps(svc.validate_recommendation(payload)))
        elif method == "validate_tool_call":
            print(json.dumps(svc.validate_tool_call(payload["tool_name"], payload.get("args", {}))))
        elif method == "authorize_execution":
            # Caller must look up the recommendation to produce `rec` here;
            # for simplicity we take a minimal body carrying required_approval.
            rec = payload.get("recommendation", {"required_approval": payload.get("required_approval", "store_manager"), "action_type": payload.get("action_type", "FRONT_OFFICE")})
            print(json.dumps(svc.authorize_execution(rec, payload["approver_role"])))
        else:
            print(json.dumps({"allowed": False, "reason": f"unknown_method:{method}"}))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"allowed": False, "reason": f"guardrail_error: {e}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
