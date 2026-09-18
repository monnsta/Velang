async function api(path, options = {}) {
	const response = await fetch(path, {
		credentials: 'same-origin',
		headers: {'Content-Type': 'application/json', ...(options.headers || {})},
		...options,
	});
	const body = await response.json().catch(() => ({}));
	if (!response.ok) throw new Error(body.detail || body.error || 'Request failed');
	return body;
}

function money(value, currency = 'INR') {
	try { return new Intl.NumberFormat('en-IN', {style: 'currency', currency}).format(Number(value)); }
	catch (_) { return `${currency} ${value}`; }
}

document.querySelectorAll('[data-add-cart]').forEach((button) => {
	button.addEventListener('click', async () => {
		button.disabled = true;
		try {
			const variant = document.querySelector('[data-variant-select]');
			const payload = {product_id: Number(button.dataset.addCart), quantity: 1};
			if (variant && variant.value) payload.variant_id = Number(variant.value);
			const data = await api('/api/cart/items', {method: 'POST', body: JSON.stringify(payload)});
			if (!data.ok) throw new Error(data.error || 'Could not add');
			button.textContent = 'Added';
			setTimeout(() => { button.textContent = button.dataset.original || 'Add to cart'; }, 1200);
		} catch (error) {
			if (error.message === 'Login required') window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
			else alert(error.message);
		} finally { button.disabled = false; }
	});
});

document.querySelectorAll('[data-wishlist]').forEach((button) => {
	button.addEventListener('click', async () => {
		try {
			const data = await api(`/api/wishlist/${Number(button.dataset.wishlist)}/toggle`, {method: 'POST', body: JSON.stringify({product_id: Number(button.dataset.wishlist)})});
			button.setAttribute('aria-pressed', String(data.saved));
			button.textContent = data.saved ? '♥' : '♡';
		} catch (error) {
			if (error.message === 'Login required') window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
			else alert(error.message);
		}
	});
});

document.querySelectorAll('[data-remove-cart]').forEach((button) => {
	button.addEventListener('click', async () => {
		await api(`/api/cart/items/${button.dataset.removeCart}`, {method: 'DELETE'});
		window.location.reload();
	});
});

document.querySelectorAll('[data-qty-form]').forEach((form) => {
	form.addEventListener('submit', async (event) => {
		event.preventDefault();
		const item = Number(form.dataset.qtyForm);
		const quantity = Number(form.querySelector('input').value);
		await api(`/api/cart/items/${item}`, {method: 'PATCH', body: JSON.stringify({quantity})});
		window.location.reload();
	});
});

const loginForm = document.querySelector('[data-login-form]');
if (loginForm) {
	loginForm.addEventListener('submit', async (event) => {
		event.preventDefault();
		const form = new FormData(loginForm);
		const error = loginForm.querySelector('[data-form-error]');
		try {
			await api('/api/auth/login', {method: 'POST', body: JSON.stringify({email: form.get('email'), password: form.get('password')})});
			window.location.href = new URLSearchParams(window.location.search).get('next') || '/account';
		} catch (err) { error.textContent = err.message; error.hidden = false; }
	});
}

const registerForm = document.querySelector('[data-register-form]');
if (registerForm) {
	registerForm.addEventListener('submit', async (event) => {
		event.preventDefault();
		const form = new FormData(registerForm);
		const error = registerForm.querySelector('[data-form-error]');
		try {
			await api('/api/auth/register', {method: 'POST', body: JSON.stringify({name: form.get('name'), email: form.get('email'), password: form.get('password')})});
			window.location.href = '/account';
		} catch (err) { error.textContent = err.message; error.hidden = false; }
	});
}

window.velangGoogleLogin = async function(response) {
	try {
		await api('/api/auth/google', {method: 'POST', body: JSON.stringify({credential: response.credential})});
		window.location.href = new URLSearchParams(window.location.search).get('next') || '/account';
	} catch (error) { alert(error.message); }
};

const checkoutForm = document.querySelector('[data-checkout-form]');
if (checkoutForm) {
	checkoutForm.addEventListener('submit', async (event) => {
		event.preventDefault();
		const form = new FormData(checkoutForm);
		const button = checkoutForm.querySelector('button[type=submit]');
		button.disabled = true;
		try {
			const result = await api('/api/orders', {method: 'POST', body: JSON.stringify({address_id: Number(form.get('address_id')), coupon_code: form.get('coupon_code') || '', notes: form.get('notes') || ''})});
			if (!result.ok) throw new Error(result.error || 'Could not place order');
			if (result.payment && result.payment.intent_uri) window.location.href = result.payment.intent_uri;
			else window.location.href = '/orders';
		} catch (error) { alert(error.message); button.disabled = false; }
	});
}

async function saveAddress(event) {
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
		await api(`/api/addresses${id ? `/${id}` : ""}`, {method: id ? "PUT" : "POST", body: JSON.stringify(body)});
		window.location.reload();
	} catch (error) {
		showError("address-error", error.message);
	}
}

function resetAddressForm() {
	document.getElementById("address-form").reset();
	document.getElementById("address-id").value = "";
	document.getElementById("address-label").value = "Home";
	document.getElementById("address-country").value = "India";
	document.getElementById("address-form-title").textContent = "Add address";
	document.getElementById("address-error").textContent = "";
}

async function editAddress(id) {
	try {
		const addresses = await api("/api/addresses");
		const address = addresses.find(item => item.id === id);
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
		document.getElementById("address-form").scrollIntoView({behavior: "smooth", block: "start"});
	} catch (error) {
		showError("address-error", error.message);
	}
}

async function removeAddress(id) {
	if (!window.confirm("Delete this address?")) return;
	try {
		await api(`/api/addresses/${id}`, {method: "DELETE"});
		window.location.reload();
	} catch (error) {
		showError("address-error", error.message);
	}
}

function showError(id, message) {
	const element = document.getElementById(id);
	if (element) element.textContent = message || "Something went wrong.";
}
