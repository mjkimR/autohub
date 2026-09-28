# 구현·검증 현황

2026-09-28 기준. 아래 범위는 모두 운영 Cloud Run에 배포됐고 실서비스 카나리로 확인했다.
현재 revision은 `autohub-00006-dz7`이다.

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
| MCP | `/mcp/` Streamable HTTP, 공개 도구 17개, `autohub:mcp:read/write` scope. Claude Code에서 사용 중 | [연결 안내](mcp.md) |
| WorkPlan·WorkItem | Plans 탭, Plan/Item 의존성, pause/resume/revoke, 등록·머지 직후 즉시 후속 실행, webhook 직후 Issue 동기화 | [카나리 09-23](canary-results-2026-09-23.md), [카나리 09-28](canary-results-2026-09-28.md) |

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
`c7d8e9f0a1b2`(work plan).

## 제외·보류

- live로 유발하지 않은 것: Telegram, Jules quota 소진/429, required review·branch protection,
  연결 테스트의 취소·timeout·응답 유실·인증 장애, 실제 만료 행 삭제, 실패 Item 재시도,
  Plan 수정 revision 충돌, CI 실패가 섞인 Plan. 모두 자동화 테스트 범위다.
- 보류: 자동 계획/WBS, 동적 catalog 선택, 병합 전 LLM 리뷰, 실패 Item 재시도 API.
  추가 저장소의 branching 정책은 온보딩 때 정한다. provider 불확실성은
  [Catalog 미해결 항목](ai-catalog-implementation-notes.md#known-limitations-and-remaining-work)에 있다.
- 알려진 정리 대상: Plan 등록 요청의 쿼리 수가 많다(query counter 경고). 동작에는 영향 없다.
