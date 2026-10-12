import re
from pydantic import BaseModel


def extract_json_text(text: str):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    if m:
        return m.group(1).strip()
    a, b = text.find("{"), text.rfind("}")
    return text[a : b + 1] if a != -1 and b > a else text


def parse_structured_output(text: str, schema: type[BaseModel]):
    return schema.model_validate_json(extract_json_text(text))
