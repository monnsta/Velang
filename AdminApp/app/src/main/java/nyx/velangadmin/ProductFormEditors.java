package nyx.velangadmin;

import android.content.ClipData;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.ArrayList;
import nyx.velangadmin.core.AdminCoreActivity;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/** Reusable structured image and variant editors used by the product form. */
public final class ProductFormEditors {
	private ProductFormEditors() {
	}

	public static final class ImageEditor {
		public final LinearLayout container;
		public final EditText serialized;
		private final AdminCoreActivity host;
		private final ArrayList<ImageRow> rows = new ArrayList<>();
		private boolean actionsAdded;
		private LinearLayout actionsContainer;

		public ImageEditor(AdminCoreActivity host, JSONArray initial) {
			this.host = host;
			container = host.column(8);
			serialized = new EditText(host);
			container.addView(host.label("Product images", 15));
			container.addView(host.label(
					"Each image has its own URL and alt text. Upload from your device or reuse a file from the asset library.",
					12));
			serialized.setVisibility(View.GONE);
			if (initial != null) {
				for (int i = 0; i < initial.length(); i++) {
					JSONObject item = initial.optJSONObject(i);
					if (item != null)
						addRow(item.optString("path", ""), item.optString("alt_text", ""));
				}
			}
			if (rows.isEmpty())
				addRow("", "");
			actionsContainer = new LinearLayout(host);
			actionsContainer.setOrientation(LinearLayout.HORIZONTAL);
			actionsContainer.setGravity(Gravity.CENTER_VERTICAL);
			actionsContainer.addView(host.iconButton(R.drawable.ic_add, "Add image", v -> addRow("", "")));
			actionsContainer.addView(host.iconButton(R.drawable.ic_upload, "Upload image from device",
					v -> host.pickFile(asset -> addAsset(asset))));
			actionsContainer.addView(host.iconButton(R.drawable.ic_library, "Choose asset from library",
					v -> host.chooseAsset(this::addAsset)));
			container.addView(actionsContainer);
			actionsAdded = true;
			sync();
		}

		private void addAsset(JSONObject asset) {
			addRow(asset.optString("path", ""), asset.optString("alt_text", ""));
			sync();
		}

		private void addRow(String pathValue, String altValue) {
			LinearLayout card = host.column(8);
			card.setBackground(host.outline(host.surfaceColor(), host.borderColor()));
			card.addView(host.label("Image " + (rows.size() + 1), 13));
			EditText path = host.input("/media/uploads/… or https://…", pathValue);
			path.setSingleLine(true);
			path.setHint("Image URL / media path");
			card.addView(path);
			EditText alt = host.input("Describe the image", altValue);
			alt.setSingleLine(true);
			alt.setHint("Alt text (recommended)");
			card.addView(alt);
			ImageRow row = new ImageRow(card, path, alt);
			rows.add(row);
			TextView dragHint = host.label("Hold and drag to reorder", 11);
			card.addView(dragHint);
			card.setLongClickable(true);
			card.setOnLongClickListener(v -> startRowDrag(card, row));
			dragHint.setOnLongClickListener(v -> startRowDrag(card, row));
			card.addView(host.iconButton(R.drawable.ic_delete, "Remove this image", v -> {
				container.removeView(card);
				rows.remove(row);
				refreshNumbers();
				sync();
			}));
			attachDropTargets(card, row, (source, target) -> reorderRows((ImageRow) source, (ImageRow) target));
			int at = actionsAdded ? container.getChildCount() - 1 : container.getChildCount();
			container.addView(card, at);
			android.text.TextWatcher watcher = new android.text.TextWatcher() {
				@Override
				public void beforeTextChanged(CharSequence s, int start, int count, int after) {
				}

				@Override
				public void onTextChanged(CharSequence s, int start, int before, int count) {
					sync();
				}

				@Override
				public void afterTextChanged(android.text.Editable s) {
				}
			};
			path.addTextChangedListener(watcher);
			alt.addTextChangedListener(watcher);
		}

		private void reorderRows(ImageRow source, ImageRow target) {
			int from = rows.indexOf(source);
			int to = rows.indexOf(target);
			if (from < 0 || to < 0 || from == to)
				return;
			rows.remove(from);
			if (from < to)
				to--;
			rows.add(Math.max(0, Math.min(to, rows.size())), source);
			rebuildRows();
		}

		private void rebuildRows() {
			for (ImageRow item : rows)
				container.removeView(item.card);
			int index = container.indexOfChild(actionsContainer);
			if (index < 0)
				index = container.getChildCount();
			for (ImageRow item : rows)
				container.addView(item.card, index++);
			refreshNumbers();
			sync();
		}

		private void refreshNumbers() {
			for (int i = 0; i < rows.size(); i++) {
				View first = rows.get(i).card.getChildAt(0);
				if (first instanceof TextView)
					((TextView) first).setText("Image " + (i + 1));
			}
		}

		private void sync() {
			try {
				JSONArray array = new JSONArray();
				for (ImageRow row : rows) {
					String path = row.path.getText().toString().trim();
					if (path.isEmpty())
						continue;
					array.put(new JSONObject().put("path", path).put("alt_text", row.alt.getText().toString().trim()));
				}
				serialized.setText(array.toString());
			} catch (JSONException ignored) {
			}
		}
	}

	@FunctionalInterface
	private interface DropHandler {
		void onDrop(Object source, Object target);
	}

	private static boolean startRowDrag(View view, Object row) {
		ClipData data = ClipData.newPlainText("reorder", "Reorder item");
		return view.startDragAndDrop(data, new View.DragShadowBuilder(view), row, 0);
	}

	private static void attachDropTargets(View view, Object row, DropHandler handler) {
		view.setOnDragListener((target, event) -> {
			switch (event.getAction()) {
				case android.view.DragEvent.ACTION_DRAG_STARTED:
					return event.getLocalState() != null;
				case android.view.DragEvent.ACTION_DRAG_ENTERED:
					if (target == view)
						target.setAlpha(0.78f);
					return true;
				case android.view.DragEvent.ACTION_DRAG_EXITED:
					if (target == view)
						target.setAlpha(1f);
					return true;
				case android.view.DragEvent.ACTION_DROP:
					target.setAlpha(1f);
					Object source = event.getLocalState();
					if (source != null && source.getClass() == row.getClass())
						handler.onDrop(source, row);
					return true;
				case android.view.DragEvent.ACTION_DRAG_ENDED:
					target.setAlpha(1f);
					return true;
				default:
					return true;
			}
		});
		if (view instanceof ViewGroup) {
			ViewGroup group = (ViewGroup) view;
			for (int i = 0; i < group.getChildCount(); i++)
				attachDropTargets(group.getChildAt(i), row, handler);
		}
	}

	private static final class ImageRow {
		final LinearLayout card;
		final EditText path;
		final EditText alt;

		ImageRow(LinearLayout card, EditText path, EditText alt) {
			this.card = card;
			this.path = path;
			this.alt = alt;
		}
	}

	public static final class VariantEditor {
		public final LinearLayout container;
		public final EditText serialized;
		private final AdminCoreActivity host;
		private final ArrayList<VariantRow> rows = new ArrayList<>();
		private final LinearLayout actionsContainer;

		public VariantEditor(AdminCoreActivity host, JSONArray initial) {
			this.host = host;
			container = host.column(8);
			serialized = new EditText(host);
			container.addView(host.label("Product variants", 15));
			container.addView(host.label(
					"Use variants for options with their own SKU, price or inventory. Leave this empty if the product has no variants.",
					12));
			serialized.setVisibility(View.GONE);
			if (initial != null) {
				for (int i = 0; i < initial.length(); i++) {
					JSONObject item = initial.optJSONObject(i);
					if (item != null)
						addRow(item.optString("name", ""), item.optString("sku", ""),
								item.isNull("price") ? "" : item.optString("price", ""),
								String.valueOf(item.optInt("stock_count", 0)),
								item.optJSONObject("meta"));
				}
			}
			actionsContainer = new LinearLayout(host);
			actionsContainer.setOrientation(LinearLayout.HORIZONTAL);
			actionsContainer.setGravity(Gravity.CENTER_VERTICAL);
			actionsContainer.addView(
					host.iconButton(R.drawable.ic_add, "Add variant", v -> addRow("", "", "", "0", new JSONObject())));
			container.addView(actionsContainer);
			sync();
		}

		private void addRow(String nameValue, String skuValue, String priceValue, String stockValue,
				JSONObject metaValue) {
			LinearLayout card = host.column(8);
			card.setBackground(host.outline(host.surfaceColor(), host.borderColor()));
			card.addView(host.label("Variant " + (rows.size() + 1), 13));
			EditText name = host.input("e.g. Sand / Large", nameValue);
			name.setSingleLine(true);
			name.setHint("Variant name (required)");
			card.addView(name);
			EditText sku = host.input("Leave blank to generate from the product SKU", skuValue);
			sku.setSingleLine(true);
			sku.setHint("Variant SKU (optional)");
			card.addView(sku);
			EditText price = host.input("Leave blank to use product price", priceValue);
			price.setSingleLine(true);
			price.setHint("Variant price (optional)");
			price.setInputType(
					android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
			card.addView(price);
			EditText stock = host.input("0", stockValue);
			stock.setSingleLine(true);
			stock.setHint("Variant stock count");
			stock.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
			card.addView(stock);
			VariantRow row = new VariantRow(card, name, sku, price, stock,
					metaValue == null ? new JSONObject() : metaValue);
			rows.add(row);
			TextView dragHint = host.label("Hold and drag to reorder", 11);
			card.addView(dragHint);
			card.setLongClickable(true);
			card.setOnLongClickListener(v -> startRowDrag(card, row));
			dragHint.setOnLongClickListener(v -> startRowDrag(card, row));
			card.addView(host.iconButton(R.drawable.ic_delete, "Remove variant", v -> {
				container.removeView(card);
				rows.remove(row);
				refreshNumbers();
				sync();
			}));
			attachDropTargets(card, row, (source, target) -> reorderRows((VariantRow) source, (VariantRow) target));
			int at = container.indexOfChild(actionsContainer);
			if (at < 0)
				at = container.getChildCount();
			container.addView(card, at);
			android.text.TextWatcher watcher = new android.text.TextWatcher() {
				@Override
				public void beforeTextChanged(CharSequence s, int start, int count, int after) {
				}

				@Override
				public void onTextChanged(CharSequence s, int start, int before, int count) {
					sync();
				}

				@Override
				public void afterTextChanged(android.text.Editable s) {
				}
			};
			name.addTextChangedListener(watcher);
			sku.addTextChangedListener(watcher);
			price.addTextChangedListener(watcher);
			stock.addTextChangedListener(watcher);
		}

		private void reorderRows(VariantRow source, VariantRow target) {
			int from = rows.indexOf(source);
			int to = rows.indexOf(target);
			if (from < 0 || to < 0 || from == to)
				return;
			rows.remove(from);
			if (from < to)
				to--;
			rows.add(Math.max(0, Math.min(to, rows.size())), source);
			rebuildRows();
		}

		private void rebuildRows() {
			for (VariantRow item : rows)
				container.removeView(item.card);
			int index = container.indexOfChild(actionsContainer);
			if (index < 0)
				index = container.getChildCount();
			for (VariantRow item : rows)
				container.addView(item.card, index++);
			refreshNumbers();
			sync();
		}

		private void refreshNumbers() {
			for (int i = 0; i < rows.size(); i++) {
				View first = rows.get(i).card.getChildAt(0);
				if (first instanceof TextView)
					((TextView) first).setText("Variant " + (i + 1));
			}
		}

		public boolean isValid() {
			for (VariantRow row : rows) {
				String name = row.name.getText().toString().trim();
				String sku = row.sku.getText().toString().trim();
				String price = row.price.getText().toString().trim();
				String stock = row.stock.getText().toString().trim();
				if (name.isEmpty() && sku.isEmpty() && price.isEmpty() && (stock.isEmpty() || "0".equals(stock)))
					continue;
				if (name.isEmpty())
					return false;
				if (!price.isEmpty()) {
					try {
						if (new java.math.BigDecimal(price).signum() < 0)
							return false;
					} catch (NumberFormatException error) {
						return false;
					}
				}
				try {
					if (Integer.parseInt(stock.isEmpty() ? "0" : stock) < 0)
						return false;
				} catch (NumberFormatException error) {
					return false;
				}
			}
			return true;
		}

		private void sync() {
			try {
				JSONArray values = new JSONArray();
				for (VariantRow row : rows) {
					String name = row.name.getText().toString().trim();
					String sku = row.sku.getText().toString().trim();
					String price = row.price.getText().toString().trim();
					String stock = row.stock.getText().toString().trim();
					if (name.isEmpty() && sku.isEmpty() && price.isEmpty() && (stock.isEmpty() || "0".equals(stock)))
						continue;
					JSONObject value = new JSONObject().put("name", name);
					if (!sku.isEmpty())
						value.put("sku", sku);
					value.put("price", price.isEmpty() ? JSONObject.NULL : price);
					int stockCount = 0;
					try {
						stockCount = Integer.parseInt(stock.isEmpty() ? "0" : stock);
					} catch (NumberFormatException ignored) {
					}
					value.put("stock_count", stockCount);
					value.put("meta", row.meta == null ? new JSONObject() : new JSONObject(row.meta.toString()));
					values.put(value);
				}
				serialized.setText(values.toString());
			} catch (JSONException ignored) {
			}
		}
	}

	private static final class VariantRow {
		final LinearLayout card;
		final EditText name;
		final EditText sku;
		final EditText price;
		final EditText stock;
		final JSONObject meta;

		VariantRow(LinearLayout card, EditText name, EditText sku, EditText price, EditText stock, JSONObject meta) {
			this.card = card;
			this.name = name;
			this.sku = sku;
			this.price = price;
			this.stock = stock;
			this.meta = meta;
		}
	}
}
