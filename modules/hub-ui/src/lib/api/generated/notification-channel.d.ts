/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/notification-channels": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Notification Channels */
        get: operations["list_notification_channels_api_v1_notification_channels_get"];
        put?: never;
        /** Create Notification Channel */
        post: operations["create_notification_channel_api_v1_notification_channels_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/notification-channels/{channel_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Notification Channel */
        delete: operations["delete_notification_channel_api_v1_notification_channels__channel_id__delete"];
        options?: never;
        head?: never;
        /** Patch Notification Channel */
        patch: operations["patch_notification_channel_api_v1_notification_channels__channel_id__patch"];
        trace?: never;
    };
    "/api/v1/notification-channels/{channel_id}/test": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Test Notification Channel
         * @description Send a test notice through one channel, enabled or not, and report whether Telegram accepted it.
         */
        post: operations["test_notification_channel_api_v1_notification_channels__channel_id__test_post"];
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
        /** NotificationChannelCreate */
        NotificationChannelCreate: {
            /** Name */
            name: string;
            /**
             * Kind
             * @default telegram
             * @constant
             */
            kind: "telegram";
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /**
             * Min Level
             * @default info
             * @enum {string}
             */
            min_level: "debug" | "info" | "warning" | "error" | "critical";
            /**
             * Chat Id
             * @description Telegram chat the bot posts to
             */
            chat_id: string;
            /**
             * Bot Token
             * @description Telegram bot token from @BotFather
             */
            bot_token: string;
        };
        /** NotificationChannelList */
        NotificationChannelList: {
            /** Items */
            items: components["schemas"]["NotificationChannelRead"][];
        };
        /** NotificationChannelPatch */
        NotificationChannelPatch: {
            /** Name */
            name?: string | null;
            /** Enabled */
            enabled?: boolean | null;
            /** Min Level */
            min_level?: ("debug" | "info" | "warning" | "error" | "critical") | null;
            /** Chat Id */
            chat_id?: string | null;
            /** Bot Token */
            bot_token?: string | null;
        };
        /** NotificationChannelRead */
        NotificationChannelRead: {
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
            /** Name */
            name: string;
            /** Kind */
            kind: string;
            /** Enabled */
            enabled: boolean;
            /**
             * Min Level
             * @enum {string}
             */
            min_level: "debug" | "info" | "warning" | "error" | "critical";
            /** Chat Id */
            chat_id: string | null;
            /** Last Sent At */
            last_sent_at: string | null;
            /** Last Error */
            last_error: string | null;
        };
        /** NotificationTestResult */
        NotificationTestResult: {
            /** Delivered */
            delivered: boolean;
            /** Detail */
            detail?: string | null;
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
    list_notification_channels_api_v1_notification_channels_get: {
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
                    "application/json": components["schemas"]["NotificationChannelList"];
                };
            };
        };
    };
    create_notification_channel_api_v1_notification_channels_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NotificationChannelCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NotificationChannelRead"];
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
    delete_notification_channel_api_v1_notification_channels__channel_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                channel_id: string;
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
    patch_notification_channel_api_v1_notification_channels__channel_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                channel_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NotificationChannelPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NotificationChannelRead"];
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
    test_notification_channel_api_v1_notification_channels__channel_id__test_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                channel_id: string;
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
                    "application/json": components["schemas"]["NotificationTestResult"];
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
