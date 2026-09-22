# 웹훅 누락 복구 카나리 — 2026-09-22

## 검증 대상

[mjkimR/test-sandbox PR #12](https://github.com/mjkimR/test-sandbox/pull/12)를 등록한 뒤 Auto Hub용 repository webhook을 잠시 비활성화한다. GitHub의 Ready 전환과 CI 성공 이벤트가 Hub에 전달되지 않는 동안, 정기 polling이 현재 상태를 조회해 자동 머지하는지 확인한다. 최초 등록 자체가 누락된 `@auto-run`의 발견이나 수신 후 처리 실패 재시도는 이번 범위가 아니다.

배포 revision은 `autohub-00009-mqv`이며 외부 Cloud Scheduler는 기존 `*/5 * * * *`를 유지한다. 프로젝트 설정, 스케줄 간격, workflow는 변경하지 않는다. 텔레그램은 제외한다.

| 항목 | 값 |
| --- | --- |
| Hub run | `96d6be64-67c4-47f7-9811-3486164e784d` |
| 기준 main | `e269696af7ed900c02af9e5d77507e5a0b8d0ff1` |
| PR head | `1973cd3db8f1b1f509f889637698eec055e2b1d9` |
| Sandbox webhook | `682791717` |

## 재현

1. 기존 `clamp` 함수의 양 끝 경계값 assertion 두 개를 추가했다. 로컬 `python hello.py`와 [최초 CI](https://github.com/mjkimR/test-sandbox/actions/runs/35677176585)가 성공했다.
2. Draft PR을 `implemented=true`로 등록하고 초기 상태를 수동 advance로 관찰했다. 10:49:43 KST에 `awaiting_ci`, Draft 승인 대기, 에이전트 요청 0건을 확인했다. 다음 실행 가능 시각은 10:54:42 KST였다.
3. 10:50:30 KST에 sandbox Auto Hub webhook만 `active=false`로 변경했다. 기존 PR 관련 delivery 4개는 모두 `processed`였으며 미처리 이벤트가 없었다. URL, 이벤트 목록, secret은 변경하지 않았다.
4. 10:50:33 KST에 PR을 Ready로 전환했다. [Ready 이벤트로 실행된 CI](https://github.com/mjkimR/test-sandbox/actions/runs/35677259553)도 동일 head에서 성공했다.
5. Ready 이후 수동 advance, scheduler 강제 실행, delivery 재전송, 직접 merge 없이 읽기 전용 조회만 수행했다. 10:52:30 KST에도 Hub는 기존 Draft 승인 대기 상태였고 PR은 open이었다.

## 결과

통과했다. 웹훅이 비활성인 동안 10:55:11 KST에 자동 squash merge됐고, 10:55:12 KST에 run과 synthetic implementation attempt가 `completed`가 됐다. Ready 전환부터 완료까지 약 4분 39초가 걸렸다.

- Cloud Run의 정기 dispatcher 요청은 10:55:04 KST에 시작해 약 8.59초 후 HTTP 200으로 완료됐다. Cloud Scheduler 로그도 HTTP 200을 기록했다.
- 비활성화 시점부터 복구 시점까지 sandbox의 새 webhook delivery는 0건이었다. PR 관련 기존 delivery 4개는 상태·처리 횟수까지 동일했다. 같은 시간대 Cloud Run 요청 로그에도 webhook 수신이나 해당 run의 수동 advance 요청이 없었다.
- 완료 확인 시에도 webhook은 `active=false`였다. 10:56:02 KST에 원래 `active=true`로 복구하고 URL과 이벤트 목록이 원래 값과 일치하는지 다시 조회했다.
- Merge commit은 `61206ce317b99ff406341447473ec8d8fbffe206`이다. 머지된 `hello.py`는 처음 준비한 소스와 정확히 같고 변경 파일도 `hello.py` 하나였다.
- 에이전트 요청은 0건이다. 수동 관찰은 차단 전 초기 Draft 상태 설정에만 사용했다. Ready 이후에는 polling만으로 승인 상태와 CI를 재확인해 완료했다.

이 결과는 **이미 등록된 실행의 웹훅 누락 복구**를 검증한다. 등록 트리거 자체가 Hub에 도착하지 않은 PR의 자동 발견까지 검증하거나 보장하지 않는다.

`just lint`, `just check`, `git diff --check`가 통과했다. 이번 작업은 운영 카나리와 결과 문서 작성이며 Auto Hub 코드를 수정하거나 커밋하지 않았다.
