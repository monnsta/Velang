package nyx.velangadmin.core;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;
import java.util.Map;
import nyx.velangadmin.AdminApi;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import static nyx.velangadmin.AdminJson.*;

public abstract class AdminCoreActivity extends Activity {
	@FunctionalInterface
	protected interface ThrowingRunnable {
		void run() throws Exception;
	}

	protected final Executor executor = Executors.newCachedThreadPool();
	protected int BG;
	protected int SURFACE;
	protected int BLACK;
	protected int MUTED;
	protected int BORDER;
	protected SharedPreferences prefs;
	protected AdminApi api;
	protected LinearLayout root;
	protected LinearLayout content;
	protected LinearLayout stickyActions;
	protected ScrollView contentScroll;
	protected TextView pageTitle;
	protected boolean darkMode;
	protected int productListScrollY;
	protected java.util.function.Consumer<JSONObject> uploadResultHandler;
	protected ProgressBar progressIndicator;

	protected abstract JSONObject buildProductPreviewContext(EditText name, EditText slug, EditText subtitle,
			EditText description, EditText price, EditText currency);

	protected abstract String htmlEscape(String value);

	protected abstract String firstImageFromSerialized(String raw);

	protected abstract void previewProduct(JSONObject productPayload, boolean detailPage);

	protected abstract void showPreviewHtml(String title, String html);

	protected abstract void previewMarkdown(String markdown, String title);

	protected abstract void previewMarkdown(String markdown, String title, JSONObject context);

	protected abstract void loadMedia();

	protected abstract String humanBytes(long size);

	protected abstract void editAssetAltText(JSONObject asset);

	public abstract void chooseAsset(java.util.function.Consumer<JSONObject> callback);

	public abstract void pickFile();

	public abstract void pickFile(java.util.function.Consumer<JSONObject> callback);

	protected abstract byte[] readAll(InputStream in) throws Exception;

	protected abstract String queryName(Uri uri);

	protected abstract void loadSite();

	protected abstract String normalizedMoney(String raw, String title);

	protected abstract int parseColorOrDefault(String value, int fallback);

	protected abstract EditText colorField(LinearLayout box, String title, String value);

	protected abstract void showColorPicker(EditText target, View fieldSwatch);

	protected abstract void themeForm(JSONObject theme);

	protected abstract Object parseJsonValue(String raw) throws JSONException;

	protected abstract void loadUsers();

	protected abstract void toggleUser(int id, boolean active, boolean admin);

	protected abstract void loadPages();

	protected abstract void renderPages(JSONArray rows, String query, LinearLayout list);

	protected abstract void pageForm(JSONObject p);

	protected abstract void loadOrders();

	protected abstract void renderOrders(JSONArray rows, String query, LinearLayout list);

	protected abstract void changeOrder(int id, String status, String payment);

	protected abstract void loadTemplates();

	protected abstract void templateForm(JSONObject t);

	protected abstract void loadCategories();

	protected abstract boolean categoryWouldCreateCycle(JSONObject candidate, JSONArray all, int currentId);

	protected abstract void categoryForm(JSONObject c, JSONArray knownCategories);

	protected abstract void loadProducts();

	protected abstract void renderProducts(JSONArray rows, String query, LinearLayout list);

	protected abstract void startNewProduct();

	protected abstract void loadProduct(int id);

	protected abstract void showProductsAfterEdit();

	protected abstract void setDragListenerOnTree(View view, View.OnDragListener listener);

	protected abstract void reorderProducts(JSONArray rows, int sourceId, int targetId);

	protected abstract void moveProduct(int id, String direction);

	protected abstract JSONObject readTemplateValues(java.util.Map<String, EditText> fields);

	protected abstract void renderTemplateFields(LinearLayout box, JSONObject selected, JSONObject initial,
			java.util.Map<String, EditText> inputs, java.util.Map<String, Boolean> required);

	protected abstract void productForm(JSONObject p, JSONObject options);

	protected abstract void asyncSaveProduct(
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
			android.widget.Switch visibility,
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
			Runnable onSaved);

	protected abstract void loadDashboard();

	protected abstract void loadAudit();

	protected abstract void showLogin();

	protected abstract void showShell(String title, Runnable loader);


	public void onCreate(Bundle state) {
		super.onCreate(state);
		prefs = getSharedPreferences("velang_admin", MODE_PRIVATE);
		darkMode = prefs.getBoolean("dark_mode", false);
		BG = Color.parseColor(darkMode ? "#101214" : "#f4f5f3");
		SURFACE = Color.parseColor(darkMode ? "#1b1e21" : "#ffffff");
		BLACK = Color.parseColor(darkMode ? "#f2f4f5" : "#17191b");
		MUTED = Color.parseColor(darkMode ? "#a8afb5" : "#656d72");
		BORDER = Color.parseColor(darkMode ? "#383e43" : "#dfe3e0");
		getWindow().setStatusBarColor(BG);
		getWindow().setNavigationBarColor(BG);
		getWindow().getDecorView().setSystemUiVisibility(darkMode ? 0 : View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
		api = new AdminApi(
				prefs.getString("server", ""), prefs.getString("token", ""));
		if (apiToken().isEmpty())
			showLogin();
		else
			showShell("Dashboard", this::loadDashboard);
	}

	protected String apiToken() {
		return prefs.getString("token", "");
	}

	public int dp(int value) {
		return Math.round(value * getResources().getDisplayMetrics().density);
	}

	public int surfaceColor() {
		return SURFACE;
	}

	public int borderColor() {
		return BORDER;
	}

	public int foregroundColor() {
		return BLACK;
	}

	public LinearLayout column(int padding) {
		LinearLayout box = new LinearLayout(this);
		box.setOrientation(LinearLayout.VERTICAL);
		box.setPadding(dp(padding), dp(padding), dp(padding), dp(padding));
		return box;
	}

	public TextView label(String text, float size) {
		TextView v = new TextView(this);
		v.setText(text);
		v.setTextSize(size);
		v.setTextColor(BLACK);
		v.setPadding(0, dp(5), 0, dp(5));
		return v;
	}

	public GradientDrawable outline(int fill, int stroke) {
		GradientDrawable drawable = new GradientDrawable();
		drawable.setColor(fill);
		drawable.setStroke(dp(1), stroke);
		drawable.setCornerRadius(dp(12));
		return drawable;
	}

	public EditText input(String hint, String value) {
		EditText e = new EditText(this);
		e.setHint(hint);
		e.setText(value == null ? "" : value);
		e.setTextColor(BLACK);
		e.setHintTextColor(MUTED);
		e.setSingleLine(false);
		e.setBackground(outline(SURFACE, BORDER));
		e.setPadding(dp(14), dp(11), dp(14), dp(11));
		LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT);
		lp.setMargins(0, 0, 0, dp(10));
		e.setLayoutParams(lp);
		return e;
	}

	public Button button(String text, View.OnClickListener listener) {
		Button b = new Button(this);
		b.setText(text);
		b.setAllCaps(false);
		b.setTextColor(BLACK);
		b.setBackground(outline(darkMode ? Color.parseColor("#252a2e") : Color.parseColor("#f8f9f7"), BORDER));
		b.setPadding(dp(14), dp(6), dp(14), dp(6));
		b.setMinHeight(dp(44));
		b.setElevation(0);
		b.setStateListAnimator(null);
		b.setOnClickListener(listener);
		return b;
	}

	public ImageButton iconButton(int drawableId, String description, View.OnClickListener listener) {
		ImageButton button = new ImageButton(this);
		button.setImageResource(drawableId);
		button.setColorFilter(darkMode ? Color.WHITE : BLACK);
		button.setContentDescription(description);
		button.setBackground(outline(Color.TRANSPARENT, Color.TRANSPARENT));
		button.setPadding(dp(10), dp(10), dp(10), dp(10));
		button.setOnClickListener(listener);
		return button;
	}

	public CheckBox check(String text, boolean value) {
		CheckBox c = new CheckBox(this);
		c.setText(text);
		c.setTextColor(BLACK);
		c.setChecked(value);
		return c;
	}

	public void frame(View view) {
		root = column(0);
		root.setBackgroundColor(BG);
		root.addView(view, new LinearLayout.LayoutParams(-1, -1));
		setContentView(root);
	}

	protected void loadThumbnail(ImageView image, String path) {
		if (path == null || path.trim().isEmpty())
			return;
		String urlText = path.startsWith("http://") || path.startsWith("https://")
				? path
				: api.getBaseUrl().replaceAll("/+$", "") + (path.startsWith("/") ? path : "/" + path);
		image.setTag(urlText);
		executor.execute(() -> {
			Bitmap bitmap = null;
			HttpURLConnection connection = null;
			try {
				connection = (HttpURLConnection) new URL(urlText).openConnection();
				connection.setConnectTimeout(5000);
				connection.setReadTimeout(7000);
				connection.setInstanceFollowRedirects(true);
				connection.connect();
				if (connection.getResponseCode() == HttpURLConnection.HTTP_OK) {
					try (InputStream stream = connection.getInputStream()) {
						bitmap = BitmapFactory.decodeStream(stream);
					}
				}
			} catch (Exception ignored) {
			} finally {
				if (connection != null)
					connection.disconnect();
			}
			Bitmap result = bitmap;
			if (result != null)
				runOnUi(() -> {
					if (urlText.equals(image.getTag()))
						image.setImageBitmap(result);
				});
		});
	}

	protected void clearContent() {
		content.removeAllViews();
		if (stickyActions != null) {
			stickyActions.removeAllViews();
			stickyActions.setVisibility(View.GONE);
		}
	}

	protected void busy(boolean busy) {
		if (content == null)
			return;
		if (busy) {
			if (progressIndicator != null && progressIndicator.getParent() instanceof ViewGroup) {
				((ViewGroup) progressIndicator.getParent()).removeView(progressIndicator);
			}
			progressIndicator = new ProgressBar(this);
			LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-2, -2);
			params.gravity = Gravity.CENTER_HORIZONTAL;
			params.setMargins(0, dp(8), 0, dp(8));
			content.addView(progressIndicator, params);
		} else {
			if (progressIndicator != null && progressIndicator.getParent() instanceof ViewGroup) {
				((ViewGroup) progressIndicator.getParent()).removeView(progressIndicator);
			}
			progressIndicator = null;
		}
	}

	protected EditText field(LinearLayout box, String title, String value) {
		box.addView(label(title, 13));
		EditText e = input("", value);
		String normalized = title.toLowerCase(java.util.Locale.ROOT);
		boolean multiline = normalized.contains("markdown")
				|| normalized.contains("json")
				|| normalized.contains("description")
				|| normalized.contains("shipping note")
				|| normalized.equals("care")
				|| normalized.equals("dimensions")
				|| normalized.contains("images")
				|| normalized.contains("notes")
				|| normalized.contains("instructions")
				|| normalized.contains("story")
				|| normalized.contains("one link per line")
				|| normalized.contains("page content")
				|| normalized.contains("announcement text");
		if (multiline) {
			e.setSingleLine(false);
			e.setMinLines(normalized.contains("markdown") ? 5 : 3);
			e.setMaxLines(normalized.contains("markdown") ? 12 : 7);
			e.setGravity(Gravity.TOP | Gravity.START);
			e.setVerticalScrollBarEnabled(true);
			e.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS);
			e.setHint("Enter " + title.toLowerCase(java.util.Locale.ROOT));
			e.setOnTouchListener((view, event) -> {
				if (event.getAction() == android.view.MotionEvent.ACTION_DOWN
						|| event.getAction() == android.view.MotionEvent.ACTION_MOVE) {
					view.getParent().requestDisallowInterceptTouchEvent(true);
				} else if (event.getAction() == android.view.MotionEvent.ACTION_UP
						|| event.getAction() == android.view.MotionEvent.ACTION_CANCEL) {
					view.getParent().requestDisallowInterceptTouchEvent(false);
				}
				return false;
			});
		} else {
			e.setSingleLine(true);
			e.setHint("Enter " + title.toLowerCase(java.util.Locale.ROOT));
		}
		if (normalized.contains("price")) {
			e.setInputType(android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
		} else if (normalized.contains("stock count") || normalized.contains("low stock threshold")
				|| normalized.contains("display order") || normalized.contains("template id")
				|| normalized.contains("position") || normalized.contains("radius")
				|| normalized.contains("max content width")) {
			e.setInputType(android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_FLAG_SIGNED);
		}
		box.addView(e);
		return e;
	}

	protected void sectionHeading(String title, String detail) {
		TextView heading = label(title, 17);
		heading.setTypeface(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD);
		heading.setPadding(0, dp(12), 0, dp(0));
		content.addView(heading);
		if (detail != null && !detail.isEmpty()) {
			TextView help = label(detail, 12);
			help.setTextColor(MUTED);
			content.addView(help);
		}
	}

	protected void confirm(String title, String message, Runnable action) {
		new AlertDialog.Builder(this)
				.setTitle(title)
				.setMessage(message)
				.setNegativeButton("Keep it", null)
				.setPositiveButton("Continue", (dialog, which) -> action.run())
				.show();
	}

	protected void async(
			java.util.concurrent.Callable<JSONObject> call,
			java.util.function.Consumer<JSONObject> success) {
		busy(true);
		executor.execute(
				() -> {
					try {
						JSONObject data = call.call();
						runOnUi(() -> {
							busy(false);
							success.accept(data);
						});
					} catch (Exception e) {
						String message = e.getMessage() == null ? "Request failed" : e.getMessage();
						if (message.contains("401") || message.toLowerCase().contains("admin session")) {
							prefs.edit().remove("token").apply();
							api.setToken("");
							runOnUi(() -> {
								busy(false);
								showLogin();
							});
						} else {
							runOnUi(() -> {
								busy(false);
								Toast.makeText(this, message, Toast.LENGTH_LONG).show();
							});
						}
					}
				});
	}

	protected void asyncAction(ThrowingRunnable call, Runnable success) {
		busy(true);
		executor.execute(
				() -> {
					try {
						call.run();
						runOnUi(() -> {
							busy(false);
							success.run();
						});
					} catch (Exception e) {
						String message = e.getMessage() == null ? "Request failed" : e.getMessage();
						if (message.contains("401") || message.toLowerCase().contains("admin session")) {
							prefs.edit().remove("token").apply();
							api.setToken("");
							runOnUi(() -> {
								busy(false);
								showLogin();
							});
						} else {
							runOnUi(() -> {
								busy(false);
								Toast.makeText(this, message, Toast.LENGTH_LONG).show();
							});
						}
					}
				});
	}

	protected void runOnUi(Runnable r) {
		runOnUiThread(r);
	}

}
