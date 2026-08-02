const crypto = require("node:crypto");
const { performance } = require("node:perf_hooks");
const { TableClient } = require("@azure/data-tables");

const FUNCTION_VERSION = "v3.0-azure-live-replay";
const SENSOR_TABLE = "SensorTelemetry";
const BENCHMARK_TABLE = "BenchmarkTelemetry";

function responseHeaders() {
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-functions-key, Authorization",
        "Content-Type": "application/json"
    };
}

function setResponse(context, status, body) {
    context.res = {
        status,
        headers: responseHeaders(),
        body
    };
}

function safeTableKey(value, fallback) {
    const normalized = String(value ?? fallback)
        .replace(/[\\/#?\u0000-\u001f\u007f-\u009f]/g, "_")
        .slice(0, 256);
    return normalized || fallback;
}

function asFiniteNumber(value, fieldName) {
    if (value === undefined || value === null || value === "") return undefined;
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
        throw new TypeError(`${fieldName} must be a finite number`);
    }
    return parsed;
}

function addElectricalReadings(entity, source, prefix = "") {
    const mappings = [
        ["suhu", "suhu"],
        ["kelembaban", "kelembaban"],
        ["tegangan", "tegangan"],
        ["arus", "arus"],
        ["daya", "daya"]
    ];

    for (const [inputName, outputName] of mappings) {
        const value = asFiniteNumber(source[inputName], `${prefix}${inputName}`);
        if (value !== undefined) entity[outputName] = value;
    }
}

function validateBenchmarkMetadata(benchmark) {
    if (!benchmark || benchmark.mode !== "historical_replay") return null;

    const required = ["runId", "messageId", "sourceRowId", "replayBlockId", "sourceTimestamp", "replaySentAt"];
    const missing = required.filter((field) => benchmark[field] === undefined || benchmark[field] === null || benchmark[field] === "");
    if (missing.length > 0) {
        throw new TypeError(`Missing benchmark metadata: ${missing.join(", ")}`);
    }

    for (const field of ["sourceTimestamp", "replaySentAt"]) {
        if (Number.isNaN(Date.parse(benchmark[field]))) {
            throw new TypeError(`benchmark.${field} must be an ISO-8601 timestamp`);
        }
    }

    return benchmark;
}

function createBaseEntity(sensorData, benchmark, receivedAt) {
    const gatewayId = sensorData.deviceId || benchmark?.gatewayId || "RASPBERRY_PI_GATEWAY_001";
    const randomSuffix = crypto.randomUUID();

    if (benchmark) {
        return {
            tableName: BENCHMARK_TABLE,
            entity: {
                partitionKey: safeTableKey(benchmark.runId, "azure-live-replay"),
                rowKey: safeTableKey(`${benchmark.messageId}-${randomSuffix}`, randomSuffix),
                dataType: "historical_replay_probe",
                measurementScope: "azure_public_cloud_https_function_and_table_storage",
                physicalSensorLive: false,
                benchmarkRunId: String(benchmark.runId),
                benchmarkMessageId: String(benchmark.messageId),
                sourceRowId: String(benchmark.sourceRowId),
                replayBlockId: String(benchmark.replayBlockId),
                sourceTimestamp: new Date(benchmark.sourceTimestamp).toISOString(),
                replaySentAt: new Date(benchmark.replaySentAt).toISOString(),
                sourceType: "historical_replay",
                gatewayId: String(gatewayId),
                sourceNodeId: String(benchmark.sourceNodeId || "ESP32_ENERGY_MONITOR_001"),
                sourceNodeAttribution: String(
                    benchmark.sourceNodeAttribution || "architecture_metadata_not_row_level_field"
                ),
                receivedAt,
                functionVersion: FUNCTION_VERSION
            }
        };
    }

    const eventTimestamp = sensorData.timestamp || receivedAt;
    if (Number.isNaN(Date.parse(eventTimestamp))) {
        throw new TypeError("timestamp must be an ISO-8601 timestamp");
    }

    return {
        tableName: SENSOR_TABLE,
        entity: {
            partitionKey: safeTableKey(gatewayId, "RASPBERRY_PI_GATEWAY_001"),
            rowKey: safeTableKey(`${Date.now()}-${randomSuffix}`, randomSuffix),
            eventTimestamp: new Date(eventTimestamp).toISOString(),
            deviceId: String(gatewayId),
            receivedAt,
            functionVersion: FUNCTION_VERSION
        }
    };
}

function populateEntity(entity, sensorData) {
    if (sensorData.esp32) {
        entity.dataType = entity.dataType || "aggregated_gateway";
        addElectricalReadings(entity, sensorData.esp32, "esp32.");

        if (sensorData.esp32.tinyml) {
            const tinyml = sensorData.esp32.tinyml;
            if (tinyml.anomaly !== undefined) entity.tinyml_anomaly = Boolean(tinyml.anomaly);
            const confidence = asFiniteNumber(tinyml.confidence, "esp32.tinyml.confidence");
            if (confidence !== undefined) entity.tinyml_confidence = confidence;
            if (tinyml.power_mode !== undefined) entity.tinyml_power_mode = String(tinyml.power_mode);
            const inferenceUs = asFiniteNumber(tinyml.inference_us, "esp32.tinyml.inference_us");
            if (inferenceUs !== undefined) entity.tinyml_inference_us = inferenceUs;
        }

        if (sensorData.esp32.ac) {
            const acPower = asFiniteNumber(sensorData.esp32.ac.power, "esp32.ac.power");
            if (acPower !== undefined) entity.ac_power = acPower;
            if (sensorData.esp32.ac.mode !== undefined) entity.ac_mode = String(sensorData.esp32.ac.mode);
            const setpoint = asFiniteNumber(sensorData.esp32.ac.setpoint, "esp32.ac.setpoint");
            if (setpoint !== undefined) entity.ac_setpoint = setpoint;
        }

        if (sensorData.camera) {
            const peopleCount = asFiniteNumber(sensorData.camera.people_count, "camera.people_count");
            if (peopleCount !== undefined) entity.people_count = Math.trunc(peopleCount);
            const fps = asFiniteNumber(sensorData.camera.fps, "camera.fps");
            if (fps !== undefined) entity.camera_fps = fps;
        }

        if (sensorData.gateway) {
            const gatewayMappings = [
                ["cpu_temp_c", "gateway_cpu_temp"],
                ["cpu_percent", "gateway_cpu_percent"],
                ["memory_percent", "gateway_memory_percent"],
                ["disk_percent", "gateway_disk_percent"]
            ];
            for (const [inputName, outputName] of gatewayMappings) {
                const value = asFiniteNumber(sensorData.gateway[inputName], `gateway.${inputName}`);
                if (value !== undefined) entity[outputName] = value;
            }
        }

        if (sensorData.batch?.count !== undefined) {
            entity.batch_count = Math.trunc(asFiniteNumber(sensorData.batch.count, "batch.count"));
        }
        return;
    }

    entity.dataType = entity.dataType || "single_sensor";
    addElectricalReadings(entity, sensorData);
    if (sensorData.jumlahOrang !== undefined) {
        entity.jumlahOrang = Math.trunc(asFiniteNumber(sensorData.jumlahOrang, "jumlahOrang"));
    }
    if (sensorData.status_tegangan !== undefined) entity.status_tegangan = String(sensorData.status_tegangan);
    if (sensorData.status_arus !== undefined) entity.status_arus = String(sensorData.status_arus);
}

function isMissingTableError(error) {
    return error?.statusCode === 404 || error?.code === "TableNotFound";
}

async function createEntityWithTableRecovery(tableClient, entity) {
    try {
        await tableClient.createEntity(entity);
        return;
    } catch (error) {
        if (!isMissingTableError(error)) throw error;
    }

    try {
        await tableClient.createTable();
    } catch (error) {
        if (error?.statusCode !== 409) throw error;
    }
    await tableClient.createEntity(entity);
}

/**
 * Protected HTTP ingestion endpoint.
 *
 * Historical replay probes are isolated in BenchmarkTelemetry so they cannot
 * be mistaken for new physical sensor observations in SensorTelemetry.
 */
module.exports = async function (context, req) {
    const startedAt = performance.now();
    const receivedAt = new Date().toISOString();

    if (req.method === "OPTIONS") {
        setResponse(context, 200, { success: true, functionVersion: FUNCTION_VERSION });
        return;
    }

    if (!req.body || typeof req.body !== "object" || Array.isArray(req.body)) {
        setResponse(context, 400, {
            error: "Request body is required",
            code: "INVALID_REQUEST_BODY",
            functionVersion: FUNCTION_VERSION
        });
        return;
    }

    const sensorData = req.body;
    if (sensorData.suhu === undefined && sensorData.jumlahOrang === undefined && !sensorData.esp32) {
        setResponse(context, 400, {
            error: "Invalid sensor data - need suhu, jumlahOrang, or esp32",
            code: "INVALID_SENSOR_DATA",
            functionVersion: FUNCTION_VERSION
        });
        return;
    }

    const connectionString = process.env.STORAGE_CONNECTION_STRING;
    if (!connectionString) {
        context.log.error("STORAGE_CONNECTION_STRING is not configured");
        setResponse(context, 500, {
            error: "Storage configuration is unavailable",
            code: "STORAGE_NOT_CONFIGURED",
            functionVersion: FUNCTION_VERSION
        });
        return;
    }

    try {
        const benchmark = validateBenchmarkMetadata(sensorData.benchmark);
        const { tableName, entity } = createBaseEntity(sensorData, benchmark, receivedAt);
        populateEntity(entity, sensorData);

        const tableClient = TableClient.fromConnectionString(connectionString, tableName);
        const storageStartedAt = performance.now();
        await createEntityWithTableRecovery(tableClient, entity);
        const persistedAt = new Date().toISOString();
        const storageWriteMs = performance.now() - storageStartedAt;
        const serverProcessingMs = performance.now() - startedAt;

        context.log(
            `Saved ${entity.dataType} to ${tableName}; functionVersion=${FUNCTION_VERSION}; ` +
            `serverProcessingMs=${serverProcessingMs.toFixed(3)}`
        );

        setResponse(context, 200, {
            success: true,
            message: "Data saved",
            functionVersion: FUNCTION_VERSION,
            dataType: entity.dataType,
            table: tableName,
            eventTimestamp: entity.eventTimestamp || entity.sourceTimestamp,
            receivedAt,
            persistedAt,
            storageWriteMs: Number(storageWriteMs.toFixed(3)),
            serverProcessingMs: Number(serverProcessingMs.toFixed(3)),
            benchmark: benchmark ? {
                mode: "historical_replay",
                runId: entity.benchmarkRunId,
                messageId: entity.benchmarkMessageId,
                sourceRowId: entity.sourceRowId,
                replayBlockId: entity.replayBlockId,
                physicalSensorLive: false
            } : null
        });
    } catch (error) {
        const isValidationError = error instanceof TypeError;
        context.log.error(`SaveSensorData ${FUNCTION_VERSION} failed`, error);
        setResponse(context, isValidationError ? 400 : 500, {
            error: isValidationError ? error.message : "Storage write failed",
            code: isValidationError ? "INVALID_PAYLOAD" : "STORAGE_WRITE_FAILED",
            functionVersion: FUNCTION_VERSION
        });
    }
};

module.exports.FUNCTION_VERSION = FUNCTION_VERSION;
