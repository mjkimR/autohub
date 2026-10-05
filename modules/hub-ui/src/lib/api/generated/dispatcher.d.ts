/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/dispatchers/trigger": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Trigger Dispatch
         * @description Called by an external trigger such as Google Cloud Scheduler.
         *     Processes due schedules using FOR UPDATE SKIP LOCKED to prevent duplicate execution.
         */
        post: operations["trigger_dispatch_api_v1_dispatchers_trigger_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export interface components {
    schemas: {
        /** DispatchResponse */
        DispatchResponse: {
            /** Dispatched */
            dispatched: number;
        };
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** SchedulerDefaults */
        SchedulerDefaults: {
            /**
             * Global Timeout Seconds
             * @description Default global timeout for scheduled tasks in seconds
             * @default 300
             */
            GLOBAL_TIMEOUT_SECONDS: number;
            /**
             * Global Timeout Buffer
             * @description Buffer time to subtract from the global timeout to ensure tasks complete within limits in seconds
             * @default 30
             */
            GLOBAL_TIMEOUT_BUFFER: number;
            /**
             * Max Concurrent Tasks
             * @description Maximum number of concurrent tasks that can be scheduled
             * @default 10
             */
            MAX_CONCURRENT_TASKS: number;
            /**
             * Max Retry Attempts
             * @description Maximum number of retry attempts for failed tasks
             * @default 3
             */
            MAX_RETRY_ATTEMPTS: number;
            /**
             * Max Dispatch Limit
             * @description Maximum number of schedules or retry jobs to fetch in a single tick
             * @default 200
             */
            MAX_DISPATCH_LIMIT: number;
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
    trigger_dispatch_api_v1_dispatchers_trigger_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["SchedulerDefaults"] | null;
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DispatchResponse"];
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
