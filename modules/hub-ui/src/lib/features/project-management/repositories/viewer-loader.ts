import type { CustomViewerConfig, InstalledViewer } from './types';

const manifestUrl = '/plugins/repository-viewers/manifest.json';
let registryRequest: Promise<InstalledViewer[]> | null = null;
const pending = new Map<string, Promise<InstalledViewer>>();

export function readViewerRegistry(): Promise<InstalledViewer[]> {
	if (registryRequest) return registryRequest;
	const promise = (async () => {
		const response = await fetch(manifestUrl, { cache: 'no-store' });
		if (response.status === 404) return [];
		if (!response.ok) throw new Error('Could not load repository viewers');
		const manifest: unknown = await response.json();
		if (
			!manifest ||
			typeof manifest !== 'object' ||
			!('viewers' in manifest) ||
			!Array.isArray(manifest.viewers)
		) {
			throw new Error('Invalid repository viewer registry');
		}
		const ids = new Set<string>(),
			tags = new Set<string>();
		const viewers: InstalledViewer[] = [];
		for (const value of manifest.viewers) {
			if (!value || typeof value !== 'object')
				throw new Error('Invalid repository viewer registry entry');
			const viewer = value as Record<string, unknown>;
			if (
				typeof viewer.id !== 'string' ||
				!/^[a-z][a-z0-9-]{0,63}$/.test(viewer.id) ||
				viewer.id === 'default' ||
				ids.has(viewer.id) ||
				typeof viewer.label !== 'string' ||
				!viewer.label.trim() ||
				typeof viewer.tagName !== 'string' ||
				!/^[a-z][a-z0-9]*(-[a-z0-9]+)+$/.test(viewer.tagName) ||
				tags.has(viewer.tagName) ||
				typeof viewer.version !== 'string' ||
				!/^[a-f0-9]{64}$/.test(viewer.version) ||
				viewer.scriptUrl !==
					`/plugins/repository-viewers/${viewer.id}/viewer.${viewer.version}.js` ||
				(viewer.initialPath !== undefined && typeof viewer.initialPath !== 'string')
			) {
				throw new Error('Invalid repository viewer registry entry');
			}
			ids.add(viewer.id);
			tags.add(viewer.tagName);
			viewers.push(viewer as unknown as InstalledViewer);
		}
		return viewers;
	})();
	registryRequest = promise;
	const clear = () => {
		if (registryRequest === promise) registryRequest = null;
	};
	void promise.then(clear, clear);
	return promise;
}

export function loadViewer(config: CustomViewerConfig): Promise<InstalledViewer> {
	const key = 'viewerId' in config ? config.viewerId : `${config.scriptUrl}#${config.tagName}`;
	const existing = pending.get(key);
	if (existing) return existing;
	const promise = (async () => {
		const viewer =
			'viewerId' in config
				? (await readViewerRegistry()).find((viewer) => viewer.id === config.viewerId)
				: config;
		if (!viewer) throw new Error('Selected repository viewer is not installed');
		if (!customElements.get(viewer.tagName)) {
			await import(/* @vite-ignore */ viewer.scriptUrl);
			if (!customElements.get(viewer.tagName))
				throw new Error('Repository viewer did not register its custom element');
		}
		return viewer;
	})();
	pending.set(key, promise);
	void promise.catch(() => pending.delete(key));
	return promise;
}
