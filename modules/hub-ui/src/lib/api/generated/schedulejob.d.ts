/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/schedule_jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Schedule Jobs */
        get: operations["get_schedule_jobs_api_v1_schedule_jobs_get"];
        put?: never;
        /** Create Schedule Job */
        post: operations["create_schedule_job_api_v1_schedule_jobs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/schedule_jobs/{schedule_job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Schedule Job */
        get: operations["get_schedule_job_api_v1_schedule_jobs__schedule_job_id__get"];
        /** Put Schedule Job */
        put: operations["put_schedule_job_api_v1_schedule_jobs__schedule_job_id__put"];
        post?: never;
        /** Delete Schedule Job */
        delete: operations["delete_schedule_job_api_v1_schedule_jobs__schedule_job_id__delete"];
        options?: never;
        head?: never;
        /** Patch Schedule Job */
        patch: operations["patch_schedule_job_api_v1_schedule_jobs__schedule_job_id__patch"];
        trace?: never;
    };
}
export interface components {
    schemas: {
        DeleteResponse: CommonComponents["schemas"]["DeleteResponse"];
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** PaginatedList[ScheduleJobRead] */
        PaginatedList_ScheduleJobRead_: {
            /** Items */
            items: components["schemas"]["ScheduleJobRead"][];
            /** Total Count */
            total_count?: number | null;
            /**
             * Offset
             * @default 0
             */
            offset: number;
            /** Limit */
            limit?: number | null;
            /**
             * Last
             * @description Check if the current page is the last page
             */
            readonly last: boolean | null;
            /** First */
            readonly first: boolean;
        };
        /** ScheduleJobCreate */
        ScheduleJobCreate: {
            /**
             * Name
             * @description The name of the schedule job.
             */
            name: string;
            /**
             * Schedule Config Id
             * @description Reference to the schedule config that triggered this job execution.
             */
            schedule_config_id?: string | null;
            /**
             * Dispatcher Run Id
             * @description Reference to the dispatcher run that executed this job. Allows grouping multiple schedule jobs under a single dispatcher run for better traceability.
             */
            dispatcher_run_id?: string | null;
            /** @description Execution status of the schedule. */
            status: components["schemas"]["ScheduleJobStatus"];
            /**
             * Started At
             * Format: date-time
             * @description Timestamp when the task execution started.
             */
            started_at: string;
            /**
             * Finished At
             * @description Timestamp when the task execution finished.
             */
            finished_at?: string | null;
            /**
             * Payload
             * @description Snapshot of the payload used during execution.
             */
            payload?: {
                [key: string]: unknown;
            };
            /**
             * Error Message
             * @description Error message if the task execution failed.
             */
            error_message?: string | null;
        };
        /** ScheduleJobPatch */
        ScheduleJobPatch: {
            /**
             * Name
             * @description The name of the schedule job.
             */
            name?: string | null;
            /**
             * Schedule Config Id
             * @description Reference to the schedule config.
             */
            schedule_config_id?: string | null;
            /**
             * Dispatcher Run Id
             * @description Reference to the dispatcher run.
             */
            dispatcher_run_id?: string | null;
            /** @description Execution status of the schedule. */
            status?: components["schemas"]["ScheduleJobStatus"] | null;
            /**
             * Started At
             * @description Timestamp when the task execution started.
             */
            started_at?: string | null;
            /**
             * Finished At
             * @description Timestamp when the task execution finished.
             */
            finished_at?: string | null;
            /**
             * Payload
             * @description Snapshot of the payload used during execution.
             */
            payload?: {
                [key: string]: unknown;
            } | null;
            /**
             * Error Message
             * @description Error message if the task execution failed.
             */
            error_message?: string | null;
        };
        /** ScheduleJobPut */
        ScheduleJobPut: {
            /**
             * Name
             * @description The name of the schedule job.
             */
            name: string;
            /**
             * Schedule Config Id
             * @description Reference to the schedule config that triggered this job execution.
             */
            schedule_config_id?: string | null;
            /**
             * Dispatcher Run Id
             * @description Reference to the dispatcher run that executed this job. Allows grouping multiple schedule jobs under a single dispatcher run for better traceability.
             */
            dispatcher_run_id?: string | null;
            /** @description Execution status of the schedule. */
            status: components["schemas"]["ScheduleJobStatus"];
            /**
             * Started At
             * Format: date-time
             * @description Timestamp when the task execution started.
             */
            started_at: string;
            /**
             * Finished At
             * @description Timestamp when the task execution finished.
             */
            finished_at?: string | null;
            /**
             * Payload
             * @description Snapshot of the payload used during execution.
             */
            payload?: {
                [key: string]: unknown;
            };
            /**
             * Error Message
             * @description Error message if the task execution failed.
             */
            error_message?: string | null;
        };
        /** ScheduleJobRead */
        ScheduleJobRead: {
            /**
             * Name
             * @description The name of the schedule job.
             */
            name: string;
            /**
             * Schedule Config Id
             * @description Reference to the schedule config that triggered this job execution.
             */
            schedule_config_id?: string | null;
            /**
             * Dispatcher Run Id
             * @description Reference to the dispatcher run that executed this job. Allows grouping multiple schedule jobs under a single dispatcher run for better traceability.
             */
            dispatcher_run_id?: string | null;
            /** @description Execution status of the schedule. */
            status: components["schemas"]["ScheduleJobStatus"];
            /**
             * Started At
             * Format: date-time
             * @description Timestamp when the task execution started.
             */
            started_at: string;
            /**
             * Finished At
             * @description Timestamp when the task execution finished.
             */
            finished_at?: string | null;
            /**
             * Payload
             * @description Snapshot of the payload used during execution.
             */
            payload?: {
                [key: string]: unknown;
            };
            /**
             * Error Message
             * @description Error message if the task execution failed.
             */
            error_message?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
        };
        /**
         * ScheduleJobStatus
         * @enum {string}
         */
        ScheduleJobStatus: "pending" | "success" | "failure";
        ValidationError: CommonComponents["schemas"]["ValidationError"];
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export interface operations {
    get_schedule_jobs_api_v1_schedule_jobs_get: {
        parameters: {
            query?: {
                /** @description offset for pagination */
                offset?: number;
                /** @description limit for pagination */
                limit?: number;
                /** @description Case-insensitive literal substring search; percent and underscore are ordinary characters. */
                search?: string | null;
                /** @description Filter by name (case-insensitive substring) */
                name?: string | null;
                /** @description Filter by execution status */
                status?: components["schemas"]["ScheduleJobStatus"] | null;
                /** @description Filter by schedule configuration ID */
                schedule_config_id?: string | null;
                /** @description Filter by dispatcher run ID */
                dispatcher_run_id?: string | null;
                /** @description Filter by whether retry is needed */
                retry_need?: boolean | null;
                /**
                 * @description **Order by options:**
                 *
                 *     * `name`: Sort by name
                 *     * `status`: Sort by status
                 *     * `started_at`: Sort by execution start time
                 *     * `finished_at`: Sort by execution finish time
                 *     * `created_at`: Sort by creation time
                 *     * `updated_at`: Sort by update time
                 *     * `id`: Sort by ID
                 *
                 *     **Usage:**
                 *     * Prefix with `-` for descending order (e.g., `-title`).
                 *     * Multiple fields can be separated by commas (e.g., `-created_at,title`).
                 *     * **Default:** `-started_at`
                 */
                order_by?: string | null;
            };
            header?: never;
            path?: never;
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
                    "application/json": components["schemas"]["PaginatedList_ScheduleJobRead_"];
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
    create_schedule_job_api_v1_schedule_jobs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ScheduleJobCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScheduleJobRead"];
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
    get_schedule_job_api_v1_schedule_jobs__schedule_job_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_job_id: string;
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
                    "application/json": components["schemas"]["ScheduleJobRead"];
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
    put_schedule_job_api_v1_schedule_jobs__schedule_job_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_job_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ScheduleJobPut"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScheduleJobRead"];
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
    delete_schedule_job_api_v1_schedule_jobs__schedule_job_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_job_id: string;
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
                    "application/json": components["schemas"]["DeleteResponse"];
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
    patch_schedule_job_api_v1_schedule_jobs__schedule_job_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_job_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ScheduleJobPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScheduleJobRead"];
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
