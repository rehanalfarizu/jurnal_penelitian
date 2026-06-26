const { TableClient } = require("@azure/data-tables");

/**
 * Azure Function: IoT Hub to Storage Table
 * Receives data from Azure IoT Hub (Event Hub-compatible endpoint) 
 * and stores to Azure Storage Table
 * - Sensor data -> SensorTelemetry table
 * - People count -> PeopleCount table (separate)
 */
module.exports = async function (context, eventHubMessages) {
    context.log(`📥 Processing ${eventHubMessages.length} messages from IoT Hub`);

    try {
        // Dapatkan Storage Connection String
        const connectionString = process.env.STORAGE_CONNECTION_STRING;
        
        if (!connectionString) {
            throw new Error("STORAGE_CONNECTION_STRING not configured");
        }

        // Table clients untuk kedua tabel
        const sensorTableClient = TableClient.fromConnectionString(connectionString, "SensorTelemetry");
        const peopleTableClient = TableClient.fromConnectionString(connectionString, "PeopleCount");

        // Create tables jika belum ada
        await sensorTableClient.createTable().catch(() => {
            context.log('ℹ️  Table SensorTelemetry already exists');
        });
        await peopleTableClient.createTable().catch(() => {
            context.log('ℹ️  Table PeopleCount already exists');
        });

        // Process setiap message
        for (const message of eventHubMessages) {
            try {
                context.log('📊 Processing message:', JSON.stringify(message));

                // Parse data jika berupa string
                const sensorData = typeof message === 'string' ? JSON.parse(message) : message;
                
                // Ambil device ID dari system properties atau dari payload
                const deviceId = context.bindingData.systemPropertiesArray?.[0]?.['iothub-connection-device-id'] 
                    || sensorData.deviceId 
                    || "UNKNOWN_DEVICE";
                
                const timestamp = sensorData.timestamp || new Date().toISOString();
                const rowKey = Date.now().toString() + Math.random().toString(36).substring(2, 7);
                
                // Cek apakah ini data people count (dari Raspberry Pi Camera)
                if (sensorData.jumlahOrang !== undefined || sensorData.sensorType === 'camera_people_counter') {
                    // Simpan ke tabel PeopleCount
                    const peopleEntity = {
                        partitionKey: deviceId,
                        rowKey: rowKey,
                        timestamp: timestamp,
                        count: parseInt(sensorData.jumlahOrang ?? 0),
                        deviceId: deviceId,
                        location: sensorData.location || "Ruang Utama",
                        receivedAt: new Date().toISOString()
                    };
                    
                    await peopleTableClient.createEntity(peopleEntity);
                    context.log('✅ People count saved to PeopleCount table');
                    context.log(`   - Device: ${deviceId}`);
                    context.log(`   - Count: ${peopleEntity.count} orang`);
                    context.log(`   - Location: ${peopleEntity.location}`);
                }
                
                // Cek apakah ini data sensor (dari ESP32)
                if (sensorData.suhu !== undefined || sensorData.temperature !== undefined) {
                    // Simpan ke tabel SensorTelemetry
                    const sensorEntity = {
                        partitionKey: deviceId,
                        rowKey: rowKey,
                        timestamp: timestamp,
                        deviceId: deviceId,
                        receivedAt: new Date().toISOString(),
                        suhu: parseFloat(sensorData.suhu ?? sensorData.temperature),
                        kelembaban: parseFloat(sensorData.kelembaban ?? sensorData.humidity),
                        tegangan: parseFloat(sensorData.tegangan ?? sensorData.voltage),
                        arus: parseFloat(sensorData.arus ?? sensorData.current),
                        daya: parseFloat(sensorData.daya ?? sensorData.power),
                        status_tegangan: sensorData.status_tegangan || "normal",
                        status_arus: sensorData.status_arus || "normal"
                    };
                    
                    // Tambahan field jika ada
                    if (sensorData.energy !== undefined) {
                        sensorEntity.energy = parseFloat(sensorData.energy);
                    }

                    await sensorTableClient.createEntity(sensorEntity);
                    context.log('✅ Sensor data saved to SensorTelemetry table');
                    context.log(`   - Device: ${deviceId}`);
                    context.log(`   - Suhu: ${sensorEntity.suhu}°C`);
                    context.log(`   - Daya: ${sensorEntity.daya}W`);
                }

            } catch (err) {
                context.log.error(`❌ Error processing message: ${err.message}`);
                context.log.error(err.stack);
                // Continue processing other messages
            }
        }

        context.log('✅ All messages processed successfully');

    } catch (error) {
        context.log.error('❌ Fatal error:', error.message);
        context.log.error(error.stack);
        throw error; // Re-throw untuk retry
    }
};
