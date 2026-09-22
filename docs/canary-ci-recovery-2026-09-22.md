# CI 실패 자동 복구 카나리 — 2026-09-22

## 결과

배포 revision `autohub-00008-xtl`에서 CI 실패 감지 → Codex 수정 요청 → 수정 push → 새 head의 CI 성공 → 자동 squash merge를 확인했다. Hub run의 최종 상태는 `completed`다. 현재 로컬 작업 내용은 배포하지 않았다.

- 대상: [mjkimR/test-sandbox PR #7](https://github.com/mjkimR/test-sandbox/pull/7)
- Hub run: `6de4c840-12a2-47cc-92df-bdd890e3d6ac`
- 수정 attempt: `201ac146-20d5-4553-91bd-8c05faa36fa2` (`ci-fix`)
- 요청: [수정 댓글 1건](https://github.com/mjkimR/test-sandbox/pull/7#issuecomment-5769436568), delivery `1`
- 배포 서비스: `autohub`, `us-west1`
- clone 없이 `gh` API로 테스트 브랜치와 PR을 준비했다.

## 재현과 검증

기존 CI는 `python3 hello.py`를 실행한다. `absolute_difference(a, b)`에 의도적으로 `return a + b`를 넣고, 정상 기대값을 검사하는 assertion 4개를 추가했다. 정순·역순·음수·동일 입력을 검사한다. 기존 함수와 workflow는 유지했다.

1. 로컬에서 심은 구현은 실패하고 `abs(a - b)`를 사용하는 대조 구현은 성공하는지 확인했다.
2. [최초 GitHub Actions](https://github.com/mjkimR/test-sandbox/actions/runs/35670946460)가 `absolute_difference(8, 3) must equal 5` assertion으로 실패했다.
3. PR을 `implemented=true`로 Hub에 등록했다. 최초 상태는 `awaiting_ci`였으며 초기 구현 요청은 전송되지 않았다.
4. 정기 스케줄이 실패를 관찰하고 `ci-fix` 요청을 1회 전송했다.
5. Codex가 구현 한 줄만 `return abs(a - b)`로 고쳤다. assertion 4개와 workflow는 그대로였다.
6. [수정된 head의 GitHub Actions](https://github.com/mjkimR/test-sandbox/actions/runs/35671452073)가 성공했다.
7. Hub가 자동 merge했으며 09:20:06 KST에 run이 완료됐다. 수동 advance·수동 merge는 사용하지 않았다.

| 증거 | 값 |
| --- | --- |
| 최초 head | `dd0f467d38ea6945a415db1884e5aaa48a605e7a` |
| Codex 수정 head | `f8c67df83f5d69d234aca281f26994c88721a382` |
| Squash merge commit | `f2b921bf07550c97134441b104d792f45c146338` |
| 요청 idempotency key | `3193a039-c1ef-409f-ae51-899222bcbe6d` |
| Hub 등록 시각 | 09:13:12 KST |
| 수정 요청 시각 | 09:18:10 KST |
| 최종 요청 수 | 1 |

## 발견 사항

### 프로젝트 실행 스케줄 누락 — 운영 설정 복구

시작 시 Cloud Scheduler tick과 `/api/health/deep`은 정상이었지만, Hub의 `schedule_configs`와 `schedule_jobs` 조회 결과는 모두 0건이었다. 따라서 등록된 PR이 `awaiting_ci`에서 진행되지 않았다. 다른 run들은 완료 또는 취소 상태였고, 이번 PR만 활성 상태였다.

기존 API로 `Dispatch test-sandbox` 스케줄을 생성했다. 작업은 `pipeline.dispatch_project`, 간격은 60초, 대상은 기존 sandbox 프로젝트다. 생성 후 수정 요청과 merge가 자동으로 진행됐다. 웹훅은 활성 상태였으므로 polling 단독 복구를 검증한 것은 아니다. 복구된 스케줄은 활성 상태로 유지했다.

- 스케줄 ID: `b1d7bc26-84be-49cd-b4b0-2afc1dad9504`
- 프로젝트 ID: `7dd8264a-b675-4b94-9e4b-8e71d2eae1ee`
- 최초 카나리 시점에는 누락 원인을 확인하지 못했다. 후속 조사 결과는 아래에 기록했다.
- 전역 tick 정상 여부만으로는 프로젝트별 실행 스케줄 누락을 발견할 수 없다.

### 후속 조사: GitHub 연결을 나중에 추가하는 경로의 생성 누락

현재 UI는 프로젝트 생성 시 이름과 활성 여부만 전송하고, GitHub 연결은 이후 설정에서 추가한다. `ProjectService.create`는 생성 시 GitHub 연결이 있을 때만 dispatch 스케줄을 만든다. 반면 `update`에서 호출하는 `sync_dispatch_schedules`는 기존 행을 수정할 뿐, 조회 결과가 비어 있으면 아무 작업도 하지 않는다.

로컬 DB/API 재현 결과:

| 경로 | 기대 | 실제 |
| --- | --- | --- |
| GitHub 연결을 포함해 프로젝트 생성 | dispatch 스케줄 1개 | 기존 lifecycle 테스트 통과 |
| 이름만으로 생성 후 GitHub 연결 추가 | dispatch 스케줄 1개 | API 저장은 200, 스케줄은 0개 |
| 프로젝트 dispatch를 일반 스케줄 API로 삭제 | 프로젝트 소유 작업 보호 필요 | 삭제가 200으로 허용됨 |

기존 lifecycle 테스트는 생성 요청에 연결을 함께 넣어 실제 UI의 두 단계 흐름을 검증하지 않았다. 임시 진단 테스트는 이 두 누락을 재현한 후 작업 트리에서 제거했다. 조사 단계에서는 애플리케이션 코드를 변경하지 않았다.

운영 요청 로그에는 동일 배포 revision에서 2026-09-21 22:20:41 KST 프로젝트 생성(201), 22:28:03 KST 프로젝트 수정(200)이 기록돼 있다. 생성부터 이번 카나리 직전까지 조회한 Cloud Run HTTP 로그에서는 스케줄 삭제 요청을 찾지 못했다. 요청 본문은 확인할 수 없으므로 과거 요청 내용을 확정할 수는 없지만, UI 흐름·코드·재현 결과상 뒤늦은 GitHub 연결 시 생성 누락이 이번 현상과 일치한다.

### 후속 수정 — 미배포

- GitHub 연결을 저장할 때 스케줄이 없으면 생성하고, 있으면 같은 스케줄을 갱신한다. 반복 저장해도 추가 생성하지 않는다.
- 연결 해제 시 기존 스케줄을 비활성화한다. 재연결 시 기존 ID와 실행 이력을 유지하고 다음 실행 시각을 다시 계산한다.
- 최초 생성과 실행 간격 변경 모두 프로젝트에 설정된 간격을 적용한다.
- 일반 스케줄 API에서 dispatch 작업의 직접 생성·수정·삭제와 다른 작업을 dispatch로 바꾸는 요청을 409로 거절한다. UI는 직접 조작 버튼 대신 프로젝트 설정 링크를 표시한다.
- 기존 연결 프로젝트의 누락 스케줄은 프로젝트 설정을 다시 저장하면 보정된다. 배포 시 일괄 보정은 추가하지 않았다. `test-sandbox`는 앞서 수동 보정한 상태다.

관련 SQLite 통합 테스트 79개, 전체 백엔드 테스트 622개, PostgreSQL lifecycle·회귀 테스트 7개가 통과했다. 새 회귀 테스트는 `tests/integration/features/project_management/projects/test_dispatch_schedules.py`에 있다. `just lint`, `just check` 및 프런트엔드 테스트 110개도 통과했다.

### 수정 요청의 실패 로그 발췌 — 수정 완료, 미배포

실제 Actions 로그에는 assertion traceback이 있었지만, Hub의 수정 댓글에 들어간 발췌는 checkout 정리와 Node.js 경고 등 로그 끝부분만 포함했다. 실패한 job 이름 `test`는 올바르게 전달됐다.

이번에는 PR 본문에 기대 동작을 명시했고 Codex가 직접 재현할 수 있어 수정에 성공했다. 최초 카나리 결과가 실패 로그 전달 품질까지 검증한 것은 아니다.

후속 수정에서는 오류·예외 메시지와 주변 코드를 우선 발췌한다. 인식되는 메시지가 없으면 첫 Actions 실패 종료 표시 직전의 출력을 사용하고, 종료 표시도 없을 때만 로그 끝부분을 사용한다. 타임스탬프와 ANSI 색상 코드를 제거하며, 기존 비밀값 마스킹을 발췌·잘라내기 전에 적용한다. job당 1,000자, 최대 3개 job, 다운로드 2MB 제한은 유지한다.

실제 PR #7의 실패 job `106567029156` 로그 14,429자를 수정된 함수로 재생했다. 결과 950자에 traceback, 실패 assertion, `AssertionError: absolute_difference(8, 3) must equal 5`가 모두 포함되고 checkout 정리 로그는 제외됐다. 새 카나리 요청이나 배포는 하지 않았다.

회귀 테스트는 긴 정리 로그, 긴 traceback, 컴파일러·테스트 오류, 작은 길이 제한, 비밀값 마스킹을 다룬다. DB/API 통합 테스트에서는 발췌가 CI-fix 요청에 저장되고, 로그 API가 403을 반환해도 수정 요청 준비가 계속되는 것을 확인한다.

이 수정 후 전체 백엔드 테스트 643개와 `just lint`, `just check`가 통과했다.

## 범위

이번 결과는 단일 PR의 CI 자동 수정 경로에 한정한다. 충돌 자동 해결, 웹훅 누락 복구, Jules, Draft 승인, 장애 직후 댓글 재조정은 검증하지 않았다. 텔레그램은 사용자 요청에 따라 제외했다.
