/**
 * Gallery behavior shared by product cards and product detail pages.
 * Kept separate from cart/account interactions so either side can evolve safely.
 */

/* Product cards store the gallery as data and swap one image node. This makes
   it impossible for inactive product photographs to leak into the card layout. */
function readImageList(element, key) {
	try {
		const value = JSON.parse(element.dataset[key] || "[]");
		return Array.isArray(value) ? value : [];
	} catch (_) {
		return [];
	}
}

function bindSwipeCarousel(container, image, paths, alts, thumb, threshold = 38) {
	if (!image || paths.length < 2) return;

	let active = 0;
	let pointerStart = null;
	let ignoreClick = false;
	let isAnimating = false;

	const updateProgress = () => {
		if (!thumb) return;
		thumb.style.width = `${100 / paths.length}%`;
		thumb.style.left = `${active * 100 / paths.length}%`;
		thumb.style.transform = "none";
	};

	const show = (index, direction = 1) => {
		const next = (index + paths.length) % paths.length;
		if (next === active && image.dataset.activeImage !== undefined) return;
		if (isAnimating) return;

		const parent = image.parentElement;
		if (!parent) return;

		if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
			active = next;
			image.src = paths[active];
			image.alt = alts[active] || container.dataset.fallbackAlt || image.alt;
			image.dataset.activeImage = String(active);
			image.classList.remove("is-zoomed");
			updateProgress();
			return;
		}

		isAnimating = true;
		const prevActive = active;
		active = next;

		const slideInDir = direction > 0 ? "100%" : "-100%";
		const slideOutDir = direction > 0 ? "-100%" : "100%";

		image.style.setProperty("--gallery-slide-dir", slideInDir);
		image.classList.remove("is-sliding-in", "is-sliding-out");
		image.src = paths[active];
		image.alt = alts[active] || container.dataset.fallbackAlt || image.alt;
		image.dataset.activeImage = String(active);
		image.classList.remove("is-zoomed");

		// Create outgoing ghost image for smooth side-by-side gallery push
		const ghost = image.cloneNode(true);
		ghost.src = paths[prevActive];
		ghost.style.setProperty("--gallery-slide-out-dir", slideOutDir);
		ghost.classList.add("is-sliding-out");
		parent.appendChild(ghost);

		void image.offsetWidth;
		image.classList.add("is-sliding-in");

		updateProgress();

		const cleanup = () => {
			ghost.remove();
			image.classList.remove("is-sliding-in");
			isAnimating = false;
		};

		image.addEventListener("animationend", cleanup, { once: true });
	};

	// Initial state is already represented by the server-rendered image. Do not
	// call show() here: doing so caused a visible slide/flicker on every page load.
	image.dataset.activeImage = String(active);
	updateProgress();
	container.addEventListener("pointerdown", (event) => {
		if (!event.isPrimary || event.button !== 0) return;
		pointerStart = { x: event.clientX, y: event.clientY };
		ignoreClick = false;
	}, { passive: true });
	container.addEventListener("pointerup", (event) => {
		if (!pointerStart || !event.isPrimary) return;
		const deltaX = event.clientX - pointerStart.x;
		const deltaY = event.clientY - pointerStart.y;
		pointerStart = null;
		if (Math.abs(deltaX) > threshold && Math.abs(deltaX) > Math.abs(deltaY) * 1.15) {
			const dir = deltaX < 0 ? 1 : -1;
			show(active + dir, dir);
			ignoreClick = true;
		}
	}, { passive: true });
	container.addEventListener("pointercancel", () => { pointerStart = null; }, { passive: true });

	return {
		show,
		consumeSwipeClick() {
			if (!ignoreClick) return false;
			ignoreClick = false;
			return true;
		},
	};
}

document.querySelectorAll("[data-image-carousel]").forEach((carousel) => {
	const image = carousel.querySelector("[data-card-image]");
	const paths = readImageList(carousel, "imagePaths");
	const alts = readImageList(carousel, "imageAlts");
	const thumb = carousel.querySelector("[data-image-progress-thumb]");
	if (!image || !paths.length) return;

	const carouselState = bindSwipeCarousel(carousel, image, paths, alts, thumb);
	carousel.querySelector(".card-link")?.addEventListener("click", (event) => {
		if (carouselState?.consumeSwipeClick()) event.preventDefault();
	});
});

/* Product gallery uses the same single-image rail; taps toggle zoom at the tap point. */
document.querySelectorAll("[data-product-gallery]").forEach((gallery) => {
	const image = gallery.querySelector("[data-gallery-image]");
	const paths = readImageList(gallery, "imagePaths");
	const alts = readImageList(gallery, "imageAlts");
	const thumb = gallery.querySelector("[data-gallery-progress-thumb]");
	if (!image || !paths.length) return;

	const carouselState = bindSwipeCarousel(gallery, image, paths, alts, thumb, 45);
	image.addEventListener("click", (event) => {
		if (carouselState?.consumeSwipeClick()) {
			event.preventDefault();
			return;
		}
		if (image.classList.contains("is-zoomed")) {
			image.classList.remove("is-zoomed");
			return;
		}
		const bounds = image.getBoundingClientRect();
		const x = Math.max(0, Math.min(100, ((event.clientX - bounds.left) / bounds.width) * 100));
		const y = Math.max(0, Math.min(100, ((event.clientY - bounds.top) / bounds.height) * 100));
		image.style.setProperty("--zoom-x", `${x}%`);
		image.style.setProperty("--zoom-y", `${y}%`);
		image.classList.add("is-zoomed");
	});
});

/* Keep the product header sticky over the gallery, then restore readable contrast. */
const siteHeader = document.querySelector(".site-nav");
if (siteHeader?.closest("body.product-page")) {
	const updateHeaderContrast = () => {
		const gallery = document.querySelector("[data-product-gallery]");
		const image = gallery?.querySelector("[data-gallery-image]");
		const pictureHeight = image?.getBoundingClientRect().height || gallery?.getBoundingClientRect().height || 0;
		const threshold = Math.max(60, pictureHeight * 0.5);
		siteHeader.classList.toggle("is-scrolled", window.scrollY >= threshold);
	};
	updateHeaderContrast();
	window.addEventListener("scroll", updateHeaderContrast, { passive: true });
	window.addEventListener("pageshow", updateHeaderContrast, { passive: true });
	window.addEventListener("resize", updateHeaderContrast, { passive: true });
}
