/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/schedule_configs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Schedule Configs */
        get: operations["get_schedule_configs_api_v1_schedule_configs_get"];
        put?: never;
        /** Create Schedule Config */
        post: operations["create_schedule_config_api_v1_schedule_configs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/schedule_configs/{schedule_config_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Schedule Config */
        get: operations["get_schedule_config_api_v1_schedule_configs__schedule_config_id__get"];
        /** Put Schedule Config */
        put: operations["put_schedule_config_api_v1_schedule_configs__schedule_config_id__put"];
        post?: never;
        /** Delete Schedule Config */
        delete: operations["delete_schedule_config_api_v1_schedule_configs__schedule_config_id__delete"];
        options?: never;
        head?: never;
        /** Patch Schedule Config */
        patch: operations["patch_schedule_config_api_v1_schedule_configs__schedule_config_id__patch"];
        trace?: never;
    };
}
export interface components {
    schemas: {
        DeleteResponse: CommonComponents["schemas"]["DeleteResponse"];
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** PaginatedList[ScheduleConfigRead] */
        PaginatedList_ScheduleConfigRead_: {
            /** Items */
            items: components["schemas"]["ScheduleConfigRead"][];
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
        /** ScheduleConfigCreate */
        ScheduleConfigCreate: {
            /**
             * Name
             * @description Human-readable name of the schedule.
             */
            name: string;
            /**
             * Description
             * @description Optional description of what this schedule does.
             */
            description?: string | null;
            /**
             * Task Func
             * @description Dotted path to the task function to execute (e.g. 'tasks.send_report').
             */
            task_func: string;
            /**
             * Cron Expression
             * @description Cron expression for time-based scheduling (e.g. '0 9 * * 1-5'). Mutually exclusive with interval_seconds.
             */
            cron_expression?: string | null;
            /**
             * Interval Seconds
             * @description Fixed interval in seconds between executions. Mutually exclusive with cron_expression.
             */
            interval_seconds?: number | null;
            /**
             * Payload
             * @description Arbitrary JSON payload passed to the task function as kwargs.
             * @default {}
             */
            payload: {
                [key: string]: unknown;
            };
            /**
             * Enabled
             * @description Whether this schedule is active and should be picked up by the dispatcher.
             * @default true
             */
            enabled: boolean;
            /**
             * Start At
             * @description Optional datetime after which the schedule becomes active.
             */
            start_at?: string | null;
            /**
             * End At
             * @description Optional datetime after which the schedule is no longer executed.
             */
            end_at?: string | null;
        };
        /** ScheduleConfigPatch */
        ScheduleConfigPatch: {
            /**
             * Name
             * @description Human-readable name of the schedule.
             */
            name?: string | null;
            /**
             * Description
             * @description Optional description of what this schedule does.
             */
            description?: string | null;
            /**
             * Task Func
             * @description Dotted path to the task function to execute.
             */
            task_func?: string | null;
            /**
             * Cron Expression
             * @description Cron expression for time-based scheduling.
             */
            cron_expression?: string | null;
            /**
             * Interval Seconds
             * @description Fixed interval in seconds between executions.
             */
            interval_seconds?: number | null;
            /**
             * Payload
             * @description Arbitrary JSON payload passed to the task function as kwargs.
             */
            payload?: {
                [key: string]: unknown;
            } | null;
            /**
             * Enabled
             * @description Whether this schedule is active.
             */
            enabled?: boolean | null;
            /**
             * Start At
             * @description Optional datetime after which the schedule becomes active.
             */
            start_at?: string | null;
            /**
             * End At
             * @description Optional datetime after which the schedule is no longer executed.
             */
            end_at?: string | null;
        };
        /** ScheduleConfigPut */
        ScheduleConfigPut: {
            /**
             * Name
             * @description Human-readable name of the schedule.
             */
            name: string;
            /**
             * Description
             * @description Optional description of what this schedule does.
             */
            description?: string | null;
            /**
             * Task Func
             * @description Dotted path to the task function to execute (e.g. 'tasks.send_report').
             */
            task_func: string;
            /**
             * Cron Expression
             * @description Cron expression for time-based scheduling (e.g. '0 9 * * 1-5'). Mutually exclusive with interval_seconds.
             */
            cron_expression?: string | null;
            /**
             * Interval Seconds
             * @description Fixed interval in seconds between executions. Mutually exclusive with cron_expression.
             */
            interval_seconds?: number | null;
            /**
             * Payload
             * @description Arbitrary JSON payload passed to the task function as kwargs.
             * @default {}
             */
            payload: {
                [key: string]: unknown;
            };
            /**
             * Enabled
             * @description Whether this schedule is active and should be picked up by the dispatcher.
             * @default true
             */
            enabled: boolean;
            /**
             * Start At
             * @description Optional datetime after which the schedule becomes active.
             */
            start_at?: string | null;
            /**
             * End At
             * @description Optional datetime after which the schedule is no longer executed.
             */
            end_at?: string | null;
        };
        /** ScheduleConfigRead */
        ScheduleConfigRead: {
            /**
             * Name
             * @description Human-readable name of the schedule.
             */
            name: string;
            /**
             * Description
             * @description Optional description of what this schedule does.
             */
            description?: string | null;
            /**
             * Task Func
             * @description Dotted path to the task function to execute (e.g. 'tasks.send_report').
             */
            task_func: string;
            /**
             * Cron Expression
             * @description Cron expression for time-based scheduling (e.g. '0 9 * * 1-5'). Mutually exclusive with interval_seconds.
             */
            cron_expression?: string | null;
            /**
             * Interval Seconds
             * @description Fixed interval in seconds between executions. Mutually exclusive with cron_expression.
             */
            interval_seconds?: number | null;
            /**
             * Payload
             * @description Arbitrary JSON payload passed to the task function as kwargs.
             * @default {}
             */
            payload: {
                [key: string]: unknown;
            };
            /**
             * Enabled
             * @description Whether this schedule is active and should be picked up by the dispatcher.
             * @default true
             */
            enabled: boolean;
            /**
             * Start At
             * @description Optional datetime after which the schedule becomes active.
             */
            start_at?: string | null;
            /**
             * End At
             * @description Optional datetime after which the schedule is no longer executed.
             */
            end_at?: string | null;
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
            /**
             * Last Run At
             * @description Timestamp of the most recent execution.
             */
            last_run_at: string | null;
            /**
             * Next Run At
             * @description Timestamp of the next scheduled execution.
             */
            next_run_at: string | null;
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
    get_schedule_configs_api_v1_schedule_configs_get: {
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
                /** @description Filter by task function path (case-insensitive substring) */
                task_func?: string | null;
                /** @description Filter by enabled status */
                enabled?: boolean | null;
                /**
                 * @description **Order by options:**
                 *
                 *     * `name`: Sort by name
                 *     * `created_at`: Sort by creation time
                 *     * `updated_at`: Sort by update time
                 *     * `next_run_at`: Sort by next run time
                 *     * `last_run_at`: Sort by last run time
                 *     * `id`: Sort by ID
                 *
                 *     **Usage:**
                 *     * Prefix with `-` for descending order (e.g., `-title`).
                 *     * Multiple fields can be separated by commas (e.g., `-created_at,title`).
                 *     * **Default:** `-created_at`
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
                    "application/json": components["schemas"]["PaginatedList_ScheduleConfigRead_"];
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
    create_schedule_config_api_v1_schedule_configs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ScheduleConfigCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScheduleConfigRead"];
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
    get_schedule_config_api_v1_schedule_configs__schedule_config_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_config_id: string;
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
                    "application/json": components["schemas"]["ScheduleConfigRead"];
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
    put_schedule_config_api_v1_schedule_configs__schedule_config_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_config_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ScheduleConfigPut"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScheduleConfigRead"];
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
    delete_schedule_config_api_v1_schedule_configs__schedule_config_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_config_id: string;
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
    patch_schedule_config_api_v1_schedule_configs__schedule_config_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_config_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ScheduleConfigPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScheduleConfigRead"];
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
