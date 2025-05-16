from groq import Groq
client = Groq(api_key="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")
response = client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[{"role": "user", "content": "Test message"}]
)
print(response.choices[0].message.content)