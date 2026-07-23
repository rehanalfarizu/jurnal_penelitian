const { TableClient } = require("@azure/data-tables");

/**
 * Azure Function: Save Sensor Data (Protected)
 * Receives sensor data via HTTP POST and stores to Azure Storage Table
 * Supports:
 * - Single ESP32 payload (legacy)
 * - Aggregated gateway payload (ESP32 + Camera + Gateway health)
 */
module.exports = async function (context, req) {
    // Enable CORS
    context.res = {
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, x-functions-key, Authorization',
            'Content-Type': 'application/json'
        }
    };

    // Handle OPTIONS preflight request
    if (req.method === 'OPTIONS') {
        context.res.status = 200;
        return;
    }

    context.log('Sensor data received via HTTP');

    try {
        // Validasi request body
        if (!req.body) {
            context.log.error('No request body provided');
            context.res.status = 400;
            context.res.body = { error: "Request body is required" };
            return;
        }

        const sensorData = req.body;
        context.log('Received:', JSON.stringify(sensorData));

        // Validasi data sensor
        if (sensorData.suhu === undefined && sensorData.jumlahOrang === undefined && !sensorData.esp32) {
            context.res.status = 400;
            context.res.body = { error: "Invalid sensor data - need suhu, jumlahOrang, or esp32" };
            return;
        }

        const connectionString = process.env.STORAGE_CONNECTION_STRING;

        if (!connectionString) {
            throw new Error("STORAGE_CONNECTION_STRING not configured");
        }

        const tableClient = TableClient.fromConnectionString(connectionString, "SensorTelemetry");

        // Create table if not exists
        await tableClient.createTable().catch(() => {});

        const deviceId = sensorData.deviceId || "RASPBERRY_PI_GATEWAY_001";
        const timestamp = sensorData.timestamp || new Date().toISOString();

        // Check if aggregated payload (from RPi Gateway)
        if (sensorData.esp32) {
            // Save aggregated gateway data
            const entity = {
                partitionKey: deviceId,
                rowKey: Date.now().toString() + Math.random().toString(36).substring(2, 7),
                timestamp: timestamp,
                deviceId: deviceId,
                receivedAt: new Date().toISOString(),
                dataType: 'aggregated_gateway'
            };

            // ESP32 sensor data
            const esp32 = sensorData.esp32;
            if (esp32.suhu !== undefined) entity.suhu = parseFloat(esp32.suhu);
            if (esp32.kelembaban !== undefined) entity.kelembaban = parseFloat(esp32.kelembaban);
            if (esp32.tegangan !== undefined) entity.tegangan = parseFloat(esp32.tegangan);
            if (esp32.arus !== undefined) entity.arus = parseFloat(esp32.arus);
            if (esp32.daya !== undefined) entity.daya = parseFloat(esp32.daya);

            // TinyML data
            if (esp32.tinyml) {
                entity.tinyml_anomaly = esp32.tinyml.anomaly;
                entity.tinyml_confidence = esp32.tinyml.confidence;
                entity.tinyml_power_mode = esp32.tinyml.power_mode;
                entity.tinyml_inference_us = esp32.tinyml.inference_us;
            }

            // AC data
            if (esp32.ac) {
                entity.ac_power = esp32.ac.power;
                entity.ac_mode = esp32.ac.mode;
                entity.ac_setpoint = esp32.ac.setpoint;
            }

            // ESP32 health
            if (esp32.health) {
                entity.esp32_temp_c = esp32.health.esp32_temp_c;
                entity.free_heap_bytes = esp32.health.free_heap_bytes;
                entity.wifi_rssi_dbm = esp32.health.wifi_rssi_dbm;
            }

            // Camera data
            if (sensorData.camera) {
                entity.people_count = sensorData.camera.people_count;
                entity.camera_fps = sensorData.camera.fps;
            }

            // Gateway health
            if (sensorData.gateway) {
                const gw = sensorData.gateway;
                entity.gateway_cpu_temp = gw.cpu_temp_c;
                entity.gateway_cpu_percent = gw.cpu_percent;
                entity.gateway_memory_percent = gw.memory_percent;
                entity.gateway_disk_percent = gw.disk_percent;
            }

            // Batch info
            if (sensorData.batch) {
                entity.batch_count = sensorData.batch.count;
            }

            await tableClient.createEntity(entity);

            context.log('Aggregated gateway data saved');
            context.log('   - Suhu:', esp32.suhu);
            context.log('   - Kelembaban:', esp32.kelembaban);
            context.log('   - People count:', sensorData.camera ? sensorData.camera.people_count : 'N/A');

        } else {
            // Legacy single sensor payload (direct from ESP32 or other)
            const entity = {
                partitionKey: deviceId,
                rowKey: Date.now().toString() + Math.random().toString(36).substring(2, 7),
                timestamp: timestamp,
                deviceId: deviceId,
                receivedAt: new Date().toISOString()
            };

            if (sensorData.suhu !== undefined) {
                entity.suhu = parseFloat(sensorData.suhu);
                entity.kelembaban = parseFloat(sensorData.kelembaban || 0);
                entity.tegangan = parseFloat(sensorData.tegangan || 0);
                entity.arus = parseFloat(sensorData.arus || 0);
                entity.daya = parseFloat(sensorData.daya || 0);
                entity.status_tegangan = sensorData.status_tegangan || "unknown";
                entity.status_arus = sensorData.status_arus || "unknown";
            }

            if (sensorData.jumlahOrang !== undefined) {
                entity.jumlahOrang = parseInt(sensorData.jumlahOrang);
            }

            await tableClient.createEntity(entity);

            context.log('Sensor data saved');
            context.log('   - Suhu:', sensorData.suhu);
        }

        context.res.status = 200;
        context.res.body = {
            success: true,
            message: "Data saved",
            timestamp: timestamp
        };

    } catch (error) {
        context.log.error('Error:', error);
        context.res.status = 500;
        context.res.body = { error: error.message };
    }
};
