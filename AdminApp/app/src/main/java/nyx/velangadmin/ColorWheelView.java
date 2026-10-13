package nyx.velangadmin;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.view.MotionEvent;
import android.view.View;

/**
 * Small dependency-free hue/saturation wheel for editing storefront theme
 * colors.
 */
public final class ColorWheelView extends View {
	private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
	private Bitmap wheel;
	private final float[] hsv = new float[] { 0f, 1f, 1f };
	private float brightness = 1f;
	private float radius;
	private float centerX;
	private float centerY;
	private int color = Color.BLACK;
	private java.util.function.IntConsumer listener;

	public ColorWheelView(Context context, int initialColor, java.util.function.IntConsumer onColorChanged) {
		super(context);
		listener = onColorChanged;
		Color.colorToHSV(initialColor, hsv);
		brightness = hsv[2];
		color = initialColor;
		setLayerType(View.LAYER_TYPE_SOFTWARE, null);
	}

	public int getSelectedColor() {
		return Color.HSVToColor(new float[] { hsv[0], hsv[1], brightness });
	}

	public void setBrightness(float value) {
		brightness = Math.max(0f, Math.min(1f, value));
		color = getSelectedColor();
		if (wheel != null)
			renderWheel(wheel.getWidth());
		invalidate();
		if (listener != null)
			listener.accept(color);
	}

	@Override
	protected void onSizeChanged(int width, int height, int oldWidth, int oldHeight) {
		super.onSizeChanged(width, height, oldWidth, oldHeight);
		int size = Math.max(1, Math.min(width, height));
		centerX = width / 2f;
		centerY = height / 2f;
		radius = size / 2f - 2f;
		if (wheel != null && !wheel.isRecycled())
			wheel.recycle();
		wheel = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888);
		renderWheel(size);
	}

	private void renderWheel(int size) {
		int[] pixels = new int[size * size];
		float wheelRadius = size / 2f - 2f;
		for (int y = 0; y < size; y++) {
			for (int x = 0; x < size; x++) {
				float dx = x + .5f - size / 2f;
				float dy = y + .5f - size / 2f;
				float distance = (float) Math.sqrt(dx * dx + dy * dy);
				if (distance > wheelRadius) {
					pixels[y * size + x] = Color.TRANSPARENT;
				} else {
					float hue = (float) ((Math.toDegrees(Math.atan2(dy, dx)) + 360d) % 360d);
					float saturation = Math.min(1f, distance / wheelRadius);
					pixels[y * size + x] = Color.HSVToColor(new float[] { hue, saturation, brightness });
				}
			}
		}
		wheel.setPixels(pixels, 0, size, 0, 0, size, size);
	}

	@Override
	protected void onDraw(Canvas canvas) {
		super.onDraw(canvas);
		if (wheel == null)
			return;
		float size = wheel.getWidth();
		float left = (getWidth() - size) / 2f;
		float top = (getHeight() - size) / 2f;
		canvas.drawBitmap(wheel, left, top, paint);
		float angle = (float) Math.toRadians(hsv[0]);
		float markerX = centerX + (float) Math.cos(angle) * hsv[1] * radius;
		float markerY = centerY + (float) Math.sin(angle) * hsv[1] * radius;
		paint.setStyle(Paint.Style.STROKE);
		paint.setStrokeWidth(Math.max(2f, getResources().getDisplayMetrics().density * 2f));
		paint.setColor(Color.WHITE);
		canvas.drawCircle(markerX, markerY, 8f * getResources().getDisplayMetrics().density, paint);
		paint.setStrokeWidth(Math.max(1f, getResources().getDisplayMetrics().density));
		paint.setColor(Color.BLACK);
		canvas.drawCircle(markerX, markerY, 10f * getResources().getDisplayMetrics().density, paint);
		paint.setStyle(Paint.Style.FILL);
	}

	@Override
	public boolean onTouchEvent(MotionEvent event) {
		if (event.getAction() != MotionEvent.ACTION_DOWN && event.getAction() != MotionEvent.ACTION_MOVE)
			return true;
		float dx = event.getX() - centerX;
		float dy = event.getY() - centerY;
		float distance = (float) Math.sqrt(dx * dx + dy * dy);
		if (distance > radius) {
			dx *= radius / distance;
			dy *= radius / distance;
			distance = radius;
		}
		hsv[0] = (float) ((Math.toDegrees(Math.atan2(dy, dx)) + 360d) % 360d);
		hsv[1] = radius == 0 ? 0 : Math.min(1f, distance / radius);
		color = getSelectedColor();
		invalidate();
		if (listener != null)
			listener.accept(color);
		return true;
	}
}
