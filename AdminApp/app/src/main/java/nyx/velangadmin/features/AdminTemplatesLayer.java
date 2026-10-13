package nyx.velangadmin.features;

import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import nyx.velangadmin.R;
import nyx.velangadmin.TemplateFieldsEditor;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import static nyx.velangadmin.AdminJson.*;

public abstract class AdminTemplatesLayer extends AdminCategoriesLayer {
	@Override
	protected void loadTemplates() {
		async(
				() -> api.get("/api/admin/templates"),
				data -> {
					clearContent();
					content.addView(iconButton(R.drawable.ic_add, "New template", v -> templateForm(null)));
					JSONArray rows = data.optJSONArray("templates");
					if (rows == null)
						return;
					for (int i = 0; i < rows.length(); i++) {
						JSONObject t = rows.optJSONObject(i);
						if (t == null)
							continue;
						LinearLayout row = column(10);
						row.setBackground(outline(SURFACE, BORDER));
						LinearLayout heading = new LinearLayout(this);
						heading.setGravity(android.view.Gravity.CENTER_VERTICAL);
						TextView name = label(t.optString("name", "Untitled template"), 17);
						name.setTypeface(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD);
						heading.addView(name, new LinearLayout.LayoutParams(0, -2, 1));
						heading.addView(iconButton(R.drawable.ic_edit, "Edit template", v -> templateForm(t)));
						heading.addView(iconButton(R.drawable.ic_delete, "Delete template", v -> deleteTemplate(t)));
						row.addView(heading);
						row.addView(label(t.optString("product_type", "general") + " · "
								+ t.optInt("field_count", (t.optJSONArray("fields_schema") == null ? 0 : t.optJSONArray("fields_schema").length()))
								+ " fields · " + t.optInt("assigned_products") + " products"
								+ (t.optBoolean("is_active", true) ? " · Active" : " · Inactive"), 12));
						content.addView(row);
					}
				});
	}

	@Override
	protected void templateForm(JSONObject t) {
		clearContent();
		content.addView(
				label(t == null ? "New description template" : "Edit description template", 23));
		EditText name = field(content, "Name", t == null ? "" : t.optString("name"));
		EditText type = field(content, "Product type", t == null ? "general" : t.optString("product_type"));
		EditText body = field(
				content,
				"Markdown + Jinja body",
				t == null
						? "# {{ product.name }}\n\n{{ product.description }}\n\n**SKU:** {{ product.sku }}\n"
						: t.optString("body_markdown"));
		JSONArray initialSchema = t == null ? new JSONArray() : t.optJSONArray("fields_schema");
		TemplateFieldsEditor fieldsEditor = new TemplateFieldsEditor(this, initialSchema);
		content.addView(fieldsEditor.container);
		CheckBox active = check("Active", t == null || t.optBoolean("is_active", true));
		content.addView(active);
		content.addView(
				label(
						"Template fields available under {{ product }} include name, subtitle, price, SKU, type, material, care, dimensions, shipping_note, tags and meta. Rendering is sandboxed and sanitized on the server.",
						13));
		content.addView(button("Preview on storefront", v -> {
			try {
				JSONObject sample = new JSONObject();
				sample.put("id", 0);
				sample.put("name", "Example product");
				sample.put("slug", "example-product");
				sample.put("sku", "DEMO-001");
				sample.put("description", "A short sample product description.");
				sample.put("subtitle", "Everyday essential");
				sample.put("price", "1299.00");
				sample.put("currency", "INR");
				sample.put("product_type", type.getText().toString());
				sample.put("material", "Cotton");
				sample.put("care", "Cold wash");
				sample.put("dimensions", "30 × 20 cm");
				sample.put("shipping_note", "Ships in 2–4 business days");
				sample.put("tags", new JSONArray().put("sample").put("everyday"));
				JSONArray images = new JSONArray();
				sample.put("images", images);
				JSONObject sampleMeta = new JSONObject();
				JSONObject sampleFields = new JSONObject();
				JSONArray sampleSchema = fieldsEditor.valuesForSave();
				for (int i = 0; i < sampleSchema.length(); i++) {
					JSONObject spec = sampleSchema.optJSONObject(i);
					if (spec == null)
						continue;
					String key = spec.optString("key", "");
					if (key.isEmpty())
						continue;
					String sampleValue = spec.optString("default", "");
					if (sampleValue.isEmpty() && "select".equals(spec.optString("type"))) {
						JSONArray choices = spec.optJSONArray("choices");
						if (choices != null && choices.length() > 0)
							sampleValue = choices.optString(0, "");
					} else if (sampleValue.isEmpty()) {
						sampleValue = "Sample " + spec.optString("label", key) + " value.";
					}
					sampleFields.put(key, sampleValue);
				}
				sampleMeta.put("template_values", sampleFields);
				sample.put("meta", sampleMeta);
				JSONObject preview = new JSONObject();
				preview.put("mode", "product");
				preview.put("product", sample);
				preview.put("template", new JSONObject()
						.put("body_markdown", body.getText().toString())
						.put("fields_schema", sampleSchema));
				previewProduct(preview, true);
			} catch (JSONException | IllegalArgumentException error) {
				Toast.makeText(this, error.getMessage() == null ? "Check the template fields." : error.getMessage(), Toast.LENGTH_LONG).show();
			}
		}));
		content.addView(button("Save template", v -> {
			try {
				JSONObject b = new JSONObject();
				b.put("name", name.getText().toString().trim());
				b.put("product_type", type.getText().toString().trim());
				b.put("body_markdown", body.getText().toString());
				b.put("fields_schema", fieldsEditor.valuesForSave());
				b.put("is_active", active.isChecked());
				asyncAction(() -> {
					if (t == null)
						api.post("/api/admin/templates", b);
					else
						api.put("/api/admin/templates/" + t.optInt("id"), b);
				}, this::loadTemplates);
			} catch (JSONException | IllegalArgumentException error) {
				Toast.makeText(this, error.getMessage() == null ? "Check the template fields." : error.getMessage(),
						Toast.LENGTH_LONG).show();
			}
		}));
		if (t != null)
			content.addView(button("Delete template", v -> deleteTemplate(t)));
	}

	private void deleteTemplate(JSONObject template) {
		String name = template.optString("name", "this template");
		int assigned = template.optInt("assigned_products", 0);
		if (assigned > 0) {
			new android.app.AlertDialog.Builder(this).setTitle("Template is in use")
					.setMessage("“" + name + "” is assigned to " + assigned
							+ " product(s). Reassign those products before deleting this template so their descriptions remain intact.")
					.setPositiveButton("Got it", null).show();
			return;
		}
		String message = "Delete ‘" + name + "’? This cannot be undone.";
		confirm("Delete template?", message, () -> {
			asyncAction(() -> api.delete("/api/admin/templates/" + template.optInt("id")), this::loadTemplates);
		});
	}
}
