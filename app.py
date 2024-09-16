import chainlit as cl
import openai
import os
from langsmith.wrappers import wrap_openai
from langsmith import traceable
import requests
from bs4 import BeautifulSoup
from prompts import SYSTEM_PROMPT

api_key = os.getenv("OPENAI_API_KEY")
endpoint_url = "https://api.openai.com/v1"

client = wrap_openai(openai.AsyncClient(api_key=api_key, base_url=endpoint_url))

# https://platform.openai.com/docs/models/gpt-4o
model_kwargs = {
    "model": "chatgpt-4o-latest",
    "temperature": 0.3,
    "max_tokens": 500
}

@cl.on_message
@traceable
async def on_message(message: cl.Message):
    # Maintain an array of messages in the user session
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})

    response_message = cl.Message(content="")
    await response_message.send()
    
    # User enters a URL 
    url = message.content
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    text = [p.text for p in soup.find_all("p")]
    full_text = "\n".join(text)
    # print(full_text)

    # System prompt
    system_msg = (
        SYSTEM_PROMPT + full_text
    )

    # Pass in website text
    messages = [
        {"role": "system", "content": system_msg},
        # {"role": "user", "content": },
    ]

    # Pass in the only current message for each request
    stream = await client.chat.completions.create(messages=messages, 
                                                  stream=True, **model_kwargs)
    # Pass in the full message history for each request
    # stream = await client.chat.completions.create(messages=message_history,
    #                                               stream=True, **model_kwargs)
    
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)

    await response_message.update()

    # Record the AI's response in the history
    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)
