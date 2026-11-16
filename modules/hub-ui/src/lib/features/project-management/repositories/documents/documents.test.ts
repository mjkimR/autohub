import { expect, test, vi } from 'vitest';
import { blob, sourceFor } from './fixtures';
import { parseRepositoryDocument, resolveRepositoryLink } from './model';
import { renderRepositoryMarkdown } from './render';
import { discoverDocuments, milestoneRows } from './discovery';
import { loadHandbook } from './handbook';

test('metadata supports YAML arrays and exact source while binary, duplicate keys and scalar frontmatter fail', () => {
	const raw = '---\r\nid: ADR-one\r\ntitle: A choice\r\nsupersedes: [ADR-old]\r\n---\r\n# Heading';
	const doc = parseRepositoryDocument(blob('docs/a.md', raw));
	expect(doc).toMatchObject({ id: 'ADR-one', title: 'A choice', body: '# Heading', raw });
	expect(doc.meta.supersedes).toEqual(['ADR-old']);
	expect(() => parseRepositoryDocument({ ...blob('a.md', 'AAAA'), encoding: 'base64' })).toThrow(
		'Binary'
	);
	expect(() => parseRepositoryDocument(blob('a.md', '---\nid: A\nid: B\n---\ntext'))).toThrow(
		'Invalid YAML'
	);
	expect(() => parseRepositoryDocument(blob('a.md', '---\n- a\n---\ntext'))).toThrow('mapping');
});

test.each([
	['../b.md#hello', 'docs/b.md', 'hello'],
	['#heading', 'docs/sub/a.md', 'heading'],
	['/README.md', 'README.md', ''],
	['%2e%2e/b.md', 'docs/b.md', '']
])('repository link %s resolves within repository', (href, path, fragment) =>
	expect(resolveRepositoryLink('docs/sub/a.md', href)).toEqual({ path, fragment })
);
test.each([
	'../../../escape.md',
	'javascript:alert(1)',
	'//host/a.md',
	'%ZZ',
	'../%2egit/config',
	'..\\escape.md'
])('unsafe or external link %s is not a repository path', (href) =>
	expect(resolveRepositoryLink('docs/a.md', href)).toBeNull()
);

test('Markdown sanitization removes active content and forged routing attributes and creates headings and safe links', () => {
	const doc = parseRepositoryDocument(
		blob(
			'docs/a.md',
			'# Title\n\n## Same\n\n## Same\n\n[relative](b.md#part) [external](https://example.com) [bad](javascript:alert(1))\n\n`CAP-DOC-example`\n\n<script>alert(1)</script><img src=x onerror=alert(2)><a data-repository-path="secrets" href="https://example.com">forged</a>'
		)
	);
	const result = renderRepositoryMarkdown(doc);
	const root = document.createElement('div');
	root.innerHTML = result.html;
	expect(root.querySelector('script,[onerror]')).toBeNull();
	expect(result.headings.map((h) => h.id)).toEqual(['title', 'same', 'same-1']);
	expect(root.querySelector('a[data-repository-path]')?.getAttribute('data-repository-path')).toBe(
		'docs/b.md'
	);
	expect(root.querySelector('a[data-document-id]')?.textContent).toBe('CAP-DOC-example');
	expect(root.textContent).toContain('forged');
	expect(root.querySelector('a[data-repository-path="secrets"]')).toBeNull();
	expect(root.querySelector('a[target="_blank"]')?.getAttribute('rel')).toBe('noopener noreferrer');
	expect(result.html).not.toContain('javascript:');
});

test('document discovery preserves ref and reports partial failures without fabricated documents', async () => {
	const source = sourceFor({
		'docs/good.md': '# Good',
		'docs/bad.md': '# Bad',
		'specs/2026-11/a/spec.md': '# Spec'
	});
	const original = source.blob;
	source.blob = vi.fn(async (path, ref, signal) => {
		if (path.endsWith('bad.md')) throw new Error('Denied');
		return original(path, ref, signal);
	});
	const signal = new AbortController().signal;
	const result = await discoverDocuments(source, 'feature', 'documents', signal);
	expect(result.documents.map((d) => d.title)).toEqual(['Good']);
	expect(result.errors).toEqual(['docs/bad.md: Denied']);
	expect(source.tree).toHaveBeenCalledWith('docs', 'feature', signal);
	expect(source.blob).toHaveBeenCalledWith('docs/good.md', 'feature', signal);
});

test('missing optional roots are empty but a refused root read rejects', async () => {
	const source = sourceFor({ 'README.md': '# Root' });
	expect(await discoverDocuments(source, 'feature', 'specs', new AbortController().signal)).toEqual(
		{ documents: [], errors: [] }
	);
	source.tree = async () => {
		throw new Error('Forbidden');
	};
	await expect(
		discoverDocuments(source, 'feature', 'documents', new AbortController().signal)
	).rejects.toThrow('Forbidden');
});

test('roadmap membership uses direct proposal anchors and includes package archives', async () => {
	const source = sourceFor({
		'docs/packages/sdk/roadmap/_archive/MS-old.md':
			'---\nid: MS-old\ntitle: Old\ndepends_on: [MS-missing]\n---\n# Old',
		'docs/proposals/PROP-a/proposal.md':
			'---\nid: PROP-a\nstatus: accepted\nmilestone: MS-old\n---\n# Member',
		'specs/2026-11/a/spec.md': '---\nid: SPEC-a\nmilestone: MS-old\n---\n# Not a member'
	});
	const result = await discoverDocuments(
		source,
		'feature',
		'roadmap',
		new AbortController().signal
	);
	const [row] = milestoneRows(result.documents);
	expect(result.errors).toEqual([]);
	expect(row.dependencies).toEqual([{ id: 'MS-missing', status: 'unknown' }]);
	expect(row.members.map((d) => d.id)).toEqual(['PROP-a']);
});

test('handbook distinguishes absent, invalid and refused manifest', async () => {
	const signal = new AbortController().signal;
	expect(await loadHandbook(sourceFor({}), 'feature', signal)).toBeNull();
	const source = sourceFor({ 'handbook/manifest.json': '{"tag":"v1.0.0","langs":["en","ko"]}' });
	expect(await loadHandbook(source, 'feature', signal)).toEqual({
		tag: 'v1.0.0',
		langs: ['en', 'ko']
	});
	source.blob = async () => blob('handbook/manifest.json', '{"tag":"v1","langs":["../bad"]}');
	await expect(loadHandbook(source, 'feature', signal)).rejects.toThrow('including en');
	source.blob = async () => {
		throw new Error('Forbidden');
	};
	await expect(loadHandbook(source, 'feature', signal)).rejects.toThrow('Forbidden');
});
