# Video-AI 작업 규칙

이 레포는 9:16 숏폼을 자동 제작하는 파이프라인이다. Claude의 역할은 두 가지뿐이다:

1. **기획**: 대본·씬 분할·Veo 프롬프트를 작성해 `job.json` 생성
2. **복구**: `blocked`/품질 불량 씬의 프롬프트를 고쳐 재실행

API 호출·폴링·재시도·렌더링은 전부 `pipeline/` 스크립트가 한다. **Claude가 직접 curl로 Veo/ElevenLabs API를 호출하지 말 것.**

## 표준 워크플로

1. 주제를 받으면 `jobs/<YYYY-MM-DD>_<영문-슬러그>/job.json` 생성 (스키마는 `jobs/job.example.json` 참고)
2. `python pipeline/run.py jobs/<디렉터리>` 실행 (venv: `source .venv/bin/activate`)
3. 완료 후 job.json 확인:
   - `blocked` 씬 → 프롬프트에서 안전필터 트리거 요소(실존 인물, 아동, 폭력, 브랜드 로고 등)를 제거하고 리라이트 → `status`를 `pending`으로 → 재실행
   - `failed` 씬 → `last_error` 확인, 일시 오류면 그냥 재실행
4. 최종 보고: `final.mp4` 경로 + 씬별 상태 요약

## 대본 규칙 (한국어 나레이션)

- 씬 수: 5~7개, 총 30~50초
- **씬당 나레이션 7초 이내 = 한국어 25~30자.** Veo 클립이 8초 고정이라 이걸 넘기면 영상이 모자란다
- 1번 씬은 3초 안에 훅(질문/반전/충격 사실). 마지막 씬은 여운 또는 CTA
- 구어체, 짧은 문장. "~습니다" 금지, "~다/~까/~지" 종결
- 이모지·특수문자 금지 (TTS가 읽어버림)

## Veo 프롬프트 규칙 (영어)

- 구조: `[shot type] + [subject/action] + [environment] + [lighting] + [camera movement] + [style]`
- 항상 포함: `no text, no captions, no dialogue, no voiceover` (TTS를 얹으므로)
- 세로 화면에 맞는 구도 명시: 인물은 상반신 위주, 풍경은 수직 요소(빌딩, 폭포, 골목)
- 씬 간 톤 통일: 같은 시간대·색감·렌즈 느낌을 모든 씬 프롬프트에 반복 명시
- 금지: 실존 인물 이름, 브랜드/로고, 아동 단독, 유혈. 안전필터에 걸리면 씬 전체가 blocked됨

## job.json 필드 요약

- `model`: 초안 `veo-3.1-fast-generate-preview` / 최종 `veo-3.1-generate-preview` (doctor.py로 사용 가능 모델 확인)
- `voice_id`: .env의 `ELEVENLABS_VOICE_ID`가 기본값, 씬별 오버라이드 가능
- `keep_ambience`: true면 Veo 원본 오디오를 -18dB로 깔아줌 (기본 false)
- 씬 `status`: `pending → running → done`, 실패 시 `failed`(재시도 가능) / `blocked`(프롬프트 수정 필요)

## 커밋

- 결과물(`jobs/`)은 커밋하지 않는다 (.gitignore 처리됨)
- 파이프라인 수정 시 한글 커밋 메시지: `type(scope): 명사형 종결어미`
