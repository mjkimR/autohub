# 저장소별 렌더러

프로젝트의 GitHub 저장소마다 `Repository viewer`를 선택한다. `default`는 내장 Git browser를
사용하고, 다른 ID는 배포에 설치된 해당 Custom Element를 사용한다. 하나의 autohub 설치에
여러 렌더러를 등록할 수 있으며 specrig은 그중 하나다. 예를 들어 저장소 A는 `specrig`,
저장소 B는 `custom-architecture`, 저장소 C는 `default`를 선택할 수 있다.

프로젝트 Connections 탭의 `Repository viewer`는 설치된 렌더러 이름을 표시한다. 선택은
`github.automation.repository_viewer`에 ID로 저장되며 기존 JSON 컬럼을 사용한다.
설치되지 않은 기존 선택은 `(unavailable)`로 유지하여 설정 편집 시 덮어쓰지 않는다.
ID는 소문자로 시작하는 최대 64자의 영문 소문자·숫자·하이픈이며, 프로젝트 설정으로
임의 JavaScript URL을 받지 않는다. 설치가 없거나 로딩이 실패하면 Git browser 복귀 버튼을
제공한다. Custom View 전환은 해당 프로젝트의 ID만 로드한다.

## 배포 시점 설치

렌더러 번들·압축 파일·설치 manifest는 autohub Git에 넣지 않는다. 설정 예시
`modules/hub-ui/repository-viewers.example.json`을 복사하여 **Git에서 무시되는**
`modules/hub-ui/repository-viewers.local.json`을 만든다. 각 항목은 다음 필드를 가진다.

| 필드 | 용도 |
| --- | --- |
| `id` | 프로젝트에서 선택할 렌더러 ID. `default`는 내장 뷰어용으로 예약 |
| `label` | 설정 화면의 이름 |
| `tagName` | 번들이 등록하는 Custom Element 태그 |
| `url` | 별도로 발행·배포한 단일 JS 번들의 HTTPS 주소 |
| `sha256` | 다운로드한 JS 원본의 SHA-256 |
| `initialPath` | 선택적 최초 탐색 경로. specrig은 `docs/`, 일반 렌더러는 기본 빈 경로 |

`npm run build`는 Docker/Cloud Build의 프런트엔드 빌드 단계에서 설정을 읽고 각 번들을
다운로드한다. 모든 해시 검증이 끝난 뒤 무시된 `static/plugins/repository-viewers/`에
`<id>/viewer.<sha256>.js`와 런타임 `manifest.json`을 생성한다. 서로 다른 ID와 태그를
등록하여 브라우저의 Custom Element 등록 충돌을 막는다. 하나라도 다운로드·검증에
실패하면 빌드가 실패하고 기존 설치를 유지한다. 설정이 없으면 오래된 생성물을 지우고
내장 Git browser만 빌드한다. 설정 예시는 설치 설정으로 자동 채택하지 않는다.

```sh
cp modules/hub-ui/repository-viewers.example.json modules/hub-ui/repository-viewers.local.json
# Edit the local file with published bundle URLs, hashes and renderer metadata.
just build-ui
```

추적된 `.gcloudignore`는 `.dockerignore`를 사용하므로 배포용 로컬 설정이 Cloud Build
소스 컨텍스트에 포함된다. `.dockerignore`는 로컬에서 생성한 번들을 제외하므로 실제
번들은 이미지 빌드에서 다운로드한다. 설정 자체는 Git에서 무시되며 인증 비밀을 담지 않는 설치
메타데이터다. workbench의 `just deploy autohub`와 autohub 배포 helper 모두 같은 Docker
빌드에서 설치한다. Git checkout만 사용하는 CI 환경은 해당 배포 설정을 별도로 제공해야 한다.
빌드가 sibling checkout의 코드나 번들 경로에 의존하지 않는다.

로컬 개발도 `npm run dev`에서 같은 설치를 수행한다. 명시적 설정 파일로 설치만 실행하려면
`just install-repository-viewers /absolute/path/config.json`을 사용한다. 이 명령은 생성 경로에
설치하며 설정·번들을 Git에 추가하지 않는다. 런타임은 manifest를 읽어 선택한 ID의 해시
경로를 import한다. 번들 버전 변경은 페이지 새로고침으로 새 Custom Element를 등록한다.
실제 산출물 발행·운영 배포는 별도 작업이다.

## 공통 호스트 계약

호스트는 모든 렌더러에 `repo-id`, `api-base`, `branch`, 설정한 `initial-path`를 전달한다.
JavaScript `dataSource` 프로퍼티의 `info(signal)`, `tree(path, ref, signal)`,
`blob(path, ref, signal)`은 기존 타입 지정 API 클라이언트를 사용하여 Bearer 인증,
401 세션 갱신·재시도와 취소를 처리한다. 토큰은 DOM 속성으로 전달하지 않는다.

- `GET /api/v1/projects/{project_id}/repository/info`
- `GET /api/v1/projects/{project_id}/repository/tree?path=...&ref=...`
- `GET /api/v1/projects/{project_id}/repository/blob?path=...&ref=...`

트리는 `{items: [...]}`와 `file/dir` 항목을 반환한다. specrig은 이를 내부 `blob/tree`로
정규화하며 Markdown, YAML 프론트매터와 Mermaid를 Shadow DOM 내부에 렌더링한다.
다른 렌더러는 같은 저장소 데이터와 ref로 자신의 UI를 구성한다. 브랜치 변경은 모든
렌더러의 `branch` 속성에 반영된다.
