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
}
export interface components {
    schemas: {
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        LinkedIssue: CommonComponents["schemas"]["LinkedIssue"];
        PipelineRunRead: CommonComponents["schemas"]["PipelineRunRead"];
        PipelineRunState: CommonComponents["schemas"]["PipelineRunState"];
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
}
