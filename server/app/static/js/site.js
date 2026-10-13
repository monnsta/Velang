/**
 * Shared storefront behavior.
 *
 * The storefront is server-rendered, so this file deliberately stays small:
 * it handles progressive enhancement, asynchronous cart/account actions, and
 * the two global header surfaces (search and navigation).
 */

async function api(path, options = {}) {
	/** Request a JSON API endpoint and normalize common server errors. */
	const response = await fetch(path, {
		credentials: "same-origin",
		headers: { "Content-Type": "application/json", ...(options.headers || {}) },
		...options,
	});

	const text = await response.text();
	let body = {};
	try {
		body = text ? JSON.parse(text) : {};
	} catch (_) {
		body = {};
	}

	if (!response.ok) {
		throw new Error(body.detail || body.error || `Request failed (${response.status})`);
	}

	return body;
}

function showToast(message) {
	/** Display a short, non-blocking error or status message. */
	let toast = document.querySelector("[data-toast]");
	if (!toast) {
		toast = document.createElement("div");
		toast.dataset.toast = "";
		toast.className = "toast";
		document.body.appendChild(toast);
	}
	toast.textContent = message || "Something went wrong.";
	toast.classList.add("is-visible");
	window.clearTimeout(toast._timeout);
	toast._timeout = window.setTimeout(() => toast.classList.remove("is-visible"), 2600);
}

let scrollLockY = 0;
let pageScrollLocked = false;
function setBodyLock(locked, mode = "menu") {
	/** Lock the document without changing the sticky header's scroll coordinate. */
	if (locked && !pageScrollLocked) {
		scrollLockY = window.scrollY;
		document.body.style.position = "fixed";
		document.body.style.top = `-${scrollLockY}px`;
		document.body.style.left = "0";
		document.body.style.right = "0";
		document.body.style.width = "100%";
		pageScrollLocked = true;
	} else if (!locked && pageScrollLocked) {
		document.body.style.position = "";
		document.body.style.top = "";
		document.body.style.left = "";
		document.body.style.right = "";
		document.body.style.width = "";
		pageScrollLocked = false;
		window.scrollTo(0, scrollLockY);
	}
	document.body.classList.toggle("menu-open", locked && mode === "menu");
	document.body.classList.toggle("search-open", locked && mode === "search");
}

const searchPanel = document.querySelector("[data-search-panel]");
const searchToggle = document.querySelector("[data-search-toggle]");
const searchClose = document.querySelector("[data-search-close]");
const searchInput = searchPanel?.querySelector("input");

function setSearchOpen(open) {
	/** Open or close the full-header search surface with its CSS transition. */
	if (!searchPanel) return;
	searchPanel.classList.toggle("is-open", open);
	searchPanel.setAttribute("aria-hidden", String(!open));
	searchToggle?.setAttribute("aria-expanded", String(open));
	if (open) {
		setMenuOpen(false);
		setBodyLock(true, "search");
		window.requestAnimationFrame(() => searchInput?.focus());
	} else {
		setBodyLock(false);
	}
}

searchToggle?.addEventListener("click", () => setSearchOpen(true));
searchClose?.addEventListener("click", () => setSearchOpen(false));

const menu = document.querySelector("[data-side-menu]");
const menuBackdrop = document.querySelector("[data-menu-backdrop]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const menuClose = document.querySelector("[data-menu-close]");

function setMenuOpen(open) {
	/** Open or close the persistent side navigation used on every storefront page. */
	if (!menu || !menuBackdrop) return;
	menu.classList.toggle("is-open", open);
	menuBackdrop.classList.toggle("is-open", open);
	menu.setAttribute("aria-hidden", String(!open));
	menuToggle?.setAttribute("aria-expanded", String(open));
	if (open) {
		setSearchOpen(false);
		setBodyLock(true, "menu");
	} else {
		setBodyLock(false);
	}
}

menuToggle?.addEventListener("click", () => setMenuOpen(true));
menuClose?.addEventListener("click", () => setMenuOpen(false));
menuBackdrop?.addEventListener("click", () => setMenuOpen(false));
menu?.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => setMenuOpen(false)));

document.addEventListener("keydown", (event) => {
	/** Close global overlays from the keyboard without interfering with forms. */
	if (event.key !== "Escape") return;
	setSearchOpen(false);
	setMenuOpen(false);
});
