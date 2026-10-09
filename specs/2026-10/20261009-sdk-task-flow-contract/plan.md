---
id: PLAN-sdk-task-flow-contract
spec: SPEC-sdk-task-flow-contract
---

# 구현 계획

## 불변식 검토

기존 SDK는 Pydantic 외 runtime dependency를 추가하지 않는다. planhub의 기존 범위·조율 4-layer 서버는 변경하지 않고 독립 mock 환경과 outbound 데모를 추가한다. 코드 등록과 배포 binding을 분리하고 실행 상태는 autohub 계약으로 제공한다.

## 구성

SDK flow 모델은 순차 task·approval wait와 제한된 revise 반환, 입력 literal/run/step 참조를 제공한다. release의 manifest v2는 기존 v1과 별개다. client는 urllib 기반이며 자동 재시도 없이 오류를 구조화한다.

mock은 SDK 계약 모델·jsonschema 검증을 재사용하는 FastAPI HTTP stub이다. 메모리 snapshot·request/command 멱등성·fake clock·scenario 결과만 관리하고 운영 실행기를 구현하지 않는다. 승인 명령은 로컬 demo identity로 제한하며 실제 서비스 identity와 증거 검증은 후속이다.

## 검증

SDK 모델·transport 오류 테스트, mock 실제 loopback HTTP client 시나리오 테스트, wheel/sdist build·분리 환경 artifact 설치를 확인한다. 각 저장소 just lint/check와 planhub specrig lint를 실행한다. 운영 DB·실제 GitHub 실행은 검증 범위 밖이다.
