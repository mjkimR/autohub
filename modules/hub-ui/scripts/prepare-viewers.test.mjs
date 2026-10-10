import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, writeFile, mkdir, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { prepareViewers } from './prepare-viewers.mjs';

async function fixture(t, config) {
	const dir = await mkdtemp(join(tmpdir(), 'viewer-install-'));
	t.after(() => rm(dir, { recursive: true, force: true }));
	const root = pathToFileURL(`${dir}/`);
	const configPath = new URL('repository-viewers.local.json', root);
	if (config) await writeFile(configPath, JSON.stringify(config));
	return { root, configPath };
}
const bundle = Buffer.from('export const renderer = true;');
const sha256 = createHash('sha256').update(bundle).digest('hex');
const viewer = (id) => ({
	id,
	label: `${id} renderer`,
	tagName: `${id}-repo-viewer`,
	url: `https://artifacts.example/${id}/viewer.js`,
	sha256
});
const manifestPath = (root) => new URL('static/plugins/repository-viewers/manifest.json', root);

test('deployment configuration installs multiple hash-named renderers and runtime registry', async (t) => {
	const { root, configPath } = await fixture(t, {
		viewers: [viewer('specs'), viewer('architecture')]
	});
	const installed = await prepareViewers(root, configPath, async () => new Response(bundle));
	assert.deepEqual(
		installed.map((item) => item.id),
		['specs', 'architecture']
	);
	for (const item of installed)
		assert.deepEqual(await readFile(new URL(`static${item.scriptUrl}`, root)), bundle);
	assert.deepEqual(JSON.parse(await readFile(manifestPath(root))), { viewers: installed });
});

test('missing configuration clears stale generated assets without downloading', async (t) => {
	const { root, configPath } = await fixture(t);
	await mkdir(new URL('static/plugins/repository-viewers/', root), { recursive: true });
	await writeFile(manifestPath(root), 'old');
	assert.deepEqual(
		await prepareViewers(root, configPath, () => {
			throw new Error('Unexpected download');
		}),
		[]
	);
	await assert.rejects(readFile(manifestPath(root)), { code: 'ENOENT' });
});

test('failed download or checksum leaves an existing installation intact', async (t) => {
	const { root, configPath } = await fixture(t, { viewers: [viewer('specs')] });
	await prepareViewers(root, configPath, async () => new Response(bundle));
	const previous = await readFile(manifestPath(root));
	await assert.rejects(
		prepareViewers(root, configPath, async () => new Response('altered')),
		/checksum mismatch/
	);
	await assert.rejects(
		prepareViewers(root, configPath, async () => new Response('', { status: 404 })),
		/HTTP 404/
	);
	assert.deepEqual(await readFile(manifestPath(root)), previous);
});

test('invalid IDs, duplicate tags, unsafe URLs and checksums fail before download', async (t) => {
	for (const config of [
		{ viewers: [viewer('../escape')] },
		{ viewers: [viewer('default')] },
		{ viewers: [viewer('one'), viewer('one')] },
		{ viewers: [viewer('one'), { ...viewer('two'), tagName: 'one-repo-viewer' }] },
		{ viewers: [{ ...viewer('one'), url: 'http://example.com/viewer.js' }] },
		{ viewers: [{ ...viewer('one'), sha256: 'invalid' }] }
	]) {
		const { root, configPath } = await fixture(t, config);
		await assert.rejects(
			prepareViewers(root, configPath, () => {
				throw new Error('Unexpected download');
			}),
			/Invalid|duplicate|HTTPS|SHA-256/
		);
	}
});
