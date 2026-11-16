import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, expect, test, vi } from 'vitest';
import { tick } from 'svelte';
import NativeSddViewer from './NativeSddViewer.svelte';
import { sourceFor, blob } from './fixtures';
vi.mock('./diagrams', () => ({ diagrams: () => ({ update() {}, destroy() {} }) }));
afterEach(cleanup);

const doc = 'docs/guide.md';
const signal = () => expect.any(AbortSignal);

test('native sections search, clear search, render source and follow same-ref relative links', async () => {
	const source = sourceFor({
		[doc]:
			'---\nid: CAP-DOC-guide\ntitle: Guide\nstatus: active\n---\n# Guide\n\n[Next](next.md#part)',
		'docs/next.md': '# Next\n\n## Part'
	});
	const selected = vi.fn();
	render(NativeSddViewer, { dataSource: source, branch: 'feature', onselectpath: selected });
	expect(screen.queryByRole('button', { name: 'Shared' })).toBeNull();
	expect(screen.queryByRole('button', { name: /theme/i })).toBeNull();
	await fireEvent.input(await screen.findByLabelText('Find documents'), {
		target: { value: 'missing' }
	});
	expect(await screen.findByText('No matching documents.')).toBeTruthy();
	await fireEvent.click(screen.getByRole('button', { name: 'Clear search' }));
	await fireEvent.click(await screen.findByRole('button', { name: 'Guide' }));
	await screen.findByRole('heading', { name: 'Guide', level: 1 });
	expect(selected).toHaveBeenLastCalledWith(doc);
	await fireEvent.click(screen.getByRole('tab', { name: 'Source' }));
	expect(await screen.findByText(/title: Guide/)).toBeTruthy();
	await fireEvent.click(screen.getByRole('tab', { name: 'Preview' }));
	await fireEvent.click(await screen.findByRole('link', { name: 'Next' }));
	await screen.findByRole('heading', { name: 'Part' });
	expect(source.blob).toHaveBeenCalledWith('docs/next.md', 'feature', signal());
	expect(selected).toHaveBeenLastCalledWith('docs/next.md');
});

test('binary addressed files explain content and return to their directory', async () => {
	const source = sourceFor({ 'assets/picture.png': 'AAAA' });
	const original = source.blob;
	source.blob = vi.fn(async (path, ref, abort) => ({
		...(await original(path, ref, abort)),
		encoding: 'base64' as const
	}));
	render(NativeSddViewer, {
		dataSource: source,
		branch: 'feature',
		initialPath: 'assets/picture.png',
		onselectpath: vi.fn()
	});
	expect(await screen.findByText(/Binary file cannot be displayed/)).toBeTruthy();
	await fireEvent.click(screen.getByRole('button', { name: 'Back to files' }));
	expect(await screen.findByRole('button', { name: 'picture.png' })).toBeTruthy();
	expect(source.tree).toHaveBeenCalledWith('assets', 'feature', signal());
});

test('failed file reads expose Retry and do not publish a selected unit', async () => {
	const source = sourceFor({ [doc]: '# Guide' }),
		selected = vi.fn();
	const original = source.blob;
	let refused = true;
	source.blob = vi.fn(async (path, ref, abort) => {
		if (refused) throw new Error('Access denied');
		return original(path, ref, abort);
	});
	render(NativeSddViewer, {
		dataSource: source,
		branch: 'feature',
		initialPath: doc,
		onselectpath: selected
	});
	expect(await screen.findByRole('alert')).toHaveProperty(
		'textContent',
		expect.stringContaining('Access denied')
	);
	expect(selected).not.toHaveBeenCalledWith(doc);
	refused = false;
	await fireEvent.click(screen.getByRole('button', { name: 'Retry document' }));
	await screen.findByRole('heading', { name: 'Guide', level: 1 });
	expect(selected).toHaveBeenLastCalledWith(doc);
});

test('changing source and branch discards an older pending read and its selection callback', async () => {
	const source = sourceFor({ [doc]: '# Old' });
	let finish!: (value: ReturnType<typeof blob>) => void;
	source.blob = vi.fn(
		() =>
			new Promise<ReturnType<typeof blob>>((resolve) => {
				finish = resolve;
			})
	);
	const selected = vi.fn();
	const view = render(NativeSddViewer, {
		dataSource: source,
		branch: 'old',
		initialPath: doc,
		onselectpath: selected
	});
	await waitFor(() => expect(finish).toBeTypeOf('function'));
	const next = sourceFor({ 'docs/new.md': '# New' });
	await view.rerender({
		dataSource: next,
		branch: 'new',
		initialPath: 'docs/new.md',
		onselectpath: selected
	});
	await screen.findByRole('heading', { name: 'New', level: 1 });
	finish(blob(doc, '# Old'));
	await tick();
	await tick();
	expect(screen.queryByRole('heading', { name: 'Old', level: 1 })).toBeNull();
	expect(selected).toHaveBeenLastCalledWith('docs/new.md');
	expect(next.blob).toHaveBeenCalledWith('docs/new.md', 'new', signal());
});

test('handbook release and language changes load the selected language README and relative page', async () => {
	const source = sourceFor({
		'handbook/manifest.json': '{"tag":"v1.2.0","langs":["en","ko"]}',
		'handbook/en/README.md': '# English',
		'handbook/ko/README.md': '# Korean\n\n[Chapter](chapter.md)',
		'handbook/ko/chapter.md': '# Chapter'
	});
	render(NativeSddViewer, { dataSource: source, branch: 'feature', onselectpath: vi.fn() });
	await fireEvent.click(screen.getByRole('button', { name: 'Handbook' }));
	expect(await screen.findByText('Handbook release: v1.2.0')).toBeTruthy();
	await screen.findByRole('heading', { name: 'English', level: 1 });
	await fireEvent.change(screen.getByLabelText('Handbook language'), { target: { value: 'ko' } });
	await screen.findByRole('heading', { name: 'Korean', level: 1 });
	await fireEvent.click(screen.getByRole('link', { name: 'Chapter' }));
	await screen.findByRole('heading', { name: 'Chapter', level: 1 });
	expect(source.blob).toHaveBeenCalledWith('handbook/ko/chapter.md', 'feature', signal());
});

test('ID references reject ambiguity rather than selecting the first document', async () => {
	const source = sourceFor({
		[doc]: '# Guide\n\n`CAP-DOC-duplicate`',
		'docs/a.md': '---\nid: CAP-DOC-duplicate\n---\n# A',
		'docs/b.md': '---\nid: CAP-DOC-duplicate\n---\n# B'
	});
	const selected = vi.fn();
	render(NativeSddViewer, {
		dataSource: source,
		branch: 'feature',
		initialPath: doc,
		onselectpath: selected
	});
	await fireEvent.click(await screen.findByRole('link', { name: 'CAP-DOC-duplicate' }));
	expect(await screen.findByRole('alert')).toHaveProperty(
		'textContent',
		expect.stringContaining('ambiguous')
	);
	expect(selected).not.toHaveBeenCalledWith('docs/a.md');
	expect(selected).not.toHaveBeenCalledWith('docs/b.md');
});
