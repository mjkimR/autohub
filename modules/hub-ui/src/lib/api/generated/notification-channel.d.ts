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
    "/api/v1/notification-channels/{channel_id}/decision-subscription": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Subscription */
        get: operations["read_subscription_api_v1_notification_channels__channel_id__decision_subscription_get"];
        /** Save Subscription */
        put: operations["save_subscription_api_v1_notification_channels__channel_id__decision_subscription_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/notification-channels/{channel_id}/decision-notices": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** History */
        get: operations["history_api_v1_notification_channels__channel_id__decision_notices_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/notification-channels/{channel_id}/decision-notices/{notice_id}/resend": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Resend */
        post: operations["resend_api_v1_notification_channels__channel_id__decision_notices__notice_id__resend_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/notification-channels/{channel_id}/decision-requests/{request_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Request Outcome */
        get: operations["request_outcome_api_v1_notification_channels__channel_id__decision_requests__request_id__get"];
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
        /** DecisionRequestRead */
        DecisionRequestRead: {
            /**
             * Record State
             * @enum {string}
             */
            record_state: "unknown" | "recorded";
            /**
             * Operation
             * @enum {string}
             */
            operation: "subscription" | "resend";
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Result */
            result?: {
                [key: string]: unknown;
            } | null;
            current: components["schemas"]["SubscriptionRead"];
            attempt?: components["schemas"]["NoticeAttemptRead"] | null;
        };
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** NoticeAttemptRead */
        NoticeAttemptRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Notice Ids */
            notice_ids: string[];
            /** State */
            state: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Outcome At */
            outcome_at: string | null;
            /** Detail */
            detail: string | null;
        };
        /** NoticeHistory */
        NoticeHistory: {
            /** Items */
            items: components["schemas"]["NoticeRead"][];
            /** Attempts */
            attempts: components["schemas"]["NoticeAttemptRead"][];
            /** Next Cursor */
            next_cursor: string | null;
            /** Has More */
            has_more: boolean;
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
        };
        /** NoticeRead */
        NoticeRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Decision Key */
            decision_key: string;
            /** Fingerprint */
            fingerprint: string;
            /** Destination Generation */
            destination_generation: number;
            /** State */
            state: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Observed */
            observed: {
                [key: string]: unknown;
            };
            /** Last Attempt Id */
            last_attempt_id: string | null;
        };
        /** NoticeResend */
        NoticeResend: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Expected Revision */
            expected_revision: number;
            /** Expected Destination Generation */
            expected_destination_generation: number;
            /**
             * Acknowledge Possible Duplicate
             * @default false
             */
            acknowledge_possible_duplicate: boolean;
        };
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
        /** SubscriptionRead */
        SubscriptionRead: {
            /**
             * Channel Id
             * Format: uuid
             */
            channel_id: string;
            /** Revision */
            revision: number;
            /** Destination Generation */
            destination_generation: number;
            settings: components["schemas"]["SubscriptionSettings"];
            /** Channel Enabled */
            channel_enabled: boolean;
            /** Severity Enabled */
            severity_enabled: boolean;
            /** Chat Id */
            chat_id: string | null;
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
        };
        /** SubscriptionSettings */
        SubscriptionSettings: {
            /**
             * Enabled
             * @default false
             */
            enabled: boolean;
            /**
             * Project Scope
             * @default selected
             * @enum {string}
             */
            project_scope: "selected" | "all";
            /** Project Ids */
            project_ids?: string[];
            /** Kinds */
            kinds?: ("run-question" | "native-hub-question" | "native-worker-question" | "native-workflow" | "native-proposal" | "native-integration")[];
            /**
             * Mode
             * @default immediate
             * @enum {string}
             */
            mode: "immediate" | "digest";
            /**
             * Review Origin
             * @default
             */
            review_origin: string;
            /**
             * Trusted Destination
             * @default false
             */
            trusted_destination: boolean;
        };
        /** SubscriptionWrite */
        SubscriptionWrite: {
            /**
             * Enabled
             * @default false
             */
            enabled: boolean;
            /**
             * Project Scope
             * @default selected
             * @enum {string}
             */
            project_scope: "selected" | "all";
            /** Project Ids */
            project_ids?: string[];
            /** Kinds */
            kinds?: ("run-question" | "native-hub-question" | "native-worker-question" | "native-workflow" | "native-proposal" | "native-integration")[];
            /**
             * Mode
             * @default immediate
             * @enum {string}
             */
            mode: "immediate" | "digest";
            /**
             * Review Origin
             * @default
             */
            review_origin: string;
            /**
             * Trusted Destination
             * @default false
             */
            trusted_destination: boolean;
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Expected Revision */
            expected_revision: number;
            /** Expected Destination Generation */
            expected_destination_generation: number;
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
    read_subscription_api_v1_notification_channels__channel_id__decision_subscription_get: {
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
                    "application/json": components["schemas"]["SubscriptionRead"];
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
    save_subscription_api_v1_notification_channels__channel_id__decision_subscription_put: {
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
                "application/json": components["schemas"]["SubscriptionWrite"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecisionRequestRead"];
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
    history_api_v1_notification_channels__channel_id__decision_notices_get: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
            };
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
                    "application/json": components["schemas"]["NoticeHistory"];
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
    resend_api_v1_notification_channels__channel_id__decision_notices__notice_id__resend_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                channel_id: string;
                notice_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NoticeResend"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecisionRequestRead"];
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
    request_outcome_api_v1_notification_channels__channel_id__decision_requests__request_id__get: {
        parameters: {
            query: {
                operation: "subscription" | "resend";
            };
            header?: never;
            path: {
                channel_id: string;
                request_id: string;
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
                    "application/json": components["schemas"]["DecisionRequestRead"];
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
