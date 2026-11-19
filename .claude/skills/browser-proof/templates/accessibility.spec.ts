import { expect, test, type Page } from "@playwright/test";

// Accessibility, measured in the real browser. Read-only: it may log in, nothing else.
// ADAPT: every line marked ADAPT (URLs, selectors, labels). Keep the helpers as they are.

/** WCAG contrast between an element's text colour and the background actually painted behind it. */
async function contrast(page: Page, selector: string) {
  return page.locator(selector).first().evaluate((el) => {
    // A canvas converts any CSS colour (oklch, lab, hsl…) to RGB.
    const ctx = document.createElement("canvas").getContext("2d", { willReadFrequently: true })!;
    const rgba = (colour: string) => {
      ctx.clearRect(0, 0, 1, 1);
      ctx.fillStyle = colour;
      ctx.fillRect(0, 0, 1, 1);
      const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
      return { r, g, b, a: a / 255 };
    };
    const over = (top: { r: number; g: number; b: number; a: number }, under: { r: number; g: number; b: number }) => ({
      r: top.r * top.a + under.r * (1 - top.a),
      g: top.g * top.a + under.g * (1 - top.a),
      b: top.b * top.a + under.b * (1 - top.a),
    });
    // Effective background: the ancestors' backgrounds, composited from the root down.
    const layers: ReturnType<typeof rgba>[] = [];
    for (let n: Element | null = el; n; n = n.parentElement) layers.unshift(rgba(getComputedStyle(n).backgroundColor));
    let background = { r: 255, g: 255, b: 255 }; // the browser's canvas default
    for (const layer of layers) background = over(layer, background);
    const text = over(rgba(getComputedStyle(el).color), background);
    const luminance = ({ r, g, b }: { r: number; g: number; b: number }) => {
      const [R, G, B] = [r, g, b].map((v) => {
        const c = v / 255;
        return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * R + 0.7152 * G + 0.0722 * B;
    };
    const [light, dark] = [luminance(text), luminance(background)].sort((a, b) => b - a);
    return (light + 0.05) / (dark + 0.05);
  });
}

test("contrast: at least 4.5:1 for every text style of the theme (WCAG AA)", async ({ page }) => {
  await page.goto("/"); // ADAPT: a page that shows most text styles
  const styles: Record<string, string> = {
    // ADAPT: one selector per text style. The selector must hit an element WITH text:
    // a surprising ratio usually means it matched a decorative or hidden element.
    "body text": "h1",
    "secondary text": "main p",
    "navigation link": "header nav a",
    "primary button": "main button[type=submit]",
  };
  for (const [what, selector] of Object.entries(styles))
    expect(await contrast(page, selector), what).toBeGreaterThanOrEqual(4.5);
});

test("keyboard: skip link, visible focus, a task done without the mouse", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to content" }); // ADAPT: the skip link's name
  await expect(skip).toBeFocused();
  await expect(skip).toBeInViewport();

  // ADAPT: a DIFFERENT page than the one just visited, so focus restarts from the top of the document.
  await page.goto("/about");
  for (let i = 0; i < 8; i++) {
    await page.keyboard.press("Tab");
    const focus = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement;
      const s = getComputedStyle(el);
      return {
        name: (el.getAttribute("aria-label") ?? el.textContent ?? "").trim().slice(0, 30),
        visible: (s.outlineStyle !== "none" && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== "none",
      };
    });
    expect(focus.visible, `visible focus on "${focus.name}"`).toBe(true);
  }

  // ADAPT: one real task with the keyboard only (here: a login).
  await page.goto("/login");
  await page.getByLabel("Email").focus();
  await page.keyboard.type("demo@example.test");
  await page.keyboard.press("Tab");
  await page.keyboard.type("demo-password");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("labels: every field has an accessible name, including on repeated forms", async ({ page }) => {
  const unnamed = () =>
    page.evaluate(() =>
      [...document.querySelectorAll<HTMLInputElement>("input:not([type=hidden]), select, textarea")]
        .filter((c) => !(c.labels?.length || c.getAttribute("aria-label") || c.getAttribute("aria-labelledby")))
        .map((c) => c.name || c.id || c.outerHTML.slice(0, 60)),
    );
  // ADAPT: every page with a form, and above all the pages that repeat one form per row:
  // duplicate ids leave every field but the first without its label.
  for (const url of ["/login", "/settings", "/admin/users"]) {
    await page.goto(url);
    expect(await unnamed(), `fields without a label on ${url}`).toEqual([]);
  }
});
