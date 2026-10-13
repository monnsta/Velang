package nyx.velangadmin.features;

import org.json.JSONObject;
import static nyx.velangadmin.AdminJson.*;

public abstract class AdminDashboardLayer extends AdminShellLayer {
	@Override
	protected void loadDashboard() {
		async(
				() -> api.get("/api/admin/dashboard"),
				data -> {
					clearContent();
					JSONObject c = data.optJSONObject("counts");
					content.addView(
							label("Signed in as " + data.optJSONObject("admin").optString("email"), 14));
					String[] keys = { "products", "categories", "orders", "users" };
					for (String k : keys) {
						content.addView(label(k.toUpperCase() + "   " + c.optInt(k), 28));
					}
				});
	}
}
