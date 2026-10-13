"""Resolve saved product values against reusable description-template fields."""

import re

from app.core.markdown import escape_plain_template_value

FIELD_KEY_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_]{0,63}")


def prepare_template_field_values(fields_schema: list, saved_values: object) -> dict[str, str]:
	"""Apply defaults, validate choices, and safely prepare values for Markdown rendering."""
	values = saved_values if isinstance(saved_values, dict) else {}
	prepared = {}
	for field in fields_schema or []:
		if not isinstance(field, dict):
			continue
		key = field.get("key")
		if not isinstance(key, str) or not FIELD_KEY_RE.fullmatch(key):
			continue

		value = values.get(key, field.get("default", ""))
		if field.get("type") == "select":
			choices = field.get("choices", [])
			choices = choices if isinstance(choices, list) else []
			if key in values and value == "" and field.get("required") is not True:
				pass
			elif value not in choices:
				default = field.get("default", "")
				if default in choices:
					value = default
				elif field.get("required") is True and choices:
					value = choices[0]
				else:
					value = ""

		if field.get("markdown") is not True:
			value = escape_plain_template_value(value)
		prepared[key] = value
	return prepared
