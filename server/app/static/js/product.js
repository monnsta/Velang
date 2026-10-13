/** Product option interaction and currency-aware price formatting. */

document.querySelectorAll("[data-size-option]").forEach((button) => {
	button.addEventListener("click", () => {
		document
			.querySelectorAll("[data-size-option]")
			.forEach((item) => item.setAttribute("aria-pressed", "false"));
		button.setAttribute("aria-pressed", "true");
	});
});


/* Format every displayed amount from a numeric value and ISO currency code. */
document.querySelectorAll("[data-money]").forEach((element) => {
	const amount = Number(element.dataset.value);
	const currency = element.dataset.currency || "INR";
	if (!Number.isFinite(amount)) return;
	try {
		element.textContent = new Intl.NumberFormat(
			currency === "INR" ? "en-IN" : undefined,
			{ style: "currency", currency, currencyDisplay: "symbol" },
		).format(amount);
	} catch (_) {
		element.textContent = `${currency} ${amount.toFixed(2)}`;
	}
});

/* Variant options use the same ISO-currency formatting as all other prices. */
document.querySelectorAll("select option[data-price][data-currency]").forEach((option) => {
	const amount = Number(option.dataset.price);
	const currency = option.dataset.currency || "INR";
	if (!Number.isFinite(amount)) return;
	const name = option.textContent.split(" — ")[0];
	try {
		option.textContent = `${name} — ${new Intl.NumberFormat(currency === "INR" ? "en-IN" : undefined, { style: "currency", currency, currencyDisplay: "symbol" }).format(amount)}`;
	} catch (_) {
		option.textContent = `${name} — ${currency} ${amount.toFixed(2)}`;
	}
});

document.querySelectorAll("[data-variant-select]").forEach((select) => {
	const updateVariantPrice = () => {
		const option = select.selectedOptions[0];
		const price = document.querySelector(".product-price-large[data-money]");
		if (!option || !price || !option.dataset.price) return;
		price.dataset.value = option.dataset.price;
		price.dataset.currency = option.dataset.currency || "INR";
		const amount = Number(option.dataset.price);
		try {
			price.textContent = new Intl.NumberFormat(
				price.dataset.currency === "INR" ? "en-IN" : undefined,
				{ style: "currency", currency: price.dataset.currency, currencyDisplay: "symbol" },
			).format(amount);
		} catch (_) {
			price.textContent = `${price.dataset.currency} ${amount.toFixed(2)}`;
		}
	};
	select.addEventListener("change", updateVariantPrice);
	updateVariantPrice();
});
