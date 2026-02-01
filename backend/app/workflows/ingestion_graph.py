"""
IngestionGraph - Document ingestion workflow using LangGraph.
Nodes:
1. classify_document - Classify document type
2. extract_text - Extract text from PDF/CSV/XLSX
3. normalize_fields - Standardize dates, amounts, references
4. extract_structured - Extract structured data
5. chunk_and_embed - Create chunks with embeddings
6. persist_records - Write transactions/GST summaries
7. summarize_document - Generate document summary
"""
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import json

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.document import Document, DocumentType, DocumentStatus
from app.models.doc_chunk import DocChunk
from app.models.transaction import Transaction, TransactionSource
from app.models.gst_summary import GSTSummary
from app.services.document_parser import (
    extract_document_content,
    parse_bank_statement_csv,
    parse_invoice_csv,
)
from app.workflows.llm_adapters import get_llm_adapter, classify_document_heuristic


class IngestionState(TypedDict):
    """State for the ingestion workflow."""
    document_id: str
    document_path: str
    filename: str
    document_type: Optional[str]
    raw_text: Optional[str]
    raw_data: Optional[List[Dict]]
    normalized_data: Optional[List[Dict]]
    structured_records: Optional[List[Dict]]
    chunks: Optional[List[Dict]]
    embeddings: Optional[List[List[float]]]
    summary: Optional[str]
    error: Optional[str]
    status: str


def classify_document(state: IngestionState) -> IngestionState:
    """Classify the document type using heuristics and LLM fallback."""
    try:
        # First try heuristic classification
        doc_type = classify_document_heuristic(
            state["filename"],
            state.get("raw_text", "")[:500] or ""
        )
        
        if doc_type == "other":
            # Try LLM for better classification
            try:
                llm = get_llm_adapter()
                prompt = f"""Classify this document into one of: bank, invoice, gst, tds, other.

Filename: {state["filename"]}
Content sample: {(state.get("raw_text", "") or "")[:500]}

Respond with just the category name."""
                
                result = llm.generate(prompt).strip().lower()
                if result in ["bank", "invoice", "gst", "tds"]:
                    doc_type = result
            except Exception:
                pass  # Stick with heuristic result
        
        state["document_type"] = doc_type
        state["status"] = "classified"
    except Exception as e:
        state["error"] = f"Classification failed: {str(e)}"
        state["status"] = "failed"
    
    return state


def extract_text(state: IngestionState) -> IngestionState:
    """Extract text and data from the document."""
    try:
        content = extract_document_content(state["document_path"])
        state["raw_text"] = content.get("text", "")
        state["raw_data"] = content.get("data")
        state["status"] = "extracted"
    except Exception as e:
        state["error"] = f"Extraction failed: {str(e)}"
        state["status"] = "failed"
    
    return state


def normalize_fields(state: IngestionState) -> IngestionState:
    """Normalize dates, amounts, and references in the data."""
    try:
        if not state.get("raw_data"):
            state["normalized_data"] = None
            state["status"] = "normalized"
            return state
        
        normalized = []
        for record in state["raw_data"]:
            norm_record = {}
            for key, value in record.items():
                # Normalize amounts
                if "amount" in key.lower() or "total" in key.lower():
                    try:
                        clean_val = str(value).replace(",", "").replace("₹", "").strip()
                        if clean_val and clean_val != "-" and clean_val.lower() != "nan":
                            norm_record[key] = float(clean_val)
                        else:
                            norm_record[key] = None
                    except (ValueError, TypeError):
                        norm_record[key] = None
                else:
                    norm_record[key] = value
            
            normalized.append(norm_record)
        
        state["normalized_data"] = normalized
        state["status"] = "normalized"
    except Exception as e:
        state["error"] = f"Normalization failed: {str(e)}"
        state["status"] = "failed"
    
    return state


def extract_structured(state: IngestionState) -> IngestionState:
    """Extract structured records based on document type."""
    try:
        doc_type = state.get("document_type", "other")
        data = state.get("normalized_data") or state.get("raw_data")
        
        if not data:
            # For PDFs without structured data, try LLM extraction
            if state.get("raw_text") and doc_type in ["bank", "invoice"]:
                try:
                    llm = get_llm_adapter()
                    prompt = f"""Extract transactions from this {doc_type} document.

Document content:
{state["raw_text"][:3000]}

Return a JSON array with objects containing: date, amount, description, reference_id, counterparty.
Only return valid JSON array."""
                    
                    result = llm.generate_json(prompt)
                    if isinstance(result, list):
                        state["structured_records"] = result
                except Exception:
                    state["structured_records"] = []
            else:
                state["structured_records"] = []
        else:
            # Parse structured data based on type
            if doc_type == "bank":
                state["structured_records"] = parse_bank_statement_csv(data)
            elif doc_type == "invoice":
                state["structured_records"] = parse_invoice_csv(data)
            else:
                state["structured_records"] = data
        
        state["status"] = "structured"
    except Exception as e:
        state["error"] = f"Structured extraction failed: {str(e)}"
        state["status"] = "failed"
    
    return state


def chunk_and_embed(state: IngestionState) -> IngestionState:
    """Create text chunks and generate embeddings."""
    try:
        text = state.get("raw_text", "")
        if not text:
            state["chunks"] = []
            state["embeddings"] = []
            state["status"] = "chunked"
            return state
        
        # Simple chunking by paragraphs/lines (up to ~500 chars each)
        chunks = []
        current_chunk = ""
        
        for line in text.split("\n"):
            if len(current_chunk) + len(line) < 500:
                current_chunk += line + "\n"
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = line + "\n"
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Limit to first 50 chunks to avoid excessive embedding calls
        chunks = chunks[:50]
        
        # Generate embeddings
        embeddings = []
        if chunks:
            try:
                llm = get_llm_adapter()
                embeddings = llm.get_embeddings(chunks)
            except Exception:
                # Fallback: use empty embeddings
                embeddings = [[0.0] * 1024 for _ in chunks]
        
        state["chunks"] = [{"text": c, "index": i} for i, c in enumerate(chunks)]
        state["embeddings"] = embeddings
        state["status"] = "chunked"
    except Exception as e:
        state["error"] = f"Chunking failed: {str(e)}"
        state["status"] = "failed"
    
    return state


def persist_records(state: IngestionState) -> IngestionState:
    """Persist extracted records to the database."""
    db = SessionLocal()
    try:
        document_id = state["document_id"]
        
        # Get document to find client_id
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            state["error"] = "Document not found"
            state["status"] = "failed"
            return state
        
        # Update document type
        doc_type = state.get("document_type", "other")
        document.type = DocumentType(doc_type)
        
        # Save chunks with embeddings
        if state.get("chunks") and state.get("embeddings"):
            for chunk, embedding in zip(state["chunks"], state["embeddings"]):
                doc_chunk = DocChunk(
                    document_id=document_id,
                    chunk_text=chunk["text"],
                    metadata_json={"index": chunk["index"]},
                    embedding=json.dumps(embedding),
                )
                db.add(doc_chunk)
        
        # Save transactions
        records = state.get("structured_records", [])
        for record in records:
            safe_record = {k: v.isoformat() if isinstance(v, datetime) else v for k, v in record.items()}
            if doc_type == "bank":
                txn = Transaction(
                    client_id=document.client_id,
                    document_id=document_id,
                    source=TransactionSource.BANK,
                    txn_date=record.get("txn_date") or datetime.now(),
                    amount=record.get("amount", 0),
                    description=record.get("description"),
                    counterparty=record.get("counterparty"),
                    reference_id=record.get("reference_id"),
                    meta_json=safe_record,
                )
                db.add(txn)
            elif doc_type == "invoice":
                txn = Transaction(
                    client_id=document.client_id,
                    document_id=document_id,
                    source=TransactionSource.INVOICE,
                    txn_date=record.get("txn_date") or datetime.now(),
                    amount=record.get("amount", 0),
                    description=record.get("description"),
                    counterparty=record.get("counterparty"),
                    reference_id=record.get("reference_id"),
                    meta_json=safe_record,
                )
                db.add(txn)
            elif doc_type == "gst":
                gst = GSTSummary(
                    client_id=document.client_id,
                    document_id=document_id,
                    period=record.get("period", "Unknown"),
                    taxable_value=record.get("taxable_value", 0),
                    tax_amount=record.get("tax_amount", 0),
                    meta_json=safe_record,
                )
                db.add(gst)
        
        db.commit()
        state["status"] = "persisted"
    except Exception as e:
        db.rollback()
        state["error"] = f"Persistence failed: {str(e)}"
        state["status"] = "failed"
    finally:
        db.close()
    
    return state


def summarize_document(state: IngestionState) -> IngestionState:
    """Generate a summary of the document."""
    db = SessionLocal()
    try:
        # Generate summary
        summary_parts = []
        summary_parts.append(f"Document Type: {state.get('document_type', 'unknown')}")
        
        records = state.get("structured_records", [])
        if records:
            summary_parts.append(f"Records extracted: {len(records)}")
            
            # Calculate totals
            total_amount = sum(abs(r.get("amount", 0)) for r in records if r.get("amount"))
            if total_amount > 0:
                summary_parts.append(f"Total amount: ₹{total_amount:,.2f}")
        
        if state.get("chunks"):
            summary_parts.append(f"Text chunks created: {len(state['chunks'])}")
        
        summary = " | ".join(summary_parts)
        
        # Try LLM summary for richer description
        if state.get("raw_text"):
            try:
                llm = get_llm_adapter()
                prompt = f"""Summarize this document in 2-3 sentences:

{state["raw_text"][:2000]}"""
                llm_summary = llm.generate(prompt)
                summary = llm_summary[:500] + "\n\n" + summary
            except Exception:
                pass
        
        state["summary"] = summary
        
        # Update document with summary
        document_id = state["document_id"]
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.meta = {
                "summary": summary,
                "record_count": len(records),
                "chunk_count": len(state.get("chunks", [])),
                "processed_at": datetime.utcnow().isoformat(),
            }
            document.status = DocumentStatus.PROCESSED
            db.commit()
        
        state["status"] = "completed"
    except Exception as e:
        db.rollback()
        state["error"] = f"Summarization failed: {str(e)}"
        state["status"] = "failed"
    finally:
        db.close()
    
    return state


def should_continue(state: IngestionState) -> str:
    """Determine if we should continue or end due to error."""
    if state.get("status") == "failed":
        return "end"
    return "continue"


def create_ingestion_graph() -> StateGraph:
    """Create the ingestion workflow graph."""
    workflow = StateGraph(IngestionState)
    
    # Add nodes
    workflow.add_node("extract_text", extract_text)
    workflow.add_node("classify_document", classify_document)
    workflow.add_node("normalize_fields", normalize_fields)
    workflow.add_node("extract_structured", extract_structured)
    workflow.add_node("chunk_and_embed", chunk_and_embed)
    workflow.add_node("persist_records", persist_records)
    workflow.add_node("summarize_document", summarize_document)
    
    # Set entry point
    workflow.set_entry_point("extract_text")
    
    # Add edges
    workflow.add_conditional_edges(
        "extract_text",
        should_continue,
        {"continue": "classify_document", "end": END}
    )
    workflow.add_conditional_edges(
        "classify_document",
        should_continue,
        {"continue": "normalize_fields", "end": END}
    )
    workflow.add_conditional_edges(
        "normalize_fields",
        should_continue,
        {"continue": "extract_structured", "end": END}
    )
    workflow.add_conditional_edges(
        "extract_structured",
        should_continue,
        {"continue": "chunk_and_embed", "end": END}
    )
    workflow.add_conditional_edges(
        "chunk_and_embed",
        should_continue,
        {"continue": "persist_records", "end": END}
    )
    workflow.add_conditional_edges(
        "persist_records",
        should_continue,
        {"continue": "summarize_document", "end": END}
    )
    workflow.add_edge("summarize_document", END)
    
    return workflow.compile()


def run_ingestion(document_id: str) -> Dict[str, Any]:
    """Run the ingestion workflow for a document."""
    db = SessionLocal()
    try:
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return {"error": "Document not found", "status": "failed"}
        
        # Prepare initial state
        initial_state: IngestionState = {
            "document_id": document_id,
            "document_path": document.storage_url,
            "filename": document.filename,
            "document_type": None,
            "raw_text": None,
            "raw_data": None,
            "normalized_data": None,
            "structured_records": None,
            "chunks": None,
            "embeddings": None,
            "summary": None,
            "error": None,
            "status": "started",
        }
        
        # Run workflow
        graph = create_ingestion_graph()
        final_state = graph.invoke(initial_state)
        
        # Update document status on failure
        if final_state.get("status") == "failed":
            document.status = DocumentStatus.FAILED
            document.meta = {"error": final_state.get("error")}
            db.commit()
        
        return {
            "document_id": document_id,
            "status": final_state.get("status"),
            "document_type": final_state.get("document_type"),
            "records_count": len(final_state.get("structured_records") or []),
            "chunks_count": len(final_state.get("chunks") or []),
            "summary": final_state.get("summary"),
            "error": final_state.get("error"),
        }
    finally:
        db.close()
