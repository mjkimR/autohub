// Capture hub-ui screenshots against a mocked API.
// Usage: node capture.mjs <label> [baseUrl]   -> out/<label>/*.png
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { handle, NOW, PROJECT_DETAIL_ID } from './fixtures.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const label = process.argv[2] ?? 'before';
const base = process.argv[3] ?? 'http://localhost:5199';
const outDir = join(here, 'out', label);
mkdirSync(join(outDir, 'full'), { recursive: true });

const pages = [
	['dashboard', '/'],
	['decisions', '/decisions'],
	['projects', '/projects'],
	['project-detail', `/projects/${PROJECT_DETAIL_ID}`],
	['pipeline-runs', '/projects/runs'],
	['schedule-jobs', '/schedules/jobs'],
	['ai-catalogs', '/settings/ai-catalogs'],
	['schedule-configs', '/schedules/configs'],
	['webhooks', '/operations/webhooks'],
	['notifications', '/settings/notifications']
];
const shots = [];
for (const theme of ['light', 'dark']) for (const [name, path] of pages) shots.push({ name, path, theme, width: 1440, height: 900 });
for (const theme of ['light', 'dark']) shots.push({ name: 'dashboard-narrow', path: '/', theme, width: 390, height: 844 });
for (const [name, path] of [['decisions-narrow', '/decisions'], ['pipeline-runs-narrow', '/projects/runs']]) shots.push({ name, path, theme: 'light', width: 390, height: 844 });

const unmocked = new Set();
const errors = [];
const browser = await chromium.launch();
try {
	for (const s of shots) {
		const context = await browser.newContext({
			viewport: { width: s.width, height: s.height },
			deviceScaleFactor: 1,
			colorScheme: s.theme,
			reducedMotion: 'reduce',
			locale: 'en-US',
			timezoneId: 'UTC'
		});
		await context.addInitScript((mode) => {
			try {
				localStorage.setItem('mode-watcher-mode', mode);
			} catch {}
		}, s.theme);
		const page = await context.newPage();
		await page.clock.setFixedTime(NOW);
		page.on('pageerror', (e) => errors.push(`${s.path}: ${e.message}`));
		// Only same-origin /api/* is intercepted; anything else external is blocked.
		await page.route('**/*', async (route) => {
			const url = new URL(route.request().url());
			if (url.origin !== new URL(base).origin) return route.abort();
			if (!url.pathname.startsWith('/api/')) return route.continue();
			const res = handle(route.request().method(), url.pathname, url.searchParams);
			if (!res) {
				unmocked.add(`${route.request().method()} ${url.pathname}`);
				return route.fulfill({ status: 404, json: { detail: 'Not mocked' } });
			}
			return route.fulfill({ status: res.status, json: res.body });
		});
		await page.goto(base + s.path, { waitUntil: 'networkidle' });
		await page.waitForFunction(() => !document.body.innerText.includes('Restoring session'));
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(600);
		const actual = await page.evaluate(() => document.documentElement.classList.contains('dark'));
		if (actual !== (s.theme === 'dark')) errors.push(`${s.path}: theme class mismatch for ${s.theme}`);
		const scrollW = await page.evaluate(() => document.documentElement.scrollWidth);
		if (scrollW > s.width) errors.push(`${s.path} @${s.width}px: horizontal overflow (scrollWidth ${scrollW})`);
		const file = join(outDir, `${s.name}-${s.theme}.png`);
		await page.screenshot({ path: file, animations: 'disabled' });
		await page.screenshot({ path: join(outDir, 'full', `${s.name}-${s.theme}.png`), fullPage: true, animations: 'disabled' });
		console.log(file);
		await context.close();
	}
} finally {
	await browser.close();
}
const report = { label, unmocked: [...unmocked].sort(), errors };
writeFileSync(join(outDir, 'report.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
