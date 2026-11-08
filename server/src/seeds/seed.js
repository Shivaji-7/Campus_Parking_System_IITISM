require("dotenv").config();
const connectDb = require("../config/db");
const User = require("../models/User");
const ParkingZone = require("../models/ParkingZone");
const ParkingSlot = require("../models/ParkingSlot");
const Reservation = require("../models/Reservation");

const zoneConfigs = [
  {
    name: "SAC",
    location: "SAC",
    description: "Student Activity Centre parking zone",
    prefix: "SAC",
    fourWheelerSlots: 11,
    twoWheelerSlots: 26,
  },
  {
    name: "NLHC",
    location: "NLHC",
    description: "NLHC campus parking zone",
    prefix: "NLHC",
    fourWheelerSlots: 11,
    twoWheelerSlots: 27,
  },
  {
    name: "Central Library",
    location: "Central Library",
    description: "Parking area near the Central Library",
    prefix: "CL",
    fourWheelerSlots: 18,
    twoWheelerSlots: 43,
  },
  {
    name: "NAC",
    location: "NAC",
    description: "NAC building parking zone",
    prefix: "NAC",
    fourWheelerSlots: 18,
    twoWheelerSlots: 44,
  },
  {
    name: "CSE Department",
    location: "CSE Department",
    description: "Computer Science department parking zone",
    prefix: "CSE",
    fourWheelerSlots: 2,
    twoWheelerSlots: 6,
  },
  {
    name: "Health Centre",
    location: "Health Centre",
    description: "Parking zone for the Health Centre",
    prefix: "HC",
    fourWheelerSlots: 8,
    twoWheelerSlots: 19,
  },
  {
    name: "I2H",
    location: "I2H",
    description: "I2H block parking zone",
    prefix: "I2H",
    fourWheelerSlots: 6,
    twoWheelerSlots: 15,
  },
  {
    name: "Main Gate",
    location: "Main Gate",
    description: "Parking zone near the Main Gate",
    prefix: "MG",
    fourWheelerSlots: 10,
    twoWheelerSlots: 23,
  },
  {
    name: "Academic Complex",
    location: "Academic Complex",
    description: "Academic Complex parking zone",
    prefix: "AC",
    fourWheelerSlots: 14,
    twoWheelerSlots: 35,
  },
  {
    name: "Amber",
    location: "Amber",
    description: "Amber hostel parking zone",
    prefix: "AMB",
    fourWheelerSlots: 10,
    twoWheelerSlots: 25,
  },
  {
    name: "Aquamarine",
    location: "Aquamarine",
    description: "Aquamarine hostel parking zone",
    prefix: "AQM",
    fourWheelerSlots: 4,
    twoWheelerSlots: 9,
  },
  {
    name: "Mechanical Department",
    location: "Mechanical Department",
    description: "Mechanical department parking zone",
    prefix: "ME",
    fourWheelerSlots: 8,
    twoWheelerSlots: 19,
  },
  {
    name: "Enviro Department",
    location: "Enviro Department",
    description: "Environmental department parking zone",
    prefix: "ENV",
    fourWheelerSlots: 14,
    twoWheelerSlots: 33,
  },
  {
    name: "OAT",
    location: "OAT",
    description: "Open Air Theatre parking zone",
    prefix: "OAT",
    fourWheelerSlots: 13,
    twoWheelerSlots: 32,
  },
];

const demoUsers = [
  {
    name: "Aarav Student",
    email: "user@campus.com",
    password: "password123",
    role: "user",
    vehicleNumber: "JH10AB1234",
    department: "Computer Science",
  },
  {
    name: "Nisha Guard",
    email: "security@campus.com",
    password: "password123",
    role: "security",
    vehicleNumber: "",
    department: "Security",
  },
  {
    name: "Admin Office",
    email: "admin@campus.com",
    password: "password123",
    role: "admin",
    vehicleNumber: "",
    department: "Administration",
  },
];

const seedDatabase = async ({ force = false } = {}) => {
  try {
    await connectDb();

    if (force) {
      console.log("Force seeding: resetting demo users, zones, slots, and reservations...");
      await Promise.all([
        User.deleteMany({ email: { $in: demoUsers.map((u) => u.email) } }),
        ParkingZone.deleteMany({}),
        ParkingSlot.deleteMany({}),
        Reservation.deleteMany({}),
      ]);
    }

    for (const demoUser of demoUsers) {
      const existing = await User.findOne({ email: demoUser.email });
      if (!existing) {
        await User.create(demoUser);
        console.log(`Created demo user: ${demoUser.email}`);
      } else if (force) {
        existing.password = demoUser.password;
        await existing.save();
        console.log(`Reset password for demo user: ${demoUser.email}`);
      }
    }

    const zoneCount = await ParkingZone.countDocuments();
    if (zoneCount === 0 || force) {
      if (force && zoneCount > 0) {
        await ParkingZone.deleteMany({});
        await ParkingSlot.deleteMany({});
      }
      const zones = await ParkingZone.insertMany(
        zoneConfigs.map(({ name, location, description }) => ({
          name,
          location,
          description,
        }))
      );

      const slotData = zones.flatMap((zone, zoneIndex) => {
        const config = zoneConfigs[zoneIndex];
        const prefix = config.prefix;
        const slots = [];

        // Four-wheeler calibrated slots (prefix-4W-01 ...)
        const fourWheelerCount = config.fourWheelerSlots || 10;
        for (let i = 1; i <= fourWheelerCount; i++) {
          slots.push({
            slotNumber: `${prefix}-4W-${String(i).padStart(2, "0")}`,
            vehicleType: "four-wheeler",
            isAvailable: true,
            zone: zone._id,
          });
        }

        // Two-wheeler calibrated slots (prefix-2W-01 ...)
        const twoWheelerCount = config.twoWheelerSlots || 0;
        for (let j = 1; j <= twoWheelerCount; j++) {
          slots.push({
            slotNumber: `${prefix}-2W-${String(j).padStart(2, "0")}`,
            vehicleType: "two-wheeler",
            isAvailable: true,
            zone: zone._id,
          });
        }

        return slots;
      });

      await ParkingSlot.insertMany(slotData);
      console.log(`Created ${zones.length} zones and ${slotData.length} slots.`);
    }

    console.log("Seed verification complete.");
    return true;
  } catch (error) {
    console.error("Seed failed:", error.message);
    throw error;
  }
};

if (require.main === module) {
  const force = process.argv.includes("--force");
  seedDatabase({ force })
    .then(() => {
      console.log("Seed finished successfully.");
      process.exit(0);
    })
    .catch(() => process.exit(1));
}

module.exports = { seedDatabase, demoUsers, zoneConfigs };
