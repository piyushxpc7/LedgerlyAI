"""
ReconciliationGraph - Reconciliation workflow using LangGraph.
Nodes:
1. load_client_data - Load bank transactions, invoices, GST summaries
2. match_transactions - Rules-first matching with LLM fallback
3. detect_issues - Find mismatches, duplicates, missing invoices
4. score_severity - Rate issue severity
5. generate_working_papers - Create markdown tables + narrative
6. generate_compliance_summary - Draft narrative + issue list
7. export_pdf - Generate PDF from markdown
"""
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.transaction import Transaction, TransactionSource
from app.models.gst_summary import GSTSummary
from app.models.issue import Issue, IssueSeverity, IssueCategory, IssueStatus
from app.models.report import Report, ReportType
from app.models.reconciliation_run import ReconciliationRun, RunStatus
from app.models.client import Client
from app.services.transaction_matcher import match_transactions, detect_duplicates
from app.services.issue_detector import detect_issues, summarize_issues
from app.services.pdf_generator import generate_pdf_from_markdown
from app.workflows.llm_adapters import get_llm_adapter


class ReconciliationState(TypedDict):
    """State for the reconciliation workflow."""
    client_id: str
    run_id: str
    client_name: str
    bank_transactions: Optional[List[Dict]]
    invoice_transactions: Optional[List[Dict]]
    gst_summaries: Optional[List[Dict]]
    matches: Optional[List[Dict]]
    unmatched_bank: Optional[List[Dict]]
    unmatched_invoices: Optional[List[Dict]]
    duplicates: Optional[List[Dict]]
    issues: Optional[List[Dict]]
    issue_summary: Optional[Dict]
    working_papers_md: Optional[str]
    compliance_summary_md: Optional[str]
    working_papers_pdf: Optional[str]
    compliance_pdf: Optional[str]
    metrics: Optional[Dict]
    error: Optional[str]
    status: str


def load_client_data(state: ReconciliationState) -> ReconciliationState:
    """Load all client transactions, invoices, and GST data."""
    db = SessionLocal()
    try:
        client_id = UUID(state["client_id"])
        
        # Get client info
        client = db.query(Client).filter(Client.id == client_id).first()
        if client:
            state["client_name"] = client.name
        
        # Load bank transactions
        bank_txns = db.query(Transaction).filter(
            Transaction.client_id == client_id,
            Transaction.source == TransactionSource.BANK,
        ).all()
        
        state["bank_transactions"] = [
            {
                "id": str(t.id),
                "txn_date": t.txn_date.isoformat() if t.txn_date else None,
                "amount": float(t.amount) if t.amount else 0,
                "description": t.description,
                "counterparty": t.counterparty,
                "reference_id": t.reference_id,
            }
            for t in bank_txns
        ]
        
        # Load invoice transactions
        inv_txns = db.query(Transaction).filter(
            Transaction.client_id == client_id,
            Transaction.source == TransactionSource.INVOICE,
        ).all()
        
        state["invoice_transactions"] = [
            {
                "id": str(t.id),
                "txn_date": t.txn_date.isoformat() if t.txn_date else None,
                "amount": float(t.amount) if t.amount else 0,
                "description": t.description,
                "counterparty": t.counterparty,
                "reference_id": t.reference_id,
            }
            for t in inv_txns
        ]
        
        # Load GST summaries
        gst_summaries = db.query(GSTSummary).filter(
            GSTSummary.client_id == client_id,
        ).all()
        
        state["gst_summaries"] = [
            {
                "id": str(g.id),
                "period": g.period,
                "taxable_value": float(g.taxable_value) if g.taxable_value else 0,
                "tax_amount": float(g.tax_amount) if g.tax_amount else 0,
            }
            for g in gst_summaries
        ]
        
        state["status"] = "data_loaded"
    except Exception as e:
        state["error"] = f"Data loading failed: {str(e)}"
        state["status"] = "failed"
    finally:
        db.close()
    
    return state


def match_txns(state: ReconciliationState) -> ReconciliationState:
    """Match bank transactions with invoices."""
    try:
        bank_txns = state.get("bank_transactions", [])
        inv_txns = state.get("invoice_transactions", [])
        
        if not bank_txns or not inv_txns:
            state["matches"] = []
            state["unmatched_bank"] = bank_txns
            state["unmatched_invoices"] = inv_txns
            state["status"] = "matched"
            return state
        
        # Run matching algorithm
        matches, unmatched_bank, unmatched_invoices = match_transactions(
            bank_txns,
            inv_txns,
            date_tolerance_days=3,
            amount_tolerance_percent=0.01,
        )
        
        # Convert MatchResult to dict
        state["matches"] = [
            {
                "bank_txn_id": m.bank_txn_id,
                "invoice_txn_id": m.invoice_txn_id,
                "confidence": m.confidence,
                "match_type": m.match_type,
                "details": m.details,
            }
            for m in matches
        ]
        state["unmatched_bank"] = unmatched_bank
        state["unmatched_invoices"] = unmatched_invoices
        
        # Detect duplicates
        all_txns = bank_txns + inv_txns
        state["duplicates"] = detect_duplicates(all_txns)
        
        state["status"] = "matched"
    except Exception as e:
        state["error"] = f"Matching failed: {str(e)}"
        state["status"] = "failed"
    
    return state


def detect_all_issues(state: ReconciliationState) -> ReconciliationState:
    """Detect all types of issues from the reconciliation."""
    try:
        # Calculate invoice totals by period (simplified - use month)
        invoice_totals = {}
        for inv in state.get("invoice_transactions", []):
            if inv.get("txn_date"):
                # Extract month from date
                date_str = inv["txn_date"][:7]  # YYYY-MM
                invoice_totals[date_str] = invoice_totals.get(date_str, 0) + abs(inv.get("amount", 0))
        
        issues = detect_issues(
            matches=state.get("matches", []),
            unmatched_bank=state.get("unmatched_bank", []),
            unmatched_invoices=state.get("unmatched_invoices", []),
            duplicates=state.get("duplicates", []),
            gst_summaries=state.get("gst_summaries", []),
            invoice_totals=invoice_totals,
        )
        
        state["issues"] = issues
        state["issue_summary"] = summarize_issues(issues)
        state["status"] = "issues_detected"
    except Exception as e:
        state["error"] = f"Issue detection failed: {str(e)}"
        state["status"] = "failed"
    
    return state


def generate_working_papers(state: ReconciliationState) -> ReconciliationState:
    """Generate working papers markdown."""
    try:
        client_name = state.get("client_name", "Unknown Client")
        run_id = state["run_id"]
        
        md_parts = []
        md_parts.append(f"# Working Papers - {client_name}")
        md_parts.append(f"\n**Run ID:** {run_id}")
        md_parts.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_parts.append("\n")
        
        # Bank Transactions Summary
        bank_txns = state.get("bank_transactions", [])
        md_parts.append("## Bank Transactions Summary")
        if bank_txns:
            total_credits = sum(t["amount"] for t in bank_txns if t["amount"] > 0)
            total_debits = sum(abs(t["amount"]) for t in bank_txns if t["amount"] < 0)
            md_parts.append(f"\n- **Total Transactions:** {len(bank_txns)}")
            md_parts.append(f"- **Total Credits:** ₹{total_credits:,.2f}")
            md_parts.append(f"- **Total Debits:** ₹{total_debits:,.2f}")
        else:
            md_parts.append("\nNo bank transactions found.")
        
        # Invoice Summary
        inv_txns = state.get("invoice_transactions", [])
        md_parts.append("\n## Invoice Summary")
        if inv_txns:
            total_invoiced = sum(abs(t["amount"]) for t in inv_txns)
            md_parts.append(f"\n- **Total Invoices:** {len(inv_txns)}")
            md_parts.append(f"- **Total Invoiced Amount:** ₹{total_invoiced:,.2f}")
        else:
            md_parts.append("\nNo invoices found.")
        
        # Matching Results
        matches = state.get("matches", [])
        md_parts.append("\n## Reconciliation Results")
        md_parts.append(f"\n- **Matched Transactions:** {len(matches)}")
        md_parts.append(f"- **Unmatched Bank Entries:** {len(state.get('unmatched_bank', []))}")
        md_parts.append(f"- **Unmatched Invoices:** {len(state.get('unmatched_invoices', []))}")
        
        # Match Details Table
        if matches:
            md_parts.append("\n### Matched Transactions")
            md_parts.append("\n| Bank Amount | Invoice Amount | Confidence | Type |")
            md_parts.append("|-------------|----------------|------------|------|")
            for m in matches[:20]:  # Limit to 20 rows
                bank_amt = m["details"].get("bank_amount", 0)
                inv_amt = m["details"].get("invoice_amount", 0)
                md_parts.append(f"| ₹{bank_amt:,.2f} | ₹{inv_amt:,.2f} | {m['confidence']:.0%} | {m['match_type']} |")
        
        # Unmatched Bank Entries
        unmatched_bank = state.get("unmatched_bank", [])
        if unmatched_bank:
            md_parts.append("\n### Unmatched Bank Entries")
            md_parts.append("\n| Date | Amount | Description |")
            md_parts.append("|------|--------|-------------|")
            for t in unmatched_bank[:15]:
                md_parts.append(f"| {t.get('txn_date', 'N/A')[:10]} | ₹{t.get('amount', 0):,.2f} | {(t.get('description') or 'N/A')[:50]} |")
        
        # GST Summary
        gst = state.get("gst_summaries", [])
        if gst:
            md_parts.append("\n## GST Summary")
            md_parts.append("\n| Period | Taxable Value | Tax Amount |")
            md_parts.append("|--------|---------------|------------|")
            for g in gst:
                md_parts.append(f"| {g['period']} | ₹{g['taxable_value']:,.2f} | ₹{g['tax_amount']:,.2f} |")
        
        state["working_papers_md"] = "\n".join(md_parts)
        state["status"] = "working_papers_generated"
    except Exception as e:
        state["error"] = f"Working papers generation failed: {str(e)}"
        state["status"] = "failed"
    
    return state


def generate_compliance_summary(state: ReconciliationState) -> ReconciliationState:
    """Generate compliance summary with narrative."""
    try:
        client_name = state.get("client_name", "Unknown Client")
        issue_summary = state.get("issue_summary", {})
        issues = state.get("issues", [])
        
        md_parts = []
        md_parts.append(f"# Compliance Summary - {client_name}")
        md_parts.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_parts.append("\n")
        
        # Disclaimer
        md_parts.append("> ⚠️ **DISCLAIMER:** This summary is generated for preparation and workflow automation purposes only. ")
        md_parts.append("> It does NOT constitute tax filing, certification, or legal opinion.")
        md_parts.append("\n")
        
        # Executive Summary
        md_parts.append("## Executive Summary")
        
        total_issues = issue_summary.get("total_issues", 0)
        high_issues = issue_summary.get("by_severity", {}).get("high", 0)
        
        if total_issues == 0:
            md_parts.append("\n✅ No issues detected. All transactions reconciled successfully.")
        else:
            md_parts.append(f"\n⚠️ **{total_issues} issue(s) detected** requiring attention.")
            if high_issues > 0:
                md_parts.append(f"\n🔴 **{high_issues} high severity issue(s)** require immediate review.")
        
        # Issue Summary by Category
        md_parts.append("\n## Issue Summary")
        by_category = issue_summary.get("by_category", {})
        
        md_parts.append("\n| Category | Count |")
        md_parts.append("|----------|-------|")
        for cat, count in by_category.items():
            if count > 0:
                md_parts.append(f"| {cat.replace('_', ' ').title()} | {count} |")
        
        # Detailed Issues
        if issues:
            md_parts.append("\n## Detailed Issues")
            
            # Group by severity
            for severity in ["high", "med", "low"]:
                sev_issues = [i for i in issues if i.get("severity") and 
                             (i["severity"].value if hasattr(i["severity"], "value") else i["severity"]) == severity]
                
                if sev_issues:
                    severity_label = {"high": "🔴 High", "med": "🟡 Medium", "low": "🟢 Low"}[severity]
                    md_parts.append(f"\n### {severity_label} Severity")
                    
                    for idx, issue in enumerate(sev_issues[:10], 1):
                        category = issue.get("category")
                        if hasattr(category, "value"):
                            category = category.value
                        md_parts.append(f"\n**{idx}. {issue['title']}**")
                        md_parts.append(f"- Category: {category}")
                        details = issue.get("details_json", {})
                        if details.get("recommendation"):
                            md_parts.append(f"- Recommendation: {details['recommendation']}")
        
        # Try to add LLM-generated narrative
        try:
            llm = get_llm_adapter()
            prompt = f"""Based on the following reconciliation data, write a 2-paragraph executive narrative:

Client: {client_name}
Total Issues: {total_issues}
High Severity Issues: {high_issues}
Bank Transactions: {len(state.get('bank_transactions', []))}
Invoices: {len(state.get('invoice_transactions', []))}
Matched: {len(state.get('matches', []))}

Write a professional summary for CA review."""
            
            narrative = llm.generate(prompt)
            md_parts.insert(4, f"\n{narrative}\n")
        except Exception:
            pass  # Skip LLM narrative if unavailable
        
        state["compliance_summary_md"] = "\n".join(md_parts)
        state["status"] = "compliance_generated"
    except Exception as e:
        state["error"] = f"Compliance summary failed: {str(e)}"
        state["status"] = "failed"
    
    return state


def export_pdfs(state: ReconciliationState) -> ReconciliationState:
    """Generate PDF versions of reports."""
    db = SessionLocal()
    try:
        client_id = state["client_id"]
        run_id = state["run_id"]
        
        # Generate working papers PDF
        if state.get("working_papers_md"):
            wp_pdf = generate_pdf_from_markdown(
                state["working_papers_md"],
                f"wp-{run_id}",
                client_id,
            )
            state["working_papers_pdf"] = wp_pdf
        
        # Generate compliance summary PDF
        if state.get("compliance_summary_md"):
            cs_pdf = generate_pdf_from_markdown(
                state["compliance_summary_md"],
                f"cs-{run_id}",
                client_id,
            )
            state["compliance_pdf"] = cs_pdf
        
        # Calculate metrics
        bank_total = sum(abs(t["amount"]) for t in state.get("bank_transactions", []))
        invoice_total = sum(abs(t["amount"]) for t in state.get("invoice_transactions", []))
        
        state["metrics"] = {
            "bank_transactions": len(state.get("bank_transactions", [])),
            "invoice_transactions": len(state.get("invoice_transactions", [])),
            "matched_count": len(state.get("matches", [])),
            "unmatched_bank": len(state.get("unmatched_bank", [])),
            "unmatched_invoices": len(state.get("unmatched_invoices", [])),
            "issues_count": len(state.get("issues", [])),
            "bank_total": bank_total,
            "invoice_total": invoice_total,
        }
        
        # Persist reports and issues to database
        run = db.query(ReconciliationRun).filter(ReconciliationRun.id == UUID(run_id)).first()
        if run:
            # Save reports
            if state.get("working_papers_md"):
                wp_report = Report(
                    client_id=UUID(client_id),
                    run_id=UUID(run_id),
                    type=ReportType.WORKING_PAPERS,
                    content_md=state["working_papers_md"],
                    content_pdf_url=state.get("working_papers_pdf"),
                )
                db.add(wp_report)
            
            if state.get("compliance_summary_md"):
                cs_report = Report(
                    client_id=UUID(client_id),
                    run_id=UUID(run_id),
                    type=ReportType.COMPLIANCE_SUMMARY,
                    content_md=state["compliance_summary_md"],
                    content_pdf_url=state.get("compliance_pdf"),
                )
                db.add(cs_report)
            
            # Save issues
            for issue_data in state.get("issues", []):
                severity = issue_data["severity"]
                if isinstance(severity, str):
                    severity = IssueSeverity(severity)
                
                category = issue_data["category"]
                if isinstance(category, str):
                    category = IssueCategory(category)
                
                issue = Issue(
                    client_id=UUID(client_id),
                    run_id=UUID(run_id),
                    severity=severity,
                    category=category,
                    title=issue_data["title"],
                    details_json=issue_data.get("details_json"),
                    status=IssueStatus.OPEN,
                )
                db.add(issue)
            
            # Update run status
            run.status = RunStatus.COMPLETED
            run.ended_at = datetime.utcnow()
            run.metrics_json = state["metrics"]
            
            db.commit()
        
        state["status"] = "completed"
    except Exception as e:
        db.rollback()
        state["error"] = f"PDF export failed: {str(e)}"
        state["status"] = "failed"
    finally:
        db.close()
    
    return state


def should_continue(state: ReconciliationState) -> str:
    """Determine if we should continue or end due to error."""
    if state.get("status") == "failed":
        return "end"
    return "continue"


def create_reconciliation_graph() -> StateGraph:
    """Create the reconciliation workflow graph."""
    workflow = StateGraph(ReconciliationState)
    
    # Add nodes
    workflow.add_node("load_client_data", load_client_data)
    workflow.add_node("match_transactions", match_txns)
    workflow.add_node("detect_issues", detect_all_issues)
    workflow.add_node("generate_working_papers", generate_working_papers)
    workflow.add_node("generate_compliance_summary", generate_compliance_summary)
    workflow.add_node("export_pdfs", export_pdfs)
    
    # Set entry point
    workflow.set_entry_point("load_client_data")
    
    # Add edges
    workflow.add_conditional_edges(
        "load_client_data",
        should_continue,
        {"continue": "match_transactions", "end": END}
    )
    workflow.add_conditional_edges(
        "match_transactions",
        should_continue,
        {"continue": "detect_issues", "end": END}
    )
    workflow.add_conditional_edges(
        "detect_issues",
        should_continue,
        {"continue": "generate_working_papers", "end": END}
    )
    workflow.add_conditional_edges(
        "generate_working_papers",
        should_continue,
        {"continue": "generate_compliance_summary", "end": END}
    )
    workflow.add_conditional_edges(
        "generate_compliance_summary",
        should_continue,
        {"continue": "export_pdfs", "end": END}
    )
    workflow.add_edge("export_pdfs", END)
    
    return workflow.compile()


def run_reconciliation(client_id: str, run_id: str) -> Dict[str, Any]:
    """Run the reconciliation workflow for a client."""
    db = SessionLocal()
    try:
        # Update run status to running
        run = db.query(ReconciliationRun).filter(ReconciliationRun.id == UUID(run_id)).first()
        if run:
            run.status = RunStatus.RUNNING
            run.started_at = datetime.utcnow()
            db.commit()
        
        # Prepare initial state
        initial_state: ReconciliationState = {
            "client_id": client_id,
            "run_id": run_id,
            "client_name": "",
            "bank_transactions": None,
            "invoice_transactions": None,
            "gst_summaries": None,
            "matches": None,
            "unmatched_bank": None,
            "unmatched_invoices": None,
            "duplicates": None,
            "issues": None,
            "issue_summary": None,
            "working_papers_md": None,
            "compliance_summary_md": None,
            "working_papers_pdf": None,
            "compliance_pdf": None,
            "metrics": None,
            "error": None,
            "status": "started",
        }
        
        # Run workflow
        graph = create_reconciliation_graph()
        final_state = graph.invoke(initial_state)
        
        # Update run status on failure
        if final_state.get("status") == "failed":
            run = db.query(ReconciliationRun).filter(ReconciliationRun.id == UUID(run_id)).first()
            if run:
                run.status = RunStatus.FAILED
                run.ended_at = datetime.utcnow()
                db.commit()
        
        return {
            "client_id": client_id,
            "run_id": run_id,
            "status": final_state.get("status"),
            "metrics": final_state.get("metrics"),
            "issue_count": len(final_state.get("issues") or []),
            "error": final_state.get("error"),
        }
    finally:
        db.close()
