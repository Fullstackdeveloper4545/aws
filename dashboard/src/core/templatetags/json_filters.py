from django import template
import json

register = template.Library()

@register.filter
def json_format(value):
    """
    Format a Python object as properly formatted JSON with double quotes
    """
    try:
        # If value is already a string that looks like JSON, parse and re-format it
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                # If it's not valid JSON, return as is
                return value
        
        # If value is a Python object, convert to JSON
        return json.dumps(value, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        # If conversion fails, return the original value as string
        return str(value) 