# 저장소 뷰어 및 Specrig 지원

프로젝트의 성격에 따라 `project_type`을 설정한다 (`general` / `specrig`).
내장된 저장소 뷰어가 프로젝트 타입에 맞추어 최적화된 화면을 제공한다.

## 프로젝트 모드

| 모드 (`project_type`) | 설명 |
| --- | --- |
| `general` | 기본 Git 브라우저 (디렉터리 트리, 파일 내용, README 미리보기) |
| `specrig` | Spec-Driven Engineering 프로젝트 전용 뷰어 (Living Spec, C4 아키텍처 다이어그램, Proposals/Specs 인덱스, 태그/TOC 탐색) 및 Git 브라우저 |

프로젝트 설정(Settings) 또는 신규 프로젝트 등록 시 `Project Type`을 선택할 수 있다.

## 네이티브 뷰어 통합

과거 배포 시점 외부 번들 다운로드 및 Custom Element 동적 로더 기반 플랫폼에서, autohub 내부 네이티브 Svelte 컴포넌트(`SpecrigViewer`)로 이관·통합되었다.
별도의 외부 번들 발행이나 `repository-viewers.local.json` 설정 파일 없이 네이티브로 동작한다.

- `project_type === 'specrig'` 프로젝트에서는 기본 화면으로 **Specrig View**가 열리며, 필요 시 **Git Browser**로 전환할 수 있다.
- Markdown 파싱, YAML 프론트매터 분석, Mermaid 다이어그램 렌더링, 문서 링크 정규화가 내장 지원된다.
- 데이터 조회는 autohub의 저장소 API (`/api/v1/projects/{project_id}/repository/*`)를 직접 사용한다.
