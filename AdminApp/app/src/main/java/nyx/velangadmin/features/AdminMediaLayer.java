package nyx.velangadmin.features;

import android.app.AlertDialog;
import android.content.ClipboardManager;
import android.content.ClipData;
import android.content.Intent;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.view.Gravity;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.Toast;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.URL;
import java.util.ArrayList;
import nyx.velangadmin.R;
import org.json.JSONArray;
import org.json.JSONObject;
import static nyx.velangadmin.AdminJson.*;

public abstract class AdminMediaLayer extends AdminUsersLayer {
	@Override
	protected void onActivityResult(int requestCode, int resultCode, Intent data) {
		super.onActivityResult(requestCode, resultCode, data);
		if (requestCode != 42)
			return;
		java.util.function.Consumer<JSONObject> callback = uploadResultHandler;
		uploadResultHandler = null;
		if (resultCode != RESULT_OK || data == null)
			return;
		Uri uri = data.getData();
		executor.execute(() -> {
			try (InputStream in = getContentResolver().openInputStream(uri)) {
				if (in == null)
					throw new java.io.IOException("Could not open the selected file.");
				byte[] bytes = readAll(in);
				if (bytes.length > 20 * 1024 * 1024)
					throw new java.io.IOException("The maximum upload size is 20 MB.");
				String name = queryName(uri);
				String mime = getContentResolver().getType(uri);
				JSONObject asset = api.upload("/api/admin/media", bytes, name, mime, "");
				runOnUi(() -> {
					if (callback != null)
						callback.accept(asset);
					else
						loadMedia();
					Toast.makeText(this, "Uploaded " + name, Toast.LENGTH_SHORT).show();
				});
			} catch (Exception e) {
				runOnUi(() -> Toast.makeText(this, e.getMessage(), Toast.LENGTH_LONG).show());
			}
		});
	}

	@Override
	protected void loadMedia() {
		async(
				() -> api.get("/api/admin/media"),
				data -> {
					clearContent();
					content.addView(label("Asset library", 24));
					content.addView(label(
							"Upload images and other files once, then reuse their URLs in product galleries and Markdown pages. Deleting an asset may break pages that reference it.",
							13));
					content.addView(iconButton(R.drawable.ic_upload, "Upload asset", v -> pickFile()));
					JSONArray rows = data.optJSONArray("media");
					if (rows == null || rows.length() == 0) {
						content.addView(
								label("Your library is empty. Upload an image, logo, or document to get started.", 14));
						return;
					}
					for (int i = 0; i < rows.length(); i++) {
						JSONObject m = rows.optJSONObject(i);
						if (m == null)
							continue;
						int id = m.optInt("id");
						String path = jsonValueText(m, "path", "");
						LinearLayout row = column(12);
						row.setBackground(outline(SURFACE, BORDER));
						String mimeType = jsonValueText(m, "mime_type", "").toLowerCase(java.util.Locale.ROOT);
						if (mimeType.startsWith("image/") || path.matches("(?i).*\\.(png|jpe?g|gif|webp|avif|svg)$")) {
							ImageView preview = new ImageView(this);
							preview.setScaleType(ImageView.ScaleType.CENTER_CROP);
							preview.setBackground(outline(SURFACE, BORDER));
							row.addView(preview, new LinearLayout.LayoutParams(dp(104), dp(104)));
							loadThumbnail(preview, path);
						}
						row.addView(label(jsonValueText(m, "filename", "Unnamed asset"), 17));
						row.addView(label(path, 12));
						row.addView(label(jsonValueText(m, "alt_text", "No alt text") + "\n"
								+ jsonValueText(m, "mime_type", "unknown") + " · "
								+ humanBytes(m.optLong("size_bytes")), 12));
						LinearLayout actions = new LinearLayout(this);
						actions.setOrientation(LinearLayout.HORIZONTAL);
						actions.setGravity(Gravity.CENTER_VERTICAL);
						actions.addView(iconButton(R.drawable.ic_copy, "Copy asset URL", v -> {
							android.content.ClipboardManager clipboard = (android.content.ClipboardManager) getSystemService(
									CLIPBOARD_SERVICE);
							clipboard.setPrimaryClip(android.content.ClipData.newPlainText("Asset URL", path));
							Toast.makeText(this, "Asset path copied", Toast.LENGTH_SHORT).show();
						}));
						actions.addView(
								iconButton(R.drawable.ic_edit, "Edit image alt text", v -> editAssetAltText(m)));
						actions.addView(iconButton(R.drawable.ic_delete, "Delete asset", v -> confirm("Delete asset?",
								"This removes the uploaded file from storage. Any product or page using " + path
										+ " may show a broken image.",
								() -> asyncAction(() -> api.delete("/api/admin/media/" + id), this::loadMedia))));
						row.addView(actions);
						LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
						lp.setMargins(0, 0, 0, dp(8));
						content.addView(row, lp);
					}
				});
	}

	@Override
	protected String humanBytes(long size) {
		if (size < 1024)
			return size + " B";
		if (size < 1024 * 1024)
			return String.format(java.util.Locale.ROOT, "%.1f KB", size / 1024.0);
		return String.format(java.util.Locale.ROOT, "%.1f MB", size / (1024.0 * 1024.0));
	}

	@Override
	protected void editAssetAltText(JSONObject asset) {
		EditText alt = input("Describe this image for accessibility", jsonValueText(asset, "alt_text", ""));
		new AlertDialog.Builder(this)
				.setTitle("Alt text")
				.setMessage("A short description helps screen-reader users and image search.")
				.setView(alt)
				.setNegativeButton("Cancel", null)
				.setPositiveButton("Save", (dialog, which) -> asyncAction(
						() -> api.put("/api/admin/media/" + asset.optInt("id"),
								new JSONObject().put("alt_text", alt.getText().toString().trim())),
						this::loadMedia))
				.show();
	}

	@Override
	public void chooseAsset(java.util.function.Consumer<JSONObject> callback) {
		async(
				() -> api.get("/api/admin/media"),
				data -> {
					JSONArray rows = data.optJSONArray("media");
					if (rows == null || rows.length() == 0) {
						new AlertDialog.Builder(this).setTitle("Asset library is empty")
								.setMessage("Upload an asset first, or use Upload image in the editor.")
								.setPositiveButton("Upload asset", (dialog, which) -> pickFile(callback))
								.setNegativeButton("Cancel", null).show();
						return;
					}
					java.util.ArrayList<JSONObject> assets = new java.util.ArrayList<>();
					java.util.ArrayList<String> labels = new java.util.ArrayList<>();
					for (int i = 0; i < rows.length(); i++) {
						JSONObject asset = rows.optJSONObject(i);
						if (asset == null)
							continue;
						assets.add(asset);
						labels.add(jsonValueText(asset, "filename", "Asset") + "\n" + jsonValueText(asset, "path", ""));
					}
					new AlertDialog.Builder(this).setTitle("Choose an asset")
							.setItems(labels.toArray(new String[0]),
									(dialog, which) -> callback.accept(assets.get(which)))
							.setNegativeButton("Cancel", null)
							.setNeutralButton("Upload new", (dialog, which) -> pickFile(callback)).show();
				});
	}

	@Override
	public void pickFile() {
		pickFile(null);
	}

	@Override
	public void pickFile(java.util.function.Consumer<JSONObject> callback) {
		uploadResultHandler = callback;
		startActivityForResult(
				new Intent(Intent.ACTION_OPEN_DOCUMENT)
						.setType("*/*")
						.addCategory(Intent.CATEGORY_OPENABLE),
				42);
	}

	@Override
	protected byte[] readAll(InputStream in) throws Exception {
		java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
		byte[] b = new byte[8192];
		int n;
		while ((n = in.read(b)) != -1)
			out.write(b, 0, n);
		return out.toByteArray();
	}

	@Override
	protected String queryName(Uri uri) {
		String name = "upload.bin";
		try (android.database.Cursor c = getContentResolver()
				.query(uri, new String[] { OpenableColumns.DISPLAY_NAME }, null, null, null)) {
			if (c != null && c.moveToFirst())
				name = c.getString(0);
		} catch (Exception ignored) {
		}
		return name;
	}
}
