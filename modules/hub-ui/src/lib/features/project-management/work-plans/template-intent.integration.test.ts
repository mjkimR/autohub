import { beforeEach, expect, test, vi } from 'vitest';
import { TemplateIntent, freshPreview, type Template } from './template-intent.svelte';
const { api } = vi.hoisted(() => ({
	api: { POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), GET: vi.fn() }
}));
vi.mock('$lib/api', () => ({ api }));
beforeEach(() => {
	sessionStorage.clear();
	vi.resetAllMocks();
});
const template = {
	id: 'template',
	name: 'Routine',
	revision: 1,
	digest: 'a'.repeat(64),
	definition: {
		title: 'Plan',
		description: 'Scope',
		base_branch: 'main',
		items: [
			{
				key: 'aaaaaaaaaaaaaaaaaaaaaaaa-one',
				title: 'A',
				description: 'A',
				acceptance: 'A',
				depends_on: []
			},
			{
				key: 'aaaaaaaaaaaaaaaaaaaaaaaa-two',
				title: 'B',
				description: 'B',
				acceptance: 'B',
				depends_on: ['aaaaaaaaaaaaaaaaaaaaaaaa-one']
			}
		]
	}
} as Template;
const pending = () => ({
	op: 'create' as const,
	target: null,
	body: { request_id: crypto.randomUUID(), name: 'Routine', definition: template.definition }
});
test('fresh keys include full request and ordinal when source stems collide', () => {
	const a = freshPreview(template),
		b = freshPreview(template);
	expect(a.state).toBe('draft');
	expect(a.items?.[0].key).not.toBe(b.items?.[0].key);
	expect(a.items?.[0].key).not.toBe(a.items?.[1].key);
	expect(a.items?.[1].depends_on).toEqual([a.items?.[0].key]);
	expect(a.items?.[0].key.length).toBeLessThanOrEqual(60);
	expect(a.depends_on).toEqual([]);
	expect(a.group_key).toBeNull();
});
test('unknown original survives remount and dismissal; exact retry preserves identity', async () => {
	api.POST.mockRejectedValueOnce(new Error('response lost'));
	const first = new TemplateIntent('project', 'account');
	const request = pending();
	await first.submit(request);
	expect(first.locked).toBe(true);
	first.dismiss();
	expect(first.pending).toEqual(request);
	const restored = new TemplateIntent('project', 'account');
	expect(restored.pending).toEqual(request);
	expect(new TemplateIntent('other', 'account').pending).toBeNull();
	expect(new TemplateIntent('project', 'other').pending).toBeNull();
	api.POST.mockResolvedValue({
		data: {
			record_state: 'recorded',
			operation: 'create',
			request_id: request.body.request_id,
			original_template: template,
			current_template: template
		}
	});
	await restored.retry();
	expect(api.POST.mock.calls[1][1].body).toEqual(request.body);
	expect(restored.state).toBe('recorded');
});
test.each([401, 403, 404, 409, 422, 500])(
	'ambiguous status %i retains original intent',
	async (status) => {
		api.POST.mockResolvedValue({ error: { detail: 'unavailable' }, response: { status } });
		const intent = new TemplateIntent('project', 'account');
		await intent.submit(pending());
		expect(intent.state).toBe('unknown');
		expect(intent.locked).toBe(true);
	}
);
test('authoritative owner refusal permits explicit correction', async () => {
	api.POST.mockResolvedValue({
		error: { code: 'TEMPLATE_REVISION_CHANGED' },
		response: { status: 409 }
	});
	const intent = new TemplateIntent('p', 'a');
	await intent.submit(pending());
	expect(intent.state).toBe('refused');
	intent.dismiss();
	expect(intent.pending).toBeNull();
});
test('exact read unknown stays uncertain; recorded read separates historical/current revisions', async () => {
	const intent = new TemplateIntent('p', 'a');
	api.POST.mockRejectedValue(new Error('lost'));
	const request = pending();
	await intent.submit(request);
	api.GET.mockResolvedValueOnce({ data: { record_state: 'unknown' } });
	await intent.check();
	expect(intent.state).toBe('unknown');
	api.GET.mockResolvedValueOnce({ error: { detail: '401' } });
	await intent.check();
	expect(intent.locked).toBe(true);
	api.GET.mockResolvedValue({
		data: {
			record_state: 'recorded',
			operation: 'create',
			request_id: request.body.request_id,
			original_template: template,
			current_template: { ...template, revision: 3, deleted: true }
		}
	});
	await intent.check();
	expect(intent.outcome?.original_template?.revision).toBe(1);
	expect(intent.outcome?.current_template?.revision).toBe(3);
});
test('fresh lost request does not retain preceding receipt display', async () => {
	const intent = new TemplateIntent('p', 'a');
	api.POST.mockResolvedValueOnce({ data: { record_state: 'recorded' } });
	await intent.submit(pending());
	expect(intent.outcome).not.toBeNull();
	api.POST.mockRejectedValue(new Error('lost'));
	await intent.submit(pending());
	expect(intent.outcome).toBeNull();
	expect(intent.state).toBe('unknown');
});
test('denied storage prevents submission before a recoverable identity can be saved', async () => {
	const intent = new TemplateIntent('p', 'a');
	const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
		throw new Error('denied');
	});
	await intent.submit(pending());
	expect(api.POST).not.toHaveBeenCalled();
	expect(intent.storageError).toBe(true);
	spy.mockRestore();
});
