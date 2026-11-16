import { parseDocument } from 'yaml';
import type { RepoBlob } from '../types';

export interface RepositoryDocument {
	path: string;
	title: string;
	id: string;
	status: string;
	meta: Record<string, unknown>;
	body: string;
	raw: string;
}
export type DocumentSection =
	'documents' | 'proposals' | 'specs' | 'roadmap' | 'handbook' | 'files';
export interface DocumentListing {
	documents: RepositoryDocument[];
	errors: string[];
}

export function safePath(path: string): boolean {
	return (
		!/[\\\0]/.test(path) &&
		!path
			.split('/')
			.some((part) => !part || part === '.' || part === '..' || part.toLowerCase() === '.git')
	);
}

export function parseRepositoryDocument(
	blob: Pick<RepoBlob, 'path' | 'content' | 'encoding'>
): RepositoryDocument {
	if (blob.encoding !== 'utf-8')
		throw new Error(`${blob.path}: Binary file cannot be displayed as Markdown`);
	const raw = blob.content;
	const match = raw.match(/^\uFEFF?---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
	let meta: Record<string, unknown> = {};
	if (match) {
		const parsed = parseDocument(match[1]);
		if (parsed.errors.length)
			throw new Error(`${blob.path}: Invalid YAML metadata: ${parsed.errors[0].message}`);
		const value: unknown = parsed.toJS({ maxAliasCount: 50 });
		if (value !== null && (typeof value !== 'object' || Array.isArray(value)))
			throw new Error(`${blob.path}: Metadata must be a mapping`);
		meta = (value ?? {}) as Record<string, unknown>;
		try {
			JSON.stringify(meta);
		} catch {
			throw new Error(`${blob.path}: Metadata contains cyclic values; inspect Source`);
		}
	}
	const body = match ? raw.slice(match[0].length) : raw;
	const text = (key: string) => (typeof meta[key] === 'string' ? (meta[key] as string) : '');
	return {
		path: blob.path,
		title:
			text('title') ||
			body.match(/^#\s+(.+)$/m)?.[1]?.trim() ||
			blob.path.split('/').at(-1) ||
			blob.path,
		id: text('id'),
		status: text('status'),
		meta,
		body,
		raw
	};
}

export function resolveRepositoryLink(
	origin: string,
	href: string
): { path: string; fragment: string; directory: boolean } | null {
	if (/^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(href)) return null;
	try {
		const hash = href.indexOf('#');
		const pathname = decodeURIComponent(hash < 0 ? href : href.slice(0, hash));
		const fragment = hash < 0 ? '' : decodeURIComponent(href.slice(hash + 1));
		if (/[\\\0?]/.test(pathname)) return null;
		const parts = pathname
			? pathname.startsWith('/')
				? []
				: origin.split('/').slice(0, -1)
			: origin.split('/');
		for (const part of pathname.split('/')) {
			if (!part || part === '.') continue;
			if (part === '..') {
				if (!parts.length) return null;
				parts.pop();
			} else parts.push(part);
		}
		const path = parts.join('/');
		const directory = /(?:\/|^\.\.?|\/\.\.?)$/.test(pathname);
		return safePath(path) || (directory && path === '') ? { path, fragment, directory } : null;
	} catch {
		return null;
	}
}

export const headingSlug = (text: string) =>
	text
		.toLowerCase()
		.trim()
		.replace(/[^\p{L}\p{N}\s_-]/gu, '')
		.replace(/\s+/g, '-') || 'section';
