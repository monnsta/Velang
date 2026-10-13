/** Cart controls, custom-size validation, and pending buy-now restoration. */

const previewMode = document.body.classList.contains("preview-mode");

document.querySelectorAll("[data-add-cart], [data-buy-now]").forEach((button) => {
	if (previewMode) {
		button.addEventListener("click", () => {
			const buyNow = button.hasAttribute("data-buy-now");
			const sizeContainer = document.querySelector("[data-size-container]");
			const sizeMode = sizeContainer?.dataset.sizeMode || "none";
			const selectedSize = document.querySelector("[data-size-option][aria-pressed=true]");
			const customFields = [...document.querySelectorAll("[data-custom-size]")];
			const customValues = customFields.map((field) => field.value.trim());
			const anyCustomValue = customValues.some(Boolean);
			const mustUseCustom = sizeMode === "custom" || (sizeMode === "both" && anyCustomValue);
			if (sizeMode === "predefined" && !selectedSize) {
				showToast("Choose a size before adding this product.");
				return;
			}
			if (mustUseCustom && (!customFields.length || customValues.some((value) => !value))) {
				showToast("Enter all custom measurements before adding this product.");
				return;
			}
			if (sizeMode === "both" && !selectedSize && !anyCustomValue) {
				showToast("Choose a listed size or enter custom measurements.");
				return;
			}
			button.textContent = buyNow ? "Checkout unavailable in preview" : "Preview added";
			showToast("Preview mode: cart and checkout changes are disabled.");
			window.setTimeout(() => {
				button.textContent = button.dataset.original || (buyNow ? "Buy now" : "Add to cart");
			}, 1800);
		});
		return;
	}
	button.addEventListener("click", async () => {
		button.disabled = true;
		const buyNow = button.hasAttribute("data-buy-now");
		let payload;
		try {
			const variant = document.querySelector("[data-variant-select]");
			payload = {
				product_id: Number(button.dataset.addCart || button.dataset.buyNow),
				quantity: 1,
			};

			const sizeContainer = document.querySelector("[data-size-container]");
			const sizeMode = sizeContainer?.dataset.sizeMode || "none";
			const selectedSize = document.querySelector(
				"[data-size-option][aria-pressed=true]",
			);
			if (selectedSize) payload.options = { size: selectedSize.dataset.sizeOption };

			const customFields = [...document.querySelectorAll("[data-custom-size]")];
			const customValues = customFields.map((field) => field.value.trim());
			const anyCustomValue = customValues.some(Boolean);
			const mustUseCustom = sizeMode === "custom" || (sizeMode === "both" && anyCustomValue);
			if (sizeMode === "predefined" && !selectedSize) {
				throw new Error("Choose a size before adding this product.");
			}
			if (mustUseCustom) {
				if (!customFields.length || customValues.some((value) => !value)) {
					throw new Error("Enter all custom measurements before adding the product.");
				}
				const customSize = Object.fromEntries(
					customFields.map((field) => [field.dataset.customSize, field.value.trim()]),
				);
				payload.options = { ...(payload.options || {}), custom_size: customSize };
			} else if (sizeMode === "both" && !selectedSize) {
				throw new Error("Choose a listed size or enter custom measurements.");
			}

			if (variant && variant.value) payload.variant_id = Number(variant.value);
			const data = await api("/api/cart/items", {
				method: "POST",
				body: JSON.stringify(payload),
			});
			if (!data.ok) throw new Error(data.error || "Could not add to cart.");

			if (Number.isFinite(data.cart_count)) updateCartBadge(data.cart_count);
			if (buyNow) {
				window.location.href = "/checkout";
				return;
			}
			button.textContent = "Added";
			window.setTimeout(() => {
				button.textContent = button.dataset.original || "Add to cart";
			}, 1200);
		} catch (error) {
			if (error.message === "Login required") {
				if (buyNow && payload) {
					try { sessionStorage.setItem("velang.pending-buy", JSON.stringify(payload)); } catch (_) { }
				}
				window.location.href =
					"/login?next=" + encodeURIComponent(window.location.pathname);
			} else {
				showToast(error.message);
			}
		} finally {
			button.disabled = false;
		}
	});
});

function updateCartBadge(count) {
	const bag = document.querySelector(".nav-bag");
	if (!bag) return;
	let badge = bag.querySelector(".badge");
	if (count > 0 && !badge) {
		badge = document.createElement("span");
		badge.className = "badge";
		bag.appendChild(badge);
	}
	if (badge) {
		badge.textContent = String(count);
		if (count <= 0) badge.remove();
	}
}

// Buy-now can survive the login redirect without losing chosen size/measurements.
(async function resumePendingBuy() {
	if (previewMode) return;
	let pending;
	try {
		pending = JSON.parse(sessionStorage.getItem("velang.pending-buy") || "null");
	} catch (_) { pending = null; }
	if (!pending || !pending.product_id || !window.location.pathname.startsWith("/product/")) return;
	try {
		const result = await api("/api/cart/items", { method: "POST", body: JSON.stringify(pending) });
		if (!result.ok) throw new Error(result.error || "Could not add to cart.");
		sessionStorage.removeItem("velang.pending-buy");
		window.location.href = "/checkout";
	} catch (error) {
		if (error.message !== "Login required") {
			sessionStorage.removeItem("velang.pending-buy");
			showToast(error.message);
		}
	}
})();

document.querySelectorAll("[data-remove-cart]").forEach((button) => {
	button.addEventListener("click", async () => {
		button.disabled = true;
		try {
			await api(`/api/cart/items/${button.dataset.removeCart}`, {
				method: "DELETE",
			});
			window.location.reload();
		} catch (error) {
			button.disabled = false;
			showToast(error.message);
		}
	});
});

document.querySelectorAll("[data-qty-form]").forEach((form) => {
	form.addEventListener("submit", async (event) => {
		event.preventDefault();
		const item = Number(form.dataset.qtyForm);
		const quantity = Number(form.querySelector("input").value);
		try {
			await api(`/api/cart/items/${item}`, {
				method: "PATCH",
				body: JSON.stringify({ quantity }),
			});
			window.location.reload();
		} catch (error) {
			showToast(error.message);
		}
	});
});
