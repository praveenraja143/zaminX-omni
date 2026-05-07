"""
src/llm_engine.py
=================
Groq LLM Engine — Uses Llama 3.3 70B via Groq Cloud for:
  1. Legal text summarization (court orders → plain language)
  2. Multilingual translation (EN → Tamil/Hindi/Malayalam)
  3. Entity extraction (party names, judges, dates from legal text)
  4. Risk reasoning (explain why land is risky)
  5. Chargesheet summary generation

Groq API: https://console.groq.com/
Model: llama-3.3-70b-versatile
Free tier: ~6000 requests/day
"""

import json
import logging
from typing import Any, Dict, List, Optional

from src.config import settings

logger = logging.getLogger(__name__)

# Language display names for prompts
LANG_NAMES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "ml": "Malayalam",
}


class GroqLLMEngine:
    """
    Groq-powered LLM engine for legal intelligence.
    All methods are async-safe and use httpx for non-blocking calls.
    """

    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.is_available = bool(self.api_key)
        if not self.is_available:
            logger.warning("Groq API key not set. LLM features will use fallback.")

    async def _call_groq(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> Optional[str]:
        """Make an async call to Groq API."""
        if not self.is_available:
            return None

        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(self.base_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error("Groq API call failed: %s", e)
            return None

    async def summarize_legal_text(
        self, text: str, target_lang: str = "en"
    ) -> Dict[str, Any]:
        """
        Summarize court order text into plain language.
        Returns summary in requested language + key issue + urgency.
        """
        lang_name = LANG_NAMES.get(target_lang, "English")

        prompt = f"""You are a legal AI assistant specializing in Indian land law.
Summarize the following court order in simple {lang_name} that a rural farmer can understand.

Rules:
1. Maximum 2-3 sentences
2. Use simple words, avoid legal jargon
3. Mention: what the case is about, current status, and what happens next
4. Also extract: key_issue (1 line), urgency_level (low/medium/high)

Court Order Text:
{text[:2000]}

Respond in this exact JSON format:
{{
    "summary": "...",
    "summary_en": "...",
    "key_issue": "...",
    "urgency_level": "low|medium|high",
    "parties_involved": "..."
}}"""

        result = await self._call_groq(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        if result:
            try:
                # Try to parse JSON from the response
                cleaned = result.strip()
                if "```json" in cleaned:
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned:
                    cleaned = cleaned.split("```")[1].split("```")[0].strip()
                parsed = json.loads(cleaned)
                return {
                    "summary": parsed.get("summary", ""),
                    "summary_en": parsed.get("summary_en", parsed.get("summary", "")),
                    "key_issue": parsed.get("key_issue", ""),
                    "urgency_level": parsed.get("urgency_level", "low"),
                    "parties_involved": parsed.get("parties_involved", ""),
                    "method": "groq_llm",
                    "confidence": 0.85,
                }
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to parse Groq JSON response: %s", e)
                return {
                    "summary": result[:500],
                    "summary_en": result[:500],
                    "key_issue": "Land dispute",
                    "urgency_level": "medium",
                    "method": "groq_llm_raw",
                    "confidence": 0.6,
                }

        # Fallback: extractive summary
        return self._extractive_fallback(text)

    async def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> str:
        """Translate text between supported languages using Groq."""
        if source_lang == target_lang:
            return text

        src_name = LANG_NAMES.get(source_lang, "English")
        tgt_name = LANG_NAMES.get(target_lang, "English")

        prompt = f"""Translate the following text from {src_name} to {tgt_name}.
Keep it simple and natural. Do not add any explanation.

Text: {text[:1500]}

Translation:"""

        result = await self._call_groq(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=512,
        )
        return result or text

    async def extract_case_entities(self, text: str) -> Dict[str, Any]:
        """Extract structured entities from legal text."""
        prompt = f"""Extract the following information from this Indian court case text.
Return JSON format only.

Text: {text[:2000]}

Extract:
{{
    "petitioner": "name of petitioner",
    "respondent": "name of respondent",
    "judge_name": "name of judge",
    "case_number": "case number",
    "court_name": "court name",
    "case_type": "type of case",
    "filing_date": "date filed",
    "next_hearing": "next hearing date",
    "status": "active/disposed/pending",
    "survey_numbers": ["list of survey numbers mentioned"],
    "village_names": ["list of village names mentioned"]
}}"""

        result = await self._call_groq(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
        )

        if result:
            try:
                cleaned = result.strip()
                if "```json" in cleaned:
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned:
                    cleaned = cleaned.split("```")[1].split("```")[0].strip()
                return json.loads(cleaned)
            except (json.JSONDecodeError, KeyError):
                pass

        return {
            "petitioner": "", "respondent": "", "judge_name": "",
            "case_number": "", "court_name": "", "case_type": "Land Dispute",
            "status": "unknown",
        }

    async def assess_risk_reasoning(
        self,
        cases: List[Dict],
        land_info: Dict,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Generate human-readable risk assessment using LLM."""
        lang_name = LANG_NAMES.get(language, "English")

        cases_summary = json.dumps(cases[:5], default=str, indent=2)[:2000]
        land_summary = json.dumps(land_info, default=str)[:500]

        prompt = f"""You are a land litigation risk analyst for India.

Analyze the following court cases related to a land parcel and provide a risk assessment in {lang_name}.

Land Information:
{land_summary}

Court Cases:
{cases_summary}

Provide your assessment in this JSON format:
{{
    "risk_summary": "2-3 sentence summary of the risk in {lang_name}",
    "risk_level": "low|medium|high|critical",
    "risk_score": 0-100,
    "risk_factors": ["factor 1", "factor 2"],
    "recommendation": "what should the buyer do",
    "is_safe_to_buy": true/false
}}"""

        result = await self._call_groq(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        if result:
            try:
                cleaned = result.strip()
                if "```json" in cleaned:
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned:
                    cleaned = cleaned.split("```")[1].split("```")[0].strip()
                return json.loads(cleaned)
            except (json.JSONDecodeError, KeyError):
                pass

        return {
            "risk_summary": "Unable to generate AI risk assessment.",
            "risk_level": "medium",
            "risk_score": 50,
            "risk_factors": ["Analysis unavailable"],
            "recommendation": "Consult a lawyer for professional advice.",
            "is_safe_to_buy": False,
        }

    async def generate_chargesheet_summary(
        self, case_details: Dict, language: str = "en"
    ) -> str:
        """Generate a simplified chargesheet summary for a court case."""
        lang_name = LANG_NAMES.get(language, "English")
        case_str = json.dumps(case_details, default=str, indent=2)[:2000]

        prompt = f"""Generate a simple chargesheet summary in {lang_name} for this Indian court case.
The summary should be understandable by a common person.

Case Details:
{case_str}

Include:
1. Who filed the case and against whom
2. What the case is about
3. Current status
4. Key dates
5. What it means for the land buyer

Keep it under 200 words."""

        result = await self._call_groq(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512,
        )
        return result or "Chargesheet summary unavailable."

    @staticmethod
    def _extractive_fallback(text: str) -> Dict[str, Any]:
        """Simple extractive fallback when Groq is unavailable."""
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]

        keywords = [
            "petitioner", "respondent", "order", "directed", "dismissed",
            "disposed", "adjourned", "injunction", "property", "survey",
            "land", "boundary", "court", "judge", "hearing",
        ]

        def score(sent: str) -> float:
            lower = sent.lower()
            return sum(1 for kw in keywords if kw in lower)

        if sentences:
            scored = sorted(enumerate(sentences), key=lambda x: score(x[1]), reverse=True)
            top = sorted(scored[:2], key=lambda x: x[0])
            summary = ". ".join(s for _, s in top) + "."
        else:
            summary = text[:200]

        urgency = "low"
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["urgent", "immediate", "emergency", "stay order"]):
            urgency = "high"
        elif any(kw in text_lower for kw in ["next hearing", "adjourned", "posted for"]):
            urgency = "medium"

        return {
            "summary": summary,
            "summary_en": summary,
            "key_issue": "Land ownership/boundary dispute",
            "urgency_level": urgency,
            "method": "extractive_fallback",
            "confidence": 0.4,
        }


# Singleton instance
llm_engine = GroqLLMEngine()
