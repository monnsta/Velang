package nyx.velangadmin.features;

import android.app.AlertDialog;
import android.graphics.Color;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;
import java.net.URL;
import nyx.velangadmin.ColorWheelView;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import static nyx.velangadmin.AdminJson.*;

public abstract class AdminSiteLayer extends AdminPagesLayer {
	@Override
	protected void loadSite() {
		async(
				() -> api.get("/api/admin/site"),
				data -> {
					clearContent();
					content.addView(label("Store settings", 23));
					content.addView(label(
							"Store identity, support details and colors have friendly editors. Less common structured settings remain available below.",
							13));
					content.addView(button("Edit theme / colors", v -> themeForm(data.optJSONObject("theme"))));

					JSONObject siteValue = data.optJSONObject("site");
					if (siteValue == null)
						siteValue = new JSONObject();
					JSONObject storeValue = data.optJSONObject("store");
					if (storeValue == null)
						storeValue = new JSONObject();
					final JSONObject originalSiteValue = siteValue;
					final JSONObject originalStoreValue = storeValue;
					content.addView(label("Store identity", 18));
					EditText storeName = field(content, "Store name", siteValue.optString("name", "VELANG"));
					EditText storeDescription = field(content, "Store description",
							siteValue.optString("description", ""));
					storeDescription.setMinLines(2);
					storeDescription.setMaxLines(5);
					storeDescription.setGravity(Gravity.TOP | Gravity.START);
					EditText currency = field(content, "Default currency code",
							storeValue.optString("currency", "INR"));
					EditText country = field(content, "Store country", storeValue.optString("country", "India"));
					EditText supportEmail = field(content, "Support email", storeValue.optString("support_email", ""));
					supportEmail.setInputType(android.text.InputType.TYPE_CLASS_TEXT
							| android.text.InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
					EditText supportPhone = field(content, "Support phone", storeValue.optString("support_phone", ""));
					supportPhone.setInputType(android.text.InputType.TYPE_CLASS_PHONE);
					content.addView(button("Save store details", v -> {
						try {
							JSONObject nextSite = new JSONObject(originalSiteValue.toString());
							JSONObject nextStore = new JSONObject(originalStoreValue.toString());
							nextSite.put("name", storeName.getText().toString().trim());
							nextSite.put("description", storeDescription.getText().toString().trim());
							String currencyCode = currency.getText().toString().trim()
									.toUpperCase(java.util.Locale.ROOT);
							if (!currencyCode.matches("[A-Z]{3}"))
								throw new IllegalArgumentException(
										"Currency must be a three-letter code, such as INR.");
							if (storeName.getText().toString().trim().isEmpty())
								throw new IllegalArgumentException("Store name cannot be empty.");
							nextStore.put("currency", currencyCode);
							nextStore.put("country", country.getText().toString().trim());
							nextStore.put("support_email", supportEmail.getText().toString().trim());
							nextStore.put("support_phone", supportPhone.getText().toString().trim());
							asyncAction(() -> {
								api.put("/api/admin/site", new JSONObject().put("key", "site").put("value", nextSite));
								api.put("/api/admin/site",
										new JSONObject().put("key", "store").put("value", nextStore));
							}, this::loadSite);
						} catch (JSONException | IllegalArgumentException error) {
							new AlertDialog.Builder(this).setTitle("Check store details")
									.setMessage(error.getMessage() == null ? "Please check the fields."
											: error.getMessage())
									.setPositiveButton("OK", null).show();
						}
					}));

					content.addView(label("Announcement bar", 18));
					JSONObject announcement = data.optJSONObject("announcement");
					if (announcement == null)
						announcement = new JSONObject();
					CheckBox announcementEnabled = check("Show announcement bar",
							announcement.optBoolean("enabled", false));
					content.addView(announcementEnabled);
					EditText announcementText = field(content, "Announcement text", announcement.optString("text", ""));
					EditText announcementHref = field(content, "Announcement link (optional)",
							announcement.optString("href", ""));
					content.addView(button("Save announcement", v -> asyncAction(() -> {
						JSONObject value = new JSONObject().put("enabled", announcementEnabled.isChecked())
								.put("text", announcementText.getText().toString().trim())
								.put("href", announcementHref.getText().toString().trim());
						api.put("/api/admin/site", new JSONObject().put("key", "announcement").put("value", value));
					}, this::loadSite)));

					content.addView(label("Footer links", 18));
					JSONArray footer = data.optJSONArray("footer");
					StringBuilder footerText = new StringBuilder();
					if (footer != null) {
						for (int i = 0; i < footer.length(); i++) {
							JSONObject link = footer.optJSONObject(i);
							if (link == null)
								continue;
							if (footerText.length() > 0)
								footerText.append("\n");
							footerText.append(link.optString("label", "")).append(" | ")
									.append(link.optString("href", ""));
						}
					}
					EditText footerEditor = field(content, "One link per line: Label | /path or https://…",
							footerText.toString());
					footerEditor.setMinLines(3);
					footerEditor.setMaxLines(10);
					footerEditor.setGravity(Gravity.TOP | Gravity.START);
					content.addView(button("Save footer links", v -> {
						try {
							JSONArray links = new JSONArray();
							String[] lines = footerEditor.getText().toString().split("\\r?\\n");
							for (String line : lines) {
								if (line.trim().isEmpty())
									continue;
								String[] pair = line.split("\\|", 2);
								if (pair.length != 2 || pair[0].trim().isEmpty() || pair[1].trim().isEmpty()) {
									throw new IllegalArgumentException(
											"Each footer line must be Label | /path or full URL.");
								}
								String href = pair[1].trim();
								if (!((href.startsWith("/") && !href.startsWith("//")) || href.startsWith("https://")
										|| href.startsWith("http://") || href.startsWith("mailto:"))) {
									throw new IllegalArgumentException(
											"Footer links must use a local path, http(s), or mailto URL.");
								}
								links.put(new JSONObject().put("label", pair[0].trim()).put("href", href));
							}
							asyncAction(() -> api.put("/api/admin/site",
									new JSONObject().put("key", "footer").put("value", links)), this::loadSite);
						} catch (JSONException | IllegalArgumentException error) {
							new AlertDialog.Builder(this).setTitle("Check footer links")
									.setMessage(
											error.getMessage() == null ? "Please check the links." : error.getMessage())
									.setPositiveButton("OK", null).show();
						}
					}));

					content.addView(label("Search appearance", 18));
					JSONObject seo = data.optJSONObject("seo");
					if (seo == null)
						seo = new JSONObject();
					final JSONObject originalSeo = seo;
					EditText titleTemplate = field(content, "Page title template (use {{ title }})",
							seo.optString("title_template", "{{ title }} — VELANG"));
					EditText defaultDescription = field(content, "Default search description",
							seo.optString("default_description", ""));
					EditText ogImage = field(content, "Social share image URL",
							seo.optString("og_image", "/static/assets/logo.png"));
					content.addView(button("Save search appearance", v -> {
						try {
							JSONObject value = new JSONObject(originalSeo.toString());
							value.put("title_template", titleTemplate.getText().toString().trim());
							value.put("default_description", defaultDescription.getText().toString().trim());
							value.put("og_image", ogImage.getText().toString().trim());
							asyncAction(() -> api.put("/api/admin/site",
									new JSONObject().put("key", "seo").put("value", value)), this::loadSite);
						} catch (JSONException error) {
							Toast.makeText(this, "Could not prepare search settings: " + error.getMessage(),
									Toast.LENGTH_LONG).show();
						}
					}));

					content.addView(label("Social profiles", 18));
					JSONObject social = data.optJSONObject("social");
					if (social == null)
						social = new JSONObject();
					EditText instagram = field(content, "Instagram URL", social.optString("instagram", ""));
					EditText youtube = field(content, "YouTube URL", social.optString("youtube", ""));
					EditText twitter = field(content, "X / Twitter URL", social.optString("twitter", ""));
					content.addView(button("Save social profiles", v -> asyncAction(() -> {
						JSONObject value = new JSONObject().put("instagram", instagram.getText().toString().trim())
								.put("youtube", youtube.getText().toString().trim())
								.put("twitter", twitter.getText().toString().trim());
						api.put("/api/admin/site", new JSONObject().put("key", "social").put("value", value));
					}, this::loadSite)));

					content.addView(label("Checkout policy", 18));
					JSONObject checkout = data.optJSONObject("checkout");
					if (checkout == null)
						checkout = new JSONObject();
					CheckBox taxIncluded = check("Product prices include tax",
							checkout.optBoolean("tax_included", true));
					CheckBox allowGuest = check("Allow guest checkout", checkout.optBoolean("allow_guest", false));
					content.addView(taxIncluded);
					content.addView(allowGuest);
					EditText flatShipping = field(content, "Flat shipping fee",
							checkout.optString("flat_shipping", "0.00"));
					EditText freeShippingOver = field(content, "Free shipping above",
							checkout.optString("free_shipping_over", "0.00"));
					EditText minimumOrder = field(content, "Minimum order value",
							checkout.optString("minimum_order", "0.00"));
					flatShipping.setInputType(
							android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
					freeShippingOver.setInputType(
							android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
					minimumOrder.setInputType(
							android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
					content.addView(button("Save checkout policy", v -> {
						try {
							String flat = normalizedMoney(flatShipping.getText().toString(), "Flat shipping fee");
							String free = normalizedMoney(freeShippingOver.getText().toString(),
									"Free shipping threshold");
							String minimum = normalizedMoney(minimumOrder.getText().toString(), "Minimum order value");
							asyncAction(() -> {
								JSONObject value = new JSONObject().put("tax_included", taxIncluded.isChecked())
										.put("allow_guest", allowGuest.isChecked()).put("flat_shipping", flat)
										.put("free_shipping_over", free).put("minimum_order", minimum);
								api.put("/api/admin/site", new JSONObject().put("key", "checkout").put("value", value));
							}, this::loadSite);
						} catch (IllegalArgumentException error) {
							new AlertDialog.Builder(this).setTitle("Check checkout policy")
									.setMessage(error.getMessage()).setPositiveButton("OK", null).show();
						}
					}));
				});
	}

	@Override
	protected String normalizedMoney(String raw, String title) {
		String value = raw == null ? "" : raw.trim();
		if (value.isEmpty())
			value = "0.00";
		try {
			java.math.BigDecimal amount = new java.math.BigDecimal(value);
			if (amount.signum() < 0)
				throw new IllegalArgumentException(title + " cannot be negative.");
			return amount.setScale(2, java.math.RoundingMode.HALF_UP).toPlainString();
		} catch (NumberFormatException error) {
			throw new IllegalArgumentException(title + " must be a valid amount, such as 250 or 250.00.");
		}
	}

	@Override
	protected int parseColorOrDefault(String value, int fallback) {
		try {
			return Color.parseColor(value == null ? "" : value.trim());
		} catch (Exception ignored) {
			return fallback;
		}
	}

	@Override
	protected EditText colorField(LinearLayout box, String title, String value) {
		box.addView(label(title, 13));
		LinearLayout row = new LinearLayout(this);
		row.setOrientation(LinearLayout.HORIZONTAL);
		row.setGravity(Gravity.CENTER_VERTICAL);
		View swatch = new View(this);
		swatch.setBackground(outline(parseColorOrDefault(value, SURFACE), BORDER));
		LinearLayout.LayoutParams swatchParams = new LinearLayout.LayoutParams(dp(42), dp(42));
		swatchParams.setMargins(0, 0, dp(8), dp(10));
		row.addView(swatch, swatchParams);
		EditText hex = input("#RRGGBB", value);
		hex.setSingleLine(true);
		hex.setLayoutParams(new LinearLayout.LayoutParams(0, -2, 1));
		row.addView(hex);
		Button pick = button("Color wheel", v -> showColorPicker(hex, swatch));
		LinearLayout.LayoutParams pickParams = new LinearLayout.LayoutParams(-2, -2);
		pickParams.setMargins(dp(8), 0, 0, dp(10));
		row.addView(pick, pickParams);
		hex.addTextChangedListener(new android.text.TextWatcher() {
			@Override
			public void beforeTextChanged(CharSequence s, int start, int count, int after) {
			}

			@Override
			public void onTextChanged(CharSequence s, int start, int before, int count) {
				try {
					swatch.setBackground(outline(Color.parseColor(s.toString().trim()), BORDER));
				} catch (Exception ignored) {
					swatch.setBackground(outline(SURFACE, Color.parseColor("#b24a4a")));
				}
			}

			@Override
			public void afterTextChanged(android.text.Editable s) {
			}
		});
		box.addView(row);
		return hex;
	}

	@Override
	protected void showColorPicker(EditText target, View fieldSwatch) {
		int initial = parseColorOrDefault(target.getText().toString(), BLACK);
		LinearLayout panel = column(16);
		TextView sample = label(String.format(java.util.Locale.ROOT, "#%06X", initial & 0xFFFFFF), 14);
		View preview = new View(this);
		preview.setBackground(outline(initial, BORDER));
		panel.addView(preview, new LinearLayout.LayoutParams(-1, dp(34)));
		panel.addView(sample);
		ColorWheelView wheel = new ColorWheelView(this, initial, color -> {
			preview.setBackground(outline(color, BORDER));
			sample.setText(String.format(java.util.Locale.ROOT, "#%06X", color & 0xFFFFFF));
		});
		panel.addView(wheel, new LinearLayout.LayoutParams(-1, dp(250)));
		panel.addView(label("Brightness", 12));
		SeekBar brightness = new SeekBar(this);
		float[] initialHsv = new float[3];
		Color.colorToHSV(initial, initialHsv);
		brightness.setMax(100);
		brightness.setProgress(Math.round(initialHsv[2] * 100));
		brightness.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
			@Override
			public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
				wheel.setBrightness(progress / 100f);
			}

			@Override
			public void onStartTrackingTouch(SeekBar seekBar) {
			}

			@Override
			public void onStopTrackingTouch(SeekBar seekBar) {
			}
		});
		panel.addView(brightness);
		AlertDialog dialog = new AlertDialog.Builder(this)
				.setTitle("Choose " + "color")
				.setView(panel)
				.setNegativeButton("Cancel", null)
				.setPositiveButton("Use color", null)
				.create();
		dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
			int color = wheel.getSelectedColor();
			String hex = String.format(java.util.Locale.ROOT, "#%06X", color & 0xFFFFFF);
			target.setText(hex);
			fieldSwatch.setBackground(outline(color, BORDER));
			dialog.dismiss();
		}));
		dialog.show();
	}

	@Override
	protected void themeForm(JSONObject theme) {
		if (theme == null)
			theme = new JSONObject();
		JSONObject light = theme.optJSONObject("light");
		if (light == null)
			light = new JSONObject();
		clearContent();
		content.addView(label("Theme / colors", 23));
		content.addView(label(
				"Choose colors with the wheel or enter a hex code. This changes the storefront palette; the app's own dark mode is separate.",
				13));
		EditText lightBackground = colorField(content, "Background", light.optString("background", "#f7f7f5"));
		EditText lightSurface = colorField(content, "Surface", light.optString("surface", "#ffffff"));
		EditText lightText = colorField(content, "Text", light.optString("text", "#0a0a0a"));
		EditText lightMuted = colorField(content, "Muted text", light.optString("muted", "#686868"));
		EditText lightBorder = colorField(content, "Border", light.optString("border", "#d8d8d3"));
		EditText lightAccent = colorField(content, "Accent", light.optString("accent", "#0a0a0a"));
		EditText lightAccentText = colorField(content, "Accent text", light.optString("accent_text", "#ffffff"));
		EditText radius = field(content, "Corner radius (px)", String.valueOf(theme.optInt("radius", 0)));
		EditText max = field(content, "Max content width (px)", String.valueOf(theme.optInt("max_width", 1320)));
		content.addView(button("Save theme", v -> asyncAction(() -> {
			JSONObject lightValue = new JSONObject();
			lightValue.put("background", lightBackground.getText().toString());
			lightValue.put("surface", lightSurface.getText().toString());
			lightValue.put("text", lightText.getText().toString());
			lightValue.put("muted", lightMuted.getText().toString());
			lightValue.put("border", lightBorder.getText().toString());
			lightValue.put("accent", lightAccent.getText().toString());
			lightValue.put("accent_text", lightAccentText.getText().toString());
			JSONObject value = new JSONObject();
			value.put("mode", "light");
			value.put("light", lightValue);
			value.put("radius", parseInteger(radius, "Corner radius", 0));
			value.put("max_width", parseInteger(max, "Max content width", 1320));
			api.put("/api/admin/site", new JSONObject().put("key", "theme").put("value", value));
		}, this::loadSite)));
	}

	@Override
	protected Object parseJsonValue(String raw) throws JSONException {
		String s = raw.trim();
		if (s.startsWith("{"))
			return new JSONObject(s);
		if (s.startsWith("["))
			return new JSONArray(s);
		if ("true".equalsIgnoreCase(s) || "false".equalsIgnoreCase(s))
			return Boolean.parseBoolean(s);
		return s;
	}
}
