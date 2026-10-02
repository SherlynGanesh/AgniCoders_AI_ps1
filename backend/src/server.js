require("dotenv").config();

const express = require("express");
const cors = require("cors");

const { parseOrderMessage } = require("./services/ai/orderParser");

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
    const { message } = req.body;

    if (!message || typeof message !== "string") {
      return res.status(400).json({
        success: false,
        message: "Order message is required"
      });
    }

    const order = await parseOrderMessage(message);

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
  console.log(`DukanMitra backend running on http://localhost:${PORT}`);
});