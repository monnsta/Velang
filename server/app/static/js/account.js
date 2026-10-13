/** Sign-in, checkout, and saved-address workflows. */

window.velangGoogleLogin = async function (response) {
	/** Complete Google sign-in and return the visitor to the requested page. */
	try {
		await api("/api/auth/google", {
			method: "POST",
			body: JSON.stringify({ credential: response.credential }),
		});
		window.location.href =
			new URLSearchParams(window.location.search).get("next") || "/account";
	} catch (error) {
		showToast(error.message);
	}
};

const checkoutForm = document.querySelector("[data-checkout-form]");
if (checkoutForm) {
	checkoutForm.addEventListener("submit", async (event) => {
		event.preventDefault();
		const form = new FormData(checkoutForm);
		const button = checkoutForm.querySelector("button[type=submit]");
		button.disabled = true;
		try {
			const result = await api("/api/orders", {
				method: "POST",
				body: JSON.stringify({
					address_id: Number(form.get("address_id")),
					notes: form.get("notes") || "",
				}),
			});
			if (!result.ok) throw new Error(result.error || "Could not place order.");
			if (result.payment?.intent_uri) {
				window.location.href = result.payment.intent_uri;
			} else {
				window.location.href = "/orders";
			}
		} catch (error) {
			showToast(error.message);
			button.disabled = false;
		}
	});
}

async function saveAddress(event) {
	/** Validate and persist the address form currently shown to the visitor. */
	event.preventDefault();
	const id = document.getElementById("address-id").value;
	const body = {
		label: document.getElementById("address-label").value.trim(),
		full_name: document.getElementById("address-name").value.trim(),
		phone: document.getElementById("address-phone").value.trim(),
		line1: document.getElementById("address-line1").value.trim(),
		line2: document.getElementById("address-line2").value.trim(),
		city: document.getElementById("address-city").value.trim(),
		state: document.getElementById("address-state").value.trim(),
		postal_code: document.getElementById("address-postal").value.trim(),
		country: document.getElementById("address-country").value.trim(),
		is_default: document.getElementById("address-default").checked,
	};
	try {
		await api(`/api/addresses${id ? `/${id}` : ""}`, {
			method: id ? "PUT" : "POST",
			body: JSON.stringify(body),
		});
		window.location.reload();
	} catch (error) {
		showError("address-error", error.message);
	}
}

function resetAddressForm() {
	/** Reset the address editor to its new-address state. */
	document.getElementById("address-form").reset();
	document.getElementById("address-id").value = "";
	document.getElementById("address-label").value = "Home";
	document.getElementById("address-country").value = "India";
	document.getElementById("address-form-title").textContent = "Add address";
	document.getElementById("address-error").textContent = "";
}

async function editAddress(id) {
	/** Load one saved address and populate the editor. */
	try {
		const addresses = await api("/api/addresses");
		const address = addresses.find((item) => item.id === id);
		if (!address) return;
		document.getElementById("address-id").value = address.id;
		document.getElementById("address-label").value = address.label || "";
		document.getElementById("address-name").value = address.full_name || "";
		document.getElementById("address-phone").value = address.phone || "";
		document.getElementById("address-line1").value = address.line1 || "";
		document.getElementById("address-line2").value = address.line2 || "";
		document.getElementById("address-city").value = address.city || "";
		document.getElementById("address-state").value = address.state || "";
		document.getElementById("address-postal").value = address.postal_code || "";
		document.getElementById("address-country").value = address.country || "India";
		document.getElementById("address-default").checked = Boolean(address.is_default);
		document.getElementById("address-form-title").textContent = "Edit address";
		document.getElementById("address-form").scrollIntoView({
			behavior: "smooth",
			block: "start",
		});
	} catch (error) {
		showError("address-error", error.message);
	}
}

async function removeAddress(id) {
	/** Delete one saved address after explicit user confirmation. */
	if (!window.confirm("Delete this address?")) return;
	try {
		await api(`/api/addresses/${id}`, { method: "DELETE" });
		window.location.reload();
	} catch (error) {
		showError("address-error", error.message);
	}
}

function showError(id, message) {
	/** Put an API error into a form-local error element when it exists. */
	const element = document.getElementById(id);
	if (element) element.textContent = message || "Something went wrong.";
}
