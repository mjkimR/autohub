# CI 실패 자동 복구 카나리 — 2026-09-22

## 결과

배포 revision `autohub-00008-xtl`에서 CI 실패 감지 → Codex 수정 요청 → 수정 push → 새 head의 CI 성공 → 자동 squash merge를 확인했다. Hub run의 최종 상태는 `completed`다. 이는 최초 카나리 결과이며, 후속 수정 배포 후 검증은 아래에 별도로 기록했다.

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

문제 발생 당시 UI는 프로젝트 생성 시 이름과 활성 여부만 전송하고, GitHub 연결은 이후 설정에서 추가한다. `ProjectService.create`는 생성 시 GitHub 연결이 있을 때만 dispatch 스케줄을 만든다. 반면 수정 전 `update`에서 호출하는 `sync_dispatch_schedules`는 기존 행을 수정할 뿐, 조회 결과가 비어 있으면 아무 작업도 하지 않는다.

로컬 DB/API 재현 결과:

| 경로 | 기대 | 실제 |
| --- | --- | --- |
| GitHub 연결을 포함해 프로젝트 생성 | dispatch 스케줄 1개 | 기존 lifecycle 테스트 통과 |
| 이름만으로 생성 후 GitHub 연결 추가 | dispatch 스케줄 1개 | API 저장은 200, 스케줄은 0개 |
| 프로젝트 dispatch를 일반 스케줄 API로 삭제 | 프로젝트 소유 작업 보호 필요 | 삭제가 200으로 허용됨 |

기존 lifecycle 테스트는 생성 요청에 연결을 함께 넣어 실제 UI의 두 단계 흐름을 검증하지 않았다. 임시 진단 테스트는 이 두 누락을 재현한 후 작업 트리에서 제거했다. 조사 단계에서는 애플리케이션 코드를 변경하지 않았다.

운영 요청 로그에는 동일 배포 revision에서 2026-09-21 22:20:41 KST 프로젝트 생성(201), 22:28:03 KST 프로젝트 수정(200)이 기록돼 있다. 생성부터 이번 카나리 직전까지 조회한 Cloud Run HTTP 로그에서는 스케줄 삭제 요청을 찾지 못했다. 요청 본문은 확인할 수 없으므로 과거 요청 내용을 확정할 수는 없지만, UI 흐름·코드·재현 결과상 뒤늦은 GitHub 연결 시 생성 누락이 이번 현상과 일치한다.

### 후속 수정 — 배포 후 API 검증 완료

- GitHub 연결을 저장할 때 스케줄이 없으면 생성하고, 있으면 같은 스케줄을 갱신한다. 반복 저장해도 추가 생성하지 않는다.
- 연결 해제 시 기존 스케줄을 비활성화한다. 재연결 시 기존 ID와 실행 이력을 유지하고 다음 실행 시각을 다시 계산한다.
- 최초 생성과 실행 간격 변경 모두 프로젝트에 설정된 간격을 적용한다.
- 일반 스케줄 API에서 dispatch 작업의 직접 생성·수정·삭제와 다른 작업을 dispatch로 바꾸는 요청을 409로 거절한다. UI는 직접 조작 버튼 대신 프로젝트 설정 링크를 표시한다.
- 기존 연결 프로젝트의 누락 스케줄은 프로젝트 설정을 다시 저장하면 보정된다. 배포 시 일괄 보정은 추가하지 않았다. `test-sandbox`는 앞서 수동 보정한 상태다.

관련 SQLite 통합 테스트 79개, 전체 백엔드 테스트 622개, PostgreSQL lifecycle·회귀 테스트 7개가 통과했다. 새 회귀 테스트는 `tests/integration/features/project_management/projects/test_dispatch_schedules.py`에 있다. `just lint`, `just check` 및 프런트엔드 테스트 110개도 통과했다.

### 수정 요청의 실패 로그 발췌 — 배포 후 실제 댓글 검증 완료

실제 Actions 로그에는 assertion traceback이 있었지만, Hub의 수정 댓글에 들어간 발췌는 checkout 정리와 Node.js 경고 등 로그 끝부분만 포함했다. 실패한 job 이름 `test`는 올바르게 전달됐다.

이번에는 PR 본문에 기대 동작을 명시했고 Codex가 직접 재현할 수 있어 수정에 성공했다. 최초 카나리 결과가 실패 로그 전달 품질까지 검증한 것은 아니다.

후속 수정에서는 오류·예외 메시지와 주변 코드를 우선 발췌한다. 인식되는 메시지가 없으면 첫 Actions 실패 종료 표시 직전의 출력을 사용하고, 종료 표시도 없을 때만 로그 끝부분을 사용한다. 타임스탬프와 ANSI 색상 코드를 제거하며, 기존 비밀값 마스킹을 발췌·잘라내기 전에 적용한다. job당 1,000자, 최대 3개 job, 다운로드 2MB 제한은 유지한다.

실제 PR #7의 실패 job `106567029156` 로그 14,429자를 수정된 함수로 재생했다. 결과 950자에 traceback, 실패 assertion, `AssertionError: absolute_difference(8, 3) must equal 5`가 모두 포함되고 checkout 정리 로그는 제외됐다. 새 카나리 요청이나 배포는 하지 않았다.

회귀 테스트는 긴 정리 로그, 긴 traceback, 컴파일러·테스트 오류, 작은 길이 제한, 비밀값 마스킹을 다룬다. DB/API 통합 테스트에서는 발췌가 CI-fix 요청에 저장되고, 로그 API가 403을 반환해도 수정 요청 준비가 계속되는 것을 확인한다.

이 수정 후 전체 백엔드 테스트 643개와 `just lint`, `just check`가 통과했다.

## 범위

최초 PR #7과 재배포 후 PR #8의 결과는 CI 자동 수정 경로에 한정한다. 충돌 자동 해결, 웹훅 누락 복구, Jules, Draft 승인, 장애 직후 댓글 재조정은 검증하지 않았다. 텔레그램은 사용자 요청에 따라 제외했다.


## 재배포 후 검증 — 완료

Cloud Run `autohub-00009-mqv`가 트래픽 100%를 받는 것을 확인했다. 이미지는 `sha256:4febb2005804b62d9c29e583914b2d8d13f4ae4f3c43ee7915983b30c02b0019`이며 revision 생성 시각은 09:46:15 KST다. 로컬 HEAD는 `231b203`이며, 배포 이미지와의 commit 일치는 별도로 확인하지 않았다.

### 스케줄 API 회귀

기존 sandbox 설정을 유지한 채 비활성 임시 프로젝트로 두 단계 생성 흐름을 검증했다. 중복 repository 연결 제한 때문에 설정 전용 이름 `mjkimr/test-sandbox-schedule-canary`를 사용했으며, 실제 GitHub 저장소 접근이나 에이전트 실행은 하지 않았다.

- 연결 없이 생성: dispatcher 0개.
- 이후 GitHub 설정 저장: 비활성 dispatcher 1개, 간격 60초.
- 동일 설정 재저장: ID와 다음 실행 시각 유지.
- 프로젝트 간격을 120초로 변경: 같은 dispatcher에 반영.
- 일반 스케줄 API의 PATCH·DELETE: 모두 409로 차단.
- 연결 해제·재연결: 같은 dispatcher ID 유지.
- 임시 프로젝트 삭제 후 프로젝트와 소유 스케줄이 모두 제거됐음을 확인.

이 검증은 배포 API의 설정 저장·스케줄 수명주기 범위이며, UI 조작이나 새로 생성한 활성 스케줄의 실제 실행은 검증하지 않았다. 기존 sandbox의 활성 스케줄은 아래 CI 카나리에 사용한다.

### CI 실패 로그와 자동 복구

[PR #8](https://github.com/mjkimR/test-sandbox/pull/8)에 `sum_of_squares(a, b)`를 잘못 구현하고 정상 기대값을 검사하는 assertion 4개를 추가했다. 로컬 실패·성공 대조군을 확인하고, [최초 CI 실패](https://github.com/mjkimR/test-sandbox/actions/runs/35673517470) 후 `implemented=true`로 등록했다.

- Hub run: `6eb90faf-1efe-4680-a4b1-65c7f566a9b4`
- 최초 head: `4a97af5b58f9b95c11826cc59795c52f7c457103`
- 등록 시각: 2026-09-22 09:50:01 KST
- [CI-fix 요청 댓글](https://github.com/mjkimR/test-sandbox/pull/8#issuecomment-5769717249) 1건, attempt `b2c78bcf-8435-4b59-a1ef-2b6783dd3a4b`.
- 실제 댓글의 로그 발췌는 981자이며 traceback, 실패 assertion, `AssertionError: sum_of_squares(8, 3) must equal 73`가 포함됐다. checkout 정리 로그가 제외되고 1,000자 제한을 지키는지 자동 검증했다.
- Codex 수정 head: `506a9340a47cf3c25b09c70bc3118c309b15a4bc`. 구현 한 줄만 `return a ** 2 + b ** 2`로 수정했고 assertion 4개·기존 코드·workflow는 유지됐다. 수정 소스를 내려받아 기존 CI 명령과 같은 실행을 로컬에서 재검증했다.
- [새 head CI](https://github.com/mjkimR/test-sandbox/actions/runs/35673910385)는 성공했다.
- 10:00 정기 tick에서 자동 squash merge됐고, 10:00:12 KST에 Hub run과 CI-fix attempt가 `completed`가 됐다. 최종 수정 요청은 1건이다.
- Merge commit: `6d1a4792bbcf122d656ba7f51b87c86312e77e13`.
- 수동 advance·수동 tick·수동 merge 없이 진행했다. 09:50~09:55의 지연에는 아래 scheduler 인증 복구가 포함된다.


### 재배포 직후 Cloud Scheduler 인증 복구

09:50 KST 호출이 401 `UNAUTHENTICATED`로 실패했다. Cloud Scheduler의 `X-API-Key` 값이 Secret Manager에 저장된 기존 scheduler credential과 달랐고, 폐기된 `X-Scheduler-Key` 헤더도 남아 있었다. 기존 machine의 활성 여부·scope·key 유효성을 관리 API로 확인한 뒤 저장된 키를 다시 적용하고 구형 인증 헤더를 제거했다. 키를 새로 발급하거나 회전하지 않았다.

사용자 확인에 따라 외부 tick의 `*/5 * * * *`(5분)는 의도한 설정으로 유지했다. 프로젝트의 60초 간격은 내부 최소 간격이며 외부 호출 주기를 의미하지 않는다. 호출 URL도 유지했다. 인증 복구 후 09:55 정기 tick은 HTTP 200으로 성공했고, CI-fix 요청 전송까지 진행했다.

기본 `python3`가 Python 3.9여서 `scripts/provision-scheduler.py`는 `datetime.UTC` import 단계에서 중단됐다. 이 시도는 운영 설정을 변경하지 않았다. 인증 복구는 프로젝트 `.venv/bin/python`에서 기존 provision 검증 함수를 사용했으며, 기본 provision 명령의 1분 설정은 적용하지 않았다.


이번 재검증에서는 애플리케이션 코드를 변경하지 않았다. `just lint`, `just check`, `git diff --check`가 통과했다.

### 상위 workbench 배포 경로 수정

사용자가 재배포에 사용한 명령은 상위 저장소의 `just deploy autohub`였다. 해당 저장소의 `config/deployments.yaml`은 구형 `SCHEDULER_KEY`를 `X-Scheduler-Key`로 적용하고 정상 `X-API-Key`를 제거하도록 지정했다. `scripts/deploy.py`가 이 설정으로 매번 scheduler job을 갱신하므로, 현재 Hub의 머신 키 인증 계약과 불일치했다.

상위 배포 코드는 Auto Hub의 `scripts/provision-scheduler.py`를 같은 Python 인터프리터로 호출하도록 수정했다. Auto Hub CLI에 `--schedule` 옵션을 추가하고 workbench에 설정된 5분 간격을 전달한다. 기존 credential은 검증 후 재사용하고, 구형 인증 헤더를 제거한다. 환경 템플릿·inventory도 관리 전용 `APP_API_KEY_ROOT_KEY`로 전환하며 기존 관리 키·웹훅·커넥터 키 보존을 회귀 테스트로 확인한다.

수정된 상위 함수의 scheduler 단계만 실제 실행해 기존 머신 `6965fcf0-eab8-45a3-805d-3f663d7845f7` 재사용과 설정 적용에 성공했다. 이미지 재배포는 하지 않았다. 다음 배포에는 두 저장소의 수정이 모두 필요하다.


최종 검증: workbench `just verify`에서 98개 테스트와 consumer pin 검증이 통과했고, Auto Hub provisioner 테스트 14개 및 `just lint`, `just check`가 통과했다. 운영 조회에서 저장된 key ID `538afd98-f29f-45e9-b90f-b1d74da471e8`의 값이 `X-API-Key`와 일치하고 tick이 `*/5 * * * *`임을 확인했다. `gcloud --remove-headers`는 이 환경에서 구형 헤더 이름을 빈 값으로 남기므로, 이름의 부재가 아니라 구형 인증값이 비어 있는지 검증했다. 코드·문서 변경은 커밋하지 않았다.
