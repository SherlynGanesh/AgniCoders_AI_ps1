const orderSchema = {
  type: "object",
  properties: {
    items: {
      type: "array",
      items: {
        type: "object",
        properties: {
          rawText: {
            type: "string"
          },
          productName: {
            type: "string"
          },
          brand: {
            type: ["string", "null"]
          },
          quantity: {
            type: ["number", "null"]
          },
          unit: {
            type: ["string", "null"]
          },
          ambiguous: {
            type: "boolean"
          },
          ambiguityReason: {
            type: ["string", "null"]
          }
        },
        required: [
          "rawText",
          "productName",
          "brand",
          "quantity",
          "unit",
          "ambiguous",
          "ambiguityReason"
        ],
        additionalProperties: false
      }
    },
    needsClarification: {
      type: "boolean"
    },
    clarificationMessage: {
      type: ["string", "null"]
    }
  },
  required: [
    "items",
    "needsClarification",
    "clarificationMessage"
  ],
  additionalProperties: false
};

module.exports = { orderSchema };