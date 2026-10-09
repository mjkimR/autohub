# SDK task·flow 원격 계약

## 현재 범위

`packages/sdk`의 autohub-sdk 0.2.0은 기존 로컬 pipeline·manifest v1에 더해 순차 flow 선언과 HTTP client를 제공한다. 실제 autohub backend에 release catalog·task-runs API와 DB 기반 flow 실행기를 구현했다. SDK 계약은 planhub의 별도 환경 `mock/autohub` HTTP stub과 실제 backend의 loopback HTTP·DB 통합 테스트에서 검증한다. 운영 배포는 별도다. Python 3.13+가 필요하며 runtime dependency는 Pydantic뿐이다.

## 정의와 배포

FlowManifest v2는 TaskSpec 역할의 기존 PipelineSpec과 FlowSpec을 포함한다. TaskStep의 입력은 literal 또는 run·이전 task 출력의 경로 참조이며 다음 step으로 순서대로 이동한다. ApprovalStep은 deadline과 선택적 revise_to·max_revisions를 선언한다. FlowSpec은 result_step을 지정한다. SDK는 중복·미지원 task 참조·미래 출력 참조·잘못된 반환을 거부한다. 개별 필드와 schema assignability의 정적 판정은 없으며 host가 참조 해석과 실제 입출력 schema를 검증한다.

ReleaseSpec은 manifest와 task별 정확히 하나의 binding을 묶는다. binding은 http/native executor와 target 참조이며 Python 코드를 포함하지 않는다. 정의 등록과 worker 배포를 구분한다. host는 관리된 machine key와 provider/environment 소유권을 검사하며 서버에 설정된 binding만 허용한다. mock은 native mock.echo만 지원한다.

## HTTP 계약

| 연산 | SDK 메서드 | 경로 |
| --- | --- | --- |
| release 등록 | register_release | PUT /api/v1/task-providers/{provider}/environments/{env}/releases/{release_id} |
| 활성화 | activate_release | POST 위 release 경로/activate |
| 실행 | start_run | POST /api/v1/task-runs |
| 조회 | get_run | GET /api/v1/task-runs/{run_id} |
| 제어 | command | POST /api/v1/task-runs/{run_id}/commands |

동일 release ID·digest는 멱등이며 다른 내용은 충돌한다. 활성화는 expected_revision을 검사한다. RunRequest는 provider·environment·task 계약·inputs·idempotency_key를 사용한다. 동일 key·내용은 같은 run을 반환하고 변경된 내용은 충돌한다. 진행 중 run은 접수 당시 release ID·digest·정의·binding snapshot을 유지한다.

RunCommand는 command_id·expected_revision과 approve/revise/cancel/resume을 전달한다. 명령 재전송은 최초 receipt를 반환하고 같은 ID의 내용 변경은 충돌한다. run revision은 상태 전이마다 증가한다. AttemptView는 step·number·status·input·output·error를, RunView는 release snapshot 식별자·status·현재 step·대기 이유·attempt·결과를 제공한다. 재시도와 보완 방문은 누적 task step 시도 상한을 소비한다.

client는 기존 host 방식에 맞춰 X-API-Key를 전송하고 redirect·자동 재시도는 수행하지 않는다. AutoHubError는 HTTP status·error code를 제공하며 network timeout은 전달된다. 실제 승인 evidence·허용 명령 주체·head/revision binding은 도메인 host 계약의 후속 범위다.

## 실행 원장과 복구

SDK는 DB와 scheduler를 소유하지 않는다. 기존 내부 scheduler @task, Work Plan/Item, PR PipelineRun은 외부 SDK task·flow와 별개다. 별도 `sdk_flow_*` 테이블에 환경·release·run·step·attempt·command receipt를 저장한다. dispatch intent를 먼저 커밋하고 DB transaction 밖에서 worker를 호출한다. 60초 lease와 revision 조건부 쓰기로 늦은 결과를 차단한다. 응답이 불확실하면 기존 attempt를 조회하며, worker가 같은 ID의 부재를 명시적으로 확인한 뒤에만 그 ID로 다시 접수한다. 같은 PR을 기존 PR 실행기와 flow 실행기가 동시에 제어하지 않는다.

SDK 계약·planhub mock은 specs/2026-10/20261009-sdk-task-flow-contract에서 추적한다. durable host는 [구현 spec](../specs/2026-10/20261009-durable-sdk-host/spec.md)에서 추적한다. 후속 planhub application·specrig/PR·범위 연결은 workbench의 `docs/planhub-autohub-task-flow-design.md` F3~F4와 planhub PROP-autohub-delivery-host에 연결된다. 기존 단일 pipeline 소비자는 manifest v1과 로컬 실행을 계속 사용할 수 있다.


## 인증과 실행 대상

관리 API에서 발급한 `X-API-Key`를 사용한다. `autohub:task:write`는 등록·활성화·실행·제어, `autohub:task:read`는 조회에 필요하다. approve/revise는 write와 `autohub:task:approve`가 모두 필요하다. provider/environment는 최초 등록 machine이 소유하며 같은 machine의 key 교체는 소유권을 유지한다. command 원장에는 machine/key actor와 receipt를 남긴다. 일반 승인 명령은 PR head·review evidence의 검증을 대신하지 않는다.

native executor는 부작용 없는 `autohub.identity`만 지원한다. HTTP worker 설정과 프로토콜은 [개발 가이드](development.md#sdk-flow-host)를 따른다. 등록은 worker 코드 배포를 수행하지 않는다. host 한도는 provider/environment 64자, task key 256자, step ID 128자, 계약 버전 32비트 양의 정수, approval deadline 1년이다. JSON Schema는 draft 2020-12를 사용하고 외부 `$ref`는 거절한다.

`System maintenance`가 최대 32개 run을 한 단계씩 진행한다. GET·실행 접수는 worker를 실행하지 않는다. 승인 deadline은 명령 수신 때도 검사하고 기한 만료 전이는 다음 maintenance에서 기록한다. 외부 polling의 다음 시점은 5초 이후지만 실제 진행 간격은 dispatcher tick에 따른다. 취소는 외부 worker의 terminal 결과 확인까지 `canceling`이며, transport 오류·일반 404는 종료 증거로 사용하지 않는다.
