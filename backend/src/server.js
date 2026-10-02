require("dotenv").config();

const express = require("express");
const cors = require("cors");

const {
  parseOrderMessages
} = require("./services/ai/orderParser");

const app = express();

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.json({
    message: "DukanMitra backend is running"
  });
});

app.post("/api/orders/parse", async (req, res) => {

  try {

    const { messages } = req.body;

    if (!Array.isArray(messages) || messages.length === 0) {
      return res.status(400).json({
        success: false,
        message: "Messages array is required"
      });
    }

    const validMessages = messages.filter(
      message =>
        typeof message === "string" &&
        message.trim().length > 0
    );

    if (validMessages.length === 0) {
      return res.status(400).json({
        success: false,
        message: "At least one valid message is required"
      });
    }

    const order = await parseOrderMessages(validMessages);

    res.json({
      success: true,
      order
    });

  } catch (error) {

    console.error("Order parsing error:", error);

    res.status(500).json({
      success: false,
      message: "Failed to parse order"
    });
  }
});

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(
    `DukanMitra backend running on http://localhost:${PORT}`
  );
});