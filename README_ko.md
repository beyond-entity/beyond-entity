# Beyond Entity — Architecture Memory for AI Coding Agents

[English](README.md) · [한국어](README_ko.md) · [日本語](README_ja.md)

Beyond Entity는 AI 에이전트와 엔지니어가 함께 사용하는 지속적인 Architecture Memory입니다. 시스템의 의도, 설계 결정, 모델, 데이터 계약, Processor의 Transformation, 구현 맥락을 다음 작업 세션으로 이어갈 수 있습니다.

**beyond-entity-mcp** 플러그인은 로컬 Beyond Entity MCP 서버를 통해 이 메모리를 AI 코딩 작업과 연결합니다. 함께 제공되는 스킬은 에이전트가 맥락을 복구하고, 코드 변경 전에 설계를 확인하며, 검증된 구현 변경에 맞춰 설계를 갱신하고, 다음 에이전트나 사람을 위한 Checkpoint를 남기도록 안내합니다.

Beyond Entity는 MCP(Model Context Protocol)를 통해 Claude Code 또는 Codex와 함께 **소프트웨어 아키텍처 모델링**, **아키텍처 다이어그램**, **데이터 리니지**, **설계 기반 코딩**에 사용할 수 있습니다.

[Beyond Entity 다운로드](https://beyondentity.com/en/download) · [설치 가이드(영문)](INSTALL.md) · [사용자 가이드](docs/USER_GUIDE_ko.md) · [샘플 프로젝트(영문)](samples/README.md) · [웹사이트](https://beyondentity.com) · [GitHub](https://github.com/beyond-entity/beyond-entity)

[![Table Q의 Web, API, 데이터베이스 Attribute Lineage](assets/screenshots/table-q-workflow.png)](https://canvas.beyondentity.com/viewsample?sample_project_file_id=rXxLCaaJ1nEVN9CKbneL)

*웹 상호작용에서 API Transformation을 거쳐 데이터베이스 Attribute까지 흐름을 추적하세요. 이미지를 클릭하면 Viewer에서 Table Q를 탐색할 수 있습니다.*

## 설계 또는 기존 코드에서 시작하기

어느 쪽에서든 Architecture Memory를 구축할 수 있습니다.

- **설계부터 시작하기.** AI 에이전트에게 MCP를 통해 요구사항을 Beyond Entity 설계로 만들도록 요청하세요. 시스템 경계, Entity, 데이터 계약, Processor, Transformation을 포함합니다. 앱에서 Web/App 아키텍처, ERD, API, ETL/ELT 파이프라인, Scheduler를 직접 설계하거나 AI와 함께 작업할 수도 있습니다. 설계를 함께 리뷰하고 다듬은 뒤 구현을 요청하세요.
- **기존 코드에서 시작하기.** 에이전트에게 코드베이스를 분석해 아키텍처와 데이터 흐름을 추출하고, MCP로 모델과 설계 문서를 Beyond Entity에 기록하도록 요청하세요. 추출된 설계를 리뷰하면서 코드로 확인된 사실, 추정한 의도, 미해결 질문을 구분합니다.

두 방식 모두 코딩 중 설계를 공통 참조로 사용하고 검증된 구현 변경과 일치시키는 흐름으로 이어집니다. 기능이나 서비스 하나부터 시작해 필요한 만큼 메모리를 확장할 수 있습니다.

## 코딩할 때 AI가 설계를 참조하도록 요청하기

기능 구현, 버그 수정, 리팩터링 전에 Beyond Entity를 확인하도록 요청하세요. 에이전트는 MCP로 관련 Processor의 Transformation, 입출력 계약, 의존성을 읽고 변경에 활용할 수 있습니다.

요청한 동작이 아키텍처를 바꾼다면 해당 BE 설계도 갱신하고 변경 이유를 기록하도록 하세요. 개발 전반에서 설계를 활용하고 다음 작업자에게 맥락을 전달할 수 있습니다. 설계 참조는 에이전트의 작업 방식이며, 생성된 코드의 일치를 자동으로 보장하지는 않습니다. 구현과 설계를 비교해 검증하세요.

## 작업 흐름

1. **맥락 복구.** 최신 Checkpoint와 관련 프로젝트 문서를 읽고 다른 에이전트나 사람의 변경을 확인합니다.
2. **설계 확인.** 코드를 수정하기 전에 관련 Processor와 현재 Transformation, 입출력 Entity, Attribute를 읽습니다.
3. **구현과 동기화.** 요청한 변경을 구현하고 모델에 표현된 동작이 바뀌면 설계도 갱신합니다. 모든 코드 차이를 의도한 변경으로 가정하지 말고 불일치의 이유를 확인합니다.
4. **검증과 인계.** 구현과 설계가 일치하는지 확인하고 완료한 변경, 이유, 검증 내용, 남은 작업을 Checkpoint에 기록합니다.

프로젝트 읽기와 쓰기는 MCP를 통해 수행합니다. 스킬은 오래된 대화에만 의존하거나 BE 프로젝트 데이터베이스를 직접 편집하는 대신 최신 상태를 다시 읽도록 안내합니다. 리뷰만 요청한 경우에는 데이터를 변경하지 않습니다.

## 필요한 상세 수준으로 설계 탐색하기

기본 모델 화면은 모든 Attribute가 펼쳐진 상태로 표시됩니다. Satellite View와 사용자가 만든 Canvas에서는 Entity나 Processor 이름 중심의 작은 박스로 시작해 큰 설계도 읽기 쉽게 유지합니다. 상세가 필요하면 박스의 펼치기 버튼으로 Attribute를 표시하세요.

박스를 접는 것은 표시 방식을 바꾸는 것이며, Attribute가 없다는 뜻이 아닙니다. 전체 구조를 먼저 살펴본 뒤 현재 작업에 관련된 부분을 펼칠 수 있습니다.

[![접힌 Processor와 선택적으로 펼친 Attribute가 있는 Satellite View](assets/screenshots/table-q-satellite-view.png)](https://canvas.beyondentity.com/viewsample?sample_project_file_id=rXxLCaaJ1nEVN9CKbneL)

*전체 Canvas는 간결하게 유지하고 필요한 Entity나 Processor만 펼쳐 Attribute와 매핑을 확인하세요. 이미지를 클릭하면 Viewer가 열립니다.*

## Beyond Entity와 Archify 비교하기

[Archify](https://github.com/tt-a1i/archify) 같은 AI 아키텍처 다이어그램 도구를 살펴보고 계신가요? Archify는 코드나 시스템 설명에서 대화형 HTML/SVG 다이어그램을 생성하고, 스냅샷 비교와 모델에 정의된 경로 추적을 지원합니다.

Beyond Entity는 **AI 코딩 에이전트를 위한 Architecture Memory**에 초점을 둡니다. 편집 가능한 Entity, Attribute, Processor Transformation, ERD, 데이터 리니지와 함께 Checkpoint로 설계·구현 맥락을 세션 간에 이어갑니다. 사람은 앱에서 모델을 리뷰하고, 에이전트는 MCP로 읽고 수정합니다.

도구를 비교할 때는 대화형 시스템 다이어그램을 설명·공유하려는지, 코딩 중 에이전트가 참조하고 갱신할 공유 설계를 유지하려는지 살펴보세요. [Table Q 설계와 구현](samples/table-q/README.md)에서 BE 작업 흐름을 확인할 수 있습니다. 두 도구는 독립적인 프로젝트이며, 이 저장소는 Archify 연동이나 자동 가져오기를 제공하지 않습니다.

## 시작하기

- [공식 다운로드 페이지](https://beyondentity.com/en/download)에서 **macOS 또는 Windows**용 Beyond Entity를 설치하세요.
- [INSTALL.md](INSTALL.md)에 따라 앱에 포함된 `beyond-entity-mcp` 서버와 architecture-memory 스킬을 **Claude Code**(플러그인 마켓플레이스 이용) 또는 **Codex**에 연결하세요.
- Beyond Entity에서 프로젝트를 열거나 아래 샘플을 탐색하세요.

MCP 실행 파일은 데스크톱 앱에서 제공합니다. 이 저장소는 플러그인 설정과 architecture-memory 스킬을 제공합니다. 저장소만 다운로드하면 데스크톱 앱이 설치되는 것은 아닙니다.

## 요청 예문

**설계에서 코드로**

> 이 기능을 Entity, Processor, Transformation까지 포함해 Beyond Entity에서 먼저 설계해줘. 그 설계를 참조해 구현하고 동작이 일치하는지 검증해줘.

**코드에서 설계로**

> 기존 코드베이스를 분석하고 MCP를 통해 아키텍처를 Beyond Entity에 기록해줘. 데이터 구조, 처리 책임, 데이터 흐름을 모델링하고 확인이 필요한 설계 의도를 찾아줘.

**설계를 참조하며 코딩하기**

> 현재 Beyond Entity 설계를 참조해서 이 기능을 구현해줘. 수정 전에 관련 Processor의 Transformation을 읽고 기존 계약을 유지하며, 의도한 설계 변경은 이후 동기화해줘.

**공유 작업 이어가기**

> Beyond Entity를 이 프로젝트의 Architecture Memory로 사용해줘. 최신 Checkpoint를 읽고 이전 인계 이후의 관련 변경을 요약해줘.

> 이 Endpoint를 변경하기 전에 해당 Processor와 Transformation 설계를 확인하고 현재 구현과 비교해줘.

> 이번 변경의 구현과 관련 BE 아키텍처를 갱신하고 일치 여부를 검증한 뒤 다음 개발자를 위한 Checkpoint를 남겨줘.

## 샘플

| 샘플 | 살펴볼 내용 | 자료 |
| --- | --- | --- |
| **Table Q by Codex** | 식당·카페 대기열, 테이블 상태, 여러 매장 현황 관리와 Codex가 생성한 구현 | [프로젝트 가이드](samples/table-q/README.md) · [Viewer](https://canvas.beyondentity.com/viewsample?sample_project_file_id=rXxLCaaJ1nEVN9CKbneL) |
| **eCommerce data lake** | Oracle → Google Cloud Storage → BigQuery Lineage와 매출·상품·고객 세션 SQL 집계 | [프로젝트 가이드](samples/ecommerce/README.md) · [Viewer](https://canvas.beyondentity.com/viewsample?sample_project_file_id=BWBDcESJ4tJcGkZqvRwL) |
| **Databricks Lakehouse** | Lakehouse 설계, Python 소스, Job, 테스트, Codex 대화 요약 | [프로젝트 가이드](samples/databricks/README.md) |
| **Snowflake Enterprise ELT** | ELT 설계, SQL, Python 파이프라인, DAG, 테스트, Claude Code 대화 요약 | [프로젝트 가이드](samples/snowflake/README.md) |

[Databricks와 Snowflake 비교](samples/COMPARISON.md): 설계, 구현 구조, 수정 사례, 비즈니스 질문을 비교합니다. 샘플 가이드와 비교 문서는 영문입니다.

가이드에는 `.bemdl` 다운로드 링크가 있습니다. Table Q에는 [Codex가 생성한 구현](samples/table-q/src/)과 데이터베이스 스키마가 포함되어 있습니다. 실행 전에 [Table Q 설정 안내](samples/table-q/README.md)를 확인하세요.

[더 많은 샘플 →](https://beyondentity.com/en/sample-projects)

## 저장소 구조

```text
.
├── README.md
├── README_ko.md
├── README_ja.md
├── docs/                              # User guides in English, Korean, and Japanese
├── INSTALL.md
├── assets/screenshots/                 # README screenshots
├── .claude-plugin/marketplace.json      # Claude Code plugin marketplace
├── plugins/
│   └── beyond-entity-mcp/
│       ├── .claude-plugin/plugin.json   # Claude Code plugin manifest
│       ├── .codex-plugin/plugin.json    # Codex plugin manifest
│       ├── .mcp.json                    # MCP server (command: beyond-entity-mcp)
│       └── skills/architecture-memory/
│           ├── SKILL.md
│           └── references/modeling-principles.md
└── samples/
    ├── README.md
    ├── table-q/
    │   ├── README.md
    │   ├── src/                         # Codex-generated implementation
    │   └── db/                          # Initial schema and schema verification
    ├── ecommerce/README.md
    ├── databricks/                      # Python package, jobs, tests, architecture notes
    ├── snowflake/                       # SQL, Python pipelines, Airflow DAGs, tests
    └── COMPARISON.md
```

이 저장소는 **Claude Code 플러그인 마켓플레이스**(`.claude-plugin/marketplace.json`)를 자체 제공하며, 같은 목적의 Codex 플러그인도 포함합니다. 공개 Git 저장소로 배포하면 별도의 중앙 심사 없이 사용자가 추가할 수 있습니다([INSTALL.md](INSTALL.md) 참고). Anthropic 커뮤니티 플러그인 디렉터리 등록은 별도의 선택 사항입니다.

## 라이선스

이 저장소의 플러그인 설정, 스킬, 문서, 샘플 코드에는 MIT License가 적용됩니다. Beyond Entity 데스크톱 앱과 별도로 배포되는 MCP 실행 파일에는 각 제품의 라이선스 약관이 적용됩니다. 타사 구성 요소는 각자의 라이선스를 따릅니다.
