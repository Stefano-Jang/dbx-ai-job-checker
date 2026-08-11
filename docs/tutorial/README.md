# App 내 구축 튜토리얼 원본

이 문서는 GitHub 가이드와 App 튜토리얼에서 함께 사용하는 원본입니다.

1. `./setup.sh doctor`로 CLI, Python, Node와 인증을 확인합니다.
2. `./setup.sh configure`에서 profile과 warehouse를 명시적으로 선택합니다.
3. `./setup.sh deploy --yes`로 catalog, Jobs와 App을 배포합니다.
4. `./setup.sh verify`로 리소스와 전체 데이터 흐름을 검사합니다.
5. `./setup.sh demo normal`로 정상 리포트를 생성한 뒤 오류 시나리오를 실행합니다.

관리자 권한이 부족하면 `./setup.sh admin-pack`이 `.local/admin-requests/`에 역할별 요청서를 생성합니다.

