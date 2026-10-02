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
            type: ["string", "null"]
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
          },

          status: {
            type: "string",
            enum: [
              "complete",
              "partial",
              "needs_clarification",
              "cancelled"
            ]
          }
        },

        required: [
          "rawText",
          "productName",
          "brand",
          "quantity",
          "unit",
          "ambiguous",
          "ambiguityReason",
          "status"
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

module.exports = {
  orderSchema
};