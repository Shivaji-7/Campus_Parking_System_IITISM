const nodemailer = require("nodemailer");

let transporter = null;
let emailDisabledReasonLogged = false;

const getTransporter = () => {
  if (transporter) {
    return transporter;
  }

  const requiredEnv = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS"];
  const missing = requiredEnv.filter((key) => !process.env[key]);

  if (missing.length > 0) {
    if (!emailDisabledReasonLogged) {
      console.warn(
        `Email alerts disabled. Missing SMTP configuration: ${missing.join(", ")}`
      );
      emailDisabledReasonLogged = true;
    }
    return null;
  }

  transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT || 587),
    secure: String(process.env.SMTP_SECURE).toLowerCase() === "true",
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
    // Set socket and connection timeouts to prevent requests from hanging
    connectionTimeout: 5000,
    greetingTimeout: 5000,
    socketTimeout: 5000,
  });

  return transporter;
};

const sendEmail = async ({ to, subject, text, html }) => {
  const activeTransporter = getTransporter();

  if (!activeTransporter) {
    return false;
  }

  try {
    await activeTransporter.sendMail({
      from: process.env.EMAIL_FROM || process.env.SMTP_USER,
      to,
      subject,
      text,
      html,
    });
    return true;
  } catch (error) {
    // Log error with safe diagnostic message without exposing secret credentials
    console.error(
      `Email delivery to ${to} failed: ${error.message}${
        error.responseCode ? ` (SMTP Code: ${error.responseCode})` : ""
      }`
    );
    return false;
  }
};

module.exports = { sendEmail };
