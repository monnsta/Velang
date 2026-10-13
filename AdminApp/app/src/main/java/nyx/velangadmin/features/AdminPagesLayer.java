package nyx.velangadmin.features;

import android.app.AlertDialog;
import android.net.Uri;
import android.view.Gravity;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import java.net.URL;
import nyx.velangadmin.R;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import static nyx.velangadmin.AdminJson.*;

public abstract class AdminPagesLayer extends AdminOrdersLayer {
	@Override
	protected void loadPages() {
		async(
				() -> api.get("/api/admin/pages"),
				data -> {
					clearContent();
					content.addView(label("Pages", 24));
					content.addView(label(
							"Edit built-in pages like The Company, Terms of Service, Privacy, and Support, or create new pages. Changes to built-in pages are written to their Markdown files.",
							13));
					content.addView(iconButton(R.drawable.ic_add, "New custom page", v -> pageForm(null)));
					EditText search = input("Search title or page URL", "");
					search.setSingleLine(true);
					content.addView(search);
					JSONArray rows = data.optJSONArray("pages");
					LinearLayout list = column(0);
					content.addView(list);
					if (rows == null) {
						list.addView(label("The server returned no page list.", 14));
						return;
					}
					renderPages(rows, "", list);
					search.addTextChangedListener(new android.text.TextWatcher() {
						@Override
						public void beforeTextChanged(CharSequence s, int start, int count, int after) {
						}

						@Override
						public void onTextChanged(CharSequence s, int start, int before, int count) {
							renderPages(rows, s.toString(), list);
						}

						@Override
						public void afterTextChanged(android.text.Editable s) {
						}
					});
				});
	}

	@Override
	protected void renderPages(JSONArray rows, String query, LinearLayout list) {
		list.removeAllViews();
		String needle = query == null ? "" : query.trim().toLowerCase(java.util.Locale.ROOT);
		int count = 0;
		for (int i = 0; i < rows.length(); i++) {
			JSONObject p = rows.optJSONObject(i);
			if (p == null)
				continue;
			String title = jsonValueText(p, "title", "Untitled page");
			String slug = jsonValueText(p, "slug", "");
			if (!needle.isEmpty() && !(title.toLowerCase(java.util.Locale.ROOT).contains(needle)
					|| slug.toLowerCase(java.util.Locale.ROOT).contains(needle)))
				continue;
			boolean isStatic = "static".equals(p.optString("source", "database"));
			LinearLayout row = column(12);
			row.setBackground(outline(SURFACE, BORDER));
			row.addView(label(title, 17));
			row.addView(label("/pages/" + slug + "   ·   " + (isStatic ? "Built-in Markdown" : "Custom page")
					+ "   ·   " + (p.optBoolean("active", true) ? "Published" : "Hidden"), 12));
			row.addView(iconButton(R.drawable.ic_edit, "Edit page", v -> pageForm(p)));
			LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
			lp.setMargins(0, 0, 0, dp(8));
			list.addView(row, lp);
			count++;
		}
		if (count == 0)
			list.addView(label(needle.isEmpty() ? "No pages found." : "No pages match that search.", 14));
	}

	@Override
	protected void pageForm(JSONObject p) {
		clearContent();
		boolean isStatic = p != null && "static".equals(p.optString("source", "database"));
		String originalSlug = p == null ? "" : jsonValueText(p, "slug", "");
		content.addView(label(p == null ? "New custom page" : "Edit page", 24));
		content.addView(label(isStatic
				? "Built-in Markdown file · edits are saved to server/content/pages/"
				: "Custom database page · Markdown content is rendered using the storefront's safe renderer.", 13));
		EditText slug = field(content, "URL slug", p == null ? "" : jsonValueText(p, "slug", ""));
		EditText title = field(content, "Page title", p == null ? "" : jsonValueText(p, "title", ""));
		EditText body = field(content, "Markdown content", p == null ? "" : jsonValueText(p, "body_markdown", ""));
		body.setMinLines(8);
		body.setMaxLines(24);
		body.setGravity(Gravity.TOP | Gravity.START);
		content.addView(button("Preview as it appears on the storefront", v -> previewMarkdown(
				body.getText().toString(),
				title.getText().toString().trim().isEmpty() ? "Page preview" : title.getText().toString().trim())));
		content.addView(button("Insert store variable", v -> {
			String[] variables = { "{{ site.site.name }}", "{{ site.site.description }}", "{{ site.store.currency }}" };
			new AlertDialog.Builder(this).setTitle("Insert a store variable").setItems(variables, (dialog, which) -> {
				int cursor = Math.max(0, body.getSelectionStart());
				body.getText().insert(Math.min(cursor, body.length()), variables[which]);
			}).show();
		}));
		content.addView(button("Insert collapsible section", v -> {
			String snippet = "::: collapse Details\n\nAdd your Markdown here.\n\n:::";
			int cursor = Math.max(0, body.getSelectionStart());
			body.getText().insert(Math.min(cursor, body.length()), snippet);
		}));
		content.addView(button("Insert image or asset from library", v -> chooseAsset(asset -> {
			String path = jsonValueText(asset, "path", "");
			String alt = jsonValueText(asset, "alt_text", "");
			String filename = jsonValueText(asset, "filename", "asset");
			String mime = jsonValueText(asset, "mime_type", "").toLowerCase(java.util.Locale.ROOT);
			boolean imageAsset = mime.startsWith("image/") || path.matches("(?i).*\\.(png|jpe?g|gif|webp|avif|svg)$");
			String label = alt.isEmpty() ? filename : alt;
			String markdown = imageAsset
					? "![" + label.replace("]", "\\]") + "](" + path + ")"
					: "[" + label.replace("]", "\\]") + "](" + path + ")";
			int cursor = Math.max(0, body.getSelectionStart());
			body.getText().insert(Math.min(cursor, body.length()), markdown);
		})));
		CheckBox active = check("Published / visible on the storefront", p == null || p.optBoolean("active", true));
		content.addView(active);
		EditText meta = field(content, "Additional metadata (JSON object)",
				p == null ? "{}" : jsonObjectText(p.optJSONObject("meta")));
		content.addView(button("Save page", v -> {
			try {
				String nextSlug = slug.getText().toString().trim().toLowerCase(java.util.Locale.ROOT);
				if (!nextSlug.matches("[a-z0-9]+(?:-[a-z0-9]+)*"))
					throw new IllegalArgumentException(
							"URL slug must use lowercase letters, numbers, and hyphens only.");
				if (title.getText().toString().trim().isEmpty())
					throw new IllegalArgumentException("Page title is required.");
				JSONObject b = new JSONObject();
				b.put("slug", nextSlug);
				b.put("title", title.getText().toString().trim());
				b.put("body_markdown", body.getText().toString());
				b.put("active", active.isChecked());
				JSONObject metadata;
				try {
					metadata = new JSONObject(
							meta.getText().toString().trim().isEmpty() ? "{}" : meta.getText().toString());
				} catch (JSONException e) {
					throw new IllegalArgumentException("Additional metadata must be a valid JSON object.");
				}
				b.put("meta", metadata);
				asyncAction(() -> {
					if (p == null)
						api.post("/api/admin/pages", b);
					else if (isStatic)
						api.put("/api/admin/pages/static/" + Uri.encode(originalSlug), b);
					else
						api.put("/api/admin/pages/" + p.optInt("id"), b);
				}, this::loadPages);
			} catch (Exception error) {
				new AlertDialog.Builder(this).setTitle("Check page details")
						.setMessage(error.getMessage() == null ? "Please check the page fields." : error.getMessage())
						.setPositiveButton("OK", null).show();
			}
		}));
		if (p != null && !isStatic) {
			content.addView(button("Delete custom page", v -> confirm(
					"Delete custom page?", "This permanently deletes /pages/" + originalSlug + ".",
					() -> asyncAction(() -> api.delete("/api/admin/pages/" + p.optInt("id")), this::loadPages))));
		} else if (isStatic) {
			content.addView(label(
					"Built-in pages cannot be deleted from the app. Turn off Published to hide one without removing its source file.",
					12));
		}
	}
}
