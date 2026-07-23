/**
 * Online AC Recommendation with Online Learning
 *
 * Implements real-time ML prediction with model updates
 * - Load base model weights
 * - Update model with new data
 * - Persist state to Blob Storage
 *
 * Note: Full River library integration requires Python runtime
 * This JS version implements similar online learning logic
 */

const { TableClient } = require("@azure/data-tables");
const { BlobServiceClient } = require("@azure/storage-blob");

// Model state
let modelState = {
    dataCount: 0,
    weights: {
        suhu: -0.3,
        kelembaban: -0.01,
        daya: -0.001,
        people: -0.05,
        hour: 0.05,
        base_temp: 24.0
    },
    lastUpdate: null,
    version: "1.0"
};

// Constants
const LEARNING_RATE = 0.01;
const BASE_TEMP = 24.0;

// Blob storage for state persistence
const STORAGE_CONNECTION_STRING = process.env.STORAGE_CONNECTION_STRING || process.env.AzureWebJobsStorage;
const STATE_CONTAINER = "ml-model-state";
const STATE_BLOB = "online_ac_recommender_state.json";

// Load model state from blob storage
async function loadModelState() {
    if (!STORAGE_CONNECTION_STRING) {
        console.log("[OnlineAC] No storage connection, using default state");
        return;
    }

    try {
        const blobServiceClient = BlobServiceClient.fromConnectionString(STORAGE_CONNECTION_STRING);
        const containerClient = blobServiceClient.getContainerClient(STATE_CONTAINER);
        const blobClient = containerClient.getBlobClient(STATE_BLOB);

        const exists = await blobClient.exists();
        if (exists) {
            const response = await blobClient.download();
            const content = await response.blobBody;
            const text = await content.text();
            const state = JSON.parse(text);

            modelState = {
                ...modelState,
                ...state
            };

            console.log(`[OnlineAC] Loaded state: ${modelState.dataCount} data points`);
        }
    } catch (error) {
        console.log("[OnlineAC] Error loading state:", error.message);
    }
}

// Save model state to blob storage
async function saveModelState() {
    if (!STORAGE_CONNECTION_STRING) {
        console.log("[OnlineAC] No storage connection, state not persisted");
        return;
    }

    try {
        const blobServiceClient = BlobServiceClient.fromConnectionString(STORAGE_CONNECTION_STRING);
        const containerClient = blobServiceClient.getContainerClient(STATE_CONTAINER);

        // Create container if not exists
        await containerClient.createIfNotExists();

        const blobClient = containerClient.getBlobClient(STATE_BLOB);
        const stateJson = JSON.stringify(modelState, null, 2);

        await blobClient.upload(Buffer.from(stateJson), stateJson.length, {
            overwrite: true
        });

        console.log(`[OnlineAC] State saved: ${modelState.dataCount} data points`);
    } catch (error) {
        console.log("[OnlineAC] Error saving state:", error.message);
    }
}

// Predict AC recommendation
function predict(suhu, kelembaban, daya, jumlahOrang, hour) {
    // Default values
    hour = hour !== undefined ? hour : new Date().getHours();
    jumlahOrang = jumlahOrang || 0;
    daya = daya || 0;
    kelembaban = kelembaban || 50;
    suhu = suhu || 25;

    // Calculate recommended temp using online learning model
    let recommendedTemp = modelState.weights.base_temp;

    // Temperature factor
    if (suhu > 25) {
        recommendedTemp += (suhu - 25) * modelState.weights.suhu;
    }

    // Humidity factor
    if (kelembaban > 60) {
        recommendedTemp += (kelembaban - 60) * modelState.weights.kelembaban;
    }

    // Power factor
    if (daya > 100) {
        recommendedTemp += (daya - 100) * modelState.weights.daya;
    }

    // Hour factor (peak hours)
    if (hour >= 8 && hour <= 17) {
        recommendedTemp -= 0.5 + modelState.weights.hour;
    } else if (hour >= 22 || hour < 6) {
        recommendedTemp += 0.3;
    }

    // People factor
    if (jumlahOrang > 0) {
        recommendedTemp += jumlahOrang * modelState.weights.people;
    }

    // Clamp to comfort range
    recommendedTemp = Math.max(18, Math.min(28, recommendedTemp));

    return Math.round(recommendedTemp * 10) / 10;
}

// Online learning: Update model weights based on actual data
function updateModel(suhu, kelembaban, daya, jumlahOrang, actualTemp, hour) {
    hour = hour !== undefined ? hour : new Date().getHours();

    // Get predicted value
    const predictedTemp = predict(suhu, kelembaban, daya, jumlahOrang, hour);

    // Calculate error
    const error = actualTemp - predictedTemp;

    // Adaptive learning rate (decreases over time for stability)
    const adaptiveLR = LEARNING_RATE / (1 + modelState.dataCount * 0.001);

    // Update weights using gradient descent
    if (suhu > 25) {
        modelState.weights.suhu += adaptiveLR * error * (suhu - 25) * -0.1;
    }
    if (kelembaban > 60) {
        modelState.weights.kelembaban += adaptiveLR * error * (kelembaban - 60) * -0.1;
    }
    if (daya > 100) {
        modelState.weights.daya += adaptiveLR * error * (daya - 100) * -0.001;
    }
    if (hour >= 8 && hour <= 17) {
        modelState.weights.hour += adaptiveLR * error * -0.05;
    }
    if (jumlahOrang > 0) {
        modelState.weights.people += adaptiveLR * error * jumlahOrang * 0.01;
    }

    // Update base temp
    modelState.weights.base_temp += adaptiveLR * error * 0.1;

    // Clamp weights to reasonable range
    modelState.weights.suhu = Math.max(-1, Math.min(0, modelState.weights.suhu));
    modelState.weights.kelembaban = Math.max(-0.1, Math.min(0, modelState.weights.kelembaban));
    modelState.weights.daya = Math.max(-0.01, Math.min(0, modelState.weights.daya));

    // Increment data count
    modelState.dataCount++;
    modelState.lastUpdate = new Date().toISOString();

    // Save state periodically (every 50 data points)
    if (modelState.dataCount % 50 === 0) {
        saveModelState();
    }

    return {
        predicted: predictedTemp,
        actual: actualTemp,
        error: Math.abs(error),
        dataCount: modelState.dataCount
    };
}

// Get confidence based on data count
function getConfidence() {
    if (modelState.dataCount < 10) return 0.5;
    if (modelState.dataCount < 50) return 0.7;
    if (modelState.dataCount < 100) return 0.85;
    return 0.96;
}

// Get comfort level
function getComfortLevel(temp) {
    if (temp <= 21) return { level: "COOL", emoji: "🥶", reason: "AC lebih dingin karena ruangan panas atau padat" };
    if (temp <= 23) return { level: "COOL_COMFORTABLE", emoji: "😌", reason: "Slightly cool untuk kenyamanan maksimal" };
    if (temp <= 25) return { level: "COMFORTABLE", emoji: "😊", reason: "Setting standar untuk kenyamanan dan efisiensi energi" };
    if (temp <= 26) return { level: "WARM_COMFORTABLE", emoji: "🙂", reason: "Sedikit lebih hangat untuk penghematan energi" };
    return { level: "WARM", emoji: "☀️", reason: "Setting hemat energi karena ruangan sudah nyaman" };
}

// Main Azure Function handler
module.exports = async function (context, req) {
    // CORS headers
    context.res = {
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        }
    };

    // Handle CORS preflight
    if (req.method === 'OPTIONS') {
        context.res.status = 200;
        return;
    }

    try {
        const action = req.params.action || 'predict';

        switch (action) {
            case 'predict':
                await handlePredict(context, req);
                break;
            case 'update':
                await handleUpdate(context, req);
                break;
            case 'status':
                await handleStatus(context);
                break;
            default:
                context.res.status = 400;
                context.res.body = { error: "Invalid action. Use: predict, update, or status" };
        }
    } catch (error) {
        context.log.error("[OnlineAC] Error:", error);
        context.res.status = 500;
        context.res.body = { error: error.message };
    }
};

// Handle prediction request
async function handlePredict(context, req) {
    // Load state on first request
    if (modelState.dataCount === 0) {
        await loadModelState();
    }

    const { suhu, kelembaban, daya, jumlahOrang, jam } = req.body || {};

    if (suhu === undefined || kelembaban === undefined) {
        context.res.status = 400;
        context.res.body = { error: "Missing required fields: suhu, kelembaban" };
        return;
    }

    const hour = jam !== undefined ? jam : new Date().getHours();
    const recommendedTemp = predict(suhu, kelembaban, daya, jumlahOrang, hour);
    const comfort = getComfortLevel(recommendedTemp);

    // Calculate energy saving
    const standardTemp = 24;
    const tempDiff = recommendedTemp - standardTemp;
    const energySaving = Math.max(0, tempDiff * 3);

    context.res.status = 200;
    context.res.body = {
        success: true,
        data: {
            recommendedTemp,
            comfortLevel: comfort.level,
            comfortEmoji: comfort.emoji,
            reason: comfort.reason,
            energySavingPercent: Math.round(energySaving * 10) / 10,
            confidence: getConfidence(),
            factors: {
                suhu,
                kelembaban,
                daya: daya || 0,
                jumlahOrang: jumlahOrang || 0,
                jam: hour
            },
            model_info: {
                online_learning: true,
                version: modelState.version,
                data_count: modelState.dataCount,
                last_update: modelState.lastUpdate
            },
            timestamp: new Date().toISOString()
        }
    };
}

// Handle update request (for model training)
async function handleUpdate(context, req) {
    const { suhu, kelembaban, daya, jumlahOrang, actualTemp, jam } = req.body || {};

    if (suhu === undefined || kelembaban === undefined || actualTemp === undefined) {
        context.res.status = 400;
        context.res.body = { error: "Missing required fields: suhu, kelembaban, actualTemp" };
        return;
    }

    const hour = jam !== undefined ? jam : new Date().getHours();
    const result = updateModel(suhu, kelembaban, daya, jumlahOrang, actualTemp, hour);

    context.res.status = 200;
    context.res.body = {
        success: true,
        data: {
            training_result: result,
            message: `Model updated with data #${result.dataCount}`,
            current_weights: modelState.weights
        }
    };
}

// Handle status request
async function handleStatus(context) {
    if (modelState.dataCount === 0) {
        await loadModelState();
    }

    context.res.status = 200;
    context.res.body = {
        success: true,
        data: {
            status: "running",
            online_learning: true,
            data_count: modelState.dataCount,
            last_update: modelState.lastUpdate,
            weights: modelState.weights,
            confidence: getConfidence(),
            version: modelState.version
        }
    };
}