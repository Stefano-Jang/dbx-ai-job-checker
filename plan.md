# 고객 자가 구축형 Databricks AI Job Checker 계획

## 목표와 성공 기준

GitHub URL만 받은 고객이 소스 수정 없이 AWS Databricks 환경에 데모를 재현할 수 있게 한다.

- 고객은 저장소 clone 후 설치 wizard의 질문에 답하는 것만으로 진행한다.
- 관리자 권한이 필요한 단계에서는 wizard가 역할별 요청서를 자동 생성하고 정확히 멈춘다.
- 관리자 응답 후 `resume`으로 이어서 배포한다.
- 관리자 대기 시간을 제외하고 60분 이내 구축을 목표로 한다.
- README, 상세 가이드, App 내 튜토리얼은 동일한 원본 문서를 사용해 내용 불일치를 방지한다.

## 고객 설치 경험

루트의 `setup.sh`를 단일 진입점으로 제공한다.

```bash
git clone https://github.com/Stefano-Jang/dbx-ai-job-checker.git
cd dbx-ai-job-checker

./setup.sh doctor
./setup.sh configure
./setup.sh deploy
```

지원 명령:

- `doctor`: CLI, Python, Node, 인증, AWS workspace 기능 검사
- `configure`: profile, warehouse, catalog, model 등을 선택하는 대화형 설정
- `admin-pack`: Account/Workspace/UC 관리자 요청서 생성
- `deploy`: 현재 가능한 단계까지 멱등 배포
- `resume`: 관리자 작업 완료 후 중단 지점부터 재개
- `verify`: 권한과 전체 데이터 흐름 검증
- `demo <scenario>`: 정상 또는 오류 시나리오 실행
- `status`: 현재 진행 단계와 다음 작업 표시

`.local/config.json`과 `.local/setup-state.json`에 선택값과 진행 상태를 저장하되 Git에서 제외한다. secret과 token은 로컬 파일에 저장하지 않고 Databricks secret resource로만 관리한다.

## 문서 체계

### README

README는 짧은 랜딩 페이지로 유지한다.

- 프로젝트가 보여주는 내용
- 5분 사전 준비
- 세 개의 시작 명령
- 예상 설치 시간
- 필요한 관리자 역할
- 지원 환경과 알려진 제한
- 상세 고객 가이드 링크
- 데모 화면과 아키텍처 미리보기

### 고객 가이드

`docs/`에 번호가 있는 단계별 가이드를 제공한다.

1. **시작 전 확인**
   - 지원 환경: AWS 우선
   - Databricks CLI 1.11 이상, Python/Node 요구사항
   - 필요한 역할과 예상 시간
   - 비용 및 생성 리소스
2. **아키텍처 이해**
   - Lakeflow Jobs → 중앙 Run Watcher → Run Inspector → UC AI Gateway → Delta → App
   - Mermaid 다이어그램과 용어 설명
3. **Profile과 설정**
   - profile을 자동 선택하지 않고 후보 URL을 표시한 뒤 고객이 선택
   - warehouse, catalog, schema, model 선택 방법
   - 각 질문의 추천값과 영향
4. **어드민 요청**
   - Account Admin, Workspace Admin, Metastore/UC Admin별 요청서
   - 필요한 이유, 권한, 입력값, 반환값, 검증법
5. **배포**
   - wizard 화면과 예상 출력
   - 중단·재개 방법
   - 단계별 성공 판정
6. **검증과 데모**
   - 정상, stale, incomplete, semantic bug, runtime failure 실행
   - 화면에서 확인할 항목
7. **보안과 거버넌스**
   - 최소 권한, secret 처리, system table, AI Gateway payload 정책
8. **문제 해결**
   - 증상→원인→확인 명령→해결→문의 역할 형식
9. **업그레이드와 제거**
   - 버전 호환성, 재배포, 백업 대상
   - 삭제되는 리소스와 보존되는 Delta 데이터
   - 명시적 확인 없이는 destroy를 실행하지 않음

모든 단계에는 다음 블록을 넣는다.

- 담당 역할
- 예상 소요 시간
- 실행할 명령
- 예상 출력
- 완료 확인
- 실패 시 문의 대상
- 다음 단계

스크린샷은 실제 AWS 검증 환경에서 캡처하고, 값이 달라지는 영역은 명확히 표시한다.

## 역할별 관리자 요청 자동화

`./setup.sh admin-pack`은 현재 workspace URL, principal, App URL 등을 채운 요청서를 `.local/admin-requests/`에 생성한다.

### Account Admin 요청

- Databricks Apps 조직 기능 활성화
- 대상 workspace 명시
- 완료 증빙과 검증 방법 포함

### Workspace Admin 요청

- 중앙 watcher 및 분석 Job 서비스 주체에 감시 대상 Job의 `CAN_VIEW` 권한 부여
- 분석 대상 Notebook과 workspace source에 `CAN_READ` 권한 부여
- Databricks Apps가 비활성화된 workspace에서는 Apps preview 활성화
- 적용한 principal, Job 범위와 권한 검증 결과 반환

고객이 Workspace Admin이면 wizard가 변경 내용을 먼저 보여주고 명시적 확인 후 권한을 적용한다. 권한이 없으면 선택한 Job ID가 포함된 요청서를 생성하고 중단한다.

### Metastore/UC Admin 요청

- `system.lakeflow`, `system.ai_gateway` 활성 상태 확인
- 분석 Job/App principal에 table 단위 최소 권한 부여
- `ai_job_checker` catalog/schema 생성 권한
- UC model service용 `CREATE SERVICE`, `EXECUTE`
- 적용된 grants와 검증 결과 반환

wizard는 관리자 응답값을 검사한 후에만 다음 단계로 진행한다.

## 구현 아키텍처

### Demo Jobs

- `demo.customer_events`에서 `demo.customer_ltv` 생성
- 시나리오: `normal`, `stale`, `incomplete`, `semantic_bug`, `runtime_failure`
- 원본 Job에는 webhook, callback 또는 분석용 task를 추가하지 않는다.
- 중앙 Run Watcher가 선택된 Job의 신규 terminal run을 탐지해 분석 Job을 실행한다.
- 분석 Job은 `run_id` 기준 멱등 처리한다.

### 중앙 Run Watcher

- 1~2분 주기의 단일 Lakeflow Job으로 배포한다.
- `ops.watched_jobs`에서 `enabled = true`인 Job ID만 Jobs API로 조회한다.
- Jobs API를 신규 run의 빠른 탐지에 사용하고 `system.lakeflow`를 누락 보정과 과거 기준선에 사용한다.
- Job별 `(last_end_time, last_run_id)` watermark를 `ops.watcher_state`에 저장한다.
- 신규 terminal run을 `ops.analysis_requests`에 MERGE한 뒤 중앙 분석 Job을 `run_id` 파라미터로 실행한다.
- watcher와 분석 Job 자체는 reserved Job으로 관리하며 선택 또는 분석할 수 없게 한다.
- API/system table 지연, 재시도와 watcher 재실행에도 동일 run이 중복 분석되지 않아야 한다.

### Watched Jobs Registry

`ops.watched_jobs`를 감시 대상의 단일 원본으로 사용한다.

- 필드: `job_id`, `job_name`, `enabled`, `policy_version`, `output_table_overrides`, `added_by`, `added_at`, `updated_at`
- 최초 배포 시 감시 대상은 비어 있으며 사용자가 명시적으로 선택해야 한다.
- Job 등록 시 Jobs API `get`과 source 접근을 검사한다.
- 권한이 부족하면 활성화하지 않고 `NEEDS_PERMISSION` 상태와 필요한 `CAN_VIEW`/`CAN_READ` 요청을 표시한다.
- 출력 테이블은 UC lineage로 자동 발견하되, lineage 지연이나 미지원 작업을 위해 선택적으로 fully-qualified table override를 입력할 수 있다.
- 비활성화는 신규 run 탐지만 중단하며 기존 리포트는 삭제하지 않는다.
- 재활성화 기본값은 활성화 이후 run만 처리하고, 사용자가 요청할 때만 최근 24시간 또는 지정 run을 backfill한다.

### System Tables

- 사용 테이블:
  - `system.lakeflow.jobs`
  - `system.lakeflow.job_tasks`
  - `system.lakeflow.job_run_timeline`
  - `system.lakeflow.job_task_run_timeline`
- period row를 `job_id, run_id`별로 집계한다.
- 최근 terminal run 20건의 중앙값과 MAD로 이상을 판단한다.
- 현재 run은 Jobs API로 보강해 system table 반영 지연을 처리한다.

### Unity Catalog AI Gateway

- Model service: `ai_job_checker.ops.job_analysis_llm`
- Destination: `system.ai.databricks-claude-sonnet-4-6`
- usage tracking, inference table, PII·safety guardrail 활성화
- `system.ai_gateway.usage`에서 token, latency, status, routing을 수집
- 원본 전체 데이터 대신 schema, 집계, 제한된 표본, 검사 결과와 Notebook source만 LLM에 전달

### 저장 테이블

- `ops.analysis_requests`
- `ops.watched_jobs`
- `ops.watcher_state`
- `ops.run_reports`
- `ops.quality_metrics`
- `ops.source_snapshots`
- `ops.llm_invocations`
- `ops.analysis_policy_versions`
- `ops.app_settings`

### 분석 기준의 단일 원본

분석 로직과 App 설명이 달라지지 않도록 versioned `config/analysis-policy.yml`을 단일 원본으로 사용한다. 분석 Job은 이 파일을 실행 시점에 읽고, App은 같은 내용을 사람이 이해하기 쉬운 형태로 표시한다.

정책에는 다음을 명시한다.

- 실행 이상 기준
  - 현재 실행을 제외한 최근 성공 20건 사용
  - 최소 이력 5건
  - 중앙값과 MAD 기반 이상 판정
  - setup, queue, execution, total duration을 분리 평가
- 데이터 품질 기준
  - 고객 completeness 99% 이상
  - 데이터 freshness 1일 이내
  - `customer_id` null 및 중복 불가
  - LTV 음수 불가
  - 입력 고객과 산출 고객 수의 일관성
- 의미론 기준
  - LTV는 고객별 순매출 합계
  - 환불과 취소 금액을 제외하지 않고 순매출에 반영
  - 미래 거래나 분석 기준일 이후 데이터 사용 금지
  - Notebook 구현과 선언된 비즈니스 정의의 일치 여부 확인
- 점수 가중치와 severity 경계
- LLM model, prompt version, 입력 데이터 범위와 sampling 제한
- LLM 지시문
  - 제공된 근거만으로 판단
  - 추정과 확인된 사실을 구분
  - 발견마다 source/metric 근거 인용
  - 문제가 없으면 억지로 문제를 생성하지 않음
  - 수정안은 설명과 unified diff로 제시

각 분석 실행은 `policy_version`, policy hash와 당시의 policy snapshot을 `ops.run_reports`에 저장한다. 이후 정책이 변경되어도 과거 리포트가 어떤 기준으로 생성됐는지 재현할 수 있어야 한다.

### 다국어 정책

- App 기본 언어는 한국어(`ko`)이며 header에서 English(`en`)로 전환할 수 있다.
- 메뉴, 버튼, 상태, 도움말과 분석 기준 등 UI 문구는 locale resource로 관리하고 언어 전환 즉시 변경한다.
- 선택한 UI locale은 사용자 브라우저에 저장하되 최초 접속과 fallback은 한국어로 한다.
- watcher가 생성하는 신규 리포트의 기본 언어는 `ops.app_settings.default_report_locale`에 `ko` 또는 `en`으로 저장한다.
- 언어 전환 UI에서 “앞으로 생성되는 리포트 언어”도 함께 변경할 수 있게 하며, 변경 시점 이후 등록되는 `ops.analysis_requests`에 `report_locale`을 snapshot한다.
- 분석 Job은 `report_locale`을 LLM prompt의 `output_language`로 전달한다. verdict, severity, metric key 같은 기계 판독용 enum은 언어와 무관하게 고정하고 summary, evidence 설명과 수정 제안만 현지화한다.
- `ops.run_reports`에 `report_locale`을 저장한다. 기존 리포트는 생성 당시 언어 그대로 표시하고 자동 번역하거나 재생성하지 않는다.
- 기존 리포트를 다른 언어로 보고 싶으면 별도의 명시적 재분석을 실행해야 하며, 원본 리포트는 보존한다.
- Notebook source, SQL, JSON, unified diff와 table/column 이름은 번역하지 않는다.
- 날짜, 숫자와 단위는 UI locale에 맞게 표시하되 저장값은 locale-neutral 형식을 유지한다.

## App 화면

- header의 `한국어 | English` 언어 전환과 현재 신규 리포트 생성 언어 표시
- **Watched Jobs** 관리 화면
  - 접근 가능한 Lakeflow Job을 이름·ID·owner로 검색
  - checkbox/toggle로 감시 활성화 및 비활성화
  - 등록 전 Job/Notebook 권한 preflight와 필요한 관리자 요청 표시
  - Job별 분석 policy와 출력 테이블 자동 발견/override 설정
  - 마지막 탐지 시각, 마지막 분석 run, watcher 상태 표시
  - reserved watcher/분석 Job은 선택 불가로 표시
- 실행 목록과 상태·scenario·심각도 필터
- 각 리포트에 생성 언어 badge를 표시하고 UI 언어와 달라도 원문 그대로 렌더링
- 실행/task timeline과 평소 대비 편차
- completeness, freshness와 품질 검사
- 의미론적 분석과 근거
- Notebook 원본과 unified diff
- AI Gateway token, latency, routing, guardrail
- **분석 기준** 화면
  - 실행 이상, 데이터 품질, 의미론 기준을 자연어와 정확한 임계값으로 표시
  - 점수 구성과 severity 판정 기준 표시
  - LLM에 전달되는 지시문과 입력에 포함·제외되는 데이터 표시
  - 현재 policy/model/prompt 버전과 변경 시각 표시
- 실행 상세의 **이 실행에 사용된 기준** 탭
  - 해당 run의 policy snapshot과 hash
  - 각 기준의 측정값, 통과 여부와 판정 근거
  - 현재 정책과 과거 실행 정책이 다르면 변경 사항 표시
- 역할별 구축 튜토리얼과 관리자 요청 방법

`docs/tutorial/`을 App 빌드에서도 읽어 GitHub 문서와 App 튜토리얼을 단일 원본으로 유지한다.

## 친절한 자동화 원칙

- profile이나 리소스를 임의 선택하지 않고 추천값과 후보를 보여준다.
- 실행 전 생성·변경될 리소스를 요약하고 확인받는다.
- 모든 단계는 재실행 가능하고 이미 완료된 작업을 안전하게 건너뛴다.
- 실패하면 raw stack trace보다 원인, 해결 명령, 필요한 관리자 역할을 먼저 표시한다.
- 각 명령 종료 시 다음에 실행할 명령 하나를 출력한다.
- wizard가 생성한 환경별 값은 source에 하드코딩하지 않는다.
- Git 저장소에 Databricks host, token, password, 고객 데이터가 포함되지 않도록 CI에서 검사한다.
- 분석 기준을 변경할 때는 policy version 증가, schema 검증과 변경 사유 기록을 강제한다.

## 테스트와 품질 보증

- 신규 AWS workspace를 가정한 clean-room 설치 테스트
- 관리자 권한을 모두 가진 사용자와 역할이 분리된 사용자 흐름 모두 검증
- wizard 중단·재개·재실행 테스트
- system table 권한 부족과 감시 대상 미선택 상태 테스트
- 감시 대상 선택·해제, 권한 부족, reserved Job 차단과 per-Job watermark 테스트
- watcher 재시작 및 중복 run 탐지 시 분석 요청 멱등성 테스트
- 다섯 가지 Job scenario end-to-end 테스트
- AI Gateway 429, timeout, guardrail 차단 테스트
- 분석 Job이 사용한 policy snapshot과 App에 표시된 기준이 정확히 일치하는지 테스트
- 정책 버전 변경 후 기존 실행에는 과거 기준, 신규 실행에는 새 기준이 표시되는지 테스트
- 한국어 기본 UI, 영어 전환, 새로고침 후 사용자 UI locale 유지 테스트
- 언어 변경 전 리포트는 원문 유지되고 변경 후 신규 리포트만 선택 언어로 생성되는지 테스트
- locale과 무관하게 structured enum, source와 unified diff가 변경되지 않는지 테스트
- README와 모든 명령을 CI에서 문법·링크 검사
- Python, TypeScript, Playwright, DAB strict validation
- GitHub release마다 지원 CLI/AppKit 버전과 검증 날짜 기록

## 배포 순서

1. 고객이 `doctor`와 `configure` 실행
2. wizard가 Account/UC 관리자 요청서 생성
3. 관리자 작업 완료 후 `resume`
4. catalog/schema, model service, App, watcher와 분석 Job 배포
5. Workspace Admin이 watcher/분석 주체의 Job·Notebook 권한 적용
6. App의 Watched Jobs 화면에서 LTV Job 선택
7. watcher preflight와 최소 권한 검증
8. 정상 및 오류 scenario 실행
9. watcher가 신규 run을 탐지하고 분석 리포트 생성
10. wizard가 App URL과 고객 데모 순서를 출력

## 가정

- AWS Databricks를 공식 검증 환경으로 지원하며 Azure/GCP는 참고사항만 제공한다.
- 고객에게 최소 한 명의 Account Admin, Workspace Admin, Metastore/UC Admin 연락 창구가 있다.
- Beta인 UC AI Gateway 계약은 검증된 CLI/AppKit 버전으로 고정한다.
- 고객은 구현을 위해 소스 코드를 수정할 필요가 없다.
