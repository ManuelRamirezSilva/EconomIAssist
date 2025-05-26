import os
from openai import AzureOpenAI
from dotenv import load_dotenv
import pydantic
import json


class IntentResponse(pydantic.BaseModel):
    intent: str
    value: str

class MultiIntentResponse(pydantic.BaseModel):
    intents: list[IntentResponse]

class IntentParser:
    def __init__(self):
        # Carga el archivo .env desde la raíz del proyecto
        load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY no encontrada en el archivo .env")

        endpoint = "https://economiassist-mini-resource.cognitiveservices.azure.com/"
        deployment = "gpt-4o-mini"
        api_version = "2024-12-01-preview"

        self.client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=api_key,
        )

        self.count_intents_prompt = (
            "You are an expert at analyzing user messages for a financial assistant. "
            "Your job is to count how many distinct intents (actions or requests) are present in the user's message. "
            "Return ONLY the number as an integer. Do not include any explanation or extra text. "
            "Examples:\n"
            "User: 'I got payed today and I spent 200 pesos on groceries.'\n"
            "Output: 2\n"
            "User: 'How much did I spend last month?'\n"
            "Output: 1\n"
            "User: 'Add a meeting for tomorrow and tell me my account balance.'\n"
            "Output: 2\n"
            "User: 'I didn't spend 200 at the supermarket.'\n"
            "Output: 1"
        )

        self.system_prompt = (
            "You are an expert intent detector for a financial assistant. "
            "The user's message may be in Spanish, specifically in the Argentinian dialect, or in English. "
            "Pay special attention to Argentinian slang: for example, 'palos verdes' means 'millón de dólares' (one million USD). "
            "Your job is to analyze the user's message and classify the intent as one of the following: "
            "'money_input' (for income or money received), "
            "'money_output' (for spending or money paid), "
            "'query' (for questions or information requests), "
            "'consult_event' (for consulting about an event), "
            "'add_event' (for adding a new event, e.g., to a calendar), "
            "'request_human' (for requests to speak to or interact with a human), or "
            "'other' (for anything that does not fit the above categories). "
            "Pay special attention to negations or hypothetical statements. "
            "If the user says they did NOT do something (e.g., 'I didn't spend 200 at the supermarket', 'No gasté 200 pesos en el supermercado.', 'I haven't paid the bill yet'), "
            "or if the message is hypothetical or does not indicate an actual action, classify it as 'other'. "
            "Always answer in a JSON object with two fields: "
            "'intent' (one of: 'money_input', 'money_output', 'query', 'consult_event', 'add_event', 'request_human', or 'other'), and "
            "'value' (the amount of money involved for money_input/money_output, the question itself for queries, the event details for event intents, or the user's message for other/request_human). "
            "If a currency is involved, always use the standard 3-letter currency code (e.g., ARS, USD, EUR, etc) in the value. "
            "Return ONLY a JSON object with the fields 'intent' and 'value' for each intent. "
            "Examples:\n"
            "User: 'Me dieron 2 palos verdes.'\n"
            "Output: {\"intent\": \"money_input\", \"value\": \"2000000 USD\"}\n"
            "User: 'Me conviene pasarlos a pesos o invertir en bitcoin?'\n"
            "Output: {\"intent\": \"query\", \"value\": \"Me conviene pasarlos a pesos?\"} and {\"intent\": \"query\", \"value\": \"Me conviene invertir en bitcoin?\"}\n"
            "User: 'I got payed today, my salary was 2000 euros.'\n"
            "Output: {\"intent\": \"money_input\", \"value\": \"2000 EUR\"}\n"
            "User: 'Me pagaron hoy, mi sueldo fue de 2000 euros.'\n"
            "Output: {\"intent\": \"money_input\", \"value\": \"2000 EUR\"}\n"
            "User: 'I spent 50 dollars on groceries.'\n"
            "Output: {\"intent\": \"money_output\", \"value\": \"50 USD\"}\n"
            "User: 'Gasté 50 dólares en el super.'\n"
            "Output: {\"intent\": \"money_output\", \"value\": \"50 USD\"}\n"
            "User: 'How much did I spend last month?'\n"
            "Output: {\"intent\": \"query\", \"value\": \"How much did I spend last month?\"}\n"
            "User: '¿Cuánto gasté el mes pasado?'\n"
            "Output: {\"intent\": \"query\", \"value\": \"¿Cuánto gasté el mes pasado?\"}\n"
            "User: 'Do I have any meetings tomorrow?'\n"
            "Output: {\"intent\": \"consult_event\", \"value\": \"meetings tomorrow\"}\n"
            "User: '¿Tengo alguna reunión mañana?'\n"
            "Output: {\"intent\": \"consult_event\", \"value\": \"reunión mañana\"}\n"
            "User: 'Add dentist appointment on Friday at 10am.'\n"
            "Output: {\"intent\": \"add_event\", \"value\": \"dentist appointment on Friday at 10am\"}\n"
            "User: 'Agendá turno con el dentista el viernes a las 10.'\n"
            "Output: {\"intent\": \"add_event\", \"value\": \"turno con el dentista el viernes a las 10\"}\n"
            "User: 'I want to talk to a human.'\n"
            "Output: {\"intent\": \"request_human\", \"value\": \"I want to talk to a human.\"}\n"
            "User: 'Quiero hablar con una persona.'\n"
            "Output: {\"intent\": \"request_human\", \"value\": \"Quiero hablar con una persona.\"}\n"
            "User: 'Tell me a joke.'\n"
            "Output: {\"intent\": \"other\", \"value\": \"Tell me a joke.\"}\n"
            "User: 'Contame un chiste.'\n"
            "Output: {\"intent\": \"other\", \"value\": \"Contame un chiste.\"}\n"
            "User: 'I didn't spend 200 at the supermarket.'\n"
            "Output: {\"intent\": \"other\", \"value\": \"I didn't spend 200 at the supermarket.\"}\n"
            "User: 'No gasté 200 pesos en el supermercado.'\n"
            "Output: {\"intent\": \"other\", \"value\": \"No gasté 200 pesos en el supermercado.\"}"
        )

        self.split_intents_prompt = (
            "You are an expert at analyzing user messages for a financial assistant. "
            "The user's message may be in Spanish (Argentinian dialect) or English. "
            "Pay special attention to Argentinian slang: for example, 'palos verdes' means 'millón de dólares' (one million USD). "
            "Split the user's message into its distinct intents (actions or requests), "
            "returning a JSON array of strings, each string being a separate intent or request from the original message. "
            "If the message contains multiple questions joined by 'o' (or), split each question as a separate intent. "
            "Do not explain, just return the JSON array. "
            "Examples:\n"
            "User: 'Me dieron 2 palos verdes. Me conviene pasarlos a pesos o invertir en bitcoin?'\n"
            "Output: [\"Me dieron 2 palos verdes.\", \"Me conviene pasarlos a pesos?\", \"Me conviene invertir en bitcoin?\"]\n"
            "User: 'I got payed today and I spent 200 pesos on groceries.'\n"
            "Output: [\"I got payed today\", \"I spent 200 pesos on groceries.\"]\n"
            "User: 'Add a meeting for tomorrow and tell me my account balance.'\n"
            "Output: [\"Add a meeting for tomorrow\", \"tell me my account balance.\"]"
        )

    def receive_message(self, message: str):
        # First call: count intents
        count_response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.count_intents_prompt},
                {"role": "user", "content": message},
            ],
            max_tokens=10,
            temperature=0.0,
            top_p=1.0,
            model="gpt-4o-mini"
        )
        try:
            num_intents = int(count_response.choices[0].message.content.strip())
            if num_intents < 1:
                num_intents = 1
        except Exception:
            num_intents = 1

        # If only one intent, classify the whole message
        if num_intents == 1:
            intent_texts = [message]
        else:
            # Ask the model to split the message into its distinct intents
            split_response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.split_intents_prompt},
                    {"role": "user", "content": message},
                ],
                max_tokens=256,
                temperature=0.0,
                top_p=1.0,
                model="gpt-4o-mini"
            )
            try:
                intent_texts = json.loads(split_response.choices[0].message.content)
                if not isinstance(intent_texts, list) or not all(isinstance(x, str) for x in intent_texts):
                    intent_texts = [message] * num_intents
            except Exception:
                intent_texts = [message] * num_intents

        intent_results = []
        for intent_text in intent_texts:
            classify_response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": intent_text},
                ],
                max_tokens=4096,
                temperature=1.0,
                top_p=1.0,
                model="gpt-4o-mini"
            )
            model_output = classify_response.choices[0].message.content
            try:
                data = json.loads(model_output)
                parsed = IntentResponse(**data)
                intent_results.append((parsed.intent, parsed.value))
            except Exception:
                intent_results.append(("error", model_output.strip()))

        print(f"User: {message}\nIntents: {len(intent_results)}\nResponse: {intent_results}\n")
        return intent_results

# --- MAIN ---
if __name__ == "__main__":
    examples = [
        "Gane la loteria y me dieron 3 palos verdes. Me conviene pasarlos a pesos o invertir en bitcoin?", 
        "Un amigo me debe 300 pesos, por donde le pido que me lo pase?"
    ]
    parser = IntentParser()
    for example in examples:
        parser.receive_message(example)