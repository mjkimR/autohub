from uuid import UUID

from app.features.project_management.pipeline_runs.interaction_schemas import (
    AnswerRead,
    AnswerWrite,
    QuestionDismiss,
    QuestionList,
    QuestionRead,
    QuestionWrite,
)
from app.features.project_management.pipeline_runs.usecases.interactions import RunInteractionUseCase
from app.mcp.auth import authenticated_context
from app.mcp.contracts import Page, RunId
from app.mcp.dependencies import Dependencies
from app.mcp.registration import register
from app_mcp import ToolRegistry


class Questions(RunId, Page):
    pass


class Ask(RunId):
    question: QuestionWrite


class Answer(RunId):
    question_id: UUID
    response: AnswerWrite


class Dismiss(RunId):
    question_id: UUID
    resolution: QuestionDismiss


def register_interactions(registry: ToolRegistry, deps: Dependencies) -> None:
    use_case = RunInteractionUseCase(deps.runs)

    async def list_questions(args: Questions) -> QuestionList:
        return await use_case.list(args.run_id, args.offset, args.limit)

    async def ask(args: Ask) -> QuestionRead:
        return await use_case.ask(args.run_id, args.question, f"machine:{(await authenticated_context()).subject}")

    async def answer(args: Answer) -> AnswerRead:
        return await use_case.answer(
            args.run_id, args.question_id, args.response, f"machine:{(await authenticated_context()).subject}"
        )

    async def dismiss(args: Dismiss) -> QuestionRead:
        return await use_case.dismiss(
            args.run_id, args.question_id, args.resolution, f"machine:{(await authenticated_context()).subject}"
        )

    register(
        registry,
        "runs_questions",
        "Read questions and saved answers, including their applied attempt and current run revision.",
        Questions,
        QuestionList,
        list_questions,
    )
    register(
        registry,
        "runs_ask",
        "Record a question and block Hub progression; external agents may continue. Reuse request_id after response loss.",
        Ask,
        QuestionRead,
        ask,
        write=True,
    )
    register(
        registry,
        "runs_answer",
        "Save an answer without resuming. Reuse request_id after response loss; pass the returned answer ID to runs_resume after reading the current revision.",
        Answer,
        AnswerRead,
        answer,
        write=True,
    )
    register(
        registry,
        "runs_dismiss_question",
        "Dismiss a stale or withdrawn question with a reason. Does not resume the run.",
        Dismiss,
        QuestionRead,
        dismiss,
        write=True,
    )
