package nyx.velangadmin;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.credentials.Credential;
import androidx.credentials.CredentialManager;
import androidx.credentials.CustomCredential;
import androidx.credentials.CredentialManagerCallback;
import androidx.credentials.GetCredentialRequest;
import androidx.credentials.GetCredentialResponse;
import androidx.credentials.exceptions.GetCredentialException;

import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption;
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

public class MainActivity extends Activity {
	private final Executor executor = Executors.newCachedThreadPool();
	private final int BG = Color.rgb(247, 247, 245);
	private final int BLACK = Color.BLACK;
	private final int MUTED = Color.rgb(100, 100, 100);
	private SharedPreferences prefs;
	private AdminApi api;
	private String googleClientId = "";
	private LinearLayout root;
	private LinearLayout content;
	private TextView pageTitle;

	@Override public void onCreate(Bundle state) {
		super.onCreate(state);
		prefs = getSharedPreferences("velang_admin", MODE_PRIVATE);
		api = new AdminApi(prefs.getString("server", "http://127.0.0.1:8000"), prefs.getString("token", ""));
		if (apiToken().isEmpty()) showLogin(); else showShell("Dashboard", this::loadDashboard);
	}

	private String apiToken() { return prefs.getString("token", ""); }

	private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

	private LinearLayout column(int padding) {
		LinearLayout box = new LinearLayout(this);
		box.setOrientation(LinearLayout.VERTICAL);
		box.setPadding(dp(padding), dp(padding), dp(padding), dp(padding));
		return box;
	}

	private TextView label(String text, float size) {
		TextView v = new TextView(this);
		v.setText(text);
		v.setTextSize(size);
		v.setTextColor(BLACK);
		v.setPadding(0, dp(5), 0, dp(5));
		return v;
	}

	private GradientDrawable outline(int fill, int stroke) {
		GradientDrawable drawable = new GradientDrawable();
		drawable.setColor(fill);
		drawable.setStroke(dp(1), stroke);
		drawable.setCornerRadius(dp(2));
		return drawable;
	}

	private EditText input(String hint, String value) {
		EditText e = new EditText(this);
		e.setHint(hint);
		e.setText(value == null ? "" : value);
		e.setTextColor(BLACK);
		e.setHintTextColor(MUTED);
		e.setSingleLine(false);
		e.setBackground(outline(Color.WHITE, Color.rgb(205, 205, 200)));
		e.setPadding(dp(14), dp(11), dp(14), dp(11));
		LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT);
		lp.setMargins(0, 0, 0, dp(10));
		e.setLayoutParams(lp);
		return e;
	}

	private Button button(String text, View.OnClickListener listener) {
		Button b = new Button(this);
		b.setText(text);
		b.setAllCaps(false);
		b.setTextColor(BLACK);
		b.setBackground(outline(Color.WHITE, BLACK));
		b.setPadding(dp(12), dp(4), dp(12), dp(4));
		b.setMinHeight(dp(42));
		b.setElevation(0);
		b.setStateListAnimator(null);
		b.setOnClickListener(listener);
		return b;
	}

	private CheckBox check(String text, boolean value) {
		CheckBox c = new CheckBox(this);
		c.setText(text);
		c.setTextColor(BLACK);
		c.setChecked(value);
		return c;
	}

	private void frame(View view) {
		root = column(0); root.setBackgroundColor(BG); root.addView(view, new LinearLayout.LayoutParams(-1, -1)); setContentView(root);
	}

	private void showLogin() {
		LinearLayout box = column(24); box.setBackgroundColor(BG); box.setGravity(Gravity.CENTER_HORIZONTAL);
		box.addView(label("VELANG", 28)); box.addView(label("Admin", 18));
		box.addView(label("This is the native control app. No WebView is used.", 14));
		EditText server = input("Server URL, e.g. https://velang.example.com", api.getBaseUrl());
		box.addView(server);
		Button save = button("Save server", v -> { api.setBaseUrl(server.getText().toString()); prefs.edit().putString("server", api.getBaseUrl()).apply(); Toast.makeText(this, "Server saved", Toast.LENGTH_SHORT).show(); });
		box.addView(save);
		Button google = button("Sign in with Google", v -> signInGoogle()); box.addView(google);
		TextView status = label("", 13); status.setTextColor(MUTED); box.addView(status);
		frame(box); loadGoogleConfig(status);
	}

	private void loadGoogleConfig(TextView status) {
		executor.execute(() -> { try {
			JSONObject config = api.get("/api/admin/config"); googleClientId = config.optString("google_web_client_id", "");
			runOnUi(() -> status.setText(googleClientId.isEmpty() ? "Google Sign-In is not configured on this server." : "Google Sign-In is ready."));
		} catch (Exception e) { runOnUi(() -> status.setText("Server check failed: " + e.getMessage())); } });
	}

	private void signInGoogle() {
		if (googleClientId.isEmpty()) { Toast.makeText(this, "Configure GOOGLE_WEB_CLIENT_ID on the server first", Toast.LENGTH_LONG).show(); return; }
		CredentialManager manager = CredentialManager.create(this);
		GetSignInWithGoogleOption option = new GetSignInWithGoogleOption.Builder(googleClientId)
				.setNonce(java.util.UUID.randomUUID().toString())
				.build();
		GetCredentialRequest request = new GetCredentialRequest.Builder().addCredentialOption(option).build();
		manager.getCredentialAsync(this, request, null, getMainExecutor(), new CredentialManagerCallback<GetCredentialResponse, GetCredentialException>() {
			@Override public void onResult(GetCredentialResponse response) { handleCredential(response.getCredential()); }
			@Override public void onError(GetCredentialException e) { runOnUiThread(() -> Toast.makeText(MainActivity.this, e.getMessage(), Toast.LENGTH_LONG).show()); }
		});
	}

	private void handleCredential(Credential credential) {
		try {
			if (!(credential instanceof CustomCredential)) throw new IllegalStateException("Unexpected credential type");
			GoogleIdTokenCredential google = GoogleIdTokenCredential.createFrom(((CustomCredential) credential).getData());
			executor.execute(() -> { try {
				JSONObject result = api.post("/api/admin/login/google", new JSONObject().put("credential", google.getIdToken()));
				String token = result.getString("token"); prefs.edit().putString("token", token).apply(); api.setToken(token); runOnUiThread(() -> showShell("Dashboard", this::loadDashboard));
			} catch (Exception e) { runOnUi(() -> Toast.makeText(this, e.getMessage(), Toast.LENGTH_LONG).show()); } });
		} catch (Exception e) { Toast.makeText(this, e.getMessage(), Toast.LENGTH_LONG).show(); }
	}

	private void showShell(String title, Runnable loader) {
		LinearLayout outer = column(0); outer.setBackgroundColor(BG);
		LinearLayout top = new LinearLayout(this); top.setGravity(Gravity.CENTER_VERTICAL); top.setPadding(dp(12), dp(12), dp(12), dp(12)); top.setBackgroundColor(Color.WHITE);
		pageTitle = label(title, 21); top.addView(pageTitle, new LinearLayout.LayoutParams(0, -2, 1)); top.addView(button("↻", v -> loader.run())); top.addView(button("Logout", v -> logout())); outer.addView(top);
		HorizontalScrollView navScroll = new HorizontalScrollView(this); LinearLayout nav = new LinearLayout(this); nav.setPadding(dp(8), dp(4), dp(8), dp(4));
		String[] pages = {"Dashboard", "Products", "Categories", "Templates", "Orders", "Coupons", "Pages", "Site", "Users", "Media", "Audit"};
		for (String item : pages) { Button b = button(item, v -> { pageTitle.setText(item); switch (item) { case "Dashboard": loadDashboard(); break; case "Products": loadProducts(); break; case "Categories": loadCategories(); break; case "Templates": loadTemplates(); break; case "Orders": loadOrders(); break; case "Coupons": loadCoupons(); break; case "Pages": loadPages(); break; case "Site": loadSite(); break; case "Users": loadUsers(); break; case "Media": loadMedia(); break; case "Audit": loadAudit(); break; } }); nav.addView(b); }
		navScroll.addView(nav); outer.addView(navScroll);
		ScrollView scroll = new ScrollView(this); content = column(16); scroll.addView(content); outer.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
		frame(outer); loader.run();
	}

	private void clearContent() { content.removeAllViews(); }
	private void busy(boolean busy) { if (content == null) return; if (busy) content.addView(new ProgressBar(this)); }
	private void loadDashboard() { async(() -> api.get("/api/admin/dashboard"), data -> { clearContent(); JSONObject c=data.optJSONObject("counts"); content.addView(label("Signed in as " + data.optJSONObject("admin").optString("email"), 14)); String[] keys={"products","categories","orders","users"}; for(String k:keys){ content.addView(label(k.toUpperCase()+"   "+c.optInt(k), 28)); } content.addView(label("Everything in this app talks to the small /api/admin surface. There is no admin webpage to accidentally expose.", 14)); }); }

	private void loadProducts() {
		async(() -> api.get("/api/admin/products"), data -> { clearContent(); content.addView(button("＋ New product", v -> productForm(null))); JSONArray rows=data.optJSONArray("products"); if(rows==null) return; for(int i=0;i<rows.length();i++){ JSONObject p=rows.optJSONObject(i); LinearLayout row=column(10); row.setBackgroundColor(Color.WHITE); row.addView(label(p.optString("name"),18)); row.addView(label(p.optString("sku")+" · INR "+p.optString("price")+" · "+p.optString("status")+" · stock "+p.optInt("stock_count"),13)); row.addView(button("Edit",v->loadProduct(p.optInt("id")))); content.addView(row); } });
	}

	private void loadProduct(int id){ async(()->api.get("/api/admin/products/"+id), data->productForm(data)); }

	private EditText field(LinearLayout box,String title,String value){ box.addView(label(title,12)); EditText e=input(title,value); box.addView(e); return e; }
	private void productForm(JSONObject p){
		clearContent(); boolean edit=p!=null; content.addView(label(edit?"Edit product":"New product",23));
		EditText name=field(content,"Name",p==null?"":p.optString("name")); EditText slug=field(content,"Slug",p==null?"":p.optString("slug")); EditText sku=field(content,"SKU",p==null?"":p.optString("sku")); EditText subtitle=field(content,"Subtitle",p==null?"":p.optString("subtitle")); EditText type=field(content,"Product type",p==null?"general":p.optString("product_type")); EditText price=field(content,"Price",p==null?"0":p.optString("price")); EditText compare=field(content,"Compare-at price",p==null?"":String.valueOf(p.opt("compare_at_price"))); EditText status=field(content,"Status (draft / active / archived)",p==null?"draft":p.optString("status")); EditText visibility=field(content,"Visibility",p==null?"public":p.optString("visibility")); CheckBox featured=check("Featured",p!=null&&p.optBoolean("featured")); content.addView(featured); EditText stock=field(content,"Stock count",p==null?"0":String.valueOf(p.optInt("stock_count"))); CheckBox track=check("Track inventory",p==null||p.optBoolean("track_inventory",true)); content.addView(track); EditText threshold=field(content,"Low stock threshold",p==null?"2":String.valueOf(p.optInt("low_stock_threshold",2))); EditText badge=field(content,"Badge",p==null?"":p.optString("badge")); EditText material=field(content,"Material",p==null?"":p.optString("material")); EditText care=field(content,"Care",p==null?"":p.optString("care")); EditText dimensions=field(content,"Dimensions",p==null?"":p.optString("dimensions")); EditText shipping=field(content,"Shipping note",p==null?"":p.optString("shipping_note")); EditText description=field(content,"Product description (Markdown)",p==null?"":p.optString("description")); EditText template=field(content,"Description template ID (blank = none)",p==null?"":String.valueOf(p.opt("description_template_id"))); EditText tags=field(content,"Tags (JSON array)",p==null?"[]":p.optJSONArray("tags").toString()); EditText categories=field(content,"Category IDs (JSON array)",p==null?"[]":p.optJSONArray("category_ids").toString()); EditText images=field(content,"Images (JSON array of {path,alt_text})",p==null?"[]":p.optJSONArray("images").toString()); EditText variants=field(content,"Variants (JSON array)",p==null?"[]":p.optJSONArray("variants").toString()); EditText meta=field(content,"Advanced metadata (JSON object)",p==null?"{}":p.optJSONObject("meta").toString()); EditText seoTitle=field(content,"SEO title",p==null?"":p.optString("seo_title")); EditText seoDescription=field(content,"SEO description",p==null?"":p.optString("seo_description"));
		content.addView(button("Save product",v->asyncSaveProduct(p==null?0:p.optInt("id"), name,slug,sku,subtitle,type,price,compare,status,visibility,featured,stock,track,threshold,badge,material,care,dimensions,shipping,description,template,tags,categories,images,variants,meta,seoTitle,seoDescription)));
		if(edit) content.addView(button("Delete product",v->asyncAction(()->api.delete("/api/admin/products/"+p.optInt("id")),()->loadProducts())));
	}

	private void asyncSaveProduct(int id, EditText name,EditText slug,EditText sku,EditText subtitle,EditText type,EditText price,EditText compare,EditText status,EditText visibility,CheckBox featured,EditText stock,CheckBox track,EditText threshold,EditText badge,EditText material,EditText care,EditText dimensions,EditText shipping,EditText description,EditText template,EditText tags,EditText categories,EditText images,EditText variants,EditText meta,EditText seoTitle,EditText seoDescription){
		asyncAction(()->{ JSONObject b=new JSONObject(); b.put("name",name.getText().toString()); b.put("slug",slug.getText().toString()); b.put("sku",sku.getText().toString()); b.put("subtitle",subtitle.getText().toString()); b.put("product_type",type.getText().toString()); b.put("price",price.getText().toString()); b.put("compare_at_price",compare.getText().toString().trim().isEmpty()?JSONObject.NULL:compare.getText().toString()); b.put("status",status.getText().toString()); b.put("visibility",visibility.getText().toString()); b.put("featured",featured.isChecked()); b.put("stock_count",Integer.parseInt(stock.getText().toString())); b.put("track_inventory",track.isChecked()); b.put("low_stock_threshold",Integer.parseInt(threshold.getText().toString())); b.put("badge",badge.getText().toString()); b.put("material",material.getText().toString()); b.put("care",care.getText().toString()); b.put("dimensions",dimensions.getText().toString()); b.put("shipping_note",shipping.getText().toString()); b.put("description",description.getText().toString()); b.put("description_template_id",template.getText().toString().trim().isEmpty()?JSONObject.NULL:Integer.parseInt(template.getText().toString())); b.put("tags",new JSONArray(tags.getText().toString())); b.put("category_ids",new JSONArray(categories.getText().toString())); b.put("images",new JSONArray(images.getText().toString())); b.put("variants",new JSONArray(variants.getText().toString())); b.put("meta",new JSONObject(meta.getText().toString())); b.put("seo_title",seoTitle.getText().toString()); b.put("seo_description",seoDescription.getText().toString()); if(id==0) api.post("/api/admin/products",b); else api.put("/api/admin/products/"+id,b); },()->loadProducts());
	}

	private void loadCategories(){ async(()->api.get("/api/admin/categories"), data->{ clearContent(); content.addView(button("＋ New category",v->categoryForm(null))); JSONArray rows=data.optJSONArray("categories"); if(rows==null)return; for(int i=0;i<rows.length();i++){JSONObject c=rows.optJSONObject(i);LinearLayout row=column(10);row.setBackgroundColor(Color.WHITE);row.addView(label(c.optString("name"),18));row.addView(label(c.optString("slug")+" · "+(c.optBoolean("visible")?"visible":"hidden"),13));row.addView(button("Edit",v->categoryForm(c)));content.addView(row);}}); }
	private void categoryForm(JSONObject c){clearContent();content.addView(label(c==null?"New category":"Edit category",23));EditText name=field(content,"Name",c==null?"":c.optString("name"));EditText slug=field(content,"Slug",c==null?"":c.optString("slug"));EditText desc=field(content,"Description",c==null?"":c.optString("description"));EditText image=field(content,"Image path",c==null?"":c.optString("image_path"));EditText pos=field(content,"Position",c==null?"0":String.valueOf(c.optInt("position")));CheckBox visible=check("Visible",c==null||c.optBoolean("visible",true));content.addView(visible);EditText seo=field(content,"SEO title",c==null?"":c.optString("seo_title"));EditText seod=field(content,"SEO description",c==null?"":c.optString("seo_description"));EditText meta=field(content,"Metadata JSON",c==null?"{}":c.optJSONObject("meta").toString());content.addView(button("Save category",v->asyncAction(()->{JSONObject b=new JSONObject();b.put("name",name.getText().toString());b.put("slug",slug.getText().toString());b.put("description",desc.getText().toString());b.put("image_path",image.getText().toString());b.put("position",Integer.parseInt(pos.getText().toString()));b.put("is_visible",visible.isChecked());b.put("seo_title",seo.getText().toString());b.put("seo_description",seod.getText().toString());b.put("meta",new JSONObject(meta.getText().toString()));if(c==null)api.post("/api/admin/categories",b);else api.put("/api/admin/categories/"+c.optInt("id"),b);},()->loadCategories())));if(c!=null)content.addView(button("Delete",v->asyncAction(()->api.delete("/api/admin/categories/"+c.optInt("id")),()->loadCategories())));}

	private void loadTemplates(){async(()->api.get("/api/admin/templates"),data->{clearContent();content.addView(button("＋ New template",v->templateForm(null)));JSONArray rows=data.optJSONArray("templates");if(rows==null)return;for(int i=0;i<rows.length();i++){JSONObject t=rows.optJSONObject(i);LinearLayout row=column(10);row.setBackgroundColor(Color.WHITE);row.addView(label(t.optString("name"),18));row.addView(label(t.optString("product_type"),13));row.addView(button("Edit",v->templateForm(t)));content.addView(row);}});}
	private void templateForm(JSONObject t){clearContent();content.addView(label(t==null?"New description template":"Edit description template",23));EditText name=field(content,"Name",t==null?"":t.optString("name"));EditText type=field(content,"Product type",t==null?"general":t.optString("product_type"));EditText body=field(content,"Markdown + Jinja body",t==null?"# {{ product.name }}\n\n{{ product.description }}\n\n**Material:** {{ product.material }}\n\n**SKU:** {{ product.sku }}\n":t.optString("body_markdown"));CheckBox active=check("Active",t==null||t.optBoolean("is_active",true));content.addView(active);content.addView(label("Template fields available under {{ product }} include name, subtitle, price, SKU, type, material, care, dimensions, shipping_note, tags and meta. Rendering is sandboxed and sanitized on the server.",13));content.addView(button("Save template",v->asyncAction(()->{JSONObject b=new JSONObject();b.put("name",name.getText().toString());b.put("product_type",type.getText().toString());b.put("body_markdown",body.getText().toString());b.put("is_active",active.isChecked());if(t==null)api.post("/api/admin/templates",b);else api.put("/api/admin/templates/"+t.optInt("id"),b);},()->loadTemplates())));if(t!=null)content.addView(button("Delete",v->asyncAction(()->api.delete("/api/admin/templates/"+t.optInt("id")),()->loadTemplates())));}

	private void loadOrders(){async(()->api.get("/api/admin/orders"),data->{clearContent();JSONArray rows=data.optJSONArray("orders");if(rows==null)return;for(int i=0;i<rows.length();i++){JSONObject o=rows.optJSONObject(i);LinearLayout row=column(10);row.setBackgroundColor(Color.WHITE);row.addView(label(o.optString("number"),19));row.addView(label("INR "+o.optString("total")+" · "+o.optString("status")+" · payment "+o.optString("payment_status"),13));row.addView(button("Mark processing",v->changeOrder(o.optInt("id"),"processing",null)));row.addView(button("Mark shipped",v->changeOrder(o.optInt("id"),"shipped",null)));row.addView(button("Mark delivered",v->changeOrder(o.optInt("id"),"delivered","paid")));row.addView(button("Cancel",v->changeOrder(o.optInt("id"),"cancelled",null)));row.addView(button("Mark paid",v->changeOrder(o.optInt("id"),null,"paid")));content.addView(row);}});}
	private void changeOrder(int id,String status,String payment){asyncAction(()->{if(status!=null)api.put("/api/admin/orders/"+id+"/status",new JSONObject().put("status",status));if(payment!=null)api.put("/api/admin/orders/"+id+"/payment",new JSONObject().put("status",payment));},()->loadOrders());}

	private void loadCoupons(){async(()->api.get("/api/admin/coupons"),data->{clearContent();content.addView(button("＋ New coupon",v->couponForm(null)));JSONArray rows=data.optJSONArray("coupons");if(rows==null)return;for(int i=0;i<rows.length();i++){JSONObject c=rows.optJSONObject(i);LinearLayout row=column(10);row.setBackgroundColor(Color.WHITE);row.addView(label(c.optString("code"),18));row.addView(label(c.optString("discount_type")+" "+c.optString("value")+" · used "+c.optInt("used"),13));row.addView(button("Edit",v->couponForm(c)));content.addView(row);}});}
	private void couponForm(JSONObject c){clearContent();content.addView(label(c==null?"New coupon":"Edit coupon",23));EditText code=field(content,"Code",c==null?"":c.optString("code"));EditText type=field(content,"Discount type (percent / fixed)",c==null?"percent":c.optString("discount_type"));EditText value=field(content,"Value",c==null?"0":c.optString("value"));EditText min=field(content,"Minimum order",c==null?"0":c.optString("minimum_order_value"));EditText max=field(content,"Maximum discount",c==null?"":c.optString("max_discount"));EditText limit=field(content,"Usage limit",c==null?"":String.valueOf(c.opt("usage_limit")));CheckBox active=check("Active",c==null||c.optBoolean("active",true));content.addView(active);content.addView(button("Save coupon",v->asyncAction(()->{JSONObject b=new JSONObject();b.put("code",code.getText().toString());b.put("discount_type",type.getText().toString());b.put("value",value.getText().toString());b.put("minimum_order_value",min.getText().toString());b.put("max_discount",max.getText().toString().trim().isEmpty()?JSONObject.NULL:max.getText().toString());b.put("usage_limit",limit.getText().toString().trim().isEmpty()?JSONObject.NULL:Integer.parseInt(limit.getText().toString()));b.put("active",active.isChecked());if(c==null)api.post("/api/admin/coupons",b);else api.put("/api/admin/coupons/"+c.optInt("id"),b);},()->loadCoupons())));if(c!=null)content.addView(button("Delete",v->asyncAction(()->api.delete("/api/admin/coupons/"+c.optInt("id")),()->loadCoupons())));}

	private void loadPages(){async(()->api.get("/api/admin/pages"),data->{clearContent();content.addView(button("＋ New page",v->pageForm(null)));JSONArray rows=data.optJSONArray("pages");if(rows==null)return;for(int i=0;i<rows.length();i++){JSONObject p=rows.optJSONObject(i);LinearLayout row=column(10);row.setBackgroundColor(Color.WHITE);row.addView(label(p.optString("title"),18));row.addView(label("/pages/"+p.optString("slug"),13));row.addView(button("Edit",v->pageForm(p)));content.addView(row);}});}
	private void pageForm(JSONObject p){clearContent();content.addView(label(p==null?"New content page":"Edit content page",23));EditText slug=field(content,"Slug",p==null?"":p.optString("slug"));EditText title=field(content,"Title",p==null?"":p.optString("title"));EditText body=field(content,"Markdown",p==null?"":p.optString("body_markdown"));CheckBox active=check("Active",p==null||p.optBoolean("active",true));content.addView(active);EditText meta=field(content,"Metadata JSON",p==null?"{}":p.optJSONObject("meta").toString());content.addView(button("Save page",v->asyncAction(()->{JSONObject b=new JSONObject();b.put("slug",slug.getText().toString());b.put("title",title.getText().toString());b.put("body_markdown",body.getText().toString());b.put("active",active.isChecked());b.put("meta",new JSONObject(meta.getText().toString()));if(p==null)api.post("/api/admin/pages",b);else api.put("/api/admin/pages/"+p.optInt("id"),b);},()->loadPages())));if(p!=null)content.addView(button("Delete",v->asyncAction(()->api.delete("/api/admin/pages/"+p.optInt("id")),()->loadPages())));}

	private void loadSite(){async(()->api.get("/api/admin/site"),data->{clearContent();content.addView(label("Store settings",23));content.addView(label("Common controls are easy to edit; structured data still has an advanced JSON escape hatch when you need something unusual.",13));content.addView(button("Edit theme / colors",v->themeForm(data.optJSONObject("theme"))));String[] simple={"site","announcement","navigation","footer","homepage","seo","store","social","checkout"};for(String key:simple){Object value=data.opt(key);EditText e=field(content,key,value==null?"{}":value.toString());content.addView(button("Save "+key,v->asyncAction(()->api.put("/api/admin/site",new JSONObject().put("key",key).put("value",parseJsonValue(e.getText().toString()))),this::loadSite)));}});}
	private void themeForm(JSONObject theme){if(theme==null)theme=new JSONObject();clearContent();content.addView(label("Theme / colors",23));content.addView(label("The storefront deliberately uses a small visual system. These values are applied server-side to every SSR page.",13));EditText background=field(content,"Background",theme.optString("background","#f7f7f5"));EditText surface=field(content,"Surface",theme.optString("surface","#ffffff"));EditText text=field(content,"Text",theme.optString("text","#0a0a0a"));EditText muted=field(content,"Muted text",theme.optString("muted","#686868"));EditText border=field(content,"Border",theme.optString("border","#d8d8d3"));EditText accent=field(content,"Accent",theme.optString("accent","#0a0a0a"));EditText accentText=field(content,"Accent text",theme.optString("accent_text","#ffffff"));EditText radius=field(content,"Corner radius (px)",String.valueOf(theme.optInt("radius",0)));EditText max=field(content,"Max content width (px)",String.valueOf(theme.optInt("max_width",1320)));content.addView(button("Save theme",v->asyncAction(()->{JSONObject value=new JSONObject();value.put("background",background.getText().toString().trim());value.put("surface",surface.getText().toString().trim());value.put("text",text.getText().toString().trim());value.put("muted",muted.getText().toString().trim());value.put("border",border.getText().toString().trim());value.put("accent",accent.getText().toString().trim());value.put("accent_text",accentText.getText().toString().trim());value.put("radius",Integer.parseInt(radius.getText().toString()));value.put("max_width",Integer.parseInt(max.getText().toString()));return api.put("/api/admin/site",new JSONObject().put("key","theme").put("value",value));},this::loadSite)));content.addView(label("Advanced theme JSON",13));EditText advanced=field(content,"Full theme object",theme.toString());content.addView(button("Save advanced theme JSON",v->asyncAction(()->api.put("/api/admin/site",new JSONObject().put("key","theme").put("value",new JSONObject(advanced.getText().toString()))),this::loadSite)));content.addView(button("Back to site settings",v->loadSite()));}
	private Object parseJsonValue(String raw)throws JSONException{String s=raw.trim();if(s.startsWith("{"))return new JSONObject(s);if(s.startsWith("["))return new JSONArray(s);if("true".equalsIgnoreCase(s)||"false".equalsIgnoreCase(s))return Boolean.parseBoolean(s);return s;}

	private void loadUsers(){async(()->api.get("/api/admin/users"),data->{clearContent();JSONArray rows=data.optJSONArray("users");if(rows==null)return;for(int i=0;i<rows.length();i++){JSONObject u=rows.optJSONObject(i);LinearLayout row=column(10);row.setBackgroundColor(Color.WHITE);row.addView(label(u.optString("name",u.optString("email")),18));row.addView(label(u.optString("email"),13));row.addView(button(u.optBoolean("is_active")?"Deactivate":"Activate",v->toggleUser(u.optInt("id"),!u.optBoolean("is_active"),u.optBoolean("is_admin"))));row.addView(button(u.optBoolean("is_admin")?"Remove admin":"Make admin",v->toggleUser(u.optInt("id"),u.optBoolean("is_active"),!u.optBoolean("is_admin"))));content.addView(row);}});}
	private void toggleUser(int id,boolean active,boolean admin){asyncAction(()->api.put("/api/admin/users/"+id,new JSONObject().put("is_active",active).put("is_admin",admin)),()->loadUsers());}

	private void loadMedia(){async(()->api.get("/api/admin/media"),data->{clearContent();content.addView(button("＋ Upload media",v->pickFile()));JSONArray rows=data.optJSONArray("media");if(rows==null)return;for(int i=0;i<rows.length();i++){JSONObject m=rows.optJSONObject(i);LinearLayout row=column(8);row.setBackgroundColor(Color.WHITE);row.addView(label(m.optString("filename"),17));row.addView(label(m.optString("path")+" · "+m.optString("mime_type")+" · "+m.optInt("size_bytes")+" bytes",12));content.addView(row);}});}
	private void pickFile(){startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE),42);}
	@Override protected void onActivityResult(int requestCode,int resultCode,Intent data){super.onActivityResult(requestCode,resultCode,data);if(requestCode!=42||resultCode!=RESULT_OK||data==null)return;Uri uri=data.getData();executor.execute(()->{try(InputStream in=getContentResolver().openInputStream(uri)){byte[] bytes=readAll(in);String name=queryName(uri);String mime=getContentResolver().getType(uri);api.upload("/api/admin/media",bytes,name,mime,"");runOnUi(()->loadMedia());}catch(Exception e){runOnUi(()->Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show());}});}
	private byte[] readAll(InputStream in)throws Exception{java.io.ByteArrayOutputStream out=new java.io.ByteArrayOutputStream();byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1)out.write(b,0,n);return out.toByteArray();}
	private String queryName(Uri uri){String name="upload.bin";try(android.database.Cursor c=getContentResolver().query(uri,new String[]{OpenableColumns.DISPLAY_NAME},null,null,null)){if(c!=null&&c.moveToFirst())name=c.getString(0);}catch(Exception ignored){}return name;}

	private void async(java.util.concurrent.Callable<JSONObject> call, java.util.function.Consumer<JSONObject> success){busy(true);executor.execute(()->{try{JSONObject data=call.call();runOnUi(()->success.accept(data));}catch(Exception e){runOnUi(()->Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show());}});}
	private void asyncAction(java.util.concurrent.Callable<JSONObject> call,Runnable success){busy(true);executor.execute(()->{try{call.call();runOnUi(success);}catch(Exception e){runOnUi(()->Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show());}});}
	private void runOnUi(Runnable r){runOnUiThread(r);}
	private void loadAudit(){async(()->api.get("/api/admin/audit"), data->{clearContent();content.addView(label("Recent admin activity",23));content.addView(label("The server records changes so you can see what was edited without digging through the database.",13));JSONArray rows=data.optJSONArray("audit");if(rows==null)return;for(int i=0;i<rows.length();i++){JSONObject a=rows.optJSONObject(i);LinearLayout row=column(10);row.setBackgroundColor(Color.WHITE);row.addView(label(a.optString("action"),17));row.addView(label(a.optString("entity_type")+" #"+a.optString("entity_id")+" · "+a.optString("created_at"),12));row.addView(label(a.optJSONObject("details")==null?"":a.optJSONObject("details").toString(),12));content.addView(row);}});}

	private void logout(){executor.execute(()->{try{api.post("/api/admin/logout",null);}catch(Exception ignored){}prefs.edit().remove("token").apply();runOnUi(this::showLogin);});}
}
