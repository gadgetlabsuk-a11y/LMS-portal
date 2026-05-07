// Playwright + axe-core accessibility tests
const { test, expect } = require('@playwright/test');
const { checkA11y, injectAxe } = require('@axe-core/playwright');

const BASE = 'http://localhost:8000';

test.describe('Accessibility — WCAG 2.1 AA', () => {
  test('homepage passes axe', async ({ page }) => {
    await page.goto(BASE);
    await injectAxe(page);
    await checkA11y(page, null, {
      axeOptions: { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] } },
    });
  });
});
