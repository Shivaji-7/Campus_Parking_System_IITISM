const mongoose = require("mongoose");

const reservationSchema = new mongoose.Schema(
  {
    user: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
    },
    slot: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "ParkingSlot",
      required: true,
    },
    zone: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "ParkingZone",
      required: true,
    },
    vehicleNumber: {
      type: String,
      required: true,
      trim: true,
    },
    startsAt: {
      type: Date,
      required: true,
    },
    expiresAt: {
      type: Date,
      required: true,
    },
    status: {
      type: String,
      enum: ["active", "expired", "cancelled", "completed"],
      default: "active",
    },
    permitCode: {
      type: String,
      required: true,
      unique: true,
      default: "",
    },
    verifiedAt: {
      type: Date,
      default: null,
    },
    verifiedBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      default: null,
    },
    reminderSentAt: {
      type: Date,
      default: null,
    },
    expiryEmailSentAt: {
      type: Date,
      default: null,
    },
    actualDeparture: { type: Date, default: null },
    isOverstay: { type: Boolean, default: false },
    overstayMinutes: { type: Number, default: 0 },
    baseFee: { type: Number, default: 0 },
    finalFee: { type: Number, default: 0 },
    feeMultiplier: { type: Number, default: 1.0 },
    isBufferSlot: { type: Boolean, default: false },
  },
  { timestamps: true }
);

module.exports = mongoose.model("Reservation", reservationSchema);
