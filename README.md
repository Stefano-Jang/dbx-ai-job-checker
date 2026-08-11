# Databricks AI Job Checker

Lakeflow Job 실행의 성능, 데이터 품질, 의미론적 오류를 중앙에서 감지하고 근거와 수정안을 보여주는 AWS Databricks 데모입니다.

## 시작하기

필요한 항목은 Databricks CLI 0.292 이상, Python 3.10 이상, Node.js 18 이상입니다. 설치 과정에서 사용할 Databricks profile과 SQL warehouse ID는 사용자가 직접 선택해야 합니다.

```bash
git clone https://github.com/Stefano-Jang/dbx-ai-job-checker.git
cd dbx-ai-job-checker

./setup.sh doctor
./setup.sh configure --profile <profile> --warehouse-id <warehouse-id>
./setup.sh deploy --yes
./setup.sh verify
```

설치 설정은 Git에서 제외된 `.local/`에 저장됩니다. token, password, secret은 로컬 설정에 저장하지 않습니다.

지원 명령은 `doctor`, `configure`, `admin-pack`, `deploy`, `resume`, `verify`, `demo`, `status`입니다. `demo` 시나리오는 `normal`, `stale`, `incomplete`, `semantic_bug`, `runtime_failure`를 지원합니다.

배포되는 리소스:

- 중앙 watcher, analyzer, bootstrap과 demo Lakeflow Jobs
- `ai_job_checker.ops`의 감시 registry, watermark, 요청, 리포트, 품질 및 LLM 추적 Delta tables
- Claude Sonnet Foundation Model API를 사용하는 근거 기반 분석
- 한국어/영어 UI, run 목록, 품질 metric, 정책 snapshot과 unified diff를 표시하는 Databricks App

전체 설계와 단계별 확장 계획은 [plan.md](plan.md)를 참고하세요.

## 지원 범위

- 공식 검증 환경: AWS Databricks
- 기본 UI 및 신규 리포트 언어: 한국어
- 필요한 관리자 역할: Account Admin, Workspace Admin, Metastore/Unity Catalog Admin
- 목표 설치 시간: 관리자 대기 시간을 제외하고 60분 이내
