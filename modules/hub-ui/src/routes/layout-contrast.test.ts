import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, test } from 'vitest';

// WCAG 2.x contrast of the key token pairs (SPEC-hub-ui-color-system AC-06), computed from layout.css itself.

type Rgb = [number, number, number];
type Theme = 'light' | 'dark';

const css = readFileSync(join(import.meta.dirname, 'layout.css'), 'utf8');

function block(selector: string): string {
	const start = css.indexOf(`${selector} {`);
	if (start < 0) throw new Error(`layout.css has no ${selector} block`);
	return css.slice(start, css.indexOf('}', start));
}

function parseTokens(source: string): Map<string, { lch: Rgb; alpha: number }> {
	const tokens = new Map<string, { lch: Rgb; alpha: number }>();
	const pattern =
		/--([\w-]+):\s*oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*(?:\/\s*([\d.]+)%)?\s*\)/g;
	for (const match of source.matchAll(pattern)) {
		const [, name, l, c, h, alpha] = match;
		tokens.set(name, {
			lch: [Number(l), Number(c), Number(h)],
			alpha: alpha === undefined ? 1 : Number(alpha) / 100
		});
	}
	return tokens;
}

const themes: Record<Theme, ReturnType<typeof parseTokens>> = {
	light: parseTokens(block(':root')),
	dark: parseTokens(block('.dark'))
};

function oklchToSrgb([l, c, h]: Rgb): Rgb {
	const a = c * Math.cos((h * Math.PI) / 180);
	const b = c * Math.sin((h * Math.PI) / 180);
	const lp = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3;
	const mp = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3;
	const sp = (l - 0.0894841775 * a - 1.291485548 * b) ** 3;
	const linear: Rgb = [
		4.0767416621 * lp - 3.3077115913 * mp + 0.2309699292 * sp,
		-1.2684380046 * lp + 2.6097574011 * mp - 0.3413193965 * sp,
		-0.0041960863 * lp - 0.7034186147 * mp + 1.707614701 * sp
	];
	return linear.map((x) => {
		const v = Math.min(1, Math.max(0, x));
		return v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055;
	}) as Rgb;
}

function luminance(rgb: Rgb): number {
	const [r, g, b] = rgb.map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: Rgb, b: Rgb): number {
	const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
	return (hi + 0.05) / (lo + 0.05);
}

function color(theme: Theme, name: string): Rgb {
	const token = themes[theme].get(name);
	if (!token) throw new Error(`${theme} theme has no --${name}`);
	if (token.alpha !== 1)
		throw new Error(`--${name} is translucent; pass a surface to composite over`);
	return oklchToSrgb(token.lch);
}

/** A tint of `name` at `alpha`, composited over `surface` in gamma-encoded sRGB (as the browser paints it). */
function tint(theme: Theme, name: string, alpha: number, surface: string): Rgb {
	const fg = color(theme, name);
	const bg = color(theme, surface);
	return fg.map((v, i) => alpha * v + (1 - alpha) * bg[i]) as Rgb;
}

const badgeSource = readFileSync(
	join(import.meta.dirname, '../lib/components/ui/badge/badge.svelte'),
	'utf8'
);

/** The `bg-<status>/NN` tint alpha of a Badge variant, read from badge.svelte (`dark:` overrides in dark). */
function tintAlpha(theme: Theme, status: string): number {
	const variant = badgeSource.match(new RegExp(`\\b${status}:\\s*'([^']*)'`));
	if (!variant) throw new Error(`badge.svelte has no ${status} variant`);
	const classes = variant[1].split(/\s+/);
	const alphaOf = (prefix: string) => {
		const cls = classes.find((name) => new RegExp(`^${prefix}bg-${status}/\\d+$`).test(name));
		return cls === undefined ? undefined : Number(cls.split('/')[1]) / 100;
	};
	const light = alphaOf('');
	if (light === undefined)
		throw new Error(`badge.svelte ${status} variant has no bg-${status}/NN tint`);
	return theme === 'dark' ? (alphaOf('dark:') ?? light) : light;
}

type Pair = { label: string; fg: Rgb; bg: Rgb; min: number };

function pairs(theme: Theme): Pair[] {
	const c = (name: string) => color(theme, name);
	const text = (fg: string, bg: string): Pair => ({
		label: `${fg} on ${bg}`,
		fg: c(fg),
		bg: c(bg),
		min: 4.5
	});
	const ui = (fg: string, bg: string): Pair => ({
		label: `${fg} on ${bg}`,
		fg: c(fg),
		bg: c(bg),
		min: 3
	});
	const list: Pair[] = [
		...['background', 'card', 'muted'].flatMap((bg) => [
			text('foreground', bg),
			text('muted-foreground', bg)
		]),
		text('primary-foreground', 'primary'),
		text('attention-foreground', 'attention'),
		...['background', 'card', 'attention-surface'].map((bg) => text('attention-text', bg)),
		ui('ring', 'background'),
		ui('primary', 'background'),
		// The attention stroke (inbox left rule, chip dot) is drawn with attention-text.
		ui('attention-text', 'card'),
		ui('attention-text', 'background')
	];
	for (const status of ['success', 'info', 'warning', 'destructive']) {
		list.push(text(status, 'card'));
		for (const surface of ['card', 'background']) {
			list.push({
				label: `${status} on its badge tint over ${surface}`,
				fg: c(status),
				bg: tint(theme, status, tintAlpha(theme, status), surface),
				min: 4.5
			});
		}
	}
	return list;
}

describe.each(['light', 'dark'] as const)('%s theme key-pair contrast', (theme) => {
	test.each(pairs(theme).map((pair) => [pair.label, pair] as const))('%s', (_label, pair) => {
		const ratio = contrast(pair.fg, pair.bg);
		expect(ratio, `${theme}: ${pair.label} is ${ratio.toFixed(2)}:1`).toBeGreaterThanOrEqual(
			pair.min
		);
	});
});

describe('token surface', () => {
	test.each(['light', 'dark'] as const)('%s theme keeps neutral surfaces untinted', (theme) => {
		const neutral = [
			'background',
			'card',
			'popover',
			'muted',
			'secondary',
			'accent',
			'sidebar',
			'sidebar-accent'
		];
		const charts = ['chart-1', 'chart-2', 'chart-3', 'chart-4', 'chart-5'];
		for (const name of [...neutral, ...charts]) {
			expect(themes[theme].get(name)?.lch[1], `--${name}`).toBe(0);
		}
		for (const name of ['success', 'info', 'warning']) {
			expect(themes[theme].get(name)?.lch[1], `--${name}`).toBeLessThanOrEqual(0.08);
		}
	});

	test('registers the attention family in @theme inline', () => {
		for (const name of [
			'attention',
			'attention-foreground',
			'attention-text',
			'attention-surface'
		]) {
			expect(css).toContain(`--color-${name}: var(--${name});`);
		}
	});
});
