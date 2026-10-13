package nyx.velangadmin;

import android.widget.EditText;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/** JSON conversion and display helpers shared by admin screens. */
public final class AdminJson {
	private AdminJson() {
	}

	public static String jsonObjectText(JSONObject value) {
		return value == null ? "{}" : value.toString();
	}

	public static String jsonValueText(JSONObject object, String key, String fallback) {
		if (object == null)
			return fallback;
		Object value = object.opt(key);
		return value == null || value == JSONObject.NULL ? fallback : String.valueOf(value);
	}

	public static String jsonArrayText(JSONObject object, String key) {
		JSONArray value = object == null ? null : object.optJSONArray(key);
		return value == null ? "[]" : value.toString();
	}

	public static String readableDetails(JSONObject source) {
		if (source == null || source.length() == 0)
			return "";
		StringBuilder output = new StringBuilder();
		java.util.Iterator<String> keys = source.keys();
		while (keys.hasNext()) {
			String key = keys.next();
			Object raw = source.opt(key);
			if (raw == null || raw == JSONObject.NULL)
				continue;
			if (raw instanceof JSONObject) {
				JSONObject nested = (JSONObject) raw;
				java.util.Iterator<String> childKeys = nested.keys();
				while (childKeys.hasNext()) {
					String childKey = childKeys.next();
					String value = nested.optString(childKey, "").trim();
					if (value.isEmpty())
						continue;
					if (output.length() > 0)
						output.append('\n');
					output.append(humanizeDetailKey(childKey)).append(": ").append(value);
				}
				continue;
			}
			String value = String.valueOf(raw).trim();
			if (value.isEmpty() || "[]".equals(value) || "{}".equals(value))
				continue;
			if (output.length() > 0)
				output.append('\n');
			output.append(humanizeDetailKey(key)).append(": ").append(value);
		}
		return output.toString();
	}

	private static String humanizeDetailKey(String key) {
		if (key == null || key.isEmpty())
			return "Details";
		String spaced = key.replace('_', ' ');
		return Character.toUpperCase(spaced.charAt(0)) + spaced.substring(1);
	}

	public static String separatedArray(JSONArray array, String separator) {
		if (array == null || array.length() == 0)
			return "";
		StringBuilder output = new StringBuilder();
		for (int i = 0; i < array.length(); i++) {
			Object value = array.opt(i);
			if (value == null || value == JSONObject.NULL)
				continue;
			if (output.length() > 0)
				output.append(separator);
			output.append(String.valueOf(value));
		}
		return output.toString();
	}

	public static String imageLines(JSONArray images) {
		if (images == null || images.length() == 0)
			return "";
		StringBuilder output = new StringBuilder();
		for (int i = 0; i < images.length(); i++) {
			JSONObject image = images.optJSONObject(i);
			if (image == null)
				continue;
			String path = jsonValueText(image, "path", "").trim();
			if (path.isEmpty())
				continue;
			if (output.length() > 0)
				output.append('\n');
			output.append(path);
			String alt = jsonValueText(image, "alt_text", "").trim();
			if (!alt.isEmpty())
				output.append(" | ").append(alt);
		}
		return output.toString();
	}

	public static JSONArray parseStringArray(String raw, String fieldName) throws JSONException {
		String value = raw == null ? "" : raw.trim();
		if (value.isEmpty())
			return new JSONArray();
		if (value.startsWith("[")) {
			try {
				return new JSONArray(value);
			} catch (JSONException e) {
				throw new IllegalArgumentException(fieldName + " must be a valid JSON array or comma-separated list.");
			}
		}
		JSONArray array = new JSONArray();
		for (String item : value.split(",")) {
			String trimmed = item.trim();
			if (!trimmed.isEmpty())
				array.put(trimmed);
		}
		return array;
	}

	public static JSONArray parseCategoryIds(String raw) throws JSONException {
		String value = raw == null ? "" : raw.trim();
		JSONArray output = new JSONArray();
		if (value.isEmpty())
			return output;
		JSONArray input;
		if (value.startsWith("[")) {
			try {
				input = new JSONArray(value);
			} catch (JSONException e) {
				throw new IllegalArgumentException(
						"Category IDs must be comma-separated whole numbers, for example 1, 2.");
			}
		} else {
			input = new JSONArray();
			for (String item : value.split(",")) {
				if (!item.trim().isEmpty())
					input.put(item.trim());
			}
		}
		for (int i = 0; i < input.length(); i++) {
			Object item = input.opt(i);
			try {
				if (item == null || item == JSONObject.NULL)
					throw new NumberFormatException();
				output.put(Integer.parseInt(String.valueOf(item).trim()));
			} catch (NumberFormatException e) {
				throw new IllegalArgumentException("Category IDs must contain only whole numbers, for example 1, 2.");
			}
		}
		return output;
	}

	public static JSONArray parseImages(String raw) throws JSONException {
		String value = raw == null ? "" : raw.trim();
		if (value.isEmpty())
			return new JSONArray();
		if (value.startsWith("[")) {
			JSONArray parsed;
			try {
				parsed = new JSONArray(value);
			} catch (JSONException e) {
				throw new IllegalArgumentException(
						"Images must be one path per line, optionally followed by | alt text.");
			}
			for (int i = 0; i < parsed.length(); i++) {
				JSONObject image = parsed.optJSONObject(i);
				if (image == null || jsonValueText(image, "path", "").trim().isEmpty()) {
					throw new IllegalArgumentException("Each image must be an object with a non-empty path.");
				}
				if (image.isNull("alt_text"))
					image.put("alt_text", "");
			}
			return parsed;
		}
		JSONArray output = new JSONArray();
		for (String line : value.split("\\r?\\n")) {
			String item = line.trim();
			if (item.isEmpty())
				continue;
			String[] pieces = item.split("\\s*\\|\\s*", 2);
			JSONObject image = new JSONObject();
			image.put("path", pieces[0].trim());
			image.put("alt_text", pieces.length > 1 ? pieces[1].trim() : "");
			output.put(image);
		}
		return output;
	}

	public static int parseInteger(EditText field, String name, int fallback) {
		String raw = field.getText().toString().trim();
		if (raw.isEmpty())
			return fallback;
		try {
			return Integer.parseInt(raw);
		} catch (NumberFormatException e) {
			throw new IllegalArgumentException(name + " must be a whole number.");
		}
	}

	public static String categorySummaryText(JSONArray categories, java.util.Set<Integer> selected) {
		if (selected == null || selected.isEmpty())
			return "No categories selected";
		java.util.ArrayList<String> names = new java.util.ArrayList<>();
		if (categories != null)
			for (int i = 0; i < categories.length(); i++) {
				JSONObject item = categories.optJSONObject(i);
				if (item != null && selected.contains(item.optInt("id")))
					names.add(categoryOptionLabel(item, categories));
			}
		return names.isEmpty() ? "No categories selected" : "Selected: " + android.text.TextUtils.join(" · ", names);
	}

	public static JSONObject rowById(JSONArray rows, int id) {
		if (rows == null)
			return null;
		for (int i = 0; i < rows.length(); i++) {
			JSONObject row = rows.optJSONObject(i);
			if (row != null && row.optInt("id") == id)
				return row;
		}
		return null;
	}

	public static String categoryOptionLabel(JSONObject row, JSONArray all) {
		return categoryOptionLabel(row, all, new java.util.HashSet<Integer>());
	}

	private static String categoryOptionLabel(JSONObject row, JSONArray all, java.util.Set<Integer> visited) {
		if (row == null)
			return "Unnamed category";
		String name = jsonValueText(row, "name", "Unnamed category");
		int id = row.optInt("id", 0);
		if (id > 0 && !visited.add(id))
			return name + " (cycle)";
		int parentId = row.optInt("parent_id", 0);
		JSONObject parent = parentId > 0 ? rowById(all, parentId) : null;
		if (parent != null)
			return categoryOptionLabel(parent, all, visited) + " / " + name;
		return name;
	}
}
