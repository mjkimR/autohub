/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/github-webhook-deliveries": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Github Webhook Deliveries
         * @description The delivery log: what GitHub sent, what it triggered, and why a trigger did not enroll or dispatch.
         */
        get: operations["list_github_webhook_deliveries_api_v1_github_webhook_deliveries_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/github/webhooks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Receive Github Webhook */
        post: operations["receive_github_webhook_api_github_webhooks_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export interface components {
    schemas: {
        /** GitHubWebhookDeliveryList */
        GitHubWebhookDeliveryList: {
            /** Items */
            items: components["schemas"]["GitHubWebhookDeliveryRead"][];
            /** Total Count */
            total_count: number;
        };
        /** GitHubWebhookDeliveryRead */
        GitHubWebhookDeliveryRead: {
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
            /** Delivery Id */
            delivery_id: string;
            /** Event */
            event: string;
            /** Repository */
            repository: string | null;
            /** Pull Number */
            pull_number: number | null;
            /** Auto Run */
            auto_run: boolean;
            /** Requested Catalog */
            requested_catalog: string | null;
            /** Status */
            status: string;
            /** Attempts */
            attempts: number;
            /** Processed At */
            processed_at: string | null;
            /** Failure Detail */
            failure_detail: string | null;
        };
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        ValidationError: CommonComponents["schemas"]["ValidationError"];
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export interface operations {
    list_github_webhook_deliveries_api_v1_github_webhook_deliveries_get: {
        parameters: {
            query?: {
                offset?: number;
                limit?: number;
                status?: ("received" | "retrying" | "processed" | "failed") | null;
                repository?: string | null;
                noteworthy?: boolean;
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
                    "application/json": components["schemas"]["GitHubWebhookDeliveryList"];
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
    receive_github_webhook_api_github_webhooks_post: {
        parameters: {
            query?: never;
            header?: {
                "x-github-delivery"?: string | null;
                "x-github-event"?: string | null;
                "x-hub-signature-256"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
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
