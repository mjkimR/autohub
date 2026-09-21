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

## 남은 구조 개선 후보

1. `lifecycle.py`는 조회·요청 생성을 분리했어도 1,180행이다. CI/merge 전이와 delivery orchestration의 추가 분리는 transaction·lease·revision 재검증을 함께 다루는 별도 변경이 적합하다. 이번 변경은 해당 소유권을 유지한다.
2. 프로젝트 연결 검사·빠른 스케줄, 실행 등록·PR 연결·시도 상세, 스케줄 편집 폼은 추가 컴포넌트 분리 대상이다. 프로젝트 설정과 대시보드 분리 패턴을 이어 적용할 수 있다.
3. `PipelineObservationService`의 조회·저장 transaction과 usecase 경계를 추가 정리할 수 있다. lint 통과가 transaction 설계 전체의 적절성을 증명하지는 않는다.
4. 스케줄 작업·설정 등 기존 다른 목록의 페이지 처리도 프로젝트·실행 화면 패턴으로 확장할 수 있다. 이번 서버 검색·페이지 UI의 범위는 프로젝트와 실행 목록이다.

## 검증

- SQLite 전체 테스트: **530개 통과**.
- PostgreSQL 전체 테스트: **530개 통과**. 로컬 Docker의 임시 테스트 DB를 사용했다.
- 프론트엔드 전체 테스트: **19개 파일, 90개 통과**. 의존성 정리 후에도 통과했다.
- `just lint` 통과: Python format/lint/architecture와 frontend format/ESLint.
- `just check` 통과: Python 타입 검사, Svelte 검사, 프로덕션 빌드.
- `just gen-ui-api` 통과: 집계 응답과 필터를 포함한 typed client 갱신. `git diff --check`도 통과.
- 실제 GitHub/Jules/Telegram API 호출과 배포, migration 왕복 검증은 수행하지 않았다. 이번 변경에는 DB schema migration이 없다.
