# AutoHub 제공 방식 재검토

최초 검토일: 2026-09-22. 갱신일: 2026-09-23. 대상은 이미 운영 중인 AutoHub에 사용자의 다른 저장소를
연결하고 Claude Code, Codex, Antigravity에서 이용하는 경우다.
아래 도구 이름과 배포 구조는 제안이다. 이번 갱신에서는 app-common의 `app-mcp` 코드와
로컬 MCP 호출을 검증했다. 후속 구현 상태는 아래에 별도로 기록한다.

## 후속 구현 상태 — 2026-09-23

이 검토를 바탕으로 공통 `app-mcp`의 스키마·오류 전달을 보완하고 AutoHub에
인증된 `/mcp/`와 공개 도구 17개를 로컬 구현했다. 프로젝트 연결·수정·조회,
catalog/connector 조회, 준비 상태 확인, 연결 테스트 시작·조회·취소,
기존 PR 등록과 실행 조회·이력·제어를 기존 UseCase에 연결했다.
skill·CLI·plugin이나 별도 서버는 추가하지 않았다.

공통 패키지 테스트 10개, AutoHub 전체 테스트 765개(6개 제외), 린트·타입 검사·UI 빌드를
통과했다. 공통 변경은 최초 `app-tools dev link`로 검증한 뒤, 공개 커밋
`e4b8d1dee7c2b79e0bcb4ac246802eafc13c77ca`로 Python/APM 참조와 lock을 갱신했다.
공개 커밋에서 설치한 패키지로 전체 테스트·린트·타입 검사·UI 빌드를 다시 통과했고,
APM audit 및 Python/APM SHA 일치도 확인했다. 실제 운영 배포나
Codex 등 개발 클라이언트의 연결 실측은 아직 하지 않았다.
[연결 안내](mcp.md),
[AutoHub 구현 상태](delivery-status.md)를 참고한다.

아래 코드 판정과 문제 표는 보완 전 검토 기록이다. 스키마·출력 계약·오류 플래그·예시를
공통 패키지에서 수정했고, 인증·의존성 구성·lifespan·stateless HTTP는 Hub에 연결했다.

### 자체 코드 리뷰와 간결성 검토

- 출력 모델의 alias가 공개 스키마와 실제 응답을 다르게 만드는 문제를 MCP 클라이언트로
  재현했다. 출력은 기존의 모델 필드명 계약으로 통일하고 회귀 테스트를 추가했다.
- 입력 validator의 예상 밖 예외가 공통 오류 처리 밖으로 빠지는 문제를 수정했다.
  입력 오류와 서버 오류를 구분하면서 내부 예외 내용은 노출하지 않는다.
- 실행 이력 페이지가 응답만 자르고 DB에서는 전체 이력을 읽던 부분을 수정했다.
  기존 조회에 offset/limit을 전달하고 전체 통계는 DB 집계로 유지한다.
- REST 인증이 MCP 전송 모듈을 import하던 의존성을 제거하고 machine scope를 기존
  인증 모듈에 모았다. 불필요한 `total_count or 0` fallback도 제거했다.

도구별 얇은 handler, 타입이 있는 입출력 모델, 명시적인 의존성 구성은 유지한다.
짧은 등록 helper는 scope/risk/결과 변환의 중복을 줄이므로 유효하다. 코드 줄 수를
줄이기 위한 자동 REST 변환·범용 action dispatcher·추가 DI 프레임워크는 도입하지 않는다.
공개 SHA 반영은 완료했으며, 실제 운영 클라이언트 검증은 남아 있다.

## 권고

**app-common의 `app-mcp`를 재사용해 기존 AutoHub에 원격 MCP부터 제공한다.
첫 제공물은 MCP와 짧은 연결 안내로 한정하고, skill·CLI·plugin은 실제 필요가 생긴 뒤 검토한다.**

- AutoHub 서버에 `/mcp`를 추가한다. REST와 MCP가 기존 UseCase를 공유한다.
  별도 서버 프로세스나 사용자 PC용 Python 패키지를 배포하지 않는다.
- 첫 단계에서 공개하는 사용자 작업은 MCP만으로 완료할 수 있게 한다.
  전체 사용자 기능의 공개는 후속 단계에서 넓힌다.
- skill 제작·설치·배포 흐름은 첫 단계에서 제외한다.
- 개인 사용에서는 클라이언트별 사용자 설정에 MCP를 한 번 연결한다.
  각 대상 저장소에 APM manifest, skill 사본, AutoHub 실행 환경을 추가하지 않는다.
- 대상 저장소에는 실제로 필요한 CI와 프로젝트 지침만 유지한다.
- 범용 CLI, 별도 MCP 서버 배포, 제품별 plugin 패키지는 첫 제공물에서 제외한다.
  반복되는 설치 불편이 확인되면 기존 MCP를 쉽게 연결하는 배포 수단으로 검토한다.

## 앞선 제안에 대한 자체 피드백

| 앞선 판단 | 재검토 결과 |
| --- | --- |
| 온보딩 skill을 APM으로 repo마다 배포 | 1회성 설정에 비해 지속 관리가 늘어난다. 기본 경로로 권하지 않는다. |
| skill을 설치하면 본문이 계속 컨텍스트를 차지 | 과도한 일반화다. 일반 세션에서는 메타데이터를 먼저 읽고 본문은 선택 시 로드하는 방식을 지원한다. 호출 후 본문이 대화에 남는 비용은 별개다. |
| MCP를 핵심 6~10개 도구로 제한 | 초기 예시로는 유용하지만 제품의 고정 제한으로 삼을 근거는 없다. 필요한 사용자 기능과 실제 스키마·결과 크기로 판단한다. |
| full spec MCP에 얇은 skill 추가 | MCP부터 제공한다. skill은 사용 중 반복되는 불편이 확인될 때 검토한다. full spec은 장기적인 사용자 기능 범위이며 첫 릴리스 조건이 아니다. |
| 서버가 있으므로 MCP는 얇게 붙이면 끝 | 실행 로직 재사용은 가능하지만 인증, 권한, 의존성 구성, 응답 계약과 클라이언트 호환성 작업이 남는다. |
| MCP가 있으면 repo 설정도 끝 | MCP 연결은 Hub 접근 수단이다. CI 구성과 AI provider의 저장소 설정은 별도이며 실제 연결 테스트가 필요하다. |

## 공식 문서에서 확인한 점

### 도구와 skill의 컨텍스트 비용

Claude Code의 현재 문서는 MCP 도구 정의의 지연 로딩을 기본 동작으로 설명한다.
처음에는 도구 이름과 서버 지침이 들어가며, proxy나 일부 배포 환경에는 예외가 있다.
따라서 서버 지침까지 긴 매뉴얼로 만들면 안 된다.
[Claude Code MCP](https://code.claude.com/docs/en/mcp#scale-with-mcp-tool-search)

Codex는 도구 allow/deny list와 도구별 출력 토큰 제한을 지원한다.
OpenAI API의 Tool Search는 지연 로딩을 지원하지만, API 기능을 근거로
모든 Codex 모델·클라이언트와 ChatGPT 웹의 기본 동작을 동일하다고 단정하지 않는다.
[Codex MCP](https://developers.openai.com/codex/mcp),
[OpenAI Tool Search](https://developers.openai.com/api/docs/guides/tools-tool-search)

Antigravity는 `disabledTools`를 제공한다. 조사한 MCP 문서에서 모든 도구 정의의
자동 지연 로딩을 보장하는 설명은 확인하지 못했다.
[Antigravity MCP](https://antigravity.google/docs/mcp)

세 개발 클라이언트 모두 skill의 점진적 로딩을 문서화하고 있다.
Claude Code의 일반 세션은 설명을 먼저 로드하고 호출 시 본문을 로드한다.
Codex는 이름·설명, 본문, 참조 자료 순으로 필요에 따라 읽는다.
Antigravity도 discovery → activation → execution으로 설명한다.
따라서 얇은 선택형 skill을 배제할 이유는 컨텍스트 자체보다 필요성과 관리 부담이다.
[Claude skills](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill),
[OpenAI customization](https://learn.chatgpt.com/docs/customization/overview#skills),
[Antigravity skills](https://antigravity.google/docs/skills)

### 전송과 배포

원격 MCP에는 Streamable HTTP를 사용한다. MCP protocol revision과 SDK 구현은
변하므로, 구현 시 지원 버전을 고정하고 실제 클라이언트 버전과 대조한다.
공식 Python SDK 저장소에는 ASGI와 구형·신형 HTTP 클라이언트를 함께 다루는 예제가
있다. 저장소 `main` 예제가 현재 설치 가능한 안정 릴리스와 같다고 가정하지 않는다.
[MCP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http),
[Python SDK 예제](https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/stories/stateless_legacy/README.md)

MCP prompts는 사용자가 선택하는 재사용 프롬프트이고 tools는 모델이 호출하는 기능이다.
자동 작업 순서를 prompts만으로 제공하는 것은 skill과 같은 사용 경험을 보장하지 않는다.
가이드는 문서로 유지하고, tools로도 조회할 수 있게 하면 기본 사용 흐름의 호환성을
확보하기 쉽다. resources/prompts는 지원 클라이언트용 편의 기능으로 추가할 수 있다.
[MCP prompts](https://modelcontextprotocol.io/specification/2025-11-25/server/prompts),
[MCP tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)

## 현재 코드에서 발견한 설계상 요점

검토 위치는 workbench의 독립 자식 저장소 `repos/autohub`다.

| 근거 파일 | 발견과 의미 |
| --- | --- |
| `modules/hub/app/auth.py`, `router.py` | 일반 API는 사용자 로그인, machine key는 `autohub:dispatch` 전용이다. 현재 scheduler key를 MCP 사용자 키로 재사용할 수 없다. |
| `features/project_management/projects/models.py` | 저장소 연결은 unique지만 프로젝트별 접근 권한 모델은 이 모델에 없다. repo별 MCP 권한을 약속하려면 별도 구현해야 한다. |
| `features/project_management/projects/usecases/crud.py` | 기존 UseCase를 공유할 수 있다. 생성 중복은 충돌로 처리하며, 재시도 시 기존 프로젝트를 반환하는 온보딩 계약은 별도 설계가 필요하다. |
| `features/project_management/projects/services.py` | 업데이트에 revision 검사가 있다. MCP에서 이를 보존하고 충돌을 명확하게 전달해야 한다. |
| `features/project_management/pipeline_runs/api/v1.py` | pause/resume/cancel 외에 lease, implementation attempt, worker callback이 함께 있다. REST 전체 자동 변환은 내부 실행 제어까지 노출한다. |
| `features/project_management/pipeline_runs/schemas.py` | run 응답에 PR 본문·연결 issue snapshot이, attempt 응답에 request snapshot이 포함된다. 기본 MCP 조회에는 별도 요약 응답이 적절하다. |
| `features/project_management/connection_tests/api.py` | 시작·조회·진행·취소 기능을 재사용할 수 있다. 시작은 request ID를 받는다. 기존 중복 실행 방지를 MCP 경로에서도 유지한다. |
| `features/project_management/projects/usecases/onboarding.py` | 기존 check는 PR 번호를 필요로 하며 최대 75초를 사용한다. 일반적인 repo 사전 진단 도구와 동일하지 않다. Codex의 문서상 기본 도구 timeout 60초와도 조율이 필요하다. |
| `features/project_management/agent_schedules/api/v1.py` | 프로젝트별 반복 작업과 run-now가 있다. PR만 다루는 MCP는 AutoHub의 사용자 기능 전체를 대표하지 못한다. |

UseCase 생성자는 FastAPI `Depends`를 사용한다. MCP handler가 함수를 직접 호출한다고
HTTP dependency injection이나 라우터 인증이 자동 적용되지는 않는다.
공통 의존성 구성과 인증된 호출자 전달 경계를 명시하고, 기존 비즈니스 로직을 재사용한다.

## app-common FastMCP 패키지 재사용 검토

**판정: `app-mcp`를 기반으로 진행할 수 있다. 다만 현재 상태를 그대로 운영에 붙이는
완제품으로 보기는 어렵고, 아래 전송 경계 보완을 먼저 해야 한다.** 새 MCP 프레임워크를
AutoHub 안에 만드는 것보다 공통 패키지를 보완하고 Hub에는 업무 도구만 두는 편이 단순하다.

검토 기준은 app-common `0487069f96f6b831ee6301113aa60cb8443a79f5`의
`packages/transports/app-mcp`다. AutoHub가 현재 의존하는 app-common SHA
`ca4e6a4fdca035314c4e032ca9397e633830ecf5`에도 이 패키지가 있으며,
두 SHA 사이 해당 패키지의 소스와 `pyproject.toml` 차이는 없다.
AutoHub의 `modules/hub/pyproject.toml`에는 아직 `app-mcp` 의존성이 없다.

### 이미 제공하는 부분

| 근거 | 재사용할 기능 | 앱에서 맡을 부분 |
| --- | --- | --- |
| `src/app_mcp/server.py` | `create_mcp`, `create_http_app`으로 FastMCP 등록과 ASGI 앱 생성 | Hub에 마운트하고 기존 lifespan과 결합 |
| `registry.py`, `context.py` | 입력 모델 검증, scope 검사, 인증된 `ToolContext` 계약 | 자격 증명 검증, 호출자 구성, 필요한 업무 권한 검사 |
| `result.py` | `AppError`를 구조화하고 예상 밖 예외의 내부 정보를 숨김 | Hub 오류 의미와 클라이언트에 전달할 결과 계약 |
| `policy.py`, `registry.py` | 확인·멱등성 키의 존재 검사, 선택형 audit hook | 확인의 신뢰 근거, 실제 중복 방지 저장, 감사 기록 저장 |

확인과 멱등성 정책은 기본값에서 비활성이다. 모든 도구에 새로운 승인 절차를 붙일 필요는
없다. 기존 업무 정책에 필요한 경우만 사용한다. 키 존재 검사만으로 중복 실행이 방지되지는 않는다.

### 통합 전에 보완할 점

| 우선순위 | 확인한 문제 | 처리 방향 |
| --- | --- | --- |
| 필수 | `_tool_signature()`가 필드의 타입과 기본값만 옮긴다. `Field(description=..., ge=1, le=100)`의 설명·범위가 실제 `tools/list`에서 빠졌다. | Pydantic 필드 메타데이터를 보존하고 기본값·필수값·alias도 전송 경계에서 검증한다. Registry의 런타임 검증은 유지한다. |
| 필수 | `ToolResult.is_error`를 본문의 `ok=false`로만 변환한다. 입력 오류·권한 거부도 MCP 결과의 오류 플래그는 false였다. | 구조화된 오류 내용을 유지하면서 MCP의 `isError`에도 실패를 반영한다. |
| 필수 | 인증은 `context_provider` 콜백 자리만 있다. `create_mcp()` 자체에는 인증 구현이 없다. scope 검사는 호출 시 적용되고 도구 목록은 전체 등록된다. | HTTP 경계에서 인증하고 신뢰할 수 있는 호출자를 전달한다. 첫 단계는 개인 운영자용 공개 도구만 등록한다. 사용자별 목록 필터가 필요해지면 별도 보완한다. |
| 통합 시 | `output_model`은 Registry에서만 검증한다. 실제 공개 출력 스키마는 일반 객체이며 risk annotation도 전달되지 않는다. | 실제 `{ok, result, error}` 응답에 맞는 출력 계약을 노출하고 조회·변경 annotation을 연결한다. |
| 통합 시 | HTTP helper는 `path`만 받는다. Hub에는 기존 lifespan, timeout middleware, SPA catch-all이 있다. | 기존 초기화·정리를 보존하며 MCP lifespan을 결합하고 SPA보다 먼저 마운트한다. 장기 연결과 재연결도 검증한다. |
| 정리 | README와 consumer MCP 가이드 예시는 현 `ToolDefinition`의 필수 `input_model` 인자와 맞지 않는다. | 예시를 현재 모델 기반 계약에 맞춘다. README의 위치 인자를 그대로 복사하지 않는다. |

스키마와 오류 전달 보완은 공통 `app-mcp`의 전송 경계에서 처리한다. 업무별 도구와 인증 연결은
AutoHub에 둔다. 임시 wrapper를 Hub에 중첩해 같은 문제를 우회하는 구조는 만들지 않는다.

HTTP 경로는 `create_http_app(mcp, path="/")`를 `app.mount("/mcp", ...)`에 붙이는 식으로
한 번만 조합한다. 기본 내부 경로 `/mcp`를 다시 `/mcp` 아래에 마운트하면 경로가 겹친다.
기존 Hub lifespan을 MCP lifespan으로 대체하지 않는다. FastMCP 공식 문서도 마운트 시
lifespan 전달과 기존 lifespan 결합을 안내한다.
[FastMCP FastAPI 통합](https://gofastmcp.com/integrations/fastapi#combining-lifespans)

Cloud Run에서 세션이 다른 인스턴스로 이어질 수 있으므로 첫 제공은 stateless HTTP를
우선 검증한다. 현재 helper는 해당 인자를 노출하지 않지만 반환된 FastMCP의
`http_app(stateless_http=True, path="/")`는 로컬 설치 버전에서 지원한다.
설정 하나 때문에 별도 전송 계층을 만들지 말고 이 API를 쓰거나 공통 helper에 옵션을 추가한다.

### 의존성과 검증 결과

- 패키지는 Python `>=3.12`, Hub는 `>=3.13`이므로 선언상 Python 버전 충돌은 없다.
- `app-mcp` 선언은 `fastmcp>=2.0`으로 넓다. 이번 로컬 환경은 FastMCP `4.0.3`,
  MCP SDK `2.2.0`, Pydantic `2.13.5`였다. 모든 허용 버전의 호환성을 검증한 것은 아니다.
- `repos/app-common`에서 `.venv/bin/python -m pytest packages/transports/app-mcp/tests -q`:
  **5 passed**. 기존 테스트의 전송 검증은 앱 생성까지다.
- 추가로 `fastmcp.Client(mcp)`를 사용한 인메모리 `tools/list`, `tools/call`에서
  정상 반환, scope 거부, 잘못된 입력 처리를 확인했다. 이 과정에서 위 스키마 누락과
  오류 플래그 문제를 재현했다. HTTP 인증·Hub DB·실제 개발 클라이언트는 검증하지 않았다.
- 소비 시 `app-mcp`를 다른 app-common 패키지와 동일한 pushed Git SHA 및
  `packages/transports/app-mcp` subdirectory로 추가하고 Hub lockfile을 갱신한다.
  공통 보완을 채택할 때 해당 SHA를 명시적으로 갱신한다. sibling 경로 의존성은 넣지 않는다.

## MCP의 공개 범위

full spec은 **외부 사용자가 수행할 수 있는 AutoHub 작업의 명시적 계약**으로 정의한다.
MCP의 모든 선택 기능 구현이나 REST의 모든 endpoint 복제까지 포함하지 않는다.
아래 표는 후속 확장을 포함한 목표 범위이며, 첫 제공 범위는 뒤의 1차 계획을 따른다.

| 기능군 | 제공 방향 |
| --- | --- |
| 안내·기능 조회 | 지원 기능, 배포 버전, 온보딩·작업·문제 조사 가이드와 CI 템플릿 조회 |
| 프로젝트 | 저장소로 찾기, 생성·연결·설정 조회와 갱신, 준비 상태 진단 |
| 연결 테스트 | 시작·상태·취소·정리 상태 조회 |
| PR 실행 | 기존 PR 등록, 실행 목록·상태·진단·이력 조회, pause/resume/cancel |
| Catalog·세션 | 사용 가능한 catalog·용량·provider capability 조회, 결과·report 조회 |
| 반복 작업 | 프로젝트별 agent schedule 조회·생성·수정·삭제·다음 tick 실행 요청 |
| 관리 작업 | 공유 catalog 정책 변경, 프로젝트 삭제, 정리 수동 해결 등은 명시적인 관리 권한으로 분리 |
| 내부 실행 프로토콜 | lease, worker completion callback, attempt 생성 등은 일반 사용자 MCP 범위에서 제외 |

자격 증명 원문 입력·회수·키 발급은 초기에는 기존 관리 화면에서 처리한다.
MCP는 사용할 수 있는 연결의 이름·ID·준비 상태를 제공한다.
서버가 모든 공개 기능을 구현하더라도 호출자의 권한에 따라 노출·실행 범위를 제한한다.
skill에 적힌 제한이나 도구 annotation을 서버 권한 검사 대신 사용하지 않는다.

도구 수를 줄이려고 `execute(action, payload)` 하나로 모든 작업을 합치지 않는다.
조회와 변경의 권한, 입력 검증, 오류 의미를 분리할 수 있는 작업 단위를 유지한다.
공유되는 목록 필터·페이지 처리·결과 형식은 통일한다.

## 최초 연결 안내와 후속 skill 판단

첫 제공물에는 MCP URL, 자격 증명 준비·등록, 연결 확인, 대표적인 조회·등록 예시를 담은
짧은 문서만 둔다. 우선 실제 사용하는 클라이언트 하나에서 흐름을 검증하고 다른 클라이언트의
연결 예시를 추가한다. 세 클라이언트의 동시 지원을 첫 검증의 선행 조건으로 삼지 않는다.
MCP 설정이나 인증 정보가 클라이언트 사이에 자동 공유된다고 가정하지 않는다.

상세 인자와 결과는 MCP 스키마에 담는다. 초기 안내를 위해 별도 문서 조회 시스템,
resources/prompts 묶음, APM 배포 흐름을 만들지는 않는다. 실제 업무 도구의 설명만으로
부족한 안내가 확인되면 같은 원본 문서를 조회하는 기능을 추가한다.

현재 PR 등록은 기존 PR을 받는다. PR 생성은 로컬/GitHub 도구나 기존 사용자 흐름에서
처리하며, MCP v1이 범용 PR 생성 기능까지 갖춘 것으로 표현하지 않는다.
Draft → Ready 승인은 기존 사용자 정책을 유지한다.

skill은 반복 설명이나 잘못된 도구 선택이 실제로 관찰될 때 검토한다. 도입하더라도
MCP를 선택적으로 안내하는 역할이며 서버 권한, API 인자, 재시도 로직을 복제하지 않는다.

## 인증과 운영 방식

개인용 첫 검증은 세 개발 클라이언트가 지원하는 HTTP Bearer/header 연결을 활용할 수
있다. 다만 MCP용 자격 증명과 scope를 구분해야 한다. 기존 `app-prebuilt-auth`의 API key
모델에는 이미 scope, 만료, 폐기 필드가 있으므로 이 경로의 확장을 우선 검토한다.
새 토큰 저장소·발급 시스템부터 만들지는 않는다. Hub의 `MACHINE_SCOPES`는 현재
`autohub:dispatch`뿐이므로 MCP scope를 명시적으로 추가하고 검증 경계를 연결해야 한다.
GitHub PAT나 root key를 에이전트의 AutoHub 인증 수단으로 사용하지 않는다.
이 방식은 수동 토큰 연결이며 표준 OAuth 자동 연결을 구현한 것과 구별한다.
[Claude HTTP 연결](https://code.claude.com/docs/en/mcp#option-1-add-a-remote-http-server),
[Codex MCP](https://developers.openai.com/codex/mcp),
[Antigravity MCP](https://antigravity.google/docs/mcp)

ChatGPT 웹까지 동일한 로그인 경험으로 제공하는 것을 첫 릴리스 조건으로 잡으면,
OAuth 2.1과 discovery metadata를 처음부터 포함한다. 현재 Hub의 사용자 로그인 API가
그 자체로 MCP OAuth authorization server가 되는 것은 아니다.
개인 개발 클라이언트 우선 검증 후 OAuth를 추가하는 순서를 권고한다.
[OpenAI 인증](https://developers.openai.com/plugins/build/auth),
[MCP 인증](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

작업 상태는 기존 DB와 scheduler에 남긴다. MCP 연결 종료를 업무 취소로 취급하지 않고,
취소는 별도 도구로 요청한다. 오래 걸리는 작업은 ID를 반환하고 상태를 다시 조회한다.
MCP 메모리 세션을 workflow 저장소로 쓰지 않는다.

클라이언트 재시도와 연결 유실에서도 중복 PR 테스트나 agent 요청이 생기지 않도록
mutation의 request ID·revision·결과 재조회 규약을 정한다. 기존에 보장되는 부분과
MCP를 위해 추가할 부분을 구분해서 검증한다.

## 제공 순서와 검증 기준

### 1차: 실제 다른 repo 도입

- 원격 MCP와 토큰 연결, 사용자 기능별 공개 도구 계약을 만든다.
- 프로젝트 연결·진단, catalog 선택 정보, 실제 연결 테스트, PR 등록·조회·제어를 구현한다.
- 실제 사용하는 클라이언트 하나의 연결 안내와 짧은 온보딩 문서를 제공한다.
- skill 없이 실제 다른 repo의 기존 PR 등록 → 상태 조회 → 결과 확인을 끝까지 검증한다.
- 연결·인증·조회부터 붙여 공통 경계를 확인한 뒤 변경 도구를 추가한다.
- 이 시점에는 반복 작업·관리 영역까지 full spec 구현 완료라고 표시하지 않는다.

### 2차: 사용자 기능 범위 완성

- 세션/report·반복 작업과 필요한 관리 도구를 추가한다.
- 나머지 개발 클라이언트 연결을 검증하고, 필요가 확인된 경우에만 OAuth·skill·plugin을 검토한다.
- 기존 CI 재사용 사례가 쌓인 뒤 공용 reusable workflow 제공 여부를 결정한다.

### 검증

첫 단계는 MCP만 연결한 상태에서 아래 업무·오류 동작을 검증한다.
나중에 skill을 제안할 근거가 생기면 같은 계정·모델·클라이언트 버전에서 별도로 비교한다.

| 비교 | 확인할 항목 |
| --- | --- |
| MCP 연결 | HTTP 초기화, 도구 목록·스키마, 인증 실패·scope 거부, 업무 오류의 MCP 오류 표시 |
| Hub 통합 | 기존 lifespan 유지, REST·SPA 경로, 재시작·인스턴스 변경 시 재연결 |
| 작은 CI repo / 복합 CI repo | 기존 workflow 재사용, 필수 job 식별, 실제 연결 테스트와 정리 |
| 재요청·재연결 | 중복 프로젝트·PR 테스트·작업 dispatch 여부, 기존 실행 복구 |
| 권한 제한 | 미인증 요청·허용되지 않은 scope의 호출이 차단되는지. 프로젝트별 권한·목록 필터를 추가하면 조회와 호출을 함께 검증 |
| 대량 이력·오류 | 요약 우선 응답, 페이지 처리·로그 발췌·오류 코드가 우선 지원 클라이언트에서 사용 가능한지 |

컨텍스트 지표를 공개하지 않는 제품은 숫자를 추정해 확정값처럼 쓰지 않는다.
서버 스키마의 토큰 추산은 실제 클라이언트 입력량과 분리해서 기록한다.
첫 단계의 완료 기준은 MCP만으로 공개한 업무 흐름의 성공이다.
패키지 로컬 검증과 AutoHub 통합 검증, 실제 운영 클라이언트 검증을 구분한다.
후속 구현의 수행 결과는 문서 상단에 기록한다.

## 대안 비교

| 제공 형태 | 판단 |
| --- | --- |
| GitHub 문서만 | 최초 설정에는 충분하지만 일상적인 조회·제어마다 API 호출 방법과 인증을 에이전트가 다시 다룬다. 보조 진입점으로 유지한다. |
| 원격 MCP만 | **첫 단계 권고안이다.** 기존 Hub에 app-mcp를 통합하고 연결 안내만 제공한다. |
| 원격 MCP + 선택형 skill | 후속 선택지다. 반복 작업에서 필요가 확인된 뒤 추가한다. |
| repo마다 필수 APM skill | 현재 개인의 여러 repo 사용 목표에는 관리가 과하다. 기본값으로 삼지 않는다. |
| CLI 중심 | shell 자동화나 CI 소비자가 생기면 의미가 있다. 현재 세 AI 클라이언트 통합을 위해 먼저 만들 필요는 없다. |
| 클라이언트별 plugin 세 종류 | 향후 설치 편의용 포장으로 검토한다. 핵심 인터페이스보다 먼저 만들지 않는다. |
