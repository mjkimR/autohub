/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/users/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Me */
        get: operations["read_me_api_v1_users_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read User
         * @description Get a specific user by id.
         */
        get: operations["read_user_api_v1_users__user_id__get"];
        /** Update User */
        put: operations["update_user_api_v1_users__user_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/admin/user": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create User
         * @description Create new user.
         */
        post: operations["create_user_api_v1_users_admin_user_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/admin/admin": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create Admin
         * @description Create new admin user.
         */
        post: operations["create_admin_api_v1_users_admin_admin_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/admin/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Users
         * @description Get user list.
         */
        get: operations["read_users_api_v1_users_admin__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/admin/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete User */
        delete: operations["delete_user_api_v1_users_admin__user_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/admin/{user_id}/access": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Change Access */
        post: operations["change_access_api_v1_users_admin__user_id__access_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/admin/{user_id}/access-events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Access Events */
        get: operations["access_events_api_v1_users_admin__user_id__access_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/login/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login_api_v1_users_login__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/login/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Refresh
         * @description Exchange a refresh token for a new pair, extending the session by another refresh lifetime.
         *
         *     The token stops working when its user is deactivated or its password changes. A refresh token is long and
         *     random-signed, so guessing it is not what the login lockout is for.
         */
        post: operations["refresh_api_v1_users_login_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export interface components {
    schemas: {
        /** Body_login_api_v1_users_login__post */
        Body_login_api_v1_users_login__post: {
            /** Grant Type */
            grant_type?: string | null;
            /** Username */
            username: string;
            /**
             * Password
             * Format: password
             */
            password: string;
            /**
             * Scope
             * @default
             */
            scope: string;
            /** Client Id */
            client_id?: string | null;
            /**
             * Client Secret
             * Format: password
             */
            client_secret?: string | null;
        };
        DeleteResponse: CommonComponents["schemas"]["DeleteResponse"];
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** PaginatedList[UserReadAdmin] */
        PaginatedList_UserReadAdmin_: {
            /** Items */
            items: components["schemas"]["UserReadAdmin"][];
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
        /** RefreshRequest */
        RefreshRequest: {
            /** Refresh Token */
            refresh_token: string;
        };
        Token: CommonComponents["schemas"]["Token"];
        /** UserAccessChange */
        UserAccessChange: {
            /**
             * Action
             * @enum {string}
             */
            action: "approve" | "reject" | "suspend" | "activate" | "promote" | "demote";
            /** Expected Version */
            expected_version: number;
            /** Reason */
            reason?: string | null;
        };
        /** UserAccessEventRead */
        UserAccessEventRead: {
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
            /** User Id */
            user_id: string | null;
            /** Actor Id */
            actor_id: string | null;
            /** Action */
            action: string;
            /** Reason */
            reason: string | null;
        };
        /** UserCreate */
        UserCreate: {
            /**
             * Firstname
             * @description The user's first name.
             */
            firstname: string;
            /**
             * Lastname
             * @description The user's last name.
             */
            lastname: string;
            /**
             * Email
             * Format: email
             * @description The user's email address.
             */
            email: string;
            /**
             * Password
             * Format: password
             * @description The user's password.
             */
            password: string;
            /**
             * Profile Image Url
             * @description URL of the user's profile image.
             */
            profile_image_url?: string | null;
            /**
             * Phone Number
             * @description The user's phone number.
             */
            phone_number?: string | null;
            /**
             * Locale
             * @description The user's preferred locale.
             */
            locale?: string | null;
            /**
             * Timezone
             * @description The user's preferred timezone.
             */
            timezone?: string | null;
            /**
             * Extra
             * @description Additional user metadata.
             */
            extra?: {
                [key: string]: unknown;
            } | null;
        };
        /** UserRead */
        UserRead: {
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
             * Firstname
             * @description The user's first name.
             */
            firstname: string;
            /**
             * Lastname
             * @description The user's last name.
             */
            lastname: string | null;
            /**
             * Email
             * Format: email
             * @description The user's email address.
             */
            email: string;
            /**
             * Profile Image Url
             * @description URL of the user's profile image.
             */
            profile_image_url?: string | null;
            /**
             * Phone Number
             * @description The user's phone number.
             */
            phone_number?: string | null;
            /**
             * Locale
             * @description The user's preferred locale.
             */
            locale?: string | null;
            /**
             * Timezone
             * @description The user's preferred timezone.
             */
            timezone?: string | null;
        };
        /** UserReadAdmin */
        UserReadAdmin: {
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
             * Firstname
             * @description The user's first name.
             */
            firstname: string;
            /**
             * Lastname
             * @description The user's last name.
             */
            lastname: string | null;
            /**
             * Email
             * Format: email
             * @description The user's email address.
             */
            email: string;
            /**
             * Profile Image Url
             * @description URL of the user's profile image.
             */
            profile_image_url?: string | null;
            /**
             * Phone Number
             * @description The user's phone number.
             */
            phone_number?: string | null;
            /**
             * Locale
             * @description The user's preferred locale.
             */
            locale?: string | null;
            /**
             * Timezone
             * @description The user's preferred timezone.
             */
            timezone?: string | null;
            /**
             * Approval Status
             * @default approved
             * @enum {string}
             */
            approval_status: "pending" | "approved" | "rejected";
            /**
             * Auth Version
             * @default 0
             */
            auth_version: number;
            /**
             * Is Active
             * @description Whether the user account is active.
             */
            is_active: boolean;
            /**
             * Is Verified
             * @description Whether the user's email has been verified.
             */
            is_verified: boolean;
            /**
             * Is Superadmin
             * @description Whether the user has superadmin privileges.
             */
            is_superadmin: boolean;
            /**
             * Last Login At
             * @description The timestamp of the user's last login.
             */
            last_login_at?: string | null;
            /**
             * Extra
             * @description Additional user metadata.
             */
            extra?: {
                [key: string]: unknown;
            } | null;
        };
        /** UserUpdate */
        UserUpdate: {
            /**
             * Firstname
             * @description The user's first name.
             */
            firstname?: string | null;
            /**
             * Lastname
             * @description The user's last name.
             */
            lastname?: string | null;
            /**
             * Email
             * @description The user's email address.
             */
            email?: string | null;
            /**
             * Password
             * @description The user's password.
             */
            password?: string | null;
            /**
             * Profile Image Url
             * @description URL of the user's profile image.
             */
            profile_image_url?: string | null;
            /**
             * Phone Number
             * @description The user's phone number.
             */
            phone_number?: string | null;
            /**
             * Locale
             * @description The user's preferred locale.
             */
            locale?: string | null;
            /**
             * Timezone
             * @description The user's preferred timezone.
             */
            timezone?: string | null;
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
    read_me_api_v1_users_me_get: {
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
                    "application/json": components["schemas"]["UserReadAdmin"];
                };
            };
        };
    };
    read_user_api_v1_users__user_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
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
                    "application/json": components["schemas"]["UserRead"];
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
    update_user_api_v1_users__user_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserRead"];
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
    create_user_api_v1_users_admin_user_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserRead"];
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
    create_admin_api_v1_users_admin_admin_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserRead"];
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
    read_users_api_v1_users_admin__get: {
        parameters: {
            query?: {
                /** @description offset for pagination */
                offset?: number;
                /** @description limit for pagination */
                limit?: number;
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
                    "application/json": components["schemas"]["PaginatedList_UserReadAdmin_"];
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
    delete_user_api_v1_users_admin__user_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
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
    change_access_api_v1_users_admin__user_id__access_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserAccessChange"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserReadAdmin"];
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
    access_events_api_v1_users_admin__user_id__access_events_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
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
                    "application/json": components["schemas"]["UserAccessEventRead"][];
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
    login_api_v1_users_login__post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/x-www-form-urlencoded": components["schemas"]["Body_login_api_v1_users_login__post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Token"];
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
    refresh_api_v1_users_login_refresh_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RefreshRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Token"];
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
