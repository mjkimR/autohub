import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { parseDocument } from 'yaml';
import { normalizeTree, type RepositoryDataSource } from './repository';

export interface RepositoryDocument {
	path: string;
	meta: Record<string, any>;
	body: string;
	raw: string;
	title: string;
}
export interface Heading {
	id: string;
	title: string;
	level: number;
}
export interface RenderedDocument {
	html: string;
	headings: Heading[];
}
export const documentAnchor = (path: string) => `doc-${encodeURIComponent(path)}`;
export const headingSlug = (title: string) =>
	title
		.toLowerCase()
		.trim()
		.replace(/[^\p{L}\p{N}\s_-]/gu, '')
		.replace(/\s+/g, '-');

export function parseBlob(path: string, content: string, encoding: string): RepositoryDocument {
	const raw =
		encoding === 'utf-8'
			? content
			: encoding === 'base64'
				? new TextDecoder('utf-8', { fatal: true }).decode(
						Uint8Array.from(atob(content.replace(/\s/g, '')), (c) => c.charCodeAt(0))
					)
				: (() => {
						throw new Error(`Unsupported encoding: ${encoding}`);
					})();
	const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
	let meta: Record<string, any> = {};
	if (match) {
		const yaml = parseDocument(match[1]);
		if (yaml.errors.length) throw new Error(yaml.errors[0].message);
		const value = yaml.toJS({ maxAliasCount: 100 });
		if (value && typeof value === 'object' && !Array.isArray(value)) meta = value;
	}
	const body = match ? raw.slice(match[0].length) : raw;
	const title =
		typeof meta.title === 'string'
			? meta.title
			: (body.match(/^#\s+(.+)$/m)?.[1] ?? path.split('/').at(-1)!);
	return { path, meta, body, raw, title };
}

// One pool serves directory discovery and blob reads, including recursive trees.
export async function indexDocuments(
	source: RepositoryDataSource,
	ref: string,
	signal: AbortSignal
) {
	type Job = { path: string; kind: 'tree' | 'blob' };
	const jobs: Job[] = [
		{ path: 'docs', kind: 'tree' },
		{ path: 'specs', kind: 'tree' }
	];
	const seen = new Set<string>();
	const documents: RepositoryDocument[] = [];
	const errors: string[] = [];
	while (jobs.length && !signal.aborted) {
		const batch = jobs.splice(0, 6);
		await Promise.all(
			batch.map(async (job) => {
				const key = `${job.kind}:${job.path}`;
				if (seen.has(key)) return;
				seen.add(key);
				try {
					if (job.kind === 'tree') {
						const items = normalizeTree(await source.tree(job.path, ref, signal));
						for (const item of items) {
							// Hosts must return descendants; reject cycles and out-of-scope paths.
							if (
								!item.path.startsWith(`${job.path}/`) ||
								item.path.split('/').some((p) => p === '..' || p === '.')
							)
								continue;
							if (item.type === 'tree') jobs.push({ path: item.path, kind: 'tree' });
							else if (item.name.endsWith('.md')) jobs.push({ path: item.path, kind: 'blob' });
						}
					} else {
						const blob = await source.blob(job.path, ref, signal);
						documents.push(parseBlob(job.path, blob.content, blob.encoding));
					}
				} catch (error) {
					if (!signal.aborted)
						errors.push(`${job.path}: ${error instanceof Error ? error.message : error}`);
				}
			})
		);
	}
	return {
		documents: documents.sort((a, b) => a.path.localeCompare(b.path, undefined, { numeric: true })),
		errors
	};
}

export function idIndex(documents: RepositoryDocument[]) {
	const index = new Map<string, RepositoryDocument>();
	const duplicates = new Set<string>();
	for (const doc of documents) {
		if (typeof doc.meta.id !== 'string') continue;
		if (index.has(doc.meta.id)) duplicates.add(doc.meta.id);
		else index.set(doc.meta.id, doc);
	}
	for (const id of duplicates) index.delete(id);
	return index;
}

export function resolvePath(origin: string, href: string) {
	if (/^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(href)) return null;
	const [pathname, rawFragment = ''] = href.split('#');
	let fragment: string;
	try {
		fragment = decodeURIComponent(rawFragment);
	} catch {
		return null;
	}
	let decoded: string;
	try {
		decoded = decodeURIComponent(pathname);
	} catch {
		return null;
	}
	const parts = decoded
		? decoded.startsWith('/')
			? []
			: origin.split('/').slice(0, -1)
		: origin.split('/');
	for (const part of decoded.split('/')) {
		if (!part || part === '.') continue;
		if (part === '..') {
			if (!parts.length) return null;
			parts.pop();
		} else parts.push(part);
	}
	return { path: parts.join('/'), fragment };
}

export function renderDocument(
	doc: RepositoryDocument,
	documents: RepositoryDocument[]
): RenderedDocument {
	const wrapper = document.createElement('div');
	wrapper.innerHTML = DOMPurify.sanitize(
		marked.parse(doc.body, { gfm: true, breaks: true }) as string,
		{ USE_PROFILES: { html: true } }
	);
	const headings: Heading[] = [];
	const counts = new Map<string, number>();
	for (const node of wrapper.querySelectorAll('h1,h2,h3,h4,h5,h6')) {
		const rawTitle = node.textContent ?? '';
		const selfPrefix = `[${doc.meta.id}]`;
		const title =
			node.tagName === 'H1' && typeof doc.meta.id === 'string' && rawTitle.startsWith(selfPrefix)
				? rawTitle.slice(selfPrefix.length).trim()
				: rawTitle;
		if (title !== rawTitle) node.textContent = title;
		const slug = headingSlug(rawTitle) || 'section';
		const n = counts.get(slug) ?? 0;
		counts.set(slug, n + 1);
		const id = `${documentAnchor(doc.path)}--${slug}${n ? `-${n}` : ''}`;
		node.id = id;
		headings.push({ id, title, level: Number(node.tagName.slice(1)) });
	}
	const byId = idIndex(documents);
	function linkNode(node: HTMLElement, target: RepositoryDocument, fragment = '') {
		node.setAttribute('href', `#${documentAnchor(target.path)}${fragment ? `--${fragment}` : ''}`);
		node.dataset.docPath = target.path;
		node.dataset.fragment = fragment;
	}
	for (const a of wrapper.querySelectorAll<HTMLAnchorElement>('a[href]')) {
		const href = a.getAttribute('href')!;
		const byReference = byId.get(href) ?? byId.get(href.replace(/^\[|\]$/g, ''));
		const resolved = resolvePath(doc.path, href);
		const target = byReference ?? (resolved && documents.find((d) => d.path === resolved.path));
		if (target) linkNode(a, target, byReference ? '' : resolved!.fragment);
	}
	// ID references occur both as [ID] prose and exact inline code; fenced code is untouched.
	const walker = document.createTreeWalker(wrapper, NodeFilter.SHOW_TEXT);
	const nodes: Text[] = [];
	while (walker.nextNode()) nodes.push(walker.currentNode as Text);
	for (const node of nodes) {
		const parent = node.parentElement;
		if (!parent || parent.closest('a,pre,h1,h2,h3,h4,h5,h6')) continue;
		const value = node.textContent ?? '';
		const exactCode = parent.tagName === 'CODE' && byId.has(value);
		const pattern = exactCode
			? /^(.*)$/g
			: /\[((?:CAP|US|ARCH|ADR|PROP|SPEC|PLAN|TASKS|REC|MAT|PADR)-[A-Za-z0-9][A-Za-z0-9-]*)\]/g;
		let match: RegExpExecArray | null;
		let cursor = 0;
		const replacement = document.createDocumentFragment();
		while ((match = pattern.exec(value))) {
			const target = byId.get(match[1]);
			if (!target) continue;
			replacement.append(value.slice(cursor, match.index));
			const a = document.createElement('a');
			a.textContent = match[0];
			linkNode(a, target);
			replacement.append(a);
			cursor = match.index + match[0].length;
		}
		if (cursor) {
			replacement.append(value.slice(cursor));
			node.replaceWith(replacement);
		}
	}
	return { html: wrapper.innerHTML, headings };
}

export function bookGroup(doc: RepositoryDocument) {
	const path = doc.path.replace(/^docs\/packages\/[^/]+\//, 'docs/');
	if (
		!path.startsWith('docs/') ||
		/\/(proposals|materials)\//.test(path) ||
		/\/README\.md$/i.test(path)
	)
		return null;
	if (path === 'docs/glossary.md') return '용어';
	for (const [directory, title] of [
		['architecture', '아키텍처'],
		['capabilities', '역량'],
		['stories', '사용자 스토리'],
		['decisions', '의사결정'],
		['development', '개발 가이드']
	]) {
		if (path.startsWith(`docs/${directory}/`)) return title;
	}
	return '개요';
}
export const bookGroups = [
	'개요',
	'아키텍처',
	'역량',
	'사용자 스토리',
	'용어',
	'의사결정',
	'개발 가이드'
];
export const namespaceOf = (doc: RepositoryDocument) =>
	doc.path.match(/^docs\/packages\/([^/]+)\//)?.[1] ?? String(doc.meta.namespace ?? 'global');

// Markdown list tokens exclude checkbox examples inside fenced code.
export function taskProgress(body: string) {
	let total = 0,
		checked = 0;
	function visit(tokens: any[]) {
		for (const token of tokens) {
			if (token.type === 'list')
				for (const item of token.items) {
					if (item.task) {
						total++;
						if (item.checked) checked++;
					}
					visit(item.tokens ?? []);
				}
			else if (token.type === 'blockquote') visit(token.tokens ?? []);
		}
	}
	visit(marked.lexer(body));
	return { total, checked };
}
