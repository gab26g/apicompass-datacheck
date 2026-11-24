'use strict';
// User-operated first-account wrapper. Never run noninteractively or pass a password.
const path = require('node:path');

class EnrollmentError extends Error {}

function installGuards({ helpers, User, auth, registerSchema }) {
  if (typeof helpers.askQuestion !== 'function' || typeof helpers.askSilentQuestion !== 'function' ||
      typeof User.countDocuments !== 'function' || typeof auth.registerUser !== 'function' ||
      typeof registerSchema.safeParse !== 'function') {
    throw new EnrollmentError('Pinned enrollment interfaces differ; stop for review.');
  }
  const visible = helpers.askQuestion;
  const register = auth.registerUser;
  let checked = false;
  helpers.askQuestion = async query => {
    // The upstream CLI connects before asking any questions. Refuse existing
    // databases before collecting the user's email or password.
    if (!checked) {
      if (await User.countDocuments({}) !== 0) throw new EnrollmentError('Production already has a user; first-account setup refused.');
      checked = true;
    }
    if (query.startsWith('Password:')) {
      const password = await helpers.askSilentQuestion('Choose your application password (hidden, at least 12 characters): ');
      if (typeof password !== 'string' || password.length < 12 || password.length > 128) {
        throw new EnrollmentError('Password must contain 12–128 characters. Nothing was created.');
      }
      const confirmation = await helpers.askSilentQuestion('Repeat your application password (hidden): ');
      if (password !== confirmation) throw new EnrollmentError('Passwords differ. Nothing was created.');
      return password; // Never reaches upstream's blank/generate/print branch.
    }
    return visible(query);
  };
  auth.registerUser = async (user, additional) => {
    try {
      // Upstream validation errors log the input object, including password.
      // Validate first without logging, then invoke the original registration.
      if (!registerSchema.safeParse(user).success) return { status: 400, message: 'Account fields did not pass validation; nothing was created.' };
      if (await User.countDocuments({}) !== 0) return { status: 409, message: 'An account already exists; first-account setup refused.' };
      return await register(user, { ...additional, emailVerified: true });
    } catch {
      return { status: 500, message: 'Private enrollment failed; ask the operator to inspect state without exposing credentials.' };
    }
  };
}

function main() {
  const safeError = () => process.stderr.write('Private enrollment stopped; no credential details were printed.\n');
  try {
    if (!process.stdin.isTTY || !process.stdout.isTTY || process.argv.length !== 2) {
      throw new EnrollmentError('Run this directly with docker exec -it in the private Session Manager terminal; pass no arguments.');
    }
    if (process.cwd() !== '/app') throw new EnrollmentError('Run with Docker working directory /app.');
    console.error = safeError; // Database errors must not echo connection URIs.
    require('/app/node_modules/module-alias')({ base: '/app/api' });
    const mongoose = require('/app/node_modules/mongoose');
    const schemas = require('/app/node_modules/@librechat/data-schemas');
    // Only this one-off CLI process is muted; the running server is untouched.
    for (const name of ['error', 'warn', 'info', 'debug', 'verbose', 'silly', 'http', 'log']) {
      if (typeof schemas.logger?.[name] === 'function') schemas.logger[name] = () => {};
    }
    const { User } = schemas.createModels(mongoose);
    const helpers = require('/app/config/helpers');
    const auth = require('/app/api/server/services/AuthService');
    const { registerSchema } = require('/app/api/strategies/validators');
    installGuards({ helpers, User, auth, registerSchema });
    process.stdout.write('Fresh first account: this user becomes LibreChat application ADMIN. AWS permissions are unchanged.\n');
    // Preserve the upstream CLI flow, skip email verification delivery, and
    // never supply email, name, username or password in command arguments.
    process.argv = ['node', path.resolve('/app/config/create-user.js'), '--email-verified=true'];
    require('/app/config/create-user.js');
  } catch (error) {
    process.stderr.write(error instanceof EnrollmentError ? error.message + '\n' : 'Pinned enrollment interfaces could not be loaded; stop for review.\n');
    process.exitCode = 1;
  }
}

module.exports = { installGuards, EnrollmentError };
if (require.main === module) main();
