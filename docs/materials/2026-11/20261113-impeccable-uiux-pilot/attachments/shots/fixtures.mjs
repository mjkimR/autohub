// Deterministic mock API for Auto Hub hub-ui screenshots.
// Shapes follow modules/hub-ui/src/lib/api/generated/*.d.ts. No real data or credentials.

export const NOW = new Date('2026-11-12T09:30:00Z');
const ago = (min) => new Date(NOW.getTime() - min * 60_000).toISOString();
const later = (min) => new Date(NOW.getTime() + min * 60_000).toISOString();
const uuid = (n) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;

const stamps = (min) => ({ created_at: ago(min), updated_at: ago(Math.max(0, min - 5)) });

// ---- connectors / catalogs -------------------------------------------------
const CONNECTOR_GH = uuid(101);
const CONNECTOR_JULES = uuid(102);
export const connectors = [
	{ id: CONNECTOR_GH, name: 'GitHub App (sandbox)', provider: 'github', config: {}, enabled: true, has_credentials: true, ...stamps(9000) },
	{ id: CONNECTOR_JULES, name: 'Jules workspace', provider: 'jules', config: {}, enabled: true, has_credentials: true, ...stamps(8000) },
	{ id: uuid(103), name: 'Legacy PAT', provider: 'github', config: {}, enabled: false, has_credentials: false, ...stamps(20000) }
];

const CAT_CODEX = uuid(201);
const CAT_JULES = uuid(202);
const catalog = (o) => ({
	adapter: 'default',
	connector_id: null,
	enabled: true,
	availability_state: 'normal',
	available_at: null,
	availability_source: null,
	availability_updated_at: ago(30),
	availability_note: null,
	configured_concurrency: 2,
	effective_concurrency: 2,
	refresh_jitter_minutes: 5,
	policy_config: {},
	policy_state: {},
	revision: 3,
	held_run_count: 0,
	active_dispatch_count: 0,
	open_session_count: 0,
	connector_provider: null,
	pipeline_delivery: true,
	connection_test: true,
	session_work_types: [],
	...stamps(10000),
	...o
});
export const catalogs = [
	catalog({ id: CAT_CODEX, key: 'codex-primary', name: 'Codex primary', kind: 'codex', adapter: 'codex-cli', active_dispatch_count: 2, open_session_count: 1, configured_concurrency: 3, effective_concurrency: 3 }),
	catalog({ id: CAT_JULES, key: 'jules-team', name: 'Jules team', kind: 'jules', adapter: 'jules-api', connector_id: CONNECTOR_JULES, connector_provider: 'jules', held_run_count: 1 }),
	catalog({ id: uuid(203), key: 'codex-backup', name: 'Codex backup', kind: 'codex', adapter: 'codex-cli', availability_state: 'quota_blocked', available_at: later(180), availability_source: 'daily_quota', availability_note: 'Daily quota reached', held_run_count: 2, effective_concurrency: 0 }),
	catalog({ id: uuid(204), key: 'codex-probe', name: 'Codex probe', kind: 'codex', adapter: 'codex-cli', availability_state: 'probe', configured_concurrency: 1, effective_concurrency: 1 }),
	catalog({ id: uuid(205), key: 'jules-archive', name: 'Jules archive', kind: 'jules', adapter: 'jules-api', enabled: false, availability_state: 'disabled', connector_id: CONNECTOR_JULES, connector_provider: 'jules', effective_concurrency: 0 })
];

// ---- projects --------------------------------------------------------------
const P1 = uuid(301);
const P2 = uuid(302);
const P3 = uuid(303);
const verification = { workflow: 'ci.yml', required_jobs: ['lint', 'test'], event: 'pull_request' };
const automation = {
	auto_merge: true,
	merge_method: 'squash',
	auto_fix_ci: true,
	auto_fix_conflicts: true,
	auto_enroll_on_trigger: false,
	auto_enroll_sessions: false,
	dispatch_interval_seconds: 300,
	max_in_flight_runs: 3,
	repository_viewer: 'default'
};
const project = (o) => ({
	project_type: 'general',
	enabled: true,
	revision: 4,
	template_version: null,
	last_check: null,
	...stamps(12000),
	...o
});
const github = (repository) => ({ repository, github_connector_id: CONNECTOR_GH, verification, template_id: 'python-uv', automation, ai_catalog_id: CAT_CODEX });
export const projects = [
	project({
		id: P1,
		name: 'Payments service',
		project_type: 'sdd',
		repository: 'example-org/payments-service',
		github_connector_id: CONNECTOR_GH,
		verification,
		github: github('example-org/payments-service'),
		last_check: {
			checked_at: ago(45),
			project_revision: 4,
			ready: true,
			github_login: 'autohub-bot',
			checks: [
				{ name: 'repository', status: 'passed', detail: 'Repository reachable' },
				{ name: 'workflow', status: 'passed', detail: 'ci.yml found' },
				{ name: 'branch_protection', status: 'skipped', detail: 'Not required' }
			]
		}
	}),
	project({
		id: P2,
		name: 'Docs site',
		repository: 'example-org/docs-site',
		github_connector_id: CONNECTOR_GH,
		verification,
		github: { ...github('example-org/docs-site'), template_id: 'node-npm' },
		last_check: {
			checked_at: ago(300),
			project_revision: 2,
			ready: false,
			checks: [
				{ name: 'repository', status: 'passed', detail: 'Repository reachable' },
				{ name: 'workflow', status: 'failed', detail: 'Required job "build" not found' }
			]
		}
	}),
	project({ id: P3, name: 'Internal tooling', enabled: false, repository: null })
];

// ---- pipeline runs ---------------------------------------------------------
const RUN_STATES = [
	['implementing', 'Add idempotency keys to refund endpoint', null],
	['awaiting_ci', 'Migrate ledger tables to partitioned layout', null],
	['paused', 'Retry webhook delivery with backoff', 'Waiting for an answer to a design question'],
	['blocked', 'Upgrade payment SDK to v5', 'Merge conflict could not be resolved automatically'],
	['failed', 'Fix flaky settlement reconciliation test', 'CI failed 3 times on required job "test"'],
	['queued', 'Document refund API errors', null],
	['dispatching', 'Add currency rounding helper', null],
	['completed', 'Bump lint toolchain', null],
	['canceled', 'Experiment: async ledger writer', 'Canceled by user']
];
export const runs = RUN_STATES.map(([state, title, pause], i) => {
	const number = 412 - i * 7;
	const branch = `autohub/${title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 32)}`;
	const projectId = i % 3 === 2 ? P2 : P1;
	const repo = projectId === P1 ? 'example-org/payments-service' : 'example-org/docs-site';
	return {
		id: uuid(400 + i),
		project_id: projectId,
		ai_catalog_id: i % 2 ? CAT_JULES : CAT_CODEX,
		requested_catalog_id: null,
		sdd_snapshot: null,
		sdd_progress: null,
		project_revision: 4,
		pull_number: number,
		pull_url: `https://github.com/${repo}/pull/${number}`,
		pull_snapshot: {
			number,
			url: `https://github.com/${repo}/pull/${number}`,
			title,
			body: null,
			base_ref: 'main',
			head_ref: branch,
			head_sha: `${(0x9a3f00 + i * 4099).toString(16)}c0ffee1234567890abcdef`,
			linked_issues: []
		},
		state,
		pause_reason: pause,
		branch,
		revision: 3 + i,
		epoch: 1,
		lease_owner: ['implementing', 'dispatching'].includes(state) ? 'worker-1' : null,
		lease_expires_at: ['implementing', 'dispatching'].includes(state) ? later(10) : null,
		next_action_at: state === 'awaiting_ci' ? later(4) : null,
		quota_block_count: state === 'blocked' ? 1 : 0,
		...stamps(15 + i * 40)
	};
});

export const stats = {
	project_count: projects.length,
	schedule_count: 6,
	connector_count: connectors.length,
	active_connector_count: 2,
	total_runs: 148,
	runs_by_state: { queued: 2, dispatching: 1, implementing: 3, awaiting_ci: 4, paused: 1, blocked: 1, failed: 2, completed: 131, canceled: 3 }
};

// ---- decisions -------------------------------------------------------------
const decision = (o) => ({
	run_state: 'paused',
	pull_number: runs[2].pull_number,
	pull_url: runs[2].pull_url,
	run_id: runs[2].id,
	project_id: P1,
	fingerprint: 'fp-' + o.key,
	revision: 1,
	head_sha: runs[2].pull_snapshot.head_sha,
	waiting_since: ago(95),
	observed_at: ago(3),
	...o
});
export const decisions = [
	decision({ key: 'd1', kind: 'run-question', subject_id: 'q-retry-policy', title: 'Should failed webhook deliveries retry with exponential backoff or a fixed interval?', question_state: 'open', actionable: true }),
	decision({ key: 'd2', kind: 'native-hub-question', subject_id: 'hq-ledger-split', title: 'Split the ledger migration into two pull requests?', question_state: 'answered', actionable: true, run_id: runs[1].id, run_state: 'awaiting_ci', pull_number: runs[1].pull_number, pull_url: runs[1].pull_url, waiting_since: ago(240) }),
	decision({ key: 'd3', kind: 'native-workflow', subject_id: 'wf-approve-plan', title: 'Approve the refund idempotency plan', question_state: 'answered', actionable: false, run_id: runs[0].id, run_state: 'implementing', pull_number: runs[0].pull_number, pull_url: runs[0].pull_url, waiting_since: ago(30), head_sha: null }),
	decision({ key: 'd4', kind: 'native-proposal', subject_id: 'prop-sdk-v5', title: 'Accept proposal: pin payment SDK to v5.2 until the conflict is resolved', question_state: 'open', actionable: true, run_id: runs[3].id, run_state: 'blocked', pull_number: runs[3].pull_number, pull_url: runs[3].pull_url, project_id: P2 })
];

// ---- schedule jobs ---------------------------------------------------------
const JOBS = [
	['github.sync_pull_requests', 'success', 2, null],
	['pipeline.dispatch', 'pending', 0, null],
	['pipeline.observe_ci', 'success', 5, null],
	['ai_catalog.refresh_availability', 'failure', 15, 'Upstream returned 503 Service Unavailable'],
	['pipeline.dispatch', 'success', 20, null],
	['github.sync_pull_requests', 'success', 32, null],
	['notifications.send_decision_notices', 'success', 45, null],
	['pipeline.observe_ci', 'pending', 1, null]
];
export const jobs = JOBS.map(([name, status, min, err], i) => ({
	id: uuid(500 + i),
	name,
	schedule_config_id: uuid(600 + (i % 3)),
	dispatcher_run_id: uuid(700 + Math.floor(i / 2)),
	status,
	started_at: ago(min + 1),
	finished_at: status === 'pending' ? null : ago(min),
	payload: { project_id: P1 },
	error_message: err,
	...stamps(min + 1)
}));

// ---- connection tests (project overview) -----------------------------------
const connectionTest = (o) => ({
	project_id: P1,
	project_revision: 4,
	repository: 'example-org/payments-service',
	configuration_current: true,
	cleanup_resolution_available: false,
	test_spec: null,
	phase: 'done',
	cleanup_status: 'completed',
	detail: null,
	evidence: {},
	cancel_requested: false,
	created_at: ago(60),
	deadline: later(30),
	finished_at: ago(50),
	...o
});
const snap = (c) => ({ id: c.id, key: c.key, name: c.name, kind: c.kind, adapter: c.adapter, revision: c.revision, connector_id: c.connector_id });
export const connectionTests = [
	connectionTest({ id: uuid(801), ai_catalog_id: CAT_CODEX, catalog_snapshot: snap(catalogs[0]), status: 'succeeded' }),
	connectionTest({ id: uuid(802), ai_catalog_id: CAT_JULES, catalog_snapshot: snap(catalogs[1]), status: 'failed', detail: 'Session timed out', configuration_current: false })
];

export const me = {
	id: uuid(1),
	firstname: 'Demo',
	lastname: 'User',
	email: 'demo@example.com',
	is_superadmin: true,
	...stamps(50000)
};

// ---- router ----------------------------------------------------------------
const page = (items, q) => {
	const offset = Number(q.get('offset') ?? 0);
	const limit = Number(q.get('limit') ?? items.length);
	return { items: items.slice(offset, offset + limit), total_count: items.length };
};

/** Returns { status, body } or null when the endpoint is not mocked. */
export function handle(method, path, q) {
	if (method === 'POST' && path === '/api/v1/auth/browser/refresh')
		return { status: 200, body: { access_token: 'mock-access-token', token_type: 'bearer' } };
	if (method !== 'GET') return null;
	switch (path) {
		case '/api/health':
			return { status: 200, body: { status: 'ok' } };
		case '/api/health/deep':
			return { status: 200, body: { status: 'ok', scheduler: 'ok', last_tick_at: ago(0.5) } };
		case '/api/v1/users/me':
			return { status: 200, body: me };
		case '/api/v1/dashboard/stats':
			return { status: 200, body: stats };
		case '/api/v1/pipeline-runs': {
			const pid = q.get('project_id');
			return { status: 200, body: page(pid ? runs.filter((r) => r.project_id === pid) : runs, q) };
		}
		case '/api/v1/pipeline-runs/decisions':
			return { status: 200, body: { items: decisions, has_more: false, next_cursor: null } };
		case '/api/v1/schedule_jobs': {
			const status = q.get('status');
			return { status: 200, body: page(status ? jobs.filter((j) => j.status === status) : jobs, q) };
		}
		case '/api/v1/projects':
			return { status: 200, body: page(projects, q) };
		case '/api/v1/connectors':
			return { status: 200, body: page(connectors, q) };
		case '/api/v1/ai-catalogs':
			return { status: 200, body: { items: catalogs } };
	}
	let m = path.match(/^\/api\/v1\/projects\/([^/]+)$/);
	if (m) {
		const p = projects.find((x) => x.id === m[1]);
		return p ? { status: 200, body: p } : { status: 404, body: { detail: 'Project not found' } };
	}
	m = path.match(/^\/api\/v1\/projects\/([^/]+)\/connection-tests$/);
	if (m) return { status: 200, body: connectionTests.filter((t) => t.project_id === m[1]) };
	m = path.match(/^\/api\/v1\/pipeline-runs\/([^/]+)$/);
	if (m) {
		const r = runs.find((x) => x.id === m[1]);
		return r ? { status: 200, body: r } : { status: 404, body: { detail: 'Run not found' } };
	}
	return null;
}

export const PROJECT_DETAIL_ID = P1;
