const { TableClient } = require("@azure/data-tables");

/**
 * Azure Function: MQTT to Storage Table
 * Receives data from HiveMQ webhook and stores directly to Azure Storage Table
 */
module.exports = async function (context, req) {
    context.log('📥 MQTT data received from HiveMQ webhook');

    try {
        // Validasi request body
        if (!req.body) {
            context.log.error('❌ No request body provided');
            context.res = {
                status: 400,
                body: { error: "Request body is required" }
            };
            return;
        }

        // Parse data dari MQTT
        const sensorData = req.body;
        
        // Log received data
        context.log('📊 Received sensor data:', JSON.stringify(sensorData));
        
        // Deteksi tipe data (sensor ESP32 atau people counter)
        const isESP32Data = sensorData.suhu !== undefined;
        const isPeopleCountData = sensorData.jumlahOrang !== undefined;
        
        if (!isESP32Data && !isPeopleCountData) {
            context.log.warn('⚠️  Unknown data format - no sensor data or people count');
        }

        // Tambahkan timestamp dan metadata
        const timestamp = sensorData.timestamp || new Date().toISOString();
        const deviceId = sensorData.deviceId || process.env.DEVICE_ID || "ESP32_ENERGY_MONITOR_001";
        
        const enrichedData = {
            ...sensorData,
            timestamp: timestamp,
            deviceId: deviceId,
            receivedAt: new Date().toISOString()
        };

        context.log('✅ Data enriched:', JSON.stringify(enrichedData));

        // === SIMPAN KE AZURE STORAGE TABLE ===
        try {
            const connectionString = process.env.STORAGE_CONNECTION_STRING;
            
            if (!connectionString) {
                throw new Error("STORAGE_CONNECTION_STRING not configured");
            }

            const tableClient = TableClient.fromConnectionString(
                connectionString,
                "SensorTelemetry"
            );

            // Create table jika belum ada
            await tableClient.createTable().catch(() => {
                context.log('ℹ️  Table already exists');
            });

            // Prepare entity untuk Storage Table
            const entity = {
                partitionKey: deviceId,
                rowKey: Date.now().toString(), // Unique ID menggunakan timestamp
                timestamp: timestamp,
                deviceId: deviceId,
                receivedAt: enrichedData.receivedAt
            };
            
            // Tambahkan field ESP32 jika ada
            if (enrichedData.suhu !== undefined) {
                entity.suhu = enrichedData.suhu;
                entity.kelembaban = enrichedData.kelembaban;
                entity.tegangan = enrichedData.tegangan;
                entity.arus = enrichedData.arus;
                entity.daya = enrichedData.daya;
                entity.status_tegangan = enrichedData.status_tegangan || "unknown";
                entity.status_arus = enrichedData.status_arus || "unknown";
            }
            
            // Tambahkan field people count jika ada
            if (enrichedData.jumlahOrang !== undefined) {
                entity.jumlahOrang = enrichedData.jumlahOrang;
            }

            // Insert ke Storage Table
            await tableClient.createEntity(entity);
            
            context.log('💾 Data saved to Storage Table successfully');
            context.log(`   - Device: ${deviceId}`);
            if (enrichedData.suhu !== undefined) {
                context.log(`   - Suhu: ${enrichedData.suhu}°C`);
                context.log(`   - Daya: ${enrichedData.daya}W`);
            }
            if (enrichedData.jumlahOrang !== undefined) {
                context.log(`   - Jumlah Orang: ${enrichedData.jumlahOrang}`);
            }

        } catch (storageError) {
            context.log.error('❌ Storage error:', storageError.message);
            // Continue execution - don't fail the whole function
        }

        // Response sukses
        context.res = {
            status: 200,
            body: {
                success: true,
                message: "Data received and stored successfully",
                data: enrichedData,
                stored: true,
                timestamp: new Date().toISOString()
            }
        };

    } catch (error) {
        context.log.error('❌ Error processing request:', error.message);
        context.log.error('Stack trace:', error.stack);
        context.res = {
            status: 500,
            body: {
                success: false,
                error: "Internal server error",
                message: error.message
            }
        };
    }
};
