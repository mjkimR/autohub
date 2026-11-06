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
    "/api/v1/projects/{project_id}/work-plans/{plan_id}/items/{item_id}/recover": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Recover Work Item */
        post: operations["recover_work_item_api_v1_projects__project_id__work_plans__plan_id__items__item_id__recover_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/work-plans/{plan_id}/items/{item_id}/recoveries": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Work Item Recoveries */
        get: operations["work_item_recoveries_api_v1_projects__project_id__work_plans__plan_id__items__item_id__recoveries_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/work-plans/{plan_id}/items/{item_id}/replacement-links": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Replacement Links */
        get: operations["replacement_links_api_v1_projects__project_id__work_plans__plan_id__items__item_id__replacement_links_get"];
        put?: never;
        /** Link Replacement */
        post: operations["link_replacement_api_v1_projects__project_id__work_plans__plan_id__items__item_id__replacement_links_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/work-plans/{plan_id}/items/{item_id}/replacement-links/{link_id}/acceptances": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Accept Replacement */
        post: operations["accept_replacement_api_v1_projects__project_id__work_plans__plan_id__items__item_id__replacement_links__link_id__acceptances_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/work-plans/{plan_id}/items/{item_id}/replacement-links/{link_id}/withdraw": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Withdraw Replacement */
        post: operations["withdraw_replacement_api_v1_projects__project_id__work_plans__plan_id__items__item_id__replacement_links__link_id__withdraw_post"];
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
        /** RecoveryEligibility */
        RecoveryEligibility: {
            /** Eligible */
            eligible: boolean;
            /** Reason */
            reason: string;
            /** Next Action */
            next_action: string;
            /** Run Revision */
            run_revision?: number | null;
            /** Pending State */
            pending_state?: string | null;
            /** Pending Detail */
            pending_detail?: string | null;
        };
        /** RecoveryEventRead */
        RecoveryEventRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Kind */
            kind: string;
            /** Detail */
            detail: string;
            /** Evidence */
            evidence: {
                [key: string]: unknown;
            };
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** ReplacementAcceptCommand */
        ReplacementAcceptCommand: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Reason */
            reason: string;
            /** Expected Original Revision */
            expected_original_revision: number;
            /** Expected Replacement Revision */
            expected_replacement_revision: number;
            /** Expected Evidence Revision */
            expected_evidence_revision: number;
            /**
             * Dependent Item Id
             * Format: uuid
             */
            dependent_item_id: string;
            /** Original Digest */
            original_digest: string;
            /** Replacement Digest */
            replacement_digest: string;
            /** Merge Sha */
            merge_sha: string;
            /**
             * Execution Id
             * Format: uuid
             */
            execution_id: string;
        };
        /** ReplacementAcceptanceRead */
        ReplacementAcceptanceRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Dependent Item Id
             * Format: uuid
             */
            dependent_item_id: string;
            /** Active */
            active: boolean;
            /** Consumed */
            consumed: boolean;
            snapshot: components["schemas"]["ReplacementSnapshot"];
            /** Actor */
            actor: string;
            /** Reason */
            reason: string;
        };
        /** ReplacementEndpoint */
        ReplacementEndpoint: {
            /**
             * Plan Id
             * Format: uuid
             */
            plan_id: string;
            /**
             * Item Id
             * Format: uuid
             */
            item_id: string;
            /** Key */
            key: string;
            /** Title */
            title: string;
            /** Description */
            description: string;
            /** Acceptance */
            acceptance: string;
            /** Digest */
            digest: string;
            /** Plan Revision */
            plan_revision: number;
            /** Plan State */
            plan_state: string;
            /** Item State */
            item_state: string;
            /** Repository */
            repository: string;
            /**
             * Connector Id
             * Format: uuid
             */
            connector_id: string;
            /** Target */
            target: string;
            /** Branch */
            branch: string | null;
            /** Execution Id */
            execution_id: string | null;
            /** Pull Number */
            pull_number: number | null;
            /** Pull Url */
            pull_url: string | null;
            /** Merge Sha */
            merge_sha: string | null;
            /** Completed At */
            completed_at: string | null;
        };
        /** ReplacementEventRead */
        ReplacementEventRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Acceptance Id */
            acceptance_id: string | null;
            /** Kind */
            kind: string;
            /** Actor */
            actor: string;
            /** Reason */
            reason: string;
            /** Revision */
            revision: number;
            /** Evidence */
            evidence: {
                [key: string]: unknown;
            };
            /** Created At */
            created_at: string;
        };
        /** ReplacementLinkCommand */
        ReplacementLinkCommand: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Reason */
            reason: string;
            /** Expected Original Revision */
            expected_original_revision: number;
            /** Expected Replacement Revision */
            expected_replacement_revision: number;
            /** Expected Evidence Revision */
            expected_evidence_revision: number;
            /**
             * Replacement Item Id
             * Format: uuid
             */
            replacement_item_id: string;
        };
        /** ReplacementLinkRead */
        ReplacementLinkRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Active */
            active: boolean;
            snapshot: components["schemas"]["ReplacementSnapshot"];
            current_replacement: components["schemas"]["ReplacementEndpoint"];
            /** Actor */
            actor: string;
            /** Reason */
            reason: string;
            /** Acceptances */
            acceptances: components["schemas"]["ReplacementAcceptanceRead"][];
            /** Events */
            events: components["schemas"]["ReplacementEventRead"][];
            /**
             * Event Offset
             * @default 0
             */
            event_offset: number;
            /**
             * Event Total Count
             * @default 0
             */
            event_total_count: number;
        };
        /** ReplacementRead */
        ReplacementRead: {
            original: components["schemas"]["ReplacementEndpoint"];
            candidate?: components["schemas"]["ReplacementEndpoint"] | null;
            /** Evidence Revision */
            evidence_revision: number;
            /** Links */
            links: components["schemas"]["ReplacementLinkRead"][];
            /**
             * History Offset
             * @default 0
             */
            history_offset: number;
            /**
             * History Total Count
             * @default 0
             */
            history_total_count: number;
            /**
             * History Limit
             * @default 10
             */
            history_limit: number;
            result?: components["schemas"]["ReplacementResult"] | null;
        };
        /** ReplacementResult */
        ReplacementResult: {
            /** Operation */
            operation: string;
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /**
             * Link Id
             * Format: uuid
             */
            link_id: string;
            /** Acceptance Id */
            acceptance_id: string | null;
            /** Original Revision */
            original_revision: number;
            /** Evidence Revision */
            evidence_revision: number;
        };
        /** ReplacementSnapshot */
        ReplacementSnapshot: {
            original: components["schemas"]["ReplacementEndpoint"];
            replacement: components["schemas"]["ReplacementEndpoint"];
        };
        /** ReplacementWithdrawCommand */
        ReplacementWithdrawCommand: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Reason */
            reason: string;
            /** Expected Original Revision */
            expected_original_revision: number;
            /** Expected Replacement Revision */
            expected_replacement_revision: number;
            /** Expected Evidence Revision */
            expected_evidence_revision: number;
            /** Acceptance Id */
            acceptance_id?: string | null;
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
            /** Branch */
            branch: string | null;
            /** Attach Branch */
            attach_branch: string | null;
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
            recovery: components["schemas"]["RecoveryEligibility"] | null;
        };
        /** WorkItemRecover */
        WorkItemRecover: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Expected Revision */
            expected_revision: number;
            /** Expected Run Revision */
            expected_run_revision?: number | null;
            /** Reason */
            reason: string;
        };
        /** WorkItemRecoveryList */
        WorkItemRecoveryList: {
            /** Items */
            items: components["schemas"]["WorkItemRecoveryRead"][];
            /** Total Count */
            total_count: number;
        };
        /** WorkItemRecoveryRead */
        WorkItemRecoveryRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Actor */
            actor: string;
            /** Reason */
            reason: string;
            /** Command */
            command: {
                [key: string]: unknown;
            };
            /** Prior Outcome */
            prior_outcome: {
                [key: string]: unknown;
            };
            /** Accepted Revision */
            accepted_revision: number;
            /** Accepted Run Revision */
            accepted_run_revision: number | null;
            /** State */
            state: string;
            /** Detail */
            detail: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Refusal Reason */
            refusal_reason?: string | null;
            /** Events */
            events?: components["schemas"]["RecoveryEventRead"][];
        };
        /** WorkItemRecoveryResult */
        WorkItemRecoveryResult: {
            recovery: components["schemas"]["WorkItemRecoveryRead"];
            item: components["schemas"]["WorkItemRead"];
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
            /**
             * Attach Branch
             * @description Explicit attach: an activity branch (plan-<slug> or dev-<slug>) that already exists on the remote and carries this work. Without it the item starts dev-<key>, and an existing branch of that name refuses the start.
             */
            attach_branch?: string | null;
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
    recover_work_item_api_v1_projects__project_id__work_plans__plan_id__items__item_id__recover_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                plan_id: string;
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkItemRecover"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkItemRecoveryResult"];
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
    work_item_recoveries_api_v1_projects__project_id__work_plans__plan_id__items__item_id__recoveries_get: {
        parameters: {
            query?: {
                offset?: number;
                limit?: number;
            };
            header?: never;
            path: {
                project_id: string;
                plan_id: string;
                item_id: string;
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
                    "application/json": components["schemas"]["WorkItemRecoveryList"];
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
    replacement_links_api_v1_projects__project_id__work_plans__plan_id__items__item_id__replacement_links_get: {
        parameters: {
            query?: {
                replacement_item_id?: string | null;
                offset?: number;
                limit?: number;
                event_link_id?: string | null;
                event_offset?: number;
            };
            header?: never;
            path: {
                project_id: string;
                plan_id: string;
                item_id: string;
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
                    "application/json": components["schemas"]["ReplacementRead"];
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
    link_replacement_api_v1_projects__project_id__work_plans__plan_id__items__item_id__replacement_links_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                plan_id: string;
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReplacementLinkCommand"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReplacementRead"];
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
    accept_replacement_api_v1_projects__project_id__work_plans__plan_id__items__item_id__replacement_links__link_id__acceptances_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                plan_id: string;
                item_id: string;
                link_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReplacementAcceptCommand"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReplacementRead"];
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
    withdraw_replacement_api_v1_projects__project_id__work_plans__plan_id__items__item_id__replacement_links__link_id__withdraw_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                plan_id: string;
                item_id: string;
                link_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReplacementWithdrawCommand"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReplacementRead"];
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
