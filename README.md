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
2026-11-06 09:30 KST, Higgsfield Shorts 소식 1건을 게시했습니다.
https://cafe.naver.com/f-e/cafes/31813012/articles/11

API 성공, 공개 게시판의 openArticle=true 및 이미지·영상 미첨부, 이력 저장을 확인했습니다.
성공한 요청은 표지 없는 multipart이며 공식 URL은 링크 태그 대신 일반 텍스트입니다. 이모지와 h2/ul/li/strong/br 태그는 유지했습니다. 단일 항목으로 범위를 줄였으므로 링크 태그가 오류의 유일한 원인이라고 단정하지 않습니다.

## 현재 진단 제한
config.json의 diagnostic_event_id가 higgsfield-shorts-2026-11-03으로 설정되어 있습니다.
이 상태에서는 해당 소식만 선택하며 이미 게시한 소식은 중복 전송하지 않습니다. 다른 분야로 이어서 전송하거나 수집 체크포인트를 전진시키지 않습니다.
정규 배치 재개 시 진단 결과와 기존 게시 이력을 확인한 뒤 이 제한을 해제해야 합니다. 제한이 남아 있으면 주간 전체 게시가 준비됐다고 보고하지 마세요.

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
