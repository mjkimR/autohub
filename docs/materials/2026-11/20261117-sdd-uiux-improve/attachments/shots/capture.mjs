// Capture hub-ui screenshots against a mocked API.
// Usage: node capture.mjs <label> [baseUrl]   -> out/<label>/*.png
// Env: SUITE=all adds the original non-SDD pages; ONLY=<substr,substr> captures matching shot names only.
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { handle, NOW, PROJECT_DETAIL_ID } from './fixtures.mjs';
import { PROP, PROP_EMPTY, SPEC, RUN_GATE, RUN_RESUME, RUN_IMPL, RUN_FAILED, SDD_PROJECT } from './fixtures-sdd.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const label = process.argv[2] ?? 'before';
const base = process.argv[3] ?? 'http://localhost:5199';
const outDir = join(here, 'out', label);
mkdirSync(join(outDir, 'full'), { recursive: true });

// ---- shot definitions ------------------------------------------------------
const repo = (extra = '') => `/projects/${SDD_PROJECT}?tab=repository${extra}`;
const unit = (u) => repo(`&unit=${encodeURIComponent(u)}`);
const runPage = (id) => `/projects/${SDD_PROJECT}/runs/${id}`;
const click = (role, name, opts = {}) => async (page) => page.getByRole(role, { name, ...opts }).first().click();
const startPlanning = click('button', 'Start Planning');
const openEnroll = async (page) => {
	await page.getByText('Enroll an existing PR').click();
	await page.getByLabel('Pull request').fill('433');
};
const enroll = async (page) => {
	await openEnroll(page);
	await page.getByRole('button', { name: 'Enroll PR' }).click();
};
const inspectOwner = async (page) => {
	await startPlanning(page);
	await page.getByText('Request details').first().waitFor();
};
const reviewEntry = (title) => async (page) => {
	await page.locator('article', { hasText: title }).getByRole('button', { name: 'Review' }).click();
};

/**
 * name, path, ready (text that must appear), actions (after load), scenario:
 *   fail: [regex on "METHOD /path?query"] -> 500; hang: [regex] -> never answered;
 *   override: { "METHOD /path": {status, body} }; plus fixture options (start, claim, sddRuns).
 */
const sddShots = [
	// Repository view (NativeSddViewer, SddUnitActions, SddProposals, SddExecution, SddRunLinks)
	{ name: 'sdd-repo-documents', path: repo(), ready: 'Select a document to inspect it' },
	{ name: 'sdd-repo-proposals', path: repo(), actions: click('button', 'Proposals', { exact: true }), ready: 'Webhook delivery backoff' },
	{ name: 'sdd-repo-specs', path: repo(), actions: click('button', 'Specs', { exact: true }), ready: 'Idempotent refund requests' },
	{ name: 'sdd-repo-roadmap', path: repo(), actions: click('button', 'Roadmap', { exact: true }), ready: 'Q4 reliability' },
	{ name: 'sdd-repo-git-browser', path: repo(), actions: click('button', 'Git Browser'), ready: 'README.md' },
	{ name: 'sdd-repo-proposal-unit', path: unit(PROP), ready: 'PR #431', main: true },
	{ name: 'sdd-repo-spec-unit', path: unit(SPEC), ready: 'PR #433' },
	{ name: 'sdd-repo-history-empty', path: unit(PROP_EMPTY), ready: 'No PR runs for this unit yet' },
	{ name: 'sdd-repo-history-error', path: unit(PROP), scenario: { fail: ['/sdd/runs'] }, ready: 'Retry history' },
	{ name: 'sdd-repo-docs-error', path: repo(), scenario: { fail: ['/repository/tree\\?path=docs(&|$)'] }, ready: 'Document listing incomplete' },
	{ name: 'sdd-repo-unit-unavailable', path: unit('docs/proposals/PROP-missing-unit'), ready: 'Unit unavailable' },
	{ name: 'sdd-repo-loading', path: repo(), scenario: { hang: ['/repository/info'] }, ready: 'Loading repository' },
	{ name: 'sdd-repo-enroll-open', path: unit(SPEC), actions: openEnroll, ready: 'Register an existing PR' },
	// Start outcomes (SddStartOutcome) and claim recovery (SddClaimRecovery)
	{ name: 'sdd-start-success', path: unit(PROP), actions: startPlanning, ready: 'Planning registered' },
	{ name: 'sdd-start-refused', path: unit(PROP), scenario: { start: 'refused' }, actions: startPlanning, ready: 'Enable the project and connect its GitHub repository' },
	{ name: 'sdd-start-unresolved', path: unit(PROP), scenario: { start: 'unresolved' }, actions: startPlanning, ready: 'Start outcome unresolved' },
	{ name: 'sdd-start-owner-conflict', path: unit(PROP), scenario: { start: 'conflict' }, actions: startPlanning, ready: 'Request details', main: true },
	{ name: 'sdd-start-conflict-no-claim', path: unit(PROP), scenario: { start: 'conflict-no-claim' }, actions: startPlanning, ready: 'Planning was not started' },
	{ name: 'sdd-claim-releasable', path: unit(PROP), scenario: { start: 'conflict', claim: 'releasable' }, actions: async (p) => { await inspectOwner(p); await p.getByRole('checkbox').check(); }, ready: 'Release inspected reservation' },
	{ name: 'sdd-claim-live-lease', path: unit(PROP), scenario: { start: 'conflict', claim: 'live' }, actions: inspectOwner, ready: 'publication lease still owns the work' },
	{ name: 'sdd-claim-with-run', path: unit(PROP), scenario: { start: 'conflict', claim: 'withRun' }, actions: inspectOwner, ready: 'Open retained Run' },
	{ name: 'sdd-enroll-reconcile-required', path: unit(SPEC), scenario: { start: 'enroll-reconcile' }, actions: enroll, ready: 'Request details' },
	// PR run page (run-page/*, RunOrigins, RunDecisions, SddRunPanel)
	{ name: 'sdd-run-gate-pending', path: runPage(RUN_GATE), ready: 'Evidence at head', main: true },
	{ name: 'sdd-run-resume-pending', path: runPage(RUN_RESUME), ready: 'Resume with this answer' },
	{ name: 'sdd-run-gate-earlier-head', path: runPage(RUN_GATE), scenario: { observation: 'earlier-head' }, ready: 'Observed on an earlier head', main: true },
	{ name: 'sdd-run-draft-waiting', path: runPage(RUN_IMPL), scenario: { observation: 'draft-waiting' }, ready: 'Applied gate answer', main: true },
	{ name: 'sdd-run-ready-failed', path: runPage(RUN_IMPL), scenario: { observation: 'ready-failed' }, ready: 'Applied gate answer' },
	{ name: 'sdd-run-ready-passed', path: runPage(RUN_IMPL), scenario: { observation: 'ready-passed' }, ready: 'Applied gate answer' },
	{ name: 'sdd-run-implementing', path: runPage(RUN_IMPL), ready: 'Attempt #2' },
	{ name: 'sdd-run-failed', path: runPage(RUN_FAILED), ready: 'AGENT_NO_COMMIT' },
	{ name: 'sdd-run-questions-error', path: runPage(RUN_GATE), scenario: { fail: [`/pipeline-runs/${RUN_GATE}/questions`] }, ready: "Couldn't load this run's decisions" },
	{ name: 'sdd-run-attempts-error', path: runPage(RUN_GATE), scenario: { fail: [`/pipeline-runs/${RUN_GATE}/attempts`] }, ready: 'Evidence at head' },
	{ name: 'sdd-run-loading', path: runPage(RUN_GATE), scenario: { hang: [`GET /api/v1/pipeline-runs/${RUN_GATE}$`] }, ready: 'Loading PR run' },
	{ name: 'sdd-run-not-found', path: runPage('00000000-0000-4000-8000-000000000999'), ready: 'PR run not found' },
	// Decisions inbox and RunDecisionsDialog
	{ name: 'sdd-decisions-inbox', path: '/decisions', ready: 'Planning gate', main: true },
	{ name: 'sdd-decisions-dialog-gate', path: '/decisions', actions: reviewEntry('Planning gate'), ready: 'Evidence at head', main: true },
	{ name: 'sdd-decisions-dialog-scrolled', path: '/decisions', actions: async (p) => { await reviewEntry('Planning gate')(p); await p.getByText('Evidence at head').waitFor(); await p.getByLabel('Your answer').scrollIntoViewIfNeeded(); }, ready: 'Save and resume', main: true },
	{ name: 'sdd-decisions-dialog-resume', path: '/decisions', actions: reviewEntry('Development gate'), ready: 'Resume with this answer' },
	{ name: 'sdd-decisions-empty', path: '/decisions', scenario: { override: { 'GET /api/v1/pipeline-runs/decisions': { status: 200, body: { items: [], has_more: false, next_cursor: null } } } }, ready: 'No matching observed pending decisions' },
	{ name: 'sdd-decisions-error', path: '/decisions', scenario: { fail: ['GET /api/v1/pipeline-runs/decisions(\\?|$)'] } },
	// Project detail of the SDD project
	{ name: 'sdd-project-overview', path: `/projects/${SDD_PROJECT}`, ready: 'Payments service' },
	{ name: 'sdd-project-runs', path: `/projects/${SDD_PROJECT}?tab=runs`, ready: 'Plan: Idempotent refund requests' }
];

const legacyPages = [
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

let shots = [];
for (const theme of ['light', 'dark']) for (const s of sddShots) shots.push({ ...s, theme, width: 1440, height: 900 });
for (const theme of ['light', 'dark'])
	for (const s of sddShots.filter((x) => x.main)) shots.push({ ...s, name: `${s.name}-narrow`, theme, width: 390, height: 844 });
if (process.env.SUITE === 'all') {
	for (const theme of ['light', 'dark']) for (const [name, path] of legacyPages) shots.push({ name, path, theme, width: 1440, height: 900 });
	for (const theme of ['light', 'dark']) shots.push({ name: 'dashboard-narrow', path: '/', theme, width: 390, height: 844 });
}
if (process.env.ONLY) {
	const only = process.env.ONLY.split(',');
	shots = shots.filter((s) => only.some((o) => s.name.includes(o)));
}

// ---- capture ---------------------------------------------------------------
const unmocked = new Set();
const errors = [];
const perShot = {};
const index = [];
const browser = await chromium.launch();
try {
	for (const s of shots) {
		const key = `${s.name}-${s.theme}`;
		const shotUnmocked = new Set();
		const shotErrors = [];
		const sc = s.scenario ?? {};
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
			// Deterministic request ids so request ids shown in start outcomes match across runs.
			let n = 0;
			try {
				crypto.randomUUID = () => `11111111-2222-4333-8444-${String(++n).padStart(12, '0')}`;
			} catch {}
		}, s.theme);
		const page = await context.newPage();
		await page.clock.setFixedTime(NOW);
		page.on('pageerror', (e) => shotErrors.push(`pageerror: ${e.message}`));
		page.on('console', (m) => {
			if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) shotErrors.push(`console: ${m.text().slice(0, 300)}`);
		});
		// Only same-origin /api/* is intercepted; anything else external is blocked.
		await page.route('**/*', async (route) => {
			const req = route.request();
			const url = new URL(req.url());
			if (url.origin !== new URL(base).origin) return route.abort();
			if (!url.pathname.startsWith('/api/')) return route.continue();
			const sig = `${req.method()} ${url.pathname}${url.search}`;
			if ((sc.hang ?? []).some((r) => new RegExp(r).test(sig))) return; // never answered (loading state)
			if ((sc.fail ?? []).some((r) => new RegExp(r).test(sig)))
				return route.fulfill({ status: 500, json: { type: 'about:blank', title: 'Internal Server Error', status: 500, detail: 'Internal Server Error' } });
			const ov = sc.override?.[`${req.method()} ${url.pathname}`];
			if (ov) return route.fulfill({ status: ov.status, json: ov.body });
			let body = null;
			try {
				body = req.postDataJSON();
			} catch {}
			const res = handle(req.method(), url.pathname, url.searchParams, body, sc);
			if (!res) {
				const u = `${req.method()} ${url.pathname}`;
				unmocked.add(u);
				shotUnmocked.add(u);
				return route.fulfill({ status: 404, json: { detail: 'Not mocked' } });
			}
			return route.fulfill({ status: res.status, json: res.body });
		});
		const hang = (sc.hang ?? []).length > 0;
		await page.goto(base + s.path, { waitUntil: hang ? 'domcontentloaded' : 'networkidle' });
		await page.waitForFunction(() => !document.body.innerText.includes('Restoring session'));
		if (!hang) await page.waitForLoadState('networkidle');
		try {
			if (s.actions) {
				await page.waitForTimeout(400);
				await s.actions(page);
				await page.waitForLoadState('networkidle');
			}
			if (s.ready) await page.getByText(s.ready).first().waitFor({ timeout: 10000 });
		} catch (e) {
			shotErrors.push(`ready/actions failed: ${e.message.split('\n')[0]}`);
		}
		if (!hang) await page.waitForLoadState('networkidle');
		await page.waitForTimeout(600);
		const actual = await page.evaluate(() => document.documentElement.classList.contains('dark'));
		if (actual !== (s.theme === 'dark')) shotErrors.push(`theme class mismatch for ${s.theme}`);
		const scrollW = await page.evaluate(() => document.documentElement.scrollWidth);
		if (scrollW > s.width) shotErrors.push(`horizontal overflow @${s.width}px (scrollWidth ${scrollW})`);
		const file = join(outDir, `${key}.png`);
		await page.screenshot({ path: file, animations: 'disabled' });
		await page.screenshot({ path: join(outDir, 'full', `${key}.png`), fullPage: true, animations: 'disabled' });
		console.log(file, shotErrors.length ? `(${shotErrors.length} issue(s))` : '');
		for (const e of shotErrors) errors.push(`${key} ${s.path}: ${e}`);
		perShot[key] = { path: s.path, unmocked: [...shotUnmocked].sort(), errors: shotErrors };
		index.push({ file: `${key}.png`, name: s.name, theme: s.theme, viewport: `${s.width}x${s.height}`, url: s.path, scenario: s.scenario ?? null });
		await context.close();
	}
} finally {
	await browser.close();
}
const report = { label, unmocked: [...unmocked].sort(), errors, shots: perShot };
writeFileSync(join(outDir, 'report.json'), JSON.stringify(report, null, 2));
writeFileSync(join(outDir, 'index.json'), JSON.stringify(index, null, 2));
console.log(JSON.stringify({ label, unmocked: report.unmocked, errors }, null, 2));
