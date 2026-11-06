/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/projects/{project_id}/sdd/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Spec Runs
         * @description The latest 20 runs bound to this project/spec, including finished executions.
         */
        get: operations["spec_runs_api_v1_projects__project_id__sdd_runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/proposals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Proposals
         * @description Proposals on the base with their activity branches, waiting run and the actions they can take.
         */
        get: operations["list_proposals_api_v1_projects__project_id__sdd_proposals_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/proposals/{slug}/planning": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start Planning
         * @description Start Planning of a draft proposal: Hub creates plan-<slug> and its pull request, then enrolls the run.
         */
        post: operations["start_planning_api_v1_projects__project_id__sdd_proposals__slug__planning_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/proposals/{slug}/development": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start Development
         * @description Start Development of an accepted proposal: dev-<slug>, a draft pull request, a handoff-first run.
         */
        post: operations["start_development_api_v1_projects__project_id__sdd_proposals__slug__development_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/runtime": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Sdd Runtime
         * @description Whether this host can evaluate SDD runs: the runtime pin and an isolated devkit start, without a PR.
         */
        get: operations["sdd_runtime_api_v1_projects__project_id__sdd_runtime_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/readiness": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Inspect Sdd
         * @description Inspect a bound spec at a PR revision without starting work or changing Git.
         */
        post: operations["inspect_sdd_api_v1_projects__project_id__sdd_readiness_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/milestones": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Milestones
         * @description Global and package milestones at the selected immutable ref; inspection only.
         */
        get: operations["list_milestones_api_v1_projects__project_id__sdd_milestones_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/milestone-preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Preview Milestone
         * @description Observe bounded member readiness without creating or resuming activities.
         */
        post: operations["preview_milestone_api_v1_projects__project_id__sdd_milestone_preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export interface components {
    schemas: {
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        LinkedIssue: CommonComponents["schemas"]["LinkedIssue"];
        /** MilestoneList */
        MilestoneList: {
            /** Resolved Sha */
            resolved_sha: string;
            /** Complete */
            complete: boolean;
            /** Reasons */
            reasons: string[];
            /** Items */
            items: {
                [key: string]: unknown;
            }[];
        };
        /** MilestoneMember */
        MilestoneMember: {
            /** Id */
            id: string;
            /** Path */
            path: string;
            /**
             * Title
             * @default
             */
            title: string;
            /** Status */
            status: string;
            /** Activity Kind */
            activity_kind?: ("plan" | "dev") | null;
            /** Stage */
            stage?: string | null;
            /**
             * Admission
             * @enum {string}
             */
            admission: "pass" | "held" | "unknown";
            /**
             * Scheduling
             * @enum {string}
             */
            scheduling: "pass" | "held";
            /** Workflow Hold */
            workflow_hold?: {
                [key: string]: unknown;
            };
            /**
             * Eligibility
             * @enum {string}
             */
            eligibility: "eligible_now" | "held" | "existing_activity" | "finished" | "unsupported" | "unknown";
            /** Reasons */
            reasons: string[];
            /** Evidence */
            evidence?: {
                [key: string]: unknown;
            }[];
            /** Evidence Observed At */
            evidence_observed_at?: string | null;
        };
        /** MilestonePreview */
        MilestonePreview: {
            /** Project Id */
            project_id: string;
            /** Repository */
            repository: string;
            /** Requested Ref */
            requested_ref: string;
            /** Resolved Sha */
            resolved_sha: string;
            /** Milestone */
            milestone: {
                [key: string]: unknown;
            };
            /** Observed At */
            observed_at: string;
            /** Runtime Identity */
            runtime_identity?: string | null;
            /** Complete */
            complete: boolean;
            /** Counts */
            counts: {
                [key: string]: number;
            };
            /** Limits */
            limits: {
                [key: string]: number;
            };
            /** Reasons */
            reasons: string[];
            /** Warnings */
            warnings: components["schemas"]["SddWarning"][];
            /** Nodes */
            nodes: {
                [key: string]: unknown;
            }[];
            /** Edges */
            edges: {
                [key: string]: unknown;
            }[];
            /** Members */
            members: components["schemas"]["MilestoneMember"][];
        };
        /** MilestonePreviewRequest */
        MilestonePreviewRequest: {
            /** Ref */
            ref: string;
            /** Milestone Id */
            milestone_id: string;
            /** Milestone Path */
            milestone_path?: string | null;
        };
        PipelineRunRead: CommonComponents["schemas"]["PipelineRunRead"];
        PipelineRunState: CommonComponents["schemas"]["PipelineRunState"];
        /** ProposalList */
        ProposalList: {
            /** Base Branch */
            base_branch: string;
            /** Base Sha */
            base_sha: string;
            /** Items */
            items: components["schemas"]["ProposalState"][];
            /** Truncated */
            truncated: boolean;
        };
        /** ProposalRun */
        ProposalRun: {
            /** Id */
            id: string;
            /** State */
            state: string;
            /** Revision */
            revision: number;
            /** Pause Reason */
            pause_reason?: string | null;
            /** Pull Number */
            pull_number: number;
            /** Head Sha */
            head_sha?: string | null;
            /** Plan Accept Open */
            plan_accept_open: boolean;
            /** Decided */
            decided: boolean;
        };
        /** ProposalState */
        ProposalState: {
            /** Slug */
            slug: string;
            /** Id */
            id: string;
            /** Path */
            path: string;
            /** Title */
            title: string;
            /**
             * Status
             * @description The proposal's status on the base branch
             */
            status: string;
            /**
             * Display Status
             * @description reviewing while plan-<slug> exists for a draft (no base commit)
             */
            display_status: string;
            /** Task Kind */
            task_kind?: string | null;
            /** Planning Effort */
            planning_effort?: ("low" | "medium" | "high") | null;
            /** Dev Effort */
            dev_effort?: ("low" | "medium" | "high") | null;
            /** Plan Branch */
            plan_branch: boolean;
            /** Dev Branch */
            dev_branch: boolean;
            /** Plan Pull */
            plan_pull?: number | null;
            /** Dev Pull */
            dev_pull?: number | null;
            run?: components["schemas"]["ProposalRun"] | null;
            /** Actions */
            actions: ("start_planning" | "accept" | "reject" | "start_development")[];
            /** Note */
            note?: string | null;
        };
        PullRequestSnapshot: CommonComponents["schemas"]["PullRequestSnapshot"];
        /** SddInspectionRequest */
        SddInspectionRequest: {
            /** Pull Number */
            pull_number: number;
            /** Spec Dir */
            spec_dir: string;
        };
        /** SddReadiness */
        SddReadiness: {
            /** Ready */
            ready: boolean;
            /** Reason */
            reason?: string | null;
            /** Head Sha */
            head_sha?: string | null;
            /** Base Sha */
            base_sha?: string | null;
            /** Cli Version */
            cli_version?: string | null;
            /** Workflow */
            workflow?: {
                [key: string]: unknown;
            };
            /** Current */
            current?: {
                [key: string]: unknown;
            };
            /** Warnings */
            warnings?: components["schemas"]["SddWarning"][];
        };
        /**
         * SddRuntimeStatus
         * @description The host's SDD runtime: its pin and whether devkit starts inside the sandbox (the new-host canary).
         */
        SddRuntimeStatus: {
            /** Ok */
            ok: boolean;
            /**
             * Profile
             * @default default
             */
            profile: string;
            /** Bundles */
            bundles?: string[];
            /** Provider */
            provider?: string | null;
            /** Lock Sha256 */
            lock_sha256?: string | null;
            /** Revisions */
            revisions?: {
                [key: string]: string;
            };
            /** Isolation */
            isolation?: string | null;
            /** Detail */
            detail?: string | null;
        };
        /**
         * SddWarning
         * @description A best-effort finding that did not stop the evaluation (a stale receipt, a runtime revision mismatch).
         */
        SddWarning: {
            /** Code */
            code: string;
            /** Detail */
            detail: string;
        };
        /**
         * StartActivityRequest
         * @description Start Planning or Development of a proposal in the cloud: Hub makes the branch and pull request.
         */
        StartActivityRequest: {
            /**
             * Request Id
             * Format: uuid
             * @description Client UUID; retries after a lost response enroll the same start
             */
            request_id: string;
            /**
             * Base Branch
             * @default main
             */
            base_branch: string;
            /** Activity Effort */
            activity_effort?: ("low" | "medium" | "high") | null;
            /** Catalog */
            catalog?: string | null;
        };
        ValidationError: CommonComponents["schemas"]["ValidationError"];
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export interface operations {
    spec_runs_api_v1_projects__project_id__sdd_runs_get: {
        parameters: {
            query: {
                spec_dir: string;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineRunRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_proposals_api_v1_projects__project_id__sdd_proposals_get: {
        parameters: {
            query?: {
                base_branch?: string;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProposalList"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    start_planning_api_v1_projects__project_id__sdd_proposals__slug__planning_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                slug: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StartActivityRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineRunRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    start_development_api_v1_projects__project_id__sdd_proposals__slug__development_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                slug: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StartActivityRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineRunRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sdd_runtime_api_v1_projects__project_id__sdd_runtime_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SddRuntimeStatus"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    inspect_sdd_api_v1_projects__project_id__sdd_readiness_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SddInspectionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SddReadiness"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_milestones_api_v1_projects__project_id__sdd_milestones_get: {
        parameters: {
            query: {
                ref: string;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MilestoneList"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    preview_milestone_api_v1_projects__project_id__sdd_milestone_preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MilestonePreviewRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MilestonePreview"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
