# Work plan 실서비스 카나리 결과 — 2026-09-23

`mjkimR/test-sandbox`와 Cloud Run에서 WorkPlan·WorkItem의 실제 실행을 두 차례 검증했다.
#1은 tick 기반 동작과 pause/revoke를, #2는 즉시 후속 실행(요청 내 kick)과 Cloud Tasks
webhook 처리를 확인했다. PR/Issue 링크는 GitHub 증거이며 이전 카나리는
[2026-09-22 결과](canary-results-2026-09-22.md)에 있다.

## 결과

| 검증 | 증거 | 확인한 결과 |
| --- | --- | --- |
| #1 의존 Item 순차 실행 | PR [#18](https://github.com/mjkimR/test-sandbox/pull/18), [#20](https://github.com/mjkimR/test-sandbox/pull/20) | `is-odd` 머지 후에만 `count-odd` 시작, 두 PR 자동 머지 후 Plan `completed`. 시작·후속은 모두 5분 tick 시점 |
| #1 Issue 사본 | Plan [#17](https://github.com/mjkimR/test-sandbox/issues/17), Item [#16](https://github.com/mjkimR/test-sandbox/issues/16), [#19](https://github.com/mjkimR/test-sandbox/issues/19) | Plan Issue와 Item sub-issue 연결, 완료 후 닫힘 |
| #1 pause/revoke | Plan [#21](https://github.com/mjkimR/test-sandbox/issues/21)·Item [#22](https://github.com/mjkimR/test-sandbox/issues/22), 하위 Plan [#23](https://github.com/mjkimR/test-sandbox/issues/23)·Item [#24](https://github.com/mjkimR/test-sandbox/issues/24) | pause 중 미시작 유지, revoke로 미시작 Item `revoked`. revoke된 Plan에 의존한 Plan은 시작 없이 revoke 가능. PR/run 생성 0 |
| #2 등록 즉시 시작 | PR [#25](https://github.com/mjkimR/test-sandbox/pull/25) | 등록 요청 응답 안에서 첫 Item run과 PR 생성(생성 후 약 0.4초에 시작) |
| #2 머지 즉시 후속 | PR [#29](https://github.com/mjkimR/test-sandbox/pull/29) | #25 머지 01:36:07Z → 의존 Item 시작 01:36:09Z. #29 머지 3초 뒤 Plan `completed` |
| #2 Cloud Tasks webhook | Cloud Run 요청 로그 | GitHub 응답 202(0.1–0.5초), 이어서 `/deliveries/{id}/process` 204. 백그라운드 처리 경로 미사용 |
| #2 Issue 사본 | Plan [#26](https://github.com/mjkimR/test-sandbox/issues/26), Item [#27](https://github.com/mjkimR/test-sandbox/issues/27), [#28](https://github.com/mjkimR/test-sandbox/issues/28) | 등록 뒤 첫 tick에 생성, 완료 뒤 다음 tick에 모두 닫힘 |

배포 기준: #1은 서비스 재생성 이전 revision, #2는 서비스 재생성 후 `autohub-00001-spj`, 동시 요청
확인은 `autohub-00002-rcl`이다. 최종 main의 `hello.py`는 네 helper와 marker A–D를 모두
포함하고 실행이 성공한다.

## 재현 요점과 판정 범위

- Item은 기존 helper 뒤에 함수를 추가하고 `__main__`에 marker 주석과 assertion을 붙이는
  작은 변경으로 한정했다. 두 번째 Item은 첫 Item의 함수를 호출하도록 명세해 순서를 강제했다.
- #2는 UI 탭을 닫은 상태에서 API로 등록하고 Plan 조회만 20초 간격으로 반복했다.
  수동 advance·tick·재전송은 하지 않았다.
- `waiting` Item의 API `detail`은 비어 있는 것이 정상이다. UI가 의존 관계로
  "Waiting for tasks/plans", "Plan paused" 등을 계산한다(단위 테스트로 고정).
- Issue 생성·닫기는 여전히 tick 주기(최대 5분)를 따른다. 실행은 Issue를 기다리지 않는다.

## 발견한 문제와 완료한 보정

| 문제 | 최종 처리 |
| --- | --- |
| run lease 경합(409)으로 미뤄진 webhook이 실패로 기록 | 경합은 `processed`와 사유로 기록하고 다음 관찰에 맡김 |
| Issue 재시도 cooldown이 tick보다 1초 늦게 끝나 한 주기를 건너뜀 | 성공 시 `next_action_at`을 비워 다음 tick에서 바로 처리 |
| 후속 Item이 tick까지 대기 | 등록·수정·재개와 머지 webhook 처리 요청 안에서 kick(최대 25초) |
| 응답 후 백그라운드 webhook 처리가 CPU throttling으로 지연 | Cloud Tasks queue가 별도 요청으로 처리. HMAC 서명 callback, 실패 시 기존 방식으로 대체 |
| 공유 무료 PostgreSQL(20 연결) 고갈로 새 revision 시작 실패 | 인스턴스 1·worker 1·pool 3+3·`MAX_CONCURRENT_TASKS` 3, planroot도 상한 설정 |
| UI 동시 요청에서 pool 교착(30초 timeout 500, webhook 응답 18초) | 인증이 요청 세션을 끝까지 잡던 문제를 app-common에서 수정. 동시 20요청 1초 내 200 확인 |

## 정리 상태와 제외 범위

- 카나리 PR은 모두 머지됐고 `autohub/work/*` 브랜치는 저장소 설정상 남아 있다.
- 큐 대기 run의 슬롯 반환, base 변경 뒤 충돌 감지, Jules 수집, 재시도는 여전히 tick
  주기를 따른다. Issue는 카나리 이후 webhook 처리 뒤 즉시 동기화하도록 바꿨으며 live
  확인은 아직 하지 않았다.
- 실패 Item 재시도, Plan 수정에 따른 revision 충돌, 실제 CI 실패가 섞인 Plan은 live로
  유발하지 않았다.
