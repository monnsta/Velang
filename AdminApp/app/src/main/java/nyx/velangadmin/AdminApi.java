package nyx.velangadmin;

import java.io.IOException;
import java.util.concurrent.TimeUnit;
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.ResponseBody;
import org.json.JSONObject;

public final class AdminApi {
	private final OkHttpClient client = new OkHttpClient.Builder()
			.connectTimeout(15, TimeUnit.SECONDS)
			.readTimeout(30, TimeUnit.SECONDS)
			.build();
	private String baseUrl;
	private String token;

	public AdminApi(String baseUrl, String token) {
		setBaseUrl(baseUrl);
		this.token = token == null ? "" : token;
	}

	public void setBaseUrl(String value) {
		baseUrl = value == null ? "" : value.trim().replaceAll("/+$", "");
	}

	public void setToken(String token) {
		this.token = token == null ? "" : token;
	}

	public String getBaseUrl() {
		return baseUrl;
	}

	public JSONObject get(String path) throws Exception {
		return request("GET", path, null);
	}

	public JSONObject post(String path, JSONObject payload) throws Exception {
		return request("POST", path, payload == null ? null : payload.toString());
	}

	public JSONObject put(String path, JSONObject payload) throws Exception {
		return request("PUT", path, payload == null ? null : payload.toString());
	}

	public JSONObject delete(String path) throws Exception {
		return request("DELETE", path, null);
	}

	private JSONObject request(String method, String path, String json) throws Exception {
		Request.Builder builder = new Request.Builder().url(baseUrl + path);
		if (!token.isEmpty())
			builder.header("Authorization", "Bearer " + token);
		if (json != null) {
			RequestBody body = RequestBody.create(json, MediaType.parse("application/json; charset=utf-8"));
			if (method.equals("POST"))
				builder.post(body);
			else if (method.equals("PUT"))
				builder.put(body);
			else
				builder.method(method, body);
		} else
			builder.method(method, null);
		try (Response response = client.newCall(builder.build()).execute()) {
			ResponseBody body = response.body();
			String text = body == null ? "{}" : body.string();
			if (!response.isSuccessful()) {
				try {
					JSONObject error = new JSONObject(text);
					throw new IOException(error.optString("detail", "HTTP " + response.code()));
				} catch (org.json.JSONException ignored) {
					throw new IOException("HTTP " + response.code() + ": " + text);
				}
			}
			return new JSONObject(text);
		}
	}

	public JSONObject upload(
			String path, byte[] data, String filename, String mimeType, String altText) throws Exception {
		RequestBody fileBody = RequestBody.create(
				data, MediaType.parse(mimeType == null ? "application/octet-stream" : mimeType));
		MultipartBody body = new MultipartBody.Builder()
				.setType(MultipartBody.FORM)
				.addFormDataPart("file", filename, fileBody)
				.addFormDataPart("alt_text", altText == null ? "" : altText)
				.build();
		Request.Builder builder = new Request.Builder().url(baseUrl + path).post(body);
		if (!token.isEmpty())
			builder.header("Authorization", "Bearer " + token);
		try (Response response = client.newCall(builder.build()).execute()) {
			ResponseBody responseBody = response.body();
			String text = responseBody == null ? "{}" : responseBody.string();
			if (!response.isSuccessful())
				throw new IOException("HTTP " + response.code() + ": " + text);
			return new JSONObject(text);
		}
	}
}
