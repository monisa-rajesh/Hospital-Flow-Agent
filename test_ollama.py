
from langchain_ollama import ChatOllama

model = ChatOllama(
    model="qwen3:4b",
    temperature=0,
)

response = model.invoke(
    "Reply in one sentence: What is the purpose of a hospital resource dashboard?"
)

print(response.content)
