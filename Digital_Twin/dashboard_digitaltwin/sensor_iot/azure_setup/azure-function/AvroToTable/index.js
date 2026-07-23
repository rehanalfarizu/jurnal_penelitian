const { TableClient } = require("@azure/data-tables");
const { BlobServiceClient } = require("@azure/storage-blob");

/**
 * Azure Function: Blob to Table
 * BlobTrigger untuk process data dari IoT Hub storage
 * Simpan ke Table Storage untuk historical queries
 */
module.exports = async function (context, myBlob) {
    const blobName = context.bindingData.blobTrigger || "unknown";
    context.log("Processing blob:", blobName);

    try {
        const connectionString = process.env.STORAGE_CONNECTION_STRING;

        // Create table client
        const tableClient = TableClient.fromConnectionString(connectionString, "SensorTelemetryGateway");
        await tableClient.createTable().catch(() => {});

        // Parse blob content
        let content = myBlob;
        if (!content) {
            context.log("No content");
            return;
        }

        // Convert Buffer to string
        let contentStr;
        if (Buffer.isBuffer(content)) {
            contentStr = content.toString('utf8');
        } else if (typeof content === 'string') {
            contentStr = content;
        } else {
            contentStr = JSON.stringify(content);
        }

        // Extract JSON data from Avro-like content
        // Avro format has binary headers, so we look for JSON patterns
        const jsonPatterns = contentStr.match(/\{[^}]*"esp32"[^}]*\}/g);

        if (!jsonPatterns || jsonPatterns.length === 0) {
            context.log("No JSON data found in blob");
            return;
        }

        // Process each JSON object found
        for (const jsonStr of jsonPatterns) {
            try {
                const data = JSON.parse(jsonStr);

                if (!data.esp32) continue;

                const timestamp = data.timestamp || new Date().toISOString();
                const rowKey = Date.now().toString() + Math.random().toString(36).substring(2, 7);

                const entity = {
                    partitionKey: "RASPBERRY_PI_GATEWAY_001",
                    rowKey: rowKey,
                    timestamp: timestamp,
                    deviceId: "RASPBERRY_PI_GATEWAY_001",
                    receivedAt: new Date().toISOString(),
                    // ESP32 data
                    suhu: data.esp32.suhu || 0,
                    kelembaban: data.esp32.kelembaban || 0,
                    tegangan: data.esp32.tegangan || 0,
                    arus: data.esp32.arus || 0,
                    daya: data.esp32.daya || 0,
                    // TinyML
                    tinyml_anomaly: data.esp32.tinyml?.anomaly || false,
                    tinyml_power_mode: data.esp32.tinyml?.power_mode || "unknown",
                    // AC
                    ac_power: data.esp32.ac?.power || null,
                    ac_mode: data.esp32.ac?.mode || null,
                    ac_setpoint: data.esp32.ac?.setpoint || null,
                    // Gateway data
                    gateway_cpu_percent: data.gateway?.cpu_percent || 0,
                    gateway_memory_percent: data.gateway?.memory_percent || 0,
                    gateway_disk_percent: data.gateway?.disk_percent || 0,
                    gateway_cpu_temp: data.gateway?.cpu_temp_c || 0,
                    // Camera
                    people_count: data.camera?.people_count || 0
                };

                await tableClient.createEntity(entity);
                context.log("Saved - Suhu:", entity.suhu, "Kelembaban:", entity.kelembaban);

            } catch (e) {
                context.log("Error parsing JSON:", e.message);
            }
        }

        context.log("Blob processed successfully");

    } catch (error) {
        context.log.error("Error:", error.message);
        throw error;
    }
};
