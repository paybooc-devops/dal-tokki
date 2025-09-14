## Tokki Video Jobs API

FastAPI 기반의 비동기 이미지→투명 배경→비디오 생성 파이프라인 API.

### 주요 특징
- **비동기 작업 플로우**: 업로드된 이미지(Data URI) → 이미지 편집(그림 고도화) → 배경 제거 → 이미지-투-비디오 생성 → 웹훅 처리 → 결과 파일 서빙.
- **정적 파일 서빙**: `app/data` 하위 결과물을 `/static` 경로로 제공.
- **웹훅 연동**: fal.ai 작업 완료 시 웹훅으로 후속 단계 트리거 및 파일 다운로드.

### 디렉터리 구조
```
app/
  main.py              # FastAPI 엔드포인트 및 웹훅, 정적 서빙
  schemas.py           # Pydantic 스키마 정의
  data/                # 생성 산출물 저장소 (정적 서빙 루트)
    image/
      origin/          # 업로드 원본 이미지 (data URI → PNG)
      new/             # 외부 URL에서 수신된 신규 이미지(웹훅)
      transparent/     # 배경 제거 이미지
    video/
      result/          # 최종 비디오 결과
fal/
  image.py             # 이미지 편집(고도화) fal 클라이언트 submit
  transparent.py       # 배경 제거 fal 클라이언트 submit
  video.py             # 이미지→비디오 fal 클라이언트 submit
```

### 요구 사항
- Python 3.10+
- 종속성: FastAPI, Uvicorn, Pydantic v2, python-dotenv, fal-client, openai

### 설치
```bash
pip install -r requirements.txt
```

### 환경 변수(.env)
- `FAL_KEY`: fal.ai API 키 (필수). 미설정 시 실행 시점에 예외 발생.
- `HOST_ADDRESS`: 이 서비스의 외부 접근 가능한 베이스 URL (예: `http://localhost:8000`).

예시 `.env`:
```
FAL_KEY=your_fal_api_key
HOST_ADDRESS=http://localhost:8000
```

### 실행
개발 모드(핫리로드):
```bash
python -m app.main
```
또는 직접 uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

서빙 경로:
- 정적 파일: `GET /static/...` (`app/data` 디렉터리 내 파일)
- OpenAPI 문서: `GET /docs`, `GET /redoc`

### 작업 흐름(요약)
1) 클라이언트가 `POST /api/v1/video-jobs`로 Data URI 이미지를 업로드하면 서버가 `app/data/image/origin/{job_id}.png`로 저장 후, 이미지 고도화 작업을 fal.ai에 제출(웹훅: `/hook/v1/image-jobs/{job_id}`).
2) 이미지 웹훅 수신 시, 응답 payload의 이미지 URL을 다운로드해 `image/new`에 저장하고, 곧바로 배경 제거 작업을 fal.ai에 제출(웹훅: `/hook/v1/transparent-jobs/{job_id}`).
3) 투명 배경 웹훅 수신 시, 투명 PNG를 `image/transparent`에 저장하고, 이미지→비디오 작업을 fal.ai에 제출(웹훅: `/hook/v1/video-jobs/{job_id}`).
4) 비디오 웹훅 수신 시, 결과 비디오 URL을 다운로드해 `video/result/{job_id}.mp4`로 저장.
5) 클라이언트는 `GET /api/v1/video-jobs/{job_id}`로 상태를 폴링하여 URL을 획득.

상태 전이(`GET /api/v1/video-jobs/{job_id}` 응답의 `status`):
- `processing-1`: 초기 상태(파일 미존재)
- `processing-2`: origin 이미지 존재
- `processing-3`: transparent 이미지 존재
- `finish`: 비디오 결과 존재

### API

#### POST /api/v1/video-jobs
- **설명**: Data URI(base64) 이미지 업로드 후 비동기 파이프라인 시작.
- **요청 바디** (`CreateVideoJobRequest`):
```json
{
  "image_data_uri": "data:image/png;base64,......"
}
```
- **성공 응답 202** (`CreateVideoJobResponse`):
```json
{
  "job_id": "<uuid>"
}
```
- **에러**: 422 `ErrorResponse`(검증 실패), 500 `ErrorResponse`(서버 오류)

#### GET /api/v1/video-jobs/{job_id}
- **설명**: 작업 상태 및 산출물 URL 조회.
- **성공 응답 200** (`GetVideoJobStatusResponse`):
```json
{
  "status": "finish | processing-3 | processing-2 | processing-1",
  "video_url": "http://.../static/video/result/{job_id}.mp4" | null,
  "gen_url": "http://.../static/image/transparent/{job_id}.png" | null,
  "origin_url": "http://.../static/image/origin/{job_id}.png" | null
}
```
- **에러**: 404(존재하지 않는 작업일 때만 의미), 500

#### 웹훅 엔드포인트(내부 사용)
- `POST /hook/v1/image-jobs/{job_id}`: 이미지 고도화 결과 수신, 신규 이미지 다운로드 및 배경 제거 제출.
- `POST /hook/v1/transparent-jobs/{job_id}`: 배경 제거 결과 수신, 투명 PNG 저장 및 비디오 생성 제출.
- `POST /hook/v1/video-jobs/{job_id}`: 비디오 결과 수신, mp4 다운로드.

각 웹훅은 payload 내 URL을 찾아 백그라운드 작업으로 파일을 저장하며, 실패 시 서버 로그에만 기록합니다.

### 보안 및 운영 고려사항
- `HOST_ADDRESS`는 외부에서 접근 가능한 주소여야 하며, fal.ai가 이 주소로 웹훅을 호출할 수 있어야 합니다(로컬 개발 시 터널링 사용 권장: Cloudflared, ngrok 등).
- `app/data`는 서비스에 의해 쓰기 가능해야 하며, 용량 관리/정리 정책이 필요합니다.
- 웹훅 시그니처 검증은 현재 미구현입니다. 운영 환경에서는 검증 구현을 권장합니다.
- 예외 처리: 전역 422/500 핸들러 제공. 세부 오류는 로그 확인.

### 로컬 테스트 팁
- 생성된 `job_id`는 `POST /api/v1/video-jobs` 응답에서 확인 가능합니다.
- 진행 상황은 상태 API를 폴링하거나 `/static/...` 경로에서 파일 생성 여부로 확인할 수 있습니다.
- 단독 모듈 테스트:
  - `python fal/image.py`
  - `python fal/transparent.py`
  - `python fal/video.py`

### 라이선스
프로젝트 루트에 라이선스 명시가 없으므로, 사내/개인용으로 가정합니다. 공개 배포 전 라이선스 추가를 권장합니다.

