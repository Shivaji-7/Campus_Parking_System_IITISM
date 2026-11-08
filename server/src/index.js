require("dotenv").config();
const path = require("path");
const express = require("express");
const cors = require("cors");
const helmet = require("helmet");
const morgan = require("morgan");
const connectDb = require("./config/db");
const { getJwtSecret, validateRuntimeEnv } = require("./config/env");
const authRoutes = require("./routes/authRoutes");
const parkingRoutes = require("./routes/parkingRoutes");
const adminRoutes = require("./routes/adminRoutes");
const { processReservationAlerts } = require("./services/reservationAlertService");
const { seedDatabase } = require("./seeds/seed");

const app = express();
const PORT = process.env.PORT || 5000;
const HOST = process.env.HOST || "0.0.0.0";
const alertCheckIntervalMs = Number(process.env.ALERT_CHECK_INTERVAL_MS || 60000);
let server;
let alertTimer;

const getAllowedOrigins = () => {
  if (!process.env.CLIENT_URL) {
    return true;
  }

  return process.env.CLIENT_URL.split(",").map((value) => value.trim());
};

app.use(
  helmet({
    crossOriginResourcePolicy: false,
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'", "https://esm.sh", "https://cdn.jsdelivr.net"],
        scriptSrcElem: ["'self'", "https://esm.sh", "https://cdn.jsdelivr.net"],
        styleSrc: [
          "'self'",
          "'unsafe-inline'",
          "https://fonts.googleapis.com",
          "https://cdn.jsdelivr.net",
        ],
        fontSrc: ["'self'", "https://fonts.gstatic.com", "data:"],
        imgSrc: [
          "'self'",
          "data:",
          "blob:",
          "https://*.tile.openstreetmap.org",
          "https://*.tile.openstreetmap.de",
          "https://*.tile.openstreetmap.fr",
          "https://*.basemaps.cartocdn.com",
          "https://server.arcgisonline.com",
        ],
        connectSrc: ["'self'"],
      },
    },
  })
);
app.use(
  cors({
    origin: getAllowedOrigins(),
    credentials: true,
  })
);
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(morgan(process.env.NODE_ENV === "production" ? "combined" : "dev"));
app.use(express.static(path.join(__dirname, "../../public")));

app.get("/api/health", (req, res) => {
  res.json({ message: "Campus Parking Management System API is running" });
});

app.use("/api/auth", authRoutes);
app.use("/api/parking", parkingRoutes);
app.use("/api/admin", adminRoutes);
app.use("/api/analytics", require("./routes/analyticsRoutes"));
app.use("/api/simulation", require("./routes/simulationRoutes"));

app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "../../public/index.html"));
});

app.use((error, req, res, next) => {
  console.error("Unhandled application error:", error);

  if (res.headersSent) {
    return next(error);
  }

  res.status(500).json({
    message:
      process.env.NODE_ENV === "production"
        ? "Something went wrong. Please try again later."
        : error.message,
  });
});

const stopServer = async (signal) => {
  console.log(`${signal} received. Shutting down gracefully...`);

  if (alertTimer) {
    clearInterval(alertTimer);
  }

  if (server) {
    await new Promise((resolve) => server.close(resolve));
  }

  process.exit(0);
};

const startServer = async () => {
  try {
    getJwtSecret();
    validateRuntimeEnv().forEach((warning) => {
      console.warn(`Startup warning: ${warning}`);
    });

    await connectDb();
    await seedDatabase();

    server = app.listen(PORT, HOST, () => {
      console.log(`Server running on http://${HOST}:${PORT}`);
    });

    alertTimer = setInterval(async () => {
      try {
        await processReservationAlerts();
      } catch (error) {
        console.error("Reservation alert check failed:", error.message);
      }
    }, alertCheckIntervalMs);
  } catch (error) {
    console.error("Application startup failed:", error.message);
    process.exit(1);
  }
};

process.on("SIGTERM", () => stopServer("SIGTERM"));
process.on("SIGINT", () => stopServer("SIGINT"));
process.on("unhandledRejection", (error) => {
  console.error("Unhandled promise rejection:", error);
});
process.on("uncaughtException", (error) => {
  console.error("Uncaught exception:", error);
  process.exit(1);
});

startServer();
