import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:5173';

const pages = [
  { path: '/', name: 'home' },
  { path: '/runs', name: 'runs' },
  { path: '/scenarios', name: 'scenarios' },
  { path: '/assumptions', name: 'assumptions' },
  { path: '/compare', name: 'compare' },
];

async function takeScreenshots() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  const page = await context.newPage();

  console.log('Taking screenshots...\n');

  for (const { path, name } of pages) {
    try {
      const url = `${BASE_URL}${path}`;
      console.log(`📸 ${name}: ${url}`);
      await page.goto(url, { waitUntil: 'networkidle', timeout: 10000 });
      await page.waitForTimeout(500); // Allow any animations to settle
      await page.screenshot({ 
        path: `screenshots/${name}.png`,
        fullPage: true 
      });
      console.log(`   ✓ Saved to screenshots/${name}.png`);
    } catch (error) {
      console.log(`   ✗ Failed: ${error instanceof Error ? error.message : error}`);
    }
  }

  await browser.close();
  console.log('\nDone!');
}

takeScreenshots();
