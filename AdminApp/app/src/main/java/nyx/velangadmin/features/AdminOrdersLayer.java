package nyx.velangadmin.features;

import android.view.Gravity;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import nyx.velangadmin.R;
import org.json.JSONArray;
import org.json.JSONObject;
import static nyx.velangadmin.AdminJson.*;

public abstract class AdminOrdersLayer extends AdminTemplatesLayer {
	@Override
	protected void loadOrders() {
		async(() -> api.get("/api/admin/orders"), data -> {
			clearContent();
			content.addView(label("Production overview", 23));
			content.addView(label(
					"The queue groups paid, not-yet-completed orders by product, variant and customer options. Special-care work is shown first.",
					13));
			JSONArray production = data.optJSONArray("production");
			if (production == null || production.length() == 0) {
				content.addView(label("Nothing in the paid production queue right now.", 14));
			} else {
				for (int i = 0; i < production.length(); i++) {
					JSONObject item = production.optJSONObject(i);
					if (item == null)
						continue;
					LinearLayout card = column(10);
					card.setBackground(outline(SURFACE, BORDER));
					card.addView(label(
							(item.optBoolean("special_care") ? "⚑ SPECIAL CARE · " : "") + item.optString("name"), 16));
					card.addView(label(
							"Qty " + item.optInt("quantity") + " · SKU " + item.optString("sku")
									+ (item.optString("variant").isEmpty() ? "" : " · " + item.optString("variant")),
							12));
					JSONObject choices = item.optJSONObject("options");
					if (choices != null && choices.length() > 0)
						card.addView(label("Customer options:\n" + readableDetails(choices), 12));
					String details = readableDetails(item.optJSONObject("product_details"));
					if (!details.isEmpty())
						card.addView(label("Product / material specification:\n" + details, 12));
					JSONArray notes = item.optJSONArray("production_notes");
					if (notes != null)
						for (int j = 0; j < notes.length(); j++)
							card.addView(label("Maker note: " + notes.optString(j), 12));
					JSONArray orderNumbers = item.optJSONArray("orders");
					if (orderNumbers != null)
						card.addView(label("Orders: " + separatedArray(orderNumbers, ", "), 11));
					content.addView(card);
				}
			}
			content.addView(label("Orders", 23));
			EditText search = input("Search order, customer, status or SKU", "");
			search.setSingleLine(true);
			content.addView(search);
			JSONArray rows = data.optJSONArray("orders");
			LinearLayout list = column(0);
			content.addView(list);
			if (rows == null) {
				list.addView(label("The server returned no orders list.", 14));
				return;
			}
			renderOrders(rows, search.getText().toString(), list);
			search.addTextChangedListener(new android.text.TextWatcher() {
				@Override
				public void beforeTextChanged(CharSequence s, int start, int count, int after) {
				}

				@Override
				public void onTextChanged(CharSequence s, int start, int before, int count) {
					renderOrders(rows, s.toString(), list);
				}

				@Override
				public void afterTextChanged(android.text.Editable s) {
				}
			});
		});
	}

	@Override
	protected void renderOrders(JSONArray rows, String query, LinearLayout list) {
		list.removeAllViews();
		String needle = query == null ? "" : query.trim().toLowerCase(java.util.Locale.ROOT);
		int count = 0;
		for (int i = 0; i < rows.length(); i++) {
			JSONObject order = rows.optJSONObject(i);
			if (order == null)
				continue;
			JSONArray items = order.optJSONArray("items");
			StringBuilder searchable = new StringBuilder(order.toString().toLowerCase(java.util.Locale.ROOT));
			if (!needle.isEmpty() && !searchable.toString().contains(needle))
				continue;
			LinearLayout card = column(12);
			card.setBackground(outline(SURFACE, BORDER));
			card.addView(label(order.optString("number"), 18));
			card.addView(label(order.optString("customer_name") + " · " + order.optString("customer_email"), 12));
			card.addView(label(order.optString("currency", "INR") + " " + order.optString("total") + " · "
					+ order.optString("status") + " · payment " + order.optString("payment_status"), 12));
			JSONObject address = order.optJSONObject("address");
			if (address != null && address.length() > 0)
				card.addView(label("Ship to: " + address.optString("full_name") + ", " + address.optString("line1")
						+ (address.optString("line2").isEmpty() ? "" : ", " + address.optString("line2")) + ", "
						+ address.optString("city") + " " + address.optString("postal_code") + " · "
						+ address.optString("phone"), 12));
			if (!order.optString("notes").trim().isEmpty())
				card.addView(label("Customer note: " + order.optString("notes"), 12));
			if (items != null)
				for (int j = 0; j < items.length(); j++) {
					JSONObject item = items.optJSONObject(j);
					if (item == null)
						continue;
					String productLine = "• " + item.optInt("quantity") + " × " + item.optString("name")
							+ (item.optString("variant").isEmpty() ? "" : " · " + item.optString("variant"))
							+ (item.optString("sku").isEmpty() ? "" : " · SKU " + item.optString("sku"));
					card.addView(label((item.optBoolean("special_care") ? "⚑ SPECIAL CARE · " : "") + productLine, 13));
					JSONObject opts = item.optJSONObject("options");
					if (opts != null && opts.length() > 0)
						card.addView(label("Customer options:\n" + readableDetails(opts), 12));
					String productDetails = readableDetails(item.optJSONObject("product_details"));
					if (!productDetails.isEmpty())
						card.addView(label("Product specification:\n" + productDetails, 12));
					if (!item.optString("production_notes").trim().isEmpty())
						card.addView(label("Production: " + item.optString("production_notes"), 12));
				}
			LinearLayout actions = new LinearLayout(this);
			actions.setOrientation(LinearLayout.HORIZONTAL);
			actions.setGravity(Gravity.CENTER_VERTICAL);
			actions.setHorizontalScrollBarEnabled(true);
			actions.addView(button("Process", v -> changeOrder(order.optInt("id"), "processing", null)));
			actions.addView(button("Ship", v -> changeOrder(order.optInt("id"), "shipped", null)));
			actions.addView(button("Delivered", v -> changeOrder(order.optInt("id"), "delivered", null)));
			actions.addView(button("Cancel", v -> changeOrder(order.optInt("id"), "cancelled", null)));
			actions.addView(button("Mark paid", v -> changeOrder(order.optInt("id"), null, "paid")));
			actions.addView(iconButton(R.drawable.ic_delete, "Delete order", v -> confirm("Delete order?",
					"Permanently delete " + order.optString("number")
							+ " and its payment/item history? This cannot be undone.",
					() -> asyncAction(() -> api.delete("/api/admin/orders/" + order.optInt("id")), this::loadOrders))));
			HorizontalScrollView actionScroll = new HorizontalScrollView(this);
			actionScroll.setHorizontalScrollBarEnabled(false);
			actionScroll.addView(actions);
			card.addView(actionScroll);
			list.addView(card);
			count++;
		}
		if (count == 0)
			list.addView(label(needle.isEmpty() ? "No orders yet." : "No orders match that search.", 14));
	}

	@Override
	protected void changeOrder(int id, String status, String payment) {
		asyncAction(
				() -> {
					if (status != null)
						api.put("/api/admin/orders/" + id + "/status", new JSONObject().put("status", status));
					if (payment != null)
						api.put(
								"/api/admin/orders/" + id + "/payment", new JSONObject().put("status", payment));
				},
				() -> loadOrders());
	}
}
