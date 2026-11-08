const ParkingSlot = require("../models/ParkingSlot");
const ParkingZone = require("../models/ParkingZone");
const Reservation = require("../models/Reservation");
const { createPermitCode } = require("../utils/permit");
const { processReservationAlerts } = require("../services/reservationAlertService");

const refreshExpiredReservations = async () => {
  await processReservationAlerts();
};

const getDurationMinutes = (durationHours, durationMinutes) => {
  const hours = Math.max(0, Number(durationHours || 0));
  const minutes = Math.max(0, Number(durationMinutes || 0));

  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) {
    throw new Error("Duration must be numeric");
  }

  const totalMinutes = Math.round(hours * 60 + minutes);

  if (totalMinutes < 10) {
    throw new Error("Minimum reservation duration is 10 minutes");
  }

  if (totalMinutes > 12 * 60) {
    throw new Error("Maximum reservation duration is 12 hours");
  }

  return totalMinutes;
};

const getSlots = async (req, res) => {
  await refreshExpiredReservations();

  const slots = await ParkingSlot.find()
    .populate("zone", "name location")
    .sort({ createdAt: 1 });

  res.json({ slots });
};

const getZones = async (req, res) => {
  const zones = await ParkingZone.find().sort({ createdAt: 1 });
  res.json({ zones });
};

const reserveSlot = async (req, res) => {
  try {
    await refreshExpiredReservations();

    const { slotId, vehicleNumber, durationHours, durationMinutes } = req.body;
    const slot = await ParkingSlot.findById(slotId).populate("zone");

    if (!slot) {
      return res.status(404).json({ message: "Parking slot not found" });
    }

    if (!slot.isAvailable) {
      return res.status(400).json({ message: "Parking slot is not available" });
    }

    const { isUserBanned } = require("../services/reputationService");
    
    if (isUserBanned(req.user)) {
      return res.status(403).json({ message: "User is banned from making reservations" });
    }

    const startsAt = new Date();
    const totalDurationMinutes = getDurationMinutes(durationHours, durationMinutes);
    const expiresAt = new Date(startsAt.getTime() + totalDurationMinutes * 60 * 1000);

    const baseRatePerHour = 10; // Simple base rate
    const baseFee = (totalDurationMinutes / 60) * baseRatePerHour;
    const feeMultiplier = req.user.reputation ? req.user.reputation.feeMultiplier : 1.0;
    const finalFee = baseFee * feeMultiplier;

    const reservation = await Reservation.create({
      user: req.user._id,
      slot: slot._id,
      zone: slot.zone._id,
      vehicleNumber: vehicleNumber || req.user.vehicleNumber || "NA",
      startsAt,
      expiresAt,
      permitCode: createPermitCode(),
      baseFee,
      finalFee,
      feeMultiplier,
    });

    slot.isAvailable = false;
    await slot.save();

    const populatedReservation = await Reservation.findById(reservation._id)
      .populate("slot", "slotNumber vehicleType")
      .populate("zone", "name location")
      .populate("user", "name email");

    res.status(201).json({
      message: "Parking slot reserved successfully",
      reservation: populatedReservation,
    });
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
};

const getMyReservations = async (req, res) => {
  await refreshExpiredReservations();

  const reservations = await Reservation.find({ user: req.user._id })
    .populate("slot", "slotNumber vehicleType")
    .populate("zone", "name location")
    .sort({ createdAt: -1 });

  const now = new Date();
  const notifications = reservations
    .filter(
      (reservation) =>
        reservation.status === "active" &&
        reservation.expiresAt.getTime() - now.getTime() <= 30 * 60 * 1000
    )
    .map((reservation) => ({
      reservationId: reservation._id,
      message: `Reservation ${reservation.permitCode} expires soon`,
      expiresAt: reservation.expiresAt,
    }));

  res.json({ reservations, notifications });
};

const getActiveReservations = async (req, res) => {
  await refreshExpiredReservations();

  const reservations = await Reservation.find({ status: "active" })
    .populate("user", "name email vehicleNumber")
    .populate("slot", "slotNumber vehicleType")
    .populate("zone", "name location")
    .sort({ expiresAt: 1 });

  res.json({ reservations });
};

const verifyPermit = async (req, res) => {
  try {
    const { permitCode } = req.body;
    await refreshExpiredReservations();

    const reservation = await Reservation.findOne({ permitCode })
      .populate("user", "name email vehicleNumber")
      .populate("slot", "slotNumber vehicleType")
      .populate("zone", "name location");

    if (!reservation) {
      return res.status(404).json({ message: "Permit not found" });
    }

    const isValid = reservation.status === "active" && reservation.expiresAt > new Date();

    if (isValid) {
      reservation.verifiedAt = new Date();
      reservation.verifiedBy = req.user._id;
      await reservation.save();
    }

    res.json({
      valid: isValid,
      reservation,
      message: isValid ? "Permit verified successfully" : "Permit is not valid",
    });
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
};

const updateSlotAvailability = async (req, res) => {
  try {
    const { isAvailable } = req.body;
    const slot = await ParkingSlot.findByIdAndUpdate(
      req.params.id,
      { isAvailable },
      { new: true }
    ).populate("zone", "name location");

    if (!slot) {
      return res.status(404).json({ message: "Parking slot not found" });
    }

    res.json({ message: "Slot availability updated", slot });
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
};

const { processCheckout, calculateReputation } = require("../services/reputationService");

const checkout = async (req, res) => {
  try {
    const { reservationId } = req.params;
    const result = await processCheckout(req.user._id, reservationId);
    
    // Free up the slot
    const slot = await ParkingSlot.findById(result.reservation.slot);
    if (slot) {
      slot.isAvailable = true;
      await slot.save();
    }

    res.json({ message: "Checkout successful", result });
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
};

const getReputation = async (req, res) => {
  try {
    const reputation = calculateReputation(req.user);
    res.json({ reputation });
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
};

module.exports = {
  getSlots,
  getZones,
  reserveSlot,
  getMyReservations,
  getActiveReservations,
  verifyPermit,
  updateSlotAvailability,
  refreshExpiredReservations,
  checkout,
  getReputation,
};
