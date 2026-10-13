package nyx.velangadmin.features;

import android.widget.LinearLayout;
import org.json.JSONArray;
import org.json.JSONObject;
import static nyx.velangadmin.AdminJson.*;

public abstract class AdminAuditLayer extends AdminPreviewLayer {
	@Override
	protected void loadAudit() {
		async(
				() -> api.get("/api/admin/audit"),
				data -> {
					clearContent();
					content.addView(label("Recent admin activity", 23));
					content.addView(
							label(
									"The server records changes so you can see what was edited without digging through the database.",
									13));
					JSONArray rows = data.optJSONArray("audit");
					if (rows == null)
						return;
					for (int i = 0; i < rows.length(); i++) {
						JSONObject a = rows.optJSONObject(i);
						LinearLayout row = column(10);
						row.setBackground(outline(SURFACE, BORDER));
						row.addView(label(a.optString("action"), 17));
						row.addView(
								label(
										a.optString("entity_type")
												+ " #"
												+ a.optString("entity_id")
												+ " · "
												+ a.optString("created_at"),
										12));
						row.addView(
								label(
										a.optJSONObject("details") == null ? "" : a.optJSONObject("details").toString(),
										12));
						content.addView(row);
					}
				});
	}
}
