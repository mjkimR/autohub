/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/projects/{project_id}/agent-schedules": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Agent Schedules
         * @description A project's recurring agent sessions, each with its owned scheduler entry and recent sessions.
         */
        get: operations["list_agent_schedules_api_v1_projects__project_id__agent_schedules_get"];
        put?: never;
        /** Create Agent Schedule */
        post: operations["create_agent_schedule_api_v1_projects__project_id__agent_schedules_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/agent-schedules/{schedule_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Agent Schedule */
        get: operations["get_agent_schedule_api_v1_projects__project_id__agent_schedules__schedule_id__get"];
        /** Update Agent Schedule */
        put: operations["update_agent_schedule_api_v1_projects__project_id__agent_schedules__schedule_id__put"];
        post?: never;
        /** Delete Agent Schedule */
        delete: operations["delete_agent_schedule_api_v1_projects__project_id__agent_schedules__schedule_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/agent-schedules/{schedule_id}/run-now": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Run Agent Schedule Now
         * @description Make the schedule due on the dispatcher's next tick.
         */
        post: operations["run_agent_schedule_now_api_v1_projects__project_id__agent_schedules__schedule_id__run_now_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export interface components {
    schemas: {
        AICatalogSessionRead: CommonComponents["schemas"]["AICatalogSessionRead"];
        /** AgentScheduleList */
        AgentScheduleList: {
            /** Items */
            items: components["schemas"]["AgentScheduleRead"][];
        };
        /** AgentScheduleRead */
        AgentScheduleRead: {
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
             * Project Id
             * Format: uuid
             */
            project_id: string;
            /**
             * Schedule Config Id
             * Format: uuid
             */
            schedule_config_id: string;
            /**
             * Ai Catalog Id
             * Format: uuid
             */
            ai_catalog_id: string;
            /** Work Type */
            work_type: string;
            /** Title */
            title: string;
            /** Prompt */
            prompt: string;
            /** Starting Branch */
            starting_branch: string;
            /** Enabled */
            enabled: boolean;
            /** Cron Expression */
            cron_expression: string | null;
            /** Interval Seconds */
            interval_seconds: number | null;
            /**
             * Task Func
             * @description The scheduler task the owned schedule runs
             * @default
             */
            task_func: string;
            /** Next Run At */
            next_run_at?: string | null;
            /** Last Run At */
            last_run_at?: string | null;
            /** Recent Sessions */
            recent_sessions?: components["schemas"]["AICatalogSessionRead"][];
        };
        /** AgentScheduleWrite */
        AgentScheduleWrite: {
            /**
             * Ai Catalog Id
             * Format: uuid
             * @description Catalog whose sessions this schedule starts; its kind picks the task
             */
            ai_catalog_id: string;
            /**
             * Work Type
             * @description 'task' work ends in a pull request adopted into the pipeline; a 'report' is stored from the session
             * @default task
             * @enum {string}
             */
            work_type: "task" | "report";
            /** Title */
            title: string;
            /** Prompt */
            prompt: string;
            /**
             * Starting Branch
             * @default main
             */
            starting_branch: string;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Cron Expression */
            cron_expression?: string | null;
            /** Interval Seconds */
            interval_seconds?: number | null;
        };
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        ValidationError: CommonComponents["schemas"]["ValidationError"];
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export interface operations {
    list_agent_schedules_api_v1_projects__project_id__agent_schedules_get: {
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
                    "application/json": components["schemas"]["AgentScheduleList"];
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
    create_agent_schedule_api_v1_projects__project_id__agent_schedules_post: {
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
                "application/json": components["schemas"]["AgentScheduleWrite"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentScheduleRead"];
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
    get_agent_schedule_api_v1_projects__project_id__agent_schedules__schedule_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
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
                    "application/json": components["schemas"]["AgentScheduleRead"];
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
    update_agent_schedule_api_v1_projects__project_id__agent_schedules__schedule_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                schedule_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AgentScheduleWrite"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentScheduleRead"];
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
    delete_agent_schedule_api_v1_projects__project_id__agent_schedules__schedule_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                schedule_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
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
    run_agent_schedule_now_api_v1_projects__project_id__agent_schedules__schedule_id__run_now_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
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
                    "application/json": components["schemas"]["AgentScheduleRead"];
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
