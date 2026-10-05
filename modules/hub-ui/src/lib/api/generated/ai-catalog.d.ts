/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/ai-catalogs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Ai Catalogs */
        get: operations["list_ai_catalogs_api_v1_ai_catalogs_get"];
        put?: never;
        /** Create Ai Catalog */
        post: operations["create_ai_catalog_api_v1_ai_catalogs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai-catalogs/{catalog_key}/sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Ai Catalog Sessions */
        get: operations["list_ai_catalog_sessions_api_v1_ai_catalogs__catalog_key__sessions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai-catalogs/{catalog_key}/availability": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Set Ai Catalog Availability */
        put: operations["set_ai_catalog_availability_api_v1_ai_catalogs__catalog_key__availability_put"];
        post?: never;
        /** Clear Ai Catalog Availability */
        delete: operations["clear_ai_catalog_availability_api_v1_ai_catalogs__catalog_key__availability_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai-catalogs/{catalog_key}/enabled": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Set Ai Catalog Enabled */
        put: operations["set_ai_catalog_enabled_api_v1_ai_catalogs__catalog_key__enabled_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai-catalogs/{catalog_key}/policy-config": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Ai Catalog Policy Config */
        put: operations["update_ai_catalog_policy_config_api_v1_ai_catalogs__catalog_key__policy_config_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai-catalogs/{catalog_key}/connector": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Set Ai Catalog Connector */
        put: operations["set_ai_catalog_connector_api_v1_ai_catalogs__catalog_key__connector_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export interface components {
    schemas: {
        /**
         * AICatalogKind
         * @enum {string}
         */
        AICatalogKind: "codex" | "jules";
        /** AICatalogList */
        AICatalogList: {
            /** Items */
            items: components["schemas"]["AICatalogRead"][];
        };
        /** AICatalogRead */
        AICatalogRead: {
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
            /** Key */
            key: string;
            /** Name */
            name: string;
            kind: components["schemas"]["AICatalogKind"];
            /** Adapter */
            adapter: string;
            /** Connector Id */
            connector_id: string | null;
            /** Enabled */
            enabled: boolean;
            availability_state: components["schemas"]["AICatalogState"];
            /** Available At */
            available_at: string | null;
            /** Availability Source */
            availability_source: string | null;
            /** Availability Updated At */
            availability_updated_at: string | null;
            /** Availability Note */
            availability_note: string | null;
            /** Configured Concurrency */
            configured_concurrency: number;
            /**
             * Effective Concurrency
             * @default 0
             */
            effective_concurrency: number;
            /** Refresh Jitter Minutes */
            refresh_jitter_minutes: number;
            /** Policy Config */
            policy_config?: {
                [key: string]: unknown;
            };
            /** Policy State */
            policy_state?: {
                [key: string]: unknown;
            };
            /** Revision */
            revision: number;
            /**
             * Held Run Count
             * @default 0
             */
            held_run_count: number;
            /**
             * Active Dispatch Count
             * @default 0
             */
            active_dispatch_count: number;
            /**
             * Open Session Count
             * @default 0
             */
            open_session_count: number;
            /**
             * Connector Provider
             * @description Connector provider the catalog authenticates with; set for kinds with sessions
             */
            connector_provider?: string | null;
            /**
             * Pipeline Delivery
             * @description Whether the catalog's adapter can deliver pull request pipeline work
             * @default false
             */
            pipeline_delivery: boolean;
            /**
             * Connection Test
             * @description Supports an isolated project PR connection test
             * @default false
             */
            connection_test: boolean;
            /**
             * Session Work Types
             * @description Work types the catalog's scheduled sessions can do: 'task' (adopted pull requests), 'report'
             */
            session_work_types?: string[];
        };
        /** AICatalogSessionList */
        AICatalogSessionList: {
            /** Items */
            items: components["schemas"]["AICatalogSessionRead"][];
            /** Total Count */
            total_count: number;
        };
        AICatalogSessionRead: CommonComponents["schemas"]["AICatalogSessionRead"];
        /**
         * AICatalogState
         * @enum {string}
         */
        AICatalogState: "normal" | "quota_blocked" | "probe" | "disabled" | "unknown";
        /** CreateAICatalogRequest */
        CreateAICatalogRequest: {
            /** Key */
            key: string;
            /** Name */
            name: string;
            kind: components["schemas"]["AICatalogKind"];
            /** Connector Id */
            connector_id?: string | null;
            /**
             * Configured Concurrency
             * @default 1
             */
            configured_concurrency: number;
            /** Policy Config */
            policy_config?: {
                [key: string]: unknown;
            };
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
        };
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** SetAvailabilityRequest */
        SetAvailabilityRequest: {
            /**
             * Available At
             * Format: date-time
             */
            available_at: string;
            /** Note */
            note?: string | null;
            /**
             * Source
             * @default manual
             */
            source: string;
        };
        /** SetConnectorRequest */
        SetConnectorRequest: {
            /** Connector Id */
            connector_id: string | null;
        };
        /** SetEnabledRequest */
        SetEnabledRequest: {
            /** Enabled */
            enabled: boolean;
        };
        /**
         * UpdatePolicyConfigRequest
         * @description Kind-specific quota settings; the catalog's quota policy validates and normalizes them.
         */
        UpdatePolicyConfigRequest: {
            /** Policy Config */
            policy_config: {
                [key: string]: unknown;
            };
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
    list_ai_catalogs_api_v1_ai_catalogs_get: {
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
                    "application/json": components["schemas"]["AICatalogList"];
                };
            };
        };
    };
    create_ai_catalog_api_v1_ai_catalogs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateAICatalogRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AICatalogRead"];
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
    list_ai_catalog_sessions_api_v1_ai_catalogs__catalog_key__sessions_get: {
        parameters: {
            query?: {
                offset?: number;
                limit?: number;
                status?: ("open" | "completed" | "failed") | null;
                schedule_config_id?: string | null;
            };
            header?: never;
            path: {
                catalog_key: string;
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
                    "application/json": components["schemas"]["AICatalogSessionList"];
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
    set_ai_catalog_availability_api_v1_ai_catalogs__catalog_key__availability_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                catalog_key: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SetAvailabilityRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AICatalogRead"];
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
    clear_ai_catalog_availability_api_v1_ai_catalogs__catalog_key__availability_delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                catalog_key: string;
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
                    "application/json": components["schemas"]["AICatalogRead"];
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
    set_ai_catalog_enabled_api_v1_ai_catalogs__catalog_key__enabled_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                catalog_key: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SetEnabledRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AICatalogRead"];
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
    update_ai_catalog_policy_config_api_v1_ai_catalogs__catalog_key__policy_config_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                catalog_key: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdatePolicyConfigRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AICatalogRead"];
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
    set_ai_catalog_connector_api_v1_ai_catalogs__catalog_key__connector_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                catalog_key: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SetConnectorRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AICatalogRead"];
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
