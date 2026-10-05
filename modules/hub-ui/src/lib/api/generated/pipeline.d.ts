/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/pipelines/inspect": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Inspect Pipeline
         * @description Inspect CI without creating PRs, dispatching workflows, posting comments, or saving state.
         */
        post: operations["inspect_pipeline_api_v1_pipelines_inspect_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipelines/observations/{schedule_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Pipeline Observation
         * @description Return the last successful observation, not live CI evidence or a merge authorization.
         */
        get: operations["get_pipeline_observation_api_v1_pipelines_observations__schedule_id__get"];
        put?: never;
        post?: never;
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
        JobSnapshot: CommonComponents["schemas"]["JobSnapshot"];
        PipelineObservation: CommonComponents["schemas"]["PipelineObservation"];
        PipelineObservationConfig: CommonComponents["schemas"]["PipelineObservationConfig"];
        PullObservation: CommonComponents["schemas"]["PullObservation"];
        RunSnapshot: CommonComponents["schemas"]["RunSnapshot"];
        ValidationError: CommonComponents["schemas"]["ValidationError"];
        VerificationConfig: CommonComponents["schemas"]["VerificationConfig"];
        VerificationResult: CommonComponents["schemas"]["VerificationResult"];
        VerificationStatus: CommonComponents["schemas"]["VerificationStatus"];
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export interface operations {
    inspect_pipeline_api_v1_pipelines_inspect_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PipelineObservationConfig"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineObservation"];
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
    get_pipeline_observation_api_v1_pipelines_observations__schedule_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_id: string;
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
                    "application/json": components["schemas"]["PipelineObservation"];
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
