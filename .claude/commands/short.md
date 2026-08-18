---
description: 주제 하나로 9:16 숏폼을 기획부터 최종 렌더링까지 자동 제작
allowed-tools: Bash, Write, Read, Edit, Glob
---

주제: $ARGUMENTS

CLAUDE.md의 대본 규칙과 Veo 프롬프트 규칙을 따라 아래를 순서대로 수행하라.

1. 주제를 분석해 5~7개 씬으로 구성된 대본을 작성한다
   - 씬당 한국어 나레이션 25~30자 이내, 1번 씬은 3초 훅
2. 각 씬마다 영어 Veo 프롬프트를 작성한다
   - 모든 씬에 동일한 시간대·색감·스타일 키워드를 반복해 톤을 통일
   - 반드시 `no text, no captions, no dialogue, no voiceover` 포함
3. `jobs/<오늘날짜>_<영문-슬러그>/job.json`을 생성한다 (`jobs/job.example.json` 스키마)
4. 실행한다: `source .venv/bin/activate && python pipeline/run.py jobs/<디렉터리>`
5. 실행 후 job.json을 다시 읽어 상태를 확인한다
   - `blocked` 씬: 안전필터 트리거를 제거해 프롬프트 리라이트 → status를 pending으로 → 4번 재실행
   - `failed` 씬: last_error가 일시 오류(429/5xx/timeout)면 4번 재실행
   - 최대 3회 복구 시도 후에도 안 되면 중단하고 원인 보고
6. 최종 보고: final.mp4 절대경로, 총 길이, 씬별 상태 표
