from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class MatchResult:
    """Result of matching two transactions."""
    bank_txn_id: str
    invoice_txn_id: str
    confidence: float
    match_type: str  # "exact", "fuzzy", "llm"
    details: Dict[str, Any]


def match_transactions(
    bank_transactions: List[Dict[str, Any]],
    invoice_transactions: List[Dict[str, Any]],
    date_tolerance_days: int = 3,
    amount_tolerance_percent: float = 0.01,
) -> Tuple[List[MatchResult], List[Dict], List[Dict]]:
    """
    Match bank transactions with invoice transactions.
    
    Returns:
        - List of matches
        - Unmatched bank transactions
        - Unmatched invoice transactions
    """
    matches = []
    matched_bank_ids = set()
    matched_invoice_ids = set()
    
    # Sort transactions by date for efficiency
    bank_txns = sorted(bank_transactions, key=lambda x: x.get("txn_date") or datetime.min)
    invoice_txns = sorted(invoice_transactions, key=lambda x: x.get("txn_date") or datetime.min)
    
    # Phase 1: Exact matches (same amount, same date, same reference)
    for bank_txn in bank_txns:
        if bank_txn.get("id") in matched_bank_ids:
            continue
            
        for inv_txn in invoice_txns:
            if inv_txn.get("id") in matched_invoice_ids:
                continue
            
            if _is_exact_match(bank_txn, inv_txn):
                match = MatchResult(
                    bank_txn_id=str(bank_txn.get("id")),
                    invoice_txn_id=str(inv_txn.get("id")),
                    confidence=1.0,
                    match_type="exact",
                    details={
                        "bank_amount": float(bank_txn.get("amount", 0)),
                        "invoice_amount": float(inv_txn.get("amount", 0)),
                        "bank_date": str(bank_txn.get("txn_date")),
                        "invoice_date": str(inv_txn.get("txn_date")),
                    }
                )
                matches.append(match)
                matched_bank_ids.add(bank_txn.get("id"))
                matched_invoice_ids.add(inv_txn.get("id"))
                break
    
    # Phase 2: Fuzzy matches (similar amount within tolerance, date within window)
    for bank_txn in bank_txns:
        if bank_txn.get("id") in matched_bank_ids:
            continue
            
        best_match = None
        best_confidence = 0.0
        
        for inv_txn in invoice_txns:
            if inv_txn.get("id") in matched_invoice_ids:
                continue
            
            confidence = _calculate_match_confidence(
                bank_txn, 
                inv_txn, 
                date_tolerance_days, 
                amount_tolerance_percent
            )
            
            if confidence > 0.7 and confidence > best_confidence:
                best_confidence = confidence
                best_match = inv_txn
        
        if best_match:
            match = MatchResult(
                bank_txn_id=str(bank_txn.get("id")),
                invoice_txn_id=str(best_match.get("id")),
                confidence=best_confidence,
                match_type="fuzzy",
                details={
                    "bank_amount": float(bank_txn.get("amount", 0)),
                    "invoice_amount": float(best_match.get("amount", 0)),
                    "bank_date": str(bank_txn.get("txn_date")),
                    "invoice_date": str(best_match.get("txn_date")),
                    "confidence_score": best_confidence,
                }
            )
            matches.append(match)
            matched_bank_ids.add(bank_txn.get("id"))
            matched_invoice_ids.add(best_match.get("id"))
    
    # Get unmatched transactions
    unmatched_bank = [t for t in bank_txns if t.get("id") not in matched_bank_ids]
    unmatched_invoices = [t for t in invoice_txns if t.get("id") not in matched_invoice_ids]
    
    return matches, unmatched_bank, unmatched_invoices


def _is_exact_match(bank_txn: Dict, inv_txn: Dict) -> bool:
    """Check if two transactions are an exact match."""
    # Check amount
    bank_amount = abs(float(bank_txn.get("amount", 0)))
    inv_amount = abs(float(inv_txn.get("amount", 0)))
    
    if abs(bank_amount - inv_amount) > 0.01:
        return False
    
    # Check date (same day)
    bank_date = bank_txn.get("txn_date")
    inv_date = inv_txn.get("txn_date")
    
    if bank_date and inv_date:
        if isinstance(bank_date, str):
            bank_date = datetime.fromisoformat(bank_date.replace("Z", "+00:00"))
        if isinstance(inv_date, str):
            inv_date = datetime.fromisoformat(inv_date.replace("Z", "+00:00"))
        
        if bank_date.date() != inv_date.date():
            return False
    
    # Check reference if available
    bank_ref = bank_txn.get("reference_id", "").lower().strip()
    inv_ref = inv_txn.get("reference_id", "").lower().strip()
    
    if bank_ref and inv_ref and bank_ref == inv_ref:
        return True
    
    # If no reference but amount and date match
    if bank_amount > 0 and bank_date and inv_date:
        return True
    
    return False


def _calculate_match_confidence(
    bank_txn: Dict, 
    inv_txn: Dict,
    date_tolerance_days: int,
    amount_tolerance_percent: float,
) -> float:
    """Calculate the confidence score for a potential match."""
    confidence = 0.0
    
    # Amount similarity (40% weight)
    bank_amount = abs(float(bank_txn.get("amount", 0)))
    inv_amount = abs(float(inv_txn.get("amount", 0)))
    
    if bank_amount == 0 or inv_amount == 0:
        return 0.0
    
    amount_diff_percent = abs(bank_amount - inv_amount) / max(bank_amount, inv_amount)
    
    if amount_diff_percent <= amount_tolerance_percent:
        confidence += 0.4 * (1 - amount_diff_percent / amount_tolerance_percent)
    else:
        return 0.0  # Amount too different, no match
    
    # Date proximity (30% weight)
    bank_date = bank_txn.get("txn_date")
    inv_date = inv_txn.get("txn_date")
    
    if bank_date and inv_date:
        if isinstance(bank_date, str):
            bank_date = datetime.fromisoformat(bank_date.replace("Z", "+00:00"))
        if isinstance(inv_date, str):
            inv_date = datetime.fromisoformat(inv_date.replace("Z", "+00:00"))
        
        date_diff = abs((bank_date.date() - inv_date.date()).days)
        
        if date_diff <= date_tolerance_days:
            confidence += 0.3 * (1 - date_diff / date_tolerance_days)
    
    # Reference similarity (20% weight)
    bank_ref = str(bank_txn.get("reference_id", "")).lower().strip()
    inv_ref = str(inv_txn.get("reference_id", "")).lower().strip()
    
    if bank_ref and inv_ref:
        if bank_ref == inv_ref:
            confidence += 0.2
        elif bank_ref in inv_ref or inv_ref in bank_ref:
            confidence += 0.1
    
    # Description similarity (10% weight)
    bank_desc = str(bank_txn.get("description", "")).lower()
    inv_desc = str(inv_txn.get("description", "")).lower()
    
    if bank_desc and inv_desc:
        # Simple word overlap
        bank_words = set(bank_desc.split())
        inv_words = set(inv_desc.split())
        common_words = bank_words & inv_words
        
        if len(bank_words | inv_words) > 0:
            overlap = len(common_words) / len(bank_words | inv_words)
            confidence += 0.1 * overlap
    
    return confidence


def detect_duplicates(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect potential duplicate transactions.
    Returns list of duplicate groups.
    """
    duplicates = []
    seen = {}
    
    for txn in transactions:
        # Create a key based on amount, date, and reference
        amount = round(float(txn.get("amount", 0)), 2)
        date = txn.get("txn_date")
        if isinstance(date, datetime):
            date = date.date().isoformat()
        elif isinstance(date, str):
            date = date[:10]  # Take just the date part
        
        key = f"{amount}|{date}"
        
        if key in seen:
            seen[key].append(txn)
        else:
            seen[key] = [txn]
    
    # Return groups with more than one transaction
    for key, group in seen.items():
        if len(group) > 1:
            duplicates.append({
                "key": key,
                "transactions": group,
                "count": len(group),
            })
    
    return duplicates


def detect_amount_mismatches(
    invoice_total: float,
    gst_declared: float,
    tolerance: float = 0.01,
) -> bool:
    """Check if there's a mismatch between invoice total and GST declared amount."""
    diff = abs(invoice_total - gst_declared)
    return diff > tolerance * max(invoice_total, gst_declared, 1)
