# MCP 분리와 도구별 평가·보완 결과

2026-09-29 로컬 구현 기준. 배포·운영 키 발급·클라이언트 재연결은 아직 수행하지 않았다.
초기 평가는 호출 빈도나 모델별 사용성 실험 결과가 아닌 현재 계약과 일상 작업 흐름에 대한 설계 판단이다.
상·중·하 등급은 최초 판단을 보존하고, 아래에 실제 보완 결과를 기록한다.

## 현재 구성

- 작업용 `/mcp/`: 기존 `autohub:mcp:read` / `autohub:mcp:write`, 조회 9개 + 실행 제어 4개 = **13개**.
- 운영용 `/ops/mcp/`: 별도 machine의 `autohub:mcp:ops`, 프로젝트·연결 테스트 변경 **4개**.
- 작업용은 기본 연결로 유지하고 운영용만 추가로 켜고 끈다. 두 연결을 모두 켜면 중복 없이 **17개**다.
- 조회·revision 확인·테스트 결과 확인은 기본 연결을 사용한다. 운영 연결에 조회를 복제하지 않는다.
- 일반 write 키는 운영 endpoint에 접근할 수 없고, 모든 scope가 있어도 다른 endpoint의 도구를 호출할 수 없다.
- scope는 machine 단위다. 동일 machine에서 키만 하나 더 발급해서는 권한이 분리되지 않는다.

## 평가 기준

- **상: 그대로 유지.** 독립된 목적과 효과가 분명하고 현재 계약으로 직접 필요하다.
- **중: 유지하되 사용 방식 보완.** 호출 시점·입력 선택·재시도·후속 행동을 개선한다.
- **하: 통합·제거 재검토.** 독립 도구로서의 효용을 다른 도구에 포함할 수 있는지 판단한다.

위험도나 구현 품질의 점수가 아니다. 실행 취소도 독립된 의도가 분명하므로 상이다.

## 하 1개 통합 결과

`connectors.list`를 `catalogs.list`와 묶어 **`projects.options`**로 통합했다.
기존 두 이름은 공개 목록·호출에서 제거했고 별칭을 남기지 않았다.
기본 응답은 catalog 선택지이며, 온보딩에는 `connectors_page={}`를 지정해 connector 선택지도 받는다.
기존 프로젝트 정보가 없어도 호출 가능하다. credential·connector config·catalog 내부 정책은 반환하지 않는다.
Catalog와 connector에 독립된 pagination과 total을 제공하므로 한쪽 페이지가 다른 쪽 탐색을 제한하지 않는다.

## 중 8개 보완 결과

| 기존 도구 → 현재 도구 | 연결 | 구현한 보완 |
| --- | --- | --- |
| `catalogs.list` → `projects.options` | 작업용 | capability·enabled 필터, 필터 적용 후 paging, project_id 지정 시 설정된 catalog 선택을 페이지와 무관하게 반환. 온보딩 connector 선택지 통합. 기본 설정이 충분하면 호출 생략 가능. |
| `projects.readiness` | 작업용 | catalog 하나를 지정해 조회 가능. `check_kind=configuration_only`와 `blocked/manual_checks/configured` 상태를 반환해 설정 확인과 실제 검증을 구분. `ready=true`여도 manual 항목은 완료로 취급하지 않음. |
| `connection_tests.list` | 작업용 | catalog·실행 상태·현재 설정 일치 여부 필터와 offset paging 제공. `history_limit=30`, 해당 범위의 matching total, `next_offset` 명시. 오래된 ID는 get으로 직접 조회. |
| `runs.enroll` | 작업용 | `pull_request.implemented`를 필수로 받아 구현 요청과 기존 코드 CI 관측을 구분. 누락·오타 필드를 거부. 응답 유실 시 project_id + pull_number로 기존 실행을 찾도록 안내. |
| `runs.resume` | 작업용 | 검사한 run의 `expected_revision` 필수. 잠금 안에서 비교해 오래된 상태의 재개를 GitHub I/O 전에 거부. 기존 외부 조회 후 revision 재검사도 유지. |
| `projects.create` | 운영용 | GitHub 연결 생성 시 `github.automation.auto_merge` 명시적 선택 필수. 나머지 기본 설정은 schema·응답에 공개. GitHub 없는 프로젝트 생성은 유지. |
| `projects.update` | 운영용 | 선택적 `dry_run`으로 실제 merge·설정 검증을 저장 없이 수행. 경로별 before/after와 `applied` 반환. 같은 expected_revision으로 적용하고 중간 변경은 거부. 기존 nested merge·list replace·연결 해제 규칙 유지. |
| `connection_tests.start` | 운영용 | request_id = test_id 계약을 schema에 명시해 응답 유실 후 바로 get 가능. 선택적 project revision 검사로 오래된 설정에서 새 테스트 시작 방지. 기존 request ID 재전송은 검사보다 먼저 복구. 응답의 next_action으로 cleanup·실패·설정 불일치 후속 행동 구분. |

필수 입력은 에이전트가 의도를 명시하도록 하는 계약이다. 별도의 사용자 승인 단계를 추가하지 않는다.
설정 미리보기 역시 선택 사항이고, 이미 최신 문맥이 있으면 선행 조회를 반복할 필요가 없다.
설정된 catalog가 조회된다는 사실만으로 현재 활성·가용 상태나 CI 검증 성공을 보장하지 않는다.

## 상 9개 유지

| 도구 | 연결 | 유지 이유 |
| --- | --- | --- |
| `projects.list` | 작업용 | 이름·repository로 프로젝트 탐색. |
| `projects.get` | 작업용 | 대상·설정·최신 revision 확인. |
| `runs.list` | 작업용 | 진행 작업 탐색과 등록 응답 유실 복구. |
| `runs.get` | 작업용 | 실행 상태·PR 링크 확인과 변경 대기. |
| `runs.attempts` | 작업용 | 필요할 때만 시도별 실패 원인·외부 대화 링크 조회. |
| `connection_tests.get` | 작업용 | 실제 검증 근거와 cleanup 확인. 공통 테스트 응답에 next_action 추가. |
| `runs.pause` | 작업용 | 재개 가능한 중지. 이미 전달된 외부 작업은 계속될 수 있음. |
| `runs.cancel` | 작업용 | Hub 진행 종료. pause와 다른 효과이므로 독립 유지. |
| `connection_tests.cancel` | 운영용 | 테스트 취소·cleanup 요청. 완료 여부는 get으로 확인. |

현재 도구는 **상으로 평가했던 9개 + 보완한 중 8개 = 17개**다.
하 1개는 options에 통합했으며, 중 도구의 실제 모델 사용성이 검증됐다는 이유로 등급을 자동 상향하지 않는다.

## 사용 흐름과 전환

기존 프로젝트는 get → 명시적인 implemented 선택으로 enroll → get 순서로 사용한다.
실패 원인은 attempts로 조사하고, paused/blocked 원인을 해결한 뒤 현재 revision으로 resume한다.

온보딩·정책 변경 시 기본 연결에 운영 연결을 추가한다. 작업용의 options에서 catalog·connector를 확인하고,
운영용에서 명시적인 자동 머지 설정으로 create하거나 update를 수행한다. 영향 확인이 필요하면 dry_run으로
경로별 차이를 먼저 확인한다. readiness는 작업용, 테스트 시작은 운영용, 결과·cleanup 관측은 작업용이다.
테스트가 `succeeded`여도 cleanup이 남았으면 `next_action=wait`이고, 현재 설정과 다르면 `review_configuration`이다.

배포 후 도구 discovery를 갱신해야 한다. `catalogs.list`·`connectors.list` 호출은 options로 옮기고,
enroll의 implemented, resume의 expected_revision, GitHub 연결 create의 auto_merge를 명시한다.
REST 입력은 기존 기본값을 유지하며 DB migration은 없다. 상세 계약은 [MCP 안내](mcp.md)에 있다.

## 검증 범위와 한계

도구 목록 13+4와 중복·제거된 이름의 호출 거부, endpoint·scope 격리, 키 폐기·만료·machine 비활성화,
REST·scheduler 우회 거부, credential 비노출, 옵션의 독립 pagination·필터를 검사한다.
미리보기의 미저장·목록 교체·연결 해제·잘못된 connector 거부, 미리보기 후 동시 변경 충돌,
필수 입력 누락, 오래된 run revision 거부, 테스트 request replay·최근 30개 필터·paging·오래된 ID 조회를 검증한다.
기존 프로젝트·실행·연결 테스트의 도메인 회귀 테스트를 포함해 **244개 테스트가 통과**했다.
전체 `just lint`·`just check`도 통과했고, 문서 링크와 `git diff --check`를 확인했다.
실제 GitHub/Cloud Run 호출 및 모델의 도구 선택 품질은 이 테스트가 증명하지 않는다.
