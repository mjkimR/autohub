/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Projects */
        get: operations["list_projects_api_v1_projects_get"];
        put?: never;
        /** Create Project */
        post: operations["create_project_api_v1_projects_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/templates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Project Templates
         * @description Versioned starter files for installation in a target repository.
         */
        get: operations["get_project_templates_api_v1_projects_templates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/import_schedule": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Project Schedule
         * @description Atomically adopt a legacy schedule, preserving its trigger, PRs, and history.
         */
        post: operations["import_project_schedule_api_v1_projects_import_schedule_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Project */
        get: operations["get_project_api_v1_projects__project_id__get"];
        put?: never;
        post?: never;
        /** Delete Project */
        delete: operations["delete_project_api_v1_projects__project_id__delete"];
        options?: never;
        head?: never;
        /**
         * Update Project
         * @description Change only the fields present in the body; ``expected_revision`` rejects stale edits.
         */
        patch: operations["update_project_api_v1_projects__project_id__patch"];
        trace?: never;
    };
    "/api/v1/projects/{project_id}/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Enroll Pull Request
         * @description Register one open pull request as a queued pipeline run. Reads GitHub only; posts nothing.
         */
        post: operations["enroll_pull_request_api_v1_projects__project_id__runs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/check": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Check Project
         * @description Read GitHub, verify one current PR run, and identify the token's account. Never writes to GitHub.
         */
        post: operations["check_project_api_v1_projects__project_id__check_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export interface components {
    schemas: {
        /** CheckRequest */
        CheckRequest: {
            /** Pull Number */
            pull_number: number;
        };
        /** ConnectionCheck */
        ConnectionCheck: {
            /**
             * Checked At
             * Format: date-time
             */
            checked_at: string;
            /** Project Revision */
            project_revision: number;
            /** Ready */
            ready: boolean;
            /** Checks */
            checks: components["schemas"]["ConnectionCheckItem"][];
            observation?: components["schemas"]["PipelineObservation"] | null;
            /**
             * Github Login
             * @description GitHub account the connector token acts as; Codex mentions are posted by it.
             */
            github_login?: string | null;
        };
        /** ConnectionCheckItem */
        ConnectionCheckItem: {
            /** Name */
            name: string;
            /**
             * Status
             * @enum {string}
             */
            status: "passed" | "failed" | "skipped";
            /** Detail */
            detail: string;
        };
        /** EnrollPullRequest */
        EnrollPullRequest: {
            /** Pull Number */
            pull_number: number;
            /**
             * Catalog
             * @description AI catalog to deliver this run: a catalog key, or a kind ('codex') when exactly one enabled catalog has it; empty follows the project's selection
             */
            catalog?: string | null;
            /**
             * Implemented
             * @description The pull request already holds its implementation (for example, an agent session opened it); skip the implementation request and start by observing CI
             * @default false
             */
            implemented: boolean;
        };
        /**
         * GitHubAutomationConfig
         * @description Per-project automation policy. Defaults preserve the original unattended flow.
         */
        GitHubAutomationConfig: {
            /**
             * Auto Merge
             * @default true
             */
            auto_merge: boolean;
            /**
             * Merge Method
             * @default squash
             * @enum {string}
             */
            merge_method: "squash" | "merge" | "rebase";
            /**
             * Auto Fix Ci
             * @default true
             */
            auto_fix_ci: boolean;
            /**
             * Auto Fix Conflicts
             * @default true
             */
            auto_fix_conflicts: boolean;
            /**
             * Auto Enroll On Trigger
             * @default true
             */
            auto_enroll_on_trigger: boolean;
            /**
             * Auto Enroll Sessions
             * @default true
             */
            auto_enroll_sessions: boolean;
            /**
             * Dispatch Interval Seconds
             * @default 60
             */
            dispatch_interval_seconds: number;
            /** Max In Flight Runs */
            max_in_flight_runs?: number | null;
            /**
             * Repository Viewer
             * @default default
             */
            repository_viewer: string;
        };
        /**
         * GitHubAutomationPatch
         * @description Omitted fields keep their current value.
         */
        GitHubAutomationPatch: {
            /** Auto Merge */
            auto_merge?: boolean | null;
            /** Merge Method */
            merge_method?: ("squash" | "merge" | "rebase") | null;
            /** Auto Fix Ci */
            auto_fix_ci?: boolean | null;
            /** Auto Fix Conflicts */
            auto_fix_conflicts?: boolean | null;
            /** Auto Enroll On Trigger */
            auto_enroll_on_trigger?: boolean | null;
            /** Auto Enroll Sessions */
            auto_enroll_sessions?: boolean | null;
            /** Dispatch Interval Seconds */
            dispatch_interval_seconds?: number | null;
            /**
             * Max In Flight Runs
             * @description null removes the project limit
             */
            max_in_flight_runs?: number | null;
            /** Repository Viewer */
            repository_viewer?: string | null;
        };
        /**
         * GitHubConnectionPatch
         * @description Omitted fields keep their current value; connecting a project for the first time needs every required field.
         */
        GitHubConnectionPatch: {
            /** Repository */
            repository?: string | null;
            /** Github Connector Id */
            github_connector_id?: string | null;
            verification?: components["schemas"]["VerificationPatch"] | null;
            /** Template Id */
            template_id?: ("python-uv" | "node-npm") | null;
            automation?: components["schemas"]["GitHubAutomationPatch"] | null;
            /**
             * Ai Catalog Id
             * @description null selects the default Codex catalog
             */
            ai_catalog_id?: string | null;
        };
        /** GitHubProjectConnection */
        GitHubProjectConnection: {
            /** Repository */
            repository: string;
            /**
             * Github Connector Id
             * Format: uuid
             */
            github_connector_id: string;
            verification: components["schemas"]["VerificationConfig"];
            /** Template Id */
            template_id?: ("python-uv" | "node-npm") | null;
            automation?: components["schemas"]["GitHubAutomationConfig"];
            /**
             * Ai Catalog Id
             * @description AI catalog that receives pull request work; empty uses the default Codex catalog
             */
            ai_catalog_id?: string | null;
        };
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** ImportScheduleRequest */
        ImportScheduleRequest: {
            /**
             * Schedule Id
             * Format: uuid
             */
            schedule_id: string;
        };
        JobSnapshot: CommonComponents["schemas"]["JobSnapshot"];
        LinkedIssue: CommonComponents["schemas"]["LinkedIssue"];
        PipelineObservation: CommonComponents["schemas"]["PipelineObservation"];
        PipelineObservationConfig: CommonComponents["schemas"]["PipelineObservationConfig"];
        PipelineRunRead: CommonComponents["schemas"]["PipelineRunRead"];
        PipelineRunState: CommonComponents["schemas"]["PipelineRunState"];
        /** ProjectList */
        ProjectList: {
            /** Items */
            items: components["schemas"]["ProjectRead"][];
            /** Total Count */
            total_count: number;
        };
        /**
         * ProjectPatch
         * @description Change only the fields present in the request; the merged result is validated as a whole.
         */
        ProjectPatch: {
            /**
             * Expected Revision
             * @description Reject edits based on an outdated project version.
             */
            expected_revision: number;
            /** Name */
            name?: string | null;
            /** Enabled */
            enabled?: boolean | null;
            /** @description null disconnects GitHub */
            github?: components["schemas"]["GitHubConnectionPatch"] | null;
        };
        /** ProjectRead */
        ProjectRead: {
            /** Name */
            name: string;
            github?: components["schemas"]["GitHubProjectConnection"] | null;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
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
            /** Revision */
            revision: number;
            /** Template Version */
            template_version: string | null;
            last_check: components["schemas"]["ConnectionCheck"] | null;
            /** Repository */
            repository?: string | null;
            /** Github Connector Id */
            github_connector_id?: string | null;
            verification?: components["schemas"]["VerificationConfig"] | null;
        };
        /**
         * ProjectWrite
         * @description A Hub project can exist before any external system is connected.
         */
        ProjectWrite: {
            /** Name */
            name: string;
            github?: components["schemas"]["GitHubProjectConnection"] | null;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
        };
        PullObservation: CommonComponents["schemas"]["PullObservation"];
        PullRequestSnapshot: CommonComponents["schemas"]["PullRequestSnapshot"];
        RunSnapshot: CommonComponents["schemas"]["RunSnapshot"];
        /** TemplateRead */
        TemplateRead: {
            /**
             * Id
             * @enum {string}
             */
            id: "python-uv" | "node-npm";
            /** Name */
            name: string;
            /** Version */
            version: string;
            /** Changelog */
            changelog: string;
            /** Required Jobs */
            required_jobs: string[];
            /** Filename */
            filename: string;
            /** Content */
            content: string;
        };
        ValidationError: CommonComponents["schemas"]["ValidationError"];
        VerificationConfig: CommonComponents["schemas"]["VerificationConfig"];
        /** VerificationPatch */
        VerificationPatch: {
            /**
             * Workflow
             * @description Workflow filename, not display name.
             */
            workflow?: string | null;
            /**
             * Required Jobs
             * @description Exact GitHub Actions job names; replaces the whole list.
             */
            required_jobs?: string[] | null;
            /** Event */
            event?: "pull_request" | null;
        };
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
    list_projects_api_v1_projects_get: {
        parameters: {
            query?: {
                offset?: number;
                limit?: number;
                search?: string;
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
                    "application/json": components["schemas"]["ProjectList"];
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
    create_project_api_v1_projects_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectWrite"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectRead"];
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
    get_project_templates_api_v1_projects_templates_get: {
        parameters: {
            query?: never;
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
                    "application/json": components["schemas"]["TemplateRead"][];
                };
            };
        };
    };
    import_project_schedule_api_v1_projects_import_schedule_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ImportScheduleRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectRead"];
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
    get_project_api_v1_projects__project_id__get: {
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
                    "application/json": components["schemas"]["ProjectRead"];
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
    delete_project_api_v1_projects__project_id__delete: {
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
    update_project_api_v1_projects__project_id__patch: {
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
                "application/json": components["schemas"]["ProjectPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectRead"];
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
    enroll_pull_request_api_v1_projects__project_id__runs_post: {
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
                "application/json": components["schemas"]["EnrollPullRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
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
    check_project_api_v1_projects__project_id__check_post: {
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
                "application/json": components["schemas"]["CheckRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConnectionCheck"];
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
