const mongoose = require("mongoose");

const parkingZoneSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: true,
      trim: true,
    },
    location: {
      type: String,
      required: true,
      trim: true,
    },
    description: {
      type: String,
      trim: true,
      default: " ",
    },
    isActive: {
      type: Boolean,
      default: true,
    },
    dynamicBufferSize: { type: Number, default: 0 },
    baseBufferSize: { type: Number, default: 0 },
    maxBufferSize: { type: Number, default: 3 },
    lastBufferReset: { type: Date, default: Date.now },
  },
  { timestamps: true }
);

module.exports = mongoose.model("ParkingZone", parkingZoneSchema);
