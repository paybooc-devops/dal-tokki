from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
import base64


class CreateVideoJobRequest(BaseModel):
    image_data_uri: str = Field(
        ..., description="Data URI 형식의 원본 이미지(base64 포함)"
    )

    @field_validator("image_data_uri")
    @classmethod
    def validate_data_uri(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("image_data_uri는 문자열이어야 합니다.")
        if not value.startswith("data:"):
            raise ValueError("image_data_uri는 'data:'로 시작해야 합니다.")
        if ";base64," not in value:
            raise ValueError("image_data_uri는 ';base64,' 구분자를 포함해야 합니다.")

        try:
            base64_part = value.split(";base64,", 1)[1]
        except Exception as exc:  # noqa: F841
            raise ValueError("유효하지 않은 Data URI 형식입니다.")

        try:
            base64.b64decode(base64_part, validate=True)
        except Exception as exc:  # noqa: F841
            raise ValueError("image_data_uri의 base64 데이터가 유효하지 않습니다.")

        return value


class CreateVideoJobResponse(BaseModel):
    job_id: str = Field(..., description="비디오 생성 작업의 UUID")


class ErrorResponse(BaseModel):
    code: str = Field(..., description="에러 코드(예: VALIDATION_ERROR, INTERNAL_ERROR)")
    message: str = Field(..., description="사람이 읽을 수 있는 에러 메시지")


class GetVideoJobStatusResponse(BaseModel):
    status: Literal["finish", "processing"] = Field(
        ..., description="작업 상태: 완료(finish) 또는 처리중(processing)"
    )
    url: Optional[str] = Field(
        None, description="status가 finish일 때 다운로드 가능한 파일의 URL"
    )


