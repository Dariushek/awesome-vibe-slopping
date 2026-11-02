---
name: playwright
description: Drive a real browser with Playwright. Use whenever a task needs a browser, such as opening a page, checking a UI change, reading rendered content, filling a form, taking a screenshot, reproducing a UI bug or scraping data from websites.
---

# Playwright

Use Playwright for all browser work. Use another browser tool only if the user asks.

## Setup

If the project has a `playwright.config.*` or a Playwright dependency, use it through the project's own runner. Never add a second installation.

Otherwise work outside the project and add nothing to it:

```sh
dir=$(mktemp -d) && cd "$dir"
npm i @playwright/test
npx playwright install chromium
```

## Drive

Write a throwaway script in that directory, never in a test directory. Run it with `node`.

```js
const { chromium, expect } = require('@playwright/test');

(async () => {
  const browser = await chromium.launch();

  try {
    const page = await browser.newPage();
    await page.goto(process.env.BASE_URL);
    console.log(await page.locator('body').ariaSnapshot());

    await page.getByRole('link', { name: 'Sign in' }).click();
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
    await page.screenshot({ path: 'result.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();
```

## Scrape

```js
const rows = await page.locator('article').evaluateAll(items =>
  items.map(item => ({
    title: item.querySelector('h2')?.textContent.trim(),
    url: item.querySelector('a')?.href,
  })),
);
```

- Find the structure first from the aria snapshot or the page HTML. CSS selectors are fine here when they match what you saw.
- If the page loads data from a JSON endpoint, read that with `page.request` instead of parsing HTML.
- Write results to a file as you go, so a failed run can resume.
- Wait between requests. On a 429, slow down.
- Stop and tell the user on a CAPTCHA, login wall or block. Do not bypass it.

## Rules

- Observe before acting. Print the aria snapshot and use only roles, labels and text it shows.
- Prefer `getByRole`, `getByLabel` and `getByText`. Do not guess CSS paths.
- Observe again after navigation or a large page change.
- Check with `expect`, which retries. No fixed sleeps.
- Read every screenshot you take. A saved file proves nothing.
- Report console errors and failed requests when checking a UI change.
- Keep real credentials out of scripts. Read them from the environment.
- A check worth keeping becomes a real test in the project's suite.
