---
id: SPEC-sdk-task-flow-contract
title: SDK task·flow 등록과 로컬 연동
status: completed
created: 2026-10-09
---

# [SPEC-sdk-task-flow-contract] SDK task·flow 등록과 로컬 연동

## User Story

planhub 개발자로서 SDK로 작업 flow를 등록하고 실행·조회·승인·재개하여 실제 autohub 연결 전에 HTTP 계약을 검증한다.

## Scope

SDK에 선언형 flow·release·run·command 모델과 표준 라이브러리 HTTP client를 추가한다. 기존 manifest v1·로컬 pipeline은 보존한다.

## Non-Goals

운영 DB 실행기·분산 scheduler·worker 배포·실제 specrig/PR 실행·UI 편집·임의 DAG는 제외한다. 로컬 mock의 승인·시계·실행 결과는 테스트용이며 운영 승인·복구 증거가 아니다.

## Acceptance Criteria

### [AC-01] 정의와 호환
- **Given** 기존 SDK pipeline과 새 순차 task/wait flow
- **When** 정의·manifest를 검증
- **Then** 기존 v1은 동일하고 중복 ID·잘못된 task 참조·미래 출력 참조·잘못된 반환 경로는 거부된다.

### [AC-02] 등록과 실행 멱등성
- **Given** release와 실행 요청
- **When** 같은 ID/key를 재전송하거나 내용을 변경
- **Then** 동일 내용은 같은 release/run, 다른 내용은 409다. 활성화 CAS는 stale revision을 거부하며 run snapshot은 활성 release 변경에 영향을 받지 않는다.

### [AC-03] 대기와 명령
- **Given** 승인 대기 run과 revision
- **When** approve·revise·cancel·resume을 전달
- **Then** 승인 후 완료, 제한된 보완 반환, stale revision 거부, 동일 command 재전송과 ID 충돌 구분을 검증한다. 실패 task의 resume은 선언된 시도 상한을 지킨다.

### [AC-04] 관찰과 오류
- **Given** 접수 응답 유실·외부 효과 후 timeout·작업 실패·취소 지연 시나리오
- **When** SDK가 동일 요청을 재전송하고 상태를 조회
- **Then** 같은 run/attempt가 유지되고 오류와 대기 이유가 구조화되어 표시된다. 가짜 clock으로 deadline을 검증한다.

### [AC-05] 실제 HTTP client 연결
- **Given** wheel로 설치한 SDK와 mock 서버
- **When** 계획의 prepare→execute→wait_approval→finalize를 등록·실행
- **Then** sibling import 없이 실제 HTTP 경로로 동작하며 입력·출력 schema 위반은 거부되고 요청 기록에 provider·release·입력이 남는다.
