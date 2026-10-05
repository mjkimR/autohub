/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/projects/{project_id}/work-plans": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Work Plans */
        get: operations["list_work_plans_api_v1_projects__project_id__work_plans_get"];
        put?: never;
        /**
         * Create Work Plan
         * @description Create a seed/proposal/held plan, or register active work for immediate eligibility.
         */
        post: operations["create_work_plan_api_v1_projects__project_id__work_plans_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/work-plans/{plan_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Work Plan */
        get: operations["get_work_plan_api_v1_projects__project_id__work_plans__plan_id__get"];
        /** Update Work Plan */
        put: operations["update_work_plan_api_v1_projects__project_id__work_plans__plan_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/work-plans/{plan_id}/control": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Control Work Plan
         * @description Pause/resume/revoke unstarted work only; started PR runs continue through merging.
         */
        post: operations["control_work_plan_api_v1_projects__project_id__work_plans__plan_id__control_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/work-plans/{plan_id}/group": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Set Work Plan Group
         * @description Change classification at any lifecycle stage without starting or controlling execution.
         */
        patch: operations["set_work_plan_group_api_v1_projects__project_id__work_plans__plan_id__group_patch"];
        trace?: never;
    };
    "/api/v1/projects/{project_id}/work-plans/registrations/{request_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Registered Plan */
        get: operations["get_registered_plan_api_v1_projects__project_id__work_plans_registrations__request_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/work-plans/{plan_id}/activity": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Plan Activity */
        get: operations["list_plan_activity_api_v1_projects__project_id__work_plans__plan_id__activity_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/work-plans/{plan_id}/comments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Plan Comment */
        post: operations["add_plan_comment_api_v1_projects__project_id__work_plans__plan_id__comments_post"];
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
        /** IssueMirrorRead */
        IssueMirrorRead: {
            /** Issue Url */
            issue_url: string | null;
            /** Error */
            error: string | null;
            /** Pending */
            pending: boolean;
        };
        /** PlanActivityList */
        PlanActivityList: {
            /** Items */
            items: components["schemas"]["PlanActivityRead"][];
            /** Total Count */
            total_count: number;
        };
        /** PlanActivityRead */
        PlanActivityRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "comment" | "created" | "updated" | "control" | "completed";
            /** Actor */
            actor: string;
            /** Revision */
            revision: number;
            /** Body */
            body: string;
            /** Changes */
            changes: {
                [key: string]: unknown;
            };
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** PlanComment */
        PlanComment: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Body */
            body: string;
        };
        /** PlanControl */
        PlanControl: {
            /**
             * Action
             * @enum {string}
             */
            action: "pause" | "resume" | "revoke" | "propose" | "draft" | "ready";
            /** Expected Revision */
            expected_revision: number;
            /**
             * Reason
             * @default
             */
            reason: string;
        };
        ValidationError: CommonComponents["schemas"]["ValidationError"];
        /** WorkItemRead */
        WorkItemRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Key */
            key: string;
            /** Title */
            title: string;
            /** Description */
            description: string;
            /** Acceptance */
            acceptance: string;
            /** State */
            state: string;
            /** Detail */
            detail: string | null;
            /** Depends On */
            depends_on: string[];
            /** Pipeline Run Id */
            pipeline_run_id: string | null;
            /** Pipeline Run Retired At */
            pipeline_run_retired_at: string | null;
            /** Pull Url */
            pull_url: string | null;
            /** Merge Sha */
            merge_sha: string | null;
            /** Started At */
            started_at: string | null;
            /** Completed At */
            completed_at: string | null;
            issue: components["schemas"]["IssueMirrorRead"] | null;
        };
        /** WorkItemWrite */
        WorkItemWrite: {
            /** Key */
            key: string;
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Acceptance
             * @default
             */
            acceptance: string;
            /** Depends On */
            depends_on?: string[];
        };
        /** WorkPlanCreate */
        WorkPlanCreate: {
            /** Title */
            title: string;
            /** Group Key */
            group_key?: string | null;
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Base Branch
             * @default main
             */
            base_branch: string;
            /**
             * Scheduled At
             * @description Earliest start time with timezone; null allows immediate execution. Dependencies and capacity still apply.
             */
            scheduled_at?: string | null;
            /** Depends On */
            depends_on?: string[];
            /** Items */
            items?: components["schemas"]["WorkItemWrite"][];
            /**
             * State
             * @default active
             * @enum {string}
             */
            state: "draft" | "proposed" | "paused" | "active";
            /**
             * Request Id
             * @description Reuse on retries to recover the original plan; different content with the same key conflicts
             */
            request_id?: string | null;
        };
        /** WorkPlanGroupUpdate */
        WorkPlanGroupUpdate: {
            /** Group Key */
            group_key: string | null;
            /** Expected Revision */
            expected_revision: number;
            /**
             * Reason
             * @default
             */
            reason: string;
        };
        /** WorkPlanList */
        WorkPlanList: {
            /** Items */
            items: components["schemas"]["WorkPlanRead"][];
            /** Total Count */
            total_count: number;
        };
        /** WorkPlanRead */
        WorkPlanRead: {
            /** Registration Request Id */
            registration_request_id: string | null;
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
            /** Group Key */
            group_key: string | null;
            /** Title */
            title: string;
            /** Description */
            description: string;
            /** Base Branch */
            base_branch: string;
            /** State */
            state: string;
            /** Revision */
            revision: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Scheduled At */
            scheduled_at: string | null;
            /** Completed At */
            completed_at: string | null;
            /** Depends On */
            depends_on: string[];
            /** Items */
            items: components["schemas"]["WorkItemRead"][];
            issue: components["schemas"]["IssueMirrorRead"] | null;
        };
        /** WorkPlanUpdate */
        WorkPlanUpdate: {
            /** Title */
            title: string;
            /** Group Key */
            group_key?: string | null;
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Base Branch
             * @default main
             */
            base_branch: string;
            /**
             * Scheduled At
             * @description Earliest start time with timezone; null allows immediate execution. Dependencies and capacity still apply.
             */
            scheduled_at?: string | null;
            /** Depends On */
            depends_on?: string[];
            /** Items */
            items?: components["schemas"]["WorkItemWrite"][];
            /** Expected Revision */
            expected_revision: number;
            /**
             * Reason
             * @default
             */
            reason: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export interface operations {
    list_work_plans_api_v1_projects__project_id__work_plans_get: {
        parameters: {
            query?: {
                offset?: number;
                limit?: number;
                state?: string | null;
                group_key?: string | null;
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
                    "application/json": components["schemas"]["WorkPlanList"];
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
    create_work_plan_api_v1_projects__project_id__work_plans_post: {
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
                "application/json": components["schemas"]["WorkPlanCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkPlanRead"];
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
    get_work_plan_api_v1_projects__project_id__work_plans__plan_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                plan_id: string;
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
                    "application/json": components["schemas"]["WorkPlanRead"];
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
    update_work_plan_api_v1_projects__project_id__work_plans__plan_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkPlanUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkPlanRead"];
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
    control_work_plan_api_v1_projects__project_id__work_plans__plan_id__control_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanControl"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkPlanRead"];
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
    set_work_plan_group_api_v1_projects__project_id__work_plans__plan_id__group_patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkPlanGroupUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkPlanRead"];
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
    get_registered_plan_api_v1_projects__project_id__work_plans_registrations__request_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                request_id: string;
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
                    "application/json": components["schemas"]["WorkPlanRead"];
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
    list_plan_activity_api_v1_projects__project_id__work_plans__plan_id__activity_get: {
        parameters: {
            query?: {
                offset?: number;
                limit?: number;
                comments_only?: boolean;
            };
            header?: never;
            path: {
                project_id: string;
                plan_id: string;
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
                    "application/json": components["schemas"]["PlanActivityList"];
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
    add_plan_comment_api_v1_projects__project_id__work_plans__plan_id__comments_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanComment"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlanActivityRead"];
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
