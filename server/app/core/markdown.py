import bleach
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from markdown_it import MarkdownIt

TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {
	"p", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr", "img",
	"ul", "ol", "li", "strong", "em", "blockquote", "code", "pre",
	"table", "thead", "tbody", "tr", "th", "td",
}
ATTRS = {
	"a": ["href", "title", "target", "rel"],
	"img": ["src", "alt", "title", "loading"],
	"*": ["class"],
}


def render(source: str, context: dict | None = None) -> str:
	env = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)
	rendered = env.from_string(source or "").render(**(context or {}))
	html = MarkdownIt("commonmark", {"html": False, "linkify": True}).render(rendered)
	return bleach.clean(html, tags=TAGS, attributes=ATTRS, protocols=["http", "https", "mailto"])
