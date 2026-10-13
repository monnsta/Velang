package nyx.velangadmin.features;

import android.app.AlertDialog;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageButton;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import nyx.velangadmin.R;
import nyx.velangadmin.core.AdminCoreActivity;
import org.json.JSONObject;

/**
 * Login, application chrome, navigation history, drawer, and connection
 * settings.
 */
public abstract class AdminShellLayer extends AdminCoreActivity {
	protected String activeScreenTitle = "Dashboard";
	protected Runnable activeScreenLoader;
	protected final java.util.ArrayList<ScreenRecord> screenHistory = new java.util.ArrayList<>();
	protected long lastBackPressed;
	protected View drawerBackdrop;
	protected View navigationDrawer;

	protected static final class ScreenRecord {
		public final String title;
		public final Runnable loader;

		protected ScreenRecord(String title, Runnable loader) {
			this.title = title;
			this.loader = loader;
		}
	}

	protected void navigateScreen(String title, Runnable loader) {
		if ("Dashboard".equals(title)) {
			screenHistory.clear();
		} else if (activeScreenLoader != null && !title.equals(activeScreenTitle)) {
			screenHistory.add(new ScreenRecord(activeScreenTitle, activeScreenLoader));
		}
		activeScreenTitle = title;
		activeScreenLoader = loader;
		if (pageTitle != null)
			pageTitle.setText(title);
		loader.run();
	}

	protected void setScreenWithoutHistory(String title, Runnable loader) {
		activeScreenTitle = title;
		activeScreenLoader = loader;
		if (pageTitle != null)
			pageTitle.setText(title);
		loader.run();
	}

	@Override
	public void onBackPressed() {
		if (navigationDrawer != null && navigationDrawer.getVisibility() == View.VISIBLE) {
			setDrawerOpen(false);
			return;
		}
		if (!screenHistory.isEmpty()) {
			ScreenRecord previous = screenHistory.remove(screenHistory.size() - 1);
			activeScreenTitle = previous.title;
			activeScreenLoader = previous.loader;
			if (pageTitle != null)
				pageTitle.setText(previous.title);
			previous.loader.run();
			return;
		}
		if (!"Dashboard".equals(activeScreenTitle) && apiToken().length() > 0) {
			setScreenWithoutHistory("Dashboard", this::loadDashboard);
			return;
		}
		long now = android.os.SystemClock.elapsedRealtime();
		if (now - lastBackPressed < 2000) {
			super.onBackPressed();
		} else {
			lastBackPressed = now;
			Toast.makeText(this, "Press back again to exit", Toast.LENGTH_SHORT).show();
		}
	}

	@Override
	protected void showLogin() {
		LinearLayout box = column(24);
		box.setBackgroundColor(BG);
		box.setGravity(Gravity.CENTER_HORIZONTAL);
		box.addView(label("VELANG", 28));
		box.addView(label("Admin device", 18));
		box.addView(label(
				"Connect this installation to your store. Pairing is needed only once; the app stores a revocable session token.",
				14));
		EditText server = input("Store URL, e.g. https://velang.example.com", api.getBaseUrl());
		server.setSingleLine(true);
		box.addView(server);
		EditText pairingKey = input("One-time server pairing key", "");
		pairingKey.setSingleLine(true);
		pairingKey.setInputType(
				android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
		box.addView(pairingKey);
		Button pair = button("Verify server and pair device", null);
		pair.setOnClickListener(v -> {
			String candidate = server.getText().toString().trim().replaceAll("/+$", "");
			String key = pairingKey.getText().toString();
			if (!(candidate.startsWith("https://") || candidate.startsWith("http://"))) {
				Toast.makeText(this, "Enter a complete server URL", Toast.LENGTH_LONG).show();
				return;
			}
			if (key.isEmpty()) {
				Toast.makeText(this, "Enter the server pairing key", Toast.LENGTH_LONG).show();
				return;
			}
			String previous = api.getBaseUrl();
			pair.setEnabled(false);
			executor.execute(() -> {
				boolean serverVerified = false;
				try {
					api.setBaseUrl(candidate);
					api.get("/api/admin/config");
					serverVerified = true;
					prefs.edit().putString("server", candidate).apply();
					String deviceId = prefs.getString("device_id", "");
					if (deviceId.isEmpty()) {
						deviceId = java.util.UUID.randomUUID().toString() + java.util.UUID.randomUUID();
						prefs.edit().putString("device_id", deviceId).apply();
					}
					JSONObject result = api.post("/api/admin/pair",
							new JSONObject().put("key", key).put("device_id", deviceId));
					String token = result.getString("token");
					prefs.edit().putString("server", candidate).putString("token", token).apply();
					api.setToken(token);
					runOnUiThread(() -> showShell("Dashboard", this::loadDashboard));
				} catch (Exception error) {
					if (serverVerified)
						api.setBaseUrl(candidate);
					else
						api.setBaseUrl(previous);
					runOnUi(() -> {
						pair.setEnabled(true);
						Toast.makeText(this, "Connection or pairing failed: " + error.getMessage(), Toast.LENGTH_LONG)
								.show();
					});
				}
			});
		});
		box.addView(pair);
		TextView status = label("The server must have ADMIN_PAIRING_KEY configured. Use HTTPS on public networks.", 13);
		status.setTextColor(MUTED);
		box.addView(status);
		frame(box);
	}

	@Override
	protected void showShell(String title, Runnable loader) {
		screenHistory.clear();
		activeScreenTitle = title;
		activeScreenLoader = loader;
		FrameLayout shell = new FrameLayout(this);
		shell.setBackgroundColor(BG);
		LinearLayout outer = column(0);
		outer.setBackgroundColor(BG);

		LinearLayout top = new LinearLayout(this);
		top.setGravity(Gravity.CENTER_VERTICAL);
		top.setPadding(dp(8), dp(7), dp(8), dp(7));
		top.setBackgroundColor(SURFACE);
		ImageButton menuButton = iconButton(R.drawable.ic_menu, "Open navigation drawer", v -> setDrawerOpen(true));
		top.addView(menuButton, new LinearLayout.LayoutParams(dp(42), dp(42)));
		pageTitle = label(title, 20);
		pageTitle.setSingleLine(true);
		pageTitle.setEllipsize(TextUtils.TruncateAt.END);
		LinearLayout.LayoutParams titleParams = new LinearLayout.LayoutParams(0, -2, 1);
		titleParams.setMargins(dp(6), 0, dp(4), 0);
		top.addView(pageTitle, titleParams);
		top.addView(iconButton(R.drawable.ic_refresh, "Refresh this page", v -> activeScreenLoader.run()),
				new LinearLayout.LayoutParams(dp(42), dp(42)));
		outer.addView(top);

		contentScroll = new ScrollView(this);
		contentScroll.setFillViewport(true);
		content = column(16);
		contentScroll.addView(content);
		outer.addView(contentScroll, new LinearLayout.LayoutParams(-1, 0, 1));
		stickyActions = new LinearLayout(this);
		stickyActions.setOrientation(LinearLayout.HORIZONTAL);
		stickyActions.setGravity(Gravity.CENTER_VERTICAL);
		stickyActions.setPadding(dp(12), dp(8), dp(12), dp(8));
		stickyActions.setBackground(outline(SURFACE, BORDER));
		stickyActions.setVisibility(View.GONE);
		outer.addView(stickyActions, new LinearLayout.LayoutParams(-1, -2));
		shell.addView(outer, new FrameLayout.LayoutParams(-1, -1));

		drawerBackdrop = new View(this);
		drawerBackdrop.setBackgroundColor(0x66000000);
		drawerBackdrop.setVisibility(View.GONE);
		drawerBackdrop.setOnClickListener(v -> setDrawerOpen(false));
		shell.addView(drawerBackdrop, new FrameLayout.LayoutParams(-1, -1));

		LinearLayout drawer = column(14);
		drawer.setBackgroundColor(SURFACE);
		drawer.setElevation(dp(12));
		drawer.addView(label("VELANG", 22));
		drawer.addView(label("Store administration", 12));
		LinearLayout tools = new LinearLayout(this);
		tools.setGravity(Gravity.CENTER_VERTICAL);
		ImageButton themeButton = iconButton(R.drawable.ic_theme,
				darkMode ? "Switch to light theme" : "Switch to dark theme", v -> {
					prefs.edit().putBoolean("dark_mode", !darkMode).apply();
					recreate();
				});
		ImageButton serverButton = iconButton(R.drawable.ic_server, "Server connection settings",
				v -> showServerSettings());
		ImageButton logoutButton = iconButton(R.drawable.ic_logout, "Log out", v -> logout());
		tools.addView(themeButton, new LinearLayout.LayoutParams(dp(48), dp(48)));
		tools.addView(serverButton, new LinearLayout.LayoutParams(dp(48), dp(48)));
		tools.addView(logoutButton, new LinearLayout.LayoutParams(dp(48), dp(48)));
		drawer.addView(tools);
		drawer.addView(label("NAVIGATION", 11));
		ScrollView navScroll = new ScrollView(this);
		LinearLayout pageNavigation = column(4);
		String[] pages = { "Dashboard", "Products", "Categories", "Templates", "Orders", "Pages", "Site", "Users",
				"Media", "Audit" };
		for (String item : pages) {
			Button pageButton = button(item, v -> {
				setDrawerOpen(false);
				navigateScreen(item, loaderForPage(item));
			});
			pageButton.setGravity(Gravity.CENTER_VERTICAL | Gravity.START);
			pageButton.setPadding(dp(14), dp(5), dp(14), dp(5));
			pageNavigation.addView(pageButton, new LinearLayout.LayoutParams(-1, -2));
		}
		navScroll.addView(pageNavigation);
		drawer.addView(navScroll, new LinearLayout.LayoutParams(-1, 0, 1));
		navigationDrawer = drawer;
		FrameLayout.LayoutParams drawerParams = new FrameLayout.LayoutParams(dp(280), -1, Gravity.LEFT | Gravity.TOP);
		shell.addView(drawer, drawerParams);
		setDrawerOpen(false);
		frame(shell);
		loader.run();
	}

	protected Runnable loaderForPage(String item) {
		switch (item) {
			case "Dashboard":
				return this::loadDashboard;
			case "Products":
				return this::loadProducts;
			case "Categories":
				return this::loadCategories;
			case "Templates":
				return this::loadTemplates;
			case "Orders":
				return this::loadOrders;
			case "Pages":
				return this::loadPages;
			case "Site":
				return this::loadSite;
			case "Users":
				return this::loadUsers;
			case "Media":
				return this::loadMedia;
			default:
				return this::loadAudit;
		}
	}

	protected void setDrawerOpen(boolean open) {
		if (drawerBackdrop == null || navigationDrawer == null)
			return;
		drawerBackdrop.setVisibility(open ? View.VISIBLE : View.GONE);
		navigationDrawer.setVisibility(open ? View.VISIBLE : View.GONE);
		if (open) {
			drawerBackdrop.bringToFront();
			navigationDrawer.bringToFront();
		}
	}

	protected void showServerSettings() {
		EditText field = input("https://store.example.com", api.getBaseUrl());
		field.setSingleLine(true);
		new AlertDialog.Builder(this)
				.setTitle("Server connection")
				.setMessage("Use the HTTPS address of your Velang storefront.")
				.setView(field)
				.setNegativeButton("Cancel", null)
				.setPositiveButton("Verify and save", (dialog, which) -> {
					String candidate = field.getText().toString().trim().replaceAll("/+$", "");
					if (!(candidate.startsWith("https://") || candidate.startsWith("http://"))) {
						Toast.makeText(this, "Enter a complete http:// or https:// URL", Toast.LENGTH_LONG).show();
						return;
					}
					String previous = api.getBaseUrl();
					executor.execute(() -> {
						try {
							api.setBaseUrl(candidate);
							api.get("/api/admin/config");
							prefs.edit().putString("server", candidate).apply();
							runOnUiThread(() -> Toast.makeText(this, "Server saved", Toast.LENGTH_SHORT).show());
						} catch (Exception error) {
							api.setBaseUrl(previous);
							runOnUiThread(() -> Toast
									.makeText(this, "Server check failed: " + error.getMessage(), Toast.LENGTH_LONG)
									.show());
						}
					});
				})
				.show();
	}

	protected void logout() {
		executor.execute(
				() -> {
					try {
						api.post("/api/admin/logout", null);
					} catch (Exception ignored) {
					}
					prefs.edit().remove("token").apply();
					runOnUi(this::showLogin);
				});
	}

}
