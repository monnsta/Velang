package nyx.velangadmin.features;

import android.widget.LinearLayout;
import org.json.JSONArray;
import org.json.JSONObject;
import static nyx.velangadmin.AdminJson.*;

public abstract class AdminUsersLayer extends AdminSiteLayer {
	@Override
	protected void loadUsers() {
		async(
				() -> api.get("/api/admin/users"),
				data -> {
					clearContent();
					JSONArray rows = data.optJSONArray("users");
					if (rows == null)
						return;
					for (int i = 0; i < rows.length(); i++) {
						JSONObject u = rows.optJSONObject(i);
						LinearLayout row = column(10);
						row.setBackground(outline(SURFACE, BORDER));
						row.addView(label(u.optString("name", u.optString("email")), 18));
						row.addView(label(u.optString("email"), 13));
						row.addView(
								button(
										u.optBoolean("is_active") ? "Deactivate" : "Activate",
										v -> toggleUser(
												u.optInt("id"), !u.optBoolean("is_active"), u.optBoolean("is_admin"))));
						row.addView(
								button(
										u.optBoolean("is_admin") ? "Remove admin" : "Make admin",
										v -> toggleUser(u.optInt("id"), u.optBoolean("is_active"),
												!u.optBoolean("is_admin"))));
						row.addView(button("Delete account", v -> confirm("Delete account?",
								"Unused accounts can be deleted. Accounts with order history are protected and must be deactivated instead.",
								() -> asyncAction(() -> api.delete("/api/admin/users/" + u.optInt("id")),
										this::loadUsers))));
						content.addView(row);
					}
				});
	}

	@Override
	protected void toggleUser(int id, boolean active, boolean admin) {
		asyncAction(
				() -> api.put(
						"/api/admin/users/" + id,
						new JSONObject().put("is_active", active).put("is_admin", admin)),
				() -> loadUsers());
	}
}
