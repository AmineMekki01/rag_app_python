import openai
from openai import ChatCompletion
from starlette.responses import StreamingResponse

from src.app.chat.constants import ChatRolesEnum
from src.app.chat.models import BaseMessage, Message
from src.app.core.logs import logger
from src.app.settings import settings
from src.app.chat.streaming import stream_generator, format_to_event_stream
from src.app.chat.constants import ChatRolesEnum, NO_DOCUMENTS_FOUND
from src.app.chat.exceptions import RetrievalNoDocumentsFoundException
from src.app.chat.retrieval import process_retrieval


class OpenAIService:
    @classmethod
    async def chat_completion_without_streaming(cls, input_message: BaseMessage) -> Message:
        completion: openai.ChatCompletion = await openai.ChatCompletion.acreate(
            model=input_message.model,
            api_key=settings.OPENAI_API_KEY,
            messages=[{"role": ChatRolesEnum.USER.value,
                       "content": input_message.message}],
        )
        logger.info(f"Got the following response: {completion}")
        return Message(
            model=input_message.model,
            message=cls.extract_response_from_completion(completion),
            role=ChatRolesEnum.ASSISTANT.value
        )

    @staticmethod
    async def chat_completion_with_streaming(input_message: BaseMessage) -> StreamingResponse:
        subscription: openai.ChatCompletion = await openai.ChatCompletion.acreate(
            model=input_message.model,
            api_key=settings.OPENAI_API_KEY,
            messages=[{"role": ChatRolesEnum.USER.value,
                       "content": input_message.message}],
            stream=True,
        )
        return StreamingResponse(stream_generator(subscription), media_type="text/event-stream")

    @staticmethod
    def extract_response_from_completion(chat_completion: ChatCompletion) -> str:
        return chat_completion.choices[0]["message"]["content"]

    @classmethod
    async def qa_without_stream(cls, input_message: BaseMessage) -> Message:
        try:
            augmented_message: BaseMessage = process_retrieval(
                message=input_message)
            return await cls.chat_completion_without_streaming(input_message=augmented_message)
        except RetrievalNoDocumentsFoundException:
            return Message(model=input_message.model, message=NO_DOCUMENTS_FOUND, role=ChatRolesEnum.ASSISTANT.value)

    @classmethod
    async def qa_with_stream(cls, input_message: BaseMessage) -> StreamingResponse:
        try:
            augmented_message: BaseMessage = process_retrieval(
                message=input_message)
            return await cls.chat_completion_with_streaming(input_message=augmented_message)
        except RetrievalNoDocumentsFoundException:
            return StreamingResponse(
                (format_to_event_stream(y) for y in "Not found"),
                media_type="text/event-stream",
            )