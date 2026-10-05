/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/projects/{project_id}/connection-tests": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Tests */
        get: operations["list_tests_api_v1_projects__project_id__connection_tests_get"];
        put?: never;
        /** Start Test */
        post: operations["start_test_api_v1_projects__project_id__connection_tests_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/connection-tests/options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Test Options */
        get: operations["test_options_api_v1_projects__project_id__connection_tests_options_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/connection-tests/{test_id}/advance": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Advance Test */
        post: operations["advance_test_api_v1_projects__project_id__connection_tests__test_id__advance_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/connection-tests/{test_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Test */
        post: operations["cancel_test_api_v1_projects__project_id__connection_tests__test_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/connection-tests/{test_id}/resolve-cleanup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Resolve Cleanup */
        post: operations["resolve_cleanup_api_v1_projects__project_id__connection_tests__test_id__resolve_cleanup_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export interface components {
    schemas: {
        /** ConnectionTestCatalog */
        ConnectionTestCatalog: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Key */
            key: string;
            /** Name */
            name: string;
            /** Kind */
            kind: string;
            /** Adapter */
            adapter: string;
            /** Revision */
            revision: number;
            /** Connector Id */
            connector_id: string | null;
            /** Configuration Fingerprint */
            configuration_fingerprint?: string | null;
            test_spec?: components["schemas"]["ConnectionTestSpec"] | null;
        };
        /** ConnectionTestOption */
        ConnectionTestOption: {
            /**
             * Ai Catalog Id
             * Format: uuid
             */
            ai_catalog_id: string;
            /** Name */
            name: string;
            /** Kind */
            kind: string;
            spec: components["schemas"]["ConnectionTestSpec"];
            /** Requirements */
            requirements: components["schemas"]["RequirementStatus"][];
            /** Configuration Fingerprint */
            configuration_fingerprint: string;
            /** Ready */
            ready: boolean;
        };
        /** ConnectionTestRead */
        ConnectionTestRead: {
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
            /** Project Revision */
            project_revision: number;
            /** Repository */
            repository: string;
            /** Ai Catalog Id */
            ai_catalog_id: string | null;
            catalog_snapshot: components["schemas"]["ConnectionTestCatalog"] | null;
            /**
             * Configuration Current
             * @default false
             */
            configuration_current: boolean;
            /**
             * Cleanup Resolution Available
             * @default false
             */
            cleanup_resolution_available: boolean;
            test_spec?: components["schemas"]["ConnectionTestSpec"] | null;
            /**
             * Status
             * @enum {string}
             */
            status: "running" | "succeeded" | "failed" | "timed_out" | "canceled";
            /** Phase */
            phase: string;
            /**
             * Cleanup Status
             * @enum {string}
             */
            cleanup_status: "pending" | "waiting" | "completed" | "failed";
            /** Detail */
            detail: string | null;
            /** Evidence */
            evidence: {
                [key: string]: unknown;
            };
            /** Cancel Requested */
            cancel_requested: boolean;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Deadline
             * Format: date-time
             */
            deadline: string;
            /** Finished At */
            finished_at: string | null;
        };
        /** ConnectionTestSpec */
        ConnectionTestSpec: {
            /** Key */
            key: string;
            /**
             * Version
             * @default 1
             */
            version: number;
            /** Title */
            title: string;
            /** Description */
            description: string;
            /** Connector Provider */
            connector_provider?: string | null;
            /**
             * Create Once
             * @default false
             */
            create_once: boolean;
            /**
             * Discovers Output Pr
             * @default false
             */
            discovers_output_pr: boolean;
            /**
             * Manual Cleanup Resolution
             * @default false
             */
            manual_cleanup_resolution: boolean;
            /** Delivery Key */
            delivery_key: string;
            /** Requirements */
            requirements: components["schemas"]["TestRequirement"][];
            /** Phases */
            phases?: {
                [key: string]: string;
            };
            /** Evidence */
            evidence?: components["schemas"]["TestEvidence"][];
        };
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** RequirementStatus */
        RequirementStatus: {
            /** Key */
            key: string;
            /**
             * Status
             * @enum {string}
             */
            status: "configured" | "missing" | "manual";
        };
        /** ResolveCleanup */
        ResolveCleanup: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /**
             * Confirmed Remote Stopped
             * @constant
             */
            confirmed_remote_stopped: true;
            /** Note */
            note: string;
            /** Unrelated Pulls */
            unrelated_pulls?: {
                [key: string]: string;
            };
        };
        /** StartConnectionTest */
        StartConnectionTest: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Ai Catalog Id */
            ai_catalog_id?: string | null;
        };
        /** TestEvidence */
        TestEvidence: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Origin */
            origin?: string | null;
        };
        /** TestRequirement */
        TestRequirement: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Description */
            description: string;
            /**
             * Source
             * @enum {string}
             */
            source: "project_github" | "catalog_connector" | "manual";
            /** Provider */
            provider?: string | null;
            /** Url */
            url?: string | null;
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
    list_tests_api_v1_projects__project_id__connection_tests_get: {
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
                    "application/json": components["schemas"]["ConnectionTestRead"][];
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
    start_test_api_v1_projects__project_id__connection_tests_post: {
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
                "application/json": components["schemas"]["StartConnectionTest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConnectionTestRead"];
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
    test_options_api_v1_projects__project_id__connection_tests_options_get: {
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
                    "application/json": components["schemas"]["ConnectionTestOption"][];
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
    advance_test_api_v1_projects__project_id__connection_tests__test_id__advance_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                test_id: string;
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
                    "application/json": components["schemas"]["ConnectionTestRead"];
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
    cancel_test_api_v1_projects__project_id__connection_tests__test_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                test_id: string;
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
                    "application/json": components["schemas"]["ConnectionTestRead"];
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
    resolve_cleanup_api_v1_projects__project_id__connection_tests__test_id__resolve_cleanup_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                test_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResolveCleanup"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConnectionTestRead"];
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
