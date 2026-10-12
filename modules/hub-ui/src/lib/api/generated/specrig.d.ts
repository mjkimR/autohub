/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/projects/{project_id}/specrig/runs": {
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
        get: operations["spec_runs_api_v1_projects__project_id__specrig_runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/specrig/readiness": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Inspect Specrig
         * @description Inspect a bound spec at a PR revision without starting work or changing Git.
         */
        post: operations["inspect_specrig_api_v1_projects__project_id__specrig_readiness_post"];
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
        /** SpecrigInspectionRequest */
        SpecrigInspectionRequest: {
            /** Pull Number */
            pull_number: number;
            /** Spec Dir */
            spec_dir: string;
        };
        /** SpecrigReadiness */
        SpecrigReadiness: {
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
    spec_runs_api_v1_projects__project_id__specrig_runs_get: {
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
    inspect_specrig_api_v1_projects__project_id__specrig_readiness_post: {
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
                "application/json": components["schemas"]["SpecrigInspectionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SpecrigReadiness"];
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
