# 카나리 결과 — 2026-10-01: 새 스키마 위 연결 테스트·Plan·질문 흐름

`DB_SCHEMA: autohub`로 새 스키마에서 시작한 배포를 `mjkimR/test-sandbox`와 개인 Codex catalog
(`personal-codex`, 동시 실행 1)로 검증했다. 등록·질문·답변·재개는 모두 MCP(`/mcp/`, `/ops/mcp/`)로 했다.
연결 테스트와 Plan 전반은 `autohub-00012-9gf`, 질문 흐름은 작성자 보정을 배포한 `autohub-00013-l4q`다.

| 검증 | 증거 | 결과 |
| --- | --- | --- |
| 연결 테스트 | PR [#41](https://github.com/mjkimR/test-sandbox/pull/41) `9bd4a6a3` | Codex 푸시 → CI 통과 → `succeeded` (07:25:11Z) |
| Plan 등록 멱등성 | Plan `1dcdbd8b`, 같은 `request_id` 2회 | 같은 Plan·Item id 반환, 중복 없음 |
| 의존 순서 | `divide` → `greet` | `greet`은 `divide` 머지 직후 시작 |
| Item A `divide` | PR [#42](https://github.com/mjkimR/test-sandbox/pull/42) | 구현·CI·자동 머지 07:27:14Z, 등록 후 약 2분 |
| 질문 감지 | PR [#46](https://github.com/mjkimR/test-sandbox/pull/46) Codex 답글 07:27:51Z | **보정 배포 뒤** 08:10:04Z `blocked` "Operator decision required: Which greeting word should greet(name) use?" |
| 답변·재개 멱등성 | `runs_answer`, `runs_resume` 각 2회 | 같은 answer id, 같은 resume receipt(revision 6) |
| 답변 전달 | 새 멘션 08:15:08Z | 본문에 `Operator decision … Answer: Annyeong` 포함 |
| Item B `greet` | PR #46 머지 08:16:45Z | `return f"Annyeong, {name}!"`, `# CANARY_20261001_GREET` 단언 포함 |
| Plan 완료 | `work_plans_get` | `completed`, 두 Item `succeeded` |

## 발견·보정 1: 실패·취소된 Codex 연결 테스트가 catalog 슬롯을 점유

`active_dispatch_count`는 `execution_finished`가 아닌 연결 테스트를 하루 동안 세는데, Codex 연결
테스트는 푸시를 확인할 때만 이 값을 세웠다. 푸시 없이 끝난 테스트가 유일한 슬롯을 잡아 새 테스트가
"AI catalog has reached its concurrency limit"로 막혔다.

보정(`dc8fc8b`): Codex의 첫 답글을 클라우드 작업 종료로 보고 `execution_finished`를 세운다. 취소·실패
뒤 정리 단계에서도 답글을 확인한다. 답글 뒤 5분 안에 푸시가 없으면 GH_TOKEN 점검 안내와 함께 실패한다.

## 발견·보정 2: Pipeline run도 푸시 없는 답글을 2시간 기다림

같은 상황의 일반 run은 silent watchdog(2시간 5분)까지 `implementing`에 머물렀다.

보정(`74f8f53`): 첫 전달이나 재개 전달에서 Codex가 답글을 단 뒤 5분이 지나도 head가 그대로면
`blocked`("Codex replied without pushing; …")로 멈춘다. silent 재전달 뒤에는 이전 작업의 늦은 답글일 수
있어 기존 watchdog을 유지한다.

## 발견·보정 3: Pipeline이 Codex 답글을 전혀 인식하지 못함

GitHub REST는 작성자를 `chatgpt-codex-connector[bot]`으로 반환하는데, `collect_replies`는
`chatgpt-codex-connector`와 정확히 비교했다. 연결 테스트 경로는 `[bot]`을 떼고 있어 영향이 없었지만,
pipeline에서는 질문 감지·quota 감지·보정 2가 모두 동작하지 않았다. 테스트 fixture도 접미사 없는
로그인을 써서 놓쳤다. 이번 카나리에서 `greet` 질문이 40분 넘게 감지되지 않아 드러났다.

보정(`fa9bea7`): 작성자 비교 전에 `[bot]`을 떼고, pipeline 테스트 fixture를 실제 REST 값으로 바꿨다.
보정 전 코드로 4개 테스트가 실패하는 것을 확인했다. 배포 뒤 첫 tick에서 기존 답글이 질문으로 등록됐다.

## 환경 문제: Codex 환경 GH_TOKEN 무효

Codex 진단 결과 환경의 `GH_TOKEN`이 GitHub API에서 401, push에서 "Invalid username or token"이었다.
권한 부족(403/404)이 아니라 토큰 문자열 자체가 무효였다. Hub 커넥터 토큰은 정상이었다. 토큰을 다시
발급해 Codex 환경에 넣은 뒤 연결 테스트가 통과했다. 보정 1의 안내 문구가 이 경우를 가리킨다.

## 관찰

- 재개(08:10:48Z) 뒤 실제 멘션(08:15:09Z)까지 약 4분 20초가 걸렸다. 질문 감지(08:10:04Z)와 같이
  5분 scheduler tick에 맞춰 진행됐고, 재개 자체는 즉시 전달하지 않는다.
- `greet` 설명의 "코딩 전에 질문하라"는 카나리용 지시였다. 재개 멘션에 같은 지시와 답변이 함께
  들어갔지만 Codex는 다시 묻지 않고 답변으로 구현했다.
