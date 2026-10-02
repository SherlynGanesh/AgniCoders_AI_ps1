const Groq = require("groq-sdk");
const { orderSchema } = require("./schema");

const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY
});

async function parseOrderMessage(message) {
  const systemPrompt = `
You are the AI order parser for DukanMitra, an order desk for small Indian shopkeepers.

Your job is to understand casual customer orders written in:
- English
- Hindi
- Hinglish
- Hindi written using English letters

Extract the requested products accurately.

RULES:

1. Identify EVERY product requested.

2. Extract quantity whenever the customer provides it.

3. Understand common Hindi quantity words:
- ek = 1
- do = 2
- teen = 3
- chaar = 4
- paanch = 5
- aadha = 0.5
- dedh = 1.5
- dhai = 2.5

4. Normalize units:
- kilo, kilogram, kg → kg
- gram, g → g
- litre, liter, l, L → L
- millilitre, milliliter, ml → ml
- packet, pack → pack
- piece, pcs → piece
- bottle → bottle

5. Detect brands when explicitly mentioned.
Examples:
- Amul
- Parle
- Britannia
- Tata
- Surf Excel

6. Preserve the customer's original product phrase in rawText.

7. Do NOT invent a quantity if the customer did not provide one.
Use null.

8. Do NOT invent a brand.
Use null.

9. Do NOT invent price, stock or product variants.

10. If the wording could refer to multiple products, mark ambiguous as true.

11. If an item is ambiguous, explain the reason in ambiguityReason.

12. If clarification is required, set needsClarification to true and generate a SHORT clarificationMessage.

13. The clarification message should be natural and suitable for an Indian shopkeeper.

14. Do not perform catalog matching.
Another system will match the extracted product against the shopkeeper's actual catalog.

15. Return ONLY the JSON structure requested by the schema.
`;

  const response = await groq.chat.completions.create({
    model: "openai/gpt-oss-20b",

    messages: [
      {
        role: "system",
        content: systemPrompt
      },
      {
        role: "user",
        content: message
      }
    ],

    response_format: {
      type: "json_schema",
      json_schema: {
        name: "order_parser",
        strict: true,
        schema: orderSchema
      }
    }
  });

  const content = response.choices[0].message.content;

  return JSON.parse(content);
}

module.exports = {
  parseOrderMessage
};