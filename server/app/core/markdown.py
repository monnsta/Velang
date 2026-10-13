"""Safe Markdown rendering with sandboxed template variables and reusable accordions."""

import html as html_module
import re

import bleach
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from markdown_it import MarkdownIt

TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {
	"p", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr", "img",
	"ul", "ol", "li", "strong", "em", "blockquote", "code", "pre",
	"table", "thead", "tbody", "tr", "th", "td", "details", "summary", "div", "span",
}
ATTRS = {
	"a": ["href", "title", "target", "rel"],
	"img": ["src", "alt", "title", "loading"],
	"details": ["class", "open"],
	"summary": ["class"],
	"div": ["class"],
	"*": ["class"],
}
COLLAPSE_RE = re.compile(
	r"(?ms)^:::\s*collapse(?P<open>\s+open)?\s+(?P<title>[^\n]+)\n(?P<body>.*?)^:::\s*$",
	re.IGNORECASE,
)
UNSAFE_LINK_RE = re.compile(
	r"\[([^\]]*)\]\(\s*(?:javascript|vbscript|data)\s*:.*?\)",
	re.IGNORECASE,
)
EVENT_ATTRIBUTE_RE = re.compile(
	r"\bon[a-z]+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)",
	re.IGNORECASE,
)
FIELD_VALUE_RE = re.compile(
	r"{{\s*product\.fields\.([A-Za-z][A-Za-z0-9_]{0,63})\s*}}"
)


def escape_plain_template_value(value: object) -> str:
	"""Escape Markdown syntax while preserving deliberate line breaks in plain fields."""
	text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
	escaped = re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", text)
	return escaped.replace("\n", "  \n")


def _render_markdown(source: str, depth: int = 0) -> str:
	"""Render Markdown and turn ``::: collapse Title`` blocks into native accordions."""
	if depth > 8:
		return "<p>Accordion nesting is too deep.</p>"
	blocks: dict[str, str] = {}

	def replace_collapse(match: re.Match) -> str:
		key = f"VELANGCOLLAPSEPLACEHOLDER{len(blocks)}TOKEN"
		# Accordion labels are plain text. Strip tag-like snippets and event-handler
		# attributes before escaping so payload fragments cannot leak into the UI.
		title_text = EVENT_ATTRIBUTE_RE.sub("", match.group("title"))
		title_text = re.sub(r"<[^>]*>", "", title_text).strip()
		title = html_module.escape(title_text)
		inner = _render_markdown(match.group("body").strip(), depth + 1)
		open_attribute = " open" if match.group("open") else ""
		blocks[key] = (
			f'<details class="accordion"{open_attribute}>'
			f'<summary><span class="accordion-title">{title}</span></summary>'
			f'<div class="accordion-body">{inner}</div></details>'
		)
		return key

	rendered = COLLAPSE_RE.sub(replace_collapse, source or "")
	# Remove unsafe links and event handlers before parsing. Raw HTML remains disabled
	# by CommonMark, and the final Bleach pass enforces the element/attribute allowlist.
	rendered = UNSAFE_LINK_RE.sub(r"\1", rendered)
	rendered = EVENT_ATTRIBUTE_RE.sub("", rendered)
	output = MarkdownIt("commonmark", {"html": False, "linkify": True}).render(rendered)
	for key, markup in blocks.items():
		output = output.replace(f"<p>{key}</p>", markup).replace(key, markup)
	return output


def _omit_empty_field_lines(source: str, context: dict) -> str:
	"""Omit complete Markdown lines that depend only on empty template fields."""
	product = context.get("product", {}) if isinstance(context, dict) else {}
	fields = product.get("fields", {}) if isinstance(product, dict) else {}
	if not isinstance(fields, dict) or not fields:
		return source

	lines = []
	for line in (source or "").splitlines():
		keys = FIELD_VALUE_RE.findall(line)
		if keys and all(not str(fields.get(key, "") or "").strip() for key in keys):
			continue
		lines.append(line)

	cleaned = "\n".join(lines)
	return re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", cleaned).strip("\n")


def render(source: str, context: dict | None = None) -> str:
	"""Render Markdown with sandboxed Jinja variables and sanitize the result."""
	env = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)
	template_context = {
		"site": {"site": {"name": "VELANG", "description": ""}},
	}
	template_context.update(context or {})
	source = _omit_empty_field_lines(source or "", template_context)
	rendered = env.from_string(source).render(**template_context)
	html = _render_markdown(rendered)
	return bleach.clean(
		html,
		tags=TAGS,
		attributes=ATTRS,
		protocols=["http", "https", "mailto"],
		strip=True,
	)
