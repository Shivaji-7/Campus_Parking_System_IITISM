const User = require('../models/User');
const Reservation = require('../models/Reservation');

const getFeeMultiplier = (stars) => {
  if (stars === 5) return 0.7;
  if (stars === 4) return 0.85;
  if (stars === 3) return 1.0;
  if (stars === 2) return 1.2;
  if (stars === 1) return 1.5;
  if (stars === 0) return 2.0;
  return 1.0;
};

const isUserBanned = (user) => {
  if (!user.reputation) return false;
  return user.reputation.stars === 0 && user.reputation.warnings >= 5;
};

const calculateReputation = (user) => {
  return user.reputation || { stars: 3, benefits: 0, warnings: 0, totalOverstays: 0, feeMultiplier: 1.0 };
};

const applyOverstayPenalty = async (userId) => {
  const user = await User.findById(userId);
  if (!user) return null;

  user.reputation.warnings += 1;
  user.reputation.benefits = 0;
  user.reputation.totalOverstays += 1;

  if (user.reputation.warnings >= 3 && user.reputation.stars > 0) {
    user.reputation.stars -= 1;
    user.reputation.warnings = 0; // reset warnings after losing a star? Let's just follow instructions, "decrements star if warnings >= 3"
  }
  user.reputation.feeMultiplier = getFeeMultiplier(user.reputation.stars);
  await user.save();
  return user;
};

const applyPunctualReward = async (userId) => {
  const user = await User.findById(userId);
  if (!user) return null;

  user.reputation.benefits += 1;

  if (user.reputation.benefits >= 5 && user.reputation.stars < 5) {
    user.reputation.stars += 1;
    user.reputation.benefits = 0; // reset benefits after gaining a star
  }
  user.reputation.feeMultiplier = getFeeMultiplier(user.reputation.stars);
  await user.save();
  return user;
};

const processCheckout = async (userId, reservationId) => {
  const reservation = await Reservation.findOne({ _id: reservationId, user: userId });
  if (!reservation) throw new Error("Reservation not found");

  if (reservation.status === 'completed') {
    throw new Error("Already checked out");
  }

  const now = new Date();
  reservation.actualDeparture = now;
  reservation.status = 'completed';

  const expiresAt = new Date(reservation.expiresAt);
  if (now > expiresAt) {
    reservation.isOverstay = true;
    reservation.overstayMinutes = Math.ceil((now - expiresAt) / (1000 * 60));
    await applyOverstayPenalty(userId);
  } else {
    reservation.isOverstay = false;
    reservation.overstayMinutes = 0;
    await applyPunctualReward(userId);
  }

  await reservation.save();
  
  const updatedUser = await User.findById(userId);
  return {
    reservation,
    reputation: updatedUser.reputation
  };
};

module.exports = {
  processCheckout,
  calculateReputation,
  applyOverstayPenalty,
  applyPunctualReward,
  getFeeMultiplier,
  isUserBanned
};
