from typing import List, Dict, Any
from datetime import datetime
from decimal import Decimal

from app.models.issue import IssueSeverity, IssueCategory


def detect_issues(
    matches: List[Dict],
    unmatched_bank: List[Dict],
    unmatched_invoices: List[Dict],
    duplicates: List[Dict],
    gst_summaries: List[Dict],
    invoice_totals: Dict[str, float],
) -> List[Dict[str, Any]]:
    """
    Detect all types of issues from reconciliation data.
    Returns a list of issue dictionaries.
    """
    issues = []
    
    # Issue 1: Missing invoices (bank transactions without matching invoices)
    for bank_txn in unmatched_bank:
        if abs(float(bank_txn.get("amount", 0))) > 100:  # Ignore small amounts
            issue = {
                "category": IssueCategory.MISSING_INVOICE,
                "severity": _calculate_severity(float(bank_txn.get("amount", 0))),
                "title": f"Missing invoice for bank transaction",
                "details_json": {
                    "bank_transaction": {
                        "id": str(bank_txn.get("id", "")),
                        "date": str(bank_txn.get("txn_date", "")),
                        "amount": float(bank_txn.get("amount", 0)),
                        "description": bank_txn.get("description", ""),
                        "reference": bank_txn.get("reference_id", ""),
                    },
                    "recommendation": "Locate the corresponding invoice or document this as a non-invoice transaction.",
                },
            }
            issues.append(issue)
    
    # Issue 2: Unreconciled invoices (invoices without bank entries)
    for inv_txn in unmatched_invoices:
        if abs(float(inv_txn.get("amount", 0))) > 100:
            issue = {
                "category": IssueCategory.MISMATCH,
                "severity": _calculate_severity(float(inv_txn.get("amount", 0))),
                "title": f"Invoice not found in bank statement",
                "details_json": {
                    "invoice": {
                        "id": str(inv_txn.get("id", "")),
                        "date": str(inv_txn.get("txn_date", "")),
                        "amount": float(inv_txn.get("amount", 0)),
                        "reference": inv_txn.get("reference_id", ""),
                        "counterparty": inv_txn.get("counterparty", ""),
                    },
                    "recommendation": "Verify payment status or check for recording errors.",
                },
            }
            issues.append(issue)
    
    # Issue 3: Duplicates
    for dup_group in duplicates:
        if dup_group["count"] > 1:
            total_amount = sum(
                abs(float(t.get("amount", 0))) 
                for t in dup_group["transactions"]
            )
            issue = {
                "category": IssueCategory.DUPLICATE,
                "severity": IssueSeverity.MEDIUM if dup_group["count"] == 2 else IssueSeverity.HIGH,
                "title": f"Potential duplicate transactions detected ({dup_group['count']} entries)",
                "details_json": {
                    "duplicate_key": dup_group["key"],
                    "count": dup_group["count"],
                    "total_amount": total_amount,
                    "transactions": [
                        {
                            "id": str(t.get("id", "")),
                            "date": str(t.get("txn_date", "")),
                            "amount": float(t.get("amount", 0)),
                            "description": t.get("description", ""),
                        }
                        for t in dup_group["transactions"]
                    ],
                    "recommendation": "Review and remove duplicate entries if confirmed.",
                },
            }
            issues.append(issue)
    
    # Issue 4: GST mismatches
    for gst in gst_summaries:
        period = gst.get("period", "")
        gst_taxable = float(gst.get("taxable_value", 0))
        
        # Get invoice total for the same period
        invoice_total = invoice_totals.get(period, 0)
        
        if invoice_total > 0 and gst_taxable > 0:
            diff = abs(gst_taxable - invoice_total)
            diff_percent = diff / max(gst_taxable, invoice_total) * 100
            
            if diff_percent > 1:  # More than 1% difference
                issue = {
                    "category": IssueCategory.GST_MISMATCH,
                    "severity": IssueSeverity.HIGH if diff_percent > 5 else IssueSeverity.MEDIUM,
                    "title": f"GST filing mismatch for period {period}",
                    "details_json": {
                        "period": period,
                        "gst_declared_taxable": gst_taxable,
                        "invoice_total": invoice_total,
                        "difference": diff,
                        "difference_percent": round(diff_percent, 2),
                        "recommendation": "Reconcile GST returns with invoice records.",
                    },
                }
                issues.append(issue)
    
    # Issue 5: Low confidence matches
    for match in matches:
        if match.get("confidence", 1.0) < 0.85 and match.get("match_type") == "fuzzy":
            issue = {
                "category": IssueCategory.OTHER,
                "severity": IssueSeverity.LOW,
                "title": "Low confidence transaction match",
                "details_json": {
                    "bank_txn_id": match.get("bank_txn_id"),
                    "invoice_txn_id": match.get("invoice_txn_id"),
                    "confidence": match.get("confidence"),
                    "details": match.get("details", {}),
                    "recommendation": "Manually verify this match is correct.",
                },
            }
            issues.append(issue)
    
    return issues


def _calculate_severity(amount: float) -> IssueSeverity:
    """Calculate issue severity based on amount."""
    abs_amount = abs(amount)
    
    if abs_amount > 100000:  # > 1 lakh
        return IssueSeverity.HIGH
    elif abs_amount > 10000:  # > 10k
        return IssueSeverity.MEDIUM
    else:
        return IssueSeverity.LOW


def summarize_issues(issues: List[Dict]) -> Dict[str, Any]:
    """Create a summary of detected issues."""
    summary = {
        "total_issues": len(issues),
        "by_severity": {
            "high": 0,
            "medium": 0,
            "low": 0,
        },
        "by_category": {
            "missing_invoice": 0,
            "duplicate": 0,
            "mismatch": 0,
            "gst_mismatch": 0,
            "other": 0,
        },
    }
    
    for issue in issues:
        severity = issue.get("severity")
        if isinstance(severity, IssueSeverity):
            severity = severity.value
        
        category = issue.get("category")
        if isinstance(category, IssueCategory):
            category = category.value
        
        if severity in summary["by_severity"]:
            summary["by_severity"][severity] += 1
        if category in summary["by_category"]:
            summary["by_category"][category] += 1
    
    return summary
