/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/system_configs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get System Configs */
        get: operations["get_system_configs_api_v1_system_configs_get"];
        put?: never;
        /** Create System Config */
        post: operations["create_system_config_api_v1_system_configs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system_configs/{system_config_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get System Config */
        get: operations["get_system_config_api_v1_system_configs__system_config_id__get"];
        /** Put System Config */
        put: operations["put_system_config_api_v1_system_configs__system_config_id__put"];
        post?: never;
        /** Delete System Config */
        delete: operations["delete_system_config_api_v1_system_configs__system_config_id__delete"];
        options?: never;
        head?: never;
        /** Patch System Config */
        patch: operations["patch_system_config_api_v1_system_configs__system_config_id__patch"];
        trace?: never;
    };
}
export interface components {
    schemas: {
        DeleteResponse: CommonComponents["schemas"]["DeleteResponse"];
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** PaginatedList[SystemConfigRead] */
        PaginatedList_SystemConfigRead_: {
            /** Items */
            items: components["schemas"]["SystemConfigRead"][];
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
        /** SystemConfigCreate */
        SystemConfigCreate: {
            /**
             * Name
             * @description The name of the system_config.
             */
            name: string;
            /**
             * Data
             * @description The data of the system_config.
             */
            data?: {
                [key: string]: unknown;
            } | null;
        };
        /** SystemConfigPatch */
        SystemConfigPatch: {
            /**
             * Name
             * @description The name of the system_config.
             */
            name?: string | null;
            /**
             * Data
             * @description The data of the system_config.
             */
            data?: {
                [key: string]: unknown;
            } | null;
        };
        /** SystemConfigPut */
        SystemConfigPut: {
            /**
             * Name
             * @description The name of the system_config.
             */
            name: string;
            /**
             * Data
             * @description The data of the system_config.
             */
            data?: {
                [key: string]: unknown;
            } | null;
        };
        /** SystemConfigRead */
        SystemConfigRead: {
            /**
             * Name
             * @description The name of the system_config.
             */
            name: string;
            /**
             * Data
             * @description The data of the system_config.
             */
            data?: {
                [key: string]: unknown;
            } | null;
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
    get_system_configs_api_v1_system_configs_get: {
        parameters: {
            query?: {
                /** @description offset for pagination */
                offset?: number;
                /** @description limit for pagination */
                limit?: number;
                /** @description Filter by name (case-insensitive substring) */
                name?: string | null;
                /**
                 * @description **Order by options:**
                 *
                 *     * `name`: Sort by name
                 *     * `created_at`: Sort by creation time
                 *     * `updated_at`: Sort by update time
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
                    "application/json": components["schemas"]["PaginatedList_SystemConfigRead_"];
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
    create_system_config_api_v1_system_configs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SystemConfigCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemConfigRead"];
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
    get_system_config_api_v1_system_configs__system_config_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                system_config_id: string;
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
                    "application/json": components["schemas"]["SystemConfigRead"];
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
    put_system_config_api_v1_system_configs__system_config_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                system_config_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SystemConfigPut"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemConfigRead"];
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
    delete_system_config_api_v1_system_configs__system_config_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                system_config_id: string;
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
    patch_system_config_api_v1_system_configs__system_config_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                system_config_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SystemConfigPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemConfigRead"];
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
