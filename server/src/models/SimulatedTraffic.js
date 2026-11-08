const mongoose = require("mongoose");

const simulatedTrafficSchema = new mongoose.Schema(
  {
    timestamp: { type: Date, required: true },
    sim_time_sec: { type: Number },
    zone_id: { type: String, required: true, index: true },
    zone_name: { type: String, required: true },
    occupied_slots: { type: Number, required: true },
    available_slots: { type: Number, required: true },
    capacity: { type: Number, required: true },
    occupancy_percentage: { type: Number, required: true },
    active_vehicles: { type: Number },
    entry_count: { type: Number },
    exit_count: { type: Number },
    cumulative_entered: { type: Number },
    cumulative_exited: { type: Number },
    zone_parking_starts: { type: Number, default: 0 },
    zone_parking_ends: { type: Number, default: 0 },
    cumulative_parked: { type: Number, default: 0 },
    cumulative_unparked: { type: Number, default: 0 },
    zone_teleports: { type: Number, default: 0 },
    traffic_density: { type: Number },
    avg_speed_kmh: { type: Number },
    run_id: { type: String, index: true },
    is_simulated: { type: Boolean, default: true },
  },
  { timestamps: true }
);

simulatedTrafficSchema.index({ run_id: 1, zone_id: 1, sim_time_sec: 1 });

module.exports = mongoose.model("SimulatedTraffic", simulatedTrafficSchema, "simulated_traffic_data");
