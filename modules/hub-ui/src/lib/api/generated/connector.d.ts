/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/connectors": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Connectors */
        get: operations["get_connectors_api_v1_connectors_get"];
        put?: never;
        /** Create Connector */
        post: operations["create_connector_api_v1_connectors_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/connectors/{connector_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Connector */
        get: operations["get_connector_api_v1_connectors__connector_id__get"];
        /** Put Connector */
        put: operations["put_connector_api_v1_connectors__connector_id__put"];
        post?: never;
        /** Delete Connector */
        delete: operations["delete_connector_api_v1_connectors__connector_id__delete"];
        options?: never;
        head?: never;
        /** Patch Connector */
        patch: operations["patch_connector_api_v1_connectors__connector_id__patch"];
        trace?: never;
    };
}
export interface components {
    schemas: {
        /** ConnectorCreate */
        ConnectorCreate: {
            /** Name */
            name: string;
            provider: components["schemas"]["ConnectorProvider"];
            /** Config */
            config?: {
                [key: string]: components["schemas"]["JsonValue"];
            };
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Credentials */
            credentials: {
                [key: string]: components["schemas"]["JsonValue"];
            };
        };
        /** ConnectorPatch */
        ConnectorPatch: {
            /** Name */
            name?: string | null;
            /** Config */
            config?: {
                [key: string]: components["schemas"]["JsonValue"];
            } | null;
            /** Enabled */
            enabled?: boolean | null;
            /** Credentials */
            credentials?: {
                [key: string]: components["schemas"]["JsonValue"];
            };
        };
        /**
         * ConnectorProvider
         * @enum {string}
         */
        ConnectorProvider: "github" | "jules";
        /** ConnectorPut */
        ConnectorPut: {
            /** Name */
            name: string;
            provider: components["schemas"]["ConnectorProvider"];
            /** Config */
            config?: {
                [key: string]: components["schemas"]["JsonValue"];
            };
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Credentials */
            credentials: {
                [key: string]: components["schemas"]["JsonValue"];
            };
        };
        /** ConnectorRead */
        ConnectorRead: {
            /** Name */
            name: string;
            provider: components["schemas"]["ConnectorProvider"];
            /** Config */
            config?: {
                [key: string]: components["schemas"]["JsonValue"];
            };
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
            /** Has Credentials */
            has_credentials: boolean;
        };
        DeleteResponse: CommonComponents["schemas"]["DeleteResponse"];
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        JsonValue: unknown;
        /** PaginatedList[ConnectorRead] */
        PaginatedList_ConnectorRead_: {
            /** Items */
            items: components["schemas"]["ConnectorRead"][];
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
        ValidationError: CommonComponents["schemas"]["ValidationError"];
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export interface operations {
    get_connectors_api_v1_connectors_get: {
        parameters: {
            query?: {
                /** @description offset for pagination */
                offset?: number;
                /** @description limit for pagination */
                limit?: number;
                /** @description Filter query parameter (name) */
                name?: string | null;
                /** @description Filter query parameter (provider) */
                provider?: string | null;
                /** @description Filter query parameter (enabled) */
                enabled?: boolean | null;
                /**
                 * @description **Order by options:**
                 *
                 *     * `name`
                 *     * `created_at`
                 *     * `updated_at`
                 *     * `id`
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
                    "application/json": components["schemas"]["PaginatedList_ConnectorRead_"];
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
    create_connector_api_v1_connectors_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConnectorCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConnectorRead"];
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
    get_connector_api_v1_connectors__connector_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                connector_id: string;
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
                    "application/json": components["schemas"]["ConnectorRead"];
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
    put_connector_api_v1_connectors__connector_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                connector_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConnectorPut"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConnectorRead"];
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
    delete_connector_api_v1_connectors__connector_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                connector_id: string;
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
    patch_connector_api_v1_connectors__connector_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                connector_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConnectorPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConnectorRead"];
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
