"""One fresh observation/admission transition per batch; native owners retain all gates."""

from uuid import uuid4

from app.features.project_management.pipeline_runs.models import PipelineRun
from app_layer_base.core.database.transaction import AsyncTransaction

from .activity_claims import ActivityClaims
from .batch_policy import graph_drift, project_basis
from .batch_schemas import activity_request
from .schemas import MilestonePreviewRequest


class BatchDriver:
    def __init__(self, use_case):
        self.uc, self.sdd, self.repo = use_case, use_case.sdd, use_case.repo

    async def tick(self, project_id, batch_id):
        from .milestones import preview_milestone
        from .repos import SddRepository

        async with AsyncTransaction() as session:
            project = await self.uc.projects.get(session, project_id)
            row = await self.repo.get(session, project_id, batch_id)
            if row is None or not row.exclusion:
                return
            revision, basis, state = row.revision, row.basis, row.state
            members = await self.repo.members(session, batch_id)
            active = next((m for m in members if m.state != "succeeded"), None)
            if active is None:
                return
            member_id = active.id
            if active.state in ("failed", "canceled", "rejected"):
                return await self._hold(
                    project_id,
                    batch_id,
                    revision,
                    "Terminal native outcome requires Stop or a separately reviewed new selection",
                )
            claims = await self.repo.claims(session, member_id)
            current_claim = next((c for c in claims if not c.settled), None)
            claim_id = current_claim.id if current_claim else None
            run_id = current_claim.run_id if current_claim else None
            refused = next((c for c in reversed(claims) if c.checkpoint.get("refusal")), None)
            acknowledged = (row.evaluation or {}).get("reviewed_refusal")
            if refused and str(refused.id) != acknowledged and not current_claim:
                return await self._hold(
                    project_id,
                    batch_id,
                    revision,
                    "Native admission was definitively refused; inspect before explicit Resume: "
                    + refused.checkpoint["refusal"]["detail"],
                )
            if project_basis(project) != basis["project"]:
                return await self._hold(project_id, batch_id, revision, "Project binding/configuration changed")
        if current_claim and not run_id:
            # Claim already won before pause/stop; only the same admitted operation may reconcile.
            return await ActivityClaims(self.uc.projects, self.sdd.observer, self.sdd.run_use_case).execute(
                project_id, claim_id
            )
        if run_id:
            return await self._observe_owner(project, batch_id, member_id, claim_id, run_id, revision, basis)
        if state != "running":
            return

        async def runs_for(unit):
            async with AsyncTransaction() as session:
                return await SddRepository().runs(session, project_id, unit)

        request = MilestonePreviewRequest(
            ref=basis["ref"], milestone_id=basis["milestone"]["id"], milestone_path=basis["milestone"]["path"]
        )
        preview = await preview_milestone(
            self.sdd.observer,
            project,
            request,
            runs_for,
            capture=True,
            retained_dependencies=[edge["requested_id"] for edge in basis["edges"]],
        )
        from .batch_evidence import confirmed_ancestry

        if not await confirmed_ancestry(self.sdd.observer, project, basis["sha"], preview["resolved_sha"]):
            return await self._hold(project_id, batch_id, revision, "Selected base ancestry is unknown or rewritten")
        reason = await self._compare(project_id, batch_id, revision, basis, preview)
        if reason:
            return await self._hold(project_id, batch_id, revision, reason, preview)
        candidate = next(
            (m for m in preview["members"] if m["id"] == active.anchor_id and m["path"] == active.path), None
        )
        if candidate is None or candidate["eligibility"] != "eligible_now":
            return await self._hold(
                project_id,
                batch_id,
                revision,
                "; ".join(candidate["reasons"]) if candidate else "Exact unadmitted member is missing",
                preview,
                attention=False,
            )
        async with AsyncTransaction() as session:
            current_project = await self.uc.projects.get(session, project_id, lock=True)
            row = await self.repo.get(session, project_id, batch_id, lock=True)
            if (
                row is None
                or row.revision != revision
                or row.state != "running"
                or project_basis(current_project) != basis["project"]
            ):
                return
            member = next(m for m in await self.repo.members(session, batch_id) if m.id == member_id)
            if any(not c.settled for c in await self.repo.claims(session, member_id)):
                return
            from .batch_evidence import remote_head

            if await remote_head(self.sdd.observer, current_project, basis["ref"]) != preview["resolved_sha"]:
                row.detail = "Base moved before claim; discard this evaluation and retry fresh on the next bounded tick"
                row.revision += 1
                return
            phase = member.phase
            preferences = dict(member.initial["preferences"])
            effective = member.initial.get("effective_preferences", {})
            for key in ("planning_effort", "dev_effort"):
                if effective.get(key):
                    preferences[key] = effective[key]
            claim_request = activity_request(preferences, phase, uuid4(), basis["ref"])
            reservations = ActivityClaims(self.uc.projects, self.sdd.observer, self.sdd.run_use_case)
            claim = await reservations.reserve(
                session,
                current_project,
                phase,
                member.anchor_id.removeprefix("PROP-"),
                claim_request,
                row.actor,
                member_id=member_id,
                expected_sha=preview["resolved_sha"],
            )
            claim_id = claim.id
            member.state = "admitted"
            row.revision += 1
            row.detail = "One native owner admitted; its gates and merge remain separate"
            row.evaluation = {
                **row.evaluation,
                "sha": preview["resolved_sha"],
                "observed_at": preview["observed_at"],
                "original_edges": basis["edges"],
                "observed_edges": preview["edges"],
                "canonical_resolutions": preview["batch_basis"].get("canonical_resolutions", {}),
            }
        return await reservations.execute(project_id, claim_id)

    async def _compare(self, project_id, batch_id, revision, basis, preview):
        if not preview["complete"]:
            return "Incomplete fresh evidence: " + "; ".join(preview["reasons"])
        fresh = preview["batch_basis"]
        old = basis["evidence"]
        if any(old[k] != fresh[k] for k in ("configuration", "runtime", "policy")):
            return "Runtime/configuration/policy changed; stop and create a new selection"
        old_members = {r["id"]: r for r in old["members"]}
        new_members = {r["id"]: r for r in fresh["members"]}
        if set(new_members) - set(old_members):
            return "Milestone membership expanded; immutable selection cannot adopt it"
        async with AsyncTransaction() as session:
            selected = {m.anchor_id: m for m in await self.repo.members(session, batch_id)}
            reason = graph_drift(
                basis["edges"], preview["edges"], preview["nodes"], selected, fresh.get("canonical_resolutions", {})
            )
            if reason:
                return reason
            old_milestone = old.get("milestone")
            new_milestone = fresh.get("milestone")
            if (
                old_milestone
                and new_milestone
                and any(
                    old_milestone.get(k) != new_milestone.get(k) for k in ("id", "path", "content_digest", "depends_on")
                )
            ):
                return "Milestone anchor changed beyond ordinary prerequisite completion"
            for key, original in old_members.items():
                current = new_members.get(key)
                member = selected.get(key)
                if current is None:
                    if member is None or not member.spec_anchor or not member.outcome:
                        return f"Unexplained member removal: {key}"
                    continue
                expected = (member.outcome or {}).get("accepted_basis", original) if member else original
                if expected["path"] != current["path"] or expected["content_digest"] != current["content_digest"]:
                    return f"Selected member content/scope changed: {key}"
                if original["status"] != current["status"] and (
                    not member
                    or member.phase != "dev"
                    or not (member.outcome or {}).get("planning_merge")
                    or current["status"] != "accepted"
                ):
                    return f"Unproven member lifecycle transformation: {key}"
                if original["depends_on"] != current["depends_on"]:
                    # Verify every rewritten edge resolves to the same exact completed SPEC.
                    old_edges = {e["requested_id"]: e for e in basis["edges"] if e["source"] == key}
                    new_edges = {e["requested_id"]: e for e in preview["edges"] if e["source"] == key}
                    removed = set(original["depends_on"]) - set(current["depends_on"])
                    added = set(current["depends_on"]) - set(original["depends_on"])
                    if len(removed) != len(added):
                        return f"Dependency graph changed: {key}"
                    for dep in removed:
                        resolved = fresh.get("canonical_resolutions", {}).get(dep)
                        if (
                            dep.startswith("PROP-")
                            and resolved
                            and resolved.get("kind") == "spec"
                            and resolved.get("status") == "completed"
                        ):
                            target = resolved["id"]
                            edge = new_edges.get(target)
                            if (
                                target in added
                                and edge
                                and edge["canonical_id"] == target
                                and edge["path"] == resolved["path"]
                                and edge["status"] == "completed"
                            ):
                                continue
                        predecessor = selected.get(dep)
                        target = (predecessor.spec_anchor or {}).get("id") if predecessor else None
                        edge = new_edges.get(target)
                        if (
                            not target
                            or target not in added
                            or predecessor is None
                            or not predecessor.outcome
                            or not edge
                            or edge["status"] != "completed"
                            or edge["canonical_id"] != target
                        ):
                            return f"Canonical dependency repair requires exact completed SPEC evidence: {key}"
                        if dep not in old_edges:
                            return f"Original dependency identity missing: {key}"
        return None

    async def _observe_owner(self, project, batch_id, member_id, claim_id, run_id, revision, basis):
        async with AsyncTransaction() as session:
            run = await session.get(PipelineRun, run_id)
            if run is None or run.project_id != project.id or run.github_repository != basis["project"]["repository"]:
                return await self._hold(project.id, batch_id, revision, "Exact native run ownership unavailable")
            failure = None
            if run.state in ("failed", "canceled"):
                failure = {
                    "state": run.state,
                    "run_state": run.state,
                    "revision": run.revision,
                    "run_id": str(run.id),
                    "pull_number": run.pull_number,
                    "pull_url": run.pull_url,
                    "branch": run.branch,
                }
            if run.state == "blocked":
                return await self._hold(project.id, batch_id, revision, "Native owner requires operator inspection")
            if run.state != "completed" and failure is None:
                return
            snapshot, progress, pull_number, branch = (
                run.sdd_snapshot or {},
                run.sdd_progress or {},
                run.pull_number,
                run.branch,
            )
        if failure:
            return await self._terminal(project.id, batch_id, member_id, claim_id, run_id, revision, failure)
        pull = await self.sdd.observer.get_pull_request(
            project.github_connector_id, project.github_repository, pull_number
        )
        if (
            not pull.get("merged")
            or not pull.get("merge_commit_sha")
            or (pull.get("head") or {}).get("ref") != branch
            or (pull.get("base") or {}).get("ref") != basis["ref"]
        ):
            return await self._hold(
                project.id, batch_id, revision, "Owner-confirmed merge evidence is pending", attention=False
            )
        if progress.get("unit_status") == "rejected":
            failure = {
                "state": "rejected",
                "run_state": "completed",
                "revision": run.revision,
                "run_id": str(run_id),
                "pull_number": pull_number,
                "pull_url": run.pull_url,
                "branch": branch,
            }
            return await self._terminal(project.id, batch_id, member_id, claim_id, run_id, revision, failure)
        accepted = None
        if not snapshot.get("handoff_from"):
            from .batch_evidence import accepted_proposal

            accepted = await accepted_proposal(
                self.sdd.observer,
                project,
                basis["ref"],
                snapshot.get("spec_dir", "") + "/proposal.md",
                pull["merge_commit_sha"],
            )
        completed = None
        if snapshot.get("handoff_from") and snapshot.get("spec_dir", "").startswith("specs/"):
            from .batch_evidence import completed_spec

            completed = await completed_spec(
                self.sdd.observer, project, basis["ref"], snapshot["spec_dir"], pull["merge_commit_sha"]
            )
        async with AsyncTransaction() as session:
            await self.uc.projects.get(session, project.id, lock=True)
            row = await self.repo.get(session, project.id, batch_id, lock=True)
            if row is None or row.revision != revision:
                return
            member = next(m for m in await self.repo.members(session, batch_id) if m.id == member_id)
            claim = next(c for c in await self.repo.claims(session, member_id) if c.id == claim_id)
            evidence = {"run_id": str(run_id), "pull_number": pull_number, "merge_sha": pull["merge_commit_sha"]}
            if claim.activity == "plan":
                if (progress.get("proposal") or {}).get("status") not in (None, "accepted") or progress.get(
                    "unit_status"
                ) == "rejected":
                    row.detail = "Planning did not produce accepted direction"
                    row.state = "attention"
                    row.revision += 1
                    return
                if not accepted or accepted["id"] != member.anchor_id:
                    row.state, row.detail = "attention", "Accepted exact Planning merge checkpoint is missing"
                    row.revision += 1
                    return
                member.phase = "dev"
                member.state = "waiting"
                member.outcome = {"planning_merge": evidence, "accepted_basis": accepted}
            else:
                target = snapshot.get("spec_dir")
                origin = snapshot.get("handoff_from")
                if (
                    origin != member.path.removesuffix("/proposal.md")
                    or not isinstance(target, str)
                    or not target.startswith("specs/")
                ):
                    row.state, row.detail = "attention", "Validated exact native handoff lineage is missing"
                    row.revision += 1
                    return
                if not completed:
                    row.detail = "Exact completed SPEC is not confirmed on selected base"
                    row.revision += 1
                    return
                member.spec_anchor = {**completed, "run_id": str(run_id)}
                member.state = "succeeded"
                member.outcome = {**(member.outcome or {}), "development_merge": evidence}
            claim.settled = True
            all_members = await self.repo.members(session, batch_id)
            if all(m.state == "succeeded" for m in all_members):
                row.state, row.exclusion = "completed", False
            elif row.state == "stopped":
                row.exclusion = False
            row.revision += 1

    async def _hold(self, project_id, batch_id, revision, detail, preview=None, *, attention=True):
        async with AsyncTransaction() as session:
            await self.uc.projects.get(session, project_id, lock=True)
            row = await self.repo.get(session, project_id, batch_id, lock=True)
            if row and row.revision == revision:
                row.detail = detail[:2048]
                if attention and row.state == "running":
                    row.state = "attention"
                row.revision += 1
                if preview:
                    row.evaluation = {
                        **row.evaluation,
                        "sha": preview["resolved_sha"],
                        "observed_at": preview["observed_at"],
                        "original_edges": row.basis["edges"],
                        "observed_edges": preview["edges"],
                        "canonical_resolutions": preview.get("batch_basis", {}).get("canonical_resolutions", {}),
                    }

    async def _terminal(self, project_id, batch_id, member_id, claim_id, run_id, revision, failure):
        async with AsyncTransaction() as session:
            await self.uc.projects.get(session, project_id, lock=True)
            row = await self.repo.get(session, project_id, batch_id, lock=True)
            if row is None or row.revision != revision:
                return
            run = await session.get(PipelineRun, run_id)
            if (
                run is None
                or run.project_id != project_id
                or run.revision != failure["revision"]
                or run.state != failure["run_state"]
            ):
                return
            if failure["state"] == "rejected" and (run.sdd_progress or {}).get("unit_status") != "rejected":
                return
            member = next(m for m in await self.repo.members(session, batch_id) if m.id == member_id)
            claim = next(c for c in await self.repo.claims(session, member_id) if c.id == claim_id)
            if claim.run_id != run_id:
                return
            member.state = failure["state"]
            member.outcome = {**(member.outcome or {}), "terminal_owner": failure}
            claim.checkpoint = {**claim.checkpoint, "outcome": failure}
            claim.settled = True
            row.detail = "Native owner ended without success; no automatic replacement or next member"
            if row.state == "stopped":
                row.exclusion = False
            elif row.state == "running":
                row.state = "attention"
            row.revision += 1
