# 코드 위생 점검 및 개선 — 2026-09-21

## 현재 판단

`modules/hub` / `modules/hub-ui` 구분, 기능별 디렉터리, 얇은 SvelteKit route 구성은 유지한다. 전체 디렉터리 재편보다 기능 내부의 책임 분리와 실패 경로 보완이 효과적이다.

주요 실행·API·화면 경로, 정적 import 관계, 단독 참조 심볼, CI와 검증 명령을 점검했다. 모든 실행 경로의 수동 검증이나 커버리지 측정 결과는 아니다. 변경은 작업 트리에 있으며 배포하지 않았다.

## 반영한 기능 수정

| 문제 | 변경과 검증 |
| --- | --- |
| 대시보드 상태별 통계가 최근 실행 50개, 활성 커넥터 집계가 첫 100개에 한정 | 인증된 `GET /api/v1/dashboard/stats`에서 전체 DB 집계. 하나의 SQL 문으로 같은 시점의 카운터를 읽는다. 화면에는 최근 활동 5개만 가져오며 전체 통계와 분리한다. 51개 실행·102개 커넥터·101개 스케줄 테스트를 추가했다. |
| 프로젝트·실행 목록에서 첫 페이지 밖의 데이터가 검색되지 않음 | 두 API에 서버 `search`, 실행 API에 `state` 필터 추가. 검색은 대소문자를 무시하고 `%`, `_`는 와일드카드가 아닌 문자로 취급한다. 검색·필터가 페이지 제한보다 먼저 적용되며 `total_count`도 같은 조건으로 계산한다. UI에 이전/다음 페이지, 필터 변경 시 첫 페이지 복귀를 구현했다. |
| 선택 목록이 첫 페이지에서 잘림 | 프로젝트·커넥터 선택지는 `allPages`로 끝까지 읽는다. 페이지 중간 실패를 부분 성공으로 처리하지 않는다. 총합이 없는 페이지 형식도 지원한다. |
| 느린 이전 검색이 새 검색 결과를 덮어씀 | `PaginatedState`가 최신 요청의 성공·실패만 반영한다. 마지막 페이지의 마지막 항목 삭제 시 남은 마지막 페이지로 돌아간다. 지연 응답·지연 실패·삭제 경계 테스트를 추가했다. |
| HTTP 실패가 빈 목록처럼 보임 | 프로젝트, 실행, 설정, 작업, 알림, AI 카탈로그, agent schedule 목록에서 HTTP 오류를 확인하고 빈 목록과 구별되는 재시도 상태를 표시한다. 대시보드 통계를 읽지 못하면 숫자 0 대신 `—`와 오류 안내를 표시한다. |
| 변경 요청의 네트워크 예외가 처리되지 않음 | 알림·카탈로그·agent schedule 변경에서 실패를 안내하고 입력 및 저장 버튼 상태를 유지한다. 연결된 실행을 여는 요청의 네트워크 오류도 처리한다. |
| 422 오류 배열을 문자열로 단정 | `apiErrorMessage`에서 문자열·필드 메시지 배열·비정상 응답을 구분한다. 제출한 입력값 전체는 메시지에 포함하지 않는다. |
| 네트워크 실패 후 요청 복제본이 남음 | API middleware의 `onError`에서도 재시도 보관 Map을 정리한다. 실패·취소 전파와 후속 요청 복구를 검증했다. 메모리 사용량 자체를 계측한 테스트는 아니다. |
| 로그아웃·재로그인 중 오래된 refresh/401 응답이 세션을 변경 | 세션 세대별로 갱신을 공유한다. 이전 세션의 응답은 현재 토큰을 덮어쓰거나 로그아웃시키지 않는다. 이미 갱신된 토큰이 있으면 지연 401은 이를 사용해 한 번 재시도한다. 경쟁 상황 회귀 테스트를 추가했다. |
| `blocked` 색상이 화면마다 다름 | 상태 표시를 `pipeline-runs/presentation.ts`로 공통화했다. |

## 반영한 구조 정리

- **읽기와 실행 분리**: `pipeline_runs/usecases/queries.py`에 실행·시도·전달·응답 조회를 모았다. 조회 API는 실행 adapter와 lifecycle 전체를 DI로 구성하지 않는다.
- **요청 identity 생성 분리**: `pipeline_runs/requests.py`에서 immutable request 생성과 canonical SHA-256 digest를 관리한다. 최초 요청·CI 수정·충돌 수정·재개가 같은 digest 함수를 사용한다. key 재사용과 snapshot 변경을 테스트했다.
- **순환 의존성 제거**: `ProjectError`를 `projects/errors.py`, adapter 지원 정보를 `adapters/capabilities.py`로 분리했다. 지원 여부 조회는 구현 adapter·DB·관찰 서비스를 import하지 않는다. 지연 import를 포함한 앱 내부 정적 import 분석에서 순환 연결이 더 이상 발견되지 않았다. 지원 정보와 실제 registry의 일치도 테스트한다.
- **프로젝트 설정 분리**: 설정 폼 상태·저장·다이얼로그를 `ProjectSettingsDialog.svelte`로 이동했다. 목록 화면은 1,292행에서 903행으로 줄었고, 기존 revision·automation 보존과 422 오류 테스트가 통과한다.
- **대시보드 상태 분리**: API 로딩·집계 표시·실패 상태는 `dashboard.svelte.ts`, 화면과 새로고침 타이머는 `DashboardView.svelte`가 담당한다.
- **공통 목록 동작**: pagination 상태와 `ListPagination`, `LoadError`를 재사용한다. `utils.ts` 하나에 기능별 로직을 모으지 않았다.

## 미사용 코드와 의존성

- 호출·생성이 없던 프론트엔드 `ApiError`를 삭제했다.
- 앱에서 사용하지 않던 `sveltekit-superforms`, `zod` 직접 의존성을 제거하고 npm lockfile과 UI README를 갱신했다. 다른 패키지의 전이 의존성으로 남는 항목은 별개다. 기존 패키지 버전은 올리지 않았다.
- Python 단독 참조 심볼 중 route, validator, event listener, 등록된 task, 공용 라이브러리 hook은 유지했다. `tasks/examples.py`, calendar fake와 등록용 `__init__.py`도 정상 사용 경로가 있다.
- 백엔드 `cachetools`, `dotenv`는 직접 사용이 없더라도 공용 라이브러리의 설치 계약을 추가 확인해야 해서 유지했다. `python-multipart`는 로그인 form 처리에 필요하다.
- `[tool.rye.workspace]`와 테스트의 평면 디렉터리 이름은 기능상 결함이 아니므로 변경하지 않았다.

## 후속 모듈 분리

- **프로젝트 화면**: 연결 점검과 빠른 스케줄 생성의 상태·API 호출·마크업을 `ProjectConnectionCheckDialog.svelte`, `ProjectScheduleDialog.svelte`로 분리했다. `ProjectsView.svelte`는 903행에서 449행이 됐다.
- **실행 화면**: 시도 이력, PR 등록, PR 연결을 `AttemptHistoryDialog.svelte`, `EnrollPullRequestDialog.svelte`, `AttachPullRequestDialog.svelte`로 분리했다. `PipelineRunsView.svelte`는 1,018행에서 583행이 됐다. 목록의 필터·페이지·선택과 `?run=` 링크 해석은 부모 화면에 남겼다. 다이얼로그를 닫으면 해당 입력·이력 확장 상태를 폐기한다.
- **스케줄 편집**: 생성·수정은 명시적인 `create`/`edit` 모드의 `ScheduleEditorDialog.svelte`를 공유한다. 입력 초깃값과 요청 변환은 같은 기능 폴더의 `schedule-form.ts`에 모았다. `ScheduleConfigsView.svelte`는 764행에서 398행이 됐다. 수정 시 task 읽기 전용, payload 복사·보존, 이전 trigger를 지우는 명시적 null, 서버의 관리 스케줄 수정 거부를 유지한다.
- **관찰 결과 저장**: `observe_and_save`와 `observe_project_and_save`는 `ObservePipelineUseCase`로 이동했다. 외부 관찰 이후 설정·revision을 재검증하고 저장하는 트랜잭션을 유스케이스가 소유한다. 스케줄 task도 새 진입점을 호출한다.
- **실행 수명주기**: `lifecycle.py`는 1,180행에서 352행이 됐다. 기존 공개 메서드와 DI 생성자는 유지하며, 구체적인 책임을 아래 모듈에 위임한다. 부모 객체나 mixin에 의존하지 않고 필요한 repository/service를 명시적으로 전달한다.

| 모듈 | 책임과 트랜잭션 소유권 |
| --- | --- |
| `leases.py` | lease 획득·갱신·해제의 짧은 트랜잭션과 충돌 판정 |
| `catalogs.py` | 명시적 지정·프로젝트 기본값·재개 시 카탈로그 선택. 호출자의 session 사용 |
| `delivery.py` | 전달 준비·admission → 트랜잭션 밖 외부 호출 → lease/attempt/delivery 재검증·저장. 전달 직전 추가 검증과 타임아웃 후 reconciliation 유지 |
| `control.py` | 일시정지·재개·취소·PR 연결·외부 시도 결과 기록. 재개의 외부 조회 전후 트랜잭션과 revision 검증 유지 |
| `progress.py` | 실행 진행의 준비 → 외부 관찰 → 재검증·반영. 짧은 트랜잭션과 lease·revision·attempt 검증 소유 |
| `implementation.py` | 구현 결과·head 변경·쿼터 응답·무응답 재시도. DB 준비·반영과 외부 조회를 분리 |
| `ci.py` | CI 조회·로그·병합은 트랜잭션 밖에서 수행하고, 결과 반영은 `progress.py`가 제공하는 session 사용 |
| `transitions.py` | PR 종료·프로젝트 변경 차단·GitHub 대기 등 공유 상태 변경. 별도 트랜잭션을 열지 않음 |

후속 회귀 테스트는 스케줄 방식 양방향 전환·payload 보존·수정 거부 후 입력 유지, 빠른 스케줄 요청과 재열기 초기화, PR 연결 후 새로고침, 실행 이력 재조회·확장 상태 초기화, 관찰 도중 설정 변경 시 저장 거부를 검증한다. 기존 전달 중단·타임아웃·lease·revision 경합 테스트의 검증 내용은 유지하고 내부 patch 경로만 새 소유 모듈로 옮겼다. 분리 후 앱의 181개 Python 모듈을 정적으로 분석했으며 지연 import를 포함해 순환 의존성은 발견하지 못했다.

## 후속 개선 1·2·3 반영

1. **실행 관찰의 트랜잭션 분리**: `progress.py`가 짧은 트랜잭션에서 입력과 실행 버전을 확보하고, GitHub PR·응답·CI·실패 로그 조회와 병합을 트랜잭션 밖에서 수행한다. 병합 직전과 최종 반영 직전에 lease 소유자·토큰·유효기간, 실행 revision·상태, 프로젝트 revision·활성 여부, 활성 attempt·delivery 정보를 재검증한다. 관찰 I/O는 90초로 제한하고 lease는 최소 120초로 연장한다. 일시정지·취소·PR 연결도 실행 행 잠금을 사용한다.
2. **읽기 트랜잭션 소유권 정리**: `ReadConnectorTokenUseCase`가 커넥터 자격 증명 조회를 소유하며 복호화는 트랜잭션 밖에서 수행한다. 관찰 서비스에는 토큰 조회 함수를 주입한다. 저장된 보고서 조회는 `GetPipelineObservationUseCase`가 하나의 읽기 트랜잭션에서 설정과 결과를 확인하며, 자격 증명 의존성을 구성하지 않는다. 기존 `PipelineObservationQueryService`와 중복 커넥터 조회 메서드는 제거했다.
3. **스케줄 목록 확장**: 설정·작업 화면에 공통 페이지 상태·페이지 이동·오류 재시도를 적용했다. 기존 offset/limit·총 개수·상태 필터 API에 대소문자 구분 없는 `search`를 추가했다. 설정은 이름·task 함수, 작업은 이름·상태를 검색하며 `%`·`_`는 문자 그대로 처리한다. 검색·필터 변경 시 첫 페이지로 이동하고 마지막 행 삭제 시 유효한 페이지로 복귀한다. OpenAPI 클라이언트도 갱신했다.

관찰 중 일시정지·취소·프로젝트 수정·lease 재획득·attempt 완료·delivery 변경·타임아웃을 회귀 테스트로 검증한다. 병합 전 재관찰 도중 취소되면 병합 요청을 보내지 않는다. 이미 GitHub로 전송된 병합은 취소로 되돌릴 수 없으며, 그 사이 로컬 상태가 변경되면 병합 결과가 해당 최신 상태를 덮어쓰지 않도록 거부한다. 이 외부 시스템 간 원자성 한계도 테스트로 명시했다.

테스트 DB 생성 전에 라우터의 모델을 등록하도록 테스트 초기화를 보완했다. 일부 스케줄 테스트만 독립 실행해도 프로젝트 관리 스케줄 테이블이 누락되지 않는다.

## 이전 점검 검증

- SQLite 전체 테스트: **530개 통과**.
- PostgreSQL 전체 테스트: **530개 통과**. 로컬 Docker의 임시 테스트 DB를 사용했다.
- 프론트엔드 전체 테스트: **19개 파일, 90개 통과**. 의존성 정리 후에도 통과했다.
- `just lint` 통과: Python format/lint/architecture와 frontend format/ESLint.
- `just check` 통과: Python 타입 검사, Svelte 검사, 프로덕션 빌드.
- `just gen-ui-api` 통과: 집계 응답과 필터를 포함한 typed client 갱신. `git diff --check`도 통과.
- 실제 GitHub/Jules/Telegram API 호출과 배포, migration 왕복 검증은 수행하지 않았다. 이번 변경에는 DB schema migration이 없다.

## 후속 분리 검증

- `just test`: SQLite 전체 **532개 통과**.
- `just test-pg`: PostgreSQL 전체 **532개 통과**. Docker 소켓의 샌드박스 접근 제한을 확인한 뒤 승인된 실행으로 로컬 임시 테스트 DB에서 검증했다.
- `just test-ui`: **19개 파일, 96개 통과**.
- `just lint`: Python format/lint/architecture와 frontend format/ESLint 통과.
- `just check`: Python·Svelte 타입 검사와 프로덕션 빌드 통과.
- `git diff --check` 통과. API 계약과 DB 스키마를 변경하지 않았으며 migration은 없다.
- 실제 GitHub/Jules/Telegram 호출과 배포는 수행하지 않았다.

## 후속 개선 1·2·3 검증

- `just test`: SQLite 전체 **546개 통과**.
- `just test-pg`: PostgreSQL 전체 **546개 통과**. 로컬 Docker의 임시 테스트 DB에서 실제 행 잠금과 경합을 검증했다.
- `just test-ui`: **19개 파일, 99개 통과**.
- 스케줄 설정·작업 API와 dispatcher·webhook 테스트를 별도 선택해서 실행해도 통과한다.
- `just lint`: Python format/lint/architecture 및 frontend format/ESLint 통과.
- `just check`: Python·Svelte 타입 검사와 프로덕션 빌드 통과.
- `just gen-ui-api`, `git diff --check` 통과. 목록 검색 query를 추가했으며 DB 스키마 변경이나 migration은 없다.
- GitHub HTTP는 mock으로 검증했으며 실제 외부 API 호출과 배포는 수행하지 않았다.
