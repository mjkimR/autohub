import type { RepositoryDataSource } from '../data-source';
import { listChildren } from './discovery';

export interface HandbookManifest {
	tag: string;
	langs: string[];
}
export async function loadHandbook(
	source: RepositoryDataSource,
	ref: string,
	signal: AbortSignal
): Promise<HandbookManifest | null> {
	const roots = await listChildren(source, '', ref, signal);
	if (!roots.some((item) => item.type === 'dir' && item.path === 'handbook')) return null;
	const children = await listChildren(source, 'handbook', ref, signal);
	if (!children.some((item) => item.type === 'file' && item.path === 'handbook/manifest.json'))
		return null;
	const blob = await source.blob('handbook/manifest.json', ref, signal);
	if (blob.encoding !== 'utf-8') throw new Error('handbook/manifest.json must be UTF-8');
	const manifest: unknown = JSON.parse(blob.content);
	if (
		!manifest ||
		typeof manifest !== 'object' ||
		!('tag' in manifest) ||
		typeof manifest.tag !== 'string' ||
		!('langs' in manifest) ||
		!Array.isArray(manifest.langs) ||
		!manifest.langs.every(
			(lang: unknown) => typeof lang === 'string' && /^[a-zA-Z0-9_-]+$/.test(lang)
		) ||
		!manifest.langs.includes('en')
	)
		throw new Error('handbook/manifest.json requires tag and langs including en');
	return { tag: manifest.tag, langs: [...new Set(manifest.langs)] as string[] };
}
