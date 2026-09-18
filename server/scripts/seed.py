import asyncio
from decimal import Decimal
import os

from sqlalchemy import select

from app.core.site import set_site
from app.db.models import Category, ContentPage, DescriptionTemplate, Product, ProductCategory, ProductImage
from app.db.session import SessionLocal, init_db
from app.core.site_defaults import DEFAULT_SITE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(ROOT, "data", "media")

PRODUCTS = [
	("The Visionary", "the-visionary", "VISIONARY", "Graphic tee", "19.90", "the_visionary-1.jpg"),
	("The Reptilian", "the-reptilian", "REPTILIAN", "Graphic tee", "19.90", "the_reptilian-1.png"),
	("Forever Young", "forever-young", "FOREVER", "Graphic tee", "19.90", "forever_young-1.png"),
	("Heartless", "heartless", "HEARTLESS", "Graphic tee", "19.90", "heartless-1.jpg"),
	("Motion Sickness", "motion-sickness", "MOTION", "Graphic tee", "19.90", "motion_sickness-1.jpg"),
	("Berserk", "berserk", "BERSERK", "Graphic tee", "19.90", "berserk-1.png"),
	("Celestial", "celestial", "CELESTIAL", "Graphic tee", "19.90", "celestial-1.png"),
	("Tomorrow Is Not Promised", "tomorrow-is-not-promised", "TOMORROW", "Statement tee", "21.90", "tomorrow_is_not_promised-1.jpg"),
	("I'm Vengeance", "im-vengeance", "VENGEANCE", "Statement tee", "21.90", "im_vengeance-1.png"),
	("The Edge", "the-edge", "EDGE", "Statement tee", "21.90", "the_edge-1.jpg"),
	("Rebel", "rebel", "REBEL", "Graphic tee", "19.90", "rebel-1.png"),
	("Punisher", "punisher", "PUNISHER", "Graphic tee", "19.90", "punisher-1.png"),
	("The Devil Makes Three", "the-devil-makes-three", "DEVIL", "Graphic tee", "19.90", "the_devil_makes_three-1.png"),
	("Syncronization", "syncronization", "SYNC", "Graphic tee", "19.90", "syncronization-1.png"),
	("Hell Is Empty", "hell-is-empty", "HELL", "Statement tee", "21.90", "hell_is_empty-1.png"),
	("Tiger Fury", "tiger-fury", "TIGER", "Graphic tee", "19.90", "tiger_fury-1.png"),
	("Nirvana In Utero", "nirvana-in-utero", "NIRVANA", "Graphic tee", "19.90", "nirvana_in_utero-1.png"),
	("See You In The Sun", "see-you-in-the-sun", "SUN", "Graphic tee", "19.90", "see_you_in_the_sun-1.png"),
]


def page_content(slug: str, title: str, body: str):
	return {"slug": slug, "title": title, "body_markdown": body, "active": True, "meta": {}}


async def seed():
	await init_db()
	async with SessionLocal() as db:
		category_rows = {
			"graphic-tees": "Graphic Tees",
			"statement": "Statement Pieces",
		}
		categories = {}
		for slug, name in category_rows.items():
			row = (await db.execute(select(Category).where(Category.slug == slug))).scalar_one_or_none()
			if not row:
				row = Category(name=name, slug=slug, description="Pieces grouped by visual language and intent.", position=len(categories))
				db.add(row)
				await db.flush()
			categories[slug] = row

		templates = {}
		for name, product_type, body in [
			("Graphic tee", "Graphic tee", "# {{ product.name }}\n\n{{ product.subtitle }}\n\n{{ product.description }}\n\n**Material:** {{ product.material or 'Cotton' }}\n\n**Care:** {{ product.care or 'Wash according to garment label.' }}\n"),
			("Statement piece", "Statement tee", "# {{ product.name }}\n\n> {{ product.subtitle }}\n\n{{ product.description }}\n\n**Designed for:** {{ product.product_type }}\n\n**SKU:** {{ product.sku }}\n"),
		]:
			row = (await db.execute(select(DescriptionTemplate).where(DescriptionTemplate.name == name))).scalar_one_or_none()
			if not row:
				row = DescriptionTemplate(name=name, product_type=product_type, body_markdown=body)
				db.add(row)
				await db.flush()
			templates[product_type] = row

		for index, (name, slug, sku, product_type, price, image) in enumerate(PRODUCTS):
			row = (await db.execute(select(Product).where(Product.slug == slug))).scalar_one_or_none()
			if not row:
				row = Product(
					name=name, slug=slug, sku=sku, subtitle=f"A {product_type.lower()} built around a symbol.",
					description="Designed as a visual statement rather than decoration.",
					description_template_id=templates[product_type if product_type in templates else "Graphic tee"].id,
					product_type=product_type, price=Decimal(price), status="active", visibility="public",
					featured=index < 6, position=index, stock_count=12, track_inventory=True,
					badge="Selected" if index < 3 else "", material="100% cotton",
					care="Machine wash cold. Follow garment label.", shipping_note="Ships from India.",
				)
				db.add(row)
				await db.flush()
				db.add(ProductImage(product_id=row.id, path=f"/media/{image}", alt_text=name, position=0, is_primary=True))
				cat = categories["statement" if product_type == "Statement tee" else "graphic-tees"]
				db.add(ProductCategory(product_id=row.id, category_id=cat.id))

		for slug, title, body in [
			("the-company", "The Company", "# MAN AND HIS SYMBOLS\n\nHuman beings have always communicated through symbols. The clothes we choose are part of that language.\n\nAt **VELANG**, graphics are conceived as symbols rather than filler: purpose, discipline, identity, resilience, ambition and self-mastery.\n\nMeaning comes before spectacle.\n"),
			("terms", "Terms of Service", "# Terms of Service\n\nThese demo terms should be replaced with your actual legal copy before launch.\n"),
			("return-policy", "Return Policy", "# Return Policy\n\nSet your actual return windows, exclusions and process here. This content is editable from the admin app.\n"),
			("privacy", "Privacy Policy", "# Privacy Policy\n\nSet your actual privacy policy here. This content is editable from the admin app.\n"),
			("support", "Support", "# Support\n\nAdd your support email, hours, shipping help and common questions here.\n"),
		]:
			row = (await db.execute(select(ContentPage).where(ContentPage.slug == slug))).scalar_one_or_none()
			if not row:
				db.add(ContentPage(**page_content(slug, title, body)))

		for key, value in DEFAULT_SITE.items():
			await set_site(db, key, value)
		await db.commit()
		print(f"Seeded {len(PRODUCTS)} demo products, 2 categories, templates, pages and site defaults.")


if __name__ == "__main__":
	asyncio.run(seed())
