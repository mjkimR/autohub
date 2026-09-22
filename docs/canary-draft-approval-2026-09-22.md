# Draft 승인 카나리 — 2026-09-22

## 결과

배포 revision `autohub-00009-mqv`에서 [mjkimR/test-sandbox PR #11](https://github.com/mjkimR/test-sandbox/pull/11)의 Draft 승인과 현재 head CI 조건이 모두 통과했다. 최종 Ready 이후 10:40:11 KST에 자동 squash merge됐고, 10:40:12 KST에 run과 attempt가 `completed`가 됐다. `main` branch API의 `protected=false`를 확인했다. rulesets 조회는 계정 기능 제한으로 403을 반환했으며, ruleset 목록을 확인한 것으로 취급하지 않는다.

이 카나리는 상태 전환 직후 수동 관찰 API(`/pipeline-runs/{id}/advance`)로 승인·CI 조건을 판정한다. 최종 Ready 승인 이후에는 수동 advance 없이 자동 머지를 확인했다. GitHub에서 직접 merge하거나 프로젝트 설정을 바꾸지 않았다. 텔레그램은 범위에서 제외한다.

## 준비

정상 구현 `clamp(value, lower, upper)`와 경계값 assertion 3개를 추가한 Draft PR을 만들었다. 기존 함수·assertion·workflow는 유지했다. 로컬 실행과 [최초 CI](https://github.com/mjkimR/test-sandbox/actions/runs/35676086772)가 성공한 뒤 `implemented=true`로 등록했다.

| 항목 | 값 |
| --- | --- |
| Hub run | `260d1fa3-5e1c-4dd1-8d67-34ec889c7a32` |
| 기준 main | `24aa2f6ce88d3fe59e3164bd24f10be983b0853a` |
| 최초 head | `e637e074b63804fdbf783174090b0b903d20051a` |

## 검증 단계

### 1. Draft + CI 성공 — 통과

10:32:58 KST 관찰에서 run은 `awaiting_ci`, PR은 Draft/open 상태였다. `pause_reason`은 `Waiting for approval: the pull request is a draft. Mark it ready for review to approve merging. Automatic merge requires passing CI and must be enabled for this project.`였다. 에이전트 요청은 0건이다.

### 2. Ready + 현재 head CI 없음 — 통과

주석만 추가한 새 커밋 `9c4a8a7e7ccaaabbc429beb9ac37f04be7634a32`에 `[skip ci]`를 사용한 뒤 Ready로 전환했다. 현재 head의 pull_request workflow run은 0건이다.

10:35:06 KST 관찰에서 `awaiting_ci`를 유지하고 Draft 승인 대기 사유는 사라졌다. PR은 Ready/open이며 머지되지 않았다. 최초 head의 성공한 CI는 새 head를 승인하는 데 사용되지 않았다. 수정 요청도 0건이다.

Ready 전환 직후 첫 관찰 요청은 409를 반환했다. 이후 lease가 없는 상태에서 재관찰해 위 결과를 확인했다. 첫 409의 구체적인 원인은 확정하지 않았으며 카나리 판정은 성공한 재관찰 결과를 사용한다.

### 3. 다시 Draft + 새 CI 성공 — 통과

Ready 승인을 취소하고 Draft로 돌린 뒤, skip-CI용 주석을 제거한 정상 커밋 `e4e55c2310740d3bd75acd00d0d025d81555677d`을 push했다. [새 CI](https://github.com/mjkimR/test-sandbox/actions/runs/35676353593)가 성공했다. 관찰 API 성공 후 10:37:55 KST 재조회에서 `awaiting_ci`와 동일한 `Waiting for approval` 사유, Draft/open 상태를 확인했다. 요청 수는 0건이다.

### 4. 최종 Ready + 현재 head CI 성공 — 통과

10:37:57 KST에 최종 Ready로 전환했다. Ready 이벤트가 실행한 [동일 head의 새 CI](https://github.com/mjkimR/test-sandbox/actions/runs/35676475973)도 성공했다. 승인 대기 사유는 사라졌으나 이전 Draft 관찰에서 설정된 `next_action_at=10:42:11 KST`는 남았다. 하지만 최종적으로 10:40 정기 tick 구간에 자동 머지됐다. 재확인 시각만 보고 10:45 처리로 예상했던 중간 안내는 실제 결과와 달랐다. 최종 Ready 이후 운영자의 수동 advance는 사용하지 않았다.


## 최종 증거와 관찰 범위

- 최종 head: `e4e55c2310740d3bd75acd00d0d025d81555677d`.
- Merge commit: `e269696af7ed900c02af9e5d77507e5a0b8d0ff1`.
- GitHub merge: 10:40:11 KST, Hub 완료: 10:40:12 KST.
- 10:40:05에 시작한 Cloud Scheduler trigger 요청은 HTTP 200으로 성공했다. merge 직후 10:40:13에는 GitHub webhook이 202로 수신됐다. 웹훅이 활성 상태였으므로 polling 단독 경로로 일반화하지 않는다.
- 최종 merge commit의 소스는 처음 작성한 정상 구현과 일치한다. skip-CI용 임시 주석은 제거됐고, workflow는 변경되지 않았다.
- 전체 에이전트 요청은 0건이며 synthetic implementation attempt 하나만 완료됐다.
- Ready 전환 및 Draft 복귀 직후 각각 첫 수동 관찰에 409가 있었으나 후속 관찰은 200으로 성공했다. 구체적 경합 원인은 별도로 확정하지 않았다.

Draft/Ready 상태와 CI를 분리해 검증한 결과이며, UI 조작이나 텔레그램 발송은 검증하지 않았다. Required review/branch protection 정책도 범위 밖이다. 다음 카나리는 웹훅 누락 복구와 Jules 실연동이다.

관련 로컬 병합·Draft 통합 회귀 테스트 40개와 `just lint`, `just check`, `git diff --check`가 통과했다. 이번 작업은 운영 카나리와 결과 문서 작성이며 Auto Hub 코드를 수정하거나 커밋하지 않았다.
