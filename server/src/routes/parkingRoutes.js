const express = require("express");
const {
  getSlots,
  getZones,
  reserveSlot,
  getMyReservations,
  getActiveReservations,
  verifyPermit,
  updateSlotAvailability,
  checkout,
  getReputation,
} = require("../controllers/parkingController");
const { getReservationQr } = require("../controllers/qrController");
const { protect, authorize } = require("../middleware/auth");

const router = express.Router();

router.get("/slots", protect, getSlots);
router.get("/zones", protect, getZones);
router.post("/reserve", protect, authorize("user", "admin"), reserveSlot);
router.get("/my-reservations", protect, authorize("user", "admin"), getMyReservations);
router.get("/active-reservations", protect, authorize("security", "admin"), getActiveReservations);
router.post("/verify-permit", protect, authorize("security", "admin"), verifyPermit);
router.patch("/slots/:id/availability", protect, authorize("security", "admin"), updateSlotAvailability);
router.get("/reservations/:id/qr", protect, getReservationQr);
router.post("/checkout/:reservationId", protect, authorize("user", "admin"), checkout);
router.get("/reputation", protect, authorize("user", "admin"), getReputation);

module.exports = router;
