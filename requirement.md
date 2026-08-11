# 고객 설명용 데모 목적
# LTV 관련 테이블을 만드는 notebook task를 수행하는 Lakeflow Job이 있음
# 이 Job의 수행이 끝나면 모든 run 이후 notification을 webhook으로 보냄
# Webhook을 받는 Databricks Apps 존재
# Databricks Apps에서는 Job run id를 바탕으로, 아래를 수행
1. Job run이 평소대비 정상적으로 돌았는지
2. 생성된 LTV 관련 테이블이 의미론적으로 문제가 없는지
3. 혹시 의미론적으로 문제가 있다면 notebook source code를 어떻게 바꾸는 것을 제안하는지
4. Job에 대해서는 completeness, freshness등 데이터 정합도와 관련된 정보도 필요
5. 이러한 분석은 LLM을 통해서 수행

# 데모환경이기 때문에, Databricks Apps에서는 소스코드를 설명할 수 있도록 화면에 보여줘야 함
# 또한, Job run 이후 LLM 분석 결과 리포트를 Apps 화면에서 보여줘야 함
# Apps 화면에서는 Job run 목록이 나오고, 각각에 대해 생성한 리포트를 볼 수 있어야 함

# 전체 환경 구성 방법에 대해 튜토리얼 식으로 설명할 수 있는 화면이 있으면 좋음

