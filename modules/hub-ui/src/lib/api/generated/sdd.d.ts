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
         * @description Request Planning: publish a Draft PR and enroll ordinary repository-owned work.
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
         * @description Request Development: publish a Draft PR and enroll ordinary repository-owned work.
         */
        post: operations["start_development_api_v1_projects__project_id__sdd_proposals__slug__development_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/batches": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Batches */
        get: operations["list_batches_api_v1_projects__project_id__sdd_batches_get"];
        put?: never;
        /**
         * Retired Sdd Evaluation
         * @deprecated
         * @description Embedded evaluation and executable native batches have been retired.
         */
        post: operations["retired_sdd_evaluation_api_v1_projects__project_id__sdd_batches_post"];
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
         * Retired Sdd Evaluation
         * @deprecated
         * @description Embedded evaluation and executable native batches have been retired.
         */
        post: operations["retired_sdd_evaluation_api_v1_projects__project_id__sdd_milestone_preview_post"];
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
         * Retired Sdd Evaluation
         * @deprecated
         * @description Embedded evaluation and executable native batches have been retired.
         */
        get: operations["retired_sdd_evaluation_api_v1_projects__project_id__sdd_milestones_get"];
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
         * Retired Sdd Evaluation
         * @deprecated
         * @description Embedded evaluation and executable native batches have been retired.
         */
        post: operations["retired_sdd_evaluation_api_v1_projects__project_id__sdd_readiness_post"];
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
         * Retired Sdd Evaluation
         * @deprecated
         * @description Embedded evaluation and executable native batches have been retired.
         */
        get: operations["retired_sdd_evaluation_api_v1_projects__project_id__sdd_runtime_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/batches/{batch_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Batch */
        get: operations["get_batch_api_v1_projects__project_id__sdd_batches__batch_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/batches/{batch_id}/controls": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Control Batch */
        post: operations["control_batch_api_v1_projects__project_id__sdd_batches__batch_id__controls_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/claims/{claim_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Claim */
        get: operations["get_claim_api_v1_projects__project_id__sdd_claims__claim_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/claims/{claim_id}/reconcile": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reconcile Claim
         * @description Acknowledge inspected external work and release only this retired reservation.
         */
        post: operations["reconcile_claim_api_v1_projects__project_id__sdd_claims__claim_id__reconcile_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/sdd/runs/{run_id}/reconcile": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reconcile Retired Run
         * @description Acknowledge retired external work without resuming the retained Run.
         */
        post: operations["reconcile_retired_run_api_v1_projects__project_id__sdd_runs__run_id__reconcile_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export interface components {
    schemas: {
        /** BatchRead */
        BatchRead: {
            /** Id */
            id: string;
            /** Project Id */
            project_id: string;
            /** State */
            state: string;
            /** Revision */
            revision: number;
            /** Exclusion */
            exclusion: boolean;
            /** Detail */
            detail: string | null;
            /** Basis */
            basis: {
                [key: string]: unknown;
            };
            /** Evaluation */
            evaluation: {
                [key: string]: unknown;
            };
            /** Members */
            members: {
                [key: string]: unknown;
            }[];
            /**
             * Retired
             * @default true
             */
            retired: boolean;
        };
        /** ClaimRead */
        ClaimRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Project Id
             * Format: uuid
             */
            project_id: string;
            /** Unit */
            unit: string;
            /** Activity */
            activity: string;
            /** Run Id */
            run_id: string | null;
            /** Settled */
            settled: boolean;
            /** Retired */
            retired: boolean;
            /** Checkpoint Digest */
            checkpoint_digest: string;
            /** Checkpoint */
            checkpoint: {
                [key: string]: unknown;
            };
        };
        /** ControlBatch */
        ControlBatch: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Expected Revision */
            expected_revision: number;
            /**
             * Action
             * @enum {string}
             */
            action: "pause" | "resume" | "stop";
        };
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        LinkedIssue: CommonComponents["schemas"]["LinkedIssue"];
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
             * @description Descriptive status read from the selected base; not execution eligibility
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
            actions: ("start_planning" | "start_development")[];
            /** Note */
            note?: string | null;
        };
        PullRequestSnapshot: CommonComponents["schemas"]["PullRequestSnapshot"];
        /** ReconcileClaimRequest */
        ReconcileClaimRequest: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Expected Checkpoint Digest */
            expected_checkpoint_digest: string;
            /**
             * Acknowledge External Work
             * @constant
             */
            acknowledge_external_work: true;
        };
        /** ReconcileRunRequest */
        ReconcileRunRequest: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Expected Revision */
            expected_revision: number;
            /**
             * Acknowledge External Work
             * @constant
             */
            acknowledge_external_work: true;
        };
        RunOrigin: CommonComponents["schemas"]["RunOrigin"];
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
    list_batches_api_v1_projects__project_id__sdd_batches_get: {
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
                    "application/json": components["schemas"]["BatchRead"][];
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
    retired_sdd_evaluation_api_v1_projects__project_id__sdd_batches_post: {
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
                    "application/json": unknown;
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
    retired_sdd_evaluation_api_v1_projects__project_id__sdd_milestone_preview_post: {
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
                    "application/json": unknown;
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
    retired_sdd_evaluation_api_v1_projects__project_id__sdd_milestones_get: {
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
                    "application/json": unknown;
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
    retired_sdd_evaluation_api_v1_projects__project_id__sdd_readiness_post: {
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
                    "application/json": unknown;
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
    retired_sdd_evaluation_api_v1_projects__project_id__sdd_runtime_get: {
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
                    "application/json": unknown;
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
    get_batch_api_v1_projects__project_id__sdd_batches__batch_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                batch_id: string;
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
                    "application/json": components["schemas"]["BatchRead"];
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
    control_batch_api_v1_projects__project_id__sdd_batches__batch_id__controls_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                batch_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ControlBatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BatchRead"];
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
    get_claim_api_v1_projects__project_id__sdd_claims__claim_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                claim_id: string;
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
                    "application/json": components["schemas"]["ClaimRead"];
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
    reconcile_claim_api_v1_projects__project_id__sdd_claims__claim_id__reconcile_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                claim_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReconcileClaimRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClaimRead"];
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
    reconcile_retired_run_api_v1_projects__project_id__sdd_runs__run_id__reconcile_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                run_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReconcileRunRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
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
}
