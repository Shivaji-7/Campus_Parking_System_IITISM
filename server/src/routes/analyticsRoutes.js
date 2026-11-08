const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/auth');
const analyticsController = require('../controllers/analyticsController');

// All analytics routes are protected
router.use(protect);

router.get('/occupancy', analyticsController.getOccupancyData);
router.get('/prediction', analyticsController.getPrediction);
router.get('/predictions', analyticsController.getPrediction);
router.get('/reputation-stats', analyticsController.getReputationStats);
router.get('/overstay-report', analyticsController.getOverstayReport);

module.exports = router;
