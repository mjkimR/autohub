# Work plan 카나리 결과 — 2026-09-28: webhook 직후 Issue 동기화

`mjkimR/test-sandbox`에서 1-item Plan을 API로 등록해 webhook 처리 직후 Issue 동기화를 확인했다.
수동 advance·tick·재전송은 하지 않았다. #1은 `autohub-00004-96p`, #2는 순서 보정을 배포한
`autohub-00006-dz7`이다.

| 검증 | 증거 | 결과 |
| --- | --- | --- |
| #1 등록 즉시 시작 | PR [#31](https://github.com/mjkimR/test-sandbox/pull/31) | 등록 응답 8초 안에 run·PR 생성, 자동 머지 00:46:48Z |
| #1 Issue 즉시 생성 | Item [#32](https://github.com/mjkimR/test-sandbox/issues/32) 00:44:51Z, Plan [#33](https://github.com/mjkimR/test-sandbox/issues/33) 00:44:54Z | PR webhook 처리 뒤 11~14초, tick 이전 |
| #1 Plan Issue 닫힘 | #33 00:46:51Z | 머지 뒤 3초 |
| #1 Item Issue 닫힘 | #32 00:50:06Z | **tick에서 닫힘.** 아래 문제 |
| #2 Issue 생성 순서 | Plan [#35](https://github.com/mjkimR/test-sandbox/issues/35) 01:12:06Z → Item [#36](https://github.com/mjkimR/test-sandbox/issues/36) 01:12:09Z | Plan 먼저, Item은 첫 게시에서 부모 연결 |
| #2 Issue 닫힘 | PR [#34](https://github.com/mjkimR/test-sandbox/pull/34) 머지 01:13:08Z → #36 01:13:11Z, #35 01:13:14Z | 머지 뒤 3~6초, tick 미대기 |

## 발견·보정: Item mirror가 Plan보다 먼저 처리되면 5분 쿨다운

같은 트랜잭션에서 만든 Plan/Item `WorkIssueMirror`는 `created_at`이 같아 순서가 id로 결정됐다.
Item이 먼저 처리되면 sub-issue 연결이 "Waiting for the parent issue record to synchronize"로 실패하고
lease 시점의 5분 쿨다운이 남아 이후 webhook 즉시 동기화가 건너뛴다. 실행에는 영향이 없고
Item Issue의 부모 연결·닫힘만 tick까지 밀린다.

보정: `issue_sync.py`에서 아직 Issue가 없는 Plan 행을 먼저 선택한다(`next_action_at`, Plan 우선,
`created_at`, `id`). 회귀 테스트로 고정했고 #2에서 재확인했다.
