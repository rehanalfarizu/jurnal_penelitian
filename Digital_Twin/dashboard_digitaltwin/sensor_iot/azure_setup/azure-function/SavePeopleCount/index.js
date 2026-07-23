const { TableClient } = require("@azure/data-tables");

/**
 * Azure Function: Save People Count
 * Receives people count data via HTTP POST and stores to PeopleCount table
 * Used by Raspberry Pi camera or web dashboard
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

    context.log('📥 People count data received');

    try {
        // Validasi request body
        if (!req.body) {
            context.res.status = 400;
            context.res.body = { error: "Request body is required" };
            return;
        }

        const data = req.body;
        context.log('📊 Received:', JSON.stringify(data));

        // Validasi count
        if (data.count === undefined && data.jumlahOrang === undefined) {
            context.res.status = 400;
            context.res.body = { error: "count or jumlahOrang field is required" };
            return;
        }

        // Simpan ke Storage Table
        const connectionString = process.env.STORAGE_CONNECTION_STRING;
        
        if (!connectionString) {
            throw new Error("STORAGE_CONNECTION_STRING not configured");
        }

        // Gunakan tabel PeopleCount
        const tableClient = TableClient.fromConnectionString(connectionString, "PeopleCount");

        // Create table if not exists
        try {
            await tableClient.createTable();
            context.log('✓ PeopleCount table created');
        } catch (e) {
            // Table already exists
        }

        // Standardize timestamp to UTC ISO-8601
        // UI layer converts to local timezone (WIB) only for display
        const deviceId = data.deviceId || "CAMERA_001";
        const count = parseInt(data.count ?? data.jumlahOrang ?? 0);
        const timestamp = data.timestamp || new Date().toISOString();

        const entity = {
            partitionKey: deviceId,
            rowKey: Date.now().toString() + Math.random().toString(36).substring(2, 7),
            timestamp: timestamp, // Always UTC ISO
            count: count,
            deviceId: deviceId,
            location: data.location || "Ruang Utama",
            receivedAt: new Date().toISOString() // Always UTC ISO
        };

        // Insert to table
        await tableClient.createEntity(entity);

        context.log(`✅ People count saved: ${count} orang`);
        context.log(`   - Device: ${deviceId}`);
        context.log(`   - Location: ${entity.location}`);

        context.res.status = 200;
        context.res.body = {
            success: true,
            message: "People count saved",
            data: {
                count: count,
                timestamp: timestamp,
                deviceId: deviceId
            }
        };

    } catch (error) {
        context.log.error('❌ Error:', error.message);
        context.res.status = 500;
        context.res.body = { error: error.message };
    }
};
