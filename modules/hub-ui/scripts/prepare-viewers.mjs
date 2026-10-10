import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir, rm, rename } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const idPattern = /^[a-z][a-z0-9-]{0,63}$/;
const tagPattern = /^[a-z][a-z0-9]*(-[a-z0-9]+)+$/;

/** Deploy-time installation owns this ignored directory; no renderer bundle is tracked. */
export async function prepareViewers(root, configPath, fetcher = fetch) {
	const destination = new URL('static/plugins/repository-viewers/', root);
	let config;
	try {
		config = JSON.parse(await readFile(configPath, 'utf8'));
	} catch (error) {
		if (error.code !== 'ENOENT') throw error;
		await rm(destination, { recursive: true, force: true });
		return [];
	}
	if (!Array.isArray(config.viewers)) throw new Error('Configuration must contain a viewers array');
	const ids = new Set(),
		tags = new Set();
	const entries = config.viewers.map((viewer) => {
		if (
			typeof viewer.id !== 'string' ||
			!idPattern.test(viewer.id) ||
			viewer.id === 'default' ||
			ids.has(viewer.id)
		)
			throw new Error('Invalid or duplicate viewer ID');
		if (
			typeof viewer.tagName !== 'string' ||
			!tagPattern.test(viewer.tagName) ||
			tags.has(viewer.tagName)
		)
			throw new Error('Invalid or duplicate viewer tagName');
		if (typeof viewer.label !== 'string' || !viewer.label.trim())
			throw new Error('Viewer label is required');
		if (viewer.initialPath !== undefined && typeof viewer.initialPath !== 'string')
			throw new Error('Viewer initialPath must be a string');
		const url = new URL(viewer.url);
		if (url.protocol !== 'https:' || url.username || url.password)
			throw new Error('Viewer URL must use HTTPS without embedded credentials');
		if (!/^[a-f0-9]{64}$/.test(viewer.sha256))
			throw new Error('Viewer SHA-256 must be 64 lowercase hex characters');
		ids.add(viewer.id);
		tags.add(viewer.tagName);
		return { ...viewer, url };
	});
	// Fetch and verify every bundle before replacing any existing installation.
	const downloads = [];
	for (const viewer of entries) {
		const response = await fetcher(viewer.url, { signal: AbortSignal.timeout(120000) });
		if (!response.ok)
			throw new Error(`Viewer ${viewer.id} download failed: HTTP ${response.status}`);
		const bytes = Buffer.from(await response.arrayBuffer());
		if (createHash('sha256').update(bytes).digest('hex') !== viewer.sha256)
			throw new Error(`Viewer ${viewer.id} artifact checksum mismatch`);
		downloads.push({ viewer, bytes });
	}
	const staging = new URL('static/plugins/repository-viewers-installing/', root);
	await rm(staging, { recursive: true, force: true });
	await mkdir(staging, { recursive: true });
	try {
		const viewers = [];
		for (const { viewer, bytes } of downloads) {
			const file = `${viewer.id}/viewer.${viewer.sha256}.js`;
			await mkdir(new URL(`${viewer.id}/`, staging), { recursive: true });
			await writeFile(new URL(file, staging), bytes);
			viewers.push({
				id: viewer.id,
				label: viewer.label,
				tagName: viewer.tagName,
				scriptUrl: `/plugins/repository-viewers/${file}`,
				version: viewer.sha256,
				initialPath: viewer.initialPath ?? ''
			});
		}
		await writeFile(new URL('manifest.json', staging), `${JSON.stringify({ viewers })}\n`);
		await rm(destination, { recursive: true, force: true });
		await rename(staging, destination);
		return viewers;
	} finally {
		await rm(staging, { recursive: true, force: true });
	}
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
	const root = new URL('../', import.meta.url);
	const args = process.argv.slice(2);
	if (args.length > 1) throw new Error('Usage: prepare-viewers.mjs [config.json]');
	const config = args[0]
		? pathToFileURL(resolve(args[0]))
		: new URL('repository-viewers.local.json', root);
	if (args[0]) await readFile(config);
	const viewers = await prepareViewers(root, config);
	console.log(
		`Installed repository viewers: ${viewers.map((viewer) => viewer.id).join(', ') || 'none (Git browser)'}`
	);
}
