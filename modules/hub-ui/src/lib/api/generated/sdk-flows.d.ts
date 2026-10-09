/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/task-providers/{provider}/environments/{environment}/releases/{release_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Register */
        put: operations["register_api_v1_task_providers__provider__environments__environment__releases__release_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/task-providers/{provider}/environments/{environment}/releases/{release_id}/activate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Activate */
        post: operations["activate_api_v1_task_providers__provider__environments__environment__releases__release_id__activate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/task-runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start */
        post: operations["start_api_v1_task_runs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/task-runs/{run_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get */
        get: operations["get_api_v1_task_runs__run_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/task-runs/{run_id}/commands": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Command */
        post: operations["command_api_v1_task_runs__run_id__commands_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export interface components {
    schemas: {
        /** ActivationReceipt */
        ActivationReceipt: {
            /** Provider */
            provider: string;
            /** Environment */
            environment: string;
            /** Release Id */
            release_id: string;
            /** Digest */
            digest: string;
            /** Revision */
            revision: number;
        };
        /** ActivationRequest */
        ActivationRequest: {
            /** Expected Revision */
            expected_revision: number;
        };
        /** ApprovalStep */
        ApprovalStep: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "approval";
            /** Id */
            id: string;
            /**
             * Deadline Seconds
             * @default 86400
             */
            deadline_seconds: number;
            /** Revise To */
            revise_to?: string | null;
            /**
             * Max Revisions
             * @default 0
             */
            max_revisions: number;
        };
        /** AttemptView */
        AttemptView: {
            /** Step Id */
            step_id: string;
            /** Number */
            number: number;
            /**
             * Status
             * @enum {string}
             */
            status: "running" | "observing" | "completed" | "failed" | "canceled";
            /** Inputs */
            inputs: {
                [key: string]: unknown;
            };
            /** Output */
            output?: {
                [key: string]: unknown;
            } | null;
            /** Error */
            error?: string | null;
        };
        /**
         * FlowManifest
         * @description Version 2 is separate from the unchanged local version-1 Manifest.
         */
        FlowManifest: {
            /**
             * Manifest Version
             * @default 2
             * @constant
             */
            manifest_version: 2;
            /** Tasks */
            tasks: components["schemas"]["PipelineSpec"][];
            /**
             * Flows
             * @default []
             */
            flows: components["schemas"]["FlowSpec"][];
        };
        /** FlowSpec */
        FlowSpec: {
            /** Key */
            key: string;
            /**
             * Contract Version
             * @default 1
             */
            contract_version: number;
            /** Title */
            title: string;
            /** Input Schema */
            input_schema: {
                [key: string]: unknown;
            };
            /** Output Schema */
            output_schema: {
                [key: string]: unknown;
            };
            /** Steps */
            steps: (components["schemas"]["TaskStep"] | components["schemas"]["ApprovalStep"])[];
            /** Result Step */
            result_step: string;
        };
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** InputRef */
        InputRef: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "ref";
            /**
             * Source
             * @enum {string}
             */
            source: "run" | "step";
            /** Step Id */
            step_id?: string | null;
            /**
             * Path
             * @default []
             */
            path: string[];
        };
        /** LiteralValue */
        LiteralValue: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "literal";
            /** Value */
            value: unknown;
        };
        /** PipelineSpec */
        PipelineSpec: {
            /** Key */
            key: string;
            /** Contract Version */
            contract_version: number;
            /** Title */
            title: string;
            /** Description */
            description: string;
            /** Input Schema */
            input_schema: {
                [key: string]: unknown;
            };
            /** Output Schema */
            output_schema: {
                [key: string]: unknown;
            };
        };
        /** ReleaseReceipt */
        ReleaseReceipt: {
            /** Provider */
            provider: string;
            /** Environment */
            environment: string;
            /** Release Id */
            release_id: string;
            /** Digest */
            digest: string;
        };
        /** ReleaseSpec */
        ReleaseSpec: {
            manifest: components["schemas"]["FlowManifest"];
            /** Bindings */
            bindings: components["schemas"]["TaskBinding"][];
        };
        /** RunCommand */
        RunCommand: {
            /** Command Id */
            command_id: string;
            /** Expected Revision */
            expected_revision: number;
            /**
             * Action
             * @enum {string}
             */
            action: "approve" | "revise" | "cancel" | "resume";
        };
        /** RunRequest */
        RunRequest: {
            /** Provider */
            provider: string;
            /** Environment */
            environment: string;
            task: components["schemas"]["TaskRef"];
            /** Inputs */
            inputs: {
                [key: string]: unknown;
            };
            /** Idempotency Key */
            idempotency_key: string;
        };
        /** RunView */
        RunView: {
            /** Run Id */
            run_id: string;
            /** Provider */
            provider: string;
            /** Environment */
            environment: string;
            /** Release Id */
            release_id: string;
            /** Release Digest */
            release_digest: string;
            task: components["schemas"]["TaskRef"];
            /** Revision */
            revision: number;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "waiting" | "failed" | "canceling" | "canceled" | "completed";
            /** Current Step */
            current_step?: string | null;
            /** Waiting Reason */
            waiting_reason?: string | null;
            /**
             * Attempts
             * @default []
             */
            attempts: components["schemas"]["AttemptView"][];
            /** Output */
            output?: {
                [key: string]: unknown;
            } | null;
            /** Error */
            error?: string | null;
        };
        /** TaskBinding */
        TaskBinding: {
            task: components["schemas"]["TaskRef"];
            /**
             * Executor
             * @enum {string}
             */
            executor: "http" | "native";
            /** Target */
            target: string;
        };
        /** TaskRef */
        TaskRef: {
            /** Key */
            key: string;
            /**
             * Contract Version
             * @default 1
             */
            contract_version: number;
        };
        /** TaskStep */
        TaskStep: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "task";
            /** Id */
            id: string;
            task: components["schemas"]["TaskRef"];
            /** Inputs */
            inputs: {
                [key: string]: components["schemas"]["LiteralValue"] | components["schemas"]["InputRef"];
            };
            /**
             * Max Attempts
             * @default 1
             */
            max_attempts: number;
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
    register_api_v1_task_providers__provider__environments__environment__releases__release_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                provider: string;
                environment: string;
                release_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReleaseSpec"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReleaseReceipt"];
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
    activate_api_v1_task_providers__provider__environments__environment__releases__release_id__activate_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                provider: string;
                environment: string;
                release_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ActivationRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ActivationReceipt"];
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
    start_api_v1_task_runs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RunRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunView"];
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
    get_api_v1_task_runs__run_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
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
                    "application/json": components["schemas"]["RunView"];
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
    command_api_v1_task_runs__run_id__commands_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RunCommand"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunView"];
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
