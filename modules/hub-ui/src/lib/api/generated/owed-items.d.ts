/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/owed-items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Owed Items */
        get: operations["list_owed_items_api_v1_owed_items_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/owed-items/counts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Owed Item Counts */
        get: operations["owed_item_counts_api_v1_owed_items_counts_get"];
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
        /** CatalogHold */
        CatalogHold: {
            /**
             * Catalog Id
             * Format: uuid
             */
            catalog_id: string;
            /**
             * Reason
             * @enum {string}
             */
            reason: "unavailable" | "quota-blocked";
            /** Available At */
            available_at?: string | null;
        };
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** OwedAction */
        OwedAction: {
            /**
             * Name
             * @description The owner's existing action the operator takes next
             * @enum {string}
             */
            name: "answer" | "resume-run" | "review-plan" | "inspect-recovery" | "accept-replacement" | "inspect-work-item" | "inspect-batch" | "review-cleanup" | "inspect-run";
            /** Label */
            label: string;
        };
        /** OwedContext */
        OwedContext: {
            /** Run Id */
            run_id?: string | null;
            /** Work Plan Id */
            work_plan_id?: string | null;
            /** Work Item Id */
            work_item_id?: string | null;
            /** Sdd Batch Id */
            sdd_batch_id?: string | null;
            /** @description An AI catalog hold blocking the subject */
            catalog_hold?: components["schemas"]["CatalogHold"] | null;
        };
        /** OwedItemCounts */
        OwedItemCounts: {
            /**
             * Total
             * @description Counted owed items the filters admit
             */
            total: number;
            /**
             * By Kind
             * @description Every kind, zero and quiet kinds included
             */
            by_kind: {
                [key: string]: number;
            };
            /**
             * By Project
             * @description Counted owed items per project; projects with none are omitted
             */
            by_project: {
                [key: string]: number;
            };
        };
        /** OwedItemPage */
        OwedItemPage: {
            /** Items */
            items: components["schemas"]["OwedItemRead"][];
            /** Has More */
            has_more: boolean;
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** OwedItemRead */
        OwedItemRead: {
            /**
             * Key
             * @description <kind>:<subject id>; stable while the item stays in the set
             */
            key: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "decision" | "stopped-run" | "work-plan-proposed" | "work-item-recovery" | "work-item-replacement" | "work-item-attention" | "sdd-batch-attention" | "connection-test-cleanup" | "failed-run";
            /**
             * Counted
             * @description Whether the item carries owed-count weight; quiet items do not
             */
            counted: boolean;
            /** Cause */
            cause: string;
            subject: components["schemas"]["OwedSubject"];
            primary_action: components["schemas"]["OwedAction"];
            /**
             * Waiting Since
             * Format: date-time
             */
            waiting_since: string;
            context: components["schemas"]["OwedContext"];
        };
        /** OwedSubject */
        OwedSubject: {
            /**
             * Type
             * @enum {string}
             */
            type: "decision" | "pipeline-run" | "work-plan" | "work-item-recovery" | "replacement-link" | "work-item" | "sdd-batch" | "connection-test";
            /**
             * Id
             * @description The subject's own ID; a decision uses its decision_key
             */
            id: string;
            /**
             * Project Id
             * Format: uuid
             */
            project_id: string;
            /** Title */
            title?: string | null;
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
    list_owed_items_api_v1_owed_items_get: {
        parameters: {
            query?: {
                project_id?: string | null;
                kind?: ("decision" | "stopped-run" | "work-plan-proposed" | "work-item-recovery" | "work-item-replacement" | "work-item-attention" | "sdd-batch-attention" | "connection-test-cleanup" | "failed-run") | null;
                cursor?: string | null;
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
                    "application/json": components["schemas"]["OwedItemPage"];
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
    owed_item_counts_api_v1_owed_items_counts_get: {
        parameters: {
            query?: {
                project_id?: string | null;
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
                    "application/json": components["schemas"]["OwedItemCounts"];
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
