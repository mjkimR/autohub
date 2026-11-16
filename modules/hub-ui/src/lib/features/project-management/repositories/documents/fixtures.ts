import { vi } from 'vitest';
import type { RepositoryDataSource } from '../data-source';
import type { RepoBlob } from '../types';

export const blob = (path: string, content: string): RepoBlob => ({
	path,
	ref: 'feature',
	size: content.length,
	sha: 'sha',
	content,
	encoding: 'utf-8'
});
export function sourceFor(documents: Record<string, string>): RepositoryDataSource {
	const entries = new Map<
		string,
		Map<string, { name: string; path: string; type: 'dir' | 'file'; size: number; sha: string }>
	>();
	for (const path of Object.keys(documents)) {
		const parts = path.split('/');
		parts.forEach((name, i) => {
			const parent = parts.slice(0, i).join('/'),
				child = parts.slice(0, i + 1).join('/');
			if (!entries.has(parent)) entries.set(parent, new Map());
			entries.get(parent)!.set(child, {
				name,
				path: child,
				type: i === parts.length - 1 ? 'file' : 'dir',
				size: 1,
				sha: 'sha'
			});
		});
	}
	return {
		info: async () => ({
			repository: 'owner/repo',
			default_branch: 'main',
			branches: ['main', 'feature'],
			branches_complete: true
		}),
		refs: async () => ({ default_branch: 'main', branches: ['main', 'feature'] }),
		tree: vi.fn(async (path, ref) => ({
			path,
			ref,
			items: [...(entries.get(path)?.values() || [])]
		})),
		blob: vi.fn(async (path) => {
			if (!(path in documents)) throw new Error('Read refused');
			return blob(path, documents[path]);
		})
	};
}
