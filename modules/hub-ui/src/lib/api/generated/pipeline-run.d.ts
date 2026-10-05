/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/pipeline-runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Pipeline Runs */
        get: operations["list_pipeline_runs_api_v1_pipeline_runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Pipeline Run */
        get: operations["get_pipeline_run_api_v1_pipeline_runs__run_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/attempts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Execution Attempts */
        get: operations["list_execution_attempts_api_v1_pipeline_runs__run_id__attempts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/attempts/{attempt_id}/deliveries": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Execution Deliveries */
        get: operations["list_execution_deliveries_api_v1_pipeline_runs__run_id__attempts__attempt_id__deliveries_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/attempts/{attempt_id}/replies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Execution Replies */
        get: operations["list_execution_replies_api_v1_pipeline_runs__run_id__attempts__attempt_id__replies_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/lease": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Renew Pipeline Run Lease */
        put: operations["renew_pipeline_run_lease_api_v1_pipeline_runs__run_id__lease_put"];
        /** Acquire Pipeline Run Lease */
        post: operations["acquire_pipeline_run_lease_api_v1_pipeline_runs__run_id__lease_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/lease/release": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Release Pipeline Run Lease */
        post: operations["release_pipeline_run_lease_api_v1_pipeline_runs__run_id__lease_release_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/attempts/implementation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Prepare Implementation Attempt
         * @description Persist an immutable attempt before any external delegation.
         */
        post: operations["prepare_implementation_attempt_api_v1_pipeline_runs__run_id__attempts_implementation_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/advance": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Advance Pipeline Run
         * @description Trigger manual run progression check (PR detection or CI verification).
         */
        post: operations["advance_pipeline_run_api_v1_pipeline_runs__run_id__advance_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/pause": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Pause Pipeline Run
         * @description Pause an active pipeline run.
         */
        post: operations["pause_pipeline_run_api_v1_pipeline_runs__run_id__pause_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/resume": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Resume Pipeline Run
         * @description Resume a paused pipeline run.
         */
        post: operations["resume_pipeline_run_api_v1_pipeline_runs__run_id__resume_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Cancel Pipeline Run
         * @description Cancel a pipeline run.
         */
        post: operations["cancel_pipeline_run_api_v1_pipeline_runs__run_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/attach-pr": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Attach Pull Request
         * @description Worker callback: attach opened PR to run and transition to awaiting_ci.
         */
        post: operations["attach_pull_request_api_v1_pipeline_runs__run_id__attach_pr_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/attempts/{attempt_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Complete Attempt
         * @description Worker callback: record attempt completion or failure.
         */
        post: operations["complete_attempt_api_v1_pipeline_runs__run_id__attempts__attempt_id__complete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export interface components {
    schemas: {
        /** AttachPRRequest */
        AttachPRRequest: {
            /** Pull Number */
            pull_number: number;
            /** Pull Url */
            pull_url?: string | null;
        };
        /** CompleteAttemptRequest */
        CompleteAttemptRequest: {
            /**
             * Status
             * @enum {string}
             */
            status: "completed" | "failed";
            /** Failure Code */
            failure_code?: string | null;
            /** Failure Detail */
            failure_detail?: string | null;
        };
        /**
         * ExecutionAttemptKind
         * @enum {string}
         */
        ExecutionAttemptKind: "implementation" | "ci-fix" | "conflict-fix";
        /** ExecutionAttemptList */
        ExecutionAttemptList: {
            /** Items */
            items: components["schemas"]["ExecutionAttemptRead"][];
            /** Total Count */
            total_count: number;
            summary: components["schemas"]["PipelineRunSummary"];
        };
        /** ExecutionAttemptRead */
        ExecutionAttemptRead: {
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
             * Pipeline Run Id
             * Format: uuid
             */
            pipeline_run_id: string;
            /** Attempt Number */
            attempt_number: number;
            /** Epoch */
            epoch: number;
            kind: components["schemas"]["ExecutionAttemptKind"];
            state: components["schemas"]["ExecutionAttemptState"];
            /** Request Snapshot */
            request_snapshot: {
                [key: string]: unknown;
            };
            /** Request Digest */
            request_digest: string;
            /**
             * Idempotency Key
             * Format: uuid
             */
            idempotency_key: string;
            /** External Correlation Id */
            external_correlation_id: string | null;
            /** External Status */
            external_status: string | null;
            /** Conversation Url */
            conversation_url: string | null;
            /** Started At */
            started_at: string | null;
            /** Finished At */
            finished_at: string | null;
            /** Failure Code */
            failure_code: string | null;
            /** Failure Detail */
            failure_detail: string | null;
        };
        /**
         * ExecutionAttemptState
         * @enum {string}
         */
        ExecutionAttemptState: "planned" | "dispatching" | "running" | "suspended" | "completed" | "failed";
        /** ExecutionDeliveryRead */
        ExecutionDeliveryRead: {
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
             * Execution Attempt Id
             * Format: uuid
             */
            execution_attempt_id: string;
            /** Delivery Number */
            delivery_number: number;
            /**
             * Cause
             * @enum {string}
             */
            cause: "initial" | "silent" | "quota" | "resume";
            /** External Id */
            external_id: string | null;
            /** Posted At */
            posted_at: string | null;
        };
        /** ExecutionReplyRead */
        ExecutionReplyRead: {
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
             * Execution Attempt Id
             * Format: uuid
             */
            execution_attempt_id: string;
            /** External Id */
            external_id: string;
            /** Author */
            author: string;
            /**
             * Replied At
             * Format: date-time
             */
            replied_at: string;
            /** Excerpt */
            excerpt: string | null;
            /** Is Quota Limit */
            is_quota_limit: boolean;
        };
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** ImplementationRequest */
        ImplementationRequest: {
            /**
             * Version
             * @default 2
             * @constant
             */
            version: 2;
            /**
             * Kind
             * @default implementation
             * @enum {string}
             */
            kind: "implementation" | "ci-fix" | "conflict-fix";
            /** Correlation Marker */
            correlation_marker: string;
            /** Repository */
            repository: string;
            pull_request: components["schemas"]["PullRequestSnapshot"];
            /** Instructions */
            instructions: string;
        };
        /** LeaseGrant */
        LeaseGrant: {
            /**
             * Run Id
             * Format: uuid
             */
            run_id: string;
            /** Owner */
            owner: string;
            /**
             * Token
             * Format: uuid
             */
            token: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /** Run Revision */
            run_revision: number;
        };
        /** LeaseMutation */
        LeaseMutation: {
            /** Owner */
            owner: string;
            /**
             * Token
             * Format: uuid
             */
            token: string;
            /**
             * Ttl Seconds
             * @default 60
             */
            ttl_seconds: number;
        };
        /** LeaseRequest */
        LeaseRequest: {
            /** Owner */
            owner: string;
            /**
             * Ttl Seconds
             * @default 60
             */
            ttl_seconds: number;
        };
        LinkedIssue: CommonComponents["schemas"]["LinkedIssue"];
        /** PauseRunRequest */
        PauseRunRequest: {
            /** Reason */
            reason?: string | null;
        };
        /** PipelineRunList */
        PipelineRunList: {
            /** Items */
            items: components["schemas"]["PipelineRunRead"][];
            /** Total Count */
            total_count: number;
        };
        PipelineRunRead: CommonComponents["schemas"]["PipelineRunRead"];
        PipelineRunState: CommonComponents["schemas"]["PipelineRunState"];
        /**
         * PipelineRunSummary
         * @description What a run has cost so far: how often an agent was asked, and how long the run has taken.
         */
        PipelineRunSummary: {
            /** Attempts By Kind */
            attempts_by_kind: {
                [key: string]: number;
            };
            /** Requests Sent */
            requests_sent: number;
            /** Quota Limit Replies */
            quota_limit_replies: number;
            /**
             * Started At
             * Format: date-time
             */
            started_at: string;
            /** Finished At */
            finished_at: string | null;
            /** Elapsed Seconds */
            elapsed_seconds: number;
        };
        /** PrepareImplementationAttempt */
        PrepareImplementationAttempt: {
            /** Owner */
            owner: string;
            /**
             * Token
             * Format: uuid
             */
            token: string;
            /** Expected Run Revision */
            expected_run_revision: number;
        };
        /** PreparedImplementationAttempt */
        PreparedImplementationAttempt: {
            attempt: components["schemas"]["ExecutionAttemptRead"];
            request: components["schemas"]["ImplementationRequest"];
            /** Run Revision */
            run_revision: number;
            /** Created */
            created: boolean;
        };
        PullRequestSnapshot: CommonComponents["schemas"]["PullRequestSnapshot"];
        /** ResumeRunRequest */
        ResumeRunRequest: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Expected Revision */
            expected_revision: number;
            /** Answer Id */
            answer_id?: string | null;
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
    list_pipeline_runs_api_v1_pipeline_runs_get: {
        parameters: {
            query?: {
                project_id?: string | null;
                offset?: number;
                limit?: number;
                state?: components["schemas"]["PipelineRunState"] | null;
                search?: string;
                pull_number?: number | null;
                group_key?: string | null;
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
                    "application/json": components["schemas"]["PipelineRunList"];
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
    get_pipeline_run_api_v1_pipeline_runs__run_id__get: {
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
                    "application/json": components["schemas"]["PipelineRunRead"];
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
    list_execution_attempts_api_v1_pipeline_runs__run_id__attempts_get: {
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
                    "application/json": components["schemas"]["ExecutionAttemptList"];
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
    list_execution_deliveries_api_v1_pipeline_runs__run_id__attempts__attempt_id__deliveries_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
                attempt_id: string;
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
                    "application/json": components["schemas"]["ExecutionDeliveryRead"][];
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
    list_execution_replies_api_v1_pipeline_runs__run_id__attempts__attempt_id__replies_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
                attempt_id: string;
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
                    "application/json": components["schemas"]["ExecutionReplyRead"][];
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
    renew_pipeline_run_lease_api_v1_pipeline_runs__run_id__lease_put: {
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
                "application/json": components["schemas"]["LeaseMutation"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LeaseGrant"];
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
    acquire_pipeline_run_lease_api_v1_pipeline_runs__run_id__lease_post: {
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
                "application/json": components["schemas"]["LeaseRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LeaseGrant"];
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
    release_pipeline_run_lease_api_v1_pipeline_runs__run_id__lease_release_post: {
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
                "application/json": components["schemas"]["LeaseMutation"];
            };
        };
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
    prepare_implementation_attempt_api_v1_pipeline_runs__run_id__attempts_implementation_post: {
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
                "application/json": components["schemas"]["PrepareImplementationAttempt"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PreparedImplementationAttempt"];
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
    advance_pipeline_run_api_v1_pipeline_runs__run_id__advance_post: {
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
                    "application/json": components["schemas"]["PipelineRunRead"];
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
    pause_pipeline_run_api_v1_pipeline_runs__run_id__pause_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PauseRunRequest"] | null;
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineRunRead"];
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
    resume_pipeline_run_api_v1_pipeline_runs__run_id__resume_post: {
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
                "application/json": components["schemas"]["ResumeRunRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineRunRead"];
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
    cancel_pipeline_run_api_v1_pipeline_runs__run_id__cancel_post: {
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
                    "application/json": components["schemas"]["PipelineRunRead"];
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
    attach_pull_request_api_v1_pipeline_runs__run_id__attach_pr_post: {
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
                "application/json": components["schemas"]["AttachPRRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PipelineRunRead"];
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
    complete_attempt_api_v1_pipeline_runs__run_id__attempts__attempt_id__complete_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
                attempt_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompleteAttemptRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExecutionAttemptRead"];
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
