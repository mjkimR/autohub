# 충돌 자동 해결 카나리 — 2026-09-22

## 결과

배포 revision `autohub-00009-mqv`에서 실제 충돌 감지 → Codex 해결 → 새 head CI 성공 → 자동 squash merge를 확인했다. 10:25:11 KST에 Hub run과 conflict-fix attempt가 모두 `completed`가 됐다. `mjkimR/test-sandbox`에 실제 Git 충돌을 만든 뒤에만 Hub에 등록했다. 외부 Cloud Scheduler tick은 사용자 설정대로 5분이며, 수동 advance나 tick은 사용하지 않았다. 준비 PR #9만 운영자가 머지했고, 검증 PR #10은 Hub가 자동 머지했다.

## 준비와 등록

같은 기준 커밋 `6d1a4792bbcf122d656ba7f51b87c86312e77e13`에서 두 PR을 만들었다. `hello()`의 동일 반환 줄을 서로 다르게 바꾸고 각각의 의도를 확인하는 assertion을 추가했다.

- [준비 PR #9](https://github.com/mjkimR/test-sandbox/pull/9): ` [base-change]` 접미사와 `endswith` assertion.
- [검증 PR #10](https://github.com/mjkimR/test-sandbox/pull/10): `[branch-change] ` 접두사와 `startswith` assertion.
- 기대 결합: `[branch-change] Hello from test-sandbox! [base-change]`.
- 기존 산술 함수·assertion과 CI workflow는 유지한다.

A·B·기대 결합 코드를 각각 로컬에서 실행해 성공하고, `git merge-file`에서 충돌이 생기는지 확인했다. clone 없이 GitHub API로 두 PR을 생성했다. 자동 등록 트리거는 넣지 않았으며, #9 머지 전 두 PR 모두 Hub에 등록되지 않았음을 조회했다.

1. [PR #9 CI](https://github.com/mjkimR/test-sandbox/actions/runs/35675228189) 성공.
2. [PR #10 초기 CI](https://github.com/mjkimR/test-sandbox/actions/runs/35675231532) 성공.
3. 운영자가 #9만 squash merge해 `main`을 `27cf084bac9a6429f850c92f0c5fd8bdc7a37b34`로 변경했다.
4. GitHub가 #10을 `mergeable=false`, `mergeable_state=dirty`로 판정한 뒤 `implemented=true`로 등록했다. 현재 main ref와 #10 head도 확인했다.

| 항목 | 값 |
| --- | --- |
| PR #9 최초 head | `fcafb68519bb343a52260ae6b0210a83b0365c40` |
| PR #10 최초 head | `b79b86d71f23b0f9b2aa55a365e605ed0ef34603` |
| Hub run | `fcc8d8a3-2818-454b-82b1-b58e0867736c` |
| 등록 시각 | 2026-09-22 10:19:38 KST |
| 등록 상태 | `awaiting_ci` |

## 검증 항목 — 모두 통과

- 정기 실행이 `ci-fix`가 아닌 `conflict-fix` 요청을 생성하는지.
- Codex가 현재 main을 반영하고 두 변경·assertion을 모두 보존하는지.
- 새 head의 CI가 통과한 뒤 Hub가 #10을 자동 merge하는지.
- 최종 run 완료 및 요청 중복 여부.


## 진행 증거

10:20 정기 tick에서 최초 attempt에 `MERGE_CONFLICT`를 기록하고, `conflict-fix` attempt `92f8ce4a-fa11-4928-ab69-fccce999462c`를 생성했다. [요청 댓글](https://github.com/mjkimR/test-sandbox/pull/10#issuecomment-5769879553)은 1건이며 `delivery=1`, marker key는 `3af2b025-39da-4c25-909d-6661e45a98cc`다. 현재 main 병합·충돌 해결·검증·push 지시와 양쪽 변경 보존 조건이 포함됐다. 최초 CI는 성공이었으며 `ci-fix` 요청은 발생하지 않았다.


Codex가 해결 커밋 `16a0ff2f0e6b5ac39874b0ad0db82b2d5f624252`를 push했다. GitHub는 `mergeable=true`, `clean`으로 전환됐다. [새 head CI](https://github.com/mjkimR/test-sandbox/actions/runs/35675447054)가 성공했다.

검증 결과:

- `hello()` 반환값이 기대한 접두사·접미사를 모두 포함한다.
- 실제 해결 소스를 실행해 성공했다. 새 assertion 두 개의 순서를 제외한 AST가 기대 결합과 일치하므로, 기존 함수와 모든 assertion이 보존됐다.
- 준비 PR의 main merge commit이 해결 head의 조상임을 GitHub compare API로 확인했다.
- 최초 PR head 대비 변경 파일은 `hello.py` 하나이며 workflow 변경은 없다.
- Hub 요청 댓글은 1건이며 `kind=conflict-fix`다.
- 10:25 정기 tick에서 자동 squash merge됐고 최종 run과 conflict-fix attempt는 `completed`다. 전체 소요 시간은 등록부터 332초였다.
- 최종 merge commit은 `24aa2f6ce88d3fe59e3164bd24f10be983b0853a`이며, 해당 commit의 `hello.py`가 검증한 해결 소스와 완전히 같음을 확인했다.
- 최종 요청 댓글과 Hub의 `requests_sent`는 모두 1건이다.


## 범위와 후속

이번 카나리는 단일 PR의 실제 충돌 자동 복구 경로다. Draft 승인, 웹훅 누락 복구, Jules 실연동은 별도 검증이 필요하다. 텔레그램은 사용자 요청에 따라 제외했다.

Auto Hub 코드 변경은 없으며 결과 문서만 추가·갱신했다. `just lint`, `just check`, `git diff --check`가 통과했다. 테스트 저장소의 준비·해결·병합 결과는 위 commit으로 기록됐고, Auto Hub 작업 트리는 커밋하지 않았다.
