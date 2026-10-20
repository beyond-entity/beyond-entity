# be-parser

[English](README.md) | **한국어** | [日本語](README_ja.md)

Java/Spring 코드베이스를 위한 정적 분석기입니다. 소스를 빌드하거나 실행하지 않고 읽어서 다음을 합니다.

1. **아키텍처 모델**을 만듭니다. 모듈, processor(controller·service·repository·listener 등), endpoint, 데이터 저장소, entity와 attribute, 그리고 그 사이의 **데이터 lineage**입니다.
2. 내장 규칙 카탈로그로 **보안 사전점검**을 합니다. 규칙은 CWE, OWASP Top 10, 행정안전부 소프트웨어 보안약점 진단가이드에 대응됩니다.
3. 선택적으로 두 결과를 로컬 MCP 서버를 통해 **Beyond Entity(BE) 프로젝트로 보냅니다**([Beyond Entity 연동](#beyond-entity-연동) 참고).

모델은 다음 파일로 출력됩니다.

- `architecture-facts.json`: 소스 위치가 붙은, 라이브러리 중립적인 fact.
- `be-plan.json`: BE가 저장할 형태의 모델.
- Markdown 보고서.

1·2단계는 완전히 오프라인에서 동작합니다. Beyond Entity 설치는 3단계에만 필요합니다.

> 상태: `0.1.0-SNAPSHOT`, 개발 진행 중입니다. 출력 형식은 바뀔 수 있습니다.

---

## 목차

- [분석 대상](#분석-대상)
- [빠른 시작](#빠른-시작)
- [명령](#명령)
- [출력 파일](#출력-파일)
- [Beyond Entity 연동](#beyond-entity-연동)
- [설정](#설정)
- [보고서 언어](#보고서-언어)
- [보안 규칙 카탈로그](#보안-규칙-카탈로그)
- [동작 방식](#동작-방식)
- [한계](#한계)
- [패키지 구성](#패키지-구성)

이 폴더는 바로 실행할 수 있는 패키지입니다. Java 21 이상만 있으면 됩니다. [INSTALL.md](INSTALL.md)를 보세요. 라이선스: MIT(이 저장소 최상위의 `LICENSE`).

---

## 분석 대상

| 영역 | 지원 범위 |
|---|---|
| 빌드 구조 | Maven·Gradle 멀티 모듈 프로젝트. 각 모듈을 자기 소스 루트로 분석. 따로 배포되는 Boot 서비스로 이루어진 리액터는 서비스마다 모델이 되고, 여러 서비스가 쓰는 라이브러리는 자기 모델이 되어 서비스의 호출이 그곳으로 이어짐 |
| Web | Spring MVC / WebFlux controller, request mapping, parameter와 body, Spring Cloud Gateway route |
| Component | `@Service`, `@Component`, `@Repository`, XML bean 정의(eGovFrame 방식), 생성자·필드·setter 주입, interface → 구현체 해석, profile·조건부 bean |
| 데이터 접근 | JPA / Spring Data(파생 쿼리, `@Query`, R2DBC 포함), MyBatis mapper XML(동적 SQL·XML reload 포함), eGovFrame DAO, Spring Data Redis / MongoDB / Elasticsearch repository, Spring Session JDBC 테이블. 데이터소스는 Spring Boot·Druid·Hikari·dynamic-datasource 키에서 읽음(p6spy/log4jdbc 래퍼 포함). 스키마 스크립트, Flyway, Liquibase, 저장소 안 어디에 있든 DDL 스크립트 |
| 메시징 | Kafka(Kafka Streams 토폴로지 포함), RabbitMQ(exchange, queue, binding, dead-letter 경로), Spring Cloud Stream, JMS, Amazon SQS. JMS/SQS queue는 그것을 쓰는 애플리케이션 모델의 entity이고, 여러 서비스가 쓰면 공유 모델 "Message queues"의 entity |
| 라이브러리 | 카탈로그 기반 port: Spring AI, LangChain4j, eGovFrame core, Spring Data |
| Lineage | argument, result, handoff(한 호출의 결과 값이 다른 호출로 전달됨), composed, store lineage. 객체 port 안의 필드 단위(`creditCard.cardNumber`)까지. 메시지, 로그, 세션 속성 포함. 조회 키는 조회된 데이터와 구분 |
| 보안 | 규칙 35개(injection, 암호화, 비밀값, 인가, CSRF, PII 저장·로그, 상태를 바꾸는 GET, 인증 없는 쓰기 등), PII 컬럼 분류와 보호 수준 |

분석기는 소스 루트만으로 동작합니다. 대상의 제3자 classpath가 필요 없으므로, 의존 라이브러리를 받을 수 없는 폐쇄망에서도 쓸 수 있습니다.

---

## 빠른 시작

```bash
# 1. be-parser 명령을 PATH에 등록 (Java 21+). 또는 이 폴더에서 bin/be-parser 실행
./install.sh                         # → ~/.local/bin/be-parser

# 2a. 웹 화면: 폴더와 Beyond Entity 프로젝트를 고르고 Run
be-parser serve

# 2b. 또는 명령 하나로: 분석, 보고서 작성, Beyond Entity 프로젝트로 전송
be-parser projects                                   # 프로젝트 ID 찾기
be-parser run ~/src/spring-app --project PxxxxxxxxxxxX
be-parser run ~/src/spring-app --no-send             # 분석과 보고서만, Beyond Entity 없이
```

`run`은 모든 결과를 `~/.be-parser/out/<저장소>/`에 씁니다: `architecture-facts.json`, `be-plan.json`, `analysis-report.md`, `security-report.md`, `pii-flow.md`.

`serve`는 `127.0.0.1`에서만 열리는 웹 화면입니다. **Run** 탭에서는 폴더를 고르고 그 폴더의 옵션을 고쳐 기억시킨 뒤 실행하고, 실행 로그와 보고서를 바로 봅니다. 대상 프로젝트는 Beyond Entity 프로젝트 목록에서 고르거나, "+ New project…"로 이름과 `.bemdl` 파일명을 입력해 새로 만듭니다(기본 `<폴더>/<폴더>.bemdl`). **Settings** 탭에서는 모든 설정을 설명·기본값과 함께 보고 사용자 기본값으로 저장합니다(BE 연결 테스트 포함). 새 프로젝트는 CLI로도 만들 수 있습니다: `be-parser projects create <file.bemdl> [--name <이름>]`. `be-parser config`와 같은 파일을 고칩니다([설정](#설정)). API 호출마다 시작할 때 만든 무작위 토큰이 필요하며, 토큰은 출력·자동으로 열리는 URL에 들어 있습니다. 포트와 토큰은 `~/.be-parser/serve.json`에 저장되므로 다른 로컬 도구(예: Beyond Entity 데스크톱 앱)가 `http://127.0.0.1:<port>/?token=<token>&project=<프로젝트 ID>`로 특정 프로젝트 화면을 열 수 있습니다.

예: [spring-petclinic](https://github.com/spring-projects/spring-petclinic)은 몇 초 만에 보안 finding 16건과, 데이터베이스 프로필 3개(MySQL, PostgreSQL, H2) 각각의 테이블 7개가 나옵니다.

---

## 명령

모든 명령은 `be-parser`(`bin/be-parser`, Windows는 `bin\be-parser.cmd`)의 하위 명령이며, `lib/be-extractor.jar`를 실행합니다. `java -jar lib/be-extractor.jar <명령>`도 같습니다. `run`(분석+보고서+전송), `projects`(프로젝트 목록), `serve`(웹 화면)는 [빠른 시작](#빠른-시작)을 보세요.

### `analyze`: 소스 → fact

```
analyze <repo-root> [-o architecture-facts.json] [--commit <sha>] [--exclude <glob>]...
        [--report <base>] [--schema model_creation_schema.json] [--no-report] [--catalog <dir>] [--lang en|ko|ja]
```

| 옵션 | 의미 |
|---|---|
| `-o` | 출력 fact 파일(기본 `architecture-facts.json`) |
| `--commit` | 기록할 소스 커밋. 생략하면 저장소의 git 정보에서 branch·dirty 상태와 함께 읽음 |
| `--exclude` | 건너뛸 경로 glob(여러 번 가능). 예: `--exclude '**/generated/**'` |
| `--report` | 분석 보고서 기본 이름(`<base>.md`, `<base>.json`). 기본은 fact 옆의 `analysis-report` |
| `--no-report` | 분석 보고서를 만들지 않음 |
| `--schema` | 보고서에서 데이터 타입을 검증할 BE 저장 타입 카탈로그 |
| `--catalog` | 외부 보안 카탈로그 디렉터리(기본: 내장 카탈로그) |
| `--lang` | 보고서 언어: `en`(기본), `ko`, `ja`([보고서 언어](#보고서-언어) 참고) |

### `plan`: fact → BE 모델 (오프라인)

```
plan <architecture-facts.json> [-o be-plan.json] [--include-general-modules]
```

BE에 연결하지 않고, `send`가 쓸 모델·processor·entity·lineage를 그대로 만듭니다. `--include-general-modules`를 주면 Spring 역할이 없는 모듈(일반 라이브러리)도 남깁니다.

### `report`, `security-report`, `pii-report`

```
report           <architecture-facts.json> [-o <base>] [--schema model_creation_schema.json] [--catalog <dir>] [--lang en|ko|ja]
security-report  <architecture-facts.json> [-o security-report.md] [--catalog <dir>] [--lang en|ko|ja]
pii-report       <architecture-facts.json> [-o pii-flow.md] [--lang en|ko|ja]
```

- `report`는 기존 fact로 분석 보고서를 다시 만듭니다.
- `security-report`는 finding을 규칙, CWE·표준 대응, 위치, 근거와 함께 나열합니다.
- `pii-report`는 PII 컬럼, 보호 방식(hash, 암호화), 그 컬럼을 수집·노출하는 endpoint를 나열합니다.

### `validate`

```
validate <architecture-facts.json> <model_creation_schema.json>
```

plan이 쓸 모든 데이터 타입이 BE 저장 타입 카탈로그에서 허용되는지 확인합니다.

### `security-catalog`

```
security-catalog list|validate [--catalog <dir>] [--lang en|ko|ja]
security-catalog import-csv <items.csv> --id <standard-id> --version <v> --title <title>
        [--published <date>] [--source <url>] --catalog <dir> [--activate]
```

규칙 카탈로그를 나열하거나 검증합니다. 새 표준 버전(예: 더 새로운 CWE 목록)을 외부 카탈로그 디렉터리로 가져올 수도 있습니다.

### `send`: fact → Beyond Entity

```
send <architecture-facts.json> [--config be-extractor.properties] [--dry-run] [--include-general-modules]
     [--allow-mass-resolve]
```

설정에 지정한 BE 프로젝트에 모델, lineage, 보안 finding을 씁니다. `--dry-run`은 BE에 연결해 읽기만 하고 아무것도 쓰지 않습니다. [Beyond Entity 연동](#beyond-entity-연동)을 보세요.

---

## 출력 파일

| 파일 | 만드는 명령 | 내용 |
|---|---|---|
| `architecture-facts.json` | `analyze` | fact(`MODULE`, `PROCESSOR`, `ENDPOINT`, `CALL`, `DATA_ENTITY`, `DATA_ATTRIBUTE`, `STORE_ACCESS`, `SECURITY_FINDING`, `UNRESOLVED` 등)와 소스 파일·행·근거. 소스 저장소, branch, commit, extractor 버전 |
| `analysis-report.md` / `.json` | `analyze`, `report` | fact 유형별 개수, 데이터 저장소, 미해결 항목, 검증 결과 |
| `be-plan.json` | `plan` | 모델 → processor(입출력, endpoint, 호출 의존) → entity/attribute, SQL 형태의 transformation으로 표현한 lineage |
| `security-report.md` | `security-report` | 심각도별 finding과 CWE / OWASP / 행안부 대응 |
| `pii-flow.md` | `pii-report` | PII 컬럼, 보호 수준, 수집·노출 endpoint |
| `be-sync-report.json` | `send` | 생성·수정·삭제된 객체, 실패, 보안 scan 결과(`--dry-run`이면 `be-sync-dry-run.json`) |

Lineage는 BE 객체에 대한 SQL로 표현합니다. 예:

```sql
-- parser: EgovSysHistoryServiceImpl.selectSysHistory → EgovFileMngServiceImpl.deleteAllFileInf (handoff)
INSERT INTO {{EgovFileMngServiceImpl}} (atchFileId) SELECT p.OUTPUT.atchFileId FROM {{EgovSysHistoryServiceImpl}} p
```

---

## Beyond Entity 연동

Beyond Entity는 데이터·아키텍처 모델링 도구입니다. `send`는 Beyond Entity의 **로컬 데스크톱 MCP 서버**와 stdio로 통신합니다. 대상 프로젝트는 MCP 서버가 직접 열기 때문에, 이 저장소에는 인증 정보가 없습니다. JMS/SQS queue entity에는 데스크톱 MCP 3.2.38 이상이 필요합니다. `send`는 서버가 제공하는 정의로 plan을 검사합니다.

`send`는 다음 순서로 동작합니다.

1. MCP 사용 가이드를 읽고, plan을 BE의 현재 정의와 대조합니다(schema check).
2. 코드 분석 run을 시작합니다(프로젝트 run + 노드 run).
3. 모델, processor, entity, attribute, transformation을 생성·수정·삭제합니다. 차이만 씁니다.
4. 보안 scan을 분석 run과 함께 원자적으로 기록합니다. 근거별(소스 fact, 호출 도달, plan 유래)로 나눕니다. finding이 200건을 넘는 규칙은 정확한 소스 파일 범위로 나눈 complete scan으로 기록합니다.
5. run을 마치고, 소스 commit과 extractor 버전을 담은 checkpoint를 남깁니다.

안전장치:

- **`protected.projects`**(개발용 설정): 이 목록의 프로젝트에는 쓰지 않습니다. `target.project`를 실수로 그중 하나로 지정해도 마찬가지입니다. 여러 프로젝트를 일괄로 돌릴 때를 위한 것이며, 대상을 직접 고르는 실행에는 필요 없습니다.
- **프로젝트 잠금 재시도**: 프로젝트가 잠겨 있으면(데스크톱 앱이나 검토자가 작업 중) `mcp.lock.retry_seconds`만큼 기다렸다가 다시 시도합니다.
- **대량 해결 방지**: 한 번의 전송이 열린 finding의 비정상적으로 큰 비율을 해결 처리하게 되면, `--allow-mass-resolve` 없이는 멈춥니다.
- 쓰기가 하나라도 실패하거나 보안 scan을 기록하지 못하면 `send`는 0이 아닌 코드로 끝납니다.

설정 파일은 없어도 됩니다. 대상은 `be-parser serve`에서 고르거나 `run`에 `--project`로 줍니다. 저장소에 설정을 두려면 그곳의 `be-extractor.properties`에 원하는 [설정](#설정)을 적습니다. 예:

```properties
target.project=PxxxxxxxxxxxX
report.language=ko
analysis.exclude=**/generated/**
```

모든 옵션은 [`be-extractor.example.properties`](be-extractor.example.properties)에 있습니다.

```bash
be-parser run ~/src/spring-app --project PxxxxxxxxxxxX --dry-run
be-parser run ~/src/spring-app --project PxxxxxxxxxxxX
be-parser send out/architecture-facts.json --config be-extractor.properties   # existing facts, settings from a file
```

---

## 설정

실행 옵션은 모두 설정입니다. 각 값은 다음 층에서 정해지며, 뒤의 층이 앞의 층보다 우선합니다:

1. 내장 기본값;
2. **사용자 기본값**: `~/.be-parser/config.properties`. `be-parser config set` 또는 웹 화면의 Settings 탭으로 수정;
3. **설정 파일**: `--config <file>`, 없으면 작업 폴더의 `be-extractor.properties`(선택. 저장소에서 설정을 공유할 때);
4. **폴더별 옵션**: `~/.be-parser/sources.json`. 분석한 폴더마다 기억(`run --save`, `config set --source`, 웹 Run 탭);
5. **명령행 옵션**.

상대 경로는 그 값이 들어 있는 파일의 폴더를 기준으로, `~`는 홈 폴더로 해석합니다. `be-parser config`가 각 값과 그 출처를 보여줍니다. 설정 위치를 `~/.be-parser`가 아닌 곳으로 하려면 `BE_PARSER_HOME`을 지정합니다.

| 키 | 기본값 | 의미 |
|---|---|---|
| `target.project` * | – | 분석 결과를 쓸 Beyond Entity 프로젝트. 비우면 분석만 |
| `report.language` * | `en` | 보고서와 BE에 쓰는 finding 문구의 언어: `en`, `ko`, `ja` |
| `analysis.exclude` * | – | 건너뛸 파일·폴더의 glob(쉼표 구분. 웹 화면에서는 한 줄에 하나) |
| `extract.include_general_modules` * | `false` | Spring 역할이 없는 모듈(일반 라이브러리)도 모델에 포함 |
| `analysis.repository_key` * | 폴더 이름 | 여러 run에서 소스 저장소를 식별하는 키 |
| `security.findings.branch` * | – | 보안 finding과 함께 기록할 branch |
| `output.dir` | `~/.be-parser/out` | `run`이 facts·plan·보고서를 쓰는 곳(저장소마다 하위 폴더) |
| `java.heap` | `3g` | 분석의 최대 heap(`BE_PARSER_HEAP`이 우선) |
| `security.catalog.dir` | 내장 | 외부 보안 카탈로그 디렉터리 |
| `security.report.enabled` / `security.report.file` | `true` / `security-check-<repo>.md` | 보안 보고서를 BE 문서로 올림 |
| `pii.report.enabled` / `pii.report.file` | `true` / `pii-flow-<repo>.md` | PII 흐름 보고서를 BE 문서로 올림 |
| `checkpoint.actor` | `be-code-parser` | checkpoint와 분석 run에 남는 작성자 이름 |
| `implementation.status.enabled` | `true` | 생성한 객체에 구현 상태도 기록 |
| `be.schema` | – | 쓰기 전에 plan을 대조할 BE 저장 타입 카탈로그(`model_creation_schema.json`) |
| `security.findings.enabled` | `true` | 보안 finding 전송 |
| `security.findings.refresh` | `true` | 다시 검출된 finding에 이번 run의 위치·코드 조각·메시지를 반영(사람이 정한 상태는 유지) |
| `security.findings.mass_resolve.min` / `.ratio` | `10` / `0.3` | 대량 해결 방지 기준 |
| `mcp.command` | `/usr/local/bin/beyond-entity-mcp` | Beyond Entity MCP 서버 실행 파일(`BE_MCP_COMMAND`가 기본값을 대신함) |
| `mcp.timeout.seconds` | `120` | MCP 호출당 timeout |
| `mcp.batch_mode` | `true` | 전송 중 호출 사이에 프로젝트 DB를 열어 둠 |
| `mcp.lock.retry_seconds` / `mcp.lock.max_retries` | `30` / `20` | 프로젝트가 잠겨 있을 때 기다렸다 재시도 |
| `protected.projects` (개발용) | – | 파서 개발 중 여러 프로젝트를 한꺼번에 돌릴 때, 대상이 잘못 지정돼도 절대 쓰지 않을 프로젝트 ID. 웹 화면에는 없으며, 대상을 직접 고르는 실행에는 필요 없음 |

\* 폴더별 옵션으로도 지정 가능.

---

## 보고서 언어

보안 보고서, PII 흐름 보고서, BE에 쓰는 finding의 제목·설명·조치는 **영어(기본), 한국어, 일본어**로 만들 수 있습니다.

| 대상 | 방법 |
|---|---|
| `send` | 설정 파일에 `report.language=ko` |
| `security-report`, `pii-report`, `report`, `analyze`, `security-catalog list` | `--lang ko` |
| 모든 명령 | 환경 변수 `BE_REPORT_LANGUAGE=ko`(기본값. `--lang`이 우선) |

허용 값: `en`, `ko`, `ja`(`english`, `korean`/`kr`, `japanese`/`jp`도 가능).

언어에 따라 바뀌는 것:

- 보고서 제목, 표, 설명;
- 규칙 제목, 설명, 조치;
- 표준 제목, 항목 이름, 분류(행안부 가이드의 영어·일본어 이름. OWASP·CWE는 공식 영어 이름을 유지).

코드를 인용하는 finding 메시지(클래스, 메서드, 경로, SQL)와 개발자용 분석 보고서(`analysis-report.md`)는 영어로 남습니다. 기존 BE 프로젝트에서 언어를 바꾸면, 다음 `send`에서 보고서 문서가 새 언어로 다시 쓰이고 새 finding은 그 언어의 제목을 받습니다. 이미 있는 finding의 제목까지 바뀌는지는 BE의 갱신 동작(`security.findings.refresh`)에 달려 있습니다. 사람이 정한 상태와 판단은 어느 경우에도 유지됩니다.

---

## 보안 규칙 카탈로그

카탈로그는 `lib/be-extractor.jar` 안(`security-catalog/`)에 들어 있습니다.

- `rules.json`: 규칙 35개. 각 규칙에 검출 방식, 심각도와 신뢰도, CWE, 표준 대응이 있습니다. 문구는 영어이고, 한국어·일본어 번역이 `i18n`에 있습니다.
- `attribute-security.json`: PII 데이터 유형과 암호화 수준.
- `standards/`: 내장 표준 버전. CWE 4.20, CWE Top 25(2024, 2025), OWASP Top 10(2021, 2025), 행정안전부 소프트웨어 보안약점 진단가이드(2021, 49개)입니다.

표준은 보고서를 만들 때 해석되므로, 카탈로그를 갱신하면 다시 분석하지 않아도 반영됩니다. 다시 빌드하지 않고 새 표준을 쓰려면, `security-catalog import-csv`로 만든 디렉터리를 `--catalog`(또는 `security.catalog.dir`)로 지정하세요.

Finding은 판정이 아니라 **사전점검**입니다. 각 finding에 근거와 신뢰도가 붙습니다. 호출 도달에 의존하는 규칙은 경로를 따라가지 못하면 추측하지 않고 그 사실을 보고합니다.

---

## 동작 방식

```
소스 트리 ──► extractor-spring ──► architecture-facts.json ──► extractor-be ──► be-plan.json ──► send (MCP) ──► Beyond Entity
              (JavaParser AST,       (라이브러리 중립 fact,         (BeMapper, PortMapper,
               XML, YAML, 카탈로그)   근거, 미해결)                  LineageComposer, SecuritySync)
```

- **extractor-core**: fact 모델, fact JSON, 보안 카탈로그.
- **extractor-spring**: 모듈 탐색, JavaParser AST 기반 Java/XML/YAML 분석, classpath 없는 타입 해석, 호출 그래프, guard 분석, 보안 스캐너.
- **extractor-be**: fact를 BE 객체로 대응, port와 lineage 도출, 여러 단계 lineage 합성, MCP로 차이 동기화.
- **extractor-cli**: 명령행, 보고서, 분석 run, 전송.

설계 원칙:

- 분석기가 해석하지 못한 것은 이유와 함께 `UNRESOLVED` fact가 됩니다. 조용히 버리지 않습니다.
- 호출자 데이터를 옮기지 않는 호출 관계는 데이터 lineage와 분리해 processor `call_dependencies`에 이유(`handoff`, `no_mapping`, `no_caller_value`)와 함께 남깁니다.
- 조회 키로만 쓰인 값(`findById(id)`)은 조회된 객체로 가는 lineage가 아닙니다. 조회된 객체의 속성은 조회 결과에서 오는 **handoff**가 됩니다.


---

## 한계

- Reflection, 동적 bean 등록, 런타임에 생성되는 proxy는 따라가지 않습니다.
- 타입은 소스에서만 얻습니다. 카탈로그에 없는 라이브러리 타입은 내부를 모르는 타입으로 다룹니다.
- Lineage는 객체 port 안으로 한 단계(`creditCard.cardNumber`)까지 갑니다. 더 깊이 읽은 값(`request.getA().getB().getC()`)은 가장 가까운 port에 대응됩니다. 같은 쪽 port와 이름이 같은 중첩 필드는 BE에서 모호해지므로 중첩하지 않습니다.
- RabbitMQ 토폴로지는 `@Bean` Exchange/Queue/Binding 정의에서 읽습니다. 다른 곳(설정 파일, 관리 화면)에서 선언한 토폴로지는 읽지 않습니다.
- Kotlin, Groovy, Spring이 아닌 프레임워크는 분석하지 않습니다.

---

## 패키지 구성

```
bin/be-parser                     실행 스크립트 (macOS, Linux)
bin/be-parser.cmd                 실행 스크립트 (Windows)
lib/be-extractor.jar              프로그램
install.sh                        선택: be-parser를 PATH에 등록 (기본 ~/.local)
be-extractor.example.properties   모든 설정의 설정 파일 예시
README.md, README_ko.md, README_ja.md, INSTALL.md, SECURITY.md
```

취약점 신고는 [SECURITY.md](SECURITY.md)를 보세요.
