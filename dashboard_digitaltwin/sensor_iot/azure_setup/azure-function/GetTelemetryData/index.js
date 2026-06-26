const { TableClient } = require("@azure/data-tables");

module.exports = async function (context, req) {
    // Enable CORS
    context.res = {
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        }
    };

    // Handle OPTIONS preflight request
    if (req.method === 'OPTIONS') {
        context.res.status = 200;
        return;
    }

    try {
        const connectionString = process.env.STORAGE_CONNECTION_STRING;
        
        if (!connectionString) {
            context.res.status = 500;
            context.res.body = { error: "Storage connection string not configured" };
            return;
        }

        const tableClient = TableClient.fromConnectionString(
            connectionString,
            "SensorTelemetry"
        );

        const action = context.bindingData.action || 'latest';
        const hours = parseInt(req.query.hours) || 24;
        const limit = parseInt(req.query.limit) || 100;

        context.log(`API called: action=${action}, hours=${hours}, limit=${limit}`);

        switch (action) {
            case 'latest':
                await handleLatest(context, tableClient);
                break;
            case 'history':
                await handleHistory(context, tableClient, hours, limit);
                break;
            case 'stats':
                await handleStats(context, tableClient, hours);
                break;
            case 'people':
                await handlePeopleCount(context, connectionString, hours, limit);
                break;
            default:
                context.res.status = 400;
                context.res.body = { error: "Invalid action. Use: latest, history, stats, or people" };
        }

    } catch (error) {
        context.log.error('Error:', error);
        context.res.status = 500;
        context.res.body = { error: error.message };
    }
};

// Fungsi untuk format timestamp (UTC ISO di storage, UI convert ke local timezone)
// Konversi WIB hanya dilakukan di layer presentasi (Vue), bukan di API response
function toWIB(utcDateString) {
    const date = new Date(utcDateString);
    const wibOffset = 7 * 60 * 60 * 1000;
    const wibDate = new Date(date.getTime() + wibOffset);
    return wibDate.toISOString().replace('T', ' ').replace('Z', ' WIB').substring(0, 23) + ' WIB';
}

// Hanya untuk display di UI (opsional, bisa dihapus nanti jika frontend handle conversion)
// Sebaiknya frontend yang handle konversi local timezone
function formatTimestamp(utcDateString, forDisplay = false) {
    if (!utcDateString) return null;
    if (forDisplay) {
        return toWIB(utcDateString);
    }
    // Default: return UTC ISO (konsisten dengan storage)
    return new Date(utcDateString).toISOString();
}

async function handleLatest(context, tableClient) {
    // Support ESP32 device IDs AND RPi Gateway (new architecture)
    const entities = tableClient.listEntities({
        queryOptions: { filter: "PartitionKey eq 'ESP32_ENERGY_MONITOR_001' or PartitionKey eq 'ESP32_DHT11_Sensor' or PartitionKey eq 'RASPBERRY_PI_GATEWAY_001'" }
    });

    let latest = null;
    for await (const entity of entities) {
        if (!latest || new Date(entity.timestamp || entity.receivedAt) > new Date(latest.timestamp || latest.receivedAt)) {
            latest = entity;
        }
    }

    if (latest) {
        // Return UTC ISO timestamp - frontend handles timezone conversion for display
        const timestampUtc = latest.timestamp || latest.receivedAt || new Date().toISOString();
        context.res.status = 200;
        context.res.body = {
            success: true,
            data: {
                timestamp: timestampUtc, // UTC ISO - consistent with storage
                timestamp_display: toWIB(timestampUtc), // Optional: for quick UI use (deprecated, keep for backward compat)
                suhu: latest.suhu,
                kelembaban: latest.kelembaban,
                tegangan: latest.tegangan,
                arus: latest.arus,
                daya: latest.daya,
                deviceId: latest.deviceId || latest.PartitionKey,
                people_count: latest.jumlahOrang || latest.people_count || 0 // Add people count
            }
        };
    } else {
        context.res.status = 404;
        context.res.body = { error: "No data found" };
    }
}

async function handleHistory(context, tableClient, hours, limit) {
    const cutoffTime = new Date(Date.now() - hours * 60 * 60 * 1000);
    // Support ESP32 device IDs AND RPi Gateway (new architecture)
    const entities = tableClient.listEntities({
        queryOptions: { filter: "PartitionKey eq 'ESP32_ENERGY_MONITOR_001' or PartitionKey eq 'ESP32_DHT11_Sensor' or PartitionKey eq 'RASPBERRY_PI_GATEWAY_001'" }
    });

    const data = [];
    for await (const entity of entities) {
        const entityTimestamp = entity.timestamp || entity.receivedAt;
        if (entityTimestamp && new Date(entityTimestamp) >= cutoffTime) {
            data.push({
                timestamp: entityTimestamp,
                suhu: entity.suhu,
                kelembaban: entity.kelembaban,
                tegangan: entity.tegangan,
                arus: entity.arus,
                daya: entity.daya
            });
        }
    }

    // Sort by timestamp descending
    data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    const limitedData = data.slice(0, limit);

    context.res.status = 200;
    context.res.body = {
        success: true,
        count: limitedData.length,
        hours: hours,
        data: limitedData
    };
}

async function handleStats(context, tableClient, hours) {
    const cutoffTime = new Date(Date.now() - hours * 60 * 60 * 1000);
    // Support ESP32 device IDs AND RPi Gateway (new architecture)
    const entities = tableClient.listEntities({
        queryOptions: { filter: "PartitionKey eq 'ESP32_ENERGY_MONITOR_001' or PartitionKey eq 'ESP32_DHT11_Sensor' or PartitionKey eq 'RASPBERRY_PI_GATEWAY_001'" }
    });

    let count = 0;
    let totalSuhu = 0, totalKelembaban = 0, totalTegangan = 0, totalArus = 0, totalDaya = 0;
    let maxSuhu = -Infinity, minSuhu = Infinity;
    let maxDaya = -Infinity, minDaya = Infinity;

    for await (const entity of entities) {
        const entityTimestamp = entity.timestamp || entity.receivedAt;
        if (entityTimestamp && new Date(entityTimestamp) >= cutoffTime) {
            count++;
            totalSuhu += entity.suhu || 0;
            totalKelembaban += entity.kelembaban || 0;
            totalTegangan += entity.tegangan || 0;
            totalArus += entity.arus || 0;
            totalDaya += entity.daya || 0;

            maxSuhu = Math.max(maxSuhu, entity.suhu || 0);
            minSuhu = Math.min(minSuhu, entity.suhu || 0);
            maxDaya = Math.max(maxDaya, entity.daya || 0);
            minDaya = Math.min(minDaya, entity.daya || 0);
        }
    }

    if (count > 0) {
        context.res.status = 200;
        context.res.body = {
            success: true,
            hours: hours,
            count: count,
            averages: {
                suhu: parseFloat((totalSuhu / count).toFixed(2)),
                kelembaban: parseFloat((totalKelembaban / count).toFixed(2)),
                tegangan: parseFloat((totalTegangan / count).toFixed(2)),
                arus: parseFloat((totalArus / count).toFixed(4)),
                daya: parseFloat((totalDaya / count).toFixed(2))
            },
            ranges: {
                suhu: { min: minSuhu, max: maxSuhu },
                daya: { min: minDaya, max: maxDaya }
            }
        };
    } else {
        context.res.status = 404;
        context.res.body = { error: "No data found for the specified time range" };
    }
}

async function handlePeopleCount(context, connectionString, hours, limit) {
    try {
        const tableClient = TableClient.fromConnectionString(
            connectionString,
            "PeopleCount"
        );
        
        // Coba buat tabel jika belum ada
        try {
            await tableClient.createTable();
            context.log('✓ PeopleCount table created');
        } catch (e) {
            // Table already exists
        }
        
        const cutoffTime = new Date(Date.now() - hours * 60 * 60 * 1000);
        const entities = tableClient.listEntities();
        
        const data = [];
        let latestCount = 0;
        let latestTimestamp = null;
        
        for await (const entity of entities) {
            const entityTime = new Date(entity.timestamp);
            if (entityTime >= cutoffTime) {
                const item = {
                    timestamp: entity.timestamp, // UTC ISO - consistent with storage
                    timestamp_display: toWIB(entity.timestamp), // Optional: for quick UI use (deprecated)
                    count: entity.count || entity.jumlahOrang || 0,
                    location: entity.location || 'Ruang Utama',
                    deviceId: entity.deviceId || 'CAMERA_001'
                };
                data.push(item);
                
                // Track latest entry
                if (!latestTimestamp || entityTime > latestTimestamp) {
                    latestTimestamp = entityTime;
                    latestCount = item.count;
                }
            }
            if (data.length >= limit) break;
        }
        
        // Sort by timestamp descending
        data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
        context.res.status = 200;
        context.res.body = {
            success: true,
            totalRecords: data.length,
            hours: hours,
            latest: {
                count: latestCount,
                timestamp: latestTimestamp ? latestTimestamp.toISOString() : null // UTC ISO
            },
            data: data
        };
    } catch (error) {
        context.log.error('Error fetching people count:', error);
        context.res.status = 200;
        context.res.body = {
            success: true,
            totalRecords: 0,
            hours: hours,
            latest: {
                count: 0,
                timestamp: null
            },
            data: [],
            note: "PeopleCount table may be empty or not created yet"
        };
    }
}
