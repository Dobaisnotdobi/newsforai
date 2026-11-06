# newsforai

공식 AI 발표를 한국어 분야별 뉴스레터로 정리하는 전용 저장소입니다. 공모전 Aicontest와 코드·설정·이력을 분리합니다.

## 운영
- 게시판: https://cafe.naver.com/f-e/cafes/31813012/menus/17
- 정기 작업: Codex ai-2, 매주 목요일 11:00 Asia/Seoul.
- 분야: 종합 → 영상 → 이미지 → 음악 → 기타. 중요한 새 소식 없는 분야는 생략합니다.
- 최초 최근 7일, 이후 state/history.json의 출처별 source_checkpoints 이후를 수집합니다.
- 공식 원문에 있는 사실만 한국어로 요약하고 회사 전망을 별도 표시합니다.
- 제목은 발행일 [MM.DD], 이모지 1개, 분야와 핵심 소식입니다. 개별 항목에 공식 발표일, 핵심 3~5개, 조건, 원문 URL을 기록합니다.

## 확인된 게시 결과
2026-11-06 분야별 전체공개 게시 완료: 영상 12번(2개 소식), 이미지 13번(1개), 음악 14번(1개), 기타 15번(2개). 종합은 선정된 신규 소식이 없어 생략했습니다.
영상 통합 글 https://cafe.naver.com/f-e/cafes/31813012/articles/12 는 사용자 승인에 따라 진단용 11번 글을 대체합니다. 11번은 삭제하지 않고 이력에 superseded_by를 기록했습니다.
단일 소식 진단 제한은 해제했습니다. 같은 발행호·분야의 소식을 한 글에 묶으며 이미 해당 분야 글이 있는 경우 나머지를 별도 글로 자동 분할하지 않습니다.
요청은 표지 없는 multipart, 공식 URL은 일반 텍스트입니다. 향후 본문에는 📌 소식, 🗓️ 발표일, 👥 이용 조건, 🔭 회사 전망, 🔄 후속 변경, 🔗 원문 이모지를 사용합니다. 12~15번은 이 본문 이모지 요청 전에 게시 완료되었습니다.
공개 목록과 API 성공 및 게시 이력 저장 확인 완료. 출처 11개 체크포인트 저장, 수집 실패 출처 2개는 체크포인트를 전진시키지 않았습니다.

## 파일과 실행
sources.json: 공식 출처 및 도메인.
queue.json: 공식 원문을 검증한 발행 항목, 근거, 출처 확인 결과.
publish.py: 중복 검사, 한국어 본문 생성, 순차 게시, 이력 저장.
naver_cafe.py: Aicontest와 같은 UTF-8 multipart 및 전체공개 처리.
state/history.json: 발표 중복 키, 게시 번호·링크·출처·시각, pending 및 재확인 기록.

queue.json 변경은 .github/workflows/publish.yml을 실행합니다. 준비 없이 큐를 수정해 게시를 유발하지 마세요.
전송 전에 pending을 GitHub에 저장하고, 결과가 불명확하면 게시판을 대조한 뒤 수동으로 조정합니다. 확인 없이 pending을 삭제하거나 재전송하지 않습니다. 과거 실패 시도는 reconciliations에 보존합니다.
검증: python -m unittest test_publish 및 python publish.py --validate.

## 인증
GitHub Actions Secrets의 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_REFRESH_TOKEN을 사용합니다.
세 값 등록과 토큰 갱신 및 실제 게시가 확인됐습니다. 인증정보는 코드·설정·로그에 넣지 않습니다.
