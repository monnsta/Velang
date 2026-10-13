package nyx.velangadmin.features;

import android.app.AlertDialog;
import android.view.Gravity;
import android.view.View;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.ArrayList;
import nyx.velangadmin.R;
import org.json.JSONArray;
import org.json.JSONObject;
import static nyx.velangadmin.AdminJson.*;

public abstract class AdminCategoriesLayer extends AdminProductsLayer {
	@Override
	protected void loadCategories() {
		async(
				() -> api.get("/api/admin/categories"),
				data -> {
					clearContent();
					JSONArray resultRows = data.optJSONArray("categories");
					final JSONArray rows = resultRows == null ? new JSONArray() : resultRows;
					content.addView(iconButton(R.drawable.ic_add, "New category", v -> categoryForm(null, rows)));
					for (int i = 0; i < rows.length(); i++) {
						JSONObject c = rows.optJSONObject(i);
						LinearLayout row = column(10);
					row.setBackground(outline(SURFACE, BORDER));
						row.addView(label(c.optString("name"), 18));
						String parent = c.isNull("parent_id") ? "top level" : "parent ID " + c.optInt("parent_id");
						row.addView(
								label(
										"ID " + c.optInt("id") + " · " + parent + " · " + c.optString("slug") + " · "
												+ (c.optBoolean("visible") ? "visible" : "hidden"),
										13));
						row.addView(iconButton(R.drawable.ic_edit, "Edit category", v -> categoryForm(c, rows)));
						content.addView(row);
					}
				});
	}

	@Override
	protected boolean categoryWouldCreateCycle(JSONObject candidate, JSONArray all, int currentId) {
		if (currentId <= 0 || candidate == null)
			return false;
		java.util.Set<Integer> seen = new java.util.HashSet<>();
		int cursor = candidate.optInt("id");
		while (cursor > 0 && seen.add(cursor)) {
			if (cursor == currentId)
				return true;
			JSONObject row = rowById(all, cursor);
			if (row == null)
				return false;
			cursor = row.optInt("parent_id", 0);
		}
		return false;
	}

	@Override
	protected void categoryForm(JSONObject c, JSONArray knownCategories) {
		clearContent();
		content.addView(label(c == null ? "New category" : "Edit category", 23));
		EditText name = field(content, "Name", c == null ? "" : c.optString("name"));
		EditText slug = field(content, "Slug", c == null ? "" : c.optString("slug"));
		EditText desc = field(content, "Description", c == null ? "" : c.optString("description"));
		desc.setMinLines(3);
		desc.setGravity(Gravity.TOP | Gravity.START);
		content.addView(button("Preview description",
				v -> previewMarkdown(desc.getText().toString(), "Category description preview")));
		EditText image = field(content, "Image path", c == null ? "" : c.optString("image_path"));
		content.addView(button("Choose image from asset library",
				v -> chooseAsset(asset -> image.setText(jsonValueText(asset, "path", "")))));
		EditText pos = field(content, "Position", c == null ? "0" : String.valueOf(c.optInt("position")));
		EditText parentId = new EditText(this);
		parentId.setText((c == null || c.isNull("parent_id")) ? "" : String.valueOf(c.optInt("parent_id")));
		parentId.setVisibility(View.GONE);
		content.addView(parentId);
		int editingCategoryId = c == null ? 0 : c.optInt("id");
		int initialParentId = parentId.getText().length() == 0 ? 0 : parseInteger(parentId, "Parent category", 0);
		JSONObject initialParent = rowById(knownCategories, initialParentId);
		if (initialParent == null)
			parentId.setText("");
		TextView parentSummary = label(
				"Parent: "
						+ (initialParent == null ? "Top level" : categoryOptionLabel(initialParent, knownCategories)),
				13);
		content.addView(parentSummary);
		content.addView(button("Choose parent category", v -> {
			java.util.ArrayList<Integer> parentIds = new java.util.ArrayList<>();
			java.util.ArrayList<String> parentNames = new java.util.ArrayList<>();
			parentIds.add(0);
			parentNames.add("Top level (no parent)");
			if (knownCategories != null)
				for (int i = 0; i < knownCategories.length(); i++) {
					JSONObject candidate = knownCategories.optJSONObject(i);
					if (candidate == null || candidate.optInt("id") == editingCategoryId
							|| categoryWouldCreateCycle(candidate, knownCategories, editingCategoryId))
						continue;
					parentIds.add(candidate.optInt("id"));
					parentNames.add(categoryOptionLabel(candidate, knownCategories));
				}
			int checked = 0;
			for (int i = 0; i < parentIds.size(); i++) {
				if (String.valueOf(parentIds.get(i)).equals(parentId.getText().toString().trim()))
					checked = i;
			}
			new AlertDialog.Builder(this).setTitle("Parent category")
					.setSingleChoiceItems(parentNames.toArray(new String[0]), checked, (dialog, which) -> {
						int selected = parentIds.get(which);
						parentId.setText(selected == 0 ? "" : String.valueOf(selected));
						JSONObject selectedRow = selected == 0 ? null : rowById(knownCategories, selected);
						parentSummary.setText("Parent: " + (selectedRow == null ? "Top level"
								: categoryOptionLabel(selectedRow, knownCategories)));
						dialog.dismiss();
					}).setNegativeButton("Cancel", null).show();
		}));
		CheckBox visible = check("Visible", c == null || c.optBoolean("visible", true));
		content.addView(visible);
		EditText seo = field(content, "SEO title", c == null ? "" : c.optString("seo_title"));
		EditText seod = field(content, "SEO description", c == null ? "" : c.optString("seo_description"));
		EditText meta = field(content, "Metadata JSON", c == null ? "{}" : jsonObjectText(c.optJSONObject("meta")));
		content.addView(
				button(
						"Save category",
						v -> asyncAction(
								() -> {
									JSONObject b = new JSONObject();
									b.put("name", name.getText().toString());
									b.put("slug", slug.getText().toString());
									b.put("description", desc.getText().toString());
									b.put("image_path", image.getText().toString());
									b.put("position", parseInteger(pos, "Position", 0));
									String parent = parentId.getText().toString().trim();
									b.put("parent_id", parent.isEmpty() ? JSONObject.NULL : Integer.parseInt(parent));
									b.put("is_visible", visible.isChecked());
									b.put("seo_title", seo.getText().toString());
									b.put("seo_description", seod.getText().toString());
									JSONObject metadata = new JSONObject(
											meta.getText().toString().trim().isEmpty() ? "{}"
													: meta.getText().toString());
									b.put("meta", metadata);
									if (c == null)
										api.post("/api/admin/categories", b);
									else
										api.put("/api/admin/categories/" + c.optInt("id"), b);
								},
								() -> loadCategories())));
		if (c != null)
			content.addView(
					button(
							"Delete category",
							v -> confirm("Delete category?",
									"This removes the category. Products assigned to it may become uncategorized.",
									() -> asyncAction(
											() -> api.delete("/api/admin/categories/" + c.optInt("id")),
											() -> loadCategories()))));
	}
}
