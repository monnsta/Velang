package nyx.velangadmin.features;

import android.app.AlertDialog;
import android.content.ClipboardManager;
import android.content.ClipData;
import android.graphics.Color;
import android.os.Build;
import android.view.DragEvent;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import android.widget.Switch;
import java.net.URL;
import java.util.ArrayList;
import java.util.Map;
import nyx.velangadmin.R;
import nyx.velangadmin.ProductFormEditors;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import static nyx.velangadmin.AdminJson.*;

public abstract class AdminProductsLayer extends AdminDashboardLayer {
	@Override
	protected void loadProducts() {
		async(
				() -> api.get("/api/admin/products"),
				data -> {
					clearContent();
					content.addView(label("Products", 23));
					content.addView(iconButton(R.drawable.ic_add, "New product", v -> startNewProduct()));
					content.addView(
							label("To reorder, touch and hold a product card, then drop it onto the target card.", 12));
					EditText search = input("Search name or SKU", "");
					search.setSingleLine(true);
					search.setHint("Search by product name or SKU");
					content.addView(search);
					JSONArray rows = data.optJSONArray("products");
					LinearLayout list = column(0);
					content.addView(list);
					if (rows == null) {
						list.addView(label("The server returned no product list.", 14));
						return;
					}
					renderProducts(rows, "", list);
					if (contentScroll != null)
						contentScroll.post(() -> contentScroll.scrollTo(0, productListScrollY));
					search.addTextChangedListener(new android.text.TextWatcher() {
						@Override
						public void beforeTextChanged(CharSequence s, int start, int count, int after) {
						}

						@Override
						public void onTextChanged(CharSequence s, int start, int before, int count) {
							renderProducts(rows, s.toString(), list);
						}

						@Override
						public void afterTextChanged(android.text.Editable s) {
						}
					});
				});
	}

	@Override
	protected void renderProducts(JSONArray rows, String query, LinearLayout list) {
		list.removeAllViews();
		String needle = query == null ? "" : query.trim().toLowerCase(java.util.Locale.ROOT);
		int displayed = 0;
		for (int i = 0; i < rows.length(); i++) {
			JSONObject p = rows.optJSONObject(i);
			if (p == null)
				continue;
			String name = jsonValueText(p, "name", "Unnamed product");
			String sku = jsonValueText(p, "sku", "");
			if (!needle.isEmpty() && !(name.toLowerCase(java.util.Locale.ROOT).contains(needle)
					|| sku.toLowerCase(java.util.Locale.ROOT).contains(needle)))
				continue;
			LinearLayout row = column(12);
			row.setBackground(outline(SURFACE, BORDER));
			JSONArray images = p.optJSONArray("images");
			if (images != null && images.length() > 0) {
				JSONObject firstImage = images.optJSONObject(0);
				if (firstImage != null) {
					ImageView thumb = new ImageView(this);
					thumb.setScaleType(ImageView.ScaleType.CENTER_CROP);
					thumb.setBackground(outline(SURFACE, BORDER));
					LinearLayout.LayoutParams thumbParams = new LinearLayout.LayoutParams(dp(92), dp(92));
					thumbParams.setMargins(0, 0, 0, dp(8));
					row.addView(thumb, thumbParams);
					loadThumbnail(thumb, jsonValueText(firstImage, "path", ""));
				}
			}
			row.addView(label(name, 17));
			row.addView(label(
					(sku.isEmpty() ? "No SKU" : sku)
							+ " · " + jsonValueText(p, "currency", "INR") + " " + jsonValueText(p, "price", "0")
							+ " · " + jsonValueText(p, "status", "draft")
							+ " · stock " + jsonValueText(p, "stock_count", "0"),
					12));
			LinearLayout rowActions = new LinearLayout(this);
			rowActions.setOrientation(LinearLayout.HORIZONTAL);
			rowActions.setGravity(Gravity.END | Gravity.CENTER_VERTICAL);
			rowActions.addView(iconButton(R.drawable.ic_edit, "Edit product", v -> loadProduct(p.optInt("id"))));
			rowActions.addView(iconButton(R.drawable.ic_open, "Open product on storefront", v -> {
				String base = api.getBaseUrl().replaceAll("/+$", "");
				String slug = jsonValueText(p, "slug", "");
				new AlertDialog.Builder(this).setTitle(name).setMessage(base + "/product/" + slug)
						.setPositiveButton("Copy URL", (dialog, which) -> {
							android.content.ClipboardManager clipboard = (android.content.ClipboardManager) getSystemService(
									CLIPBOARD_SERVICE);
							clipboard.setPrimaryClip(
									android.content.ClipData.newPlainText("Product URL", base + "/product/" + slug));
							Toast.makeText(this, "Product URL copied", Toast.LENGTH_SHORT).show();
						}).setNegativeButton("Close", null).show();
			}));
			row.addView(rowActions, new LinearLayout.LayoutParams(-1, -2));
			if (needle.isEmpty()) {
				row.setTag(p.optInt("id"));
				row.setOnLongClickListener(v -> {
					android.content.ClipData dragData = android.content.ClipData.newPlainText("product-id",
							String.valueOf(p.optInt("id")));
					if (android.os.Build.VERSION.SDK_INT >= 24)
						v.startDragAndDrop(dragData, new View.DragShadowBuilder(v), Integer.valueOf(p.optInt("id")), 0);
					else
						v.startDrag(dragData, new View.DragShadowBuilder(v), Integer.valueOf(p.optInt("id")), 0);
					return true;
				});
				View.OnDragListener dragListener = (target, event) -> {
					if (event.getAction() == android.view.DragEvent.ACTION_DROP
							&& event.getLocalState() instanceof Integer) {
						reorderProducts(rows, (Integer) event.getLocalState(), p.optInt("id"));
						return true;
					}
					return event.getAction() == android.view.DragEvent.ACTION_DRAG_STARTED
							|| event.getAction() == android.view.DragEvent.ACTION_DRAG_ENTERED
							|| event.getAction() == android.view.DragEvent.ACTION_DRAG_LOCATION
							|| event.getAction() == android.view.DragEvent.ACTION_DRAG_EXITED
							|| event.getAction() == android.view.DragEvent.ACTION_DRAG_ENDED;
				};
				setDragListenerOnTree(row, dragListener);
			}
			LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
			lp.setMargins(0, 0, 0, dp(8));
			list.addView(row, lp);
			displayed++;
		}
		if (displayed == 0)
			list.addView(label(
					needle.isEmpty() ? "No products yet. Create your first product above."
							: "No products match that search.",
					14));
	}

	@Override
	protected void startNewProduct() {
		if (contentScroll != null)
			productListScrollY = contentScroll.getScrollY();
		navigateScreen("New product", () -> async(
				() -> api.get("/api/admin/product-options"), options -> productForm(null, options)));
	}

	@Override
	protected void loadProduct(int id) {
		if (contentScroll != null)
			productListScrollY = contentScroll.getScrollY();
		navigateScreen("Edit product", () -> async(() -> {
			JSONObject result = new JSONObject();
			result.put("product", api.get("/api/admin/products/" + id));
			result.put("options", api.get("/api/admin/product-options"));
			return result;
		}, data -> productForm(data.optJSONObject("product"), data.optJSONObject("options"))));
	}

	@Override
	protected void showProductsAfterEdit() {
		if (!screenHistory.isEmpty() && "Products".equals(screenHistory.get(screenHistory.size() - 1).title)) {
			screenHistory.remove(screenHistory.size() - 1);
		}
		setScreenWithoutHistory("Products", this::loadProducts);
	}

	@Override
	protected void setDragListenerOnTree(View view, View.OnDragListener listener) {
		view.setOnDragListener(listener);
		if (view instanceof ViewGroup) {
			ViewGroup group = (ViewGroup) view;
			for (int i = 0; i < group.getChildCount(); i++)
				setDragListenerOnTree(group.getChildAt(i), listener);
		}
	}

	@Override
	protected void reorderProducts(JSONArray rows, int sourceId, int targetId) {
		if (sourceId == targetId)
			return;
		java.util.ArrayList<Integer> order = new java.util.ArrayList<>();
		int from = -1, to = -1;
		for (int i = 0; i < rows.length(); i++) {
			JSONObject row = rows.optJSONObject(i);
			if (row == null)
				continue;
			int id = row.optInt("id");
			if (id == sourceId)
				from = order.size();
			if (id == targetId)
				to = order.size();
			order.add(id);
		}
		if (from < 0 || to < 0) {
			loadProducts();
			return;
		}
		Integer moving = order.remove(from);
		order.add(to, moving);
		JSONArray ids = new JSONArray();
		for (Integer id : order)
			ids.put(id);
		asyncAction(() -> api.put("/api/admin/products/reorder", new JSONObject().put("ids", ids)), this::loadProducts);
	}

	@Override
	protected void moveProduct(int id, String direction) {
		if (contentScroll != null)
			productListScrollY = contentScroll.getScrollY();
		asyncAction(() -> api.put("/api/admin/products/" + id + "/move", new JSONObject().put("direction", direction)),
				this::loadProducts);
	}

	@Override
	protected JSONObject readTemplateValues(java.util.Map<String, EditText> fields) {
		JSONObject values = new JSONObject();
		try {
			for (java.util.Map.Entry<String, EditText> entry : fields.entrySet())
				values.put(entry.getKey(), entry.getValue().getText().toString());
		} catch (JSONException ignored) {
		}
		return values;
	}

	@Override
	protected void renderTemplateFields(LinearLayout box, JSONObject selected, JSONObject initial,
			java.util.Map<String, EditText> inputs, java.util.Map<String, Boolean> required) {
		box.removeAllViews();
		inputs.clear();
		required.clear();
		if (selected == null) {
			box.addView(label("No template selected. This product will use its own Markdown description.", 13));
			return;
		}
		JSONArray schema = selected.optJSONArray("fields_schema");
		if (schema == null || schema.length() == 0) {
			box.addView(label(
					"This template has no input fields. Add fields in Templates to make its content customizable.",
					13));
			return;
		}
		for (int i = 0; i < schema.length(); i++) {
			JSONObject spec = schema.optJSONObject(i);
			if (spec == null)
				continue;
			String key = jsonValueText(spec, "key", "");
			String fieldLabel = jsonValueText(spec, "label", key);
			String type = jsonValueText(spec, "type", "text");
			boolean hasSavedValue = initial != null && initial.has(key);
			String value = jsonValueText(initial, key, jsonValueText(spec, "default", ""));
			EditText input = field(box, fieldLabel + "  ·  " + key, value);
			input.setHint(jsonValueText(spec, "placeholder", "Enter " + fieldLabel.toLowerCase(java.util.Locale.ROOT)));
			if ("select".equals(type)) {
				JSONArray choices = spec.optJSONArray("choices");
				ArrayList<String> available = new ArrayList<>();
				if (choices != null)
					for (int choiceIndex = 0; choiceIndex < choices.length(); choiceIndex++) {
						String choice = choices.optString(choiceIndex, "").trim();
						if (!choice.isEmpty()) available.add(choice);
					}
				boolean allowBlank = !spec.optBoolean("required");
				if (hasSavedValue && value.isEmpty() && allowBlank) {
					value = "";
				} else if (!available.contains(value)) {
					String defaultValue = jsonValueText(spec, "default", "");
					value = available.contains(defaultValue) ? defaultValue
							: (spec.optBoolean("required") && !available.isEmpty() ? available.get(0) : "");
				}
				input.setText(value);
				input.setFocusable(false);
				input.setClickable(true);
				input.setInputType(android.text.InputType.TYPE_NULL);
				input.setCompoundDrawablesWithIntrinsicBounds(0, 0, android.R.drawable.arrow_down_float, 0);
				input.setOnClickListener(v -> {
					if (available.isEmpty()) return;
					ArrayList<String> optionValues = new ArrayList<>();
					ArrayList<String> optionLabels = new ArrayList<>();
					if (allowBlank) {
						optionValues.add("");
						optionLabels.add("Not specified");
					}
					optionValues.addAll(available);
					optionLabels.addAll(available);
					String[] options = optionLabels.toArray(new String[0]);
					int selectedOptionIndex = Math.max(0, optionValues.indexOf(input.getText().toString()));
					new AlertDialog.Builder(this)
						.setTitle(fieldLabel)
						.setSingleChoiceItems(options, selectedOptionIndex, (dialog, which) -> {
							input.setText(optionValues.get(which));
							dialog.dismiss();
						})
						.setNegativeButton("Cancel", null)
						.show();
				});
			} else if ("textarea".equals(type)) {
				input.setSingleLine(false);
				input.setMinLines(4);
				input.setMaxLines(12);
				input.setGravity(Gravity.TOP | Gravity.START);
				input.setVerticalScrollBarEnabled(true);
				input.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS);
				input.setOnTouchListener((view, event) -> {
					if (event.getAction() == android.view.MotionEvent.ACTION_DOWN
							|| event.getAction() == android.view.MotionEvent.ACTION_MOVE) {
						view.getParent().requestDisallowInterceptTouchEvent(true);
					} else if (event.getAction() == android.view.MotionEvent.ACTION_UP
							|| event.getAction() == android.view.MotionEvent.ACTION_CANCEL) {
						view.getParent().requestDisallowInterceptTouchEvent(false);
					}
					return false;
				});
			}
			inputs.put(key, input);
			required.put(key, spec.optBoolean("required"));
			box.addView(label("select".equals(type) ? "Choose one of the template's predefined options."
					: spec.optBoolean("markdown") ? "Markdown formatting is enabled for this value."
							: "Plain text; Markdown formatting is escaped.", 11));
		}
	}

	@Override
	protected void productForm(JSONObject p, JSONObject options) {
		clearContent();
		boolean edit = p != null;
		content.addView(label(edit ? "Edit product" : "New product", 24));
		content.addView(label("Keep product details accurate. Blank optional fields are safe to leave blank.", 13));

		sectionHeading("Product identity", "The name appears on the storefront. Slugs and SKUs should be unique.");
		EditText name = field(content, "Name", jsonValueText(p, "name", ""));
		EditText slug = field(content, "Slug", jsonValueText(p, "slug", ""));
		EditText sku = field(content, "SKU", jsonValueText(p, "sku", ""));
		EditText subtitle = field(content, "Subtitle", jsonValueText(p, "subtitle", ""));
		EditText type = field(content, "Product type", jsonValueText(p, "product_type", "general"));

		sectionHeading("Pricing", "Enter prices without currency symbols. The currency code is stored separately.");
		EditText price = field(content, "Price", jsonValueText(p, "price", "0"));
		EditText compare = field(content, "Compare-at price (optional)", jsonValueText(p, "compare_at_price", ""));
		EditText currency = field(content, "Currency code (e.g. INR or USD)", jsonValueText(p, "currency", "INR"));

		sectionHeading("Publishing", "Draft products are not shown as active products on the storefront.");
		EditText status = field(content, "Status", optionLabel(jsonValueText(p, "status", "draft")));
		status.setFocusable(false);
		status.setClickable(true);
		status.setInputType(android.text.InputType.TYPE_NULL);
		status.setCompoundDrawablesWithIntrinsicBounds(0, 0, android.R.drawable.arrow_down_float, 0);
		status.setOnClickListener(v -> {
			String[] choices = {"Draft", "Active", "Archived"};
			String current = status.getText().toString().trim().toLowerCase(java.util.Locale.ROOT);
			int selected = "active".equals(current) ? 1 : "archived".equals(current) ? 2 : 0;
			new AlertDialog.Builder(this).setTitle("Product status")
					.setSingleChoiceItems(choices, selected, (dialog, which) -> {
						status.setText(choices[which]);
						dialog.dismiss();
					}).setNegativeButton("Cancel", null).show();
		});
		content.addView(label("Visibility", 13));
		Switch visibility = new Switch(this);
		visibility.setText("Visible on the public storefront");
		visibility.setTextColor(foregroundColor());
		visibility.setChecked("public".equalsIgnoreCase(jsonValueText(p, "visibility", "public")));
		content.addView(visibility);
		EditText position = field(content, "Display order", jsonValueText(p, "position", "0"));
		CheckBox featured = check("Featured", p != null && p.optBoolean("featured"));
		content.addView(featured);
		EditText badge = field(content, "Badge", jsonValueText(p, "badge", ""));

		sectionHeading("Inventory", "Turn off tracking for items that do not have a meaningful stock count.");
		EditText stock = field(content, "Stock count", jsonValueText(p, "stock_count", "0"));
		CheckBox track = check("Track inventory", p == null || p.optBoolean("track_inventory", true));
		content.addView(track);
		EditText threshold = field(content, "Low stock warning threshold",
				jsonValueText(p, "low_stock_threshold", "2"));

		sectionHeading("Description template",
				"Choose a reusable product structure. Template products only show the fields defined by that template.");
		JSONObject productMeta = p == null ? new JSONObject() : p.optJSONObject("meta");
		if (productMeta == null)
			productMeta = new JSONObject();
		JSONObject savedTemplateValues = productMeta.optJSONObject("template_values");
		JSONArray templateOptions = options == null ? new JSONArray() : options.optJSONArray("templates");
		EditText template = new EditText(this);
		template.setText(jsonValueText(p, "description_template_id", ""));
		template.setVisibility(View.GONE);
		content.addView(template);
		TextView templateSummary = label("No template selected · custom Markdown description", 13);
		content.addView(templateSummary);
		LinearLayout manualDescription = column(0);
		EditText description = field(manualDescription, "Product description (Markdown)",
				jsonValueText(p, "description", ""));
		description.setMinLines(5);
		description.setMaxLines(18);
		description.setGravity(Gravity.TOP | Gravity.START);
		manualDescription.addView(button("Preview description", v -> previewMarkdown(
				description.getText().toString(), "Product description preview",
				buildProductPreviewContext(name, slug, subtitle, description, price, currency))));
		LinearLayout templateFields = column(0);
		java.util.LinkedHashMap<String, EditText> templateInputs = new java.util.LinkedHashMap<>();
		java.util.LinkedHashMap<String, Boolean> templateRequired = new java.util.LinkedHashMap<>();
		JSONObject initiallySelected = rowById(templateOptions,
				template.getText().toString().trim().isEmpty() ? 0 : parseInteger(template, "Template", 0));
		if (initiallySelected != null) {
			templateSummary.setText(initiallySelected.optString("name")
					+ (initiallySelected.optBoolean("is_active", true) ? "" : " · inactive template"));
			manualDescription.setVisibility(View.GONE);
		} else {
			template.setText("");
		}
		renderTemplateFields(templateFields, initiallySelected,
				savedTemplateValues == null ? new JSONObject() : savedTemplateValues, templateInputs, templateRequired);
		content.addView(button("Choose template", v -> {
			String[] names = new String[(templateOptions == null ? 0 : templateOptions.length()) + 1];
			names[0] = "No template · custom Markdown";
			if (templateOptions != null)
				for (int i = 0; i < templateOptions.length(); i++) {
					JSONObject item = templateOptions.optJSONObject(i);
					names[i + 1] = (item == null ? "Unnamed template" : item.optString("name", "Unnamed template"))
							+ (item != null && !item.optBoolean("is_active", true) ? " (inactive)" : "");
				}
			int currentId = 0;
			try {
				currentId = Integer.parseInt(template.getText().toString().trim());
			} catch (Exception ignored) {
			}
			int checked = 0;
			if (templateOptions != null)
				for (int i = 0; i < templateOptions.length(); i++) {
					JSONObject item = templateOptions.optJSONObject(i);
					if (item != null && item.optInt("id") == currentId)
						checked = i + 1;
				}
			new AlertDialog.Builder(this).setTitle("Description template")
					.setSingleChoiceItems(names, checked, (dialog, which) -> {
						JSONObject currentValues = readTemplateValues(templateInputs);
						JSONObject selected = which == 0 ? null : templateOptions.optJSONObject(which - 1);
						template.setText(selected == null ? "" : String.valueOf(selected.optInt("id")));
						templateSummary.setText(selected == null ? "No template selected · custom Markdown description"
								: selected.optString("name")
										+ (selected.optBoolean("is_active", true) ? "" : " · inactive template"));
						manualDescription.setVisibility(selected == null ? View.VISIBLE : View.GONE);
						renderTemplateFields(templateFields, selected, currentValues, templateInputs, templateRequired);
						dialog.dismiss();
					}).setNegativeButton("Cancel", null).show();
		}));
		content.addView(manualDescription);
		content.addView(templateFields);
		EditText material = field(content, "Material (legacy / optional)", jsonValueText(p, "material", ""));
		EditText care = field(content, "Care instructions (legacy / optional)", jsonValueText(p, "care", ""));
		EditText dimensions = field(content, "Dimensions (legacy / optional)", jsonValueText(p, "dimensions", ""));
		EditText shipping = field(content, "Shipping note (legacy / optional)", jsonValueText(p, "shipping_note", ""));
		material.setVisibility(View.GONE);
		care.setVisibility(View.GONE);
		dimensions.setVisibility(View.GONE);
		shipping.setVisibility(View.GONE);

		sectionHeading("Production handling",
				"Mark unusually difficult or valuable pieces so the production queue flags them.");
		CheckBox specialCare = check("Requires special care during production",
				p != null && p.optBoolean("special_care"));
		content.addView(specialCare);
		EditText productionNotes = field(content, "Maker / production instructions",
				jsonValueText(p, "production_notes", ""));
		productionNotes.setMinLines(3);
		productionNotes.setMaxLines(10);
		productionNotes.setGravity(Gravity.TOP | Gravity.START);

		sectionHeading("Categories and catalog",
				"Choose categories by name rather than copying IDs. Manage product images in the image editor below.");
		EditText tags = field(content, "Tags (comma-separated)",
				separatedArray(p == null ? null : p.optJSONArray("tags"), ", "));
		EditText categories = new EditText(this);
		categories.setText(separatedArray(p == null ? null : p.optJSONArray("category_ids"), ", "));
		categories.setVisibility(View.GONE);
		content.addView(categories);
		TextView categorySummary = label("No categories selected", 13);
		content.addView(categorySummary);
		JSONArray categoryOptions = options == null ? new JSONArray() : options.optJSONArray("categories");
		java.util.Set<Integer> chosenCategories = new java.util.LinkedHashSet<>();
		try {
			JSONArray initialIds = parseCategoryIds(categories.getText().toString());
			for (int i = 0; i < initialIds.length(); i++)
				chosenCategories.add(initialIds.getInt(i));
		} catch (Exception ignored) {
		}
		categorySummary.setText(categorySummaryText(categoryOptions, chosenCategories));
		content.addView(button("Choose categories", v -> {
			if (categoryOptions == null || categoryOptions.length() == 0) {
				Toast.makeText(this, "Create a category first in Categories.", Toast.LENGTH_SHORT).show();
				return;
			}
			String[] names = new String[categoryOptions.length()];
			boolean[] checked = new boolean[categoryOptions.length()];
			for (int i = 0; i < categoryOptions.length(); i++) {
				JSONObject item = categoryOptions.optJSONObject(i);
				names[i] = categoryOptionLabel(item, categoryOptions)
						+ (item != null && !item.optBoolean("visible", true) ? " (hidden)" : "");
				checked[i] = item != null && chosenCategories.contains(item.optInt("id"));
			}
			new AlertDialog.Builder(this).setTitle("Product categories")
					.setMultiChoiceItems(names, checked, (dialog, which, selected) -> {
						JSONObject item = categoryOptions.optJSONObject(which);
						if (item == null)
							return;
						if (selected)
							chosenCategories.add(item.optInt("id"));
						else
							chosenCategories.remove(item.optInt("id"));
					}).setNegativeButton("Cancel", null).setPositiveButton("Apply", (dialog, which) -> {
						StringBuilder ids = new StringBuilder();
						for (Integer id : chosenCategories) {
							if (ids.length() > 0)
								ids.append(", ");
							ids.append(id);
						}
						categories.setText(ids.toString());
						categorySummary.setText(categorySummaryText(categoryOptions, chosenCategories));
					}).show();
		}));
		ProductFormEditors.ImageEditor imageEditor = new ProductFormEditors.ImageEditor(this,
				p == null ? null : p.optJSONArray("images"));
		content.addView(imageEditor.container);
		content.addView(imageEditor.serialized);
		ProductFormEditors.VariantEditor variantEditor = new ProductFormEditors.VariantEditor(this,
				p == null ? null : p.optJSONArray("variants"));
		content.addView(variantEditor.container);
		content.addView(variantEditor.serialized);

		sectionHeading("Sizing", "Leave size mode as none for products without customer sizing options.");
		EditText sizeMode = field(content, "Sizing options",
				sizeModeLabel(productMeta.optString("size_mode", "none")));
		sizeMode.setFocusable(false);
		sizeMode.setClickable(true);
		sizeMode.setInputType(android.text.InputType.TYPE_NULL);
		sizeMode.setCompoundDrawablesWithIntrinsicBounds(0, 0, android.R.drawable.arrow_down_float, 0);
		sizeMode.setOnClickListener(v -> {
			String[] labels = {"No sizing", "Predefined sizes", "Custom measurements", "Both"};
			String[] values = {"none", "predefined", "custom", "both"};
			int selected = 0;
			String currentMode = normalizeSizeMode(sizeMode.getText().toString());
			for (int i = 0; i < values.length; i++)
				if (values[i].equals(currentMode)) selected = i;
			new AlertDialog.Builder(this).setTitle("Sizing options")
					.setSingleChoiceItems(labels, selected, (dialog, which) -> {
						sizeMode.setText(labels[which]);
						dialog.dismiss();
					}).setNegativeButton("Cancel", null).show();
		});
		JSONArray predefined = productMeta.optJSONArray("predefined_sizes");
		JSONArray customFields = productMeta.optJSONArray("custom_size_fields");
		EditText predefinedSizes = field(content, "Predefined sizes (comma-separated)",
				separatedArray(predefined, ", "));
		EditText customSizeFields = field(content, "Custom measurement fields (comma-separated)",
				customFields == null ? "width, length" : separatedArray(customFields, ", "));
		sectionHeading("Search engine details", "Optional metadata used by search engines and link previews.");
		EditText seoTitle = field(content, "SEO title", jsonValueText(p, "seo_title", ""));
		EditText seoDescription = field(content, "SEO description", jsonValueText(p, "seo_description", ""));
		EditText meta = field(content, "Advanced metadata (JSON object)", jsonObjectText(productMeta));
		content.addView(button("Preview product card", v -> launchProductPreview(
				name, slug, sku, subtitle, type, price, currency, status, visibility, stock, track,
				description, template, templateOptions, templateInputs, imageEditor.serialized,
				variantEditor.serialized, sizeMode, predefinedSizes, customSizeFields, tags, meta, false)));
		content.addView(button("Preview product page", v -> launchProductPreview(
				name, slug, sku, subtitle, type, price, currency, status, visibility, stock, track,
				description, template, templateOptions, templateInputs, imageEditor.serialized,
				variantEditor.serialized, sizeMode, predefinedSizes, customSizeFields, tags, meta, true)));

		Runnable persistProduct = () -> {
			JSONObject templateValues = readTemplateValues(templateInputs);
			for (java.util.Map.Entry<String, Boolean> item : templateRequired.entrySet()) {
				if (item.getValue() && templateValues.optString(item.getKey(), "").trim().isEmpty()) {
					new AlertDialog.Builder(this).setTitle("Missing template field")
							.setMessage("Fill in the required field: " + item.getKey()).setPositiveButton("OK", null)
							.show();
					return;
				}
			}
			asyncSaveProduct(
					edit ? p.optInt("id") : 0, name, slug, sku, subtitle, type, price, position, currency,
					compare, status, visibility, featured, stock, track, threshold, badge, sizeMode,
					predefinedSizes, customSizeFields, material, care, dimensions, shipping, description,
					template, tags, categories, imageEditor.serialized, variantEditor.serialized, meta, seoTitle,
					seoDescription,
					specialCare, productionNotes, templateValues, this::showProductsAfterEdit);
		};
		Runnable saveProduct = () -> {
			if (!variantEditor.isValid()) {
				new AlertDialog.Builder(this).setTitle("Check product variants")
						.setMessage(
								"Give each variant a name, use a valid non-negative price, and enter a whole-number stock count of zero or more.")
						.setPositiveButton("OK", null).show();
				return;
			}
			persistProduct.run();
		};
		content.addView(button("Save product", v -> saveProduct.run()));
		if (stickyActions != null) {
			stickyActions.removeAllViews();
			Button fixedSave = button("Save product", v -> saveProduct.run());
			fixedSave.setTextColor(Color.WHITE);
			fixedSave.setBackground(outline(Color.parseColor(darkMode ? "#3b82f6" : "#17191b"),
					Color.parseColor(darkMode ? "#3b82f6" : "#17191b")));
			stickyActions.addView(fixedSave, new LinearLayout.LayoutParams(-1, -2));
			stickyActions.setVisibility(View.VISIBLE);
		}
		if (edit) {
			content.addView(button("Delete product", v -> confirm(
					"Delete product?",
					"This permanently deletes “" + jsonValueText(p, "name", "this product")
							+ "”. This cannot be undone.",
					() -> asyncAction(() -> api.delete("/api/admin/products/" + p.optInt("id")),
							this::showProductsAfterEdit))));
		}
	}

	private String optionLabel(String value) {
		String normalized = value == null ? "" : value.trim().toLowerCase(java.util.Locale.ROOT);
		if (normalized.isEmpty())
			return "Draft";
		return Character.toUpperCase(normalized.charAt(0)) + normalized.substring(1);
	}

	private String normalizeSizeMode(String value) {
		String normalized = value == null ? "" : value.trim().toLowerCase(java.util.Locale.ROOT);
		switch (normalized) {
			case "predefined sizes":
				return "predefined";
			case "custom measurements":
				return "custom";
			case "no sizing":
				return "none";
			case "none":
			case "predefined":
			case "custom":
			case "both":
				return normalized;
			default:
				return "none";
		}
	}

	private String sizeModeLabel(String value) {
		switch (normalizeSizeMode(value)) {
			case "predefined":
				return "Predefined sizes";
			case "custom":
				return "Custom measurements";
			case "both":
				return "Both";
			default:
				return "No sizing";
		}
	}

	private void launchProductPreview(
			EditText name, EditText slug, EditText sku, EditText subtitle, EditText type,
			EditText price, EditText currency, EditText status, Switch visibility,
			EditText stock, CheckBox track, EditText description, EditText template,
			JSONArray templateOptions, java.util.Map<String, EditText> templateInputs,
			EditText images, EditText variants, EditText sizeMode, EditText predefinedSizes,
			EditText customSizeFields, EditText tags, EditText meta, boolean detailPage) {
		try {
			JSONObject product = new JSONObject();
			product.put("id", 0);
			product.put("name", name.getText().toString().trim());
			product.put("slug", slug.getText().toString().trim());
			product.put("sku", sku.getText().toString().trim());
			product.put("subtitle", subtitle.getText().toString().trim());
			product.put("product_type", type.getText().toString().trim());
			product.put("price", price.getText().toString().trim().isEmpty() ? "0" : price.getText().toString().trim());
			product.put("currency", currency.getText().toString().trim().toUpperCase(java.util.Locale.ROOT));
			product.put("description", description.getText().toString());
			product.put("status", status.getText().toString());
			product.put("visibility", visibility.isChecked() ? "public" : "hidden");
			product.put("stock_count", stock.getText().toString().trim().isEmpty() ? 0 : Integer.parseInt(stock.getText().toString().trim()));
			product.put("track_inventory", track.isChecked());
			product.put("tags", parseStringArray(tags.getText().toString(), "Tags"));
			product.put("images", parseImages(images.getText().toString()));
			product.put("variants", new JSONArray(variants.getText().toString().trim().isEmpty() ? "[]" : variants.getText().toString()));

			JSONObject metadata;
			try {
				metadata = new JSONObject(meta.getText().toString().trim().isEmpty() ? "{}" : meta.getText().toString());
			} catch (JSONException error) {
				throw new IllegalArgumentException("Advanced metadata must be a valid JSON object before previewing.");
			}
			metadata.put("size_mode", normalizeSizeMode(sizeMode.getText().toString()));
			metadata.put("predefined_sizes", parseStringArray(predefinedSizes.getText().toString(), "Predefined sizes"));
			metadata.put("custom_size_fields", parseStringArray(customSizeFields.getText().toString(), "Custom measurement fields"));
			int templateId = template.getText().toString().trim().isEmpty() ? 0
					: Integer.parseInt(template.getText().toString().trim());
			JSONObject selectedTemplate = rowById(templateOptions, templateId);
			JSONObject values = readTemplateValues(templateInputs);
			if (selectedTemplate != null) {
				metadata.put("template_values", values);
			} else {
				metadata.remove("template_values");
			}
			product.put("meta", metadata);

			JSONObject templateData = new JSONObject();
			if (selectedTemplate != null) {
				templateData.put("body_markdown", selectedTemplate.optString("body_markdown", ""));
				templateData.put("fields_schema", selectedTemplate.optJSONArray("fields_schema") == null
						? new JSONArray() : selectedTemplate.optJSONArray("fields_schema"));
			}
			JSONObject payload = new JSONObject();
			payload.put("product", product);
			payload.put("template", templateData);
			previewProduct(payload, detailPage);
		} catch (JSONException | IllegalArgumentException error) {
			String message = error.getMessage() == null ? "Could not prepare the product preview." : error.getMessage();
			Toast.makeText(this, message, Toast.LENGTH_LONG).show();
		}
	}

	@Override
	protected void asyncSaveProduct(
			int id,
			EditText name,
			EditText slug,
			EditText sku,
			EditText subtitle,
			EditText type,
			EditText price,
			EditText position,
			EditText currency,
			EditText compare,
			EditText status,
			Switch visibility,
			CheckBox featured,
			EditText stock,
			CheckBox track,
			EditText threshold,
			EditText badge,
			EditText sizeMode,
			EditText predefinedSizes,
			EditText customSizeFields,
			EditText material,
			EditText care,
			EditText dimensions,
			EditText shipping,
			EditText description,
			EditText template,
			EditText tags,
			EditText categories,
			EditText images,
			EditText variants,
			EditText meta,
			EditText seoTitle,
			EditText seoDescription,
			CheckBox specialCare,
			EditText productionNotes,
			JSONObject templateValues,
			Runnable onSaved) {
		// Read and validate Android views on the UI thread. Only the API request runs
		// in the executor.
		try {
			String productName = name.getText().toString().trim();
			String productSlug = slug.getText().toString().trim();
			String productSku = sku.getText().toString().trim();
			if (productName.isEmpty())
				throw new IllegalArgumentException("Name is required.");
			if (productSlug.isEmpty())
				throw new IllegalArgumentException("Slug is required.");
			if (productSku.isEmpty())
				throw new IllegalArgumentException("SKU is required.");
			String priceValue = price.getText().toString().trim();
			if (priceValue.isEmpty())
				throw new IllegalArgumentException("Price is required.");
			try {
				new java.math.BigDecimal(priceValue);
			} catch (NumberFormatException e) {
				throw new IllegalArgumentException("Price must be a valid number, for example 1299 or 1299.50.");
			}
			String compareValue = compare.getText().toString().trim();
			if (!compareValue.isEmpty()) {
				try {
					new java.math.BigDecimal(compareValue);
				} catch (NumberFormatException e) {
					throw new IllegalArgumentException("Compare-at price must be blank or a valid number.");
				}
			}
			String currencyValue = currency.getText().toString().trim().toUpperCase(java.util.Locale.ROOT);
			if (!currencyValue.matches("[A-Z]{3}"))
				throw new IllegalArgumentException("Currency must be a three-letter code, such as INR.");
			String statusValue = status.getText().toString().trim().toLowerCase(java.util.Locale.ROOT);
			if (!java.util.Arrays.asList("draft", "active", "archived").contains(statusValue)) {
				throw new IllegalArgumentException("Status must be draft, active, or archived.");
			}
			String visibilityValue = visibility.isChecked() ? "public" : "hidden";
			int stockValue = parseInteger(stock, "Stock count", 0);
			int thresholdValue = parseInteger(threshold, "Low stock warning threshold", 2);
			if (stockValue < 0)
				throw new IllegalArgumentException("Stock count cannot be negative.");
			if (thresholdValue < 0)
				throw new IllegalArgumentException("Low stock warning threshold cannot be negative.");
			String sizeModeValue = normalizeSizeMode(sizeMode.getText().toString());
			if (!java.util.Arrays.asList("none", "predefined", "custom", "both").contains(sizeModeValue)) {
				throw new IllegalArgumentException("Size mode must be none, predefined, custom, or both.");
			}
			String templateValue = template.getText().toString().trim();
			int templateId = templateValue.isEmpty() ? 0 : parseInteger(template, "Description template ID", 0);
			if (!templateValue.isEmpty() && templateId < 1)
				throw new IllegalArgumentException(
						"Description template ID must be a positive whole number or left blank.");

			JSONObject b = new JSONObject();
			b.put("name", productName);
			b.put("slug", productSlug);
			b.put("sku", productSku);
			b.put("subtitle", subtitle.getText().toString().trim());
			b.put("product_type",
					type.getText().toString().trim().isEmpty() ? "general" : type.getText().toString().trim());
			b.put("price", priceValue);
			b.put("position", parseInteger(position, "Display order", 0));
			b.put("currency", currencyValue);
			b.put("compare_at_price", compareValue.isEmpty() ? JSONObject.NULL : compareValue);
			b.put("status", statusValue);
			b.put("visibility", visibilityValue);
			b.put("featured", featured.isChecked());
			b.put("stock_count", stockValue);
			b.put("track_inventory", track.isChecked());
			b.put("low_stock_threshold", thresholdValue);
			b.put("badge", badge.getText().toString().trim());
			b.put("description_template_id", templateValue.isEmpty() ? JSONObject.NULL : templateId);
			b.put("material", material.getText().toString().trim());
			b.put("care", care.getText().toString());
			b.put("dimensions", dimensions.getText().toString().trim());
			b.put("shipping_note", shipping.getText().toString());
			b.put("special_care", specialCare.isChecked());
			b.put("production_notes", productionNotes.getText().toString());
			b.put("description", templateValue.isEmpty() ? description.getText().toString() : "");
			b.put("tags", parseStringArray(tags.getText().toString(), "Tags"));
			b.put("category_ids", parseCategoryIds(categories.getText().toString()));
			b.put("images", parseImages(images.getText().toString()));
			String variantsValue = variants.getText().toString().trim();
			try {
				b.put("variants", variantsValue.isEmpty() ? new JSONArray() : new JSONArray(variantsValue));
			} catch (JSONException e) {
				throw new IllegalArgumentException(
						"Variants must be a valid JSON array. Use [] when there are no variants.");
			}
			JSONObject metadata;
			try {
				metadata = new JSONObject(
						meta.getText().toString().trim().isEmpty() ? "{}" : meta.getText().toString());
			} catch (JSONException e) {
				throw new IllegalArgumentException("Advanced metadata must be a valid JSON object, for example {}.");
			}
			metadata.put("size_mode", sizeModeValue);
			if (templateValue.isEmpty())
				metadata.remove("template_values");
			else
				metadata.put("template_values", templateValues == null ? new JSONObject() : templateValues);
			metadata.put("predefined_sizes",
					parseStringArray(predefinedSizes.getText().toString(), "Predefined sizes"));
			metadata.put("custom_size_fields",
					parseStringArray(customSizeFields.getText().toString(), "Custom measurement fields"));
			b.put("meta", metadata);
			b.put("seo_title", seoTitle.getText().toString().trim());
			b.put("seo_description", seoDescription.getText().toString().trim());

			asyncAction(() -> {
				if (id == 0)
					api.post("/api/admin/products", b);
				else
					api.put("/api/admin/products/" + id, b);
			}, onSaved);
		} catch (Exception error) {
			String message = error.getMessage() == null || error.getMessage().trim().isEmpty()
					? "Please check the product fields and try again."
					: error.getMessage();
			new AlertDialog.Builder(this).setTitle("Check product details").setMessage(message)
					.setPositiveButton("OK", null).show();
		}
	}
}
