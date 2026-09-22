# 구현·검증 현황

2026-09-22 기준. 주요 기능의 실서비스 카나리는 완료했다. 마지막 확인 배포는
`autohub-00010-x9c`이며, 이후 추가한 **공용 유지보수·이력 보관 정책은 구현과
로컬 검증을 마쳤지만 아직 배포하지 않았다.**

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

## 배포 대기: 공용 유지보수·이력 정리

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
run 만료가 PR 재등록으로 이어지지 않도록 기록한다. 운영 이력 삭제는 아직 실행하지 않았다.

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

## 남은 확인

- **재배포 후:** 기존 자동 생성 스케줄 제거, 공용 유지보수 1개 생성·보호·실행,
  시간당 이력 정리와 Jules 재등록 방지를 확인한다. 마지막 운영 조회에서는 프로젝트
  dispatcher 1개와 중지된 연결 테스트 스케줄 2개였으며, 사용자 스케줄이 추가되지 않았다면
  배포 후 dispatcher와 공용 유지보수 2개가 남아야 한다.
- **화면:** 최근 연결 테스트·catalog·공용 스케줄의 브라우저 확인은 사용자가 진행한다.
- **이번 범위 제외:** Telegram, 실제 Jules quota 소진/429, required review/branch protection.
  연결 테스트의 취소·timeout·응답 유실·인증 장애·수동 정리 복구는 live로 유발하지 않았다.

자동 계획/WBS, 동적 catalog 선택, 병합 전 LLM 리뷰는 보류한다. 추가 저장소의 branching
정책은 온보딩 때 결정한다. 나머지 확장·provider 불확실성은
[Catalog 미해결 항목](ai-catalog-implementation-notes.md#known-limitations-and-remaining-work)에 모은다.
