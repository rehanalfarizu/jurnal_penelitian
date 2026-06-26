const { TableClient } = require("@azure/data-tables");

module.exports = async function (context, req) {
    // Version marker
    const FUNCTION_VERSION = 'v2.0-export';

    context.log(`ExportSensorData ${FUNCTION_VERSION} - Request received`);

    // Enable CORS
    context.res = {
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
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

        // Parse query parameters
        const startDate = req.query.startDate || null;
        const endDate = req.query.endDate || null;

        // Parse date range
        let startTime, endTime;
        if (startDate && endDate) {
            startTime = new Date(startDate);
            endTime = new Date(endDate);
        } else {
            // Default: last 7 days
            endTime = new Date();
            startTime = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
        }

        // Add 1 day to endTime to include the full end date
        endTime = new Date(endTime.getTime() + 24 * 60 * 60 * 1000);

        context.log(`Export range: ${startTime.toISOString()} to ${endTime.toISOString()}`);

        // Connect to Azure Table
        const tableClient = TableClient.fromConnectionString(connectionString, "SensorTelemetry");

        // Query parameters
        const DEVICE_FILTER = "PartitionKey eq 'RASPBERRY_PI_GATEWAY_001' or PartitionKey eq 'ESP32_ENERGY_MONITOR_001' or PartitionKey eq 'ESP32_DHT11_Sensor' or PartitionKey eq 'TEST_001'";

        // CSV headers
        const headers = ['Timestamp (UTC)', 'Timestamp (WIB)', 'DeviceID', 'Suhu (C)', 'Kelembaban (%)', 'Tegangan (V)', 'Arus (A)', 'Daya (W)', 'Jumlah Orang'];
        let csvRows = [headers.join(',')];
        let recordCount = 0;
        let continuationToken = null;
        let pageCount = 0;
        let skippedPages = 0;

        context.log('Starting export with client-side filtering...');

        // Fetch all data with pagination - filter client-side
        do {
            const queryOptions = {
                queryOptions: { filter: DEVICE_FILTER }
            };

            if (continuationToken) {
                queryOptions.continuationToken = continuationToken;
            }

            try {
                const allEntities = tableClient.listEntities(queryOptions);
                let entitiesPage = [];

                for await (const entity of allEntities) {
                    entitiesPage.push(entity);
                }

                // Get continuation token for next page
                continuationToken = allEntities.continuationToken;
                pageCount++;

                // Filter and process this page - client-side filtering
                for (const entity of entitiesPage) {
                    const entityTimestamp = entity.timestamp || entity.receivedAt;
                    if (!entityTimestamp) continue;

                    // Client-side date range filter
                    const ts = new Date(entityTimestamp);
                    if (ts >= startTime && ts <= endTime) {
                        // Convert UTC to WIB (UTC+7)
                        const wibDate = new Date(ts.getTime() + 7 * 60 * 60 * 1000);
                        const wibStr = wibDate.toISOString().replace('T', ' ').substring(0, 19);

                        const row = [
                            entityTimestamp,
                            wibStr,
                            entity.PartitionKey || entity.deviceId || '',
                            entity.suhu ?? '',
                            entity.kelembaban ?? '',
                            entity.tegangan ?? '',
                            entity.arus ?? '',
                            entity.daya ?? '',
                            entity.jumlahOrang ?? entity.people_count ?? ''
                        ];

                        csvRows.push(row.map(v => `"${v}"`).join(','));
                        recordCount++;
                    }
                }

                // Log progress every 10 pages
                if (pageCount % 10 === 0) {
                    context.log(`Progress: Page ${pageCount}, Records: ${recordCount}`);
                }

                // Safety limit: stop after 500 pages (500k records)
                if (pageCount >= 500) {
                    context.log('Reached maximum page limit (500)');
                    break;
                }

            } catch (pageError) {
                context.log.error(`Error on page ${pageCount}: ${pageError.message}`);
                skippedPages++;
                // Continue to next page even if current page fails
                continuationToken = null;
            }

        } while (continuationToken);

        context.log(`Export completed: ${recordCount} records in ${pageCount} pages (skipped: ${skippedPages})`);

        // Generate filename
        const startStr = startTime.toISOString().split('T')[0];
        const endStr = endTime.toISOString().split('T')[0];
        const filename = `sensor-data-${startStr}-to-${endStr}.csv`;

        context.res = {
            status: 200,
            headers: {
                'Content-Type': 'text/csv;charset=utf-8',
                'Content-Disposition': `attachment; filename="${filename}"`,
                'X-Record-Count': recordCount.toString(),
                'X-Page-Count': pageCount.toString(),
                'X-Function-Version': FUNCTION_VERSION
            },
            body: csvRows.join('\n')
        };

    } catch (error) {
        context.log.error('Export error:', error);
        context.res.status = 500;
        context.res.body = { error: error.message };
    }
};