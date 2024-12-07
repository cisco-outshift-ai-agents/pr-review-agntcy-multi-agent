from pydantic import BaseModel, Field


class ReviewChatResponse(BaseModel):
    is_skipped: bool = Field(
        description="Indicates if the response is skipped. Set to true if the response is skipped.")
    response: str = Field(description="Your response based on the conversation.")
