const ParkingSlot = require('../models/ParkingSlot');
const ParkingZone = require('../models/ParkingZone');

const getAvailableSlots = async (zoneId) => {
  const zone = await ParkingZone.findById(zoneId);
  if (!zone) return [];
  
  const availableSlots = await ParkingSlot.find({ zone: zoneId, isAvailable: true });
  const bufferCount = zone.dynamicBufferSize || 0;
  
  if (availableSlots.length > bufferCount) {
    // Hide 'bufferCount' slots from general availability
    return availableSlots.slice(bufferCount); 
  }
  return [];
};

const incrementBuffer = async (zoneId) => {
  const zone = await ParkingZone.findById(zoneId);
  if (zone && zone.dynamicBufferSize < zone.maxBufferSize) {
    zone.dynamicBufferSize += 1;
    await zone.save();
  }
  return zone;
};

const assignBufferSlot = async (zoneId) => {
  const zone = await ParkingZone.findById(zoneId);
  if (!zone || zone.dynamicBufferSize === 0) return null;

  const availableSlots = await ParkingSlot.find({ zone: zoneId, isAvailable: true });
  if (availableSlots.length === 0) return null;

  zone.dynamicBufferSize -= 1;
  await zone.save();
  return availableSlots[0];
};

const resetBuffers = async () => {
  const zones = await ParkingZone.find();
  for (const zone of zones) {
    zone.dynamicBufferSize = zone.baseBufferSize;
    zone.lastBufferReset = new Date();
    await zone.save();
  }
};

module.exports = {
  getAvailableSlots,
  incrementBuffer,
  assignBufferSlot,
  resetBuffers
};
