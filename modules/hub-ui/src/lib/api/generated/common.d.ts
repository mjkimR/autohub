/** Generated from OpenAPI domain tags. Do not edit manually. */
export interface components {
    schemas: {
        /** AICatalogSessionRead */
        AICatalogSessionRead: {
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
            /** Schedule Config Id */
            schedule_config_id: string | null;
            /** Title */
            title: string;
            /** Work Type */
            work_type: string;
            /** Repository */
            repository: string | null;
            /** State */
            state: string;
            /** External Name */
            external_name: string | null;
            /** Url */
            url: string | null;
            /** Pull Request Url */
            pull_request_url: string | null;
            /** Pipeline Run Id */
            pipeline_run_id: string | null;
            /** Pipeline Run Retired At */
            pipeline_run_retired_at?: string | null;
            /** Result Summary */
            result_summary: string | null;
            /** Failure Detail */
            failure_detail: string | null;
            /** Observed At */
            observed_at: string | null;
        };
        /** DeleteResponse */
        DeleteResponse: {
            /**
             * Success
             * @default true
             */
            success: boolean;
            /** Message */
            message?: string | null;
            /**
             * Identity
             * @description The identity of the deleted object.
             */
            identity?: (string | number)[] | string | number | null;
            /**
             * Representation
             * @description The string representation of the deleted object.
             */
            representation?: string | null;
            /**
             * Meta
             * @description Additional metadata about the delete operation.
             */
            meta?: {
                [key: string]: unknown;
            };
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** JobSnapshot */
        JobSnapshot: {
            /**
             * Id
             * @default 0
             */
            id: number;
            /** Name */
            name: string;
            /** Status */
            status: string;
            /** Conclusion */
            conclusion?: string | null;
            /** Url */
            url?: string | null;
        };
        /** LinkedIssue */
        LinkedIssue: {
            /** Number */
            number: number;
            /** Title */
            title: string;
            /** Body */
            body?: string | null;
            /** Url */
            url: string;
        };
        /** PipelineObservation */
        PipelineObservation: {
            /**
             * Kind
             * @default pipeline_observation
             * @constant
             */
            kind: "pipeline_observation";
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            config: components["schemas"]["PipelineObservationConfig"];
            /** Pulls */
            pulls: components["schemas"]["PullObservation"][];
        };
        /**
         * PipelineObservationConfig
         * @description One repository connection and an explicit, bounded set of PRs to observe.
         */
        PipelineObservationConfig: {
            /** Repository */
            repository: string;
            /**
             * Github Connector Id
             * Format: uuid
             */
            github_connector_id: string;
            /** Pull Numbers */
            pull_numbers: number[];
            verification: components["schemas"]["VerificationConfig"];
        };
        /** PipelineRunRead */
        PipelineRunRead: {
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
             * Ai Catalog Id
             * Format: uuid
             */
            ai_catalog_id: string;
            /** Requested Catalog Id */
            requested_catalog_id?: string | null;
            /** Project Revision */
            project_revision: number;
            /** Pull Number */
            pull_number: number;
            /** Pull Url */
            pull_url: string;
            pull_snapshot: components["schemas"]["PullRequestSnapshot"];
            state: components["schemas"]["PipelineRunState"];
            /** Pause Reason */
            pause_reason: string | null;
            /** Branch */
            branch: string;
            /** Revision */
            revision: number;
            /** Epoch */
            epoch: number;
            /** Lease Owner */
            lease_owner: string | null;
            /** Lease Expires At */
            lease_expires_at: string | null;
            /** Next Action At */
            next_action_at: string | null;
            /** Quota Block Count */
            quota_block_count: number;
        };
        /**
         * PipelineRunState
         * @enum {string}
         */
        PipelineRunState: "queued" | "dispatching" | "implementing" | "awaiting_ci" | "paused" | "blocked" | "completed" | "failed" | "canceled";
        /** PullObservation */
        PullObservation: {
            /** Number */
            number: number;
            /** Head Sha */
            head_sha: string;
            /** Base Sha */
            base_sha: string;
            /** Url */
            url: string;
            result: components["schemas"]["VerificationResult"];
            run?: components["schemas"]["RunSnapshot"] | null;
            /**
             * Draft
             * @default false
             */
            draft: boolean;
            /** Mergeable State */
            mergeable_state?: string | null;
        };
        /**
         * PullRequestSnapshot
         * @description The task specification: the PR as the user wrote it, plus the issues it closes.
         */
        PullRequestSnapshot: {
            /** Number */
            number: number;
            /** Url */
            url: string;
            /** Title */
            title: string;
            /** Body */
            body?: string | null;
            /** Base Ref */
            base_ref: string;
            /** Head Ref */
            head_ref: string;
            /** Head Sha */
            head_sha: string;
            /** Linked Issues */
            linked_issues?: components["schemas"]["LinkedIssue"][];
        };
        /** RunSnapshot */
        RunSnapshot: {
            /** Id */
            id: number;
            /** Attempt */
            attempt: number;
            /** Head Sha */
            head_sha: string;
            /** Status */
            status: string;
            /** Conclusion */
            conclusion?: string | null;
            /** Url */
            url: string;
            /** Jobs */
            jobs?: components["schemas"]["JobSnapshot"][];
        };
        /** Token */
        Token: {
            /** Access Token */
            access_token: string;
            /**
             * Token Type
             * @constant
             */
            token_type: "bearer";
            /** Refresh Token */
            refresh_token?: string | null;
            /** Expires In */
            expires_in?: number | null;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /** VerificationConfig */
        VerificationConfig: {
            /**
             * Workflow
             * @description Workflow filename, not display name.
             */
            workflow: string;
            /**
             * Required Jobs
             * @description Exact GitHub Actions job names.
             */
            required_jobs: string[];
            /**
             * Event
             * @default pull_request
             * @constant
             */
            event: "pull_request";
        };
        /** VerificationResult */
        VerificationResult: {
            status: components["schemas"]["VerificationStatus"];
            /** Reason */
            reason: string;
            /** Missing Jobs */
            missing_jobs?: string[];
            /** Unsuccessful Jobs */
            unsuccessful_jobs?: string[];
        };
        /**
         * VerificationStatus
         * @enum {string}
         */
        VerificationStatus: "passed" | "waiting" | "failed" | "blocked" | "closed";
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
