const express = require("express");
const router = express.Router();
const simulationController = require("../controllers/simulationController");

// Public/commuter readable simulation & prediction endpoints
router.get("/overview", simulationController.getOverview);
router.get("/telemetry", simulationController.getTelemetry);
router.get("/prediction", simulationController.getPrediction);
router.get("/forecast", simulationController.getForecast);
router.get("/graphs", simulationController.getGraphs);
router.post("/trigger", simulationController.triggerSimulation);

module.exports = router;
