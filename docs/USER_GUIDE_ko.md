# 사용자 가이드: 요구사항에서 구현까지

[English](USER_GUIDE.md) · [한국어](USER_GUIDE_ko.md) · [日本語](USER_GUIDE_ja.md)

예제와 대화 요약: [Databricks](../samples/databricks/README.md) · [Snowflake](../samples/snowflake/README.md) · [두 예제 비교(영문)](../samples/COMPARISON.md).

Beyond Entity를 프로젝트의 공유 Architecture Memory로 사용하세요. 시스템을 설명하고, AI 에이전트와 설계하고, 데이터 흐름을 리뷰하고, 설계를 구현한 뒤 코드 변경에 맞춰 설계를 최신 상태로 유지합니다.

이 가이드는 Databricks와 Snowflake 설계 사례를 사용하고, ERD와 구현 사례에는 Table Q를 사용합니다. 서로 다른 프로젝트이며, 하나의 프로젝트가 순서대로 변하는 화면이 아닙니다. Web/App 아키텍처, API, 데이터베이스, ETL/ELT 파이프라인, Scheduler에도 같은 흐름을 적용할 수 있습니다.

**시작하기 전에:** [INSTALL.md](../INSTALL.md)에 따라 데스크톱 앱을 설치하고 MCP를 연결한 다음 `architecture-memory` 스킬을 추가하세요. 앱은 시각적으로 작업할 공간을 제공하고, MCP는 에이전트가 프로젝트를 읽고 수정할 수 있게 하며, 스킬은 그 메모리를 사용하는 작업 방식을 안내합니다.

캡처는 macOS 환경의 예시입니다. 설치는 자신의 환경에 맞는 안내를 따르세요. 이미지를 클릭하면 원본 해상도로 볼 수 있습니다. 아래 요청 예문은 복사한 뒤 프로젝트에 맞게 바꾸어 사용하세요. 버튼과 메뉴 이름은 캡처의 영문 UI 표기를 유지했습니다.

## 목차

1. [에이전트 연결 및 확인](#step-1)
2. [프로젝트 생성 또는 열기](#step-2)
3. [시스템을 설명하고 AI에게 설계 요청하기](#step-3)
4. [기존 코드에서 시작하기](#step-4)
5. [화면에서 설계 리뷰하기](#step-5)
6. [Checkpoint와 구현 상태 확인하기](#step-6)
7. [리뷰한 설계 구현하기](#step-7)
8. [코드 변경을 Beyond Entity에 반영하기](#step-8)
9. [다른 에이전트나 팀원과 작업 이어가기](#step-9)

<a id="step-1"></a>

## 1. 에이전트 연결 및 확인

데스크톱 앱의 설정에서 **MCP setup guide**를 선택하세요. [설치 가이드](../INSTALL.md)에서 Claude Code 또는 Codex에 해당하는 절차를 따라 architecture-memory 스킬까지 준비합니다. MCP 연결이 동작한다고 해서 스킬도 설치된 것은 아닙니다.

캡처에는 연결 이름이 `beyond-entity`로, 실행 파일 위치가 macOS 경로로 표시되어 있습니다. 현재 설치 가이드는 `beyond-entity-mcp`와 PATH 기반 명령을 사용합니다. 이미 동작하는 연결이 있다면 중복으로 추가하지 말고 기존 연결을 사용하세요.

설정 후 다음과 같이 요청하세요.

> Beyond Entity MCP로 사용할 수 있는 프로젝트 목록을 조회해줘. 아무것도 변경하지 말고 프로젝트 이름과 ID를 알려줘.

**확인:** 응답에 실제 프로젝트가 나오는지 확인하세요. 아직 프로젝트가 없다면 다음 단계에서 생성합니다. 호출이 실패했다면 연결 문제를 해결한 뒤 진행하세요.

<a href="../assets/screenshots/mcp_setting_codex.png"><img src="../assets/screenshots/mcp_setting_codex.png" alt="Codex 설정 요청과 프로젝트 목록, Beyond Entity MCP 설정 가이드" width="960"></a>

*Codex 예시입니다. 오른쪽의 MCP setup guide와 왼쪽의 프로젝트 목록 응답을 확인하세요.*

<details>
<summary>Claude Code 연결 예시</summary>

<a href="../assets/screenshots/mcp_setting_claude.png"><img src="../assets/screenshots/mcp_setting_claude.png" alt="Claude 연결 설정과 프로젝트 조회, MCP 설정 가이드" width="960"></a>

*Claude 예시입니다. 최신 설정과 스킬 설치 방법은 INSTALL.md를 따르세요.*

</details>

<a id="step-2"></a>

## 2. 프로젝트 생성 또는 열기

에이전트에게 프로젝트 생성을 요청하거나 Beyond Entity에서 직접 만들 수 있습니다.

### 에이전트에게 요청하기

프로젝트 이름과 에이전트가 접근할 수 있는 폴더를 지정하세요.

> [프로젝트 폴더]에 “Retail Analytics”라는 이름으로 새 로컬 Beyond Entity 프로젝트를 MCP를 통해 생성해줘. 생성된 프로젝트 이름, ID, 파일 위치를 알려주고 초기 프로젝트 문서를 읽어줘.

**확인:** 데스크톱 앱의 로컬 프로젝트 목록에 새 프로젝트가 표시되는지 확인합니다. 프로젝트를 열고 에이전트 응답의 이름과 비교하세요.

<a href="../assets/screenshots/project_creation_by_ai.png"><img src="../assets/screenshots/project_creation_by_ai.png" alt="AI가 생성한 Databricks 프로젝트와 Beyond Entity 프로젝트 목록" width="960"></a>

*왼쪽 생성 결과에 해당하는 프로젝트가 오른쪽 목록에 표시됩니다. 해당 행의 Open 버튼으로 열 수 있습니다.*

### 직접 만들기

로컬 프로젝트 목록에서 **New Platform Project**를 선택하세요. **New Local Project** 대화상자에 프로젝트 이름, 저장 위치, 파일 이름을 입력하고 **Create**를 선택합니다.

기존 파일은 **Select Project File**로 선택합니다. 수정하기 전에 에이전트에게 프로젝트 목록을 다시 조회하고 작업할 프로젝트를 식별하도록 요청하세요.

<a href="../assets/screenshots/project_creation_by_user.png"><img src="../assets/screenshots/project_creation_by_user.png" alt="이름, 저장 위치, 파일 이름, Create 버튼이 있는 새 프로젝트 대화상자" width="960"></a>

*직접 생성하는 방법은 오른쪽 대화상자를 보세요. 왼쪽 Databricks 대화는 별도 사례이며, 오른쪽은 Snowflake 프로젝트 생성 화면입니다.*

<a id="step-3"></a>

## 3. 시스템을 설명하고 AI에게 설계 요청하기

**DOCUMENT → about_this_system.md**를 열고 시스템의 목적, 사용자, 업무 흐름, 원천 시스템, 출력, 제약사항을 기록하세요. **Code/Text**로 편집하고 **Save**로 저장하거나, 에이전트에게 MCP를 통해 문서를 갱신하도록 요청할 수 있습니다.

보안 경계, 실패 처리, 실행 주기, 프로젝트 범위에 포함되지 않는 사항처럼 설계에 영향을 주는 요구사항도 포함하세요.

> MCP로 이 프로젝트의 문서를 읽어줘. 아래 요구사항을 about_this_system.md에 반영하고, 설계를 시작하기 전에 불명확한 요구사항을 확인하고 가정을 명시적으로 기록해줘: [요구사항].

<a href="../assets/screenshots/edit_about_this_system_document.png"><img src="../assets/screenshots/edit_about_this_system_document.png" alt="Databricks 프로젝트를 설명하는 About This System 문서" width="960"></a>

*about_this_system.md의 목적과 업무 시나리오를 검토하세요. 오른쪽 위에 Code/Text와 Save가 있습니다.*

요구사항이 명확해지면 다음과 같이 요청하세요.

> Beyond Entity를 이 프로젝트의 Architecture Memory로 사용해줘. MCP로 최신 문서와 설계 상태를 읽고, 요구사항에 맞는 시스템 경계, Entity, 데이터 계약, Processor, Transformation을 설계해줘. 리뷰할 수 있는 단계로 나누어 진행하고, 모델과 아키텍처 문서를 일치시켜줘. 각 주요 단계가 끝나면 결정 사항, 확인한 내용, 미해결 질문을 Checkpoint로 남겨줘. 아직 코딩은 시작하지 마.

앱에서 직접 모델링한 뒤 에이전트에게 확장이나 리뷰를 요청해도 됩니다. 이어서 작업하기 전에 최신 상태를 읽어 사용자의 수정 사항을 확인하도록 하세요.

<a href="../assets/screenshots/snowflask_start_design.png"><img src="../assets/screenshots/snowflask_start_design.png" alt="AI 설계 요청과 Beyond Entity 설계 원칙 문서" width="960"></a>

*이 Snowflake 사례는 결정 사항, 데이터 흐름, Transformation을 프로젝트에 보존하고 주요 단계를 기록하도록 요청합니다.*

<a id="step-4"></a>

## 4. 기존 코드에서 시작하기

이미 구현된 코드가 있다면 서비스 하나나 업무 흐름 하나처럼 범위를 정해서 시작하세요. 소스 폴더에 대한 접근을 제공하고 갱신할 Beyond Entity 프로젝트를 지정합니다.

> [소스 폴더]에서 [업무 흐름 또는 서비스]를 분석해줘. MCP로 현재 Beyond Entity 프로젝트를 읽고, 코드에 나타난 시스템 경계, 저장 Entity, API, Processor, 계약, Transformation을 설계로 기록해줘. 코드로 확인한 사실과 추정한 의도, 미해결 질문을 구분하고 필요한 곳에 소스 참조를 남겨줘. 이 단계에서는 구현 코드를 변경하지 마.

**확인:** 대표적인 Endpoint나 Job을 추출된 설계와 비교하세요. 실제 입력, 출력, 저장소 접근, 실패 시 동작이 모델에 포함되어 있는지 확인합니다. 추출된 설계를 구현 계약으로 사용하기 전에 불확실한 내용을 해결하세요.

<a id="step-5"></a>

## 5. 화면에서 설계 리뷰하기

시스템 전체에서 개별 Transformation으로 범위를 좁혀가며 리뷰하세요. 아래 데스크톱 캡처에는 편집 기능도 표시됩니다. 공개 샘플 Viewer에서는 설계를 탐색하고, 프로젝트 변경은 데스크톱 앱 또는 MCP를 통해 진행합니다.

### 전체 아키텍처 보기

**CANVAS → Satellite View**를 열거나 이미 열려 있는 탭을 선택하세요. 확대·축소로 시스템 그룹들이 보이도록 조정하고 캔버스를 이동하며 살펴보세요. 개별 Attribute를 추적하기 전에 시스템 이름과 경계를 확인합니다.

<a href="../assets/screenshots/databricks_review_in_satellite_view.png"><img src="../assets/screenshots/databricks_review_in_satellite_view.png" alt="애플리케이션, 저장소, Lakehouse 계층, 실행 조율, 분석을 보여주는 Databricks Satellite View" width="960"></a>

*Satellite View 탭, 시스템 그룹, 확대·축소 버튼부터 확인하세요. 이 화면에는 선택된 Attribute와 연결된 Lineage도 표시되어 있습니다.*

### 상세 펼치기와 접기

기본 모델 화면은 모든 Attribute가 펼쳐진 상태로 표시됩니다. Satellite View와 사용자가 생성한 Canvas에서는 Entity와 Processor가 이름 중심의 작은 박스로 시작합니다. 박스 오른쪽 위의 펼치기·접기 버튼으로 Attribute를 표시하거나 숨길 수 있습니다.

확인할 객체만 펼치고 나머지는 접어두세요. 박스를 접는 것은 표시 방식만 바꾸며, 설계에서 Attribute를 삭제하지 않습니다.

<a href="../assets/screenshots/snowflask_review_by_satellite_view.png"><img src="../assets/screenshots/snowflask_review_by_satellite_view.png" alt="접힌 박스와 펼친 Entity 및 Processor가 함께 보이는 Snowflake Satellite View" width="960"></a>

*아래쪽의 접힌 분석 박스와 위쪽의 펼친 Customer Entity를 비교하세요. 각 박스 오른쪽 위 버튼으로 표시 상태를 바꿉니다.*

### ERD 확인하기

**MODEL**에서 데이터베이스 모델을 열어 Entity, Attribute, 키 표시, 관계선을 확인하세요. **Logical / Physical**로 업무 관점의 이름과 구현에 사용하는 이름을 비교할 수 있습니다.

> 이 데이터베이스 모델을 요구사항과 비교해서 리뷰해줘. 키와 관계를 설명하고 누락된 제약사항이나 불명확한 소유 관계를 찾아줘. 변경을 제안하기 전에 MCP로 현재 모델을 읽어줘.

<a href="../assets/screenshots/database_review_using_erd.png"><img src="../assets/screenshots/database_review_using_erd.png" alt="Entity, 키, 관계선, 모델 속성이 보이는 Table Q 데이터베이스 모델" width="960"></a>

*Table Q의 ERD 예시입니다. 왼쪽 사이드바에서 모델을 선택하고 테이블과 관계를 확인하세요.*

### 검색과 Lineage 추적

**Search**로 `email` 같은 관련 이름을 검색하세요. **Entity, Processor 또는 Attribute를 클릭하면 연결된 데이터 흐름이 표시됩니다.** 특정 값이 시스템을 따라 이동하는 과정을 보려면 해당 Attribute를 선택하세요.

검색은 대상을 찾는 과정이고, 선택은 추적할 기준을 정하는 과정입니다.

<a href="../assets/screenshots/databricks_review_by%20search.png"><img src="../assets/screenshots/databricks_review_by%20search.png" alt="email 검색 후 Raw Customers의 Email Attribute를 선택해 Lineage가 표시된 화면" width="960"></a>

*검색창, 선택한 Email Attribute, 파란 연결선, 오른쪽의 Attribute 상세 정보를 확인하세요.*

### Lineage Depth 변경하기

오른쪽 패널의 **Max Lineage Depth** 옆 **− / +** 버튼으로 연결을 몇 단계까지 따라갈지 조정하세요. Depth를 비교할 때는 같은 객체를 선택한 상태를 유지합니다. 작은 값은 가까운 연결에 집중하는 데, 큰 값은 더 먼 아키텍처까지 살펴보는 데 유용합니다.

흐름을 따라가기 어렵다면 관련 박스를 펼치고 확대·축소도 조정하세요. Depth는 추적 범위를, 확대·축소는 캔버스가 보이는 크기를 바꿉니다.

### Processor의 Transformation 읽기

관련 Processor를 선택하고 속성 패널에서 **Transformations**를 여세요. 입력, Lookup/Context, 출력 Attribute와 함께 처리 규칙을 읽습니다. Attribute 연결은 데이터가 어디로 이동하는지 보여주고, Transformation은 데이터를 어떻게 계산하거나 처리하는지 설명합니다.

업무 규칙, 검증, 오류 처리, 상태 변경, 출력 계약을 확인하세요. ETL/ELT는 변환이 실행되는 위치와 읽고 쓰는 데이터도 확인합니다.

> MCP로 이 Processor와 Transformation을 읽어줘. 입력, 처리 규칙, 출력, 실패 사례를 설명하고 [요구사항]과 비교해서 구현 전에 부족한 부분을 찾아줘.

<a id="step-6"></a>

## 6. Checkpoint와 구현 상태 확인하기

왼쪽 탐색 메뉴에서 **Implementation Status** 영역을 열고 **Checkpoints**를 선택하세요. 항목을 열어 작성자, 시간, 메시지, 당시 상태를 확인합니다.

유용한 Checkpoint는 무엇을 왜 변경했는지, 무엇을 검증했는지, 무엇이 남았는지를 설명합니다. Checkpoint의 상태는 기록 당시의 스냅샷입니다. 현재 상태는 **Implementation Status**와 **Test Status** 화면에서 확인하세요.

구현 상태가 기록되어 있다는 사실만으로 실행 테스트 통과가 입증되지는 않습니다. 테스트 근거와 에이전트가 설명한 한계를 함께 확인하세요.

<a href="../assets/screenshots/databricks_checkpoint.png"><img src="../assets/screenshots/databricks_checkpoint.png" alt="작성자, 시간, 설계 단계, 구현 상태 스냅샷을 보여주는 Checkpoint 상세" width="960"></a>

*이 Checkpoint는 설계 명세임을 명시하고 DESIGNING 상태를 보여줍니다. 왼쪽 Computer Use 권한 요청은 캡처 당시 세션의 화면이며, Checkpoint 확인에 필요한 단계가 아닙니다.*

다음 예시는 이후 구현 중 발견된 문제와 이를 해결하기 위한 설계 변경을 기록합니다.

<a href="../assets/screenshots/snowflake_checkpoint_2.png"><img src="../assets/screenshots/snowflake_checkpoint_2.png" alt="환율 데이터 생성 흐름 추가와 수집 오류 수정을 설명하는 Snowflake Checkpoint" width="960"></a>

*주요 작업, 새 설계가 필요한 이유, 영향을 받는 객체를 읽어보세요. 위쪽 Changed by MCP와 Refresh는 앱이 외부 변경을 감지했음을 보여줍니다. 저장하지 않은 로컬 작업을 먼저 정리한 뒤 Refresh로 최신 상태를 불러오세요.*

<a id="step-7"></a>

## 7. 리뷰한 설계 구현하기

리뷰가 끝난 작은 범위를 선택하세요. 코드 위치와 관련 설계를 지정하고, 구현 전에 설계를 다시 읽도록 요청합니다.

> 리뷰한 Beyond Entity 설계를 사용해서 [소스 폴더]에 [업무 흐름]을 구현해줘. 먼저 MCP로 최신 Checkpoint, 관련 Processor의 Transformation, 데이터 계약, 의존성을 읽어줘. 동작을 결정하기 전에 모호한 부분을 설명해줘. 구현 후 적절한 검증을 수행하고 근거에 맞게 구현·테스트 상태를 갱신해줘. 변경 파일, 검증 결과, 남은 제약사항을 Checkpoint에 기록해줘.

**결과 리뷰:** 코드의 입력, 출력, 규칙, 오류 처리를 Transformation과 비교하세요. 실제로 실행한 테스트와 서비스·환경 부재로 실행하지 못한 테스트를 확인합니다. 갱신 후 설계를 다시 읽어 확인하도록 요청하세요.

아래 진행 메시지는 에이전트가 검증 결과를 보고하고, 실행 조율의 빈틈을 발견해 Beyond Entity를 수정한 뒤 계약 일치를 확인하려는 사례입니다. 메시지는 작업 흐름의 예시이며, 여기서 해당 결과를 독립적으로 검증한 것은 아닙니다.

<a href="../assets/screenshots/codex_comment.png"><img src="../assets/screenshots/codex_comment.png" alt="구현 검증, 실행 조율의 누락, 설계 재확인을 설명하는 에이전트 진행 보고" width="720"></a>

*에이전트 보고에서 구체적인 설계 변경과 검증 내용을 확인하세요.*

소스 코드와 실제 실행 화면이 포함된 구현 예시는 [Table Q by Codex](../samples/table-q/README.md)를 참고하세요.

<a id="step-8"></a>

## 8. 코드 변경을 Beyond Entity에 반영하기

요구사항이나 코드가 바뀌면 설계를 다시 확인하세요. 코드와의 차이를 모두 새로운 설계 규칙으로 바꾸어서는 안 됩니다. 차이는 버그, 의도한 변경, 미결정 사항일 수 있습니다.

> [파일 또는 Commit]의 변경을 최신 Beyond Entity 설계와 비교해줘. 의도한 동작 변경, 구현 결함, 미결정 사항으로 차이를 분류해줘. 의도한 변경은 MCP로 관련 Transformation, 계약, 관계, 아키텍처 문서에 반영하고 다른 사람이나 에이전트의 무관한 수정은 보존해줘. 갱신한 설계를 코드와 비교해 검증하고, 이유와 검증 내용, 남은 문제를 Checkpoint로 기록해줘.

**확인:** 변경된 Transformation을 살펴보고 관련 Attribute를 추적한 뒤 새 Checkpoint를 읽으세요. 갱신한 상태가 실제 검증 내용과 일치하는지 확인합니다. 앱에 **Changed by MCP**가 표시되면 최신 상태를 불러온 뒤 리뷰하세요.

<a id="step-9"></a>

## 9. 다른 에이전트나 팀원과 작업 이어가기

새 작업 세션은 이전 대화에만 의존하지 말고 현재 맥락을 복구하는 것부터 시작하세요.

> MCP로 [Beyond Entity 프로젝트]를 열어줘. 최신 Checkpoint와 관련 문서, [작업]에 필요한 현재 설계를 읽어줘. 현재 코드와 마지막 기록 이후의 변경을 확인하되 다른 에이전트나 사람의 변경도 포함해줘. 수정하기 전에 완료된 일, 해결되지 않은 차이, 다음 단계를 요약해줘. Checkpoint만으로 변경 내용을 판단하기 어렵다면 그 점을 알려줘.

Checkpoint는 의도를 복구하는 데 도움이 되지만 현재 설계와 코드 확인을 대신하지는 않습니다. 세션을 마칠 때는 다음 작업자에게 필요한 결정 사항과 근거를 기록하세요.

---

[README로 돌아가기](../README.md) · [설치 가이드](../INSTALL.md) · [샘플 프로젝트](../samples/README.md)
