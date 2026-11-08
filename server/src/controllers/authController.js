const User = require("../models/User");
const { generateToken } = require("../utils/jwt");

const buildAuthResponse = (user) => ({
  token: generateToken(user),
  user: {
    id: user._id,
    name: user.name,
    email: user.email,
    role: user.role,
    vehicleNumber: user.vehicleNumber,
    department: user.department,
  },
});

const register = async (req, res) => {
  try {
    const { name, email, password, vehicleNumber, department } = req.body;
    const normalizedEmail = typeof email === "string" ? email.trim().toLowerCase() : "";

    const existingUser = await User.findOne({ email: normalizedEmail });
    if (existingUser) {
      return res.status(400).json({ message: "Email is already registered" });
    }

    const user = await User.create({
      name: name?.trim(),
      email: normalizedEmail,
      password,
      role: "user",
      vehicleNumber: vehicleNumber?.trim(),
      department: department?.trim(),
    });

    res.status(201).json(buildAuthResponse(user));
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
};

const login = async (req, res) => {
  try {
    const { email, password } = req.body;
    const normalizedEmail = typeof email === "string" ? email.trim().toLowerCase() : "";
    const user = await User.findOne({ email: normalizedEmail });

    if (!user || !(await user.comparePassword(password))) {
      return res.status(400).json({ message: "Invalid email or password" });
    }

    res.json(buildAuthResponse(user));
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

const getProfile = async (req, res) => {
  res.json({ user: req.user });
};

module.exports = { register, login, getProfile };
