# 구현·검증 현황

2026-09-22 기준. 주요 기능의 실서비스 카나리와 **공용 유지보수·이력 보관 정책의
배포 후 확인을 완료했다.** `autohub-00011-xpl`이 트래픽 100%를 처리하며,
13:55 KST 정기 tick에서 프로젝트 dispatcher와 공용 유지보수가 모두 성공했다.

## MCP 추가 작업: 로컬 구현, 배포 전

2026-09-23: 기존 Hub에 Streamable HTTP `/mcp/`와 공개 도구 17개를 추가했다.
프로젝트·연결 준비 상태·catalog/connector 조회, 연결 테스트 시작/조회/취소,
PR 등록·실행 조회·이력·제어를 기존 UseCase에 연결한다. 기존 machine key에
`autohub:mcp:read`/`autohub:mcp:write`를 추가하고 scheduler scope와 구분한다.
별도 서버·skill·CLI·plugin은 추가하지 않았다. [연결 안내](mcp.md)

공통 `app-mcp`의 모델 스키마·출력 계약·MCP 오류 플래그 보완을 반영한 공개 커밋
`e4b8d1dee7c2b79e0bcb4ac246802eafc13c77ca`로 Python/APM 참조와 lock을 갱신했다.
공개 패키지 기준 전체 테스트 765개 통과(6개 제외), 린트·타입 검사·UI 빌드,
APM audit 및 Python/APM SHA 일치 검사를 완료했다.
**배포와 실제 Codex 연결은 아직 하지 않았다.** 기존 배포 완료 현황과 구분한다.

## 완료한 범위

| 영역 | 구현·검증 결과 | 상세 |
| --- | --- | --- |
| PR 자동화 | 등록, Codex 구현, CI 실패 수정, 충돌 해결, 현재 head CI 확인, 자동 머지 및 동시 실행 제한 | [카나리 결과](canary-results-2026-09-22.md) |
| 승인·복구 | Draft 승인/철회, 이미 등록된 실행의 웹훅 누락 시 polling 복구 | [실행 구조](architecture.md) |
| AI Catalog·Jules | 기본 catalog 설치, 추가 생성 API, 명시적 catalog 선택, quota/동시 실행 제한, task PR 자동 등록·머지와 report 저장 | [Catalog 가이드](ai-catalogs.md) |
| 프로젝트 연결 | GitHub 연결 후 dispatcher 자동 생성·복구, 소유 스케줄 직접 수정 차단, Codex/Jules 연결 테스트와 자동 정리 | [연결 테스트](project-detail-and-connection-tests.md) |
| 인증·배포 | 계정 로그인·토큰 갱신, dispatcher 전용 managed machine key와 scope 격리, 상위 workbench 배포 경로 보정 | [배포 가이드](cloud-run-deployment.md) |

목록 검색·페이지 이동·통계·오류 처리와 UI 구조 정리는
[기존 코드 정리 기록](code-hygiene-review.md)에 있다. 이 문서는 전체 기능별 변경 이력을
반복하지 않으며, 실제 외부 연동의 검증 범위는 카나리 결과를 기준으로 한다.

운영 tick은 의도한 **5분**(`*/5 * * * *`)이다. 프로젝트/유지보수의 60초는 내부
최소 간격이다. 인증은 `X-API-Key`를 사용하며 `APP_API_KEY_ROOT_KEY`는 machine 관리용이다.
이전 static scheduler key 방식은 사용하지 않는다. 다음 workbench 배포에도 상위 저장소와
Auto Hub provisioner의 수정이 모두 필요하다.

## 배포 완료: 공용 유지보수·이력 정리

설치당 하나의 `System maintenance`가 연결 테스트 진행·정리와 Jules 결과 수집을 맡는다.
기존 자동 생성 테스트별 스케줄과 catalog별 sync는 제거하며, 프로젝트 dispatcher와
반복 Agent Schedule은 유지한다. 공용 항목은 일반 API/UI에서 수정·중지·삭제할 수 없고,
시작 시점과 tick에서 누락/비활성 상태를 복구한다.

| 이력 | 보관 기준 |
| --- | --- |
| 성공 schedule job | 종료 후 3일 |
| 실패 schedule job | 종료 후 7일 |
| 종료된 pipeline run | 마지막 변경 후 30일, 하위 attempt/delivery/reply 포함 |
| Webhook delivery | 기존 90일 유지 |

시간당 한 번 최대 job 1,000개·run 200개를 정리한다. 대기·재시도 가능한 job,
활성/일시 중지/차단된 run과 유효한 lease는 보존한다. Jules 보고서·PR 링크는 남기고,
run 만료가 PR 재등록으로 이어지지 않도록 기록한다. 첫 운영 정리 실행은 성공했고,
보관 기간을 넘긴 대상이 없어 job/run 삭제는 모두 0건이었다.

마이그레이션은 `f4d5e6f7a8b9`(공용 스케줄), `a5e6f7a8b9c0`(run 만료 표시)다.
[운영 절차](development.md#system-maintenance)와
[보관 정책](operator-notices.md#history-retention)을 참고한다.

## 최신 자동화 검증

| 검증 | 결과 |
| --- | --- |
| SQLite 백엔드 전체 | 708개 통과, PostgreSQL 전용 3개 제외 |
| PostgreSQL 관련 범위 | 93개 통과: 유지보수·보관 정책·동시 실행·마이그레이션·관찰/프로젝트 API |
| AI Catalog·스케줄 UI 자동 테스트 | 24개 통과 |
| `just lint`, `just check` | 포맷·린트·구조·타입 검사·UI 빌드 통과 |
| API 클라이언트 | 재생성 완료 |

이 수치는 공용 유지보수와 보관 정책을 추가한 최종 검증이다. PostgreSQL과 UI의 수치는
선택한 관련 범위이며 전체 테스트 수가 아니다. SQLite 단일 연결의 트랜잭션 간섭을 피하도록
해당 관찰 테스트만 직렬화했고, PostgreSQL에서는 동시 실행을 검증했다.

## 운영 확인과 제외 범위

- **운영 확인 완료:** 마이그레이션 두 개 적용, 기존 테스트별 스케줄 제거, 활성 스케줄
  2개(dispatcher·공용 유지보수), 공용 항목의 동일 값 PATCH도 409, 새 revision의 정기
  dispatcher HTTP 200을 확인했다. `maintenance.history.pruned_at`은
  `2026-09-22T04:55:01.398956+00:00`으로 기록됐다. 기존 Jules session 2개와
  report/PR/run 연결, 연결 테스트 2개의 성공·정리 완료 상태 및 과거 job 이력도 보존됐다.
- **검증 경계:** 운영 job 83개와 run 10개는 모두 보관 기간 이내였다. 실제 만료 행 삭제와
  만료 후 Jules 재등록 방지는 PostgreSQL 자동화 검증 범위이며, 운영 데이터를
  인위적으로 노후화하거나 삭제해 재현하지 않았다.
- **화면:** 최근 연결 테스트·catalog·공용 스케줄의 브라우저 확인은 사용자가 진행한다.
- **이번 범위 제외:** Telegram, 실제 Jules quota 소진/429, required review/branch protection.
  연결 테스트의 취소·timeout·응답 유실·인증 장애·수동 정리 복구는 live로 유발하지 않았다.

자동 계획/WBS, 동적 catalog 선택, 병합 전 LLM 리뷰는 보류한다. 추가 저장소의 branching
정책은 온보딩 때 결정한다. 나머지 확장·provider 불확실성은
[Catalog 미해결 항목](ai-catalog-implementation-notes.md#known-limitations-and-remaining-work)에 모은다.


## Google 인증·가입 승인: 로컬 구현, 배포 대기

app-common Google OIDC prebuilt와 승인/정지/관리자 권한 API, AutoHub 로그인 및 `/admin/users` 화면을 추가했다. 화이트리스트는 사용하지 않는다. 게시된 app-common `ca4e6a4`의 `app-prebuilt-auth` 단일 패키지로 전환하고 Python/APM SHA와 lock을 갱신했다. 현재 운영 카나리 검증 결과와는 별개이며, [도입 절차와 제한](google-auth.md)을 따라 운영 설정·마이그레이션 후 실계정 검증이 필요하다.


## WorkPlan·WorkItem: 로컬 구현, 배포 대기

프로젝트 Plans 탭과 Plan·Item 일괄 등록, 같은 프로젝트의 Plan 의존성 및 동일 Plan 내부
Item 의존성, 대기 작업 대상 pause/resume/revoke를 추가했다. 등록 후 별도 승인 없이
실행 가능한 작업을 기존 PR 파이프라인으로 넘기며 프로젝트 머지 정책을 따른다.
GitHub Issue는 명세·처리 이력의 단방향 사본이며 실행 판단에 사용하지 않는다.
Issue 동기화 실패는 작업 실행을 막지 않는다. 성공 증거는 Item에 보존하고 미해결
작업이 참조하는 Run은 만료 삭제에서 보호한다.

마이그레이션은 `c7d8e9f0a1b2`이며 운영 배포·실제 GitHub 카나리는 아직 하지 않았다.
[구현 가이드와 제한](work-plans.md), [설계 합의](work-plans-design.md)를 참고한다.

로컬 검증은 SQLite 백엔드 전체 730개 통과·6개 제외, UI 전체 128개 통과,
PostgreSQL 관련 범위 31개 통과다. 마이그레이션 왕복, 동시 admission, 보관 정책,
GitHub 응답 유실 복구를 포함하며 `just lint`, `just check`도 통과했다.
GitHub I/O는 테스트 대역으로 검증했으므로 실제 저장소 카나리를 대체하지 않는다.
