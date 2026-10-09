# 구현·검증 현황

2026-10-02 기준이다. 운영 revision은 `autohub-00015-4l4`이며 DB 스키마는 `autohub`다.
아래 "운영 완료" 범위는 Cloud Run에 배포됐고 실서비스 카나리로 확인했다.

## 운영 완료

| 영역 | 확인한 내용 | 상세 |
| --- | --- | --- |
| PR 자동화 | 등록, Codex 구현, CI 실패 수정, 충돌 해결, 현재 head CI 확인, 자동 머지, 동시 실행 제한 | [카나리 09-22](canary-results-2026-09-22.md) |
| 승인·복구 | Draft 승인/철회, 웹훅 누락 시 polling 복구 | [실행 구조](architecture.md) |
| AI Catalog·Jules | 기본 catalog 설치·추가 생성, 명시적 선택, quota/동시 실행 제한, task PR 자동 등록·머지, report 저장 | [Catalog 가이드](ai-catalogs.md) |
| 프로젝트 연결 | dispatcher 자동 생성·복구, 소유 스케줄 수정 차단, Codex/Jules 연결 테스트와 정리 | [연결 테스트](project-detail-and-connection-tests.md), [카나리 10-01](canary-results-2026-10-01.md) |
| 공용 유지보수·보관 | 설치당 `System maintenance` 1개, 이력 보관 정책, 첫 운영 정리 성공 | [운영 절차](development.md#system-maintenance) |
| 인증·배포 | 계정 로그인·토큰 갱신, managed machine key와 scope 격리, workbench 배포 경로 | [배포 가이드](cloud-run-deployment.md) |
| Google 로그인·가입 승인 | 실계정 가입→승인→정지/재활성→권한 확인, `query`·`form_post` callback | [Google 인증](google-auth.md) |
| MCP | 작업용 `/mcp/` 25개(조회 13, 변경 12, `autohub:mcp:read/write`), 운영용 `/ops/mcp/` 4개(`autohub:mcp:ops`). 인자 오류는 문제별 `details`로 반환 | [연결 안내](mcp.md), [카나리 10-01](canary-results-2026-10-01.md) |
| WorkPlan·WorkItem | Plans 탭, Plan/Item 의존성, pause/resume/revoke, 등록·머지 직후 후속 실행, webhook 직후 Issue 동기화 | [카나리 09-23](canary-results-2026-09-23.md), [카나리 09-28](canary-results-2026-09-28.md) |
| Plan MCP 등록 | 프로젝트+요청 키 멱등 등록과 내용 digest, `group_key` 분류와 Plan/Run 그룹 필터 | [카나리 10-01](canary-results-2026-10-01.md) |
| 질문·답변·재개 | Codex PR 질문 마커 감지→`blocked`, 답변 저장과 재개 분리, 답변을 새 attempt에 고정, 요청 키 멱등 | [카나리 10-01](canary-results-2026-10-01.md) |
| Codex 답글 처리 | 연결 테스트 슬롯 반납, 푸시 없는 답글의 5분 감지, `[bot]` 작성자 인식 | [카나리 10-01](canary-results-2026-10-01.md) |
| 중단·복구 | Run pause 중 외부 푸시 보류, 푸시 뒤 resume의 CI 관찰 복귀, Plan pause/resume, Run cancel, Plan revoke, 원본 링크를 둔 대체 Plan | [카나리 10-02](canary-results-2026-10-02.md) |

계약은 [Run decisions](run-decisions.md), [Work plans](work-plans.md), [MCP](mcp.md)에 있다.
2026-10-01–02 카나리에서 찾은 결함은 `dc8fc8b`, `74f8f53`, `fa9bea7`, `746959d`와 app-common
`a36b829`(MCP 인자 오류 원인 표시)로 보정했다.

## 배포됐지만 실서비스 미검증

자동화 테스트로만 확인했다.

- [Work Plan backlog·활동](work-plan-backlog.md): `draft`·`proposed` 상태(PR·Run·Issue 미생성), 등록 시
  `paused` 선택, Draft·Proposed의 Item 추가·삭제, 댓글과 수정 전후 이력, MCP `work_plans_activity`·
  `work_plans_comment`. 댓글 편집·삭제·스레드·알림·GitHub 댓글 동기화는 없다.
- [분류 변경](work-plans.md#group-classification): REST `PATCH /{plan_id}/group`, MCP
  `work_plans_set_group`. revision 검사와 이력을 남기고 실행·상태·명세는 바꾸지 않는다.

## 로컬 구현, 미발행

- [autohub-sdk](../packages/sdk/README.md): `@pipeline` 선언, 입출력 검증, `Registry`, JSON manifest export,
  로컬 실행 예제. 0.2.0은 task/approval 순차 FlowSpec·release/run/command wire 모델과 HTTP client를
  제공한다. planhub의 독립 환경 mock에서 실제 HTTP 등록·실행·대기·재개·오류 시나리오를 검증한다.
  [SDK 계약](sdk-task-flow.md)에 현재 범위가 있다. 실제 backend 원격 catalog·Cloud Run task 실행·DB 단계별 복구는 미구현이다.

## 운영 상수와 호환성

- 스케줄 tick은 5분(`*/5 * * * *`). 프로젝트/유지보수의 60초는 내부 최소 간격이다. Plan resume과 등록은
  같은 요청에서 준비된 Item을 시작하지만, Run resume·cancel의 후속 반영은 다음 tick에 일어난다.
- 인증은 `X-API-Key`. `APP_API_KEY_ROOT_KEY`는 machine 관리 전용이며 MCP 자격 증명이 아니다.
- REST resume은 `request_id`, `expected_revision`이 필수다. Plan 등록 키는 MCP 필수, REST 선택이다.
- 공용 유지보수 항목은 API/UI에서 수정·중지·삭제할 수 없고 시작 시점과 tick에서 복구된다.
- 실패·취소된 연결 테스트의 브랜치는 종료 후 24시간 뒤 삭제한다.

| 이력 | 보관 기준 |
| --- | --- |
| 성공 schedule job | 종료 후 3일 |
| 실패 schedule job | 종료 후 7일 |
| 종료된 pipeline run | 마지막 변경 후 30일, 하위 attempt/delivery/reply·질문·답변 포함 |
| Webhook delivery | 90일 |

시간당 한 번 최대 job 1,000개·run 200개를 정리한다. 대기·재시도 가능한 job, 활성/일시 중지/차단된
run, 유효한 lease, 미해결 WorkItem이 참조하는 run은 보존한다. run 만료는 PR 재등록으로 이어지지 않는다.

마이그레이션: `f4d5e6f7a8b9`(공용 스케줄), `a5e6f7a8b9c0`(run 만료 표시), `b6f7a8b9c0d1`(인증),
`c7d8e9f0a1b2`(work plan), `e14a217d0910`·`f25b328e1021`(질문·답변·등록 키),
`b47d540a3243`(backlog·활동), `c58e651b4354`(group key). `b47d540a3243` downgrade는 Draft·Proposed가
남아 있으면 거부하고 활동 테이블을 삭제한다. `c58e651b4354` downgrade는 분류 값만 제거한다.

## 제외·보류

- live로 유발하지 않은 것: Telegram, Jules quota 소진/429, required review·branch protection,
  연결 테스트의 timeout·응답 유실·인증 장애, 실제 만료 행 삭제, Plan 수정 revision 충돌, CI 실패가
  섞인 Plan, 위의 미검증 기능. 모두 자동화 테스트 범위다.
- 범위 밖: 분류별 일괄 제어·정책·quota·경로 잠금, Plan 간 Item 의존성, 실패 Item 재시도 API와 자동
  successor 치환, Jules 질문 수집, 자동 계획/WBS, 동적 catalog 선택, 병합 전 LLM 리뷰.
  추가 저장소의 branching 정책은 온보딩 때 정한다. provider 불확실성은
  [Catalog 미해결 항목](ai-catalog-implementation-notes.md#known-limitations-and-remaining-work)에 있다.
- 알려진 정리 대상: Plan 등록 요청의 쿼리 수가 많다(query counter 경고). 동작에는 영향 없다.
