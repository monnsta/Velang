import asyncio
import os
from decimal import Decimal

from app.core.site import set_site
from app.core.site_defaults import DEFAULT_SITE
from app.db.models import (
	Category,
	DescriptionTemplate,
	Product,
	ProductCategory,
	ProductImage,
)
from app.db.session import SessionLocal, init_db
from sqlalchemy import select

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(ROOT, "data", "media")

# The curated catalogue lives in this seed file so a deployment does not depend on
# a separate temporary import JSON. Prices in source data are paise; convert to INR.
PRODUCT_SOURCE = [
	{
		"id": "001Xa2bwyL",
		"name": "GEOMETRIC BAND PRINT T-SHIRT",
		"price": 88000,
		"visible": True,
		"available": True,
		"description": "THE LANGUAGE OF PATTERN\n"
		"\n"
		"The Geometric Band Print T-Shirt features a refined geometric composition across "
		"a deep black cotton silhouette. A continuous ornamental band runs horizontally "
		"across the chest, framed by a field of subtle diamond motifs that gives the "
		"design a measured, architectural character.\n"
		"\n"
		"DETAILS\n"
		"\n"
		"Fabric: 100% Premium Cotton\n"
		"Colour: Black\n"
		"Fit: Classic Relaxed Fit\n"
		"Neckline: Ribbed Crew Neck\n"
		"Print: Geometric ornamental band with diamond motifs\n"
		"Print Colour: Deep Brown\n"
		"Placement: Front chest\n"
		"\n"
		"“One should either be a work of art, or wear a work of art.”",
		"sizes": [],
		"reviews": [],
		"searchTags": ["geometric", "motif", "band", "black", "brown"],
		"images": ["geometric_band/1.png", "geometric_band/2.webp"],
	},
	{
		"id": "001X7ADcQO",
		"name": "THE FLIGHT",
		"price": 85500,
		"visible": True,
		"available": True,
		"description": "A Study in Motion\n"
		"\n"
		"The Flight introduces a delicate arrangement of flying birds across a clean "
		"white cotton silhouette, creating a sense of movement through finely rendered "
		"imagery and carefully spaced placement. Each bird carries its own position and "
		"direction, giving the composition a natural rhythm across the chest.\n"
		"\n"
		"The restrained artwork allows the purity of the garment to remain central, with "
		"the subtle tones of the birds providing a measured contrast against the white "
		"ground. Finished with a classic relaxed silhouette and substantial cotton "
		"construction, the piece brings an understated character to a considered "
		"wardrobe.\n"
		"\n"
		"Construction\n"
		"Made from 100% premium cotton, selected for its substantial hand-feel, natural "
		"breathability and clean structure. The garment is cut in a classic relaxed "
		"silhouette with a ribbed crew neckline, proportioned sleeves and refined "
		"finishing throughout.\n"
		"\n"
		"DETAILS\n"
		"Fabric: 100% Premium Cotton\n"
		"\n"
		"Colour: White\n"
		"\n"
		"Fit: Classic Relaxed Fit\n"
		"\n"
		"Neckline: Ribbed Crew Neck\n"
		"\n"
		"Sleeves: Short Sleeves\n"
		"\n"
		"Artwork: Flying bird illustration\n"
		"\n"
		"Placement: Front chest\n"
		"\n"
		'"No bird soars too high if he soars with his own wings." — William Blake',
		"sizes": [],
		"reviews": [],
		"searchTags": [],
		"images": ["theflight/1.png", "theflight/2.webp"],
	},
	{
		"id": "001X3xN8iZ",
		"name": "Nuit Étoilée",
		"price": 20000000,
		"visible": True,
		"available": True,
		"description": "A Study In Light\n"
		"\n"
		"Velang Nuit Étoilée introduces a celestial character through a field of diamonds "
		"scattered across pure black cotton, each stone placed individually to evoke the "
		"irregular brilliance of a night sky. Moissonite diamonds ranging from 1 to 5 mm "
		"create a natural constellation, with brighter stones appearing sporadically "
		"across the surface.\n"
		"\n"
		"The composition is deliberately restrained, allowing the contrast between deep "
		"black cotton and reflected light to define the garment. Cut in a classic relaxed "
		"silhouette, the T-shirt brings together the ease of fine cotton with the "
		"presence of fine jewellery.\n"
		"\n"
		"DETAILS\n"
		"\n"
		"FABRIC: 100% Cotton\n"
		"\n"
		"COLOUR: Deep Black\n"
		"\n"
		"FIT: Classic Relaxed Fit\n"
		"\n"
		"NECKLINE: Ribbed Crew Neck\n"
		"\n"
		"SLEEVES: Short Sleeves\n"
		"\n"
		"DIAMOND EMBELLISHMENT: Genuine diamond detailing\n"
		"\n"
		"DIAMOND RANGE: 1–5 mm per diamond\n"
		"\n"
		"PLACEMENT: Randomised celestial arrangement across front and back\n"
		"\n"
		"FINISH: Clean, refined construction\n"
		"\n"
		"“Some nights are remembered for the stars.”",
		"sizes": [],
		"reviews": [],
		"searchTags": [
			"diamond",
			"starry",
			"night",
			"Nuit Étoilée",
			"black",
			"expensive",
		],
		"images": ["starrynight/1.png", "starrynight/2.png"],
	},
	{
		"id": "001X5IRyo7",
		"name": "THE ASCENSION",
		"price": 80000,
		"visible": True,
		"available": True,
		"description": "A HIGHER ORDER\n"
		"\n"
		"The ascension brings the visual language of an old ceremonial engraving into a "
		"sharply considered modern form. An intricate monochromatic composition stretches "
		"across the chest, centred around a commanding figure surrounded by clouds, "
		"ornamental forms and figures arranged in an almost architectural symmetry.\n"
		"\n"
		"Rendered in shades of black and silver-grey, the artwork carries the depth of an "
		"aged illustration while retaining a distinctly contemporary presence. The "
		"pointed composition gives the graphic a natural sense of structure, allowing the "
		"intricate details to unfold gradually across the garment.\n"
		"\n"
		"The black cotton creates a quiet ground for the artwork, giving the piece an "
		"almost archival character. Small fleur de lis details at the sleeves complete "
		"the composition with a discreet signature.\n"
		"\n"
		"CONSTRUCTION\n"
		"\n"
		"Constructed from 100% cotton, selected for its substantial hand feel, natural "
		"breathability and ability to hold a clean silhouette. The classic relaxed cut is "
		"carefully proportioned, with a substantial ribbed neckline, clean sleeve "
		"finishing and a considered garment structure.\n"
		"The artwork is composed as a large format chest graphic, allowing its fine "
		"engraving like details and layered figures to remain the central expression of "
		"the piece.\n"
		"\n"
		"DETAILS\n"
		"\n"
		"FABRIC: 100% Premium Cotton\n"
		"\n"
		"colour: Black\n"
		"\n"
		"Fit: Classic Relaxed Fit\n"
		"\n"
		"Neckline: Ribbed Crew Neck\n"
		"\n"
		"Sleeves: Short Sleeves\n"
		"\n"
		"Graphic: Large-format monochromatic artwork\n"
		"\n"
		"Graphic Character: Antique engraving / ceremonial illustration\n"
		"Artwork Palette: Black, charcoal and silver-grey tones\n"
		"\n"
		"Sleeve Detail: Fleur-de-lis motifs\n"
		"\n"
		"Finish: Clean, refined construction",
		"sizes": [],
		"reviews": [],
		"searchTags": ["black", "engraving", "fleur de lis", "silver", "motif"],
		"images": ["theascension/1.png", "theascension/2.png"],
	},
	{
		"id": "001X26jdBL",
		"name": "PANTHÈRE",
		"price": 76000,
		"visible": True,
		"available": True,
		"description": "THE ART OF DISTINCTION\n"
		"\n"
		"PANTHÈRE is built around a finely illustrated procession of spotted big cats, "
		"arranged in a single horizontal line across the chest. Each figure carries its "
		"own character while maintaining the rhythm of the composition. Beneath them runs "
		"a deep burgundy linear motif, giving the artwork a subtle sense of structure and "
		"movement.\n"
		"\n"
		"The gold-toned illustration against the black cotton gives the piece its "
		"character: considered, distinguished, and slightly eccentric in the best way. It "
		"has the feel of an old house archive brought into a modern wardrobe.\n"
		"\n"
		"A signature article, quite literally.\n"
		"\n"
		"CONSTRUCTION\n"
		"Made from hundread percent cotton, the garment is selected for its substantial "
		"hand-feel, natural structure and lasting character. The classic relaxed "
		"silhouette is carefully proportioned, with a substantial ribbed neckline, clean "
		"finishing and a considered weight that gives the piece its presence.\n"
		"\n"
		"DETAILS\n"
		"\n"
		"FABRIC: hundred percent cotton\n"
		"\n"
		"COLOR: Black\n"
		"\n"
		"GRAPHIC: Front placement\n"
		"\n"
		"FIT: Classic relaxed fit\n"
		"\n"
		"\n"
		"“Elegance has always belonged to those who recognise it.”\n"
		"\n"
		"\n",
		"sizes": [],
		"reviews": [],
		"searchTags": [],
		"images": ["panthere/1.png", "panthere/2.png"],
	},
	{
		"id": "001Vw4Imfn",
		"available": True,
		"visible": True,
		"name": "EVERYTHING BEYOND",
		"description": "EVERYTHING.\n"
		"\n"
		"A standard.\n"
		"The piece is built around a single word, laid across the texture of snakeskin "
		"with the ease of a handwritten signature. There is little to explain. Everything "
		"says enough.\n"
		"\n"
		"It speaks to appetite without apology—the refusal to reduce desire to what is "
		"convenient, attainable, or merely sufficient. The pursuit continues until there "
		"is nothing left to pursue.\n"
		"\n"
		"Crafted from 100% premium cotton, the garment brings this uncompromising "
		"character into a clean, classic relaxed silhouette. The restraint of the "
		"construction allows the graphic to remain exactly what it is: direct, "
		"instinctive, and unapologetic.\n"
		"\n"
		"DETAILS \n"
		"\n"
		"FABRIC: 100% cotton\n"
		"\n"
		"COLOR: Black\n"
		"\n"
		"GRAPHIC: Front placement \n"
		"\n"
		"FIT: Classic relaxed fit ",
		"price": 75800,
		"sizes": [],
		"reviews": [],
		"searchTags": [
			"snake",
			"snake",
			"pattern",
			"Everything",
			"Calligraphy",
			"Cursive",
		],
		"images": [
			"everythingbeyond/1.png",
			"everythingbeyond/2.png",
			"everythingbeyond/3.png",
		],
	},
	{
		"id": "001WPsx6SF",
		"name": "GODSPEED",
		"price": 84000,
		"visible": True,
		"available": True,
		"description": "AN ENDURING BENEDICTION\n"
		"\n"
		"Godspeed is an expression carried across generations, offered with grace to "
		"those setting out toward something meaningful. A quiet wish for favourable "
		"fortune, enduring success, and safe return. This piece preserves that sentiment "
		"through restrained design, allowing the symbol to speak with quiet confidence.\n"
		"\n"
		"Crafted from 100% cotton, the garment reflects Velang's commitment to "
		"intentional design. Every element is composed with precision, allowing "
		"proportion, typography, and symbolism to exist in quiet balance without excess.\n"
		"\n"
		"DETAILS\n"
		"\n"
		"FABRIC: 100% cotton\n"
		"\n"
		"COLOR: Onyx black\n"
		"\n"
		"GRAPHIC: front placement\n"
		"\n"
		"FIT: Classic relaxed fit\n"
		"\n"
		'"May fortune favour what is pursued with sincerity."',
		"sizes": [],
		"reviews": [],
		"searchTags": ["Godspeed", "Dragon", "Black"],
		"images": ["godspeed/1.png", "godspeed/2.png"],
	},
	{
		"id": "001WOhOgwN",
		"name": "AMOR VINCIT OMNIA",
		"price": 249000,
		"visible": True,
		"available": True,
		"description": "The Language of Desire\n"
		"\n"
		"Armour Vincit Omnia brings the language of fine jewellery into a pared-back "
		"cotton silhouette. A solitary red lipstick mark is placed against pristine "
		"white, transforming a familiar gesture into a precise statement of colour and "
		"form.\n"
		"\n"
		"The lipstick motif is formed from approximately 1800 rubies, individually placed "
		"across the composition. The stones range from 1–3 mm, creating variation in "
		"scale and allowing the surface to reflect light with the irregular brilliance "
		"characteristic of fine gemstones.\n"
		"\n"
		"DETAILS\n"
		"\n"
		"Fabric: 100% Premium Cotton\n"
		"Colour: White\n"
		"Fit: Classic Relaxed Fit\n"
		"Neckline: Ribbed Crew Neck\n"
		"Sleeves: Short Sleeves\n"
		"Embellishment: Ruby lipstick motif\n"
		"Gemstone: Natural pigeon-blood rubies\n"
		"Ruby Size: 1–3 mm\n"
		"Approximate Ruby Count: 2000\n"
		"Placement: Upper chest\n"
		"\n"
		"“The very essence of romance is uncertainty.”\n"
		"— Oscar Wilde",
		"sizes": [],
		"reviews": [],
		"searchTags": ["Amor", "Red", "Lipstic", "Mark"],
		"images": ["amorvincitomnia/1.png", "amorvincitomnia/2.png"],
	},
	{
		"id": "001WQTvErm",
		"name": "THE GOOD LIFE",
		"price": 76700,
		"visible": True,
		"available": True,
		"description": "IN PRAISE OF THE EVERYDAY\n"
		"\n"
		"Not every reminder needs complexity. Some truths earn their place through "
		"repetition, quietly returning across different seasons of life. Life Is Good is "
		"an appreciation of the ordinary moments that often become the ones we remember "
		"most.\n"
		"\n"
		"Crafted from 100% cotton, this piece reflects Velang's commitment to intentional "
		"design. Every colour and illustrated form is placed with restraint, creating a "
		"composition that feels calm, open, and enduring. The artwork carries a quiet "
		"optimism, allowing the garment to express appreciation without demanding "
		"attention.\n"
		"\n"
		"DETAILS\n"
		"\n"
		"FABRIC: 100% cotton\n"
		"\n"
		"COLOR: Light yellow\n"
		"\n"
		"GRAPHIC: Front placement \n"
		"\n"
		"FIT: Classic relaxed fit\n"
		"\n"
		"\n"
		'"A life well lived is measured by the moments we choose to cherish."\n',
		"sizes": [],
		"reviews": [],
		"searchTags": ["Yellow", "Sunny", "Life", "Good"],
		"images": ["thegoodlife/1.png", "thegoodlife/2.webp"],
	},
	{
		"id": "001WQ7CC5q",
		"name": "STATE OF MIND",
		"price": 76700,
		"visible": True,
		"available": True,
		"description": "THE WAY WE SEE THE WORLD\n"
		"\n"
		"The quality of an experience is often shaped long before the moment itself. "
		"State of Mind reflects the idea that perspective quietly influences the way we "
		"move, connect, and remember. The composition embraces simplicity, allowing "
		"colour, form, and rhythm to create an atmosphere that feels effortless and "
		"unforced.\n"
		"\n"
		"Crafted from 100% cotton, this piece reflects Velang's commitment to intentional "
		"design. Every element is introduced with care, allowing typography, colour, and "
		"proportion to exist in quiet balance. The restrained composition preserves "
		"clarity, giving the artwork space to be experienced without excess.\n"
		"\n"
		"Designed with a classic relaxed silhouette, the fabric offers natural "
		"breathability, a refined hand feel, and lasting comfort. Built for everyday "
		"wear, it maintains its structure while allowing the artwork to remain the "
		"defining expression of the garment.\n"
		"\n"
		"DETAILS\n"
		"FABRIC: 100% cotton\n"
		"COLOR: Black\n"
		"GRAPHIC: Front placement \n"
		"FIT: Classic relaxed fit\n"
		"\n"
		'"The world often reflects the way we choose to meet it."',
		"sizes": [],
		"reviews": [],
		"searchTags": ["Luck", "Palm", "Mindset"],
		"images": ["stateofmind/1.png", "stateofmind/2.webp"],
	},
	{
		"id": "001WPLuew1",
		"name": "ITS ALL FOR FUN",
		"price": 76700,
		"visible": True,
		"available": True,
		"description": "THE JOY OF MOVEMENT\n"
		"\n"
		"Not every pursuit needs to be measured by its destination. Some moments exist "
		"for the simple pleasure of movement, discovery, and shared experience. It's All "
		"For Fun reflects that spirit through a composition that celebrates freedom with "
		"quiet confidence, reminding us that joy often reveals itself in motion.\n"
		"\n"
		"Crafted from 100% cotton, this piece reflects Velang's commitment to intentional "
		"design. Every element is composed with care, allowing colour, proportion, and "
		"symbolism to exist in effortless balance. The restrained composition preserves "
		"clarity, giving each detail room to speak in its own rhythm.\n"
		"\n"
		"Designed with a classic relaxed silhouette, the fabric offers natural "
		"breathability, a refined hand feel, and lasting comfort. Built for everyday "
		"wear, it maintains its structure while allowing the artwork to remain the "
		"defining expression of the garment.\n"
		"\n"
		"DETAILS\n"
		"\n"
		"FABRIC: 100% cotton\n"
		"\n"
		"COLOR: Baby blue\n"
		"\n"
		"GRAPHIC: Front placement \n"
		"\n"
		"FIT: Classic relaxed fit\n"
		"\n"
		'"Joy asks for nothing beyond the moment itself."',
		"sizes": [],
		"reviews": [],
		"searchTags": ["Joy", "Blue", "Horses", "It's all for fun"],
		"images": ["itsallforfun/1.png", "itsallforfun/2.png"],
	},
]


def load_products():
	"""Normalize curated product records and preserve every gallery image."""
	import re

	return [
		{
			"name": item["name"].strip(),
			"slug": re.sub(r"[^a-z0-9]+", "-", item["name"].lower()).strip("-"),
			"sku": item.get("id", "").upper(),
			"description": item.get("description", "").strip(),
			"price": (Decimal(str(item.get("price", 0))) / Decimal(100)).quantize(
				Decimal("0.01")
			),
			"images": item.get("images", []),
			"visible": item.get("visible", True),
			"available": item.get("available", True),
			"tags": item.get("searchTags", []),
		}
		for item in PRODUCT_SOURCE
		if item.get("visible", True)
	]


def page_content(slug: str, title: str, body: str):
	return {
		"slug": slug,
		"title": title,
		"body_markdown": body,
		"active": True,
		"meta": {},
	}


async def seed():
	await init_db()
	async with SessionLocal() as db:
		category_rows = {"t-shirts": "T-Shirts"}
		categories = {}
		for slug, name in category_rows.items():
			row = (
				await db.execute(select(Category).where(Category.slug == slug))
			).scalar_one_or_none()
			if not row:
				row = Category(
					name=name,
					slug=slug,
					description="",
					position=len(categories),
				)
				db.add(row)
				await db.flush()
			categories[slug] = row

		# Keep legacy demo groups out of the new compact navigation.
		for category_row in (await db.execute(select(Category))).scalars().all():
			if category_row.slug != "t-shirts":
				category_row.is_visible = False

		templates = {}
		for name, product_type, body in [
			(
				"Graphic tee",
				"Graphic tee",
				"# {{ product.name }}\n\n{{ product.subtitle }}\n\n{{ product.description }}\n\n**Material:** {{ product.material or 'Cotton' }}\n\n**Care:** {{ product.care or 'Wash according to garment label.' }}\n",
			),
			(
				"Statement piece",
				"Statement tee",
				"# {{ product.name }}\n\n> {{ product.subtitle }}\n\n{{ product.description }}\n\n**Designed for:** {{ product.product_type }}\n\n**SKU:** {{ product.sku }}\n",
			),
		]:
			row = (
				await db.execute(
					select(DescriptionTemplate).where(DescriptionTemplate.name == name)
				)
			).scalar_one_or_none()
			if not row:
				row = DescriptionTemplate(
					name=name, product_type=product_type, body_markdown=body
				)
				db.add(row)
				await db.flush()
			templates[product_type] = row

		catalogue = load_products()
		current_slugs = {item["slug"] for item in catalogue}
		# Keep order history intact while hiding obsolete demo items from the catalogue.
		for old in (await db.execute(select(Product))).scalars().all():
			if old.slug not in current_slugs:
				old.status = "archived"
		for index, item in enumerate(catalogue):
			row = (
				await db.execute(select(Product).where(Product.slug == item["slug"]))
			).scalar_one_or_none()
			if not row:
				row = Product(
					name=item["name"],
					slug=item["slug"],
					sku=item["sku"],
					subtitle="",
					description=item["description"],
					description_template_id=None,
					product_type="T-shirt",
					price=item["price"],
					currency="INR",
					status="active",
					visibility="public",
					featured=False,
					position=index,
					stock_count=12,
					track_inventory=True,
					badge="",
					meta={
						"size_mode": "predefined",
						"predefined_sizes": ["S", "M", "L", "XL", "XXL"],
						"custom_size_fields": ["width", "length"],
					},
					tags=item["tags"],
					material="100% cotton",
					care="Machine wash cold. Follow garment label.",
					shipping_note="Ships from India.",
				)
				db.add(row)
				await db.flush()
			else:
				row.name = item["name"]
				row.sku = item["sku"]
				row.description = item["description"]
				row.price = item["price"]
				row.currency = "INR"
				row.status = "active" if item["available"] else "draft"
				row.visibility = "public"
				row.position = index
				row.tags = item["tags"]
			# Reconcile images on every seed run, preserving the JSON file as the source of truth.
			existing_images = (
				(
					await db.execute(
						select(ProductImage).where(ProductImage.product_id == row.id)
					)
				)
				.scalars()
				.all()
			)
			for existing in existing_images:
				await db.delete(existing)
			for image_index, image in enumerate(item["images"]):
				db.add(
					ProductImage(
						product_id=row.id,
						path=f"/media/{image.lstrip('/')}",
						alt_text=item["name"],
						position=image_index,
						is_primary=image_index == 0,
					)
				)
			assigned = (
				(
					await db.execute(
						select(ProductCategory).where(
							ProductCategory.product_id == row.id
						)
					)
				)
				.scalars()
				.all()
			)
			for link in assigned:
				await db.delete(link)
			db.add(
				ProductCategory(
					product_id=row.id, category_id=categories["t-shirts"].id
				)
			)

		for key, value in DEFAULT_SITE.items():
			await set_site(db, key, value)
		await db.commit()
		print(
			f"Seeded {len(catalogue)} curated products, including their image galleries."
		)


if __name__ == "__main__":
	asyncio.run(seed())
