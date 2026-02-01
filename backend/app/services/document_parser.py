import os
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from pypdf import PdfReader


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}")


def extract_data_from_csv(file_path: str) -> List[Dict[str, Any]]:
    """Extract data from a CSV file as a list of dictionaries."""
    try:
        df = pd.read_csv(file_path)
        # Clean column names
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        return df.to_dict(orient="records")
    except Exception as e:
        raise ValueError(f"Failed to extract data from CSV: {e}")


def extract_data_from_xlsx(file_path: str, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Extract data from an Excel file as a list of dictionaries."""
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name or 0)
        # Clean column names
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        return df.to_dict(orient="records")
    except Exception as e:
        raise ValueError(f"Failed to extract data from Excel: {e}")


def get_file_extension(file_path: str) -> str:
    """Get the lowercase file extension."""
    return os.path.splitext(file_path)[1].lower().lstrip(".")


def extract_document_content(file_path: str) -> Dict[str, Any]:
    """
    Extract content from a document based on its type.
    Returns a dict with 'text' and/or 'data' keys.
    """
    ext = get_file_extension(file_path)
    
    if ext == "pdf":
        text = extract_text_from_pdf(file_path)
        return {"text": text, "data": None, "format": "pdf"}
    
    elif ext == "csv":
        data = extract_data_from_csv(file_path)
        # Also create a text representation
        text = format_data_as_text(data)
        return {"text": text, "data": data, "format": "csv"}
    
    elif ext in ["xlsx", "xls"]:
        data = extract_data_from_xlsx(file_path)
        text = format_data_as_text(data)
        return {"text": text, "data": data, "format": "excel"}
    
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def format_data_as_text(data: List[Dict[str, Any]]) -> str:
    """Convert structured data to readable text format."""
    if not data:
        return ""
    
    lines = []
    for i, row in enumerate(data, 1):
        row_text = " | ".join(f"{k}: {v}" for k, v in row.items() if v is not None)
        lines.append(f"Row {i}: {row_text}")
    
    return "\n".join(lines)


def parse_bank_statement_csv(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parse bank statement CSV data into standardized transaction format.
    Handles common bank statement column variations.
    """
    transactions = []
    
    # Common column name mappings
    date_columns = ["date", "txn_date", "transaction_date", "value_date", "posting_date"]
    amount_columns = ["amount", "debit", "credit", "withdrawal", "deposit", "transaction_amount"]
    desc_columns = ["description", "particulars", "narration", "details", "remarks"]
    ref_columns = ["reference", "ref_no", "reference_id", "cheque_no", "utr", "transaction_id"]
    
    for row in data:
        txn = {}
        
        # Find date
        for col in date_columns:
            if col in row and row[col]:
                txn["txn_date"] = parse_date(str(row[col]))
                break
        
        # Find amount
        amount = 0
        for col in amount_columns:
            if col in row and row[col]:
                try:
                    val = str(row[col]).replace(",", "").replace("₹", "").strip()
                    if val and val != "-":
                        amount = float(val)
                        # Handle debit (negative) vs credit (positive)
                        if col in ["debit", "withdrawal"] and amount > 0:
                            amount = -amount
                        break
                except (ValueError, TypeError):
                    continue
        txn["amount"] = amount
        
        # Find description
        for col in desc_columns:
            if col in row and row[col]:
                txn["description"] = str(row[col]).strip()
                break
        
        # Find reference
        for col in ref_columns:
            if col in row and row[col]:
                txn["reference_id"] = str(row[col]).strip()
                break
        
        if txn.get("txn_date") and txn.get("amount"):
            txn["source"] = "bank"
            transactions.append(txn)
    
    return transactions


def parse_invoice_csv(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parse invoice CSV data into standardized transaction format.
    """
    transactions = []
    
    # Common column name mappings for invoices
    date_columns = ["date", "invoice_date", "bill_date"]
    amount_columns = ["amount", "total", "invoice_amount", "grand_total", "net_amount"]
    desc_columns = ["description", "particulars", "item", "product"]
    ref_columns = ["invoice_no", "invoice_number", "bill_no", "reference"]
    party_columns = ["party", "customer", "vendor", "buyer", "seller", "counterparty"]
    
    for row in data:
        txn = {}
        
        # Find date
        for col in date_columns:
            if col in row and row[col]:
                txn["txn_date"] = parse_date(str(row[col]))
                break
        
        # Find amount
        for col in amount_columns:
            if col in row and row[col]:
                try:
                    val = str(row[col]).replace(",", "").replace("₹", "").strip()
                    if val and val != "-":
                        txn["amount"] = float(val)
                        break
                except (ValueError, TypeError):
                    continue
        
        # Find description
        for col in desc_columns:
            if col in row and row[col]:
                txn["description"] = str(row[col]).strip()
                break
        
        # Find reference
        for col in ref_columns:
            if col in row and row[col]:
                txn["reference_id"] = str(row[col]).strip()
                break
        
        # Find counterparty
        for col in party_columns:
            if col in row and row[col]:
                txn["counterparty"] = str(row[col]).strip()
                break
        
        if txn.get("txn_date") and txn.get("amount"):
            txn["source"] = "invoice"
            transactions.append(txn)
    
    return transactions


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats to datetime."""
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d-%B-%Y",
    ]
    
    date_str = date_str.strip()
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None
