# 구현·검증 현황

운영 현황은 2026-10-01 기준이다. 아래의 운영 완료 범위는 Cloud Run에 배포됐고 실서비스 카나리로 확인했다.
현재 revision은 `autohub-00014-hrs`다. 2026-09-28 카나리 당시 revision은 `autohub-00006-dz7`이었다.

## 2026-10-01 배포와 새 스키마 카나리

`DB_SCHEMA: autohub`의 새 스키마에 아래 네 섹션(MCP 분리, 질문·답변·Plan MCP, backlog·활동,
group key)을 함께 배포했다. 각 섹션의 "배포·커밋하지 않았다"는 문장은 로컬 구현 당시 기록이다.
`mjkimR/test-sandbox`에서 [새 스키마 카나리](canary-results-2026-10-01.md)로 다음을 확인했다.

- 운영용 `/ops/mcp/`로 Codex 연결 테스트를 시작하고 PR 푸시·CI 통과로 성공했다.
- 작업용 `/mcp/`의 25개 도구로 `group_key`가 있는 Plan을 등록했다. 같은 요청 키 재전송은
  같은 Plan·Item을 돌려줬고, 의존 Item은 선행 PR 머지 뒤 시작했다. 그룹 필터로 Run을 조회했다.
- Codex가 PR 답글에 남긴 질문을 `blocked`와 질문으로 기록했다. MCP 답변·재개는 반복 호출에도
  같은 답변·영수증을 돌려줬고, 새 attempt의 멘션에 답변이 실려 Codex가 그대로 구현·머지했다.

카나리 중 발견해 배포한 보정은 세 건이다.

- `dc8fc8b`: Codex 연결 테스트가 첫 답글에서 catalog 슬롯을 반납하고, 답글 뒤 5분 안에 푸시가
  없으면 GH_TOKEN 점검 안내와 함께 실패한다.
- `74f8f53`: 첫 전달·재개 뒤 Codex가 답글만 달고 5분간 푸시하지 않으면 Run을 `blocked`로 멈춘다.
- `fa9bea7`: REST가 반환하는 `chatgpt-codex-connector[bot]`의 `[bot]`을 떼고 작성자를 비교한다.
  이전에는 pipeline의 질문·quota 감지와 위 답글 처리가 Codex 답글을 인식하지 못했다.

Draft·Proposed·댓글·활동, 분류 변경은 실서비스로 유발하지 않았다.

2026-10-02 [중단·복구 카나리](canary-results-2026-10-02.md)로 Run pause 중 Codex 푸시의 보류, Plan pause의
후속 Item 보류와 resume, Run cancel, Plan revoke와 원본 링크를 기록한 대체 Plan 완료를 확인했다.
일시정지 중 푸시된 Run의 resume이 같은 요청을 다시 보내 `blocked`가 되던 문제를 `746959d`로 보정했다.
이제 마지막 요청 이후 head가 바뀌었으면 답변 없는 resume은 CI 관찰로 돌아간다.

## Work Plan group key: 배포

2026-10-01 실행 격리 없이 작업을 분류하는 nullable `WorkPlan.group_key`를 추가했다.
[분류 계약](work-plans.md#group-classification)에 입력·조회·수정 의미를 기록했다.

- 기본값은 null이고 앞뒤 공백 제거 후 빈 값도 null로 저장한다. UI는 `(null)`로 표시한다.
  Plan 등록·편집·분류 변경과 그룹/상태 필터를 제공하며, Run 필터는 연결된 Plan의 현재 키를 따른다.
  직접 등록 Run은 미분류로 조회한다. 여러 그룹의 코드를 함께 수정하는 작업도 허용한다.
- REST `PATCH /{plan_id}/group`과 MCP `work_plans_set_group`은 revision 검사와 변경 이력을
  적용하며 실행 중·완료 후에도 분류만 변경한다. 스케줄러를 호출하거나 상태·명세를 바꾸지 않는다.
  작업용 MCP는 25개(조회 13, 변경 12), 운영용은 4개다.
- 키는 등록 digest에서 제외한다. 기존 등록 재전송은 현재 분류를 보존하고 새 키로 덮어쓰지 않는다.
  기존 클라이언트의 일반 수정 요청에서 필드를 생략해도 현재 분류를 유지한다.
- 분류별 권한·실행 제한·경로 잠금·영구 보류·일괄 제어는 이번 범위에 포함하지 않는다.

검증 결과:

- Work Plan·MCP·Run API·migration 관련 SQLite 테스트: 169 passed, 5 skipped.
- PostgreSQL 분류·등록 멱등성·동시 등록·migration 왕복·기존 데이터 보존: 17 passed.
- UI 전체: 28개 파일, 170 passed. 기존 RunDecisions 입력 테스트의 간헐적 실패가 첫 실행에서
  재현됐으며 재실행은 통과했다. 이번 변경의 그룹 입력·필터·분류 수정 테스트는 통과했다.
- `just lint`, Python/SDK 타입 검사, UI 검사·빌드 통과. OpenAPI 타입을 재생성했다.
  기존 SQLite migration 테스트가 후속 테스트의 스키마에 영향을 주지 않도록 검증 DB를 분리했다.

배포 시 `b47d540a3243` 다음 migration `c58e651b4354`와 UI/API를 함께 적용한다.
기존 Plan은 null로 유지한다. downgrade는 분류 컬럼·인덱스만 제거하므로 분류 값은 사라지고
Plan·Item·실행 기록은 유지된다. 배포·실서비스 canary·커밋은 수행하지 않았다.

자체 리뷰에서 발견한 그룹 편집 UI 두 건을 수정했다. 그룹·상태 필터를 바꿔도
편집 폼과 입력값·취소 버튼을 유지한다. revision 충돌 후 새로고침하면 현재 저장된
그룹을 보여주고 입력값을 보존하며, 사용자가 다시 저장할 때 최신 revision을 사용한다.
새로고침 실패 시에는 마지막으로 조회한 revision을 유지한다. 관련 UI 25 passed,
UI 전체 173 passed와 lint·타입 검사·빌드를 확인했다. UI 전체 첫 실행에서는 기존
RunDecisions 입력 테스트의 간헐적 실패가 재현됐고 재실행은 통과했다.
이번 보완은 백엔드·API 스키마를 변경하지 않았다.

## Work Plan backlog·댓글·변경이력: 배포, 실서비스 미검증

2026-10-01 [상태·활동 계약](work-plan-backlog.md)을 먼저 작성한 뒤 구현했다.
기존 시작 예약 변경을 보존하면서 REST·MCP·UI를 함께 확장했다.

- `draft`는 제목만으로 등록하고 Item 0개·미완성 명세를 보관한다. `proposed`는
  실행 가능한 계획을 검토 대기로 제출한다. 두 상태는 PR·Run·GitHub Issue를 만들지 않는다.
- 등록 시 `paused`를 선택하면 준비된 계획을 즉시 보류한다. 기존 API 기본값은
  `active`이며 대화에서 승인한 작업은 바로 실행할 수 있다. UI 기본 선택은 Draft다.
- Draft·Proposed의 Item 추가·삭제를 지원하고, Proposed 수정은 Draft로 되돌린다.
  `propose`, `ready`, `resume`에서 완성도·의존성·저장소 연결을 검증한다.
  공개한 active/paused Plan은 기존 고정 Item·미시작 편집 계약을 유지한다.
- 댓글과 수정 전후 값, 인증된 사용자·machine, 시각·revision·선택적 사유를
  Plan 활동에 보존한다. 댓글 재전송은 요청 키로 중복을 막고 실행에 영향을 주지 않는다.
  수정 이력은 Plan 변경과 같은 트랜잭션에 저장하며 자동 완료도 system 주체로 기록한다.
- UI에 다음 작업·판단 대기 필터, Draft/Proposed/Ready 선택, 명세 편집,
  댓글·활동 목록과 이전/이후 비교를 제공한다. 댓글은 별도로 새로고침할 수 있다.
- MCP에 `work_plans_activity`, `work_plans_comment`를 추가했다. 현재 작업용은
  당시 24개(조회 13, 변경 11), 운영용은 4개였다. 기존 read/write scope를 그대로 사용한다.

검증 결과:

- 백엔드 전체 `just test`: 875 passed, 10 skipped. 이후 추가한 연결 변경·직접 시작·
  이력 실패 롤백·동시 편집 테스트와 관련 MCP 재검증: 17 passed, 2 skipped.
- PostgreSQL의 Plan 전체·migration 왕복: 70 passed. 추가 사례·MCP·실제 전체
  migration 신규 적용·metadata 일치·왕복 재검증: 24 passed.
- UI 전체 `just test-ui`: 28개 파일, 158 passed. 예약 시각 보존 회귀를 수정했고
  Draft 저장·제안 편집·판단 필터·댓글 재전송·활동 조회를 검증했다.
- `just lint`, 최종 `just lint-check`, `just check`와 변경 후 해당 모듈 재검사 통과.
  기존 HTTP client architecture 경고 3건은 유지된다. OpenAPI 타입을 재생성했고
  문서 로컬 링크·`git diff --check`를 확인했다.

GitHub/provider I/O는 모의 응답이다. 배포·실서비스 canary·커밋은 수행하지 않았다.
`a36c439f2132` 다음에 `b47d540a3243`을 적용하고 UI/API를 함께 배포해야 한다.
Draft·Proposed가 남아 있으면 downgrade를 거부한다. 먼저 Ready 또는 철회로
전환해야 하며, downgrade는 활동 테이블을 삭제하므로 이력 보존이 필요하면 백업한다.
기존 Plan의 과거 수정 이력은 역으로 생성하지 않고 이후 변경부터 기록한다.
댓글 편집·삭제·스레드·알림·GitHub 댓글 동기화·자동 복원은 포함하지 않는다.

2026-10-01 자체 리뷰 후 두 건을 보완했다. Draft·Proposed의 Item 키 변경 시
의존 참조를 함께 갱신하고, 비어 있거나 중복인 입력은 마지막 유효 키와 그래프를
유지한다. 키 검증 오류가 있는 Item을 삭제해도 다음 Item에 오류가 남지 않도록 했다.
값이 동일한 수정·제어 요청도 수락한 revision·주체·사유를 활동으로 기록한다.
오래된 revision으로 거부된 요청과 등록 재전송은 활동을 추가하지 않는다.
관련 백엔드·MCP 77 passed, 5 skipped와 UI 전체 160 passed를 확인했다.
UI 첫 실행에서 기존 RunDecisions 입력 테스트가 간헐적으로 실패했으며 재실행은
통과했다. `just lint`, `just check`도 통과했다. 이번 보완은 migration·API 스키마를
변경하지 않았고 PostgreSQL 테스트·배포·커밋은 수행하지 않았다.

2차 리뷰에서 발견한 키 입력 상태 문제도 보완했다. 다른 Item의 키를 바꾸거나
삭제해 중복이 해소되면 모든 키를 재검증하고, Item 추가·삭제 중에도 입력 중인
값과 검증 상태를 유지한다. 전체 입력 키가 유효해지면 키와 의존 참조를 한 번에
적용해 키 맞교환도 처리한다. UI 전용 입력·DOM 상태는 API 요청에서 제외한다.
관련 UI 19 passed, UI 전체 166 passed와 `just lint-check`, `just check`를 확인했다.
백엔드 코드는 이번 2차 보완에서 추가 변경하지 않았다.

## 질문·답변·Plan MCP: 배포·카나리 확인

2026-09-30 g-sandbox 전환과 독립적으로 사용할 선행 기능을 구현했다.
기준 커밋 `5ede72e` 위의 로컬 미커밋 변경이며 운영 revision은 아직 변경하지 않았다.

- Run 질문·답변과 재개 요청 영수증을 DB에 보존한다. 답변 저장은 실행을 시작하지
  않고, 명시적 재개가 선택한 답변을 새 attempt와 delivery에 고정한다.
- UI의 Decisions, REST, 작업용 MCP가 동일한 revision·상태·PR head 검사를 사용한다.
  답변·재개 응답 유실과 동시 요청은 동일 요청 키로 회수하며 이전 재개를 반복해도
  이후 pause가 풀리지 않는다. 외부 에이전트 실행 중단을 보장하지는 않는다.
- Codex PR 질문 마커는 신뢰할 작성자·attempt·head를 검사한다. 자동 수집은 모의
  GitHub 테스트로 확인했다. 실제 provider의 질문 작성·답변 반영은 2026-10-01 카나리로 확인했다.
- Work Plan MCP 5개와 질문 MCP 4개를 추가했다. 현재 로컬 도구는 작업용 22개
  (조회 12, 변경 10), 운영용 4개다. 기존 키의 read/write scope를 재사용한다.
- Plan 등록은 프로젝트+요청 키 유일 제약과 내용 digest로 중복을 막는다. MCP는
  요청 키 필수, REST는 기존 소비자 호환을 위해 선택이다. UI도 키를 발행한다.
- 실패·취소 Run의 복구는 대체 Plan과 명시적 원본 링크를 사용한다. 원래 실패나
  의존성을 성공으로 바꾸지 않는 복구 절차를 통합 테스트로 검증했다.

마이그레이션 `e14a217d0910`, `f25b328e1021`을 matching UI/API와 함께 배포해야 한다.
REST resume의 `request_id`, `expected_revision`은 이제 필수이므로 외부 호출도 갱신해야 한다.
질문·답변은 Run의 보관 기간을 따르고 Plan 등록 키는 Plan과 함께 남는다.
최초 구현의 로컬 검증 결과:

- `just test`: 백엔드 전체 850 passed, 9 skipped. PostgreSQL 전용 사례 등은 SQLite에서 제외된다.
- `just test-pg tests/integration/features/project_management/pipeline_runs tests/integration/features/project_management/work_plans tests/integration/migrations/test_run_decisions.py tests/integration/migrations/test_work_plan_migration.py tests/integration/mcp/test_work_decisions.py`: 167 passed.
- `just test-ui`: 27개 파일, 145 passed.
- `just lint-check`, `just check`: 통과. 타입 검사·Svelte 검사·production build 포함.
  기존 HTTP client architecture 경고 3건은 그대로다.
- OpenAPI UI 타입 재생성, 문서 링크, `git diff --check` 확인.

자동 테스트의 GitHub/provider I/O는 모의 응답이며 외부 PR을 만들지 않는다.

같은 날 자체 리뷰에서 확인한 3건도 수정했다. Decisions 조회 실패 또는 두 응답의
revision 불일치 시 제어를 막고, 응답 유실 후 새로고침해도 답변 제출 키를 유지한다.
질문 파서는 JSON 이스케이프 길이와 디코딩한 질문 길이를 분리해 한글·이모지의
정상 질문이 잘리지 않도록 했다. 회귀 테스트를 추가하고 관련 백엔드 18 passed,
1 skipped, UI 전체 150 passed, `just lint-check`·`just check` 통과를 확인했다.
이 후속 수정에서는 전체 백엔드·PostgreSQL 테스트를 다시 실행하지 않았다.

2026-10-01 카나리로 live 질문 전달·답변 반영을, 2026-10-02 카나리로 대체 Plan 복구를 확인했다.
게임별 분류·일괄 제어, Jules 질문, 자동 successor 치환은 이번 범위가 아니다.
g-sandbox 코드·CI·실행 큐 및 Linear 연동은 변경하지 않았다.
[제어·복구 계약](run-decisions.md), [계획 등록](work-plans.md), [MCP](mcp.md)를 참고한다.

## MCP 작업용·운영용 분리: 배포·카나리 확인

2026-09-29 작업용 `/mcp/`와 운영용 `/ops/mcp/`를 같은 서버에 분리했다.
작업용은 조회 9개와 실행 제어 4개, 운영용은 설정·연결 테스트 제어 4개를 제공한다.
작업용을 기본 연결로 유지하고 운영용을 추가로 켜고 끈다. 양쪽을 켜도 중복 없이 총 17개다.
기존 read/write 키는 작업 실행용으로 유지하고, 프로젝트 생성·설정 변경과 연결 테스트
시작·취소는 별도 machine의 `autohub:mcp:ops` 키로 호출한다. 양쪽 도구 목록과 호출을
서버에서 분리하며 운영 키는 REST·scheduler·machine 관리 권한을 받지 않는다.
키 발급 UI도 scope에 맞는 연결 주소를 제공한다. DB migration은 없다.
기존 catalog·connector 조회는 `projects_options`로 통합했다. 중 등급 도구 8개에는
설정 미리보기, 명시적인 자동 머지·구현 여부 선택, 재개 revision 검사, readiness 상태 구분,
테스트 필터·paging·재시도와 후속 행동 안내를 보완했다. REST 입력 기본값은 유지한다.
관련 MCP·인증·프로젝트·실행·연결 테스트 244개와 전체 lint·check를 통과했다.
후속 이름 정리에서 공개 도구 17개를 snake_case로 통일하고 등록 시 최대 64자·문자 규칙을 검사한다.
점 표기 별칭은 제공하지 않으므로 배포 후 도구 discovery와 저장된 호출·허용 목록 갱신이 필요하다.
이름 변경 후 관련 테스트 58개와 전체 lint·check를 통과했다.
배포와 실제 운영 키 발급·클라이언트 연결은 아직 수행하지 않았다.
[연결·전환 안내](mcp.md), [도구별 평가](mcp-tool-review-2026-09-29.md)를 참고한다.

## SDK 초기 골격: 로컬 구현, 미발행

2026-09-29 `packages/sdk`에 독립 `autohub-sdk` 패키지를 추가했다.
`@pipeline` 선언, 입력·출력 모델 검증, 명시적인 `Registry`, 결정론적 JSON manifest export와
로컬 실행 예제를 제공한다. 서버·DB 의존성과 자동 등록 부작용은 없다.
원격 등록 API·Cloud Run 실행·단계별 복구·rside 연결은 구현하지 않았으며 패키지를 발행하지 않았다.
계약 테스트 10개, 전체 lint·check, wheel/sdist 빌드, 서버 의존성이 없는 별도 환경의 wheel 실행을 확인했다.
명령과 범위는 [SDK README](../packages/sdk/README.md)에 있다.

## 완료한 범위

| 영역 | 확인한 내용 | 상세 |
| --- | --- | --- |
| PR 자동화 | 등록, Codex 구현, CI 실패 수정, 충돌 해결, 현재 head CI 확인, 자동 머지, 동시 실행 제한 | [카나리 09-22](canary-results-2026-09-22.md) |
| 승인·복구 | Draft 승인/철회, 웹훅 누락 시 polling 복구 | [실행 구조](architecture.md) |
| AI Catalog·Jules | 기본 catalog 설치·추가 생성, 명시적 선택, quota/동시 실행 제한, task PR 자동 등록·머지, report 저장 | [Catalog 가이드](ai-catalogs.md) |
| 프로젝트 연결 | dispatcher 자동 생성·복구, 소유 스케줄 수정 차단, Codex/Jules 연결 테스트와 정리 | [연결 테스트](project-detail-and-connection-tests.md) |
| 공용 유지보수·보관 | 설치당 `System maintenance` 1개, 이력 보관 정책, 첫 운영 정리 성공 | [운영 절차](development.md#system-maintenance) |
| 인증·배포 | 계정 로그인·토큰 갱신, managed machine key와 scope 격리, workbench 배포 경로 | [배포 가이드](cloud-run-deployment.md) |
| Google 로그인·가입 승인 | 실계정 가입→승인→정지/재활성→권한 확인, `query`·`form_post` callback 모두 확인 | [Google 인증](google-auth.md) |
| MCP | 작업용 `/mcp/` 25개(`autohub:mcp:read/write`), 운영용 `/ops/mcp/` 4개(`autohub:mcp:ops`). Claude Code에서 사용 중 | [연결 안내](mcp.md), [카나리 10-01](canary-results-2026-10-01.md) |
| WorkPlan·WorkItem | Plans 탭, Plan/Item 의존성, pause/resume/revoke, 등록·머지 직후 즉시 후속 실행, webhook 직후 Issue 동기화 | [카나리 09-23](canary-results-2026-09-23.md), [카나리 09-28](canary-results-2026-09-28.md) |
| Plan MCP 등록 | 요청 키 멱등 등록, `group_key` 분류와 Run 그룹 필터, MCP로 의존 Plan 완료 | [카나리 10-01](canary-results-2026-10-01.md) |
| 질문·답변·재개 | Codex PR 질문 감지→`blocked`, MCP 답변·재개 멱등성, 새 attempt에 답변 전달·구현·머지 | [카나리 10-01](canary-results-2026-10-01.md) |
| Codex 답글 처리 | 연결 테스트 슬롯 반납, 푸시 없는 답글의 5분 감지, `[bot]` 작성자 인식 | [카나리 10-01](canary-results-2026-10-01.md) |
| 중단·복구 | Run pause 중 외부 푸시 보류와 CI 관찰 resume, Plan pause/resume, Run cancel, Plan revoke, 대체 Plan 완료와 원본 보존 | [카나리 10-02](canary-results-2026-10-02.md) |

## 운영 상수

- 스케줄 tick은 5분(`*/5 * * * *`). 프로젝트/유지보수의 60초는 내부 최소 간격이다.
- 인증은 `X-API-Key`. `APP_API_KEY_ROOT_KEY`는 machine 관리 전용이며 MCP 자격 증명이 아니다.
- 공용 유지보수 항목은 API/UI에서 수정·중지·삭제할 수 없고 시작 시점과 tick에서 복구된다.

| 이력 | 보관 기준 |
| --- | --- |
| 성공 schedule job | 종료 후 3일 |
| 실패 schedule job | 종료 후 7일 |
| 종료된 pipeline run | 마지막 변경 후 30일, 하위 attempt/delivery/reply 포함 |
| Webhook delivery | 90일 |

시간당 한 번 최대 job 1,000개·run 200개를 정리한다. 대기·재시도 가능한 job, 활성/일시 중지/차단된
run, 유효한 lease, 미해결 WorkItem이 참조하는 run은 보존한다. run 만료는 PR 재등록으로 이어지지 않는다.
마이그레이션: `f4d5e6f7a8b9`(공용 스케줄), `a5e6f7a8b9c0`(run 만료 표시), `b6f7a8b9c0d1`(인증),
`c7d8e9f0a1b2`(work plan), `e14a217d0910`·`f25b328e1021`(질문·답변·등록 키),
`b47d540a3243`(backlog·활동), `c58e651b4354`(group key).

## 제외·보류

- live로 유발하지 않은 것: Telegram, Jules quota 소진/429, required review·branch protection,
  연결 테스트의 취소·timeout·응답 유실·인증 장애, 실제 만료 행 삭제, 실패 Item 재시도,
  Plan 수정 revision 충돌, CI 실패가 섞인 Plan, Draft·Proposed·댓글·활동, 분류 변경.
  모두 자동화 테스트 범위다.
- 보류: 자동 계획/WBS, 동적 catalog 선택, 병합 전 LLM 리뷰, 실패 Item 재시도 API.
  추가 저장소의 branching 정책은 온보딩 때 정한다. provider 불확실성은
  [Catalog 미해결 항목](ai-catalog-implementation-notes.md#known-limitations-and-remaining-work)에 있다.
- 알려진 정리 대상: Plan 등록 요청의 쿼리 수가 많다(query counter 경고). 동작에는 영향 없다.
