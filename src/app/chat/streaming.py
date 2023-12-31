import asyncio
import json

import async_timeout

from src.app.chat.constants import ChatRolesEnum
from src.app.chat.exceptions import OpenAIStreamTimeoutException, OpenAIFailedProcessingException
from src.app.chat.models import Chunk, Message
from src.app.core.logs import logger
from src.app.settings import settings


async def stream_generator(subscription):
    async with async_timeout.timeout(settings.GENERATION_TIMEOUT_SEC):
        try:
            complete_response: str = ""
            async for chunk in subscription:
                complete_response = f"{complete_response}{Chunk.get_chunk_delta_content(chunk=chunk)}"
                yield format_to_event_stream(post_processing(chunk))
            message: Message = Message(
                model=chunk.model, message=complete_response, role=ChatRolesEnum.ASSISTANT.value)
            logger.info(f"Complete Streamed Message: {message}")
        except asyncio.TimeoutError:
            raise OpenAIStreamTimeoutException


def format_to_event_stream(data: str) -> str:
    return f"event: message\ndata: {data}\n\n"


def post_processing(chunk) -> str:
    try:
        logger.info(f"Chunk: {chunk}")
        formatted_chunk = Chunk.from_chunk(chunk=chunk)
        logger.info(f"Formatted Chunk: {formatted_chunk}")
        return json.dumps(formatted_chunk.model_dump())
    except Exception:
        raise OpenAIFailedProcessingException
