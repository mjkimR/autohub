# 카나리 결과 — 2026-10-02: 실행 중 중단과 대체 Plan 복구

[2026-10-01 카나리](canary-results-2026-10-01.md)에 이어 `mjkimR/test-sandbox`와 `personal-codex`(동시 실행 1)로
Run·Plan 중단 효과(A0)와 취소된 작업의 대체 Plan 복구(A3)를 MCP로 검증했다. 시각은 UTC다.
resume 보정 전은 `autohub-00013-l4q`, 보정 뒤는 `autohub-00014-hrs`(`746959d`)다.

원래 Plan `20b5822d`는 `double` → `triple` → `halve` → `quarter` 순서의 의존 Item 4개다.

| 검증 | 증거 | 결과 |
| --- | --- | --- |
| Run pause 뒤 외부 실행 | PR [#47](https://github.com/mjkimR/test-sandbox/pull/47), 요청 23:13:59 → pause 23:14:00 | Codex가 23:15:57 푸시, CI 통과. Hub는 `paused`를 유지하고 머지하지 않음 |
| Plan pause | Plan pause 23:14:08, `double` 완료 00:13:33 | Plan이 paused인 동안 tick을 지나도 `triple`은 `waiting` |
| Plan resume | 00:20:56 | 같은 요청 안에서 `triple` 시작(PR [#53](https://github.com/mjkimR/test-sandbox/pull/53) 요청 00:21:05) |
| 푸시 뒤 Run resume(보정 후) | `triple` pause 00:21:12, Codex 푸시·답글 00:22:46 | resume 즉시 `awaiting_ci`, 추가 요청 없이 00:25:13 머지 |
| Run cancel | `halve` PR [#54](https://github.com/mjkimR/test-sandbox/pull/54), 요청 00:25:25 직후 cancel | Run `canceled`, Item은 다음 tick(00:30)에 `canceled`. Codex는 취소 뒤에도 00:27:18 푸시 |
| 복구 정리 | #54를 머지 없이 닫음(00:30:35), Plan pause 00:30:39 → revoke 00:30:41 | `quarter`는 `revoked`("Unstarted work was revoked"), Plan `revoked` |
| 대체 Plan | Plan `f2adc4f1`, 설명에 원본 Plan·Item·Run·PR 대응 기록 | `halve` PR [#55](https://github.com/mjkimR/test-sandbox/pull/55) 00:32:25, `quarter` PR [#59](https://github.com/mjkimR/test-sandbox/pull/59) 00:33:56 머지, 00:33:59 `completed` |
| 원본 보존 | 원래 Plan 재조회 | `revoked` 유지, `halve` `canceled`·`quarter` `revoked`. 대체 완료로 성공 처리되지 않음 |

복구 대응은 다음과 같다. `double`(#47)과 `triple`(#53)은 성공했으므로 다시 만들지 않았다.

| 원래 Item | 원래 결과 | 대체 Item | 대체 결과 |
| --- | --- | --- | --- |
| `halve` | Run 취소, #54 머지 없이 닫음 | `halve` | #55 머지 |
| `quarter` | 미시작, Plan revoke로 철회 | `quarter`(대체 `halve`에 의존) | #59 머지 |

## 발견·보정 4: 일시정지 중 푸시된 Run의 resume이 같은 요청을 다시 보냄

`double` Run의 resume이 마지막 요청을 다시 보냈다(23:25:08). Codex는 이미 구현됐다고 답하고 푸시하지 않았고,
5분 뒤 Run이 `blocked`("Codex replied without pushing")가 됐다. 정상 감시는 head가 바뀌면 CI 관찰로 넘어가지만,
resume은 외부 구현 PR만 CI 관찰로 돌렸다.

보정(`746959d`): 답변 없이 resume할 때, 마지막으로 전달한 요청 이후 PR head가 바뀌었으면 다시 보내지 않고
`awaiting_ci`로 돌아간다. head가 그대로이거나 답변을 지정하면 기존처럼 새 attempt를 보낸다. 배포 뒤 `triple`에서
확인했다. 이미 재요청 뒤 막힌 `double`은 마지막 요청의 head가 현재 head와 같아 보정 대상이 아니므로, #47을
직접 머지한 뒤 resume해 `completed`로 끝냈다.

## 관찰

- Run cancel 뒤 Item 반영은 다음 tick까지 최대 5분 걸린다. 그동안 Item은 `running`으로 보인다.
- 대체 Plan의 Item은 다른 Plan의 Item 키에 의존할 수 없다. 처음 등록에서 `halve`에 원래 Plan의 `triple` 의존을
  남겨 거부됐다. 응답은 `MCP_INVALID_ARGUMENTS` "Tool arguments do not match its schema."뿐이고 원인
  ("Dependency target does not exist in this scope")이 빠진다. `app_mcp` registry가 `ValidationError` 내용을
  버리기 때문이며 app-common 쪽 개선 대상이다.
