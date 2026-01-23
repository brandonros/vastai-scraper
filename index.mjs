import { appendFile, mkdir, access, constants } from 'node:fs/promises';
import { join } from 'node:path';
import ky from 'ky';
import { stringify } from 'csv-stringify/sync';
import cron from 'node-cron';
import dayjs from 'dayjs';
import pino from 'pino';

const logger = pino();

// =============================================================================
// Configuration
// =============================================================================

const CONFIG = {
  baseUrl: 'https://cloud.vast.ai/api/v0/bundles/',
  dataDir: process.env.DATA_DIR || './data',
  schedule: process.env.SCHEDULE || '*/5 * * * *',
  types: ['ask', 'bid'],
  headers: {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'user-agent': process.env.USER_AGENT || 'vastai-scraper/1.0',
  },
  query: {
    gpu_name: { in: ['RTX 5090'] },
    disk_space: { gte: 8 },
    allocated_storage: 8,
    duration: { gte: 21600 },
    rentable: { eq: true },
    verified: { eq: true },
    reliability2: { gte: 0.9 },
    order: [['dph_total', 'asc'], ['total_flops', 'asc']],
    sort_option: { 0: ['dph_total', 'asc'], 1: ['total_flops', 'asc'] },
    limit: 512,
    resource_type: 'gpu',
  },
};

const SCHEMA = [
  { key: 'timestamp' },
  { key: 'id' },
  { key: 'host_id' },
  { key: 'machine_id' },
  { key: 'dph_total', decimals: 4 },
  { key: 'min_bid', decimals: 4 },
  { key: 'num_gpus' },
  { key: 'gpu_ram' },
  { key: 'cpu_cores' },
  { key: 'cpu_ram' },
  { key: 'cpu_ghz', decimals: 2 },
  { key: 'disk_space', decimals: 1 },
  { key: 'disk_bw', decimals: 1 },
  { key: 'inet_up', decimals: 1 },
  { key: 'inet_down', decimals: 1 },
  { key: 'geolocation' },
  { key: 'reliability2', decimals: 4 },
  { key: 'pci_gen' },
  { key: 'pcie_bw', decimals: 1 },
];

const COLUMNS = SCHEMA.map(f => f.key);

// =============================================================================
// HTTP
// =============================================================================

const vastClient = ky.create({
  prefixUrl: CONFIG.baseUrl,
  headers: CONFIG.headers,
  timeout: 30000,
  retry: {
    limit: 3,
    statusCodes: [408, 429, 500, 502, 503, 504],
    backoffLimit: 10000,
  },
  hooks: {
    beforeRetry: [
      ({ retryCount, error }) => {
        logger.warn({ retryCount, error: error.message }, 'Retrying request');
      },
    ],
  },
});

const healthcheckClient = ky.create({
  timeout: 10000,
  retry: 0,
});

async function fetchOffers(type) {
  const query = { ...CONFIG.query, type };
  const data = await vastClient.get('', {
    searchParams: { q: JSON.stringify(query) },
  }).json();
  return data.offers ?? [];
}

// =============================================================================
// CSV Transform
// =============================================================================

function formatValue(field, value) {
  if (value == null) return '';
  if (field.decimals != null && typeof value === 'number') {
    return value.toFixed(field.decimals);
  }
  return value;
}

function transformOffer(timestamp, offer) {
  const row = {};
  for (const field of SCHEMA) {
    const value = field.key === 'timestamp' ? timestamp : offer[field.key];
    row[field.key] = formatValue(field, value);
  }
  return row;
}

function toCSV(rows, includeHeader) {
  return stringify(rows, {
    header: includeHeader,
    columns: COLUMNS,
  });
}

// =============================================================================
// File I/O
// =============================================================================

async function fileExists(path) {
  try {
    await access(path, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

function getDailyFilename(type) {
  return join(CONFIG.dataDir, `${dayjs().format('YYYY-MM-DD')}-${type}s.csv`);
}

async function writeOffers(filename, rows) {
  const needsHeader = !(await fileExists(filename));
  const content = toCSV(rows, needsHeader);
  await appendFile(filename, content);
}

// =============================================================================
// Orchestration
// =============================================================================

async function scrapeType(type) {
  const timestamp = dayjs().toISOString();
  try {
    const offers = await fetchOffers(type);

    if (offers.length === 0) {
      logger.info({ type }, 'No offers found');
      return true;
    }

    const rows = offers.map(offer => transformOffer(timestamp, offer));
    await writeOffers(getDailyFilename(type), rows);

    logger.info({ type, count: offers.length }, 'Fetched offers');
    return true;
  } catch (error) {
    logger.error({ type, error: error.message }, 'Scrape failed');
    return false;
  }
}

async function scrapeAll() {
  const results = await Promise.all(CONFIG.types.map(scrapeType));
  const allSucceeded = results.every(Boolean);

  if (allSucceeded && process.env.HEALTHCHECK_URL) {
    await healthcheckClient.get(process.env.HEALTHCHECK_URL).catch(e => {
      logger.warn({ error: e.message }, 'Healthcheck ping failed');
    });
  }
}

async function main() {
  await mkdir(CONFIG.dataDir, { recursive: true });
  logger.info({ schedule: CONFIG.schedule }, 'Starting vast.ai scraper');

  await scrapeAll();
  cron.schedule(CONFIG.schedule, scrapeAll);
}

function shutdown(signal) {
  logger.info({ signal }, 'Shutting down');
  process.exit(0);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

main();
