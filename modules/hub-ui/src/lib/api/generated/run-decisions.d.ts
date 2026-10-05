/** Generated from OpenAPI domain tags. Do not edit manually. */
import type { components as CommonComponents } from "./common";
export interface paths {
    "/api/v1/pipeline-runs/{run_id}/questions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Questions */
        get: operations["list_questions_api_v1_pipeline_runs__run_id__questions_get"];
        put?: never;
        /** Ask Question */
        post: operations["ask_question_api_v1_pipeline_runs__run_id__questions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/questions/{question_id}/answers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Answer Question */
        post: operations["answer_question_api_v1_pipeline_runs__run_id__questions__question_id__answers_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pipeline-runs/{run_id}/questions/{question_id}/dismiss": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Dismiss Question */
        post: operations["dismiss_question_api_v1_pipeline_runs__run_id__questions__question_id__dismiss_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export interface components {
    schemas: {
        /** AnswerRead */
        AnswerRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Question Id
             * Format: uuid
             */
            question_id: string;
            /** Answer */
            answer: string;
            /** Actor */
            actor: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Applied Attempt Id */
            applied_attempt_id: string | null;
        };
        /** AnswerWrite */
        AnswerWrite: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Expected Revision */
            expected_revision: number;
            /** Answer */
            answer: string;
        };
        HTTPValidationError: CommonComponents["schemas"]["HTTPValidationError"];
        /** QuestionDismiss */
        QuestionDismiss: {
            /** Expected Revision */
            expected_revision: number;
            /** Reason */
            reason: string;
        };
        /** QuestionList */
        QuestionList: {
            /** Items */
            items: components["schemas"]["QuestionRead"][];
            /** Total Count */
            total_count: number;
            /** Run Revision */
            run_revision: number;
        };
        /** QuestionRead */
        QuestionRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Pipeline Run Id
             * Format: uuid
             */
            pipeline_run_id: string;
            /** Execution Attempt Id */
            execution_attempt_id: string | null;
            /** Head Sha */
            head_sha: string;
            /** Question */
            question: string;
            /** Actor */
            actor: string;
            /** Source */
            source: string;
            /** State */
            state: string;
            /** Resolution */
            resolution: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Answers */
            answers?: components["schemas"]["AnswerRead"][];
        };
        /** QuestionWrite */
        QuestionWrite: {
            /**
             * Request Id
             * Format: uuid
             */
            request_id: string;
            /** Expected Revision */
            expected_revision: number;
            /** Question */
            question: string;
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
    list_questions_api_v1_pipeline_runs__run_id__questions_get: {
        parameters: {
            query?: {
                offset?: number;
                limit?: number;
            };
            header?: never;
            path: {
                run_id: string;
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
                    "application/json": components["schemas"]["QuestionList"];
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
    ask_question_api_v1_pipeline_runs__run_id__questions_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuestionWrite"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionRead"];
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
    answer_question_api_v1_pipeline_runs__run_id__questions__question_id__answers_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
                question_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AnswerWrite"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnswerRead"];
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
    dismiss_question_api_v1_pipeline_runs__run_id__questions__question_id__dismiss_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
                question_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuestionDismiss"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionRead"];
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
