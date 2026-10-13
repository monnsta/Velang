package nyx.velangadmin;

import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.regex.Pattern;
import nyx.velangadmin.core.AdminCoreActivity;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/** Structured editor for dynamic product fields in a description template. */
public final class TemplateFieldsEditor {
	private static final Pattern KEY_PATTERN = Pattern.compile("[A-Za-z][A-Za-z0-9_]{0,63}");
	private static final String[] FIELD_TYPES = {"Short text", "Long text", "Choose from options"};
	private static final String[] TYPE_VALUES = {"text", "textarea", "select"};
	private static final String NO_DEFAULT = "No default";

	public final LinearLayout container;

	private final AdminCoreActivity host;
	private final LinearLayout rowsContainer;
	private final ArrayList<FieldRow> rows = new ArrayList<>();

	public TemplateFieldsEditor(AdminCoreActivity host, JSONArray initial) {
		this.host = host;
		container = host.column(0);
		container.addView(host.label("Product fields", 17));
		container.addView(host.label(
				"Define values for each product. Use {{ product.fields.key }} in the template body. Empty optional values can be omitted from their line automatically.",
				12));
		rowsContainer = host.column(0);
		container.addView(rowsContainer);
		container.addView(host.button("Add field", v -> addRow("", "", "", "", "text", new JSONArray(), false, false)));

		if (initial != null) {
			for (int i = 0; i < initial.length(); i++) {
				JSONObject field = initial.optJSONObject(i);
				if (field == null)
					continue;
				JSONArray choices = field.optJSONArray("choices");
				addRow(
						field.optString("key", ""),
						field.optString("label", ""),
						field.optString("placeholder", ""),
						field.optString("default", ""),
						field.optString("type", "text"),
						choices == null ? new JSONArray() : choices,
						field.optBoolean("markdown"),
						field.optBoolean("required"));
			}
		}
		refreshTitles();
	}

	private void addRow(
			String keyValue,
			String labelValue,
			String placeholderValue,
			String defaultValue,
			String typeValue,
			JSONArray initialChoices,
			boolean markdownValue,
			boolean requiredValue) {
		LinearLayout card = host.column(12);
		card.setBackground(host.outline(host.surfaceColor(), host.borderColor()));
		LinearLayout heading = new LinearLayout(host);
		heading.setOrientation(LinearLayout.HORIZONTAL);
		heading.setGravity(Gravity.CENTER_VERTICAL);
		TextView title = host.label("Field " + (rows.size() + 1), 14);
		title.setTypeface(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD);
		heading.addView(title, new LinearLayout.LayoutParams(0, -2, 1));
		card.addView(heading);

		EditText key = addTextInput(card, "Template key", "e.g. fabric", keyValue, false);
		EditText fieldLabel = addTextInput(card, "Field label", "e.g. Fabric", labelValue, false);
		EditText placeholder = addTextInput(card, "Placeholder", "Optional guidance for the product editor", placeholderValue, false);

		card.addView(host.label("Input control", 12));
		Spinner type = new Spinner(host);
		ArrayAdapter<String> typeAdapter = new ArrayAdapter<>(host, android.R.layout.simple_spinner_item, FIELD_TYPES);
		typeAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
		type.setAdapter(typeAdapter);
		type.setSelection(typeIndex(typeValue));
		card.addView(type);

		LinearLayout textDefaultGroup = host.column(0);
		textDefaultGroup.addView(host.label("Default value", 12));
		EditText defaultInput = host.input("Used unless a product overrides it", defaultValue);
		textDefaultGroup.addView(defaultInput);
		card.addView(textDefaultGroup);

		LinearLayout choiceDefaultGroup = host.column(0);
		choiceDefaultGroup.addView(host.label("Default option", 12));
		Spinner defaultChoice = new Spinner(host);
		choiceDefaultGroup.addView(defaultChoice);
		card.addView(choiceDefaultGroup);

		EditText choicesInput = addTextInput(
				card, "Available choices · one per line", "100% cotton\n50% cotton / 50% linen", choicesToText(initialChoices), true);
		choicesInput.setMinLines(3);
		choicesInput.setMaxLines(8);
		choicesInput.setGravity(Gravity.TOP | Gravity.START);

		CheckBox markdown = checkbox("Render Markdown in this value", markdownValue);
		CheckBox required = checkbox("Require a value before saving", requiredValue);
		card.addView(markdown);
		card.addView(required);

		FieldRow row = new FieldRow(
				card, title, key, fieldLabel, placeholder, defaultInput, textDefaultGroup,
				defaultChoice, choiceDefaultGroup, type, choicesInput, markdown, required);
		rows.add(row);
		refreshDefaultChoices(row, defaultValue);
		updateTypePresentation(row);
		heading.addView(host.iconButton(R.drawable.ic_delete, "Remove field", v -> {
			rowsContainer.removeView(card);
			rows.remove(row);
			refreshTitles();
		}), new LinearLayout.LayoutParams(host.dp(44), host.dp(44)));
		rowsContainer.addView(card);

		TextWatcher titleWatcher = new TextWatcher() {
			@Override
			public void beforeTextChanged(CharSequence s, int start, int count, int after) {
			}

			@Override
			public void onTextChanged(CharSequence s, int start, int before, int count) {
				refreshTitles();
			}

			@Override
			public void afterTextChanged(Editable s) {
			}
		};
		key.addTextChangedListener(titleWatcher);
		fieldLabel.addTextChangedListener(titleWatcher);
		choicesInput.addTextChangedListener(new TextWatcher() {
			@Override
			public void beforeTextChanged(CharSequence s, int start, int count, int after) {
			}

			@Override
			public void onTextChanged(CharSequence s, int start, int before, int count) {
				refreshDefaultChoices(row, selectedDefault(row.defaultChoice));
			}

			@Override
			public void afterTextChanged(Editable s) {
			}
		});
		type.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener() {
			@Override
			public void onItemSelected(android.widget.AdapterView<?> parent, View view, int position, long id) {
				updateTypePresentation(row);
			}

			@Override
			public void onNothingSelected(android.widget.AdapterView<?> parent) {
			}
		});
		markdown.setOnCheckedChangeListener((button, checked) -> {
			if (checked && "select".equals(typeValueAt(type.getSelectedItemPosition())))
				markdown.setChecked(false);
		});
	}

	private EditText addTextInput(LinearLayout parent, String label, String hint, String value, boolean multiline) {
		parent.addView(host.label(label, 12));
		EditText input = host.input(hint, value);
		input.setHint(hint);
		input.setSingleLine(!multiline);
		if (multiline) {
			input.setMinLines(3);
			input.setMaxLines(8);
			input.setGravity(Gravity.TOP | Gravity.START);
		}
		parent.addView(input);
		return input;
	}

	private CheckBox checkbox(String text, boolean value) {
		CheckBox box = new CheckBox(host);
		box.setText(text);
		box.setTextColor(host.foregroundColor());
		box.setChecked(value);
		return box;
	}

	private int typeIndex(String type) {
		for (int i = 0; i < TYPE_VALUES.length; i++)
			if (TYPE_VALUES[i].equalsIgnoreCase(type))
				return i;
		return 0;
	}

	private String typeValueAt(int position) {
		return TYPE_VALUES[Math.max(0, Math.min(position, TYPE_VALUES.length - 1))];
	}

	private String choicesToText(JSONArray choices) {
		if (choices == null || choices.length() == 0)
			return "";
		StringBuilder text = new StringBuilder();
		for (int i = 0; i < choices.length(); i++) {
			String choice = choices.optString(i, "").trim();
			if (choice.isEmpty())
				continue;
			if (text.length() > 0)
				text.append('\n');
			text.append(choice);
		}
		return text.toString();
	}

	private ArrayList<String> parsedChoices(String source) {
		ArrayList<String> choices = new ArrayList<>();
		for (String line : (source == null ? "" : source).split("\\r?\\n")) {
			String choice = line.trim();
			if (!choice.isEmpty() && !choices.contains(choice))
				choices.add(choice);
		}
		return choices;
	}

	private String selectedDefault(Spinner spinner) {
		Object selected = spinner.getSelectedItem();
		return selected == null || NO_DEFAULT.equals(selected.toString()) ? "" : selected.toString();
	}

	private void refreshDefaultChoices(FieldRow row, String preferredValue) {
		ArrayList<String> options = parsedChoices(row.choices.getText().toString());
		ArrayList<String> labels = new ArrayList<>();
		labels.add(NO_DEFAULT);
		labels.addAll(options);
		ArrayAdapter<String> adapter = new ArrayAdapter<>(host, android.R.layout.simple_spinner_item, labels);
		adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
		row.defaultChoice.setAdapter(adapter);
		int position = preferredValue == null || preferredValue.isEmpty() ? 0 : labels.indexOf(preferredValue);
		row.defaultChoice.setSelection(position < 0 ? 0 : position);
	}

	private void updateTypePresentation(FieldRow row) {
		boolean select = "select".equals(typeValueAt(row.type.getSelectedItemPosition()));
		row.choices.setVisibility(select ? View.VISIBLE : View.GONE);
		row.choiceDefaultGroup.setVisibility(select ? View.VISIBLE : View.GONE);
		row.textDefaultGroup.setVisibility(select ? View.GONE : View.VISIBLE);
		row.markdown.setEnabled(!select);
		if (select && row.markdown.isChecked())
			row.markdown.setChecked(false);
	}

	private void refreshTitles() {
		for (int i = 0; i < rows.size(); i++) {
			FieldRow row = rows.get(i);
			String label = row.fieldLabel.getText().toString().trim();
			String key = row.key.getText().toString().trim();
			row.title.setText("Field " + (i + 1) + (label.isEmpty() ? "" : " · " + label)
					+ (key.isEmpty() ? "" : "  {{ product.fields." + key + " }}"));
		}
	}

	public JSONArray valuesForSave() {
		JSONArray result = new JSONArray();
		Set<String> seen = new HashSet<>();
		for (FieldRow row : rows) {
			String key = row.key.getText().toString().trim();
			String label = row.fieldLabel.getText().toString().trim();
			String placeholder = row.placeholder.getText().toString().trim();
			String type = typeValueAt(row.type.getSelectedItemPosition());
			String defaultValue = "select".equals(type)
					? selectedDefault(row.defaultChoice)
					: row.defaultValue.getText().toString();
			boolean hasOptions = !placeholder.isEmpty() || !defaultValue.isEmpty()
					|| row.markdown.isChecked() || row.required.isChecked() || "select".equals(type)
					|| !key.isEmpty() || !label.isEmpty();
			if (!hasOptions)
				continue;
			if (!KEY_PATTERN.matcher(key).matches())
				throw new IllegalArgumentException("Field keys must start with a letter and contain only letters, numbers, or underscores.");
			if (label.isEmpty() || label.length() > 120)
				throw new IllegalArgumentException("Every field needs a label of 1–120 characters.");
			if (!seen.add(key))
				throw new IllegalArgumentException("Duplicate template field key: " + key);
			if (placeholder.length() > 160)
				throw new IllegalArgumentException("Field placeholders must be 160 characters or fewer.");
			if (defaultValue.length() > 1000)
				throw new IllegalArgumentException("Default values must be 1000 characters or fewer.");

			JSONArray choices = new JSONArray();
			Set<String> uniqueChoices = new LinkedHashSet<>();
			if ("select".equals(type)) {
				for (String choice : parsedChoices(row.choices.getText().toString())) {
					if (choice.length() > 120)
						throw new IllegalArgumentException("Choices must be 120 characters or fewer.");
					uniqueChoices.add(choice);
				}
				if (uniqueChoices.isEmpty())
					throw new IllegalArgumentException("Add at least one choice for " + label + ".");
				if (uniqueChoices.size() > 50)
					throw new IllegalArgumentException("A field can have at most 50 choices.");
				for (String choice : uniqueChoices)
					choices.put(choice);
				if (!defaultValue.isEmpty() && !uniqueChoices.contains(defaultValue))
					throw new IllegalArgumentException("The default for " + label + " must match one of its choices.");
			}
			try {
				result.put(new JSONObject()
						.put("key", key)
						.put("label", label)
						.put("placeholder", placeholder)
						.put("default", defaultValue)
						.put("type", type)
						.put("choices", choices)
						.put("markdown", row.markdown.isChecked() && !"select".equals(type))
						.put("required", row.required.isChecked()));
			} catch (JSONException error) {
				throw new IllegalArgumentException("Could not read template fields.", error);
			}
		}
		if (result.length() > 40)
			throw new IllegalArgumentException("A template can define at most 40 fields.");
		return result;
	}

	private static final class FieldRow {
		final LinearLayout card;
		final TextView title;
		final EditText key;
		final EditText fieldLabel;
		final EditText placeholder;
		final EditText defaultValue;
		final LinearLayout textDefaultGroup;
		final Spinner defaultChoice;
		final LinearLayout choiceDefaultGroup;
		final Spinner type;
		final EditText choices;
		final CheckBox markdown;
		final CheckBox required;

		FieldRow(LinearLayout card, TextView title, EditText key, EditText fieldLabel,
				EditText placeholder, EditText defaultValue, LinearLayout textDefaultGroup,
				Spinner defaultChoice, LinearLayout choiceDefaultGroup, Spinner type, EditText choices,
				CheckBox markdown, CheckBox required) {
			this.card = card;
			this.title = title;
			this.key = key;
			this.fieldLabel = fieldLabel;
			this.placeholder = placeholder;
			this.defaultValue = defaultValue;
			this.textDefaultGroup = textDefaultGroup;
			this.defaultChoice = defaultChoice;
			this.choiceDefaultGroup = choiceDefaultGroup;
			this.type = type;
			this.choices = choices;
			this.markdown = markdown;
			this.required = required;
		}
	}
}
