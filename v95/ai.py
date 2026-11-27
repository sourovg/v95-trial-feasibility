"""Optional AI layer (Claude). Everything works without it: callers fall back to rules.

Turned on when the `anthropic` package is installed and ANTHROPIC_API_KEY is set.
Set COHORTIA_AI=0 to force rules only.
"""
import json
import os

MODEL = os.environ.get("COHORTIA_MODEL", "claude-opus-5-5")

try:  # optional dependency
    import anthropic  # type: ignore
except Exception:  # pragma: no cover
    anthropic = None


def available():
    return bool(anthropic and os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("COHORTIA_AI", "1") != "0")


def status():
    if available():
        return "on", f"Claude ({MODEL}) helps read requests, adds tailored survey questions and drafts the summary. Rules still run and are shown."
    return "off", "Rules only. Install the anthropic package and set ANTHROPIC_API_KEY to add Claude."


def _json_call(system, user, schema, max_tokens=4000):
    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=MODEL, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        if msg.stop_reason in ("refusal", "max_tokens"):
            return None
        text = next((b.text for b in msg.content if getattr(b, "type", "") == "text"), "")
        return json.loads(text)
    except Exception:
        return None


def extract_request(text):
    from . import catalog
    schema = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "indication": {"type": "string", "enum": list(catalog.INDICATIONS)},
            "study_type": {"type": "string", "enum": [k for k, _ in catalog.STUDY_TYPES]},
            "design": {"type": "string", "enum": catalog.DESIGNS},
            "setting": {"type": "string", "enum": catalog.SETTINGS},
            "population": {"type": "string", "enum": catalog.POPULATIONS},
            "countries": {"type": "array", "items": {"type": "string", "enum": catalog.COUNTRIES}},
            "objective": {"type": "string"},
            "endpoints": {"type": "string"},
            "keywords": {"type": "string"},
        },
        "required": ["indication", "study_type", "design", "setting", "population", "countries", "objective", "endpoints", "keywords"],
    }
    return _json_call(
        "You turn clinical feasibility requests (RFPs) into structured fields. Choose only from the allowed values. "
        "If the request does not say something, pick the most likely value and keep objective/endpoints short.",
        "Request:\n" + (text or "")[:6000], schema)


def extra_questions(req, existing_titles):
    schema = {"type": "object", "additionalProperties": False, "properties": {"questions": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {"pillar": {"type": "string", "enum": ["interest", "practice", "design", "patients", "capabilities"]},
                       "text": {"type": "string"}, "kind": {"type": "string", "enum": ["single", "multi", "number", "scale", "text"]},
                       "options": {"type": "array", "items": {"type": "string"}}},
        "required": ["pillar", "text", "kind", "options"]}}}, "required": ["questions"]}
    out = _json_call(
        "You design short investigator feasibility questionnaires for clinical studies. Add at most 4 questions that are specific "
        "to this request and not already covered. No questions about individual patients. Plain wording.",
        json.dumps({"request": {k: req.get(k) for k in ("title", "description", "objective", "endpoints", "study_type", "design", "setting")},
                    "already_asked": existing_titles})[:8000], schema)
    return (out or {}).get("questions", [])[:4]


def summary(facts):
    schema = {"type": "object", "additionalProperties": False,
              "properties": {"summary": {"type": "string"}}, "required": ["summary"]}
    out = _json_call(
        "You write the executive summary of a clinical study feasibility report for a pharma medical/clinical team. "
        "Use only the facts given. 120 words or fewer. Say what is estimate vs fact. No hype.",
        json.dumps(facts)[:12000], schema, max_tokens=1500)
    return (out or {}).get("summary")
