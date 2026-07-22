"""
Lifecycle Security & PII Data Masking Governance Engine
"""
import re
import logging
from typing import Dict, Any, Tuple

log = logging.getLogger("ai-property-advisor.harness.hooks")

# Dangerous SQL patterns
BLOCKED_SQL_PATTERNS = [
    r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b",
    r"\bALTER\b", r"\bTRUNCATE\b", r"\bGRANT\b", r"\bREVOKE\b"
]


def pre_tool_hook(tool_name: str, args: dict) -> Tuple[bool, str, dict]:
    """
    Hook executed BEFORE tool dispatch.
    Returns: (is_allowed, error_message_if_blocked, modified_args)
    """
    log.debug("Pre-tool hook executing for %s", tool_name)

    if tool_name == "execute_sql_query":
        sql = args.get("sql_query", "")
        sql_upper = sql.upper()

        for pattern in BLOCKED_SQL_PATTERNS:
            if re.search(pattern, sql_upper):
                msg = f"Security Policy Violation: Command '{pattern}' blocked. Only read-only SELECT queries are allowed."
                log.warning(msg)
                return False, msg, args

    return True, "", args


def post_tool_hook(tool_name: str, result_str: str) -> str:
    """
    Hook executed AFTER tool dispatch.
    Masks PII (Phone numbers, National ID cards) in JSON output to protect privacy.
    """
    log.debug("Post-tool hook executing for %s", tool_name)
    if not result_str or not isinstance(result_str, str):
        return result_str

    # Mask Vietnamese Phone numbers (e.g. 0912345678 -> 0912***678)
    masked = re.sub(r'(\b0[3|5|7|8|9]\d{2})\d{3}(\d{3}\b)', r'\1***\2', result_str)

    # Mask 12-digit Citizen ID / CCCD numbers (e.g. 036099001234 -> 0360****1234)
    masked = re.sub(r'(\b\d{4})\d{4}(\d{4}\b)', r'\1****\2', masked)

    return masked
