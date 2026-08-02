const test = require("node:test");
const assert = require("node:assert/strict");
const { TableClient } = require("@azure/data-tables");

const originalFactory = TableClient.fromConnectionString;
const originalConnectionString = process.env.STORAGE_CONNECTION_STRING;
const handler = require("../SaveSensorData/index.js");

function makeContext() {
    const log = () => {};
    log.error = () => {};
    return { log, res: null };
}

function installFakeTable({ createTableError, createEntityError, createEntityErrors = [] } = {}) {
    const calls = [];
    TableClient.fromConnectionString = (connectionString, tableName) => ({
        async createTable() {
            calls.push({ operation: "createTable", connectionString, tableName });
            if (createTableError) throw createTableError;
        },
        async createEntity(entity) {
            calls.push({ operation: "createEntity", tableName, entity });
            if (createEntityErrors.length > 0) throw createEntityErrors.shift();
            if (createEntityError) throw createEntityError;
        }
    });
    return calls;
}

test.beforeEach(() => {
    process.env.STORAGE_CONNECTION_STRING = "UseDevelopmentStorage=true";
});

test.afterEach(() => {
    TableClient.fromConnectionString = originalFactory;
    if (originalConnectionString === undefined) {
        delete process.env.STORAGE_CONNECTION_STRING;
    } else {
        process.env.STORAGE_CONNECTION_STRING = originalConnectionString;
    }
});

test("empty request is rejected before storage access", async () => {
    let factoryCalled = false;
    TableClient.fromConnectionString = () => {
        factoryCalled = true;
    };
    const context = makeContext();

    await handler(context, { method: "POST", body: null });

    assert.equal(context.res.status, 400);
    assert.equal(context.res.body.code, "INVALID_REQUEST_BODY");
    assert.equal(factoryCalled, false);
});

test("legacy sensor payload uses eventTimestamp instead of reserved Timestamp", async () => {
    const calls = installFakeTable();
    const context = makeContext();
    const sourceTimestamp = "2026-05-17T00:00:00.000Z";

    await handler(context, {
        method: "POST",
        body: {
            deviceId: "ESP32_ENERGY_MONITOR_001",
            timestamp: sourceTimestamp,
            suhu: "27.5",
            kelembaban: "70",
            tegangan: "220.1",
            arus: "0.15",
            daya: "33.02"
        }
    });

    assert.equal(context.res.status, 200);
    assert.equal(context.res.body.table, "SensorTelemetry");
    const insert = calls.find((call) => call.operation === "createEntity");
    assert.equal(insert.entity.eventTimestamp, sourceTimestamp);
    assert.equal(Object.hasOwn(insert.entity, "timestamp"), false);
    assert.equal(insert.entity.daya, 33.02);
});

test("historical replay is isolated with explicit provenance", async () => {
    const calls = installFakeTable();
    const context = makeContext();

    await handler(context, {
        method: "POST",
        body: {
            deviceId: "RASPBERRY_PI_GATEWAY_001",
            esp32: { suhu: 28, kelembaban: 72, tegangan: 221, arus: 0.2, daya: 44.2 },
            camera: { people_count: 2 },
            benchmark: {
                mode: "historical_replay",
                runId: "azure-live-20260802",
                messageId: "msg-0001",
                sourceRowId: 42,
                replayBlockId: 0,
                sourceTimestamp: "2026-05-17T00:00:00.000Z",
                replaySentAt: "2026-08-02T16:00:00.000Z",
                sourceNodeId: "ESP32_ENERGY_MONITOR_001",
                sourceNodeAttribution: "architecture_metadata_not_row_level_field"
            }
        }
    });

    assert.equal(context.res.status, 200);
    assert.equal(context.res.body.table, "BenchmarkTelemetry");
    assert.equal(context.res.body.benchmark.physicalSensorLive, false);
    const insert = calls.find((call) => call.operation === "createEntity");
    assert.equal(insert.tableName, "BenchmarkTelemetry");
    assert.equal(insert.entity.sourceType, "historical_replay");
    assert.equal(insert.entity.sourceRowId, "42");
    assert.equal(insert.entity.physicalSensorLive, false);
    assert.equal(insert.entity.sourceNodeAttribution, "architecture_metadata_not_row_level_field");
});

test("missing table is created once and the entity write is retried", async () => {
    const calls = installFakeTable({ createEntityErrors: [{ statusCode: 404, code: "TableNotFound" }] });
    const context = makeContext();

    await handler(context, { method: "POST", body: { suhu: 25 } });

    assert.equal(context.res.status, 200);
    assert.deepEqual(
        calls.map((call) => call.operation),
        ["createEntity", "createTable", "createEntity"],
    );
});

test("incomplete replay provenance is rejected", async () => {
    const calls = installFakeTable();
    const context = makeContext();

    await handler(context, {
        method: "POST",
        body: {
            esp32: { daya: 10 },
            benchmark: { mode: "historical_replay", runId: "missing-fields" }
        }
    });

    assert.equal(context.res.status, 400);
    assert.equal(context.res.body.code, "INVALID_PAYLOAD");
    assert.equal(calls.length, 0);
});

test("storage failures return a stable error without exposing provider details", async () => {
    const providerMessage = "AuthenticationFailed secret-redacted";
    installFakeTable({ createEntityError: new Error(providerMessage) });
    const context = makeContext();

    await handler(context, { method: "POST", body: { suhu: 25 } });

    assert.equal(context.res.status, 500);
    assert.equal(context.res.body.code, "STORAGE_WRITE_FAILED");
    assert.equal(JSON.stringify(context.res.body).includes(providerMessage), false);
});

test("OPTIONS returns CORS metadata without storage access", async () => {
    delete process.env.STORAGE_CONNECTION_STRING;
    const context = makeContext();

    await handler(context, { method: "OPTIONS" });

    assert.equal(context.res.status, 200);
    assert.equal(context.res.headers["Access-Control-Allow-Methods"], "POST, OPTIONS");
});
