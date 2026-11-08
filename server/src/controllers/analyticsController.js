const Reservation = require('../models/Reservation');
const ParkingSlot = require('../models/ParkingSlot');
const User = require('../models/User');
const ParkingZone = require('../models/ParkingZone');

const getOccupancyData = async (req, res) => {
  try {
    const zones = await ParkingZone.find();
    const occupancyData = [];

    for (const zone of zones) {
      const totalSlots = await ParkingSlot.countDocuments({ zone: zone._id });
      const occupiedSlots = await ParkingSlot.countDocuments({ zone: zone._id, isAvailable: false });
      
      occupancyData.push({
        zone: zone.name,
        total: totalSlots,
        occupied: occupiedSlots,
        occupancyRate: totalSlots === 0 ? 0 : (occupiedSlots / totalSlots) * 100
      });
    }

    res.json({ occupancyData });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

const getPrediction = async (req, res) => {
  try {
    const predictions = [];
    const now = new Date();
    
    // Simulate 24 hours of predictions using sine wave + noise
    for (let i = 1; i <= 24; i++) {
      const futureTime = new Date(now.getTime() + i * 60 * 60 * 1000);
      const hour = futureTime.getHours();
      
      // Base occupancy wave: peaks around 12 (noon)
      const baseOccupancy = Math.sin((hour - 6) * Math.PI / 12) * 50 + 50; 
      const noise = (Math.random() * 10) - 5;
      let predicted = Math.max(0, Math.min(100, baseOccupancy + noise));
      
      predictions.push({
        time: futureTime,
        predictedOccupancy: Math.round(predicted)
      });
    }
    
    res.json({ predictions });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

const getReputationStats = async (req, res) => {
  try {
    const users = await User.find({ role: 'user' });
    const stats = {
      5: 0,
      4: 0,
      3: 0,
      2: 0,
      1: 0,
      0: 0
    };
    
    users.forEach(user => {
      const stars = user.reputation?.stars ?? 3;
      if (stats[stars] !== undefined) {
        stats[stars]++;
      }
    });
    
    res.json({ reputationDistribution: stats });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

const getOverstayReport = async (req, res) => {
  try {
    const totalReservations = await Reservation.countDocuments({ status: 'completed' });
    const overstays = await Reservation.countDocuments({ status: 'completed', isOverstay: true });
    
    const overstayStats = await Reservation.aggregate([
      { $match: { isOverstay: true } },
      { $group: { _id: null, averageOverstayMinutes: { $avg: "$overstayMinutes" }, totalOverstayMinutes: { $sum: "$overstayMinutes" } } }
    ]);
    
    res.json({
      totalCompleted: totalReservations,
      totalOverstays: overstays,
      overstayRate: totalReservations === 0 ? 0 : (overstays / totalReservations) * 100,
      averageOverstayMinutes: overstayStats.length > 0 ? overstayStats[0].averageOverstayMinutes : 0,
      totalOverstayMinutes: overstayStats.length > 0 ? overstayStats[0].totalOverstayMinutes : 0
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

module.exports = {
  getOccupancyData,
  getPrediction,
  getReputationStats,
  getOverstayReport
};
