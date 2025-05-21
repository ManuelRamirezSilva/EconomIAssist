import os
from openai import AzureOpenAI
from dotenv import load_dotenv
import pydantic
import json


# Carga el archivo .env desde la raíz del proyecto
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

api_key = os.getenv("AZURE_OPENAI_API_KEY")
if not api_key:
    raise ValueError("AZURE_OPENAI_API_KEY no encontrada en el archivo .env")

endpoint = "https://economiassist-mini-resource.cognitiveservices.azure.com/"
model_name = "gpt-4o-mini"
deployment = "gpt-4o-mini"

api_version = "2024-12-01-preview"

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=api_key,
)

class IntentResponse(pydantic.BaseModel):
    intent: str
    value: str


system_prompt = (
    "You are an expert intent detector for a financial assistant. "
    "Your job is to analyze the user's message and classify the intent as one of the following: "
    "'money_input' (for income or money received), "
    "'money_output' (for spending or money paid), "
    "'query' (for questions or information requests), "
    "'consult_event' (for consulting about an event), "
    "'add_event' (for adding a new event, e.g., to a calendar), "
    "'request_human' (for requests to speak to or interact with a human), or "
    "'other' (for anything that does not fit the above categories). "
    "Pay special attention to negations or hypothetical statements. "
    "If the user says they did NOT do something (e.g., 'I didn't spend 200 at the supermarket', 'I haven't paid the bill yet'), "
    "or if the message is hypothetical or does not indicate an actual action, classify it as 'other'. "
    "Always answer in a JSON object with two fields: "
    "'intent' (one of: 'money_input', 'money_output', 'query', 'consult_event', 'add_event', 'request_human', or 'other'), and "
    "'value' (the amount of money involved for money_input/money_output, the question itself for queries, the event details for event intents, or the user's message for other/request_human). "
    "If a currency is involved, always use the standard 3-letter currency code (e.g., ARS, USD, EUR, etc) in the value. "
    "Examples:\n"
    "User: 'I got payed today, my salary was 2000 euros.'\n"
    "Output: {\"intent\": \"money_input\", \"value\": \"2000 EUR\"}\n"
    "User: 'I spent 50 dollars on groceries.'\n"
    "Output: {\"intent\": \"money_output\", \"value\": \"50 USD\"}\n"
    "User: 'How much did I spend last month?'\n"
    "Output: {\"intent\": \"query\", \"value\": \"How much did I spend last month?\"}\n"
    "User: 'Do I have any meetings tomorrow?'\n"
    "Output: {\"intent\": \"consult_event\", \"value\": \"meetings tomorrow\"}\n"
    "User: 'Add dentist appointment on Friday at 10am.'\n"
    "Output: {\"intent\": \"add_event\", \"value\": \"dentist appointment on Friday at 10am\"}\n"
    "User: 'I want to talk to a human.'\n"
    "Output: {\"intent\": \"request_human\", \"value\": \"I want to talk to a human.\"}\n"
    "User: 'Tell me a joke.'\n"
    "Output: {\"intent\": \"other\", \"value\": \"Tell me a joke.\"}\n"
    "User: 'I didn't spend 200 at the supermarket.'\n"
    "Output: {\"intent\": \"other\", \"value\": \"I didn't spend 200 at the supermarket.\"}"
)

examples = [
    "My boss transferred 5000 pesos to my account.",
    "Paid 300 USD for rent today.",
    "What is my current account balance?",
    "Is there a birthday party scheduled for next week?",
    "Schedule a call with John on Monday at 2pm.",
    "No gaste 200 pesos en el supermercado.",
    "Can I speak with a human agent?",
    "Sing me a song."
]

for example in examples:
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": example,
            }
        ],
        max_tokens=4096,
        temperature=1.0,
        top_p=1.0,
        model=deployment
    )

    model_output = response.choices[0].message.content

    try:
        data = json.loads(model_output)
        parsed = IntentResponse(**data)
        print(f"User: {example}\nParsed: {parsed}\n")
    except Exception as e:
        print(f"User: {example}\nError parsing model output:", e)
        print("Raw output:", model_output)
        print()