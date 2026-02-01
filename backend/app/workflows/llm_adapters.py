"""
LLM Adapters for provider-agnostic LLM integration.
Supports Mistral and Anthropic.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json

from app.config import get_settings

settings = get_settings()


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters."""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a text response from the LLM."""
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate a JSON response from the LLM."""
        pass
    
    @abstractmethod
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts."""
        pass


class MistralAdapter(LLMAdapter):
    """Adapter for Mistral AI API."""
    
    def __init__(self):
        from mistralai import Mistral
        self.client = Mistral(api_key=settings.mistral_api_key)
        self.model = settings.mistral_model
        self.embedding_model = settings.mistral_embedding_model
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.complete(
            model=self.model,
            messages=messages,
        )
        return response.choices[0].message.content
    
    def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        json_system = (system_prompt or "") + "\n\nRespond only with valid JSON, no markdown or explanation."
        response = self.generate(prompt, json_system)
        
        # Try to extract JSON from response
        try:
            # Remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"raw_response": response, "error": "Failed to parse JSON"}
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model=self.embedding_model,
            inputs=texts,
        )
        return [item.embedding for item in response.data]


class AnthropicAdapter(LLMAdapter):
    """Adapter for Anthropic Claude API."""
    
    def __init__(self):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt or "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    
    def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        json_system = (system_prompt or "") + "\n\nRespond only with valid JSON, no markdown or explanation."
        response = self.generate(prompt, json_system)
        
        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"raw_response": response, "error": "Failed to parse JSON"}
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        # Anthropic doesn't have native embeddings, use sentence-transformers fallback
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = model.encode(texts)
        return embeddings.tolist()


def get_llm_adapter() -> LLMAdapter:
    """Get the configured LLM adapter based on settings."""
    provider = settings.llm_provider
    
    if provider == "mistral":
        if not settings.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY is required when using Mistral provider")
        return MistralAdapter()
    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider")
        return AnthropicAdapter()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# Fallback deterministic functions for when LLM is not available
def classify_document_heuristic(filename: str, text_sample: str) -> str:
    """Classify document type using heuristics."""
    filename_lower = filename.lower()
    text_lower = text_sample.lower()[:1000]
    
    # Bank statement indicators
    bank_indicators = ["bank statement", "account statement", "balance", "withdrawal", "deposit", "debit", "credit"]
    if any(ind in filename_lower or ind in text_lower for ind in bank_indicators):
        return "bank"
    
    # Invoice indicators
    invoice_indicators = ["invoice", "bill", "tax invoice", "proforma"]
    if any(ind in filename_lower or ind in text_lower for ind in invoice_indicators):
        return "invoice"
    
    # GST indicators
    gst_indicators = ["gst", "gstin", "gstr", "return", "govt", "government"]
    if any(ind in filename_lower or ind in text_lower for ind in gst_indicators):
        return "gst"
    
    # TDS indicators
    tds_indicators = ["tds", "26as", "form 16", "challan"]
    if any(ind in filename_lower or ind in text_lower for ind in tds_indicators):
        return "tds"
    
    return "other"
