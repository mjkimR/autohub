/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/dashboard/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Dashboard Stats */
        get: operations["dashboard_stats_api_v1_dashboard_stats_get"];
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
        /** DashboardStats */
        DashboardStats: {
            /** Project Count */
            project_count: number;
            /** Schedule Count */
            schedule_count: number;
            /** Connector Count */
            connector_count: number;
            /** Active Connector Count */
            active_connector_count: number;
            /** Total Runs */
            total_runs: number;
            /** Runs By State */
            runs_by_state: {
                [key: string]: number;
            };
        };
        PipelineRunState: CommonComponents["schemas"]["PipelineRunState"];
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export interface operations {
    dashboard_stats_api_v1_dashboard_stats_get: {
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
                    "application/json": components["schemas"]["DashboardStats"];
                };
            };
        };
    };
}
