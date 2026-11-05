---
id: PADR-decision-inbox-read-projection
title: Discover decisions through an owner-backed read projection
summary: "For cross-project decision discovery, we keep a durable read projection and refresh the owning review context before acting, to bound listing cost and preserve authority, accepting snapshot lag and projection maintenance."
proposal: PROP-operator-decision-inbox
status: draft
created_at: 2026-11-05
---

# [PADR-decision-inbox-read-projection] Discover decisions through an owner-backed read projection

## 1. Context & Problem Statement

Ordinary question rows and native SDD evidence have different lifecycles. Per-run repository evaluation cannot bound a cross-project list request. Native snapshots lack per-subject waiting timestamps. A mixed worklist must preserve the owner of every decision and its current authority.

## 2. Decision Drivers

- Bounded database listing and stable identities across refreshes.
- Existing owner revision, head and publication fences.
- Accurate distinction between ordinary waiting time and native first observation.

## 3. Considered Options

- Keep per-run discovery: no projection cost, but fails the cross-project discovery outcome.
- Evaluate every repository while listing: fresh evidence but unbounded external work per page.
- Query raw question rows and native JSON: avoids a projection table but requires dialect-specific request expansion and provides no durable native waiting origin.
- Maintain a normalized discovery projection: indexed keyset pagination and explicit observation times, at the cost of transactional maintenance and migration.

## 4. Decision Outcome

- The normalized projection serves discovery and is rebuildable from owner records. → `ARCH-05-2-components` Components and owners (SHOULD).
- Ordinary saved answers remain pending until explicitly applied or dismissed. → `CAP-PR-operator-decisions` discovery rules (MUST).
- Native entries describe observed pending subjects and require refreshed owner review before mutation. → `CAP-SDD-native-delivery` discovery rules (MUST); `CAP-SDD-workflow-control` discovery rules (MUST).
- The inbox introduces no mutation authority or automatic execution. → `CAP-PR-operator-decisions` discovery rules (MUST); `CAP-SDD-workflow-control` discovery rules (MUST).
- Native waiting age records first observation of a subject generation and does not claim the historical request creation time.

## 5. Consequences

The migration bootstraps older native subjects with an explicitly labeled observation time. Owner transactions must update discovery rows. External repository changes can leave stale candidates until inspection or normal owner evaluation; freshness labels and disabled stale controls expose that limitation. If an owner adds another actionable request kind, its extractor and lifecycle tests must be extended before discovery includes it.

## 6. Confirmation

Development verifies bounded SQL/page size, no repository calls during listing/backfill, transactional invalidation, migration and current-owner filtering on both supported databases. UI integration checks verify exact subject routing, freshness failure and preserved owner mutation APIs. Review only until these checks exist; this PADR is preliminary and does not amend the current contracts.
