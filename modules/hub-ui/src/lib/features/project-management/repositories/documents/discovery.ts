import type { RepositoryDataSource } from '../data-source';
import type { RepoItem } from '../types';
import {
	parseRepositoryDocument,
	safePath,
	type DocumentListing,
	type DocumentSection,
	type RepositoryDocument
} from './model';

export const isMilestonePath = (path: string) =>
	safePath(path) && /^docs\/(?:packages\/[^/]+\/)?roadmap\/(?:_archive\/)?MS-[^/]+\.md$/.test(path);
export const isProposalPath = (path: string) =>
	/^docs\/proposals\/PROP-[^/]+\/proposal\.md$/.test(path);
const message = (error: unknown) => (error instanceof Error ? error.message : String(error));

export async function listChildren(
	source: RepositoryDataSource,
	path: string,
	ref: string,
	signal: AbortSignal
): Promise<RepoItem[]> {
	const result = await source.tree(path, ref, signal);
	const prefix = path ? `${path}/` : '';
	return (result.items ?? []).filter(
		(item) =>
			safePath(item.path) &&
			item.path.startsWith(prefix) &&
			!item.path.slice(prefix.length).includes('/')
	);
}

/** At most six repository requests run at once; optional roots come from successful parent listings. */
export async function discoverDocuments(
	source: RepositoryDataSource,
	ref: string,
	section: DocumentSection,
	signal: AbortSignal,
	includeProposalFiles = false
): Promise<DocumentListing> {
	const documents: RepositoryDocument[] = [],
		errors: string[] = [];
	const roots = await listChildren(source, '', ref, signal);
	const jobs: { path: string; file: boolean }[] = roots
		.filter((item) => item.type === 'dir' && item.path === (section === 'specs' ? 'specs' : 'docs'))
		.map((item) => ({ path: item.path, file: false }));
	const seen = new Set<string>();
	const descend = (path: string) => {
		if (section === 'proposals')
			return path === 'docs/proposals' || /^docs\/proposals\/PROP-[^/]+$/.test(path);
		if (section === 'roadmap')
			return /^docs\/(?:roadmap(?:\/_archive)?|proposals(?:\/PROP-[^/]+)?|packages(?:\/[^/]+(?:\/roadmap(?:\/_archive)?)?)?)$/.test(
				path
			);
		return section === 'specs' || includeProposalFiles || !path.startsWith('docs/proposals');
	};
	const include = (path: string) =>
		section === 'proposals'
			? isProposalPath(path)
			: section === 'roadmap'
				? isMilestonePath(path) || isProposalPath(path)
				: path.endsWith('.md');
	while (jobs.length && !signal.aborted) {
		const batch = jobs.splice(0, 6).filter((job) => {
			if (seen.has(job.path)) return false;
			seen.add(job.path);
			return true;
		});
		await Promise.all(
			batch.map(async (job) => {
				try {
					if (job.file)
						documents.push(parseRepositoryDocument(await source.blob(job.path, ref, signal)));
					else
						for (const item of await listChildren(source, job.path, ref, signal)) {
							if (item.type === 'dir' && descend(item.path))
								jobs.push({ path: item.path, file: false });
							else if (item.type === 'file' && include(item.path))
								jobs.push({ path: item.path, file: true });
						}
				} catch (error) {
					if (!signal.aborted) errors.push(`${job.path}: ${message(error)}`);
				}
			})
		);
	}
	return { documents: documents.sort((a, b) => a.path.localeCompare(b.path)), errors };
}

export function milestoneRows(documents: RepositoryDocument[]) {
	const milestones = documents.filter((doc) => isMilestonePath(doc.path));
	const statuses = new Map(milestones.map((doc) => [doc.id, doc.status]));
	return milestones.map((document) => {
		const dependencies = Array.isArray(document.meta.depends_on)
			? document.meta.depends_on.filter((id): id is string => typeof id === 'string')
			: [];
		return {
			document,
			dependencies: dependencies.map((id) => ({ id, status: statuses.get(id) || 'unknown' })),
			members: documents.filter(
				(doc) =>
					isProposalPath(doc.path) &&
					doc.meta.milestone === document.id &&
					doc.status !== 'rejected'
			)
		};
	});
}
