package nyx.velangadmin.features;

import android.app.AlertDialog;
import android.net.Uri;
import android.view.ViewGroup;
import android.webkit.WebSettings;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.widget.EditText;
import android.widget.Toast;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import static nyx.velangadmin.AdminJson.*;

public abstract class AdminPreviewLayer extends AdminMediaLayer {
	private JSONObject activeProductPreview;
	private String activePreviewMode = "product";

	@Override
	protected JSONObject buildProductPreviewContext(EditText name, EditText slug, EditText subtitle,
			EditText description, EditText price, EditText currency) {
		try {
			JSONObject product = new JSONObject();
			product.put("name", name.getText().toString().trim());
			product.put("slug", slug.getText().toString().trim());
			product.put("subtitle", subtitle.getText().toString().trim());
			product.put("description", description.getText().toString());
			product.put("price", price.getText().toString().trim());
			product.put("currency", currency.getText().toString().trim().toUpperCase(java.util.Locale.ROOT));
			product.put("meta", new JSONObject());
			return new JSONObject().put("product", product);
		} catch (JSONException ignored) {
			return new JSONObject();
		}
	}

	@Override
	protected String htmlEscape(String value) {
		if (value == null)
			return "";
		return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
				.replace("\"", "&quot;").replace("'", "&#39;");
	}

	@Override
	protected String firstImageFromSerialized(String raw) {
		try {
			JSONArray images = new JSONArray(raw == null || raw.trim().isEmpty() ? "[]" : raw);
			for (int i = 0; i < images.length(); i++) {
				JSONObject image = images.optJSONObject(i);
				if (image == null)
					continue;
				String path = image.optString("path", "").trim();
				if (!path.isEmpty())
					return path;
			}
		} catch (JSONException ignored) {
		}
		return "";
	}

	@Override
	protected void previewProduct(JSONObject payload, boolean detailPage) {
		try {
			payload.put("mode", detailPage ? "product" : "card");
			activeProductPreview = new JSONObject(payload.toString());
			activePreviewMode = detailPage ? "product" : "card";
		} catch (JSONException error) {
			Toast.makeText(this, "Could not prepare the product preview.", Toast.LENGTH_LONG).show();
			return;
		}
		String title = detailPage ? "Storefront product preview" : "Storefront card preview";
		async(() -> api.post("/api/admin/product-preview", payload), data -> {
			String html = data.optString("html", "");
			if (html.isEmpty()) {
				Toast.makeText(this, "The server returned an empty preview.", Toast.LENGTH_LONG).show();
				return;
			}
			showPreviewHtml(title, html);
		});
	}

	private String previewDocumentBaseUrl() {
		String base = api.getBaseUrl().replaceAll("/+$", "");
		if (activeProductPreview == null)
			return base + "/";
		if ("product".equals(activePreviewMode)) {
			JSONObject product = activeProductPreview.optJSONObject("product");
			String slug = product == null ? "product-preview" : product.optString("slug", "product-preview");
			if (slug.trim().isEmpty())
				slug = "product-preview";
			return base + "/product/" + Uri.encode(slug);
		}
		return base + "/shop";
	}

	private boolean sameOrigin(Uri target, Uri base) {
		if (!java.util.Objects.equals(target.getScheme(), base.getScheme())
				|| !java.util.Objects.equals(target.getHost(), base.getHost()))
			return false;
		return effectivePort(target) == effectivePort(base);
	}

	private int effectivePort(Uri uri) {
		if (uri.getPort() != -1)
			return uri.getPort();
		return "https".equalsIgnoreCase(uri.getScheme()) ? 443 : 80;
	}

	private boolean loadPreviewPage(WebView view, String mode) {
		try {
			JSONObject payload = new JSONObject(activeProductPreview.toString());
			payload.put("mode", mode);
			activePreviewMode = mode;
			executor.execute(() -> {
				try {
					JSONObject result = api.post("/api/admin/product-preview", payload);
					String storefrontHtml = result.optString("html", "");
					runOnUi(() -> {
						if (activeProductPreview == null || !mode.equals(activePreviewMode))
							return;
						if (!storefrontHtml.isEmpty())
							view.loadDataWithBaseURL(previewDocumentBaseUrl(), storefrontHtml, "text/html", "UTF-8", null);
						else
							Toast.makeText(AdminPreviewLayer.this, "The server returned an empty preview.", Toast.LENGTH_LONG).show();
					});
				} catch (Exception error) {
					runOnUi(() -> Toast.makeText(AdminPreviewLayer.this,
							"Could not load the storefront preview: " + error.getMessage(), Toast.LENGTH_LONG).show());
				}
			});
			return true;
		} catch (JSONException error) {
			Toast.makeText(this, "Could not open the storefront preview.", Toast.LENGTH_LONG).show();
			return true;
		}
	}

	@Override
	protected void showPreviewHtml(String title, String html) {
		WebView web = new WebView(this);
		WebSettings settings = web.getSettings();
		settings.setJavaScriptEnabled(true);
		settings.setDomStorageEnabled(true);
		settings.setAllowFileAccess(false);
		settings.setAllowContentAccess(false);
		web.setWebViewClient(new WebViewClient() {
			@Override
			public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
				if (!request.isForMainFrame() || activeProductPreview == null)
					return false;
				Uri target = request.getUrl();
				Uri base = Uri.parse(api.getBaseUrl());
				if (!sameOrigin(target, base)) {
					Toast.makeText(AdminPreviewLayer.this,
							"External navigation is disabled in preview.", Toast.LENGTH_SHORT).show();
					return true;
				}
				String path = target.getPath();
				if (path == null)
					return true;
				if (path.startsWith("/product/"))
					return loadPreviewPage(view, "product");
				if ("/".equals(path) || "/shop".equals(path))
					return loadPreviewPage(view, "card");
				Toast.makeText(AdminPreviewLayer.this,
						"Navigation outside this product preview is disabled.", Toast.LENGTH_SHORT).show();
				return true;
			}
		});
		web.loadDataWithBaseURL(previewDocumentBaseUrl(), html, "text/html", "UTF-8", null);
		AlertDialog dialog = new AlertDialog.Builder(this).setTitle(title)
				.setView(web).setPositiveButton("Close", null).create();
		dialog.setOnDismissListener(ignored -> {
			activeProductPreview = null;
			activePreviewMode = "product";
		});
		dialog.show();
		if (dialog.getWindow() != null) {
			dialog.getWindow().setLayout(ViewGroup.LayoutParams.MATCH_PARENT,
					Math.round(getResources().getDisplayMetrics().heightPixels * 0.82f));
		}
	}

	@Override
	protected void previewMarkdown(String markdown, String title) {
		previewMarkdown(markdown, title, null);
	}

	@Override
	protected void previewMarkdown(String markdown, String title, JSONObject context) {
		activeProductPreview = null;
		activePreviewMode = "product";
		async(
				() -> {
					JSONObject request = new JSONObject().put("body_markdown", markdown == null ? "" : markdown);
					if (context != null)
						request.put("context", context);
					return api.post("/api/admin/markdown-preview", request);
				},
				data -> {
					String html = "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
							+ "<style>body{font-family:system-ui,-apple-system,sans-serif;color:#111;background:#fff;line-height:1.65;margin:22px;overflow-wrap:anywhere}"
							+ "h1,h2,h3,h4{line-height:1.2;letter-spacing:-.03em;font-weight:500}img{max-width:100%;height:auto}"
							+ "a{color:#111;text-underline-offset:3px}blockquote{border-left:2px solid #bbb;margin-left:0;padding-left:14px;color:#555}"
							+ "pre,code{background:#f2f2ef;font-family:monospace}pre{padding:12px;white-space:pre-wrap}table{border-collapse:collapse;max-width:100%}td,th{border:1px solid #ddd;padding:6px;text-align:left}</style></head><body>"
							+ data.optString("html", "") + "</body></html>";
					showPreviewHtml(title, html);
				});
	}
}
