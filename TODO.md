### Admin app
- [ ] In templates, the field thing take up a lot of screen space, makes it harder to visualize all the variables to type in the template, and to save it and stuff cause the save button is all the way down, make the save button sticky like in product edits/add and also consistently everywhere else, also option to drag and drop variables so i can arrange them better

- [ ] Many of the editing pages and stuff can become way too long, try to make it shorter somehow without removing features, how do others handle that? do that

- [ ] Maybe a better drag and drop way to reorder? takes same time to reorder big cards, either try to make them smaller or a new way to drag and drop

- [ ] Just noticed some components don't change color according to dark/light themes like the check marks and toggles

- [ ] I don't see any use for varients currently, and badge, so maybe remove them, COMPLETELY, and sku ids, don't really see a use for it? just make one id and use that, i might want it later idk but don't see any use for it currently, remove it completely, every mention of it. yea lets keep admin panel only for controlling things, there can be different things for tracking stuff.. maybe

- [ ] Option to delete categories, only empty, same with templates, i also should be able to quickly see what products are in which categories so i can change it quickly, maybe even a better search so i can search the products categories and anything by anything, got inspiration from discord's chat search behaviour, add the ability to search everywhere, search is better than scrolling al the way down

- [ ] Reordering resets the view or something so if i have scrolled down in the product list and reorder, it takes me back all the way up, also i think it would be good if it would have moved other stuff down/up to actively make space for the thing i'm dragging and dropping, like it's the standard everywhere, to make it feel responsive


### Server
- [ ] I think the markdowns should render empty new lines as padding or by another way not new line, idk, i can't space lines further apart currently and i also think it's actually removing new lines or doing something, but i'm not sure

- [ ] Markdowns (every markdown value from product description to templates and pages) do not render all of markdown syntax, for example, tables, they are not rendered at all, and code blocks look just like `text`, add possibly every markdown syntax and render it uniquely but still consistent with the website style

- [ ] Collapsibles should have option to set a default state of open or closed, and also i think collapsables that i define in pages, markdown descriptions looks different from the menu on the header, i like the straight lines more, than the curved lines, keep it consistent. Even categories in menu that don't have sub categories, should look the same as the ones that do actually have and can uncollapse, the difference is that one won't have that arrow and the other will. Also change of mind, don't make collapsables share the save border and all that stuff, they should only have one border at the bottom, and a smooth opening and closing animation of showing and hiding whatever's under it

- [ ] make all text that has a link underlined

- [ ] Also a new type of 'collapsable' we'll reuse the current syntax, instead of, `::: collapse({state}) {title}\n...\n:::` it'll use, `::: fade({state})\n...\n:::` notice that there's no title, because this one just shows the normal text, but at a set amount of length it'll fade the text, and add a read less button, but not look like the button we currently have, instead it should be styled as a link but work as a button, and it's also underlined ofcourse, it should have the sane smooth opening and closing animation. And the name should also change from Read More to Read Less, like it is everywhere

- [ ] Maybe have the arrow that indicates if the collapsible is open or closed and rotates, be on the very right instead of left

- [ ] Make it so i can see category pages that also have subcategories, because currently i think categories with sub category only act as a collapsible instead of a link to that page showing the products in it, here's how they should work now:
      If i press the category name, it'll take me to the page, press anywhere else in that area but the name, open the collapsible, if there are no categories in it, again, take me to the page
	  The only-link-categories (categories with no sub category) should not have an arrow at the left to show that they don't have anything in it
	  To indicate that clicking the name takes you somewhere, underline it

- [ ] The menu shouldn't cover the entire screen in desktop, make sure of that

- [ ] Don't add the .00 price anywhere untill the purchase page

- [ ] Maybe have a font size control in site theme settings and make sure all the font size is consistent

- [ ] Products currently has no color option, i want to be able to add colors (hex with the wheel as well) and also have option to add different images according to the product color, they can have names, but the webpage will generally just have the color button

- [ ] Category product listing pages now need an upgrade, it's too big so i got it below here:

Currently the category pages only show a big header on top telling what category it is
it should now use the description and the image as well.
If there's an image, the category name and description should be at the bottom left corner of the *image*, yes it should be on the image, it should add a semi transparent dark gradient (light on top and darker below) as the text background on the image to keep it readable, oh and white text when it's on image, the image should have no padding whatsoever on it, whatever is there, you'll add it, full screen, just like the product image on product pages on mobile.
Now the header should get transparent on these category images too. Also new logic, have the length of scroll it takes the header to become solid again, exactly the height of the image, or simply, 'if header on big image, become transparent, otherwise solid'
category name shouldn't be very big, make it just bigger to stand out
if there's no image for the category, just have the same size of category name and description as it would have had on the image but now normal black text and no gradient stuff, it's freely on the page, padded how normal text written on it would have had
having no category description doesn't change, the name should be at the bottom left corner
after all the image stuff, padded a little add a side scrolling option, if the category has sub categories, the side sroller will list all the sub categories in it, normal names, no underline or anything, just text (category names), with some gap in them, also removing the generic browser's scrollbar, we don't want that. And also sticky, after i scroll past it, it'll come with me right below the header with no gap between that and the header
We also need to figure out how to add conflicting categories, like, men and women, these categories can have a jewelry, but men > jewelry should only have men's stuff, and women > jewelry should only have women's jewelry, but just jewelry? well that should have mixed, we also have another problem, men and women category can have jewelry category sure, but someone could also go in jewelry and expect to have men and women category in it, now that's just a circular reference maybe it's easy, but how do i filter out women jewelry if i go from men > jewelry and not jewelry > men. Also, both men-women and jewelry categories can be root AND sub categories. I mean i know this might not be that complicated but how do i present and visualize it in the admin panel? that's seems a bit hard for me.
Yeah, i don't really want to solve that, you do it, add bunch of options and document it so i can explain to others
don't take my wording too seriously, i might be calling something by a weird made up name while it actually has a different name, in your mind, keep the original (always)
