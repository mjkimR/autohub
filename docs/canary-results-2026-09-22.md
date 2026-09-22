# 실서비스 카나리 결과 — 2026-09-22

`mjkimR/test-sandbox`와 Cloud Run에서 주요 기능 검증을 완료했다. 개별 카나리 6개에
누적됐던 준비·진행 기록을 결과와 재현 요점으로 통합했다. PR/CI 링크는 GitHub 증거이며,
Hub run 이력은 보관 정책에 따라 만료될 수 있다. 현재 배포 대기 항목은
[구현·검증 현황](delivery-status.md)에서 관리한다.

## 결과

| 검증 | 증거 | 확인한 결과 |
| --- | --- | --- |
| Codex 기본 실행·동시성 | PR [#4](https://github.com/mjkimR/test-sandbox/pull/4), [#5](https://github.com/mjkimR/test-sandbox/pull/5), [#6](https://github.com/mjkimR/test-sandbox/pull/6) | 동시 제한 1에서 후속 PR 대기. GH_TOKEN 설정 후 무인 구현·push·현재 head CI·자동 머지 |
| CI 실패 복구 | PR [#7](https://github.com/mjkimR/test-sandbox/pull/7), [#8](https://github.com/mjkimR/test-sandbox/pull/8), [#8 수정 CI](https://github.com/mjkimR/test-sandbox/actions/runs/35673910385) | 각 1회 `ci-fix`로 복구·자동 머지. #8 실제 요청에 실패 assertion/traceback 포함, assertion·workflow 보존 |
| 충돌 복구 | 준비 PR [#9](https://github.com/mjkimR/test-sandbox/pull/9), 대상 [#10](https://github.com/mjkimR/test-sandbox/pull/10), [수정 CI](https://github.com/mjkimR/test-sandbox/actions/runs/35675447054) | 실제 충돌에 `conflict-fix` 1회. 양쪽 변경·assertion과 최신 main 반영 후 자동 머지 |
| Draft 승인 | PR [#11](https://github.com/mjkimR/test-sandbox/pull/11), [최종 CI](https://github.com/mjkimR/test-sandbox/actions/runs/35676475973) | Draft+CI 성공 및 Ready+현재 head CI 없음은 대기. Draft 복귀로 승인 철회, 최종 Ready+CI 성공에서 자동 머지. agent 요청 0 |
| 웹훅 누락 복구 | PR [#12](https://github.com/mjkimR/test-sandbox/pull/12), [CI](https://github.com/mjkimR/test-sandbox/actions/runs/35677259553) | 웹훅 비활성 동안 새 delivery 없이 정기 polling만으로 자동 머지. 이후 웹훅 복원 |
| Jules report | [세션](https://jules.google.com/session/15043012283364374433) | 요청한 marker·greeting·clamp 결과·명령/종료 코드가 report로 저장. PR/run 생성 없음 |
| Jules task | [세션](https://jules.google.com/session/7977738327420503966), PR [#13](https://github.com/mjkimR/test-sandbox/pull/13), [CI](https://github.com/mjkimR/test-sandbox/actions/runs/35680757810) | PR 자동 등록 → CI 확인 → 자동 머지. 기존 코드/검증 유지, 추가 agent 요청 0. 두 세션 모두 capacity 반환 |
| Catalog 생성 API | `canary-api-20260922` | 생성 201, 중복 key 409, 잘못된 key 422. 기존 catalog 불변 |
| Codex 연결 테스트 | PR [#14](https://github.com/mjkimR/test-sandbox/pull/14), [CI](https://github.com/mjkimR/test-sandbox/actions/runs/35684422375) | 고유 fixture·현재 head CI 검증 후 PR 닫기/브랜치 삭제. 머지 없음 |
| Jules 연결 테스트 | PR [#15](https://github.com/mjkimR/test-sandbox/pull/15), [CI](https://github.com/mjkimR/test-sandbox/actions/runs/35684683656) | 동일 검증 후 PR 닫기, 전용 base/출력 브랜치 모두 삭제. provider가 일반 PR을 만들었어도 개발 run 등록 차단 |

배포 기준: #7은 `autohub-00008-xtl`, #8~#12는 `autohub-00009-mqv`, Jules와
catalog/연결 테스트는 `autohub-00010-x9c`다. #4~#6은 2026-09-21 선행 검증이다.
외부 tick은 2026-09-22 기준 의도한 5분이며 내부 60초 간격과 구별한다.

## 재현 요점과 판정 범위

- **CI 실패:** 정상 기대값 assertion은 유지하고 산술 함수 구현만 틀리게 만든다.
  로컬 실패/성공 대조군과 최초 CI 실패를 확인한 뒤 `implemented=true`로 등록한다.
  #8은 `sum_of_squares`를 한 줄 수정했고, 실제 CI-fix 댓글의 오류 발췌는 981자로
  1,000자 제한 안에 있었다. 수동 advance/tick/merge 없이 복구를 확인했다.
- **충돌:** 같은 기준 커밋에서 동일 줄에 서로 다른 변경과 검증을 넣은 PR 두 개를 만든다.
  둘 다 초기 CI를 통과시킨 뒤 준비 PR만 직접 머지한다. 대상의 `mergeable_state=dirty`를
  확인한 후 등록하면 충돌 발생 시점을 조절할 수 있다. 대상은 정기 tick으로 완료했다.
- **Draft:** Draft → Ready(새 head는 `[skip ci]`) → Draft(새 CI 성공) → 최종 Ready 순서다.
  중간 조건은 수동 관찰 API로 판정했고 최종 머지는 자동이었다. 전환 직후 관찰 409가
  있었으나 재관찰은 성공했으며, 정확한 경합 원인을 확인한 것으로 취급하지 않는다.
- **웹훅:** 먼저 등록한 Draft run의 상태를 확인하고 해당 저장소의 Hub webhook만 끈 뒤
  Ready로 전환한다. 그 이후 수동 진행·tick·재전송 없이 완료와 새 delivery 0건을 확인한다.
  **등록 트리거 자체가 도착하지 않은 PR의 발견은 검증 범위가 아니다.**
- **Jules:** report와 task를 각 한 번 시작하고 반복 생성은 중지한다. task 시작 대기만
  줄이기 위해 dispatcher를 한 번 호출했으며, 이후 수집·PR 등록·머지는 자동이었다.
  report 저장과 `outputs[].pullRequest.url` 수집은 확인했으나 report 원본 message 키는
  기록하지 않았다. task의 선택적 `result_summary`는 null이었고 그 원인은 확인하지 않았다.
- **연결 테스트:** 준비·dispatch·성공 결과 수집에는 수동 advance를 사용하고 정리는 정기
  dispatcher에 맡겼다. 두 provider 모두 같은 요청 재전송은 동일 ID, 동시 새 시작은 409,
  개발 run 등록은 정리 전후 422였다. main 불변·테스트용 브랜치 3개 삭제·capacity 반환을
  확인했다. provider 작업에 수동 push나 수정은 하지 않았다.

## 발견한 문제와 완료한 보정

| 문제 | 최종 처리 |
| --- | --- |
| 프로젝트 생성 뒤 GitHub를 연결하면 dispatcher가 생성되지 않음 | 연결 저장 시 생성/복구. 재저장·간격 변경·연결 해제/재연결 시 같은 ID 유지. 일반 schedule API 직접 수정/삭제 409. 배포 API에서 비활성 임시 프로젝트로 확인하고 정리 |
| CI-fix가 로그 끝의 정리 출력만 전달 | 오류와 주변 문맥 우선 발췌, 마스킹·크기 제한 유지. #8 실제 요청에서 검증 |
| workbench 재배포가 구형 scheduler 인증을 덮어씀 | 기존 managed key 복원 후 정기 tick 200 확인. 상위 deploy가 Hub provisioner와 `--schedule`을 사용하도록 수정하고 scheduler 단계 적용 확인. 다음 배포에는 양쪽 저장소 수정 필요 |

기존 연결 프로젝트의 누락 dispatcher는 프로젝트 설정 저장으로 복구하며, 배포 시 일괄
복구를 추가한 것은 아니다. 카나리 중 정상화한 sandbox dispatcher는 유지했다.
운영 인증·tick 설정의 정식 절차는 [배포 가이드](cloud-run-deployment.md)에 있다.

## 정리 상태와 제외 범위

- Jules 카나리 Agent Schedule 2개는 소유자 API로 삭제했고, 구버전 catalog sync도 제거됐다.
  완료된 session 보고서·PR/run 연결은 보존했다.
- 연결 테스트 #14/#15는 머지 없이 닫혔고 테스트 브랜치 3개가 자동 삭제됐다.
  테스트 이후 main은 #13 merge commit `6c68c88373e01b4c04284ce1b464f6734e62278b`로 유지됐다.
- `canary-api-20260922`는 자격 증명 없는 비활성 catalog로 남았다. 삭제 API가 없으며
  프로젝트나 스케줄에 지정하지 않았다.
- 마지막 운영 조회의 중지된 연결 테스트 스케줄 2개는 공용 유지보수 마이그레이션으로
  제거할 예정이다. 공용 유지보수·이력 정리의 배포 후 검증은 아직 남아 있다.
- Telegram과 최근 화면 확인은 제외했다. Jules 실제 quota 소진/429, required review/
  branch protection, 연결 테스트 취소·timeout·응답 유실·인증 장애·수동 정리 복구와
  이미 등록된 테스트 run의 최종 merge 방어를 별도로 live 유발하지 않았다.
