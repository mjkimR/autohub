/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/projects/{project_id}/repository/info": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Repository Info
         * @description Retrieve repository information including default branch and available branches.
         */
        get: operations["get_repository_info_api_v1_projects__project_id__repository_info_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/repository/tree": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Repository Tree
         * @description List directory contents at the specified path and ref.
         */
        get: operations["get_repository_tree_api_v1_projects__project_id__repository_tree_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/repository/blob": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Repository Blob
         * @description Retrieve raw file content and metadata at the specified path and ref.
         */
        get: operations["get_repository_blob_api_v1_projects__project_id__repository_blob_get"];
        put?: never;
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
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** RepoBlobRead */
        RepoBlobRead: {
            /**
             * Path
             * @description File path within the repository
             */
            path: string;
            /**
             * Ref
             * @description Branch, tag, or commit reference
             */
            ref: string;
            /**
             * Size
             * @description Size in bytes
             */
            size: number;
            /**
             * Sha
             * @description Git blob SHA
             */
            sha: string;
            /**
             * Encoding
             * @description Encoding of the content field
             * @default utf-8
             * @enum {string}
             */
            encoding: "utf-8" | "base64";
            /**
             * Content
             * @description File content (decoded utf-8 or base64)
             */
            content: string;
        };
        /** RepoInfoRead */
        RepoInfoRead: {
            /**
             * Repository
             * @description Full repository name: owner/repo
             */
            repository: string;
            /**
             * Default Branch
             * @description Repository default branch name
             */
            default_branch: string;
            /**
             * Branches
             * @description Available branch names
             */
            branches?: string[];
        };
        /** RepoItemRead */
        RepoItemRead: {
            /**
             * Name
             * @description Item name
             */
            name: string;
            /**
             * Path
             * @description Relative path within the repository
             */
            path: string;
            /**
             * Type
             * @description Item kind: file or dir
             * @enum {string}
             */
            type: "file" | "dir";
            /**
             * Size
             * @description Size in bytes for files
             * @default 0
             */
            size: number;
            /**
             * Sha
             * @description Git blob/tree SHA
             * @default
             */
            sha: string;
        };
        /** RepoTreeRead */
        RepoTreeRead: {
            /**
             * Path
             * @description Current directory path
             * @default
             */
            path: string;
            /**
             * Ref
             * @description Branch, tag, or commit reference
             */
            ref: string;
            /**
             * Items
             * @description Items contained in the directory
             */
            items?: components["schemas"]["RepoItemRead"][];
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
    get_repository_info_api_v1_projects__project_id__repository_info_get: {
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
                    "application/json": components["schemas"]["RepoInfoRead"];
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
    get_repository_tree_api_v1_projects__project_id__repository_tree_get: {
        parameters: {
            query?: {
                /** @description Directory path relative to repository root */
                path?: string;
                /** @description Git branch, tag, or commit reference */
                ref?: string;
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
                    "application/json": components["schemas"]["RepoTreeRead"];
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
    get_repository_blob_api_v1_projects__project_id__repository_blob_get: {
        parameters: {
            query: {
                /** @description File path relative to repository root */
                path: string;
                /** @description Git branch, tag, or commit reference */
                ref?: string;
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
                    "application/json": components["schemas"]["RepoBlobRead"];
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
